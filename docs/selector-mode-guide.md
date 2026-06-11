## Selector Mode — Classify and Adjudicate Procedure

Selector mode replaces Step 4b-ii's per-owner Task dispatch with two in-session steps that run in the calling command's session. Steps 4.0, 4a, and 4b-i run unchanged and produce the candidate set. The design goal is zero sub-agent spawns: every rule is evaluated inside the current session context rather than cold-starting one sub-agent per owner.

Selector mode is opt-in (`--selector`/`selector` mode token); the default per-owner dispatch path is unchanged.

## Inputs

| Input | Description |
|-------|-------------|
| `DIFF` | The full diff for this review (caller-provided; see note below) |
| `CANDIDATES` | The `<rule-id> <owner>` list produced by Step 4b-i jq glob output |
| `MECHANICAL_FINDINGS` | Path to the Step 4a runner output JSON (e.g. `/tmp/pr-review-findings.json`) |
| Working directory | The directory under review (caller-provided) |

**Diff source differs per caller**: `commands/pr-review.md` uses the Step 0c worktree diff (`git diff origin/<TARGET_BRANCH>...HEAD`); `commands/code-review.md` uses `git diff HEAD~1` (or directory diff as parsed in Step 1).

## Step 4c-sel: CLASSIFY (in-session, no Task spawn)

**Input**: `DIFF`, the `CANDIDATES` list, and the `applies_when` text for each candidate from `rules/index.json`.

For each candidate rule, decide: **applicable** or **skipped** with a one-line reason (≤ 8 words).

**Recall contract (embed verbatim)**: "INCLUDE if a reasonable reviewer would want to read this rule before judging. Do not evaluate compliance. Do not evaluate violations. When uncertain, include."

**Skip justification rule**: a skip decision MUST be justified against the rule's `applies_when` text itself — the reason states why the `applies_when` condition does not hold for this diff. NEVER infer a rule's scope from its rule-id name or prefix (e.g. `go-testing/*` rules are NOT necessarily scoped to test files — read the `applies_when`). If the diff plausibly matches the `applies_when` condition, the rule is applicable.

**HARD INVARIANT**: the applicable set MUST be a subset of the candidate set. Every applicable rule_id must appear in the Step 4b-i candidate list. Never add a rule the glob did not produce.

**Architecture-tier bypass**: any candidate rule whose `enforcement` text contains "architecture" OR whose `doc_path` is `go-architecture-patterns.md` and concerns SRP/layering is unconditionally applicable — do not classify, always include it.

**Short-circuit**: if the applicable set is empty AND the mechanical findings from Step 4a are also empty, report:

> `selector clean — no adjudication needed`

and skip Step 4d-sel, proceeding directly to Step 5. Include the candidate count and a note that all candidates were classified as non-applicable in the Step 5 traceability section.

Produce a classify result:
```json
{
  "applicable": ["<rule-id>", "..."],
  "skipped": {
    "<rule-id>": "<one-line reason ≤ 8 words>",
    "...": "..."
  }
}
```

## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)

**Input**: the full diff (no truncation — this is the load-bearing step), the mechanical findings from `MECHANICAL_FINDINGS`, and the applicable rules from Step 4c-sel.

For each applicable rule: locate the rule's `doc_path` in `rules/index.json`, then read only the matching `### RULE <id>` block from that file (grep for the heading, read the block — do not read the whole document).

Judge the full diff plus mechanical findings. For each violation found, emit a finding that cites `rule_id` + file + line and lands in the existing report buckets:

- **Must Fix (Critical)** — security, context violations, concurrency bugs, data correctness, SRP (3+ concerns)
- **Should Fix (Important)** — architectural violations, error handling, factory/handler patterns, test gaps
- **Nice to Have (Optional)** — style, naming, minor version issues

Do not emit a per-rule "passed" entry for rules with no violation — silently omit them.

**Batching**: if the applicable set exceeds 20 rules, split adjudication into 2–3 thematic in-session passes (e.g. architecture rules first, then quality rules, then style rules). Each pass runs in the current session — still zero Task spawns. Collect all findings before proceeding to citation validation.

**Citation validation** (invoked directly — selector mode spawns NO sub-agents, including `coding:simple-bash-runner`): run the validator as a plain Bash call over the adjudication findings before consolidation — findings citing a `rule_id` absent from `rules/index.json` are dropped and logged to stderr. Resolve the script path via the plugin install chain (the working directory may not be the plugin checkout):

```bash
VALIDATOR="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/validate-citations.sh"
[ -x "$VALIDATOR" ] || VALIDATOR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/scripts/validate-citations.sh"
bash "$VALIDATOR" <findings.json>
```

## Traceability Report Section

Include this section in the Step 5 report only when the review ran in selector mode. List counts and every classify skip so operators can spot false drops:

- **Candidates**: `<N>` rules matched by Step 4b-i glob filter
- **Applicable**: `<M>` rules selected by Step 4c-sel (M ≤ N)
- **Skipped** (one line each):
  - `<rule-id>` → `<one-line reason>`
  - …
