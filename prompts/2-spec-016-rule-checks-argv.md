---
status: draft
spec: [016-bug-review-scripts-argv-e2big]
created: "2026-11-04T15:45:00Z"
branch: dark-factory/bug-review-scripts-argv-e2big
---

# Bounded, argv-free findings and aggregate in `scripts/rule-checks.sh`

<summary>
- Script-tier checks complete on an ordinary large PR instead of aborting when the aggregate findings map exceeds 128 KiB.
- No individual finding and no aggregate map is passed to `jq` as a command-line argument.
- Each finding's text and message are bounded and marked exactly as the scanner does, using the shared helper from prompt 1.
- A 200-finding fixture whose combined map is over 128 KiB proves the fix behaviorally; the same fixture makes the pre-fix script exit 126.
- The emitted finding keeps exactly its seven existing keys, with `matched_text` and `message` as strings.
- The "always exit 0" contract, every rule check, and the `.git/COMMIT_EDITMSG` finding behaviour are unchanged.
- The fixture test is wired into `make precommit`.
</summary>

<objective>
Fix `scripts/rule-checks.sh` so `emit_finding` never passes a payload through argv and the aggregate is assembled from a file, reusing the shared helper created in prompt 1. This is prompt **2 of 3** for spec 016. It covers Desired Behaviors 2, 3, 4, 5, 6 and 8 and Acceptance Criteria AC3, AC6 and AC8.
</objective>

<context>
Read fully before editing:

- `specs/in-progress/016-bug-review-scripts-argv-e2big.md` — Problem, Goal, Non-goals, Desired Behavior 2–8, AC3, AC6, AC8, Failure Modes, Constraints.
- `scripts/rule-checks.sh` — the whole file. The relevant symbols are:
  - `set -euo pipefail` at the top.
  - `emit_finding` (the `jq -cn --arg owner ... --arg matched_text "$text" --arg message "$msg"` construction).
  - `FINDINGS_FILE`, `FINDINGS_COUNT`.
  - every rule check function; none of them changes.
  - the aggregate block at the end: `owner=$(...)`, `clean_finding=$(...)`, `jq --arg o ... --argjson f "$clean_finding"`, `FBO_JSON`, and the final `jq -n --argjson findings_by_owner "$FBO_JSON"`.
- `scripts/ast-grep-runner.sh` and `scripts/lib/truncate-utf8.sh` — created in prompt 1. If the helper is missing, stop and report that prompt 1 must run first.
- `scripts/tests/test-changelog-unreleased-fold.sh` — copy its test style: `set -uo pipefail`, a `TMP` dir with `trap`, `ok` / `no` helpers, exit 1 on any failure.
- `Makefile` — the `precommit` prerequisite line and the `test-changelog-unreleased-fold` target shape.
- `scripts/acceptance.sh` sections 5(e) and 6/8 — they run `rule-checks.sh` over the self-containment fixtures and assert the four rule ids and the clean-fixture zero count. The change must keep both green.
- `/home/node/.claude/plugins/marketplaces/coding/docs/self-containment-guide.md` — the repo's own script-tier rules. The new test file under `scripts/tests/` is **not** exempt, so it must not contain a literal home-directory path, a planning-doc reference, a requirement id, or revision metadata. Build the `~/` fixture text dynamically.

**Verified repo facts this prompt relies on**

- `jq --slurpfile name file` reads the file into an array; a file containing one JSON value is available as `$name[0]`.
- `jq -s 'reduce .[] as $f ({}; .[$f.owner] += [($f | del(.owner))])' findings.jsonl` groups compact one-object-per-line findings by owner, preserves first-seen owner order and per-owner order, and removes the `owner` key. It reads the payload from a file, never argv.
- `emit_finding` writes compact JSON with `jq -cn`, so `FINDINGS_FILE` is one complete JSON object per line and is safe for `jq -s`.
- A prototype of the changes below was run against a 200-file fixture whose 200 findings produce a combined `findings_by_owner` of 232233 bytes: the fixed script exits 0 with `findings_count=200`; the pre-fix script exits 126 with empty stdout (`jq: Argument list too long`).
- The same prototype leaves `scripts/acceptance.sh`'s invariants green: the dirty self-containment fixture yields all four ids, the clean fixture yields 0, and the `.git/` exclusion still yields 0 `.git/` findings and 1 `pkg/real.go` finding.
- `shellcheck scripts/rule-checks.sh` currently exits 1 on a pre-existing SC2015 at the `resolved="$(cd "$gomod_dir" && cd "$rhs" 2>/dev/null && pwd || true)"` assignment in `check_no_cross_repo_replace`. AC10 requires exit 0; add a `# shellcheck disable=SC2015` directive with the one-line justification that the failed `cd` is meant to yield an empty path.

**Do not change these surfaces**

- Every rule check function and its `emit_finding` call sites.
- The `.git/` behaviour: findings whose file is `$TARGET_DIR/.git/COMMIT_EDITMSG` still carry that path.
- The `stats` object shape and the "always exit 0 on non-fatal tooling problems" contract.
- The rule-checks output's seven-field finding objects (the `owner` key is added for grouping and stripped before output).
</context>

<requirements>

### 1. Source the shared helper

Immediately after `set -euo pipefail`, add:

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091  # sourced helper lives beside the caller
. "$SCRIPT_DIR/lib/truncate-utf8.sh"
```

### 2. Replace `emit_finding`

Replace the function body with the following. Keep the signature and the `FINDINGS_COUNT` increment. Keep the jq program's key expression exactly `rule_level:$rule_level` (the parameter is `--arg rule_level "$level"`).

```bash
emit_finding() {
  local owner="$1" rule_id="$2" level="$3" file="$4"
  local line="${5:-0}" col="${6:-0}" text="$7" msg="$8"
  local text_raw="$TMPDIR_WORK/emit_text_raw"
  local msg_raw="$TMPDIR_WORK/emit_message_raw"
  local text_out="$TMPDIR_WORK/emit_text"
  local msg_out="$TMPDIR_WORK/emit_message"
  printf '%s' "$text" > "$text_raw"
  printf '%s' "$msg" > "$msg_raw"
  truncate_utf8_file 8192 "$text_raw" "$text_out"
  truncate_utf8_file 1024 "$msg_raw" "$msg_out"
  jq -cn \
    --arg owner "$owner" \
    --arg rule_id "$rule_id" \
    --arg rule_level "$level" \
    --arg file "$file" \
    --argjson line "$line" \
    --argjson column "$col" \
    --rawfile matched_text "$text_out" \
    --rawfile message "$msg_out" \
    '{owner:$owner, rule_id:$rule_id, rule_level:$rule_level, file:$file, line:$line, column:$column, matched_text:$matched_text, message:$message}' \
    >> "$FINDINGS_FILE"
  FINDINGS_COUNT=$((FINDINGS_COUNT + 1))
}
```

The function arguments are shell-function arguments, not an external process's argv, so `$text` / `$msg` may stay in the signature. The payload must not reach `jq` as an argument: write it to a file and use `--rawfile`.

### 3. Replace the aggregate block

Replace the entire tail block that begins `if [ -s "$FINDINGS_FILE" ]; then` and ends with the final `jq -n ... --argjson findings_by_owner "$FBO_JSON" ...` with:

```bash
if [ -s "$FINDINGS_FILE" ]; then
  jq -s 'reduce .[] as $f ({}; .[$f.owner] += [($f | del(.owner))])' \
    "$FINDINGS_FILE" > "$FBO_FILE"
fi

jq -n \
  --argjson findings_count "$FINDINGS_COUNT" \
  --argjson elapsed_ms "$ELAPSED" \
  --slurpfile findings_by_owner "$FBO_FILE" \
  '{stats:{yamls_run:0, findings_count:$findings_count, elapsed_ms:$elapsed_ms}, findings_by_owner:$findings_by_owner[0], errors:[]}'
```

Remove the now-unused `owner=`, `clean_finding=`, `FBO_TMP`, and `FBO_JSON` assignments. `FBO_FILE` remains initialized to `{}` before this block, so an empty findings file still yields `findings_by_owner: {}`.

### 4. Silence the pre-existing SC2015 so AC10 can hold

In `check_no_cross_repo_replace`, on the assignment

```bash
              resolved="$(cd "$gomod_dir" && cd "$rhs" 2>/dev/null && pwd || true)"
```

add a directive immediately above it:

```bash
              # shellcheck disable=SC2015  # intentional: a failed cd yields an empty path
```

Do not restructure the assignment; this is a lint directive only.

### 5. Add `scripts/tests/test-rule-checks-argv.sh`

Create a fixture test in the style of `scripts/tests/test-changelog-unreleased-fold.sh`. Use `set -uo pipefail` (no `-e`), a `TMP` dir with `trap 'rm -rf "$TMP"' EXIT`, `ok` / `no` helpers, and exit 1 if any case failed. Derive `REPO="$(cd "$(dirname "$0")/../.." && pwd)"`.

The script must cover:

**Case A — AC3 (ordinary large run).** Create 200 files under `$TMP/rc/src`, each containing one line of about 900 bytes that trips `self-containment/no-home-dir-paths`. Build the line dynamically so the test file itself carries no literal home-directory path:

```bash
PAD=$(printf 'a%.0s' $(seq 1 880))
for i in $(seq 1 200); do
  printf 'x = %s/%s\n' '~' "$PAD" > "$TMP/rc/src/f$(printf '%03d' "$i").txt"
done
FILES=("$TMP"/rc/src/*.txt)
```

Pass the files as a bash array, quoted: `bash "$REPO/scripts/rule-checks.sh" "$TMP/rc" "${FILES[@]}"`. Do not rely on unquoted word splitting. Assert:
- exit status is 0;
- `.stats.findings_count >= 200`;
- the combined map is over 131072 bytes: `jq -c '.findings_by_owner' out.json | wc -c` is greater than 131072 (the assertion must check the byte size, not only the count — 200 small findings sum to about 50 KB and would pass against the unfixed script);
- every emitted finding has exactly the seven keys `column,file,line,matched_text,message,rule_id,rule_level` and `matched_text` / `message` are strings.

**Case B — AC3 pre-fix proof.** Derive the pre-fix script at test time:

```bash
mkdir -p "$TMP/prefix"
git -C "$REPO" show origin/master:scripts/rule-checks.sh > "$TMP/prefix/rule-checks.sh"
```

If `git -C "$REPO" rev-parse --verify origin/master` fails, report a failure with a clear message; do not skip. Run the pre-fix script over the same 200-file fixture. Assert its exit status is 126 and its stdout is empty. This is the behavioural proof that the fixture is meaningful and that the aggregate conversion is what fixed it.

**Case C — AC6 (no payload in argv).** Assert both greps report a count of 0:

```bash
grep -cE -- '--arg(json)? (matched_text|message)' "$REPO/scripts/ast-grep-runner.sh" "$REPO/scripts/rule-checks.sh"
grep -c -- '--argjson findings_by_owner' "$REPO/scripts/rule-checks.sh"
```

The greps key on the jq parameter name, not the shell variable, so renaming a shell variable cannot defeat them. `grep -c` exits 1 at zero matches; capture the count and assert it is 0.

**Case D — AC7 for script-tier findings.** Assert a finding from the 200-file run has exactly the seven keys and string types (the `owner` grouping key must be gone from the emitted object).

**Self-containment:** the test file must not contain a literal home-directory path (`~/` or `/Users/` or `/home/`), a planning-doc reference (`specs/`, `prompts/`, `docs/plans/`), a requirement id (`FR-`, `NFR-`, `SC-` followed by a digit), or revision metadata. The `printf 'x = %s/%s\n' '~' "$PAD"` construction above keeps `~` and `/` apart in the source.

### 6. Wire the test into `make precommit`

Add this target to `Makefile`:

```make
.PHONY: test-rule-checks-argv
test-rule-checks-argv:
	@bash scripts/tests/test-rule-checks-argv.sh
```

Add `test-rule-checks-argv` to the `precommit:` prerequisite list, after `test-ast-grep-runner-truncation` (added by prompt 1). Do not remove or reorder the existing prerequisites.

### 7. Keep shellcheck clean

`shellcheck scripts/rule-checks.sh scripts/tests/test-rule-checks-argv.sh` must exit 0. The `# shellcheck disable=SC1091` on the source line and the `# shellcheck disable=SC2015` above the `resolved=` assignment are required.
</requirements>

<constraints>
- The emitted JSON schema, key names and types do not change: each finding carries exactly `rule_id`, `rule_level`, `file`, `line`, `column`, `matched_text`, `message`; the internal `owner` key is stripped before output.
- `matched_text` is bounded to 8192 bytes; `message` to 1024 bytes, cut on a UTF-8 rune boundary, with the `…[truncated, original <N> bytes]` marker inside the string.
- No payload field may be passed as a command-line argument to `jq`. In particular, `--arg matched_text`, `--arg message`, `--argjson f`, and `--argjson findings_by_owner` must be gone; use `--rawfile` and `--slurpfile`.
- Keep the documented "always exit 0" contract on non-fatal tooling problems. Exit 2 remains the bad-invocation code.
- Do not change any rule check function, the `.git/COMMIT_EDITMSG` finding behaviour, or the `stats` shape.
- Do not add a configurable cap: 8192 and 1024 are fixed values.
- Do not modify `scripts/ast-grep-runner.sh` or `scripts/lib/truncate-utf8.sh` in this prompt; prompt 1 owns them. If the helper is missing, stop and report that prompt 1 must run first.
- Do not edit `agents/ast-grep-runner.md` or `CHANGELOG.md`; prompt 3 owns them.
- Both scripts must keep working under `set -euo pipefail`.
- No new runtime dependency: the JSON tool and coreutils are already required; `python3` is already invoked by both scripts.
- `.reviewignore` handling is out of scope.
- The new test file under `scripts/` must pass the repo's own self-containment script-tier rules.
- Do NOT commit — dark-factory handles git.
- Existing tests and `make precommit` must still pass, including `scripts/acceptance.sh` sections 5(e) and 6/8.

**Open question surfaced for the auditor:** the pre-existing SC2015 in `rule-checks.sh` means AC10's `shellcheck ... exits 0` cannot hold without a directive or a refactor. This prompt adds a justified `# shellcheck disable=SC2015` (the failed `cd` is meant to yield an empty path) rather than changing runtime behaviour. If the auditor prefers a structural fix, the equivalent is `if ! resolved="$(cd "$gomod_dir" && cd "$rhs" 2>/dev/null && pwd)"; then resolved=""; fi`.
</constraints>

<verification>
Run from the repo root:

```bash
make precommit
shellcheck scripts/rule-checks.sh scripts/tests/test-rule-checks-argv.sh
bash scripts/tests/test-rule-checks-argv.sh
```

Assert the AC6 greps directly:

```bash
test "$(grep -cE -- '--arg(json)? (matched_text|message)' scripts/ast-grep-runner.sh scripts/rule-checks.sh | awk -F: '{s+=$2} END{print s+0}')" -eq 0
test "$(grep -c -- '--argjson findings_by_owner' scripts/rule-checks.sh || true)" -eq 0
```

The fixture test proves AC3 (200 findings, combined map over 131072 bytes, exit 0; pre-fix exit 126), AC6 (both greps zero) and AC7 (seven keys, string types). `make precommit` re-runs `scripts/acceptance.sh`, which locks the self-containment dirty/clean fixtures and the `.git/` exclusion.
</verification>
