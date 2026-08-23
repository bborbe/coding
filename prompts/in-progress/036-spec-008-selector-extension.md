---
status: approved
spec: [008-security-review-pipeline]
created: "2026-08-23T10:30:00Z"
queued: "2026-08-23T08:26:14Z"
branch: dark-factory/security-review-pipeline
---

# Add the dormant security extension to the selector mode guide

<summary>
- Extends the selector mode guide with a dormant security layer that activates only when a future security-review signal is present — no command sets that signal yet, so the extension cannot fire in production
- Names exactly six security trait groups for classifier selection and makes `authz` over-selection non-negotiable on resource-handler diffs
- Makes invariant selection fully deterministic — a diff touching an invariant's attack surface forces that invariant into the applicable set, with no LLM judgment
- Extends the adjudicate step's input with the diff-relevant security model subset, the applicable invariants and their evidence authorization functions, and the attack-surface inventory as a drift signal
- Keeps every existing selector-mode step, the hard narrowing invariant, and the traceability section byte-identical — the extension is purely additive and section-local
- Adds no command wiring and no rule headings, so the rule index stays at 171 and the acceptance suite stays green
</summary>

<objective>
Extend the selector mode guide's classify/adjudicate contract with the security model consumption layer — six trait groups, non-negotiable `authz` over-selection, deterministic invariant selection, and the adjudicator input extension — documented as dormant until task 4 sets the security-review signal. The extension must be purely additive: it must not renumber or restructure the existing `4c-sel`/`4d-sel` steps, the HARD INVARIANT, or the traceability section.
</objective>

<context>
Read `CLAUDE.md` (repo root) — conventions for editing `docs/` (generic examples only, reference related guides with relative links).

Read `docs/selector-mode-guide.md` (full) — the file to extend. Note the exact section headings and their order: `## Step 4c-sel: CLASSIFY (in-session, no Task spawn)`, `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)`, `## Traceability Report Section`. Note the `HARD INVARIANT` sentence inside Step 4c-sel and the verbatim recall-contract sentence `"INCLUDE if a reasonable reviewer would want to read this rule before judging..."` containing `When uncertain, include.`. **Sibling-spec coordination (frozen):** `specs/selector-mode-classify-adjudicate.md` also owns this file's structure. The extension MUST NOT renumber or restructure these steps, the HARD INVARIANT, or the traceability section — insert only new content.

Read `docs/security/security-review-pipeline.md` (full — created by prompt 1 of this spec) — the derivation contract this extension consumes: model fields (`entry_points`, `resources[].authorization_functions`, `invariants[]` with `id`/`evidence`/`attack_surfaces`), the freshness gate, diff-relevant truncation, and the attack-surface inventory drift bridge. The extension references this guide as the model source.

Read `docs/security/security-review-guide.md` (skim the RULE ids) — the mechanical rules whose finding ids the `crypto`/`secrets` selection references (`go-security/crypto-*`, `go-security/hardcoded-secret`).

Read `scripts/build-index.py` — why the extended guide must not gain any `### RULE` heading (the walker scans `docs/*.md`; a heading breaks `check-index` at 171).

Read `scripts/acceptance.sh` (the `=== 5/5 Selector mode contracts ===` section) — the check-acceptance assertions on `docs/selector-mode-guide.md` (Step 4c-sel / Step 4d-sel presence, the verbatim recall contract sentence) that must stay green after the extension.
</context>

<requirements>
1. Insert a new section titled `## Security Extension (dormant)` immediately BEFORE the existing `## Traceability Report Section` heading in `docs/selector-mode-guide.md`. This is the ONLY structural change: do not modify, move, delete, or renumber any existing line, heading, step, sentence, or the `## Inputs` table. The existing `Step 4c-sel`, `Step 4d-sel`, the HARD INVARIANT sentence, the short-circuit, the architecture-tier bypass, and the Traceability section remain byte-identical.

2. In the new section, first state the activation contract: the security extension is active **only when the current review session carries the security-review signal**; no command sets that signal yet (task 4's command wiring does), so the extension is **dormant** — documented now as the classify/adjudicate contract. When the signal is absent, the procedure runs byte-for-byte as the existing 4c-sel/4d-sel steps and this section is inert. Do NOT reference or modify any `commands/*.md` to set the signal.

3. **Classifier sub-step — security trait groups.** Specify that, under the signal, security-relevant selection is grouped into exactly six trait groups: `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. Specify the **non-negotiable over-selection** rule for `authz`: any diff touching a resource handler — a diff that changes a file cited as evidence by an entry point operating on a modeled resource, or a file cited as evidence by a modeled resource's `authorization_function` — MUST select the `authz` group; a missed authz rule is worse than an extra evaluation. Specify `crypto` and `secrets` selection: they are selected when the corresponding mechanical findings (`go-security/crypto-*`, `go-security/hardcoded-secret`) are present in the Step 4a output, or the diff changes a file that imports `crypto/*`/`hash/*` or calls a crypto/secret-handling function. State that the applicable set remains a subset of the Step 4b-i candidate set — the HARD INVARIANT above still holds.

4. **Deterministic invariant selection.** Specify that invariants come from the security model derived per `docs/security/security-review-pipeline.md`; each has an `id`, `evidence`, and `attack_surfaces`. Specify the deterministic rule with no LLM judgment: if the diff changes the evidence file of any entry point whose path appears in an invariant's `attack_surfaces`, OR the diff changes the invariant's own evidence source, that `invariant_id` is in the applicable set. State that invariants behave like the architecture-tier bypass — always considered when their attack surface is touched, never subject to a skip decision.

5. **Adjudicator input extension.** Specify that, under the signal, the Step 4d-sel ADJUDICATE input additionally gains: the diff-relevant security model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal (per `docs/security/security-review-pipeline.md`). Specify that each applicable invariant is judged against the diff slice with the single question: does this change preserve the invariant? Specify that invariant-kind findings cite `invariant_id` (the polymorphic finding contract) and that validation of those IDs is task 3 — NOT implemented in this change.

6. Use generic examples only (User, Order, Product, Customer) in any example prose. Do NOT add any `### RULE` heading to `docs/selector-mode-guide.md` (the `## Security Extension (dormant)` heading and any `###` sub-headings inside it must not be `### RULE ...` headings).

7. Do NOT touch: any `commands/*.md`, `scripts/validate-citations.sh`, any `agents/*.md`, `rules/security/*.yml`, `rules/index.json`, `scripts/build-index.py`, `docs/security/security-review-pipeline.md` (prompt 1 owns it), `CHANGELOG.md` (prompt 1 owns the `## Unreleased` entry; the state-based changelog rule stays satisfied because that bullet is already under `## Unreleased`).
8. **Hard dependency guard:** this prompt depends on prompt 1 having shipped `docs/security/security-review-pipeline.md`. If that file does not exist when this prompt runs, STOP and report that prompt 1 must execute first — do NOT invent or fabricate the derivation contract (the model fields, freshness gate, truncation, and drift bridge are frozen in that guide).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git; do NOT run `git` commands (git-based evidence, AC9 `git status` and AC10 walk, runs on the operator side of the spec's Verification ladder).
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt (including `check-acceptance`, which asserts the existing selector-mode guide content).
- Trait groups (frozen): exactly `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. Over-selection for `authz` is non-negotiable on resource-handler diffs.
- Invariant selection (frozen): deterministic — the diff touches any entry point in an invariant's `attack_surfaces`, or the invariant's own evidence source, → that `invariant_id` is applicable. No LLM judgment on invariant selection.
- Dormant extension (frozen): gated on a security-review signal that no command sets until task 4. This prompt does NOT wire commands, does NOT modify any `commands/*.md`, and does NOT add a `--security` flag.
- Sibling-spec coordination (frozen): `specs/selector-mode-classify-adjudicate.md` also edits `docs/selector-mode-guide.md`. This extension is additive and section-local — it MUST NOT renumber or restructure the existing `4c-sel`/`4d-sel` steps, the HARD INVARIANT, or the traceability section.
- `docs/selector-mode-guide.md` contains ZERO `### RULE` headings — `scripts/build-index.py` walks `docs/*.md` and a heading breaks `check-index` at 171.
- No new search infrastructure, no config knobs, opt-out flags, or tunable thresholds.
- Generic examples only (User, Order, Product, Customer) — never trading terms; no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin. No version-existence claims.
- CHANGELOG.md is NOT touched by this prompt (prompt 1 owns the `## Unreleased` bullet); four version strings NOT touched.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — `.git` is masked).
```bash
# --- Hard dependency guard: prompt 1 must have shipped the pipeline guide ---
test -f docs/security/security-review-pipeline.md && echo "prompt 1 deliverable present: ok" || { echo "ERROR: prompt 1 must execute first — do not invent the derivation contract"; exit 1; }

# --- AC5: six trait groups + authz over-selection ---
for g in authz input-origin data-to-sink external-io crypto secrets; do
  n=$(grep -c "$g" docs/selector-mode-guide.md); echo "$g: $n"; [ "$n" -ge 1 ]   # each must return >= 1
done
grep -n 'over-select' docs/selector-mode-guide.md                              # must return >= 1

# --- AC6: deterministic invariant selection ---
grep -n 'attack_surfaces' docs/selector-mode-guide.md                          # must return >= 1
grep -n 'invariant_id' docs/selector-mode-guide.md                             # must return >= 1

# --- AC7: adjudicator input extension ---
n=$(grep -c 'invariant' docs/selector-mode-guide.md); echo "invariant: $n"      # must return >= 2
grep -n 'attack-surface inventory' docs/selector-mode-guide.md                 # must return >= 1

# --- Structure lock: existing sections untouched (no renumbering) ---
grep -n 'Step 4c-sel' docs/selector-mode-guide.md                              # must return >= 1
grep -n 'Step 4d-sel' docs/selector-mode-guide.md                              # must return >= 1
grep -n 'HARD INVARIANT' docs/selector-mode-guide.md                           # must return >= 1
grep -nF 'When uncertain, include.' docs/selector-mode-guide.md                # must return >= 1 (check-acceptance)
grep -n 'Traceability' docs/selector-mode-guide.md                             # must return >= 1

# --- No RULE headings; no commands/validator touched (violation is loud) ---
grep -c '^### RULE ' docs/selector-mode-guide.md                               # must return 0
if grep -rnq 'invariant_id\|security trait group\|Security Extension' commands/ scripts/validate-citations.sh 2>/dev/null; then echo "VIOLATION: security extension leaked into commands/ or validator"; else echo "ok: no security extension in commands/ or validator"; fi

# --- Rule base untouched ---
python3 scripts/build-index.py | jq length                                     # must return 171
grep -c '^### RULE go-security/' docs/security/security-review-guide.md        # must return 5

# --- Full precommit ---
make precommit                                                                 # must exit 0
```
</verification>

<!-- OPEN QUESTION for the human reviewer: sibling-spec timing. `specs/selector-mode-classify-adjudicate.md` is still `status: draft` at the specs/ root, yet `docs/selector-mode-guide.md` already carries the full 4c-sel/4d-sel content. This extension is written against the guide's CURRENT structure (insertion point: immediately before the `## Traceability Report Section`). If that sibling spec later restructures the guide, this prompt's insertion point and byte-identical guarantees must be re-based. Approve/execute this prompt only after (or in coordination with) the sibling spec's edits, per the spec's frozen Sibling-spec coordination constraint. -->
