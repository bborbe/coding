---
status: completed
spec: [016-bug-review-scripts-argv-e2big]
summary: 'Reworked scripts/ast-grep-runner.sh to build findings via --rawfile with a shared UTF-8 rune-boundary bounding helper (matched_text <=8192, message <=1024, in-string truncation marker), added fixture tests wired into make precommit, and recorded the fix under ## Unreleased.'
execution_id: 54185fc5-1ec7-51b6-a771-ceb64f2118a7-exec-061-spec-016-ast-grep-runner-argv
dark-factory-version: dev
created: "2026-11-04T15:45:00Z"
queued: "2026-11-04T15:51:07Z"
started: "2026-11-04T15:51:09Z"
completed: "2026-11-04T15:55:17Z"
branch: dark-factory/bug-review-scripts-argv-e2big
---

# Bounded, argv-free finding construction in `scripts/ast-grep-runner.sh`

<summary>
- The mechanical scanner completes and emits findings even when one matched node is 128 KiB or larger, instead of aborting with `jq: Argument list too long`.
- A matched text longer than 8192 bytes is cut on a UTF-8 rune boundary and visibly marked inside the string, so the finding survives the consumer's fixed seven-field struct.
- A rule message longer than 1024 bytes is bounded the same way, covering messages that interpolate matched content.
- A match under its bound is emitted byte-for-byte identically to today's output, with no marker.
- The emitted finding keeps exactly its seven existing keys; no new JSON field is added.
- The existing `.git/` path filtering, the final `--slurpfile` assembly and the exit-code meanings are untouched.
- Fixture tests for the 131072-byte match, the interpolated message, the exact-bound case, the split-rune case and the small-match golden are wired into `make precommit`.
- A shared field-bounding helper is introduced for this prompt and reused by the script-tier prompt that follows.
</summary>

<objective>
Fix `scripts/ast-grep-runner.sh` so no finding payload is ever passed to `jq` as a command-line argument, and so `matched_text` / `message` are bounded with an in-string marker. This is prompt **1 of 3** for spec 016. It covers Desired Behaviors 1, 3, 4, 5, 6, 7 and 8 and Acceptance Criteria AC1, AC2, AC4, AC5 and AC7. It also creates the shared helper that prompt 2 reuses.
</objective>

<context>
Read fully before editing:

- `specs/in-progress/016-bug-review-scripts-argv-e2big.md` — Problem, Goal, Non-goals, Assumptions, Desired Behavior 1–9, Acceptance Criteria AC1, AC2, AC4, AC5, AC7, AC8, Failure Modes, Constraints.
- `scripts/ast-grep-runner.sh` — the whole file. The relevant symbols are:
  - `ROOT` (the repo-root derivation near the top of the helpers section).
  - the `trap 'rm -rf "$TMPDIR_WORK"' EXIT` line and the `TMPDIR_WORK` setup.
  - `append_error` and `append_finding`.
  - the `.git/` changed-file filter inside the `for f in "$@"` loop.
  - the per-match loop `while IFS= read -r match_line; do ... done < "$SCAN_OUT"` inside the `while IFS=$'\t' read -r rule_id yml_rel owner level` loop.
  - the per-match `.git/` case arm.
  - the final assembly loop that uses `--slurpfile arr "$owner_file"`.
  - the final `jq -n --slurpfile findings_by_owner_arr ... --slurpfile errors_arr ...`.
- `scripts/rule-checks.sh` — read it only to understand the shared JSON contract; **do not edit it in this prompt**.
- `scripts/tests/test-changelog-unreleased-fold.sh` — copy its test style: `set -uo pipefail`, a `TMP` dir with `trap`, `ok`/`no` helpers, per-case `expect_*` helpers, exit 1 on any failure.
- `Makefile` — the `precommit` prerequisite line and the `test-changelog-unreleased-fold` target shape.
- `agents/ast-grep-runner.md` — the JSON contract; do not edit it in this prompt (prompt 3 owns it).
- `scripts/acceptance.sh` section 5(e) and section 6/8 — both exercise this runner and `rule-checks.sh`; the change must keep them green.
- `/home/node/.claude/plugins/marketplaces/coding/docs/self-containment-guide.md` — the repo's own script-tier rules. The new helper and test files under `scripts/` are **not** exempt (only `specs/`, `prompts/`, `scripts/testdata/self-containment/`, `scripts/rule-checks.sh`, and two doc/agent paths are exempt), so they must not contain a literal home-directory path, a planning-doc reference, a requirement id, or revision metadata.

**Verified repo facts this prompt relies on**

- `ast-grep` is installed in the container (`/usr/local/share/npm-global/bin/ast-grep`). `jq` is 1.6 in the container; `--rawfile`, `--slurpfile`, `utf8bytelength` are available since jq 1.5.
- `rules/go/no-fmt-errorf.yml` matches a `call_expression` whose function is `fmt.Errorf`. A source line `return fmt.Errorf("%s", "<payload>")` produces a match whose `.text` is exactly `fmt.Errorf("%s", "<payload>")`. The prefix `fmt.Errorf("%s", "` is 18 bytes and the suffix `")` is 2 bytes, so a payload of `131072 - 18 - 2 = 131052` bytes yields a matched text of exactly 131072 bytes. This was verified with the real rule in the container.
- The rule's `message` is a YAML block scalar and therefore carries a trailing newline. Today's `matched_text=$(printf '%s' "$match_line" | jq -r '.text // ""')` / `message=$(... | jq -r '.message // ""')` command substitutions strip **all** trailing newlines. The replacement must strip them too, or AC4's byte-identical golden fails. This was verified: a small match is byte-identical only after the trailing newline is stripped.
- `jq -j '.text // ""'` writes the exact string with no added newline; `--rawfile` reads a file byte-for-byte with no newline stripping.
- `python3` is already a hard dependency of this script (`START_MS` / `END_MS` use it), so the byte-accurate cut adds no new runtime dependency.
- The container's `origin/master` exists (`6866cd4`), so `git -C "$REPO" show origin/master:scripts/ast-grep-runner.sh` can derive the pre-fix golden at test time.
- A pre-fix prototype with a 131072-byte match exits 126 with empty stdout; the fixed prototype exits 0 with the truncated, marked finding. The fixed prototype's small-match finding is byte-identical to the `origin/master` finding after `jq -cS` normalisation.

**Do not change these surfaces**

- The `.git/` changed-file filter (`*/.git/*) continue ;;` in the `for f in "$@"` loop) and the per-match `.git/` case arm.
- The `--slurpfile arr "$owner_file"` merge block and the final `--slurpfile findings_by_owner_arr` / `--slurpfile errors_arr` assembly.
- `append_error` and `append_finding` behaviour.
- Exit codes: `0` = ran, `2` = ast-grep missing / bad invocation.
</context>

<requirements>

### 1. Create `scripts/lib/truncate-utf8.sh`

Create the file with exactly this function (comments included; keep it shellcheck-clean and bash 3.2 compatible):

```bash
#!/usr/bin/env bash
# Shared field-bounding helper for the mechanical funnel scripts.
#
# truncate_utf8_file <limit-bytes> <input-file> <output-file>
#
# Mirrors the extraction the callers used before this change: trailing
# newlines are stripped (the old `$(...)` did that), then the value is
# bounded to <limit-bytes> on a UTF-8 rune boundary. A value that was cut
# ends with `…[truncated, original <N> bytes]`, where <N> is the pre-cut
# byte length after the trailing-newline strip. The marker is part of the
# string value, so it survives a consumer that re-marshals a fixed field set.
#
# python3 is already a hard dependency of both callers (they use it for
# START_MS/END_MS), so the byte-accurate cut adds no new runtime dependency.

truncate_utf8_file() {
  local limit="$1" in="$2" out="$3"
  local size

  if ! size=$(wc -c < "$in"); then
    printf 'error: truncate-utf8: cannot read %s\n' "$in" >&2
    return 1
  fi

  # Common case: the field is small. Strip trailing newlines exactly as the
  # previous `$(...)` extraction did and write it through unchanged.
  if [ "$size" -le "$limit" ]; then
    if ! printf '%s' "$(cat "$in")" > "$out"; then
      printf 'error: truncate-utf8: cannot write %s\n' "$out" >&2
      return 1
    fi
    return 0
  fi

  # Oversized: cut on a rune boundary. The bound is in bytes, so a plain
  # character slice is not enough; back off over continuation bytes and drop
  # a lead byte whose sequence is incomplete at the cut.
  if ! python3 - "$limit" "$in" "$out" <<'PY'
import sys

limit = int(sys.argv[1])
with open(sys.argv[2], 'rb') as fh:
    data = fh.read().rstrip(b'\n')

if len(data) <= limit:
    out = data
else:
    cut = data[:limit]
    j = len(cut) - 1
    while j >= 0 and (cut[j] & 0xC0) == 0x80:
        j -= 1
    if j < 0:
        cut = b''
    else:
        lead = cut[j]
        if lead < 0x80:
            need = 1
        elif (lead & 0xE0) == 0xC0:
            need = 2
        elif (lead & 0xF0) == 0xE0:
            need = 3
        elif (lead & 0xF8) == 0xF0:
            need = 4
        else:
            need = 1
        have = len(cut) - j
        cut = cut[:j + need] if have >= need else cut[:j]
    out = cut + ('…[truncated, original %d bytes]' % len(data)).encode('utf-8')

with open(sys.argv[3], 'wb') as fh:
    fh.write(out)
PY
  then
    printf 'error: truncate-utf8: cannot process %s\n' "$in" >&2
    return 1
  fi
}
```

The marker is the Unicode ellipsis U+2026 followed by `[truncated, original <N> bytes]`. The bound applies to the cut content only; the marker is appended beyond the bound.

### 2. Source the helper from `scripts/ast-grep-runner.sh`

Immediately after the `ROOT="$(cd "$(dirname "$0")/.." && pwd)"` assignment, add:

```bash
# shellcheck disable=SC1091  # sourced helper lives beside the caller
. "$ROOT/scripts/lib/truncate-utf8.sh"
```

### 3. Define per-match scratch paths

Immediately after `trap 'rm -rf "$TMPDIR_WORK"' EXIT`, add:

```bash
MATCH_TEXT_RAW="$TMPDIR_WORK/match_text_raw"
MATCH_MSG_RAW="$TMPDIR_WORK/match_message_raw"
MATCH_TEXT_OUT="$TMPDIR_WORK/match_text"
MATCH_MSG_OUT="$TMPDIR_WORK/match_message"
```

### 4. Replace the per-match construction

In the `while IFS= read -r match_line; do ... done < "$SCAN_OUT"` loop, replace the current block that extracts `matched_text` and `message` and builds `finding` with the following. Keep the `file` / `line` / `column` extraction and the `.git/` case arm in place.

Old:

```bash
      # Extract fields from the stream match object
      file=$(printf '%s' "$match_line" | jq -r '.file // ""')
      line=$(printf '%s' "$match_line" | jq -r '.range.start.line // 0')
      column=$(printf '%s' "$match_line" | jq -r '.range.start.column // 0')
      matched_text=$(printf '%s' "$match_line" | jq -r '.text // ""')
      message=$(printf '%s' "$match_line" | jq -r '.message // ""')

      # Defense-in-depth: drop findings from .git/ paths even if one slipped
      # past the input filter above (e.g. absolute paths the caller supplied).
      case "$file" in
        */.git/*) continue ;;
      esac

      finding=$(jq -n \
        --arg rule_id "$rule_id" \
        --arg rule_level "$level" \
        --arg file "$file" \
        --argjson line "$line" \
        --argjson column "$column" \
        --arg matched_text "$matched_text" \
        --arg message "$message" \
        '{rule_id:$rule_id, rule_level:$rule_level, file:$file, line:$line, column:$column, matched_text:$matched_text, message:$message}')
```

New:

```bash
      file=$(printf '%s' "$match_line" | jq -r '.file // ""')
      line=$(printf '%s' "$match_line" | jq -r '.range.start.line // 0')
      column=$(printf '%s' "$match_line" | jq -r '.range.start.column // 0')

      # Defense-in-depth: drop findings from .git/ paths even if one slipped
      # past the input filter above (e.g. absolute paths the caller supplied).
      case "$file" in
        */.git/*) continue ;;
      esac

      # Payloads never travel through argv: write each field to a file and
      # let jq read it with --rawfile. `jq -j` preserves the exact bytes and
      # adds no trailing newline; the helper strips trailing newlines to keep
      # the previous `$(...)` semantics.
      printf '%s' "$match_line" | jq -j '.text // ""' > "$MATCH_TEXT_RAW"
      printf '%s' "$match_line" | jq -j '.message // ""' > "$MATCH_MSG_RAW"
      truncate_utf8_file 8192 "$MATCH_TEXT_RAW" "$MATCH_TEXT_OUT"
      truncate_utf8_file 1024 "$MATCH_MSG_RAW" "$MATCH_MSG_OUT"

      finding=$(jq -n \
        --arg rule_id "$rule_id" \
        --arg rule_level "$level" \
        --arg file "$file" \
        --argjson line "$line" \
        --argjson column "$column" \
        --rawfile matched_text "$MATCH_TEXT_OUT" \
        --rawfile message "$MATCH_MSG_OUT" \
        '{rule_id:$rule_id, rule_level:$rule_level, file:$file, line:$line, column:$column, matched_text:$matched_text, message:$message}')
```

Do not change the jq program's key expression: it must stay `rule_level:$rule_level` (the parameter is `--arg rule_level "$level"`).

### 5. Add `scripts/tests/test-ast-grep-runner-truncation.sh`

Create a fixture test in the style of `scripts/tests/test-changelog-unreleased-fold.sh`. Use `set -uo pipefail` (no `-e`), a `TMP` dir with `trap 'rm -rf "$TMP"' EXIT`, `ok` / `no` helpers, and exit 1 if any case failed. Derive `REPO="$(cd "$(dirname "$0")/../.." && pwd)"`.

The script must cover these cases:

**Case A — AC1 and AC2 (131072-byte match).** Create `$TMP/ac1/pkg/order/big.go` with exactly this shape, computing the payload length in the script:

```go
package order

func load() error {
	return fmt.Errorf("%s", "<payload>")
}
```

Set `payload_len=$((131072 - 18 - 2))` (18 = `fmt.Errorf("%s", "`, 2 = `")`). Run `bash "$REPO/scripts/ast-grep-runner.sh" "$TMP/ac1"`. Assert:
- exit status is 0;
- `.stats.findings_count >= 1`;
- the finding whose `.rule_id == "go-errors/no-fmt-errorf"` has `matched_text` ending with `…[truncated, original 131072 bytes]`;
- the `matched_text` with that suffix removed is at most 8192 bytes (`utf8bytelength`).

**Case B — AC4 (small match byte-identical to pre-fix).** Create `$TMP/ac4/pkg/order/small.go` with `return fmt.Errorf("boom")`. Run the fixed runner from `$REPO` over `$TMP/ac4`. Derive the pre-fix runner at test time:

```bash
mkdir -p "$TMP/prefix/scripts"
git -C "$REPO" show origin/master:scripts/ast-grep-runner.sh > "$TMP/prefix/scripts/ast-grep-runner.sh"
ln -s "$REPO/rules" "$TMP/prefix/rules"
```

If `git -C "$REPO" rev-parse --verify origin/master` fails, report a failure with a clear message; do not skip. Run the pre-fix script over the same fixture. Extract the `go-errors/no-fmt-errorf` finding from both outputs with `jq -cS --arg rid 'go-errors/no-fmt-errorf' '[.findings_by_owner[][] | select(.rule_id==$rid)][0]'` and assert the two strings are equal. Also assert the fixed finding's `matched_text` does not contain `truncated`.

**Case C — AC5 (message over 1024 bytes).** Create a temporary mirror ROOT so a rule can be planted without touching the repo:

```bash
mkdir -p "$TMP/ac5/mirror/scripts/lib" "$TMP/ac5/mirror/rules/test" "$TMP/ac5/src"
cp "$REPO/scripts/ast-grep-runner.sh" "$TMP/ac5/mirror/scripts/"
cp "$REPO/scripts/lib/truncate-utf8.sh" "$TMP/ac5/mirror/scripts/lib/"
cat > "$TMP/ac5/mirror/rules/index.json" <<'JSON'
[{"id":"test/big-message","owner":"test-owner","level":"MUST","enforcement":"`rules/test/big-message.yml`"}]
JSON
cat > "$TMP/ac5/mirror/rules/test/big-message.yml" <<'YAML'
id: test/big-message
language: go
severity: error
message: "offending call: $CALL"
rule:
  all:
    - kind: call_expression
    - pattern: $CALL
YAML
```

Create `$TMP/ac5/src/msg.go` containing `package order`, a `func load()`, and exactly one call `bigCall("<2000 a's>")`. Run `bash "$TMP/ac5/mirror/scripts/ast-grep-runner.sh" "$TMP/ac5/src"`. Assert the `test/big-message` finding:
- `message` contains `…[truncated, original ` and ends with ` bytes]`;
- the `message` prefix before the marker is at most 1024 bytes;
- the marker's `<N>` is greater than 1024;
- `matched_text` does **not** contain `truncated` (proving the message path independently; the call is about 2011 bytes, under the 8192 bound).

**Case D — Failure Modes boundary cases.** Source `"$REPO/scripts/lib/truncate-utf8.sh"` in the test and assert directly:
- a 8192-byte input written to a file yields a 8192-byte output with no marker;
- a 8193-byte input yields an output ending with `…[truncated, original 8193 bytes]` whose prefix is 8192 bytes;
- a two-byte UTF-8 rune (`é`, bytes `0xC3 0xA9`) straddling a cut boundary makes the helper back off to the previous rune; assert the output is valid UTF-8 (e.g. `python3 -c 'open(p, encoding="utf-8").read()'` succeeds) and the marker names the original length;
- a 100000-byte input yields an output no larger than 8192 bytes plus the marker.

**Case E — Failure Modes two matches.** Put two files in one target dir (one big match, one small match) and run the fixed runner once. Assert `.stats.findings_count == 2` and that both findings are present, proving the fixed scratch paths do not interleave.

**Self-containment:** the test file must not contain a literal home-directory path (`~/` or `/Users/` or `/home/`), a planning-doc reference (`specs/`, `prompts/`, `docs/plans/`), a requirement id (`FR-`, `NFR-`, `SC-` followed by a digit), or revision metadata. Build any such fixture text dynamically; for example, do not write `~/` literally.

### 6. Wire the test into `make precommit`

Add this target to `Makefile`:

```make
.PHONY: test-ast-grep-runner-truncation
test-ast-grep-runner-truncation:
	@bash scripts/tests/test-ast-grep-runner-truncation.sh
```

Add `test-ast-grep-runner-truncation` to the `precommit:` prerequisite list. Do not remove or reorder the existing prerequisites.

### 7. Keep shellcheck clean

`shellcheck scripts/ast-grep-runner.sh scripts/lib/truncate-utf8.sh scripts/tests/test-ast-grep-runner-truncation.sh` must exit 0. The `# shellcheck disable=SC1091` directive on the source line is required because plain `shellcheck` (without `-x`) does not follow a sourced file.
</requirements>

<constraints>
- The emitted JSON schema, key names and types do not change: `rule_id`, `rule_level`, `file`, `line`, `column`, `matched_text`, `message`. The consumer `filterFindings` re-marshals a fixed seven-field struct, so the truncation marker must live **inside** the string, never as a new field.
- `matched_text` is bounded to 8192 bytes; `message` to 1024 bytes. The bound is on the cut content; the marker is appended beyond it.
- Cut on a UTF-8 rune boundary; never emit a partial multi-byte sequence.
- A field under its bound is emitted byte-identically to the pre-fix output, with no marker. Trailing newlines must be stripped exactly as the previous `$(...)` extraction did.
- No payload field may be passed as a command-line argument to `jq`. In particular, `--arg matched_text` / `--arg message` must be gone; use `--rawfile`.
- Do not modify the `.git/` changed-file filter, the per-match `.git/` case arm, the `--slurpfile arr` merge block, the final `--slurpfile findings_by_owner_arr` / `--slurpfile errors_arr` assembly, `append_error`, `append_finding`, or the exit-code meanings (`0` ran, `2` ast-grep missing / bad invocation).
- Do not add a configurable cap: 8192 and 1024 are fixed values.
- Do not change `scripts/rule-checks.sh` in this prompt; prompt 2 owns it.
- Do not edit `agents/ast-grep-runner.md` or `CHANGELOG.md` in this prompt; prompt 3 owns them.
- Both scripts must keep working under `set -euo pipefail`.
- No new runtime dependency: the JSON tool and coreutils are already required; `python3` is already invoked by both scripts.
- `.reviewignore` handling is out of scope.
- The new files under `scripts/` must pass the repo's own self-containment script-tier rules (no literal home paths, planning-doc refs, requirement ids, or revision metadata).
- Do NOT commit — dark-factory handles git.
- Existing tests and `make precommit` must still pass.

**Open question surfaced for the auditor:** AC10 asserts `shellcheck scripts/ast-grep-runner.sh scripts/rule-checks.sh` exits 0, but the current tree already exits 1 on a pre-existing SC2015 in `rule-checks.sh` (the `resolved="$(cd ... && cd ... && pwd || true)"` assignment). Prompt 2 silences that one with a justified `# shellcheck disable=SC2015` so AC10 can hold. This prompt's own shellcheck target only covers the runner, the helper and the new test; it adds the required `# shellcheck disable=SC1091` for the sourced helper.
</constraints>

<verification>
Run from the repo root:

```bash
make precommit
shellcheck scripts/ast-grep-runner.sh scripts/lib/truncate-utf8.sh scripts/tests/test-ast-grep-runner-truncation.sh
bash scripts/tests/test-ast-grep-runner-truncation.sh
```

Assert the AC6 runner half (the script-tier half lands in prompt 2):

```bash
test "$(grep -cE -- '--arg(json)? (matched_text|message)' scripts/ast-grep-runner.sh || true)" -eq 0
```

The fixture test itself proves AC1 (131072-byte match bounded and marked), AC2 (exit 0 with findings), AC4 (byte-identical small match derived from `origin/master` at test time), AC5 (interpolated message over 1024 bytes bounded), AC7 (exactly the seven keys) and the Failure Modes rows for exact-bound, split-rune, 100 KiB and two-match inputs.
</verification>
