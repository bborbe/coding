---
status: approved
spec: [014-pr-review-coverage-block]
created: "2026-10-18T13:41:49Z"
queued: "2026-10-18T14:11:29Z"
branch: dark-factory/pr-review-coverage-block
---

# Record the review coverage block in the changelog and run the final gates

<summary>
- The changelog carries an unreleased feature entry for the coverage block, or keeps the existing one without duplicating it
- No version is bumped; the release tooling cuts the tag separately
- Every container-executable acceptance check is re-run against the finished tree in one pass
- The two sibling review commands are confirmed untouched and the rule base is confirmed unchanged
- The added changelog lines are swept for leaked planning context
- The change is confirmed to touch no sibling review command, no rule and no version string
</summary>

<objective>
Ensure the `## Unreleased` `feat:` entry exists exactly once and accurately describes the shipped review-coverage block, then re-run every container-executable acceptance check for this change in one pass. This is prompt **3 of 3** for spec 014 — the release tail.
</objective>

<context>
Read fully before editing:

- `CHANGELOG.md` — the top of the file: `# Changelog`, a prose preamble, a three-bullet semver list, then `## Unreleased` at line 11 with one `- feat:` bullet at line 13 describing the coverage block, then `## v0.60.0` at line 15.
- `docs/changelog-guide.md` — the entry format `- <prefix>: <what> [context]`, the prefix table (`feat:` for a new feature), one bullet per logical change, be specific (name the commands and the shipped behaviour), and the rule that `## Unreleased` sits directly above the highest `## vX.Y.Z` and that a merge conflict in it keeps both bullet lists.
- `scripts/check-changelog-fold.sh` — the `--- the stranded-Unreleased signature ---` and `--- the stall signature ---` blocks. Only one `## Unreleased` heading may exist and it must be the **topmost** section. The script calls `git rev-parse --git-dir` and cannot run in this container.
- `commands/pr-review.md` — prompt 1's Step 5 coverage contract. This prompt re-verifies it and edits none of it.
- `scripts/acceptance.sh` — prompt 2's `=== 7/7 Review coverage contract ===` section. This prompt re-verifies it and edits none of it.
- `Makefile` — `precommit` depends on `check-links check-changelog-fold check-json check-index check-coverage check-acceptance check-rule-tests bench-test`.
- `docs/dod.md` — the repo's Definition of Done (the daemon's `validationPrompt`); its "CHANGELOG.md has an entry under `## Unreleased`" and "4-version alignment NOT touched" lines are the repo-wide form of requirements 2 and 3.

**Verified repo facts this prompt relies on**

- `grep -c '^## Unreleased' CHANGELOG.md` returns 1 today, and the heading is the topmost section. The bullet at line 13 already describes the coverage block. **Do not add a second entry.**
- `CHANGELOG.md` already contains eight historical lines matching the marker pattern (lines 28, 32, 343, 348, 543, 547, 719 and 771 — home-directory paths and version-pin prose). A whole-file marker grep over `CHANGELOG.md` therefore false-fails; the sweep below is scoped to the **added** lines via a before/after snapshot.
- `commands/pr-review.md` and `scripts/acceptance.sh` have **zero** pre-existing marker matches, so a whole-file marker scan on those two files is safe.
- The container has no git: `.dark-factory.log` records `hideGit=true hideGitSource=arg`, and `scripts/check-changelog-fold.sh` dies at `git rev-parse --git-dir`. The `git diff` scope lock in the spec and `make precommit` are therefore operator-rung checks, not container checks.
- The four version strings (the changelog's newest versioned heading, `.claude-plugin/plugin.json`, and both version fields in `.claude-plugin/marketplace.json`) stay as they are. This change ships only the `## Unreleased` entry.
</context>

<requirements>

### 1. Snapshot before editing

Take both baselines first:

```bash
cp CHANGELOG.md /tmp/changelog-before.md
find commands/pr-review.md commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security -type f -exec sha256sum {} + | sort > /tmp/scope-before.txt
```

`/tmp` does not persist across prompts, so both comparisons must happen inside this run.

### 2. Ensure exactly one topmost `## Unreleased` `feat:` entry

The section exists and the bullet is accurate as written. **Leave both unchanged.** Do not add a second heading and do not add a second bullet for the same change.

If the section is missing, insert it immediately above the first `## vX.Y.Z` heading:

```
## Unreleased

- feat: <one bullet>
```

If the section exists but the bullet is missing or does not describe the shipped behaviour, add or reword exactly one `- feat:` bullet. It must follow `docs/changelog-guide.md`: the `feat:` prefix, one bullet for the whole logical change, specific rather than vague, and no bash comment copied from a verification block. It must convey: `/coding:pr-review` reports end with a `#### Review Coverage` block that states per tier (deterministic, judgment, security) whether it ran, failed or was skipped, the finding count and reason, the full 40-character reviewed commit SHA, and a `Result:` line that reads not-clean when a required tier could not complete. A worked shape (adapt the wording; keep the sense and the prefix):

```
- feat: `/coding:pr-review` reports end with a `#### Review Coverage` block — per-tier (deterministic / judgment / security) ran / failed / skipped status, finding count and reason, the full 40-character reviewed commit SHA, and a `Result:` line that reads not-clean when a required tier could not complete
```

The topmost-heading rule is load-bearing: a second `## Unreleased` below a released section is reported as stranded by the fold guard, and an absent topmost section with unreleased work is reported as a stalled releaser.

### 3. Leave the version strings and release config alone

Do NOT touch the four version strings (the changelog's newest versioned heading, `.claude-plugin/plugin.json`, and both version fields in `.claude-plugin/marketplace.json`), `.maintainer.yaml`, or `.dark-factory.yaml`. The release is cut separately by the maintainer tooling; this change ships only the `## Unreleased` entry.

### 4. Run the final cross-cutting gates

Walk the whole change once, against the finished tree, and confirm every check in the `<verification>` block:

- the AC1–AC5 literal checks against the Step 5 region of `commands/pr-review.md`;
- `bash scripts/acceptance.sh` exits 0 and its coverage section prints five `review coverage: Step 5 carries` lines (the `ok()` helper prints `  ✅ <msg>`, not `PASS`);
- the scratch-copy negative: removing `#### Review Coverage` from a scratch copy of `commands/pr-review.md` makes the scratch copy's `make check-acceptance` exit non-zero with the `review coverage: Step 5 is missing` message;
- the AC7 negative: neither `commands/local-review.md` nor `commands/code-review.md` carries `#### Review Coverage`, and neither does any scope-lock path (`rules/`, `scripts/rule-checks.sh`, `scripts/ast-grep-runner.sh`, `scripts/validate-citations.sh`, `.maintainer.yaml`, `docs/security/`);
- the AC8 checks: the `## Unreleased` section contains at least one `- feat:` bullet, the added changelog lines carry no marker literal, the two prompt-1/2 files carry no marker literal, and the seven container-executable make targets pass.

The empty `git diff origin/master...HEAD` scope lock and the full `make precommit` (which includes the git-dependent `check-changelog-fold` target) are **operator-rung checks** in this repository: the container's `.git` is masked. Do not attempt either here, and do not report the run as failed because they cannot run. Record the seven-target result instead.

### 5. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation. Walk requirements 1–4 against the actual files. Do not report success if any check failed.
</requirements>

<constraints>
- **Scope:** this prompt writes exactly one file — `CHANGELOG.md` — and only when the existing entry is missing or inaccurate. Do NOT modify `commands/*.md`, `docs/*`, `agents/*`, `scripts/*`, `rules/*`, `scenarios/*`, `README.md`, `llms.txt`, `CLAUDE.md`, `.claude-plugin/*`, `.maintainer.yaml` or `.dark-factory.yaml`.
- **Only one `## Unreleased` heading, and it is the topmost section.** A second one, or one placed below a released heading, is reported as stranded by the fold guard. The existing heading already satisfies this; do not duplicate it.
- **No version bump.** The four version strings stay as they are; alignment is enforced at release time, not here.
- **Marker hygiene on the added changelog lines.** `CHANGELOG.md` is not an exempt path, so any added line may carry no home-directory path, no requirement id, no planning-directory reference, and no revision/sign-off meta. The literal pattern (copied from `scripts/rule-checks.sh`, not retyped from memory):

  ```
  (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
  ```

  Copy this pattern without the fence's leading indentation — a copy that carries the two leading spaces no longer matches a home-directory path. The verification block below also carries the pattern inline.

  Do not sweep the whole changelog: eight pre-existing historical lines match the pattern and are not part of this change. Use the before/after snapshot.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit=true hideGitSource=arg`), so a bare `git` call fails with `fatal: not a git repository`. The daemon commits on completion. The added-lines sweep below is snapshot-based for exactly that reason.
- **Operator-only verification stays on the spec's Verification ladder.** The empty-diff scope lock (`git diff --stat origin/master...HEAD -- …`), the full `make precommit`, the released-plugin fixture runs (AC9–AC11), the per-tier count and skip-reason runs (AC14, AC15), the bot-parser read (AC12) and the bench recall comparison (AC13) all run on the host after the PR merge. Do not attempt any of them in this container.
- **Cross-prompt boundary:** prompts 1 and 2 are single-writer files. If a final gate fails because of `commands/pr-review.md` or `scripts/acceptance.sh`, report `Status: failed` naming the file and the failing check rather than reaching back into a prompt's file.
</constraints>

<verification>
All commands run from the repo root and are container-executable. This container has **no git** — no check below uses it. The snapshots in requirement 1 must have been taken **before** the edit.

```bash
# --- AC8: the changelog entry ---
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'      # expect: >= 1
grep -nE '^## ' CHANGELOG.md | head -1                                                # expect: the `## Unreleased` line
grep -c '^## Unreleased' CHANGELOG.md                                                 # expect: 1

# --- AC8: the added changelog lines carry no marker literal (snapshot-based; no git) ---
test -s /tmp/changelog-before.md || echo "FAIL: /tmp/changelog-before.md is missing — requirement 1's baseline was not taken"
diff -u /tmp/changelog-before.md CHANGELOG.md > /tmp/changelog.diff || true
grep '^+' /tmp/changelog.diff | grep -v '^+++' > /tmp/changelog-added.txt
wc -l < /tmp/changelog-added.txt                                                      # informational: 0 when the entry was already present
if grep -qE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/changelog-added.txt; then
  echo "FAIL: a marker literal was added to CHANGELOG.md"
else
  echo "OK: added changelog lines are marker-free"
fi

# --- AC8: the two prompt-1/2 files carry no marker literal (whole-file scan is safe: zero pre-existing matches) ---
if grep -nE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' commands/pr-review.md scripts/acceptance.sh; then
  echo "FAIL: a marker literal is present in commands/pr-review.md or scripts/acceptance.sh"
else
  echo "OK: commands/pr-review.md and scripts/acceptance.sh are marker-free"
fi

# --- AC1-AC5: re-run the literal checks against the Step 5 region ---
sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md > /tmp/step5.txt
grep -cF '#### Review Coverage' /tmp/step5.txt                                       # expect: >= 1
grep -cF '| Tier | Status | Findings | Reason |' /tmp/step5.txt                       # expect: >= 1
grep -cE '^\| deterministic \| (ran|failed|skipped) \|' /tmp/step5.txt                # expect: >= 1
grep -cE '^\| judgment \| (ran|failed|skipped) \|' /tmp/step5.txt                     # expect: >= 1
grep -cE '^\| security \| (ran|failed|skipped) \|' /tmp/step5.txt                     # expect: >= 1
grep -cF 'Reviewed commit:' /tmp/step5.txt                                           # expect: >= 1
grep -cF 'Result: clean' /tmp/step5.txt                                              # expect: >= 1
grep -cF 'Result: not clean' /tmp/step5.txt                                          # expect: >= 1
grep -cF 'Emit this section as the last section of the report.' /tmp/step5.txt        # expect: >= 1
grep -cF 'in every mode (short, selector and full) and with or without --security.' /tmp/step5.txt   # expect: >= 1
grep -cF "ran means the tier's procedure completed." /tmp/step5.txt                   # expect: >= 1
grep -cF "failed means the tier was required and could not complete." /tmp/step5.txt  # expect: >= 1
grep -cF 'skipped means the invocation did not require the tier.' /tmp/step5.txt      # expect: >= 1
grep -cF 'The selector short-circuit is ran with 0, not failed.' /tmp/step5.txt       # expect: >= 1
grep -cF 'Result: clean if and only if no tier is failed.' /tmp/step5.txt             # expect: >= 1
grep -cF 'Result: not clean when any tier is failed, naming each failed tier and its reason on the same line.' /tmp/step5.txt   # expect: >= 1
grep -cF 'cd <REVIEW_DIR> && git rev-parse HEAD' /tmp/step5.txt                       # expect: >= 1
grep -cF 'full 40-character lowercase hex' /tmp/step5.txt                             # expect: >= 1
grep -cF 'an unreadable SHA produces Result: not clean.' /tmp/step5.txt               # expect: >= 1

# --- AC6: the acceptance lock passes, and still fails when the heading is removed ---
bash scripts/acceptance.sh > /tmp/acceptance-positive.log 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then echo "OK: acceptance exits 0"; else echo "FAIL: acceptance exits $rc"; cat /tmp/acceptance-positive.log; fi
grep -c 'review coverage: Step 5 carries' /tmp/acceptance-positive.log                # expect: 5

SCRATCH=$(mktemp -d)
tar cf - --exclude=.git . | ( cd "$SCRATCH" && tar xf - )
sed -i '/^#### Review Coverage$/d' "$SCRATCH/commands/pr-review.md"
make -C "$SCRATCH" check-acceptance > /tmp/acceptance-negative.log 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then echo "OK: acceptance exits $rc with the heading removed"; else echo "FAIL: acceptance passed with the heading removed — the assertion cannot fail"; fi
grep -c 'review coverage: Step 5 is missing' /tmp/acceptance-negative.log             # expect: >= 1
rm -rf "$SCRATCH"

# --- AC7: the scope lock (the grep portion is container-executable; the git diff is operator-rung) ---
if grep -q '#### Review Coverage' commands/local-review.md; then echo "FAIL: local-review.md carries the block"; else echo "OK: local-review.md untouched"; fi
if grep -q '#### Review Coverage' commands/code-review.md; then echo "FAIL: code-review.md carries the block"; else echo "OK: code-review.md untouched"; fi
if grep -rq '#### Review Coverage' rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security; then
  echo "FAIL: the block leaked into a scope-lock path"
else
  echo "OK: no scope-lock path carries the block"
fi

# --- scope lock: the paths this prompt must not touch are unchanged ---
find commands/pr-review.md commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security -type f -exec sha256sum {} + | sort > /tmp/scope-after.txt
if diff -q /tmp/scope-before.txt /tmp/scope-after.txt > /dev/null 2>&1; then
  echo "OK: scope-lock paths unchanged"
else
  echo "FAIL: a scope-lock path changed"
  diff /tmp/scope-before.txt /tmp/scope-after.txt
fi

# --- AC8: the real in-container gate (precommit minus the git-dependent changelog-fold target) ---
make check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test   # expect: exit 0
```

`make precommit` adds `check-changelog-fold` on top of the seven targets above. That target shells out to `git rev-parse --git-dir` and dies with `not a git repository` while `.git` is masked here, so it cannot pass inside this container and is deliberately excluded. The spec's AC8 `make precommit` clause and AC7's `git diff --stat origin/master...HEAD` clause are therefore satisfied on the operator rung only. Do not report this run as failed because of either, and do not report success on the checks above if any of them exited non-zero.
</verification>

<notes>
<!-- OPEN QUESTION (reviewer): the spec's Verification section lists `make precommit` and AC7's `git diff origin/master...HEAD` as container-executable, but this repository's `.dark-factory.log` records `hideGit=true` and `scripts/check-changelog-fold.sh` calls `git rev-parse --git-dir`. Both checks therefore cannot run in the prompt container. This prompt runs the seven git-free targets and the grep-based scope lock, and leaves the full precommit and the empty-diff proof to the host operator rung. If the spec should say so explicitly, its Verification ladder is the place to correct it. -->
- **The changelog entry is pre-seeded.** Commit `a40d696` added the `## Unreleased` `feat:` bullet at `CHANGELOG.md` line 13 before this prompt was generated, so this prompt verifies and preserves it rather than authoring it. Requirement 2's insert/reword fallback fires only if a later edit removes the section or the bullet. The container therefore has no required file change; this prompt's work is the final gate pass.
- **Why the changelog sweep is snapshot-based.** Eight historical lines in `CHANGELOG.md` match the marker pattern. A whole-file grep would report them as this change's additions; a `git diff` cannot run with `.git` masked. The `cp` before the edit plus `diff -u` reproduces "added lines" without git.
- **Why the topmost-heading rule matters.** Only one `## Unreleased` heading may exist and it must sit above the first released section — a heading anywhere else is stranded residue that the fold guard fails on, and the guard also treats "unreleased work with no topmost `## Unreleased` section" as a stalled releaser. The existing topmost heading satisfies both signatures; do not duplicate it.
- **Why AC7's grep portion is still run here.** The full scope lock is a git diff, but the two sibling-command zero-counts and a `Review Coverage` scan over the other scope-lock paths are container-executable and catch the concrete out-of-scope-copy failure mode the spec names.
</notes>
