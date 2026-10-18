---
status: approved
spec: [013-fresh-context-local-review-adjudication]
created: "2026-10-18T10:31:14Z"
queued: "2026-10-18T10:59:39Z"
branch: dark-factory/fresh-context-local-review-adjudication
---

# Record the change in the changelog and run the final cross-cutting gates

<summary>
- The project's changelog gains an unreleased section describing the change, so the release tooling has something to cut
- The entry says what a reader needs to know: the local review now adjudicates in one cold-context subagent, a clean diff still costs nothing, and a failed dispatch is reported as a blocking toolchain failure rather than a clean review
- No version number is bumped — the release is cut separately by the maintainer tooling
- Every acceptance check from the earlier prompts is re-run against the finished tree in one place, so a late edit that broke one of them surfaces here
- The lines added to the changelog are swept for leaked planning context, because the changelog is not one of the paths exempt from that rule
- The two other review commands are confirmed untouched, and the shared guide is confirmed to carry the new variant
</summary>

<objective>
Add the `## Unreleased` `feat:` entry for the fresh-context adjudication change to `CHANGELOG.md`, then re-run every container-executable acceptance check for this change in one pass so the finished tree is verified as a whole. This is prompt **4 of 4** for spec 013 — the release tail.
</objective>

<context>
Read fully before editing:

- `CHANGELOG.md` — the top of the file: `# Changelog`, a prose preamble, a three-bullet semver list, then the newest released section `## v0.59.0`. There is currently **no** `## Unreleased` section, so this prompt creates one.
- `docs/changelog-guide.md` — the entry format `- <prefix>: <what> [context]`, the prefix table (`feat:` for a new feature), one bullet per logical change, be specific (name the types, commands and packages), and the rule that an existing `## Unreleased` section is appended to rather than replaced.
- `scripts/check-changelog-fold.sh` — read its `--- the stranded-Unreleased signature ---` and `--- the stall signature ---` blocks. Only one `## Unreleased` heading may exist and it must be the **topmost** section; a heading below the first released section is reported as stranded residue and fails the check, and unreleased work with no topmost `## Unreleased` section is reported as a stalled releaser. Inserting the section directly above `## v0.59.0` satisfies both signatures.
- `README.md` and `llms.txt` — the registration and description lines prompt 1 wrote, which this prompt re-verifies.
- `commands/local-review.md`, `docs/selector-mode-guide.md`, `agents/selector-adjudicator.md`, `scripts/acceptance.sh`, `scenarios/011-fresh-context-adjudication-dispatch.md` — the artifacts prompts 1–3 produced; this prompt re-verifies them and edits none of them.

**Verified repo facts this prompt relies on**

- `grep -c '^## Unreleased' CHANGELOG.md` returns 0 today; the newest released heading is `## v0.59.0`.
- `grep -c 'zero LLM spawns' README.md` returns 1 today (the `/coding:local-review` paragraph in `## Quick Start`); prompt 1 removes it, and this prompt asserts it is gone.
- `CHANGELOG.md` already contains eight lines matching the marker pattern (historical entries mentioning a home-directory path or a released version pin). A whole-file grep over `CHANGELOG.md` therefore false-fails — the sweep below is scoped to the **added** lines via a before/after snapshot, because the container's `.git` is masked and cannot compute a diff.
- The container has no git: `.dark-factory.log` records `hideGit=true hideGitSource=arg`.
</context>

<requirements>

### 1. Snapshot the changelog before editing

Take the baseline **first**, so the added-lines sweep in `<verification>` has something to compare against:

```bash
cp CHANGELOG.md /tmp/changelog-before.md
```

This is the git-free equivalent of reading the file at the target branch. `/tmp` does not persist across prompts, so the comparison must happen inside this run.

### 2. Add the `## Unreleased` section

Insert, immediately above the `## v0.59.0` heading and below the semver preamble:

```
## Unreleased

- feat: <one bullet>
```

The bullet must follow `docs/changelog-guide.md`: the `feat:` prefix, specific rather than vague, one bullet for the whole logical change, and no bash comment copied from a verification block. It must convey the shipped behaviour a reader needs: `/coding:local-review` selector mode now adjudicates in exactly one fresh-context `coding:selector-adjudicator` subagent whose whole input is the diff, the classified rule set, the mechanical findings and the repo path; the clean path still dispatches nothing; a failed or empty dispatch is reported as a Must Fix toolchain failure rather than a clean report; and `/coding:pr-review` and `/coding:code-review` keep in-session adjudication. A worked shape (adapt the wording; keep the sense and the prefix):

```
- feat: `/coding:local-review` selector mode adjudicates in exactly one fresh-context `coding:selector-adjudicator` subagent that receives only the diff, the classified rule set, the mechanical findings and the repo path — the clean path still dispatches nothing, a failed or empty dispatch reports a Must Fix toolchain failure instead of a clean report, and `/coding:pr-review` and `/coding:code-review` keep in-session adjudication
```

### 3. Leave the version strings alone

Do NOT touch the four version strings (the changelog's newest versioned heading, `.claude-plugin/plugin.json`, and both version fields in `.claude-plugin/marketplace.json`) and do NOT touch `.maintainer.yaml`. The release is cut separately by the maintainer tooling; this change ships only the `## Unreleased` entry.

### 4. Run the final cross-cutting gates

Walk the whole change once, against the finished tree:

- every acceptance check in the `<verification>` block below, including the added-lines marker sweep on `CHANGELOG.md` and the re-run of the checks from prompts 1–3;
- the seven git-free `make` targets;
- a read of the finished `commands/local-review.md` selector-mode section and the guide's fresh-context subsection, confirming the dispatch is named, the four inputs are named, the short-circuit precedes the dispatch, and the failure path reads not-clean.

If any check fails, fix the file it belongs to only when that file is `CHANGELOG.md`; for anything else, report `Status: failed` naming the file and the failing check rather than reaching back into a prompt's single-writer file.

### 5. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation. Do not report success if any check failed.
</requirements>

<constraints>
- **Scope:** this prompt writes exactly one file — `CHANGELOG.md`. Do NOT modify `commands/*.md`, `docs/*`, `agents/*`, `scripts/*`, `rules/*`, `scenarios/*`, `README.md`, `llms.txt`, `CLAUDE.md`, `.claude-plugin/*`, or `.maintainer.yaml`.
- **Only one `## Unreleased` heading, and it is the topmost section.** A second one, or one placed below a released heading, is reported as stranded by the fold guard.
- **No version bump.** The four version strings stay as they are; alignment is enforced at release time, not here.
- **Marker hygiene on the added changelog lines.** `CHANGELOG.md` is not an exempt path, so the new heading and bullet may carry no home-directory path, no requirement id, no planning-directory reference, and no revision/sign-off meta. The literal pattern (copied from `scripts/rule-checks.sh`, not retyped from memory):

  ```
  (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
  ```

  Copy this pattern without the fence's leading indentation — a copy that carries the two leading spaces no longer matches a home-directory path. The verification block below also carries the pattern inline.

  Do not name a planning directory in the bullet, and do not describe the change with a version pin such as "vN of this change". Do not sweep the whole file — eight pre-existing historical lines match the pattern and are not part of this change.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit=true hideGitSource=arg`), so a bare `git` call fails with `fatal: not a git repository`. The daemon commits on completion. The added-lines sweep below is snapshot-based for exactly that reason.
- **Operator-only verification is out of scope here** and stays on the spec's Verification ladder: the empty-diff scope lock over the two sibling commands and the shared rule base, the full-diff marker sweep, the fresh-context verdict walk, the spawn-count walk, and the benchmark recall comparison. Do not attempt any of them in this container.
</constraints>

<verification>
All commands run from the repo root and are container-executable. This container has **no git** — no check below uses it. The `cp` in requirement 1 must have run **before** the changelog edit.

```bash
# --- AC12: the changelog entry ---
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'      # expect: >= 1
grep -nE '^## ' CHANGELOG.md | head -1                                                # expect: the `## Unreleased` line
grep -c '^## Unreleased' CHANGELOG.md                                                 # expect: 1

# --- AC12: the added changelog lines carry no marker literal (snapshot-based; no git) ---
diff -u /tmp/changelog-before.md CHANGELOG.md > /tmp/changelog.diff || true
grep '^+' /tmp/changelog.diff | grep -v '^+++' > /tmp/changelog-added.txt
wc -l < /tmp/changelog-added.txt                                                      # informational: 2-4 (the heading, a blank line, the bullet)
if grep -qE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/changelog-added.txt; then
  echo "FAIL: a marker literal was added to CHANGELOG.md"
else
  echo "OK: added changelog lines are marker-free"
fi

# --- AC12: registration, and the README no longer promises zero spawns for the local review ---
grep -c 'selector-adjudicator' README.md                                              # expect: >= 1
grep -c 'selector-adjudicator' llms.txt                                               # expect: >= 1
if grep -q 'zero LLM spawns' README.md; then echo "FAIL: README still claims zero LLM spawns"; else echo "OK: README zero-LLM-spawns claim removed"; fi
grep -c 'fresh-context adjudicator dispatch' README.md                       # expect: >= 1 (prompt 1's replacement phrase)

# --- re-run of the earlier prompts' checks against the finished tree ---
# AC1 — the agent is read-only and correctly named
test -f agents/selector-adjudicator.md && echo "OK: agent exists"
grep -cE '^name: selector-adjudicator$' agents/selector-adjudicator.md                # expect: 1
grep -cE '^tools: Read, Grep, Glob$' agents/selector-adjudicator.md                  # expect: 1
if grep -qE '^tools: .*(Write|Edit|Bash)' agents/selector-adjudicator.md; then echo "FAIL: write/shell tool granted"; else echo "OK: no write/shell tool"; fi
# AC2 — the command names the dispatch and its four inputs
grep -c 'coding:selector-adjudicator' commands/local-review.md                        # expect: >= 1
for label in DIFF CLASSIFIED_RULES MECHANICAL_FINDINGS REPO_PATH; do printf '%s: ' "$label"; grep -c "$label" commands/local-review.md; done
grep -n 'exactly one' commands/local-review.md | grep -c 'coding:selector-adjudicator'   # expect: >= 1
# AC3 — no zero-spawn claim survives for selector mode in the command
if grep -q 'zero sub-agent spawns' commands/local-review.md; then echo "FAIL: zero-spawn claim still present"; else echo "OK: no zero-spawn claim in local-review.md"; fi
grep -c 'zero sub-agent spawns' commands/pr-review.md                                 # expect: 3 (sibling untouched)
# AC4 — the guide documents the variant and keeps every literal the acceptance suite asserts
grep -c 'selector-adjudicator' docs/selector-mode-guide.md                            # expect: >= 1
grep -c 'fresh-context' docs/selector-mode-guide.md                                   # expect: >= 1
grep -c 'Step 4c-sel' docs/selector-mode-guide.md                                     # expect: >= 1
grep -c 'Step 4d-sel' docs/selector-mode-guide.md                                     # expect: >= 1
grep -c 'CLASSIFY' docs/selector-mode-guide.md                                        # expect: >= 1
grep -c 'ADJUDICATE' docs/selector-mode-guide.md                                      # expect: >= 1
grep -cF 'When uncertain, include.' docs/selector-mode-guide.md                       # expect: >= 1
# AC5 — the failure path is fail-closed and lands in Must Fix
grep -n 'Must Fix toolchain failure' commands/local-review.md | grep -c 'coding:selector-adjudicator'   # expect: >= 1
grep -c 'not-clean' docs/selector-mode-guide.md                                       # expect: >= 1
# AC6 — the clean short-circuit, ahead of the dispatch
grep -cF 'selector clean — no adjudication needed' commands/local-review.md           # expect: >= 1
grep -cF 'selector clean — no adjudication needed' docs/selector-mode-guide.md        # expect: >= 1
grep -c 'before the dispatch' docs/selector-mode-guide.md                             # expect: >= 1
# AC8 + AC13 — the wiring lock and the committed scenario
grep -c 'agents/selector-adjudicator.md' scripts/acceptance.sh                        # expect: >= 1
test -f scenarios/011-fresh-context-adjudication-dispatch.md && echo "OK: scenario exists"
grep -c '^status: active$' scenarios/011-fresh-context-adjudication-dispatch.md       # expect: 1
grep -c 'selector-adjudicator' scenarios/011-fresh-context-adjudication-dispatch.md   # expect: >= 1
# scope lock — the sibling commands are untouched
if grep -q 'selector-adjudicator' commands/pr-review.md; then echo "FAIL: pr-review was edited"; else echo "OK: pr-review untouched"; fi
if grep -q 'selector-adjudicator' commands/code-review.md; then echo "FAIL: code-review was edited"; else echo "OK: code-review untouched"; fi

# --- AC12 / the real in-container gate (precommit minus the git-dependent changelog-fold target) ---
make check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test   # expect: exit 0
```

`make precommit` adds `check-changelog-fold` on top of the seven targets above. That target shells out to `git rev-parse --git-dir` and dies with `not a git repository` while `.git` is masked here, so it cannot pass inside this container and is deliberately excluded — the spec's "container-executable `make precommit`" line and AC12's `make precommit` clause are therefore satisfied only on the operator rung (rung 2/3), not here. Do not report this run as failed because of it, and do not report success on the checks above if any of them exited non-zero.
</verification>

<notes>
- **What this prompt deliberately does not verify.** The spec's operator rung owns the checks that need a released plugin or a real repository history: the empty-diff scope lock over `commands/pr-review.md`, `rules/index.json`, `scripts/rule-checks.sh`, `scripts/ast-grep-runner.sh`, `scripts/validate-citations.sh`, `.maintainer.yaml` and `docs/security`; the full-diff marker sweep over every added line; the fresh-context verdict walk and its spawn counts; and the post-change benchmark recall figure. None of them can run here — the container has no git, no released plugin and no benchmark — so they are not restated as container checks.
- **Why the sweep is snapshot-based.** `CHANGELOG.md` already carries eight historical lines matching the marker pattern. A whole-file grep would report them as this change's additions; a `git diff` cannot run with `.git` masked. The `cp` before the edit plus `diff -u` reproduces "added lines" without git.
- **Why the fold guard's two signatures matter.** Only one `## Unreleased` heading may exist and it must sit above the first released section — a heading anywhere else is stranded residue that the fold guard fails on, and the guard also treats "unreleased work with no topmost `## Unreleased` section" as a stalled releaser. Inserting the section directly above `## v0.59.0` satisfies both signatures.
</notes>
