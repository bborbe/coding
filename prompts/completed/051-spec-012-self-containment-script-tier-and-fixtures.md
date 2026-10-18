---
status: completed
spec: [012-intent-aware-review-and-self-containment]
execution_id: coding-intent-drift-exec-051-spec-012-self-containment-script-tier-and-fixtures
dark-factory-version: v0.198.7
created: "2026-10-17T20:46:40Z"
queued: "2026-10-17T21:14:48Z"
started: "2026-10-17T21:17:23Z"
completed: "2026-10-17T21:19:35Z"
branch: dark-factory/intent-aware-review-and-self-containment
---

# Self-containment script checks, fixtures, and acceptance gate

<summary>
- Adds four deterministic checks to the shared script-tier runner, one per script-tier self-containment rule
- Each check scans every changed file whole and reports the real file and line of each match
- Six documented paths are exempt from the checks, evaluated per changed file — never as a whole-run switch, which would silently disable the rules on nearly every agent-authored PR
- Adds a dirty fixture that carries every marker and a clean fixture that carries none
- The acceptance suite asserts the dirty fixture yields all four rule ids and the clean fixture yields none, so the gate fails if a check stops firing or starts over-firing
- The runner stays bash 3.2 compatible and shellcheck-clean, and its other checks are untouched
- Depends on the five self-containment rule ids shipped by prompt 1; if they are absent the run fails loudly rather than guessing
</summary>

<objective>
The self-containment script tier is real and regression-locked: `scripts/rule-checks.sh` gains four checks emitting findings with the real `file` and `line`, the six documented exemption paths are applied per changed file inside each scan loop, committed dirty/clean fixtures under `scripts/testdata/self-containment/` exercise both directions, and `scripts/acceptance.sh` gains a block that hardcodes the four rule ids as literals so `make precommit` fails if a check stops firing. This is prompt **2 of 4** for spec 012 and the **only** prompt that writes `scripts/rule-checks.sh`.
</objective>

<context>
Read fully before writing:

- `scripts/rule-checks.sh` — the file to extend. Verified contract:
  - CLI: `scripts/rule-checks.sh <target-dir> [changed-file ...]`. `TARGET_DIR="$1"` then `shift`; it is resolved to an absolute path with `TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"`.
  - **Changed files are absolutised before any check runs**: each argument is prefixed with `$TARGET_DIR/` unless it already starts with `/`. This is why every exemption pattern below is anchored at `$TARGET_DIR` — a repo-relative pattern would match nothing.
  - `emit_finding <owner> <rule_id> <level> <file> <line> <col> <text> <msg>` — 8 positional args; `line` and `col` are passed through `--argjson` so they must be numbers (default `line` to `0` only when there is no match line). It appends a JSON line and increments the global `FINDINGS_COUNT`.
  - `changed_file_matches <pattern>` — returns 0 when *any* changed file matches the glob, or when no changed-file filter was set. Every existing check calls it check-level. **Do not use it for the self-containment checks** (see requirement 2).
  - Existing checks end with an explicit early return (`|| return 0`) and are all invoked, in order, in the "Run all checks" block near the bottom of the file. New checks are appended there.
  - Header comment states: exit code is always 0 (findings live in the JSON); **bash 3.2 compatible (macOS); shellcheck-clean**. `set -euo pipefail` is set.
  - Output envelope: `{stats:{yamls_run, findings_count, elapsed_ms}, findings_by_owner:{<owner>:[{rule_id, rule_level, file, line, column, matched_text, message}, ...]}, errors:[]}`. Note the `owner` key is stripped from each finding and used as the grouping key.
- `scripts/acceptance.sh` — the file to extend. Verified contract: `set -uo pipefail` (no `-e`), `cd "$(dirname "$0")/.."`, a preflight loop requiring `jq` and `ast-grep` on PATH, then helpers `ok "<msg>"` (increments `ACCEPTANCE_PASS`, prints `  ✅ <msg>`) and `fail "<msg>"` (increments `ACCEPTANCE_FAIL`, prints `  ❌ <msg>`). Sections are announced as `echo "=== N/5 <name> ==="`; the file ends with a `=== Summary ===` block that prints PASS/FAIL counts and `exit 1` when `ACCEPTANCE_FAIL > 0`.
- `docs/self-containment-guide.md` — shipped by prompt 1; the rule definitions the checks enforce.
- `rules/index.json` — shipped by prompt 1; must already contain the five `self-containment/` ids.
- `Makefile` — `check-acceptance` runs `@bash scripts/acceptance.sh`; it is one of the eight `precommit` targets.

**The five pinned patterns (verbatim — the single source of truth; do not re-type an approximation)**

```
1. (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]
2. /(Users|home)/[A-Za-z0-9._-]
3. \b(FR|NFR|SC)-[0-9]
4. \b(specs|prompts|docs/plans)/|the plan says|as discussed
5. revised per|as requested in the review|signed off by|v[0-9]+ of this change
```

Patterns 1 and 2 together are the `no-home-dir-paths` check; 3 is `no-requirement-ids`; 4 is `no-planning-doc-refs`; 5 is `no-revision-meta`. These are the exact strings the guide's `**Enforcement**:` lines describe, so rule and enforcement cannot drift. The greps are case-sensitive (no `-i`): the literals are matched as written.

**The six exemption paths (verbatim, anchored at `$TARGET_DIR`)**

```
"$TARGET_DIR"/specs/*
"$TARGET_DIR"/prompts/*
"$TARGET_DIR"/docs/self-containment-guide.md
"$TARGET_DIR"/agents/self-containment-assistant.md
"$TARGET_DIR"/scripts/rule-checks.sh
"$TARGET_DIR"/scripts/testdata/self-containment/*
```

Bare ticket ids (`[A-Z]+-<digits>`) are deliberately NOT a marker: any such pattern collides with legitimate repo content (`ADR-0001`, `BSD-2-Clause`, `GO-2026-*`), so a leaked project ticket id is left to the judgment rule rather than bought with a false-positive surface the script tier cannot adjudicate away. Do not add a generic ticket-id pattern.
</context>

<requirements>

### 0. Precondition — fail loudly if prompt 1 has not shipped

```bash
jq -r '.[].id' rules/index.json | grep -qxF 'self-containment/no-home-dir-paths' \
  || { echo "Status: failed — prompt 1 not yet deployed (self-containment rule ids absent from rules/index.json)"; exit 1; }
jq -r '.[].id' rules/index.json | grep -qxF 'self-containment/no-revision-meta' \
  || { echo "Status: failed — prompt 1 not yet deployed (self-containment rule ids absent from rules/index.json)"; exit 1; }
```

If either check fails, STOP and report `Status: failed` with exactly that message. Never report `needs_input` — a missing rule id is a ship-order bug, not a question for a human.

### 1. Add the exemption helper to `scripts/rule-checks.sh`

Place it next to `changed_file_matches` (after that function's closing brace, before the `repo_visibility` block). It must be a **new** helper — do not modify `changed_file_matches`.

```bash
# ---------------------------------------------------------------------------
# self_containment_exempt <abs-path> — returns 0 when the file is one of the six
# documented self-containment exemption paths (docs/self-containment-guide.md).
# Patterns are anchored at $TARGET_DIR because every changed-file argument was
# absolutised above; a repo-relative pattern (specs/*) matches nothing there and
# the exemption would be silently inert in every real review.
# ---------------------------------------------------------------------------
self_containment_exempt() {
  case "$1" in
    "$TARGET_DIR"/specs/*|"$TARGET_DIR"/prompts/*) return 0 ;;
    "$TARGET_DIR"/docs/self-containment-guide.md) return 0 ;;
    "$TARGET_DIR"/agents/self-containment-assistant.md) return 0 ;;
    "$TARGET_DIR"/scripts/rule-checks.sh) return 0 ;;
    "$TARGET_DIR"/scripts/testdata/self-containment/*) return 0 ;;
  esac
  return 1
}
```

### 2. Add the shared scanner and the four checks

Add the scanner helper and the four check functions immediately before the `# Run all checks` block. The scanner must keep the loop in the **current shell** (`done < <(grep ...)`, never a pipe) so `emit_finding`'s `FINDINGS_COUNT` increment survives.

```bash
# ---------------------------------------------------------------------------
# Self-containment (script tier) — see docs/self-containment-guide.md
#
# Every check scans each changed file WHOLE and evaluates the exemption PER
# FILE inside the loop. Do NOT gate these checks with changed_file_matches():
# that helper returns true when ANY changed file matches, so reusing it here
# would disable the rules for an entire run whenever a spec or prompt appears in
# the diff — silently inert on nearly every agent-authored PR while every
# assertion still passed.
# ---------------------------------------------------------------------------

# self_containment_scan <rule_id> <level> <message> <extended-regex>
# Scans every changed file whole; emits one finding per matching line, carrying
# the real file and line. Skips the exempt paths, vendor/ and node_modules/,
# and binary files.
self_containment_scan() {
  local rule_id="$1" level="$2" message="$3" pattern="$4"
  local f hit lineno
  # Guard BEFORE the array expansion: under `set -u`, bash 3.2 errors on
  # "${CHANGED_FILES[@]}" when the array is empty (the existing checks guard the
  # same way, with ${#CHANGED_FILES[@]}). No changed files means the
  # self-containment checks are diff-scoped and emit nothing.
  [ "${#CHANGED_FILES[@]}" -gt 0 ] || return 0
  for f in "${CHANGED_FILES[@]}"; do
    self_containment_exempt "$f" && continue
    case "$f" in */vendor/*|*/node_modules/*) continue ;; esac
    [ -f "$f" ] || continue
    grep -Iq . "$f" 2>/dev/null || continue   # skip binary files
    while IFS= read -r hit; do
      [ -z "$hit" ] && continue
      lineno="${hit%%:*}"
      emit_finding \
        "self-containment-assistant" \
        "$rule_id" \
        "$level" \
        "$f" \
        "$lineno" 0 \
        "${hit#*:}" \
        "$message"
    done < <(grep -nE "$pattern" "$f" 2>/dev/null || true)
  done
}

check_self_containment_no_home_dir_paths() {
  self_containment_scan \
    "self-containment/no-home-dir-paths" "MUST" \
    "A home-directory path resolves only on the author's machine. Use a repo-relative path. See docs/self-containment-guide.md." \
    '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]'
}

check_self_containment_no_requirement_ids() {
  self_containment_scan \
    "self-containment/no-requirement-ids" "SHOULD" \
    "A requirement identifier resolves only against a planning document. Describe the behaviour in the code instead. See docs/self-containment-guide.md." \
    '\b(FR|NFR|SC)-[0-9]'
}

check_self_containment_no_planning_doc_refs() {
  self_containment_scan \
    "self-containment/no-planning-doc-refs" "SHOULD" \
    "A reference to a planning directory or planning prose will not resolve in the tree. State the rationale in the code. See docs/self-containment-guide.md." \
    '\b(specs|prompts|docs/plans)/|the plan says|as discussed'
}

check_self_containment_no_revision_meta() {
  self_containment_scan \
    "self-containment/no-revision-meta" "SHOULD" \
    "Revision or sign-off provenance describes the authoring process, not the code. See docs/self-containment-guide.md." \
    'revised per|as requested in the review|signed off by|v[0-9]+ of this change'
}
```

Append these four calls to the `# Run all checks` block, after `check_skill_scripts_subdir`:

```bash
check_self_containment_no_home_dir_paths
check_self_containment_no_requirement_ids
check_self_containment_no_planning_doc_refs
check_self_containment_no_revision_meta
```

Scope rules for these checks, all of which follow from the contract above:

- **Diff-scoped**: iterate `CHANGED_FILES` only. A run with no changed-file arguments produces no self-containment findings.
- **Whole file, not hunks**: the runner receives a file list and no base ref, so a pre-existing match on an untouched line is reported; the adjudicator's changed-line filter drops it. Do not try to narrow to hunks.
- **Skip** `vendor/` and `node_modules/` path segments and binary files.
- **Never** call `changed_file_matches` in any of these four checks or in the scanner.

### 3. Add the fixtures

Create `scripts/testdata/self-containment/dirty/leaked-context.txt` with exactly this content (lower-case where the pattern is lower-case — the greps are case-sensitive):

```
notes carried over from planning (Order service)

dump goes to ~/scratch/order-dump.json

implements FR-1 and NFR-3; see specs/order-service/ for the rest

the plan says to keep the retry inline

revised per review: swapped the map for a slice
```

Create `scripts/testdata/self-containment/clean/clean-notes.txt` with exactly this content (it must match none of the five patterns):

```
notes for the Order service

the dump is written next to the binary, never to a developer machine

the retry stays inline because the extracted helper needed the request context
```

Both files are repo-owned constants and are exempt in real reviews via the `scripts/testdata/self-containment/*` pattern.

### 4. Add the acceptance assertion block to `scripts/acceptance.sh`

Renumber the five existing section headers from `=== N/5 ... ===` to `=== N/6 ... ===` (five edits, no other change to those lines). Insert this block immediately before the `echo ""` / `=== Summary ===` block:

```bash
echo "=== 6/6 Self-containment script tier ==="

# The four rule ids are HARDCODED literals, never derived from the run's own
# output: a derived expected set would still pass after a check silently stopped
# firing. This is the gate that makes the fixtures permanent.
SC_DIR="$PWD/scripts/testdata/self-containment"

# shellcheck disable=SC2046  # word-splitting is intentional: one path per arg
sc_dirty_out=$(bash scripts/rule-checks.sh "$SC_DIR/dirty" $(find "$SC_DIR/dirty" -type f) 2>/dev/null || true)
sc_dirty_ids=$(printf '%s' "$sc_dirty_out" | jq -r '[.findings_by_owner["self-containment-assistant"] // [] | .[] | .rule_id] | unique | .[]' 2>/dev/null || true)

for rid in \
  self-containment/no-home-dir-paths \
  self-containment/no-requirement-ids \
  self-containment/no-planning-doc-refs \
  self-containment/no-revision-meta; do
  if printf '%s\n' "$sc_dirty_ids" | grep -qxF "$rid"; then
    ok "self-containment dirty fixture yields $rid"
  else
    fail "self-containment dirty fixture missing a finding for $rid"
  fi
done

# shellcheck disable=SC2046
sc_clean_out=$(bash scripts/rule-checks.sh "$SC_DIR/clean" $(find "$SC_DIR/clean" -type f) 2>/dev/null || true)
sc_clean_count=$(printf '%s' "$sc_clean_out" | jq '(.findings_by_owner["self-containment-assistant"] // []) | length' 2>/dev/null || echo "ERR")
if [ "$sc_clean_count" = "0" ]; then
  ok "self-containment clean fixture yields zero findings"
else
  fail "self-containment clean fixture yielded $sc_clean_count finding(s) (want 0)"
fi
```

Each dirty-fixture assertion carries a non-zero `line` in the finding it matches; the runner emits one finding per matching line, so this is satisfied by construction.

### 5. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation, including the negative proof that the gate can fail. Do not report success if `make precommit` exited non-zero.
</requirements>

<constraints>
- **Single writer:** this is the only prompt that writes `scripts/rule-checks.sh` and `scripts/acceptance.sh`. Do not touch `docs/self-containment-guide.md` (prompt 1's), `agents/self-containment-assistant.md` (prompt 1's), `rules/index.json` (regenerated by prompt 1; do not run `make build-index` here), `commands/*.md` or `docs/selector-mode-guide.md` (prompt 3's), `CHANGELOG.md` (prompt 4's), `docs/security/**`, `scripts/validate-citations.sh`, `agents/security-verifier.md`, `.maintainer.yaml`, `scenarios/**`.
- **Exemption semantics (the load-bearing detail):** the six patterns are anchored at `$TARGET_DIR`, evaluated **per changed file inside each scan loop**, never through `changed_file_matches`. The check-level helper returns true when *any* changed file matches, so using it would disable all four rules for a whole run whenever a spec or prompt is in the diff — i.e. on nearly every agent-authored PR — while every acceptance assertion still passed. A repo-relative pattern (`specs/*`) is equally wrong: changed-file arguments are absolutised before the checks run, so it matches nothing and the exemption is silently inert.
- **Patterns are pinned:** use patterns 1-5 exactly as given above. No `-i`, no added alternatives, no generic ticket-id pattern, no narrowing to diff hunks.
- **bash 3.2 compatible and shellcheck-clean:** `rule-checks.sh` must keep working on bash 3.2 (no `mapfile`, no associative arrays, no `${var,,}`). Guard every `"${CHANGED_FILES[@]}"` expansion with `[ "${#CHANGED_FILES[@]}" -gt 0 ]` first — under `set -u`, bash 3.2 treats an empty-array expansion as an unbound variable, and the existing checks all guard the same way. The `# shellcheck disable=SC2046` comments in the acceptance block are the only suppressions allowed, and only on the two `find`-substitution lines.
- **Generic content only:** the fixtures use Order / User / Product / Customer domains — never trading or project-specific domains, never a real operator path (the dirty fixture uses a scratch file name).
- **Determinism:** the checks are pure grep/`case` over the handed file list — no network, no `gh`, no clock, no ordering dependence.
- **No new scenario file** — spec 012 ships no scenario; the fixtures asserted here are the lock.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit: true`, confirmed in `.dark-factory.log` as `hideGitSource=arg`); git fails with `fatal: not a git repository` and the daemon's `workflow: direct` post-prompt commit stages everything on completion. The fixture file list is built with `find`, never `git ls-files -o` — the fixtures are committed, so the untracked-only form returns an empty list, hands the runner zero files, and can never pass.
- **Cross-prompt boundary:** this prompt depends on prompt 1 having shipped the five rule ids into `rules/index.json`. A missing id is a failure (`Status: failed`), never `needs_input`.
</constraints>

<verification>
All commands are container-executable from the repo root. No `git` — the container's `.git` is masked.

```bash
# 1. The four checks and the helper exist, and the checks are registered
grep -c '^self_containment_exempt() {' scripts/rule-checks.sh          # expect: 1
grep -c '^self_containment_scan() {' scripts/rule-checks.sh            # expect: 1
grep -Ec '^check_self_containment_no_(home_dir_paths|requirement_ids|planning_doc_refs|revision_meta)\(\) \{' scripts/rule-checks.sh   # expect: 4
grep -Ec '^check_self_containment_no_' scripts/rule-checks.sh          # expect: 8 (4 definitions + 4 invocations)

# 2. The exemption is anchored at $TARGET_DIR and evaluated per file — never via changed_file_matches
grep -c '"\$TARGET_DIR"/specs/\*' scripts/rule-checks.sh               # expect: 1
grep -c '"\$TARGET_DIR"/scripts/testdata/self-containment/\*' scripts/rule-checks.sh   # expect: 1
grep -A3 '^self_containment_scan() {' scripts/rule-checks.sh | grep -c 'changed_file_matches'   # expect: 0
grep -A8 '^check_self_containment_no_home_dir_paths() {' scripts/rule-checks.sh | grep -c 'changed_file_matches'   # expect: 0

# 3. AC2 — the script tier fires on the dirty fixture, non-vacuously
bash scripts/rule-checks.sh "$PWD/scripts/testdata/self-containment/dirty" $(find "$PWD/scripts/testdata/self-containment/dirty" -type f) | \
  jq '[.findings_by_owner["self-containment-assistant"][] | .rule_id] | unique'
# expect the four ids: self-containment/no-home-dir-paths, self-containment/no-requirement-ids,
# self-containment/no-planning-doc-refs, self-containment/no-revision-meta
bash scripts/rule-checks.sh "$PWD/scripts/testdata/self-containment/dirty" $(find "$PWD/scripts/testdata/self-containment/dirty" -type f) | \
  jq '[.findings_by_owner["self-containment-assistant"][] | select(.line > 0)] | length'
# expect >= 4 (every finding carries a non-zero line)

# 4. AC3 — the script tier stays silent on the clean fixture
bash scripts/rule-checks.sh "$PWD/scripts/testdata/self-containment/clean" $(find "$PWD/scripts/testdata/self-containment/clean" -type f) | \
  jq '(.findings_by_owner["self-containment-assistant"] // []) | length'
# expect: 0

# 5. AC4 — the acceptance block cites the four ids as hardcoded literals
grep -c 'self-containment' scripts/acceptance.sh                        # expect: >= 1
grep -c 'self-containment/no-home-dir-paths' scripts/acceptance.sh      # expect: 1
grep -c 'self-containment/no-requirement-ids' scripts/acceptance.sh     # expect: 1
grep -c 'self-containment/no-planning-doc-refs' scripts/acceptance.sh   # expect: 1
grep -c 'self-containment/no-revision-meta' scripts/acceptance.sh       # expect: 1
grep -c '=== 6/6 Self-containment script tier ===' scripts/acceptance.sh  # expect: 1
make check-acceptance                                                   # expect: exit 0, and the block prints 5 ✅ lines

# 6. AC4 negative proof — the gate CAN fail. Done in a scratch copy so the repo is untouched.
rm -rf /tmp/sc-negative && mkdir -p /tmp/sc-negative
cp -r scripts rules docs commands agents /tmp/sc-negative/
sed -i 's|^check_self_containment_no_home_dir_paths() {|check_self_containment_no_home_dir_paths() { return 0;|' /tmp/sc-negative/scripts/rule-checks.sh
grep -c 'check_self_containment_no_home_dir_paths() { return 0;' /tmp/sc-negative/scripts/rule-checks.sh   # expect: 1 (neutralised)
sc_neg_rc=0
( cd /tmp/sc-negative && bash scripts/acceptance.sh > /tmp/sc-negative.out 2>&1 ) || sc_neg_rc=$?
echo "neutralised acceptance exit=$sc_neg_rc"                            # expect: non-zero
grep -c 'missing a finding for self-containment/no-home-dir-paths' /tmp/sc-negative.out   # expect: 1

# 7. Regression and scope: the diff-scoped contract holds and the other checks are intact
bash scripts/rule-checks.sh "$PWD" | jq '(.findings_by_owner["self-containment-assistant"] // []) | length'
# expect: 0 — with no changed-file arguments the self-containment checks are diff-scoped and emit nothing
bash scripts/rule-checks.sh "$PWD" CHANGELOG.md | jq '(.findings_by_owner | keys)'
# informational: the pre-existing owners still appear. CHANGELOG.md itself carries pre-existing
# home-directory paths, so a self-containment finding here is the whole-file contract working —
# the adjudicator's changed-line filter is what drops it, not the runner.
grep -Ec '^check_license_file_required$|^check_changelog_preamble_frozen$|^check_skill_scripts_subdir$' scripts/rule-checks.sh   # expect: 3

# 8. bash 3.2 / shellcheck hygiene (informational; shellcheck is not wired into precommit)
grep -c 'mapfile\|declare -A' scripts/rule-checks.sh                     # expect: 0

# 9. Full gate
make precommit   # expect: exit 1 ONLY on check-changelog-fold ("not a git repository"), because .git is masked; every other target must pass
make check-links check-json check-index check-coverage check-acceptance bench-test   # expect: exit 0 — the git-free targets are the real in-container gate
```

Note on `make precommit` in this container: the container's `.git` is masked, and `check-changelog-fold` / `check-rule-tests` shell out to tooling that may need it. If `make precommit` fails **only** on a `check-changelog-fold` / `not a git repository` message, report it in the completion report's `## Improvements` as an environment gap (category: GLOBAL), report `status: partial` with the real exit code, and do not fabricate a green run. `make check-acceptance` (step 5) is the gate this prompt owns and must pass.
</verification>

<notes>
- **The `grep -c` on a `|` pipeline in step 1 (`grep -A3 ... | grep -c`) can print `0` and exit 1.** That is the expected result for an absence assertion; read the printed count, not the exit code. The `! grep -q` form is used elsewhere where the shell's exit status matters.
- **`set -euo pipefail` safety of the loop guards.** `self_containment_exempt "$f" && continue`, `[ -f "$f" ] || continue` and `grep -Iq . "$f" || continue` are all safe under `set -e`: the failing command is a non-final operand of a `&&`/`||` list and is exempt from `set -e`. Do not rewrite them as bare `if` blocks with a `return` — the loop must `continue`, not return, so the remaining files are still scanned.
- **`done < <(grep ...)` and not `grep ... | while ...`.** A pipeline would run the loop in a subshell and `emit_finding`'s `FINDINGS_COUNT` increment would be lost, so `stats.findings_count` would read 0 while findings were emitted. Process substitution keeps the loop in the current shell.
- **`emit_finding`'s `line` argument goes through `--argjson`.** `"${hit%%:*}"` is always a numeric string from `grep -n`, so it is safe; never pass a non-numeric value.
- **Case-sensitive greps.** The pinned patterns are lower-case (`the plan says`, `as discussed`, `revised per`). Do not add `-i` — it would change the pinned pattern's semantics. The dirty fixture is written to match the patterns exactly as pinned.
- **Why the fixture is scanned even though the exemption covers it.** The acceptance block passes the fixture directory itself as `TARGET_DIR`, so the exemption patterns (`"$TARGET_DIR"/specs/*`, `"$TARGET_DIR"/scripts/testdata/self-containment/*`) do not match the fixture's own paths and it is scanned. In a real review of this repo the same files are exempt via `scripts/testdata/self-containment/*`. Exemption and this assertion are only jointly satisfiable in that anchored form.
- **Section renumbering.** `acceptance.sh` announces `=== N/5 ... ===`; adding the sixth block makes the denominator wrong. Renumber the five existing headers to `/6` in the same edit.
- **Open question for the reviewer:** the spec's AC4 evidence for the "gate can fail" direction is `make check-acceptance` exiting non-zero with the `no-home-dir-paths` check body emptied. The scratch copy in verification step 6 reproduces that faithfully inside the container (the repo itself is never mutated). The spec's phrasing "in a scratch copy of the repo" is satisfied by copying the five directories `acceptance.sh` reads.
</notes>
