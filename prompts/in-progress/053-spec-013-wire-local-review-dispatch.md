---
status: approved
spec: [013-fresh-context-local-review-adjudication]
created: "2026-10-18T10:31:14Z"
queued: "2026-10-18T10:59:39Z"
branch: dark-factory/fresh-context-local-review-adjudication
---

# Wire the single fresh-context dispatch into the local review and its guide

<summary>
- A local review in selector mode now classifies its applicable rules in the calling session and then hands the judgment to exactly one fresh-context adjudicator
- That adjudicator receives four named things — the diff, the classified rule list, the mechanical findings and the repository path — and nothing else, so the reasoning that produced the change cannot talk it out of a finding
- A clean diff still costs nothing: the existing short-circuit is evaluated before the dispatch, so a run with nothing to adjudicate spawns no adjudicator at all
- A dispatch that fails, errors or comes back empty is reported as a blocking toolchain failure, never as a clean review — silence is not a pass
- The failed dispatch is retried at most once, and a second failure is reported rather than swallowed
- The calling session still owns citation validation: it writes the returned findings out, runs the existing validator over them, and keeps only the findings whose rule ids resolve
- The shared guide now documents two forms of the adjudication step: the in-session form the other two review commands keep, and the fresh-context form the local review uses
- The guide keeps every literal its acceptance assertions check, byte for byte, and the two other review commands are untouched
</summary>

<objective>
Make `/coding:local-review`'s selector-mode `Step 4d-sel` a single `coding:selector-adjudicator` dispatch whose input is the diff, the classified rule set, the mechanical findings and the repo path — and document that variant in the shared selector-mode guide without disturbing the in-session procedure `/coding:pr-review` and `/coding:code-review` keep. This is prompt **2 of 4** for spec 013, and it is the only prompt that writes `commands/local-review.md` or `docs/selector-mode-guide.md`.
</objective>

<context>
Read fully before editing:

- `commands/local-review.md` in full. The four regions this prompt rewrites are: the `### Step 1: Parse Arguments` mode list (the `Otherwise (including ...)` bullet), the `### Step 4: Dispatcher` paragraph that begins `Mirrors \`commands/pr-review.md\` Step 4`, the `#### Selector mode (the default): Steps 4c-sel and 4d-sel` section (its intro sentence, its input list, its short-circuit sentence), and nothing else.
- `docs/selector-mode-guide.md` in full. The regions this prompt rewrites are: the opening paragraph, the `## Inputs` table, the `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)` heading and its two zero-spawn sentences, plus a new subsection documenting the fresh-context form.
- `commands/pr-review.md` — read only, as the sibling whose in-session procedure must stay byte-for-byte. Compare its three matching regions against `commands/local-review.md` to see exactly which sentences are shared and which are the local review's own.
- `scripts/acceptance.sh` — read the `=== 5/6 Selector mode contracts ===` section. It asserts, by literal string, that both commands still carry `selector clean — no adjudication needed`, `GUIDE_OK`, `GUIDE_MISSING`, the `--selector` token, the step labels `4c-sel` and `4d-sel`, and the routing phrase `Selector mode (default)` / `Selector mode (the default)`; that both still reference `scripts/ast-grep-runner.sh` and the `findings_by_owner` / `coding:<owner>` dispatch block; that the local review still carries the `Short Mode` skip directive; that both carry the four Step 2.5 doc mappings (`teamvault-conventions.md`, `go-k8s-binary-conventions.md`, `k8s-manifest-guide.md`, `changelog-guide.md`); and that the guide still carries `Step 4c-sel` + `CLASSIFY`, `Step 4d-sel` + `ADJUDICATE`, and the verbatim sentence `When uncertain, include.`. Every one of those literals survives this change.
- `agents/selector-adjudicator.md` — the agent prompt 1 created. Its `## Inputs` section names the four dispatch inputs; use the identical four labels here.
- `CLAUDE.md` — generic-content rule (User / Order / Product / Customer only), no personal or machine-local paths in shipped plugin files.

**The frozen literals — do not disturb them.** These are asserted verbatim by `scripts/acceptance.sh` and must appear unchanged in the files this prompt writes:

- in `commands/local-review.md`: `selector clean — no adjudication needed` (note the em dash), `GUIDE_OK`, `GUIDE_MISSING`, `Selector mode (default)`, `Selector mode (the default)`, `4c-sel`, `4d-sel`, `scripts/ast-grep-runner.sh`, `findings_by_owner`, `coding:<owner>`, the four Step 2.5 mapping filenames, the `Short Mode` skip directive, the `--selector` token.
- in `docs/selector-mode-guide.md`: `Step 4c-sel`, `CLASSIFY`, `Step 4d-sel`, `ADJUDICATE`, `When uncertain, include.` (this sentence must survive byte-for-byte — the trailing period is part of it).

**Verified repo facts this prompt relies on**

- `commands/local-review.md` carries `zero sub-agent spawns` on exactly three lines: the Step 1 `Otherwise (including ...)` bullet, the Step 4 dispatcher paragraph, and the selector-mode section's `Steps 4.0, 4a, and 4b-i run unchanged` sentence. All three are rewritten by this prompt.
- `commands/pr-review.md` carries the same three sentences and is **not** edited here; its copies stay.
- The selector-mode section's current input list is `DIFF`, `CANDIDATES`, `MECHANICAL_FINDINGS`, `Working directory`. `CANDIDATES` stays — it is the in-session `Step 4c-sel` input. `CLASSIFIED_RULES` and `REPO_PATH` are the two new labels the dispatch adds.
- `docs/selector-mode-guide.md` today contains **zero** occurrences of each of `not-clean`, `fresh-context`, and the contiguous words `before the dispatch`, and one occurrence of `fail-closed` (in the security extension's citation-validation sentence). Assertions on `not-clean`, `fresh-context` and `before the dispatch` are therefore genuinely new, not thresholds the pre-existing text already meets.
- `commands/local-review.md` currently contains one occurrence of `exactly one`, in the `--security` subsection's citation-validation step, which is unrelated to the dispatch. The dispatch sentence must therefore carry both `exactly one` and `coding:selector-adjudicator` on the same line, or the assertion is satisfied by pre-existing text.
- Neither file contains a `### RULE` block, so `rules/index.json` is unaffected and `make check-index` sees no drift.
</context>

<requirements>

### 1. `commands/local-review.md` — Step 1 mode list

Rewrite the `Otherwise (including ...)` bullet so it keeps the literal routing phrase `Selector mode (default)` and stops claiming zero sub-agent spawns. Current text:

```
- Otherwise (including `standard`, `selector`, `--selector`, or no token) → **Selector mode (default)** (in-session classify + adjudicate, zero sub-agent spawns)
```

Replace the parenthetical with a phrase naming the single fresh-context dispatch, e.g.:

```
- Otherwise (including `standard`, `selector`, `--selector`, or no token) → **Selector mode (default)** (in-session classify, then exactly one fresh-context `coding:selector-adjudicator` dispatch)
```

### 2. `commands/local-review.md` — Step 4 dispatcher paragraph

Keep the literal `Selector mode (the default)` and the `Full mode` / `Short mode` clauses. Current selector clause:

```
**Selector mode (the default)**: in-session classify + adjudicate, zero sub-agent spawns.
```

Replace it with a clause naming the single fresh-context dispatch, e.g.:

```
**Selector mode (the default)**: in-session classify, then exactly one fresh-context `coding:selector-adjudicator` dispatch for adjudication.
```

### 3. `commands/local-review.md` — the selector-mode section

This is the section headed `#### Selector mode (the default): Steps 4c-sel and 4d-sel`. Rewrite it so it describes, in order:

1. **What runs in-session.** `Steps 4.0`, `4a` and `4b-i` run unchanged, and `Step 4c-sel` CLASSIFY runs in this session. Replace the current sentence `Steps 4.0, 4a, and 4b-i run unchanged. Resolve the guide and execute Steps 4c-sel and 4d-sel from it — zero sub-agent spawns.` with wording that keeps the guide resolution and drops the zero-spawn claim, e.g.:

   ```
   Steps 4.0, 4a, and 4b-i run unchanged, and Step 4c-sel CLASSIFY runs in this session. Step 4d-sel ADJUDICATE is exactly one `coding:selector-adjudicator` dispatch. Resolve the guide and execute both steps from it.
   ```

2. **The in-session classify inputs.** Keep `DIFF` and `CANDIDATES` in the input list, since `Step 4c-sel` consumes them directly:

   - `DIFF` = the review's diff (see the dispatch list below for how the dispatch receives it)
   - `CANDIDATES` = the `Step 4b-i` `<rule-id> <owner>` output

3. **The single dispatch and its four inputs.** State that in selector mode the command spawns **exactly one** `Task` whose `subagent_type` is `coding:selector-adjudicator`, and that the dispatch prompt carries these four named inputs and nothing else:

   - **`DIFF`** = the diff, written by this session to a session-local path outside the reviewed tree (mirroring the `/tmp/pr-review-findings.json` convention, e.g. `/tmp/local-review-diff.patch`); `git diff HEAD~1`, or the directory diff as parsed in Step 1
   - **`CLASSIFIED_RULES`** = the `Step 4c-sel` applicable rule-id list
   - **`MECHANICAL_FINDINGS`** = `/tmp/local-review-findings.json`, the `Step 4a` runner output
   - **`REPO_PATH`** = the directory under review, absolute

   State that the dispatch carries no conversation history, no summary of the authoring session, no statement of what the author intended, and no prior report — the four named inputs are the whole input, and a caller that wants to explain the diff to the adjudicator has found the contamination this dispatch exists to remove. State that the subagent performs its own batching when the applicable set exceeds 20 rules, so the caller still spawns once.

4. **The caller keeps citation validation.** After the dispatch returns, this session writes the returned findings to a session-local JSON, runs `scripts/validate-citations.sh` over that file from the plugin root (the same plugin-root resolution the section already documents), and consolidates only the survivors into the Step 5 report.

5. **Fail-closed.** State that if the dispatch fails, errors, or returns nothing, the review reports it as a **Must Fix toolchain failure** naming the `coding:selector-adjudicator` dispatch, that the judgment tier reads as not-run, and that the review is never presented as a complete selector review built only from the mechanical findings. State that the dispatch is retried at most once and that a second failure is reported, never swallowed — the same fail-fast discipline `Step 4.0` and `Step 4b` already apply to a missing `ast-grep` or a missing selector guide. The sentence must contain both `Must Fix toolchain failure` and `coding:selector-adjudicator` on the same line.

6. **The clean short-circuit.** Keep the existing sentence verbatim: `On the guide's short-circuit condition the report line is \`selector clean — no adjudication needed\`.` Add, on the same or an adjacent line, that the short-circuit is evaluated before the dispatch — on an empty applicable set with empty mechanical findings the section proceeds to Step 5 with **zero** subagents spawned.

Do not change anything else in this section: the `GUIDE_OK` / `GUIDE_MISSING` fail-fast block, its exact command, the `Skip this section for short/full mode.` sentence and the traceability pointer all stay as they are.

### 4. `docs/selector-mode-guide.md` — qualify the zero-spawn claims

Four places currently assert that selector mode spawns no subagents. Each must be scoped to the callers that still do; none of them may be deleted.

1. **The opening paragraph.** It currently ends: `The design goal is zero sub-agent spawns: every rule is evaluated inside the current session context rather than cold-starting one sub-agent per owner.` Qualify it so the design goal is stated for `/coding:pr-review` and `/coding:code-review`, and so `/coding:local-review` is named as the exception whose `Step 4d-sel` runs in exactly one fresh-context `coding:selector-adjudicator` dispatch — because its calling session is the session that authored the change. Keep the rest of the paragraph (the `Step 4b-ii` replacement sentence and the `Steps 4.0, 4a, and 4b-i` sentence) as it is.

2. **The `Step 4d-sel` heading.** `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)` → scope the parenthetical to the two callers that keep the in-session form, e.g. `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn — \`/coding:pr-review\` and \`/coding:code-review\`)`. The heading must keep both literal tokens `Step 4d-sel` and `ADJUDICATE`.

3. **The batching sentence.** `Each pass runs in the current session — still zero Task spawns.` → scope it to the in-session callers and note that the fresh-context caller's adjudicator does its own batching inside its single dispatch.

4. **The citation-validation parenthetical.** `**Citation validation** (invoked directly — selector mode spawns NO sub-agents, including \`coding:simple-bash-runner\`)` → keep the operative instruction (the validator is invoked directly, never via a `coding:simple-bash-runner` subagent) and drop the absolute claim that selector mode spawns no subagents.

Do **not** alter the `Step 4c-sel` CLASSIFY procedure, the recall-contract sentence, the skip-justification rule, the `HARD INVARIANT`, the architecture-tier bypass, the short-circuit block, the `## Inputs` semantics for the in-session callers, the security extension, the intent extension, or the traceability section.

### 5. `docs/selector-mode-guide.md` — the `## Inputs` table

The table currently has rows for `DIFF`, `CANDIDATES`, `MECHANICAL_FINDINGS`, `Working directory`, and `INTENT`. Add the two missing fresh-context input names and scope all four dispatch inputs to the caller that sets them:

- Add a `CLASSIFIED_RULES` row: the `Step 4c-sel` applicable rule-id list; set only by `/coding:local-review` for its fresh-context `Step 4d-sel` dispatch.
- Add a `REPO_PATH` row: the directory under review, absolute; set only by `/coding:local-review` for its fresh-context `Step 4d-sel` dispatch.
- Append to the existing `DIFF` and `MECHANICAL_FINDINGS` rows a note that these are also the fresh-context dispatch inputs for `/coding:local-review` (the diff written to a session-local path outside the reviewed tree, mirroring the findings-file convention).

Keep the existing `CANDIDATES`, `Working directory` and `INTENT` rows intact — they are the in-session callers' inputs.

### 6. `docs/selector-mode-guide.md` — document the fresh-context form

Add a subsection immediately after the `Step 4d-sel` section and before `## Security Extension (dormant)`, titled so that it carries the literal tokens `Step 4d-sel` and `ADJUDICATE` (e.g. `## Step 4d-sel: ADJUDICATE (fresh-context dispatch — \`/coding:local-review\`)`). It documents the same step in its second form, alongside the in-session form the other two callers keep, and states:

- `/coding:local-review` is the one caller whose session is the session that authored the change, which is why its adjudication runs cold. Use the token `fresh-context` in this subsection.
- In that caller, `Step 4d-sel` is exactly one `coding:selector-adjudicator` dispatch, whose input is `DIFF`, `CLASSIFIED_RULES`, `MECHANICAL_FINDINGS` and `REPO_PATH` — and nothing else. No conversation history, no authoring rationale, no prior report, no session state.
- The adjudicator is read-only, so the review cannot mutate the tree it reviews.
- `Step 4c-sel` CLASSIFY stays in-session, and the residual contamination at the skip decision is a stated limit of this design — visible to a reader rather than discovered by one. The applicable set is still a subset of the `Step 4b-i` candidate set; the `HARD INVARIANT` is unchanged.
- The short-circuit is evaluated before the dispatch, so a clean run spawns zero subagents and the cost is bounded at one dispatch per review that has something to adjudicate. Write this sentence so the contiguous words `before the dispatch` appear in it — do not bold, hyphenate or line-break them apart.
- **Fail-closed:** a dispatch that fails, errors or returns nothing reads **not-clean** — it is reported as a **Must Fix toolchain failure** naming the dispatch, the judgment tier reads as not-run, and it is never degraded into a mechanical-findings-only report presented as a complete selector review. One retry is permitted; a second failure is reported, never swallowed. The subsection must contain the literal token `not-clean`.
- The caller keeps citation validation: it writes the returned findings to a session-local JSON and runs `scripts/validate-citations.sh` from the plugin root before consolidating survivors into the report.
- The subagent performs its own batching when the applicable set exceeds 20 rules; the caller still spawns once.
- `/coding:pr-review` and `/coding:code-review` keep the in-session form byte-for-byte.

### 7. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation. Walk the frozen-literals list at the top of this prompt against both files and confirm each literal is still present. Do not report success if any check failed.
</requirements>

<constraints>
- **Single writer, two files:** this prompt writes exactly `commands/local-review.md` and `docs/selector-mode-guide.md`. Do NOT modify `commands/pr-review.md`, `commands/code-review.md`, `agents/*`, `scripts/*`, `rules/*`, `scenarios/*`, `CHANGELOG.md`, `README.md`, `llms.txt`, `CLAUDE.md`, `.maintainer.yaml`, or `docs/security/**`.
- **Scope is `/coding:local-review` only.** The shared guide is edited **additively**: the in-session procedure the other two callers run stays byte-for-byte, and the edits to it are limited to scoping the four zero-spawn claims to those callers.
- **CLASSIFY stays in-session (frozen).** The classified rule set is a dispatch *input*, not a dispatch step. Moving classify into the subagent would spawn on every run, including the clean one.
- **Read-only adjudicator.** `tools: Read, Grep, Glob`. The agent never writes to the reviewed tree, never writes findings to disk and never runs a build or scan command. The caller owns the findings file and the citation validation.
- **Four inputs, no fifth channel.** The dispatch prompt carries the four named inputs and nothing else — no summary of the authoring conversation, no "the author intended X", no prior report.
- **Fail-closed, single retry.** A dispatch failure is a **Must Fix toolchain failure**. One retry is permitted; a second failure is reported, never swallowed. There is no fix loop, no re-review round, and no unbounded re-dispatch.
- **No new config knob, no flag, no mode token.** The fresh-context dispatch is the behaviour of the existing default mode. Do not add a `--fresh`-style token, an opt-out flag, or a config field.
- **Acceptance literals are frozen** — the list in `<context>` above. `scripts/acceptance.sh` asserts them verbatim; all of them survive this change.
- **Do not touch the security pipeline or the `--security` flag.** The `#### Security mode (under \`--security\` only)` subsection stays as it is, including its `selector-mode zero-spawn property` clause — see the note at the end of this prompt.
- **Marker hygiene on every added line.** Neither file this prompt writes is an exempt path, so no added line may carry a home-directory path, a requirement id, a planning-directory reference, or revision/sign-off meta. The literal pattern (copied from `scripts/rule-checks.sh`, not retyped from memory):

  ```
  (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
  ```

  Copy this pattern without the fence's leading indentation — a copy that carries the two leading spaces no longer matches a home-directory path. The verification block below also carries the pattern inline.

  The existing plugin-root templates (`${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/...}`) are literal-free and stay as they are.
- **Generic content only:** every example uses User, Order, Product, Customer — never trading or project-specific domain terms, never a real operator path.
- **No RULE block, no ast-grep YAML, no rule-base change.** `rules/index.json` is untouched.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked — `.dark-factory.log` records `hideGit=true hideGitSource=arg` — so a bare `git` call fails with `fatal: not a git repository`. The daemon commits on completion.
- **The `CHANGELOG.md` `## Unreleased` criterion in this repo's definition of done is deliberately deferred to prompt 4** — this prompt is forbidden from touching `CHANGELOG.md`. Do not report the missing `## Unreleased` entry as a blocker; it is a scope boundary, not an unmet criterion.
- **Cross-prompt boundary:** prompt 3's acceptance assertion greps `commands/local-review.md` for the literal `coding:selector-adjudicator` and for the four input labels, so those five strings must be in the file at the end of this run. If they are not, report `Status: failed` naming the missing strings.
</constraints>

<verification>
All commands run from the repo root and are container-executable. This container has **no git** — no check below uses it.

```bash
# --- AC2: the command names the single dispatch and its four inputs ---
grep -c 'coding:selector-adjudicator' commands/local-review.md                 # expect: >= 1
for label in DIFF CLASSIFIED_RULES MECHANICAL_FINDINGS REPO_PATH; do
  printf '%s: ' "$label"; grep -c "$label" commands/local-review.md            # expect: >= 1 each
done
# 'exactly one' also occurs pre-change in the unrelated --security citation step,
# so assert the dispatch sentence itself carries both tokens on one line:
grep -n 'exactly one' commands/local-review.md | grep -c 'coding:selector-adjudicator'   # expect: >= 1

# --- AC3: no zero-spawn claim survives for selector mode in the command ---
if grep -n 'zero sub-agent spawns' commands/local-review.md; then echo "FAIL: zero-spawn claim still present"; else echo "OK: no zero-spawn claim in local-review.md"; fi
grep -c 'zero sub-agent spawns' commands/pr-review.md                          # expect: 3 (sibling untouched)

# --- AC5: the dispatch failure path is fail-closed and lands in Must Fix ---
grep -n 'Must Fix toolchain failure' commands/local-review.md | grep -c 'coding:selector-adjudicator'   # expect: >= 1
grep -c 'not-clean' docs/selector-mode-guide.md                                # expect: >= 1 (fresh: 0 today)
grep -c 'fail-closed' docs/selector-mode-guide.md                                # expect: >= 2 (1 pre-existing in the security extension)

# --- AC6: the clean short-circuit, and it precedes the dispatch ---
grep -cF 'selector clean — no adjudication needed' commands/local-review.md    # expect: >= 1
grep -cF 'selector clean — no adjudication needed' docs/selector-mode-guide.md # expect: >= 1
grep -c 'before the dispatch' docs/selector-mode-guide.md                      # expect: >= 1 (fresh: 0 today)

# --- AC4: the guide documents the variant and keeps every literal acceptance.sh asserts ---
grep -c 'selector-adjudicator' docs/selector-mode-guide.md                     # expect: >= 1
grep -c 'fresh-context' docs/selector-mode-guide.md                            # expect: >= 1 (fresh: 0 today)
grep -c 'Step 4c-sel' docs/selector-mode-guide.md                              # expect: >= 1
grep -c 'Step 4d-sel' docs/selector-mode-guide.md                              # expect: >= 1
grep -c 'CLASSIFY' docs/selector-mode-guide.md                                 # expect: >= 1
grep -c 'ADJUDICATE' docs/selector-mode-guide.md                               # expect: >= 1
grep -cF 'When uncertain, include.' docs/selector-mode-guide.md                # expect: >= 1

# --- the frozen command literals all survive ---
for lit in 'GUIDE_OK' 'GUIDE_MISSING' '4c-sel' '4d-sel' 'Selector mode (default)' 'Selector mode (the default)' 'scripts/ast-grep-runner.sh' 'findings_by_owner' 'coding:<owner>' 'teamvault-conventions.md' 'go-k8s-binary-conventions.md' 'k8s-manifest-guide.md' 'changelog-guide.md'; do
  printf '%s: ' "$lit"; grep -cF "$lit" commands/local-review.md
done
grep -cE 'Short Mode.*No agents|Short Mode.*skip' commands/local-review.md     # expect: >= 1
grep -cE '\-\-selector|selector.*mode' commands/local-review.md                # expect: >= 1

# --- the guide's real gate, and the sibling callers stay clean ---
make check-acceptance                                                          # expect: exit 0
if grep -q 'selector-adjudicator' commands/pr-review.md; then echo "FAIL: pr-review was edited"; else echo "OK: pr-review untouched"; fi
if grep -q 'selector-adjudicator' commands/code-review.md; then echo "FAIL: code-review was edited"; else echo "OK: code-review untouched"; fi

# --- marker hygiene on the two files this prompt writes ---
if grep -nE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' commands/local-review.md docs/selector-mode-guide.md; then
  echo "FAIL: a marker literal was added outside the exempt paths"
else
  echo "OK: added lines are marker-free"
fi

# --- scope lock: prompt 1's and prompts 3/4's files did not move here ---
if grep -q 'selector-adjudicator' scripts/acceptance.sh; then echo "FAIL: acceptance.sh is prompt 3's file"; else echo "OK: acceptance.sh untouched (prompt 3)"; fi
if awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -q '^- '; then echo "FAIL: CHANGELOG.md is prompt 4's file"; else echo "OK: no changelog entry yet"; fi

# --- the real in-container gate (precommit minus the git-dependent changelog-fold target) ---
make check-links check-json check-index check-coverage check-rule-tests bench-test   # expect: exit 0
```

`make precommit` adds `check-changelog-fold` on top of the targets above. That target shells out to `git rev-parse --git-dir` and dies with `not a git repository` while `.git` is masked here, so it cannot pass inside this container and is deliberately excluded. Run `make precommit` on the host (operator rung) — do not report this run as failed because of it, and do not report success on the checks above if any of them exited non-zero.
</verification>

<notes>
- **Why `CANDIDATES` stays.** `Step 4c-sel` runs in this session and consumes `CANDIDATES` directly; `CLASSIFIED_RULES` is its *output* and the dispatch's input. Removing `CANDIDATES` from the command would break the in-session classify step, and the guide's `## Inputs` table still names it.
- **Why the dispatch sentence must carry both tokens on one line.** `grep -c 'exactly one' commands/local-review.md` already returns 1 today, from the `--security` subsection's citation-validation step. An assertion on that grep alone would pass before the change and after a revert. Pairing it with `coding:selector-adjudicator` on the same line is what makes it a real lock.
- **Why `not-clean`, `fresh-context` and `before the dispatch` are the guide's assertions.** `grep -c 'not-clean\|fail-closed' docs/selector-mode-guide.md` already returns 1 today because the security extension's citation-validation sentence says `fail-closed`, and the guide already contains the bare word `before` three times. Asserting on those three contiguous phrases — each currently absent from the guide — is what makes the checks fresh rather than thresholds the pre-existing text already meets.
- **Known stale phrase left in place, deliberately.** The `#### Security mode (under --security only)` subsection of `commands/local-review.md` still contains `or in-session per the selector-mode zero-spawn property`, which is now inaccurate for `/coding:local-review`. It is left untouched because the spec's Non-goals forbid touching the security pipeline or the `--security` flag, and this prompt's acceptance check for zero-spawn claims is scoped to `zero sub-agent spawns`. **Open question for the reviewer:** if the phrase should be reworded, it belongs in a follow-up change that is explicitly allowed to touch the security subsection.
- **Why the guide's opening line changes but nothing else in it does.** The spec's Problem section quotes that line as the flawed assumption the change corrects, so it cannot keep reading as shipped behaviour for the local review. The remaining three zero-spawn sentences are scoped to the two callers that still run in-session; none of them is deleted, and the procedure they describe is unchanged.
</notes>
