---
tags:
  - dark-factory
  - spec
status: draft
---

## Summary

- Add an opt-in `--selector` review mode to both `commands/pr-review.md` and `commands/code-review.md` that replaces per-owner sub-agent fanout with two in-session steps: CLASSIFY (narrow the glob candidates) then ADJUDICATE (judge the diff against only the applicable rule blocks).
- This is migration Step 1 of the AI-Selector Review Redesign: flagged, default OFF — without `--selector` the dispatcher behaves byte-for-byte as today.
- The existing jq glob pre-filter (Step 4b-i) STAYS as the candidate source; classify may only narrow it (`applicable ⊆ candidates`), never extend it.
- Selector mode spawns ZERO sub-agents; classify and adjudicate run as turns in the current session.
- Validation target: the bborbe/maintainer#2 fixture must surface all 13 frozen golden rule_ids at matching severities, and default-mode scenarios 002/004 must still pass unchanged.

## Problem

The dispatcher's Step 4b-ii spawns one `Task(coding:<owner>)` sub-agent per affected owner. This is the last LLM cost that scales with rule count: each owner is a cold-start sub-agent that re-reads rules and re-reads the diff, costing ~4 min of wall time apiece (observed 12-15 min for a single-file markdown PR with 2 owners; ~40 min for a standard 8-owner Go PR). The fanout also fires on glob-truthful but semantically-irrelevant matches (a typo edit in a command's description still loads the full agent-auditor context to conclude "nothing to do"). We need an in-session path that decouples review wall-time from rule count, but we must ship it behind a flag so the current behavior — which the bot and the acceptance scenarios depend on — does not change until the new path is validated on the golden fixture.

## Goal

Both review commands accept a `--selector` mode argument. When it is active, Step 4b-ii's per-owner Task dispatch is replaced by an in-session CLASSIFY step followed by an in-session ADJUDICATE step, with zero sub-agent spawns, and the existing jq glob pre-filter and citation validator both still run. When `--selector` is absent, the dispatcher executes its current logic unchanged. On the bborbe/maintainer#2 fixture, selector mode surfaces the same rule_ids at the same severities as the frozen legacy verdict.

## Non-goals

- Do NOT flip the default mode — selector is opt-in only; the default path is untouched (later migration step).
- Do NOT remove or alter the per-owner Task dispatch code path — it remains the default and the fallback (later migration step).
- Do NOT rewrite scenarios 002 or 004 — they assert default-mode behavior, which this spec leaves unchanged.
- Do NOT add `style_summary` extraction to `build-index.py` or `agents/index.json` (later step).
- Do NOT change any bot-side prompt in bborbe/maintainer (separate repo).
- Do NOT add new trigger types (`symbols:` / `imports:`) — later hardening wave.
- Do NOT author missing `### RULE` blocks — content backlog, separate spec.
- Do NOT add a tunable batch-size threshold knob — the >20-rule batching split is a fixed in-prose rule; if a future consumer demands a configurable threshold, that's a separate spec.

## Desired Behavior

1. Both commands accept `--selector` as a recognized mode token. When present, the dispatcher enters selector mode for Step 4; when absent, Step 4 runs exactly as today (short/standard/full unchanged).
2. In selector mode, Step 4a (mechanical funnel) and Step 4b-i (jq glob match producing the candidate rule list) run unchanged and produce the candidate set the same way they do today.
3. A new **Step 4c-sel CLASSIFY** runs in-session (no spawn): input is the diff plus the Step 4b-i candidate rule list. It decides, per candidate, applicable or skipped-with-reason, under a recall-optimized contract ("INCLUDE if a reasonable reviewer would want to read this rule before judging. Do not evaluate compliance. When uncertain, include."). The applicable set is a subset of the candidate set — never a superset. (Step labels carry a `-sel` suffix because the default branch already owns `4c` = context conventions and `4d` = citation validation; the selector branch is a parallel namespace and must not collide.)
4. Architecture-tier rules bypass classify and are always applicable: a rule whose `enforcement` text contains "architecture", OR whose doc lives in `go-architecture-patterns.md` and belongs to the SRP/layering family, is unconditionally included whenever it is in the candidate set.
5. If the applicable set AND the mechanical findings are both empty, the dispatcher reports the literal short-circuit `selector clean — no adjudication needed` and skips to the Step 5 report (no adjudication turn).
6. A new **Step 4d-sel ADJUDICATE** runs in-session (no spawn): it reads ONLY the `### RULE` blocks of the applicable rules from their `doc_path` files (not whole docs), judges the full diff plus the mechanical findings, and emits findings each citing `rule_id` + file + line + severity bucket — the files' existing report buckets **Must Fix (Critical) / Should Fix (Important) / Nice to Have (Optional)**. If the applicable set exceeds 20 rules, adjudication splits into 2-3 thematic in-session passes (still zero spawns).
7. Step 4d citation validation (`scripts/validate-citations.sh`) runs unchanged over the selector-mode findings, dropping any finding whose `rule_id` is not in `rules/index.json`.
8. The Step 5 report includes a traceability section listing each classify skip-reason as `rule_id → one-line reason`.

## Constraints

- Markdown-only plugin repo: edits are confined to `commands/pr-review.md`, `commands/code-review.md`, and a `## Unreleased` CHANGELOG.md bullet. No Go, no script changes, no new scripts.
- The jq glob pre-filter (Step 4b-i) prose and behavior MUST NOT change — it is the candidate source and the structural guarantee that classify can only narrow.
- `scripts/validate-citations.sh` is invoked unchanged; its contract (drop findings whose `rule_id` is absent from `rules/index.json`) is frozen.
- The default (no-flag) Step 4 logic — early exit, 4.0 preflight, 4a runner, 4b-i jq, 4b-ii per-owner dispatch, timing instrumentation, 4c conventions, 4d citation — MUST remain byte-for-byte as today; selector mode is added alongside, not by editing the existing branch.
- The two command files' selector sections MUST stay siblings: same step numbering (4c-sel CLASSIFY, 4d-sel ADJUDICATE), same contracts, same short-circuit string, differing only where the files already differ (`REVIEW_DIR` worktree vs in-place `directory`, diff source).
- `docs/dod.md` is the repo's Definition-of-Done gate; the implementation must satisfy it (CHANGELOG `## Unreleased` entry present; no personal paths introduced; `coding:` prefix on any agent reference).
- Severity vocabulary is the files' existing report buckets — **Must Fix (Critical) / Should Fix (Important) / Nice to Have (Optional)**. Do not introduce new severity names. For AC1's golden comparison apply the deterministic map Critical↔`critical`, Important↔`major`, Optional↔`nit` (the golden JSON uses the bot's verdict schema vocabulary).
- Architecture source-of-truth (schemas, step contracts, v3 amendments) lives in `~/Documents/Obsidian/Personal/50 Knowledge Base/AI-Selector Review Redesign.md` (migration Step 1); the golden baseline is `~/Documents/Obsidian/Personal/50 Knowledge Base/attachments/golden-legacy-verdict.json`.

## Failure Modes

| Trigger | Expected behavior | Recovery | Detection |
|---------|-------------------|----------|-----------|
| Mechanical funnel (`ast-grep-runner.sh`) missing/fails in selector mode | Same as today: note "mechanical funnel unavailable" and proceed to classify with judgment-rule candidates only | Re-run with toolchain present | Report line "mechanical funnel unavailable" |
| jq glob match (4b-i) yields empty candidate set AND mechanical findings empty | Short-circuit: report `selector clean — no adjudication needed`, skip to Step 5 | None needed — clean diff | Literal short-circuit string in report |
| Classify attempts to add a rule absent from the candidate set | Forbidden by invariant — applicable MUST stay a subset; the extra rule is dropped | Operator re-reads traceability section; invariant holds structurally | Report shows applicable count ≤ candidate count; every applicable id is in candidate list |
| Applicable set > 20 rules | Adjudication splits into 2-3 thematic in-session passes, zero spawns | None — batching is automatic | Report shows multiple adjudication passes, no `subagent_type` events |
| Adjudicate emits a finding citing a `rule_id` absent from `rules/index.json` | `validate-citations.sh` drops it; dispatcher logs the offender to stderr and continues with the validated subset | Author the missing rule block (separate backlog) | validate-citations.sh stderr log; finding absent from final report |
| Diff exceeds context budget on a mega-PR | Adjudicate consumes the diff truncated to changed-files-only (vendor/node_modules already excluded at Step 0c) | Re-run full mode for an exhaustive sweep | Report notes truncation |

## Security / Abuse Cases

Not user-facing input — the dispatcher operates on a diff already fetched into a controlled worktree, and the candidate set is bounded by the deterministic jq glob match. The only trust boundary is the LLM's adjudication output, which `validate-citations.sh` already gates against `rules/index.json` (hallucinated `rule_id`s are dropped). The narrowing invariant (`applicable ⊆ candidates`) structurally prevents the classify turn from injecting rules outside the deterministic pre-filter. No new attacker-controllable surface is introduced.

## Acceptance Criteria

- [ ] AC1: `--selector` mode on the bborbe/maintainer#2 fixture surfaces all 13 golden rule_ids at matching severities (the `go-library/semver-vprefix-tag-required` anomaly may be excluded when the clone carries tags) — evidence: selector run findings diffed against `golden-legacy-verdict.json` per rule_id; every golden rule_id present at its golden severity.
- [ ] AC2: zero Task/sub-agent spawns occur in `--selector` mode — evidence: session transcript / stdout contains no `tool_use` block whose `subagent_type` starts with `coding:` (`grep '"subagent_type"' <transcript>` returns no `coding:*` lines).
- [ ] AC3: default mode (no flag) behavior unchanged — evidence: `make check-acceptance` exits 0 with scenarios 002 and 004 assertions holding verbatim; `git diff` shows no edits to any `scenarios/*.md` file.
- [ ] AC4: classify respects the narrowing invariant — evidence: the Step 5 traceability/report shows a candidate count and an applicable count with candidate ≥ applicable, and every applicable rule_id also appears in the Step 4b-i candidate list.
- [ ] AC5: `make precommit` exits 0 (check-links, check-json, check-index, check-coverage, check-acceptance all green) — evidence: exit code 0.
- [ ] AC6: both `commands/pr-review.md` and `commands/code-review.md` define a `--selector` mode with Step 4c-sel CLASSIFY and Step 4d-sel ADJUDICATE and the literal short-circuit `selector clean — no adjudication needed` — evidence: `grep -n -- '--selector' commands/pr-review.md commands/code-review.md` and `grep -n 'selector clean — no adjudication needed' commands/pr-review.md commands/code-review.md` each return ≥1 line per file.
- [ ] AC7: CHANGELOG.md has a `## Unreleased` bullet describing the selector mode — evidence: `grep -n -A20 '## Unreleased' CHANGELOG.md` shows a bullet mentioning `--selector`.
- [ ] AC8: classify actually narrows on the fixture (anti-no-op guard) — evidence: on the bborbe/maintainer#2 walk, the Step 5 traceability section contains ≥1 `rule_id → skip-reason` entry and the candidate count strictly exceeds the applicable count. (The legacy golden shows 31 glob-matched judgment rules but only ~13 findings-relevant ones — a working classify must skip at least one candidate with a reason.)

Scenario coverage: NO new scenario. The behavior is reachable by the existing acceptance harness plus a manual fixture walk; default-mode regression is already locked by scenarios 002/004, which AC3 keeps green. Adding an E2E scenario for the opt-in path is premature before the default flips (a later migration step explicitly owns the 002/004 rewrites).

## Verification

```
make precommit
grep -n -- '--selector' commands/pr-review.md commands/code-review.md
grep -n 'selector clean — no adjudication needed' commands/pr-review.md commands/code-review.md
grep -n -A20 '## Unreleased' CHANGELOG.md
```

Expected: `make precommit` exits 0; both greps over the command files return ≥1 line per file; the CHANGELOG grep shows an Unreleased bullet naming `--selector`. Manual fixture walk on bborbe/maintainer#2 confirms AC1, AC2, AC4 against `golden-legacy-verdict.json`.

## Suggested Decomposition

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Add `--selector` mode + Step 4c CLASSIFY + Step 4d ADJUDICATE to `commands/pr-review.md` (mode parse, candidate reuse, classify contract, architecture bypass, short-circuit, adjudicate rule-block read + batching, citation reuse, traceability) + CHANGELOG Unreleased bullet | 1-8 | AC2, AC4, AC6, AC7 | — |
| 2 | Mirror the identical selector section into `commands/code-review.md` as a sibling (same step numbers, contracts, short-circuit string; adapt only `directory`/in-place diff source) | 1-8 | AC6 | prompt 1 |
| 3 | Fixture validation walk on bborbe/maintainer#2 vs `golden-legacy-verdict.json` + full precommit/acceptance gate | — | AC1, AC3, AC5 | prompts 1-2 |

Rationale: prompt 1 establishes the canonical selector prose in pr-review.md; prompt 2 copies it verbatim into the sibling so they cannot drift; prompt 3 validates against the frozen golden and confirms the default path did not regress. Ordering avoids two prompts editing overlapping prose, and keeps the sibling-consistency constraint enforceable by diffing prompt 2's output against prompt 1's.

## Do-Nothing Option

If we don't do this, per-owner Task fanout remains the only review path: wall-time stays coupled to rule count (~40 min on a standard 8-owner Go PR, growing as the rule base grows toward 120+), and the bot pays 2 + N calls per PR. The current path is correct and acceptable for now — that's why this ships flagged and default-OFF — but it is the bottleneck the redesign exists to remove. Shipping Step 1 behind a flag is the lowest-risk way to validate the in-session path against the golden before flipping the default in a later step.
