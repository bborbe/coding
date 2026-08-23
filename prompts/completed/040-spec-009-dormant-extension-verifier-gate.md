---
status: completed
spec: [009-security-verifier-citations]
summary: Extended the dormant Security Extension in docs/selector-mode-guide.md with the verifier gate, the severity-orthogonal blocking model plus per-surface thresholds table, and the three-kind polymorphic finding contract; reworded the stale task-3 sentence to reference validate-citations.sh.
execution_id: coding-security-verifier-exec-040-spec-009-dormant-extension-verifier-gate
dark-factory-version: dev
created: "2026-08-23T10:01:50Z"
queued: "2026-08-23T10:26:48Z"
started: "2026-08-23T10:26:50Z"
completed: "2026-08-23T10:28:18Z"
branch: dark-factory/security-verifier-citations
---

# Extend the dormant Security Extension with the verifier gate and blocking model

<summary>
- The dormant security layer in the selector-mode guide gains a post-adjudication verifier gate, documented as a hard pre-emission step for critical findings and confirmed majors
- Every surviving high-severity finding must carry the checked-counterevidence field, and the AI-review backstop is documented as the remaining safety net
- The blocking model is documented orthogonal to severity with the exact formula, and a plausible critical is explicitly a required human review item, not a merge block
- A per-surface thresholds table names the local, bot, and audit surfaces with a uniform untuned default and tuning deferred
- The polymorphic finding contract is extended to three kinds, and the validator's role under the signal is documented — invariant ids now resolve against the model, and a missing model drops them fail-closed
- The guide's frozen step headings and step bodies stay byte-identical; the change is additive and section-local within the dormant extension
- No rule headings, no command wiring, no new knobs — the thresholds table ships as a documented contract, not executable configuration
</summary>

<objective>
Extend the existing dormant `## Security Extension (dormant)` section in `docs/selector-mode-guide.md` with the verifier gate, the severity-orthogonal blocking model plus per-surface thresholds table, and the three-kind polymorphic finding contract — documented now so the layer is fully specified and active the moment a command sets the security-review signal (task 4).
</objective>

<context>
Read `CLAUDE.md` (repo root) — conventions for editing `docs/` (generic examples only, reference related guides with relative links).

Read `docs/selector-mode-guide.md` (full) — the file to extend. Note the exact section headings and order: `## Step 4c-sel: CLASSIFY (in-session, no Task spawn)` (~line 18), `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)` (~line 49), `## Security Extension (dormant)` (~line 73) with its three `###` sub-sections (`Classifier sub-step — security trait groups`, `Deterministic invariant selection`, `Adjudicator input extension`), then `## Traceability Report Section` (~line 110). The `### Adjudicator input extension` sub-section ends with the sentence: `Invariant-kind findings cite \`invariant_id\` (the polymorphic finding contract); validation of those ids is task 3 — NOT implemented in this change.` — this prompt updates that single sentence and adds new sub-sections; everything else in the dormant extension and the entire Step 4c-sel / Step 4d-sel / Traceability content stays byte-identical.

Read `agents/security-verifier.md` (full — created by prompt 2 of this spec) — the verdict contract this gate documents as its upstream producer (`confirmed | plausible | rejected`, `counterevidence_checked`, `reject_reason`).

Read `docs/security/security-review-pipeline.md` (the `Model schema and lifecycle` section) — the model source the validator resolves `invariant_id` against (`invariants[].id`).

Read `scripts/validate-citations.sh` (full — extended by prompt 1 of this spec) — the validator's polymorphic behavior this section documents: `SECURITY_MODEL_FILE` env var, `kind` resolution, fail-closed absent model.

Read `scripts/acceptance.sh` (the `=== 5/5 Selector mode contracts ===` section) — the `check-acceptance` assertions on `docs/selector-mode-guide.md` (Step 4c-sel / Step 4d-sel presence, the verbatim recall-contract sentence `When uncertain, include.`) that must stay green after this extension.

Read `scripts/build-index.py` — why the extended guide must not gain any `### RULE` heading (the walker scans `docs/*.md`; a heading breaks `check-index` at 171).
</context>

<requirements>
1. **Hard dependency guard.** This prompt depends on prompt 2 having shipped `agents/security-verifier.md`. If that file does not exist when this prompt runs, STOP and report that prompt 2 must execute first — do NOT invent or fabricate the verdict contract (the verdict values, field set, and confirmation rule are frozen in that agent file).

2. **Structural rule.** The ONLY structural change to `docs/selector-mode-guide.md` is: (a) reword one pre-existing sentence inside the dormant `### Adjudicator input extension` sub-section (requirement 4), and (b) insert three new `###` sub-sections immediately after the `### Adjudicator input extension` content and immediately before the `## Traceability Report Section` heading. Do NOT modify, move, delete, or renumber any other existing line, heading, step, sentence, the `## Inputs` table, the HARD INVARIANT, the Step 4d-sel validator-invocation block, or the Traceability section — those remain byte-identical. The `## Step 4c-sel: CLASSIFY (in-session, no Task spawn)` and `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)` headings and their step bodies are frozen.

3. **Keep the activation contract.** Each new sub-section states explicitly that it is active ONLY when the current review session carries the security-review signal; no command sets that signal yet (task 4's command wiring does), so this extension remains **dormant** and inert when the signal is absent. Do NOT reference or modify any `commands/*.md` to set the signal.

4. **Reword one stale sentence.** In the `### Adjudicator input extension` sub-section, replace the sentence:
   `Invariant-kind findings cite \`invariant_id\` (the polymorphic finding contract); validation of those ids is task 3 — NOT implemented in this change.`
   with:
   `Invariant-kind findings cite \`invariant_id\` (the polymorphic finding contract); under the signal those ids are validated by \`scripts/validate-citations.sh\` against the session's security model (see the polymorphic finding contract below).`
   This is the only pre-existing sentence edited; it must read as the same sentence otherwise.

5. **New sub-section A — `### Verifier gate (post-adjudication, pre-emission)`.** Document, gated on the signal: the verifier gate runs between Step 4d-sel adjudication output and emission; it is a hard pre-emission step for `severity=critical` and for `severity=major` when `confidence=confirmed`; every surviving high-severity finding carries `counterevidence_checked`; the verdict contract (`confirmed | plausible | rejected` with `confidence`/`exploitability`/`impact`/`counterevidence_checked`) is produced by `agents/security-verifier.md`; and the `ai_review` post-post backstop — dismiss + COMMENT + human_review — is documented as the remaining safety net for any residual false positive (the verifier is precision-control, not a proof).

6. **New sub-section B — `### Blocking model (orthogonal to severity)`.** Document the formula verbatim: `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`. State that blocking is derived orthogonal to severity — a `plausible` critical does NOT block merge and is instead reported as a required human review item. Include a per-surface thresholds table naming exactly three surfaces — `local`, `bot`, `audit` — with the v1 uniform default for all three being the formula itself and per-surface tuning explicitly deferred ("tuning after real usage is a separate task"). State that the table is a documented contract, not executable knobs — no per-surface configuration exists yet.

7. **New sub-section C — `### Polymorphic finding contract (three kinds)`.** Document the three provenance kinds: `rule` → `rule_id` resolves in `rules/index.json`; `invariant` → `invariant_id` resolves in the model's `invariants[].id` (per `docs/security/security-review-pipeline.md`); `toolchain` → no id, tool-output, kept by the validator (gosec/trivy/osv-scanner/vulncheck findings are not rule violations). Document the validator's role under the signal: the citation-validation invocation passes `SECURITY_MODEL_FILE` pointing at the session's model; absent the model, invariant findings drop fail-closed with WARN (never kept). A finding with no `kind` field is treated as `rule` (legacy path). Reference `scripts/validate-citations.sh` by name as the enforcing mechanism.

8. Use generic examples only (User, Order, Product, Customer) in any example prose. Do NOT add any `### RULE` heading to `docs/selector-mode-guide.md` (the `## Security Extension (dormant)` heading and the new `###` sub-headings are NOT `### RULE ...` headings). The AC evidence strings this section must introduce (currently all absent from the file): `exploitability` (≥1), standalone `local`/`bot`/`audit` (≥3 total), `toolchain` (≥1), `pre-emission` and/or `counterevidence_checked` (≥1).

9. Do NOT touch: any `commands/*.md`, `scripts/validate-citations.sh`, `scripts/build-index.py`, any `agents/*.md`, `rules/security/*.yml`, `rules/index.json`, `docs/security/security-review-guide.md`, `docs/security/security-review-pipeline.md`, `README.md`, `llms.txt`, `CHANGELOG.md` (prompt 4 owns the changelog entry), `scenarios/*`, `CLAUDE.md`.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; git-based evidence (AC13 `git status --short` scope-lock) runs on the operator side of the spec's Verification ladder.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt (including `check-acceptance`, which asserts the existing selector-mode guide content).
- No renumbering (frozen): `docs/selector-mode-guide.md` `## Step 4c-sel` and `## Step 4d-sel` headings and their step bodies are byte-unchanged; the dormant Security Extension edit is additive and section-local.
- Dormant layer (frozen): nothing in this task sets the security-review signal or wires a command; no `commands/*.md` change. The gate/blocking/contract documentation is active only when the signal exists.
- Blocking model (frozen): `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`; a `plausible` critical does NOT block merge (reported as a required human review item); per-surface thresholds table names `local`, `bot`, `audit` with a uniform v1 default (the formula) and per-surface tuning deferred. The table is a documented contract, NOT executable knobs — do NOT introduce config fields or opt-out flags.
- Rule base frozen: no new `### RULE` blocks, `rules/security/*.yml` stays at exactly 5 files, `rules/index.json` byte-unchanged, no `scripts/build-index.py` change. `docs/selector-mode-guide.md` contains ZERO `### RULE` headings (a heading breaks `check-index` at 171).
- Model schema frozen: invariant ids resolve against `invariants[].id` exactly as documented in `docs/security/security-review-pipeline.md`.
- Generic examples only (User, Order, Product, Customer) — never trading terms; no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin. No version-existence claims.
- CHANGELOG.md is NOT touched by this prompt (prompt 4 owns the `## Unreleased` bullet).
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- Hard dependency guard: prompt 2 must have shipped the verifier agent ---
test -f agents/security-verifier.md && echo "prompt 2 deliverable present: ok" || { echo "ERROR: prompt 2 must execute first — do not invent the verdict contract"; exit 1; }

# --- AC8: blocking model + per-surface thresholds table ---
grep -n 'exploitability' docs/selector-mode-guide.md                               # must return >= 1
grep -nE '\b(local|bot|audit)\b' docs/selector-mode-guide.md                        # must return >= 3
grep -n 'confidence==confirmed' docs/selector-mode-guide.md                         # must return >= 1 (blocking formula)

# --- AC9: three kinds + verifier gate wired in the dormant layer ---
grep -n 'toolchain' docs/selector-mode-guide.md                                     # must return >= 1
grep -nE 'pre-emission|counterevidence_checked' docs/selector-mode-guide.md         # must return >= 1
grep -n 'ai_review' docs/selector-mode-guide.md                                     # must return >= 1 (backstop documented)

# --- Structure lock: existing sections untouched (no renumbering) ---
grep -n '^## Step 4c-sel: CLASSIFY (in-session, no Task spawn)' docs/selector-mode-guide.md   # must return a line with the exact baseline heading
grep -n '^## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)' docs/selector-mode-guide.md # must return a line with the exact baseline heading
grep -nF 'When uncertain, include.' docs/selector-mode-guide.md                      # must return >= 1 (check-acceptance)
grep -n 'Traceability' docs/selector-mode-guide.md                                  # must return >= 1
grep -n 'security-verifier' docs/selector-mode-guide.md                              # must return >= 1 (gate names its producer agent)

# --- No RULE headings; no commands/validator touched (violation is loud) ---
grep -c '^### RULE ' docs/selector-mode-guide.md                                    # must return 0
if grep -rnq 'SECURITY_MODEL_FILE\|verifier gate\|security-verifier' commands/ 2>/dev/null; then echo "VIOLATION: security extension leaked into commands/"; else echo "ok: no security extension in commands/"; fi

# --- Rule base untouched ---
python3 scripts/build-index.py | jq length                                          # must return 171
grep -c '^### RULE go-security/' docs/security/security-review-guide.md             # must return 5

# --- Full precommit ---
make precommit                                                                      # must exit 0
```
</verification>

<!-- OPEN QUESTION for the human reviewer: the sibling spec `specs/selector-mode-classify-adjudicate.md` is still `status: draft` at the specs/ root and also owns the structure of `docs/selector-mode-guide.md`. This extension is written against the guide's CURRENT structure (insertion point: immediately before `## Traceability Report Section`, inside the existing `## Security Extension (dormant)` section that spec-008 prompt 2 added). If that sibling spec later restructures the guide, this prompt's insertion point and byte-identical guarantees must be re-based. Approve/execute this prompt only in coordination with the sibling spec's edits, per the spec's frozen Sibling-spec coordination / No renumbering constraints. -->
