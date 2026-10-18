---
status: approved
spec: [014-pr-review-coverage-block]
created: "2026-10-18T13:41:49Z"
queued: "2026-10-18T14:11:29Z"
branch: dark-factory/pr-review-coverage-block
---

# Lock the review coverage contract in the acceptance suite

<summary>
- The acceptance suite now fails if the coverage section, its table header, the reviewed-commit line or either verdict form leaves the PR review command
- The check reads the five literals from the Step 5 report contract, never from the suite's own output
- A sentence appended elsewhere in the command cannot satisfy the check, because the region is scoped to Step 5
- A copy of the repo with the section heading removed fails the suite, proving the assertion can fail
- The suite gains one new numbered section; the existing checks are unchanged
</summary>

<objective>
Add a coverage-block assertion to `scripts/acceptance.sh` that hardcodes the five contract literals and scopes them to the Step 5 region of `commands/pr-review.md`, so a later edit that drops the block fails `make check-acceptance`. This is prompt **2 of 3** for spec 014 and the only prompt that writes `scripts/acceptance.sh`.
</objective>

<context>
Read fully before editing:

- `scripts/acceptance.sh` in full (361 lines). Note its structure: `set -uo pipefail`, `cd "$(dirname "$0")/.."`, a preflight requiring `jq` and `ast-grep`, the `ok()` / `fail()` helpers, six numbered sections (`=== 1/6 … ===` through `=== 6/6 … ===`), a scratch area `WORK=$(mktemp -d)` created in section 4 with `trap 'rm -rf "$WORK"' EXIT`, and a summary that exits 1 when any `fail` fired.
- `commands/pr-review.md` — the Step 5 region prompt 1 wrote. Extract it with `sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md` and confirm it contains all five literals below before you start.
- `Makefile` — the `check-acceptance` target runs `bash scripts/acceptance.sh`; `make precommit` includes it.

**Verified repo facts this prompt relies on**

- `scripts/acceptance.sh` has zero pre-existing matches for the self-containment marker pattern, so a whole-file marker scan on this file is safe (unlike `CHANGELOG.md`).
- The six existing section headers are `=== 1/6 … ===` through `=== 6/6 … ===`. The summary is preceded by an `echo ""` and then `echo "=== Summary ==="`.
- The scratch area `$WORK` is created in section 4 and is still present in section 7; the existing EXIT trap removes it.
- `commands/pr-review.md` is prompt 1's single-writer file. It already carries the five literals by the time this prompt runs.
- This container's `.git` is masked — `.dark-factory.log` records `hideGit=true hideGitSource=arg` — so no `git` command can run in verification.
</context>

<requirements>

### 1. Hard dependency guard

Before editing anything, confirm prompt 1 shipped. Extract the Step 5 region and confirm each of the five literals is present:

```bash
sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md > /tmp/step5-contract.txt
for literal in \
  '#### Review Coverage' \
  '| Tier | Status | Findings | Reason |' \
  'Reviewed commit:' \
  'Result: clean' \
  'Result: not clean'; do
  printf '%s: ' "$literal"; grep -cF -- "$literal" /tmp/step5-contract.txt
done
```

Every count must be ≥ 1. If any is 0, STOP and report `Status: failed` with the explicit message that prompt 1 must execute first — the assertion below greps strings prompt 1 writes, and a block authored against a missing string would pass vacuously.

Also take the scope-lock snapshot before editing:

```bash
cp scripts/acceptance.sh /tmp/acceptance-before.md
find commands/pr-review.md commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security CHANGELOG.md -type f -exec sha256sum {} + | sort > /tmp/scope-before.txt
```

### 2. Renumber the existing sections

Change the six existing section headers from `N/6` to `N/7`:

- `=== 1/6 Mode coverage ===` → `=== 1/7 Mode coverage ===`
- `=== 2/6 Per-language routing ===` → `=== 2/7 Per-language routing ===`
- `=== 3/6 Context loading (Step 2.5 globs) ===` → `=== 3/7 Context loading (Step 2.5 globs) ===`
- `=== 4/6 Broken-YAML isolation ===` → `=== 4/7 Broken-YAML isolation ===`
- `=== 5/6 Selector mode contracts ===` → `=== 5/7 Selector mode contracts ===`
- `=== 6/6 Self-containment script tier ===` → `=== 6/7 Self-containment script tier ===`

Do not change any other line in those sections. The header comment at the top of the file is not part of this change; leave it as it is.

### 3. Add the `=== 7/7 Review coverage contract ===` section

Insert the new section after the `=== 6/7 Self-containment script tier ===` block and before the `echo ""` / `echo "=== Summary ==="` tail:

```bash
echo "=== 7/7 Review coverage contract ==="

# The PR review's Step 5 report contract is asserted by LITERAL, never derived
# from this run's own output: a derived expectation would still pass after the
# block was deleted. The region is extracted once so a sentence appended after
# Step 7 cannot satisfy any literal below.
STEP5_CONTRACT="$WORK/step5-report-contract.md"
sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md > "$STEP5_CONTRACT"
for literal in \
  '#### Review Coverage' \
  '| Tier | Status | Findings | Reason |' \
  'Reviewed commit:' \
  'Result: clean' \
  'Result: not clean'; do
  if grep -qF -- "$literal" "$STEP5_CONTRACT"; then
    ok "review coverage: Step 5 carries '$literal'"
  else
    fail "review coverage: Step 5 is missing '$literal'"
  fi
done
```

Use the existing `ok()` / `fail()` helpers and the existing `$WORK` scratch directory. Do not add a new preflight binary, a new trap, or a new helper. Do not change the summary block: it already counts `ACCEPTANCE_PASS` and `ACCEPTANCE_FAIL` and exits 1 when any `fail` fired, so the new section participates automatically.

### 4. Confirm the assertion can fail

In the `<verification>` block, make a scratch copy of the repository (excluding the masked `.git`), remove the `#### Review Coverage` lines from the scratch copy's `commands/pr-review.md`, and run the scratch copy's `make check-acceptance` target. It must exit non-zero, and the failure log must contain the `review coverage: Step 5 is missing` message — proving the failure came from this assertion and not from an unrelated crash.

### 5. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation. Confirm the six headers are `N/7`, the new section is `7/7`, `bash -n scripts/acceptance.sh` parses, `bash scripts/acceptance.sh` exits 0, and the scratch-copy `make check-acceptance` negative exits non-zero. Do not report success if any check failed.
</requirements>

<constraints>
- **Scope:** this prompt writes exactly one file — `scripts/acceptance.sh`. Do NOT modify `commands/pr-review.md` (prompt 1's file), `commands/local-review.md`, `commands/code-review.md`, `rules/*`, `scripts/rule-checks.sh`, `scripts/ast-grep-runner.sh`, `scripts/validate-citations.sh`, `docs/*`, `agents/*`, `scenarios/*`, `CHANGELOG.md`, `README.md`, `llms.txt`, `CLAUDE.md`, `.claude-plugin/*`, `.maintainer.yaml` or `docs/security/**`.
- **The assertion must be able to fail.** The five literals are written-down strings, never computed from the run's own output. Run the scratch-copy negative in `<verification>` — do not assume it.
- **Scoped to Step 5.** The assertion reads the Step 5 region, not the whole file. A whole-file grep would be satisfied by a sentence appended after Step 7 and would not test placement.
- **No new dependency.** The script already preflights `jq` and `ast-grep`; this section needs neither beyond what the script already requires. Do not add a new binary check.
- **Renumber consistently.** Exactly the six existing `N/6` headers become `N/7`; the new section is `7/7`. Do not leave a `6/6` or a `7/6` behind.
- **Marker hygiene on every added line.** `scripts/acceptance.sh` is not an exempt path, so no added line may carry a home-directory path, a requirement id, a planning-directory reference, or revision/sign-off meta. The literal pattern (copied from `scripts/rule-checks.sh`, not retyped from memory):

  ```
  (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
  ```

  Copy this pattern without the fence's leading indentation — a copy that carries the two leading spaces no longer matches a home-directory path. The verification block below also carries the pattern inline.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit=true hideGitSource=arg`), so a bare `git` call fails with `fatal: not a git repository`. The daemon commits on completion. The scratch-copy negative excludes `.git` for exactly that reason.
- **Do not touch `CHANGELOG.md`.** The changelog entry is prompt 3's scope. Do not report the changelog entry as a blocker.
- **Cross-prompt boundary:** prompt 3 re-runs `bash scripts/acceptance.sh` and the scratch-copy negative against the finished tree. If this prompt's section is absent or the script exits non-zero, report `Status: failed` naming the failing literal or the failing check.
</constraints>

<verification>
All commands run from the repo root and are container-executable. This container has **no git** — no check below uses it. The snapshots in requirement 1 must have been taken **before** the edit.

```bash
# --- the dependency guard (prompt 1 shipped) ---
sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md > /tmp/step5-contract.txt
for literal in '#### Review Coverage' '| Tier | Status | Findings | Reason |' 'Reviewed commit:' 'Result: clean' 'Result: not clean'; do
  printf '%s: ' "$literal"; grep -cF -- "$literal" /tmp/step5-contract.txt   # expect: >= 1 each
done

# --- the new section and the renumbered headers ---
grep -c '=== 7/7 Review coverage contract ===' scripts/acceptance.sh          # expect: 1
for n in 1 2 3 4 5 6; do
  printf '%s/7: ' "$n"; grep -c "=== $n/7 " scripts/acceptance.sh             # expect: 1 each
done
if grep -q '/6 ' scripts/acceptance.sh; then echo "FAIL: an old N/6 header remains"; else echo "OK: all headers renumbered"; fi
grep -c 'review coverage:' scripts/acceptance.sh                              # expect: 2 (one ok line + one fail line)
grep -c 'Step 5 is missing' scripts/acceptance.sh                             # expect: 1
bash -n scripts/acceptance.sh && echo "OK: acceptance.sh parses"

# --- the suite passes on the finished tree ---
bash scripts/acceptance.sh > /tmp/acceptance-positive.log 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then echo "OK: acceptance exits 0"; else echo "FAIL: acceptance exits $rc"; cat /tmp/acceptance-positive.log; fi
grep -c 'review coverage: Step 5 carries' /tmp/acceptance-positive.log        # expect: 5

# --- the assertion can fail: scratch copy with the heading removed ---
SCRATCH=$(mktemp -d)
tar cf - --exclude=.git . | ( cd "$SCRATCH" && tar xf - )
test -f "$SCRATCH/commands/pr-review.md" && test -f "$SCRATCH/scripts/acceptance.sh" && echo "OK: scratch copy complete"
sed -i '/^#### Review Coverage$/d' "$SCRATCH/commands/pr-review.md"
make -C "$SCRATCH" check-acceptance > /tmp/acceptance-negative.log 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then echo "OK: acceptance exits $rc with the heading removed"; else echo "FAIL: acceptance passed with the heading removed — the assertion cannot fail"; fi
grep -c 'review coverage: Step 5 is missing' /tmp/acceptance-negative.log     # expect: >= 1 (the failure is this assertion)
rm -rf "$SCRATCH"

# --- marker hygiene on the lines this prompt added (snapshot-based; no git) ---
diff -u /tmp/acceptance-before.md scripts/acceptance.sh > /tmp/acceptance.diff || true
grep '^+' /tmp/acceptance.diff | grep -v '^+++' > /tmp/acceptance-added.txt
wc -l < /tmp/acceptance-added.txt                                             # informational
if grep -qE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/acceptance-added.txt; then
  echo "FAIL: a marker literal was added to scripts/acceptance.sh"
else
  echo "OK: added lines are marker-free"
fi

# --- scope lock: the files this prompt must not touch are unchanged ---
find commands/pr-review.md commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security CHANGELOG.md -type f -exec sha256sum {} + | sort > /tmp/scope-after.txt
if diff -q /tmp/scope-before.txt /tmp/scope-after.txt > /dev/null 2>&1; then
  echo "OK: scope-lock paths unchanged"
else
  echo "FAIL: a scope-lock path changed"
  diff /tmp/scope-before.txt /tmp/scope-after.txt
fi

# --- the real in-container gate (precommit minus the git-dependent changelog-fold target) ---
make check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test   # expect: exit 0
```

`make precommit` adds `check-changelog-fold` on top of the seven targets above. That target shells out to `git rev-parse --git-dir` and dies with `not a git repository` while `.git` is masked here, so it cannot pass inside this container and is deliberately excluded. The seven-target line above is this prompt's authoritative gate; the full `make precommit` belongs to the spec's verification ladder, not here. Do not report this run as failed because of the excluded target, and do not report success on the checks above if any of them exited non-zero.
</verification>

<notes>
<!-- OPEN QUESTION (reviewer): this prompt adds a dedicated section 7/7 and renumbers the six existing headers, rather than adding a sub-block (g) to the selector-mode section. The coverage contract is mode-independent, not selector-specific, so a dedicated section is the honest home; the renumbering is six mechanical line edits. If the reviewer prefers a sub-block to avoid touching the existing headers, that is a one-section change with no effect on the assertion itself. -->
- **Why the literals are hardcoded.** An expectation derived from the run's own output would still pass after the block was deleted, which is the one failure this assertion exists to catch. The five strings are written down in the script, not read back from the command.
- **Why the region is extracted once.** `$WORK` is already the script's scratch area and its EXIT trap removes it. Extracting the Step 5 region to a file avoids both repeated `sed` calls and the `pipefail` + `grep -q` SIGPIPE trap.
- **Why the scratch copy excludes `.git`.** The container's `.git` is a masked device; copying it would fail or produce a broken repository, and the acceptance script does not use git.
</notes>
