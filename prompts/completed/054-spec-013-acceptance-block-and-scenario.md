---
status: completed
spec: [013-fresh-context-local-review-adjudication]
execution_id: coding-fresh-context-exec-054-spec-013-acceptance-block-and-scenario
dark-factory-version: v0.198.7
created: "2026-10-18T10:31:14Z"
queued: "2026-10-18T10:59:39Z"
started: "2026-10-18T11:38:21Z"
completed: "2026-10-18T11:56:41Z"
branch: dark-factory/fresh-context-local-review-adjudication
---

# Lock the dispatch wiring in the acceptance suite and commit the verdict scenario

<summary>
- The project's acceptance suite now fails if the fresh-context adjudicator file disappears, if the local review stops naming the adjudicator, or if any of the four dispatch inputs leaves the command
- The assertion uses the adjudicator's name as a written-down literal, never derived from the suite's own output, so it still fails after the wiring is deleted
- A new committed scenario holds the one walk that no scripted assertion can make: that a fresh context reaches a different verdict than the session that wrote the code
- The scenario names the seeded violation, the sentence an authoring session would say to excuse it, and the two runs whose verdicts differ
- The scenario records the expected outcome pair — excused in the session that wrote the change, flagged by the cold one — plus the spawn counts that show the cost is one dispatch, and zero on a clean diff
- The scenario is a walk the operator can re-run, so the recipe survives the completion of the work that produced it
- Nothing else changes: no command, no guide, no agent, no changelog entry
</summary>

<objective>
Add a selector-dispatch assertion block to `scripts/acceptance.sh` that fails when the wiring is removed, and commit `scenarios/011-fresh-context-adjudication-dispatch.md` holding the operator-runnable recipe whose executable core is the fresh-context verdict test. The assertion guards the wiring; the scenario guards the verdict — neither can do the other's job. This is prompt **3 of 4** for spec 013.
</objective>

<context>
Read fully before editing:

- `scripts/acceptance.sh` in full. Note its structure: `set -uo pipefail`, a `cd "$(dirname "$0")/.."`, a preflight requiring `jq` and `ast-grep`, the `ok()` / `fail()` helpers, six numbered sections (`=== 1/6 … ===` through `=== 6/6 … ===`), and a summary that exits 1 when any `fail` fired. The `=== 5/6 Selector mode contracts ===` section already has sub-blocks `(a)` through `(e)`.
- `scenarios/005-selector-clean-short-circuit.md` and `scenarios/006-selector-findings-path.md` — the house style for a walked scenario: frontmatter, H1 `# Scenario NNN: <what this proves in one line>`, a one-sentence "Validates that …" description, checkbox sections, observable outcomes only, a `## Cleanup` block, and a closing `**Status**:` line recording the walk.
- `scenarios/010-security-zero-findings.md` — the shape for an inline-built fixture, including the `## Test PR` section that describes the fixture rather than pointing at a perpetual PR.
- `commands/local-review.md` — the file the new assertion greps. Confirm it carries `coding:selector-adjudicator` and the four labels `DIFF`, `CLASSIFIED_RULES`, `MECHANICAL_FINDINGS`, `REPO_PATH` (prompt 2 writes them).
- `agents/selector-adjudicator.md` — the file whose presence the assertion checks.
- `rules/index.json` — confirm the seeded rule's entry, which the scenario cites by id:
  - `go-composition/no-same-package-private-helper-for-business-logic` — level `MUST`, `enforcement_type` `judgment`, owner `go-architecture-assistant`, trigger `**/*.go`. Its `applies_when`: a Go service package introduces new business logic (data transformation, validation, formatting — anything beyond pure plumbing) as a same-package private helper function called from a method, instead of behind a small interface + constructor + struct + method seam.
- The scenario-writing rules at `/home/node/.claude/plugins/marketplaces/dark-factory/docs/rules/scenario-writing.md` — frontmatter `status`, H1 + "Validates that …" line, Setup → Action → Expected (+ optional Cleanup) checkbox sections, observable outcomes only, self-contained, one journey per file, no internal-struct assertions.

**Why this prompt ships a scenario at all.** The behaviour the change delivers is that a *different context* reaches a different verdict. `scripts/acceptance.sh` can prove the dispatch is wired; it can never prove the cold context changed the answer. Scenario 005 covers the clean short-circuit and scenario 006 covers `/coding:pr-review`; neither reaches the fresh-context verdict. The named regression risk is concrete: a later edit silently reverting `Step 4d-sel` to in-session adjudication, which every text-level assertion would still pass. All four conditions of the scenario-writing test hold, so the walk is committed here rather than living only in the spec that is archived on completion.

**Verified repo facts this prompt relies on**

- `scenarios/` currently holds `001` through `010`; `011` is the next free number.
- `README.md`'s Acceptance Scenarios table lists `001`–`004` and `007`–`010` — scenarios `005` and `006` are not listed there. This prompt therefore adds no README row for `011`.
- `scripts/acceptance.sh` is not an exempt path for the marker rules; neither is anything under `scenarios/`.
- `scripts/acceptance.sh`'s section headers read `N/6`; adding sub-block `(f)` to section 5 keeps that count correct, so no header needs editing.
- `tar` is available at `/usr/bin/tar`; the container's `.git` is masked, so any scratch copy must exclude it.
</context>

<requirements>

### 1. Hard dependency guard

Before editing anything, confirm prompt 2 shipped:

```bash
grep -c 'coding:selector-adjudicator' commands/local-review.md
for label in DIFF CLASSIFIED_RULES MECHANICAL_FINDINGS REPO_PATH; do grep -c "$label" commands/local-review.md; done
test -f agents/selector-adjudicator.md && echo present
```

Every count must be ≥ 1 and the file must exist. If any check fails, STOP and report `Status: failed` with the explicit message that prompt 2 (and prompt 1) must execute first — the assertion below greps strings those prompts write, and a block authored against a missing string would pass vacuously.

### 2. Add sub-block `(f)` to `scripts/acceptance.sh`

Append a sub-block `(f)` to the `=== 5/6 Selector mode contracts ===` section, after the existing `(e)` runner `.git` exclusion block and before the `echo "=== 6/6 Self-containment script tier ==="` line. It uses the existing `ok()` / `fail()` helpers and the existing `grep -qF` idiom, and asserts four things:

1. `agents/selector-adjudicator.md` exists — a literal path test (`[ -f agents/selector-adjudicator.md ]`).
2. `commands/local-review.md` names `coding:selector-adjudicator` — the literal string, via `grep -qF`.
3. `agents/selector-adjudicator.md` declares `name: selector-adjudicator` — asserted with `grep -qE '^name: selector-adjudicator$'`. **This is the assertion that crosses the real boundary:** the subagent registry resolves `subagent_type` from the agent file's `name:` field, not its filename, so a file that exists and is named correctly on disk still fails at dispatch if that field is renamed. File-existence plus the command-side string is a shape test; this is the contract test.
4. each of the four input labels `DIFF`, `CLASSIFIED_RULES`, `MECHANICAL_FINDINGS`, `REPO_PATH` appears in `commands/local-review.md` — one `grep -qF` per label, counted into a `missing_inputs` variable so the failure message names how many are missing.

Add a comment above the block stating why the agent file name is a **literal** and never derived from the run's own output: an expectation computed from the same run that produced the artifacts would still pass after the wiring was deleted, which is the one failure this block exists to catch. The block must fail (non-zero exit from the script, via the existing `fail()` counter and the summary) in a copy of the repository with `agents/selector-adjudicator.md` removed.

Shape (adapt to the file's existing style; do not restructure the surrounding sections):

```bash
# (f) Selector dispatch wiring: the local review's Step 4d-sel is exactly one
# fresh-context adjudicator dispatch. The agent file name and the four input
# labels are LITERAL here, never derived from this run's own output — a derived
# expectation would still pass after the wiring was deleted.
if [ -f agents/selector-adjudicator.md ]; then
  ok "selector dispatch: agents/selector-adjudicator.md exists"
else
  fail "selector dispatch: agents/selector-adjudicator.md is missing"
fi
if grep -qF 'coding:selector-adjudicator' commands/local-review.md; then
  ok "selector dispatch: local-review.md names coding:selector-adjudicator"
else
  fail "selector dispatch: local-review.md does not name coding:selector-adjudicator"
fi
# The subagent registry resolves subagent_type from this field, not the filename —
# a renamed `name:` would pass every other assertion here and fail at dispatch.
if grep -qE '^name: selector-adjudicator$' agents/selector-adjudicator.md; then
  ok "selector dispatch: agents/selector-adjudicator.md declares name: selector-adjudicator"
else
  fail "selector dispatch: agents/selector-adjudicator.md does not declare name: selector-adjudicator"
fi
missing_inputs=0
for label in DIFF CLASSIFIED_RULES MECHANICAL_FINDINGS REPO_PATH; do
  grep -qF "$label" commands/local-review.md || missing_inputs=$((missing_inputs+1))
done
if [ "$missing_inputs" -eq 0 ]; then
  ok "selector dispatch: all four dispatch input labels present in local-review.md"
else
  fail "selector dispatch: $missing_inputs of the four dispatch input labels missing from local-review.md"
fi
```

Do not change the `N/6` section headers, the existing `(a)`–`(e)` blocks, the preflight, or the summary.

### 3. Create `scenarios/011-fresh-context-adjudication-dispatch.md`

Follow the scenario-writing rules and the house style of `scenarios/005`, `006` and `010`. Frontmatter:

```
---
status: active
---
```

Body: an H1 `# Scenario 011: <what this proves in one line>`, then a one-sentence description starting `Validates that `, then exactly these five `## ` sections in this order — `## Test PR`, `## Setup`, `## Action`, `## Expected`, `## Cleanup` — then a closing `**Status**:` line. Every item is a `- [ ]` checkbox; every assertion is an observable outcome (a file on disk, a command's output, a grep count, a transcript field), never an internal struct or function call.

The scenario must state, concretely enough that an operator can re-run it without this spec:

1. **The fixture (`## Test PR`).** An inline-built scratch repository holding a minimal generic Go order service (User / Order / Product / Customer only — never a trading or project-specific domain), created under `mktemp -d` with `git init`. The scratch repo is local-only, so the walk uses `/coding:local-review` in place rather than the branch-vs-target flow.
2. **The seeded violation.** One change that introduces new order-total business logic as a same-package private helper function called from a method, instead of behind a small interface + constructor + struct + method seam. Name the rule by its literal id `go-composition/no-same-package-private-helper-for-business-logic`, and state why it is the right seed: its enforcement is `judgment`-tier, so the mechanical funnel emits nothing for it and the verdict rests entirely on the adjudicator's read of the rule's `applies_when` text against the diff. A mechanically-detected violation would be reported by the funnel regardless of any rationale, which would break the comparison this scenario exists to make.
3. **The in-conversation rationale that excuses it.** State the sentence the fixture session says in the conversation before running the review — a plausible, good-faith justification in the author's own words, e.g. that the total calculation is used by this one handler only, so a private helper in the same package is the simplest place for it and a seam would be ceremony. This sentence is the contamination under test; the scenario records it verbatim so the walk is reproducible.
4. **The pre-change run.** At the pre-change release of the plugin (resolved by pinning a plugin clone in an isolated config directory — the technique scenarios 005 and 006 already use), in a fresh session: build the fixture, state the rationale, run `/coding:local-review`, and capture the report. Expected: the report contains **no** finding citing `go-composition/no-same-package-private-helper-for-business-logic`, and no finding whose first bold run is the seeded violation's `path:LINE` — the in-session adjudicator read the rule and found the rationale in its own context settled.
5. **The post-change run.** At the post-change release, in a fresh session: build the identical fixture, state the identical rationale, run `/coding:local-review`, and capture the report. Expected: the report contains **one** finding citing `go-composition/no-same-package-private-helper-for-business-logic`, whose first bold run is the seeded violation's `path:LINE`.
6. **The expected verdict pair.** State it as the scenario's headline outcome: excused in the session that wrote the code, flagged by the cold one. State that this pair is the assertion no scripted check can make.
7. **The cost observation.** The post-change run's stream-json transcript contains exactly one `tool_use` block whose `subagent_type` is `coding:selector-adjudicator`; a `/coding:local-review` run over a diff that short-circuits clean contains none. Mention the dispatch by name so the scenario records which subagent is counted.
8. **The honesty line.** The closing `**Status**:` line states the scenario's state truthfully: it carries `status: active` per the spec's acceptance criterion, while the walk itself is executed on the operator rung after the plugin release, and the recipe above is what the operator runs.
9. Keep it short — no more than roughly a dozen checkboxes — self-contained, one journey per file, and free of any reference to a planning directory, a requirement identifier, a home-directory path, or revision/sign-off prose.

### 4. Self-check before finishing

Re-run the `<verification>` block, including the scratch-copy negative, and confirm every expectation. Walk requirements 1–3 above against the actual files. Do not report success if any check failed.
</requirements>

<constraints>
- **Scope:** this prompt writes exactly two files — `scripts/acceptance.sh` (edited) and `scenarios/011-fresh-context-adjudication-dispatch.md` (new). Do NOT modify `commands/*.md`, `docs/*`, `agents/*`, `rules/*`, `README.md`, `llms.txt`, `CHANGELOG.md`, or any other file under `scenarios/`.
- **The assertion must be able to fail.** Its agent-file name and its four input labels are written-down literals, never computed from the run's own output. Run the scratch-copy negative in `<verification>` — do not assume it.
- **`scenarios/011` carries `status: active`.** That is the acceptance criterion for this change. Do not promote any other scenario, and do not alter `scenarios/005` or `scenarios/006`.
- **No README scenario row.** The Acceptance Scenarios table lists `001`–`004` and `007`–`010`; `005` and `006` are absent from it, so `011` is not added there either.
- **Generic content only:** the fixture and every example use User, Order, Product, Customer — never trading or project-specific domain terms.
- **Observable outcomes only** in the scenario: files on disk, command output, grep counts, exit codes, transcript fields. No internal struct or function assertions.
- **Marker hygiene on every added line.** Neither file this prompt writes is an exempt path, so no added line may carry a home-directory path, a requirement id, a planning-directory reference, or revision/sign-off meta. The literal pattern (copied from `scripts/rule-checks.sh`, not retyped from memory):

  ```
  (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
  ```

  Copy this pattern without the fence's leading indentation — a copy that carries the two leading spaces no longer matches a home-directory path. The verification block below also carries the pattern inline.

  In particular the scenario must not name a planning directory, and must not describe the pins as "vN of this change".
- **No new ast-grep YAML and no rule-base change.** `rules/index.json` is untouched.
- **No new config knob, no flag, no mode token** anywhere in the assertion or the scenario.
- **Do NOT commit and do NOT run any `git` command in `<verification>`.** This container's `.git` is masked — `.dark-factory.log` records `hideGit=true hideGitSource=arg` — so a bare `git` call fails with `fatal: not a git repository`. The scratch-copy negative below excludes `.git` for exactly that reason. The `git init` / `git commit` steps the scenario describes are instructions for the operator walking it on the host, not commands this prompt runs.
- **The `CHANGELOG.md` `## Unreleased` criterion in this repo's definition of done is deliberately deferred to prompt 4** — this prompt is forbidden from touching `CHANGELOG.md`. Do not report the missing `## Unreleased` entry as a blocker; it is a scope boundary, not an unmet criterion.
- **Cross-prompt boundary:** prompt 4 depends on this prompt's assertion block existing so that its final gate re-run exercises the wiring lock. If the block is absent at the end of this run, report `Status: failed` naming it.
</constraints>

<verification>
All commands run from the repo root and are container-executable. This container has **no git** — no check below uses it.

```bash
# --- the dependency guard (prompt 2 shipped) ---
grep -c 'coding:selector-adjudicator' commands/local-review.md                  # expect: >= 1
test -f agents/selector-adjudicator.md && echo "OK: agent file present"

# --- the acceptance block is present and complete ---
grep -c 'selector-adjudicator' scripts/acceptance.sh                           # expect: >= 1
grep -c 'agents/selector-adjudicator.md' scripts/acceptance.sh                 # expect: >= 1
for label in DIFF CLASSIFIED_RULES MECHANICAL_FINDINGS REPO_PATH; do
  printf '%s: ' "$label"; grep -c "$label" scripts/acceptance.sh               # expect: >= 1 each
done
grep -c '(f)' scripts/acceptance.sh                                            # expect: >= 1
grep -cE 'name: selector-adjudicator' scripts/acceptance.sh                    # expect: >= 1 (the name-field contract test)
bash -n scripts/acceptance.sh && echo "OK: acceptance.sh parses"
make check-acceptance                                                          # expect: exit 0

# --- AC8 negative: a scratch copy with the agent file removed must fail ---
SCRATCH=$(mktemp -d)
tar cf - --exclude=.git . | ( cd "$SCRATCH" && tar xf - )
test -f "$SCRATCH/commands/local-review.md" && test -f "$SCRATCH/scripts/acceptance.sh" && echo "OK: scratch copy complete"
rm -f "$SCRATCH/agents/selector-adjudicator.md"
bash "$SCRATCH/scripts/acceptance.sh" > /tmp/acceptance-negative.log 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then echo "OK: acceptance exits $rc with the agent file removed"; else echo "FAIL: acceptance passed with the agent file removed — the assertion cannot fail"; fi
grep -c 'selector-adjudicator.md is missing' /tmp/acceptance-negative.log      # expect: >= 1 (the failure is this assertion, not an unrelated crash)
rm -rf "$SCRATCH"

# --- AC13: the scenario file ---
test -f scenarios/011-fresh-context-adjudication-dispatch.md && echo "OK: scenario exists"
grep -c '^status: active$' scenarios/011-fresh-context-adjudication-dispatch.md          # expect: 1
grep -c 'selector-adjudicator' scenarios/011-fresh-context-adjudication-dispatch.md      # expect: >= 1
grep -c 'go-composition/no-same-package-private-helper-for-business-logic' scenarios/011-fresh-context-adjudication-dispatch.md   # expect: >= 1
grep -c '^- \[ \]' scenarios/011-fresh-context-adjudication-dispatch.md                  # expect: >= 8
grep -c '^## ' scenarios/011-fresh-context-adjudication-dispatch.md                      # expect: 5
for sec in '## Test PR' '## Setup' '## Action' '## Expected' '## Cleanup'; do
  printf '%s: ' "$sec"; grep -cF "$sec" scenarios/011-fresh-context-adjudication-dispatch.md   # expect: 1 each
done
grep -c '^# Scenario 011' scenarios/011-fresh-context-adjudication-dispatch.md           # expect: 1
grep -c 'Validates that ' scenarios/011-fresh-context-adjudication-dispatch.md            # expect: >= 1

# --- marker hygiene on the two files this prompt writes ---
if grep -nE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' scripts/acceptance.sh scenarios/011-fresh-context-adjudication-dispatch.md; then
  echo "FAIL: a marker literal was added outside the exempt paths"
else
  echo "OK: added lines are marker-free"
fi

# --- scope lock: nothing else moved ---
if grep -q 'scenarios/011' README.md; then echo "FAIL: README row is not part of this change"; else echo "OK: no README scenario row"; fi
if grep -q 'selector-adjudicator' CHANGELOG.md; then echo "FAIL: CHANGELOG.md is prompt 4's file"; else echo "OK: changelog untouched (prompt 4)"; fi
if grep -q 'selector-adjudicator' docs/selector-mode-guide.md; then echo "OK: guide already carries the dispatch (prompt 2)"; else echo "FAIL: prompt 2 did not ship"; fi

# --- the real in-container gate (precommit minus the git-dependent changelog-fold target) ---
make check-links check-json check-index check-coverage check-rule-tests bench-test   # expect: exit 0
```

`make precommit` adds `check-changelog-fold` on top of the targets above. That target shells out to `git rev-parse --git-dir` and dies with `not a git repository` while `.git` is masked here, so it cannot pass inside this container and is deliberately excluded. Run `make precommit` on the host (operator rung) — do not report this run as failed because of it, and do not report success on the checks above if any of them exited non-zero.
</verification>

<notes>
- **Why `status: active` on an unwalked scenario.** The spec's acceptance criterion for this change requires it, and the scenario-writing rules define `active` as "verified, part of the regression suite — after first successful run". The closing `**Status**:` line records the tension explicitly (the walk is the operator-rung recipe below it, executed after the release), so a reader is not misled. **Open question for the reviewer:** if the house rule should win over the acceptance criterion, the one-line change is `status: draft` here plus `draft → active` at walk time.
- **Why the seed is a judgment-tier rule.** The comparison is only meaningful if the mechanical funnel is silent for the seeded violation. A mechanically-detected violation would be emitted by the runner regardless of any rationale in the session, so the pre-change run would already contain it and the verdict pair would prove nothing. `go-composition/no-same-package-private-helper-for-business-logic` is `enforcement_type: judgment` with a `**/*.go` trigger, so it reaches the adjudicator and only the adjudicator.
- **Why the fixture is inline-built.** Scenarios 007–010 build their fixtures in Setup; a perpetual fixture PR would be a second repository to keep alive, and this fixture is a handful of Go lines.
- **Why no README row.** The Acceptance Scenarios table omits `005` and `006`, so adding a row for `011` would be an inconsistent one-off and is outside this change's scope.
</notes>
