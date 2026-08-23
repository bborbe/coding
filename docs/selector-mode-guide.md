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

## Security Extension (dormant)

The security model consumption layer extends the classify/adjudicate contract. It is **active only when the current review session carries the security-review signal**. No command sets that signal yet — task 4's command wiring does — so this extension is **dormant**: it is documented now as the classify/adjudicate contract that the steps below will honor once the signal exists. When the signal is absent, the procedure runs byte-for-byte as the existing Step 4c-sel / Step 4d-sel steps above and this section is inert.

The security model this extension consumes is derived per [security-review-pipeline.md](security/security-review-pipeline.md); the model fields (`entry_points`, `resources[].authorization_functions`, `invariants[]`), the freshness gate, diff-relevant truncation, and the attack-surface inventory drift bridge are frozen there.

### Classifier sub-step — security trait groups

Under the signal, security-relevant selection is grouped into exactly six trait groups: `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. Selecting a trait group selects the security rules in its scope; the groups are how the deterministic drift bridge (see the pipeline guide) and the classifier's judgment both contribute to the applicable set.

**Non-negotiable `authz` over-selection**: any diff touching a resource handler — a diff that changes a file cited as evidence by an entry point operating on a modeled resource, or a file cited as evidence by a modeled resource's `authorization_function` — MUST select the `authz` group. A missed authz rule is worse than an extra evaluation: over-selecting `authz` costs one extra rule read, while under-selecting it can ship an authorization regression unexamined. Example: a diff touching `pkg/handler/order.go` — a file cited as evidence by an entry point that operates on the modeled `order` resource — selects `authz` even when the changed lines look cosmetic.

**`crypto` and `secrets` selection**: the `crypto` group is selected when `go-security/crypto-*` findings are present in the Step 4a output, or the diff changes a file that imports `crypto/*`/`hash/*` or calls a crypto-handling function. The `secrets` group is selected when `go-security/hardcoded-secret` findings are present in the Step 4a output, or the diff changes a file that calls a secret-handling function. The mechanical findings referenced are `go-security/crypto-insecure-random`, `go-security/crypto-weak-algorithm`, and `go-security/hardcoded-secret` from [security-review-guide.md](security/security-review-guide.md).

The applicable set remains a subset of the Step 4b-i candidate set — the HARD INVARIANT above still holds. Trait groups never add a rule the Step 4b-i glob did not produce.

### Deterministic invariant selection

Invariants come from the security model derived per [security-review-pipeline.md](security/security-review-pipeline.md); each invariant carries an `id`, `evidence`, and `attack_surfaces`. Invariant selection is fully deterministic — no LLM judgment:

- if the diff changes the evidence file of any entry point whose path appears in an invariant's `attack_surfaces`, OR
- the diff changes the invariant's own `evidence` source,

then that `invariant_id` is in the applicable set. Example: for an invariant `INV-1` (`a member may only read orders they own`) whose `attack_surfaces` includes the path of an entry point's evidence file, any diff changing that evidence file forces `INV-1` into the applicable set.

Invariants behave like the architecture-tier bypass above — always considered when their attack surface is touched, never subject to a skip decision.

### Adjudicator input extension

Under the signal, the Step 4d-sel ADJUDICATE input additionally gains:

- the diff-relevant security model subset (per the pipeline guide's freshness gate and diff-relevant truncation),
- the applicable invariants with their evidence authorization functions, and
- the attack-surface inventory as a drift signal (per [security-review-pipeline.md](security/security-review-pipeline.md)).

Each applicable invariant is judged against the diff slice with the single question: does this change preserve the invariant? Invariant-kind findings cite `invariant_id` (the polymorphic finding contract); under the signal those ids are validated by `scripts/validate-citations.sh` against the session's security model (see the polymorphic finding contract below).

### Verifier gate (post-adjudication, pre-emission)

Under the signal, a verifier gate runs between the Step 4d-sel adjudication output and emission. It is a **hard pre-emission step** for `severity=critical` findings and for `severity=major` findings when `confidence=confirmed` — a high-severity finding cannot emit without passing this gate. Every surviving high-severity finding carries a populated `counterevidence_checked` field.

The verdict contract is produced by [security-verifier.md](../agents/security-verifier.md): each candidate resolves to `confirmed | plausible | rejected` with the fields `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, and `counterevidence_checked` (`reject_reason` is required on rejection). The verifier is **precision-control, not a proof** — a residual false positive is caught by the `ai_review` post-post backstop: **dismiss + COMMENT + human_review**. `dismiss` drops the finding from the report, `COMMENT` records it in the traceability section for the operator, and `human_review` flags it for a human. That backstop is the remaining safety net for anything the gate misses.

### Blocking model (orthogonal to severity)

Under the signal, merge blocking is derived from the verifier verdict, orthogonal to severity:

`blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`

Blocking never consults the finding's `severity` label. A `plausible` critical does NOT block merge — it is reported as a required human review item instead of a merge block. Only a fully confirmed, high-exploitability, medium-or-higher-impact finding blocks.

Per-surface thresholds (documented contract, not executable knobs):

| Surface | v1 default |
|---------|-----------|
| `local` | `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` |
| `bot` | `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` |
| `audit` | `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` |

The uniform v1 default for all three surfaces is the formula itself; tuning after real usage is a separate task and is explicitly deferred. No per-surface configuration exists yet — this table is a documented contract, not executable configuration; there are no config fields and no opt-out flags.

### Polymorphic finding contract (three kinds)

Under the signal, each finding resolves exactly one provenance, chosen by its `kind` field:

| `kind` | Provenance | Resolution |
|--------|------------|-----------|
| `rule` | `rule_id` | resolves in `rules/index.json` |
| `invariant` | `invariant_id` | resolves in the model's `invariants[].id` (per [security-review-pipeline.md](security/security-review-pipeline.md)) |
| `toolchain` | no id — tool output | kept by the validator as-is |

Toolchain findings (gosec/trivy/osv-scanner/vulncheck) are tool output, not rule violations — they carry no `rule_id` and are kept without id validation. A finding with no `kind` field is treated as `rule` (legacy path).

**Validator role under the signal**: the Step 4d-sel citation-validation invocation passes `SECURITY_MODEL_FILE` pointing at the session's security model, so invariant findings resolve against the model's `invariants[].id`. Absent the model — unset, missing, unreadable, or unparseable — invariant findings drop **fail-closed** with a WARN to stderr and are never kept. `scripts/validate-citations.sh` is the enforcing mechanism; any other `kind` value is dropped as unprovenanced.

## Traceability Report Section

Include this section in the Step 5 report only when the review ran in selector mode. List counts and every classify skip so operators can spot false drops:

- **Candidates**: `<N>` rules matched by Step 4b-i glob filter
- **Applicable**: `<M>` rules selected by Step 4c-sel (M ≤ N)
- **Skipped** (one line each):
  - `<rule-id>` → `<one-line reason>`
  - …
