---
status: draft
spec: [010-security-review-command-wiring]
created: "2026-08-23T17:16:00Z"
branch: dark-factory/security-review-command-wiring
---

# Mirror --security into commands/code-review.md (audit mode)

<summary>
- The whole-codebase audit command accepts a `--security` flag that activates the same dormant security mode as the PR review command, adapted to audit scope
- In audit mode the security model is derived over the whole repo, security findings are NOT diff-anchored (whole-repo scope), and the recon, classifier, adjudicator, verifier, blocking, deps pass, and report sections mirror the canonical wiring from the PR review command
- The `Security Findings` section is a baseline-independent whole-repo inventory — it lists every security finding regardless of the baseline diff and the severity filter, which continue to govern only the normal severity buckets
- The command stays a thin wrapper — it replicates the proven security-mode section from the PR review command and references the frozen guides and agents by name
- The frozen security contract files are proven byte-unchanged, and existing selector / short / full / baseline behavior is untouched when the flag is absent
- The report gains a `Security Findings` section and a `Security Model` provenance block alongside the existing severity buckets and baseline traceability
</summary>

<objective>
Mirror the `--security` wiring from `commands/pr-review.md` (prompt 1's deliverable) into `commands/code-review.md` so the whole-repo audit can also run the full security pipeline — whole-repo recon and model, six trait groups with deterministic invariant selection, verifier-gated findings, derived blocking, a fail-closed deps pass, and the `Security Findings` + `Security Model` report sections — with audit-scope semantics (whole repo, no diff anchoring).
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "Command = Thin Wrapper" and "Plugin Namespacing" rules and the generic-content rule.

Read `commands/code-review.md` (full) — the file to edit. Note the structure you must preserve: frontmatter `argument-hint: "[short|full|selector] [directory] [--include-optional] [--refresh-baseline]"`, Step 0 argument parsing, Step 1 codebase walk, Step 2 project detection, Step 3 toolchain preflight, Step 4 mechanical funnel (whole codebase, `code-review-findings.json`), Step 5 adjudication (selector / full / short), Step 6 baseline diff, Step 7 severity filter + dedup, Step 8 `--refresh-baseline`, Step 9 consolidated report, Step 10 next steps, Constraints. This command is NOT covered by `scripts/acceptance.sh`, but preserve its content anyway.

Read `commands/pr-review.md` (the `#### Security mode (under \`--security\` only)` subsection inserted by prompt 1) — the canonical security-mode section you must replicate. It is the single source for the recon/classifier/adjudicator/verifier/blocking/deps-pass/citation-validation contract wording.

Read `docs/selector-mode-guide.md` (the dormant `## Security Extension (dormant)` section) — FROZEN; the command references it, never edits it.

Read `docs/security/security-review-pipeline.md` (full) — the recon procedure, model schema, freshness gate, diff-relevant truncation, attack-surface inventory drift bridge, report contract. FROZEN — reference, never re-document.

Read `agents/security-verifier.md` (full) — the 7-item falsification checklist and verdict contract. FROZEN.

Read `scripts/validate-citations.sh` (full) — the polymorphic validator (`SECURITY_MODEL_FILE`, `kind` resolution, fail-closed absent-model drop path). FROZEN.
</context>

<requirements>
1. **Hard dependency guard.** Verify prompt 1 shipped the canonical wiring before editing anything: `grep -n '#### Security mode (under \`--security\` only)' commands/pr-review.md` must return a line. If it does not, STOP and report that prompt 1 must execute first — do NOT invent an alternative security-mode shape (the report-section wording and the diff-anchoring rule must be consistent across all three commands).

2. **Record the frozen-contract baseline FIRST.** Before making any edit, run:
   `sha256sum docs/selector-mode-guide.md scripts/validate-citations.sh agents/security-verifier.md agents/go-security-specialist.md docs/security/security-review-pipeline.md docs/security/security-review-guide.md > /tmp/df010-frozen.sha256`
   Keep it for the AC6 check in `<verification>`. If any of the six files is missing, STOP and report the missing path.

3. **Flag parsing (AC2).**
   a. In the frontmatter, change the `argument-hint` line to: `argument-hint: "[short|full|selector] [directory] [--include-optional] [--refresh-baseline] [--security]"`.
   b. In Step 0 (Parse Arguments), add `--security` to the recognized boolean flags: when present, set `SECURITY_REVIEW=1`, independent of the mode token and the other flags (`--include-optional`, `--refresh-baseline`). The flag is never silently ignored — the security pipeline runs in-session over the reviewed scope regardless of mode token; the existing short-mode "skip Step 5 entirely" directive applies only to the non-security adjudication.
   c. Bind the `--security` × `--refresh-baseline` interaction: when `--refresh-baseline` is set, the command writes the current finding set to `.code-review-baseline.yaml` and exits WITHOUT a report (existing behavior, unchanged) — on such an invocation no security pipeline runs, because there is no review being performed; this is not a silent ignore of the flag, it is the maintenance-mode exit that produces no findings at all. State this in Step 0.

4. **Insert a new subsection — `#### Security mode (under \`--security\` only)`** — positioned immediately AFTER the Step 4 mechanical-funnel block (which ends with the sentence "The runner is scope-agnostic — it processes whatever file list it receives. We pass the whole codebase.") and immediately BEFORE the `## Step 5: Adjudication` heading. Replicate the canonical security-mode section from `commands/pr-review.md` (same wording and step structure for recon/model derivation, classifier trait groups, adjudicator inputs, verifier gate, blocking, deps pass, and citation validation), with these audit-scope adaptations:

   - **Scope and diff anchoring** — in audit mode the scope is the whole repo — no diff anchoring — and the recon derives a whole-repo model (AC5: the string `whole` must appear at least once; the literal phrase "the scope is the whole repo — no diff anchoring" is required). Do NOT include the PR-mode "diff-changed lines" gating rule from prompt 1; whole-repo findings are in scope regardless of the diff.
   - **Recon** — enumerate entry points and resolve identities / auth mechanisms / resources / invariants over the whole codebase (not the diff's touched packages), per `docs/security/security-review-pipeline.md`.
   - **Freshness gate** — unchanged-evidence entries carried forward, changed-evidence entries re-derived, stale entries dropped and surfaced with the literal `model refresh:` line; large-repo truncation noted in the report.
   - **Adjudicator inputs** — the Step 5 selector-mode adjudication (the same 4d-sel contract) gains the whole-repo model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal.
   - **Model path** — still `/tmp/security-model.json`, session-local, never inside the reviewed repo (mirror of `/tmp/code-review-findings.json`).
   - **Deps pass** — run over the whole-repo dependency manifests; fail-closed (scan failure, DB-fetch timeout, or flagged vulnerability → Must-Fix toolchain finding, never a silent skip).
   - **Citation validation** — the Step 5 citation-validation invocation passes `SECURITY_MODEL_FILE=/tmp/security-model.json`; invariant findings fail closed on an absent model.

   Each of the literal strings `security-model.json`, `/tmp/security-model.json`, `SECURITY_MODEL_FILE`, `security-verifier`, and `model refresh` must appear at least once in this subsection (AC3/AC4 evidence).

5. **Report sections (AC4).** In Step 9 (Consolidated Report), add under the signal: a `Security Findings` section listing every security finding (rule, invariant, and toolchain) with `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields, and derived blocking state; and a `Security Model` provenance block recording `derived_from` (repo, head, review_id), the entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. A whole-repo scope containing Go source always produces the Security Model block (never a silent skip); a scope with no Go source states `no Go source — security model not derived` explicitly. The normal severity buckets, the baseline traceability section, and the selector traceability section still appear. The literal strings `Security Findings`, `Security Model`, and `model refresh` must each appear at least once in the command (AC4 evidence).

   **Security Findings is a baseline-independent whole-repo inventory per the spec's report contract** — it lists every security finding regardless of the Step 6 baseline diff and Step 7 severity filter (the baseline and severity filter continue to govern only the normal severity buckets; `--include-optional` does not suppress a security finding); derived blocking applies to every listed security finding. Do not classify security findings into the baseline's NEW/CARRIED/FIXED buckets.

6. **Preserve existing behavior (no regression).** The existing Steps 0–10 and the Constraints section are preserved unchanged except the targeted additions in requirements 3–5 (the `--refresh-baseline` mode, the baseline diff, the severity filter + dedup, and the selector/full/short adjudication all keep working; the security mode runs in addition to them, never replacing them). Do NOT touch `commands/pr-review.md`, `commands/local-review.md`, any `docs/*`, `scripts/*`, `agents/*`, `rules/*`, `README.md`, `llms.txt`, `scenarios/*`, or `CHANGELOG.md` (sibling prompts own them).

7. **Dormant contract and shipped artifacts untouched (AC6).** Do not edit `docs/selector-mode-guide.md`, `scripts/validate-citations.sh`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, `docs/security/security-review-pipeline.md`, or `docs/security/security-review-guide.md` — the command only references them. No `### RULE` heading anywhere in your edit. Generic examples only (User, Order, Product, Customer); never trading/project-specific content; no personal paths.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; the git-based negative guard (AC6 `git diff origin/master` / `git status --porcelain`) runs on the operator side of the spec's Verification ladder — the container form is the checksum baseline in requirement 2.
- The `## Security Extension (dormant)` in `docs/selector-mode-guide.md` is the frozen classify/adjudicate contract: steps 4c-sel/4d-sel and the extension text MUST NOT be renumbered, rewritten, or edited; the `--security` wiring only sets the security-review signal that activates it, and when the signal is absent the existing procedure runs byte-for-byte.
- Shipped artifacts not re-authored: `docs/security/security-review-pipeline.md`, `docs/security/security-review-guide.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, and `scripts/validate-citations.sh` already exist and are NOT modified. No new security detection rules.
- Blocking: derived per `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`, never stored as severity; per-surface configurable thresholds are out of scope — no config fields, no opt-out flags.
- Finding provenance: exactly one of `rule_id ∈ rules/index.json`, `invariant_id ∈ derived model`, or `kind=toolchain` (no id). No new validation-script work.
- Model location: `security-model.json` is session-local under `/tmp`, never committed to any repo; if it is ever written inside the reviewed repo tree it is deleted and rewritten to the session-local path.
- Commands are thin wrappers: no inline rules; all agent references use the `coding:` prefix; the classify/adjudicate/verifier procedure is executed per the guides, not re-implemented in the command.
- HARD INVARIANT preserved: the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
- Selector-mode zero-sub-agent-spawn property preserved for the classify/adjudicate steps; the verifier execution mechanism is the only deviation point and is reversible (the session decides at review time).
- The `--security` mode must not bypass or soften the existing Step 3 toolchain preflight (ast-grep/sg fail-fast) or the Step 4 mechanical funnel.
- `--refresh-baseline` wins over `--security`: a baseline-refresh invocation writes the baseline and exits without a review, so no security pipeline runs on it (maintenance write, not a silent flag ignore).
- Audit scope is the whole tracked codebase as of HEAD (`git ls-files`), vendored/generated files always excluded — unchanged from the existing command constraints.
- Generic content only: fixtures and examples use User, Order, Product, Customer — never trading/project-specific content, never personal paths.
- Existing tests must still pass: `make precommit` (incl. `check-acceptance`) exits 0.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- AC1: repo integrity ---
make precommit    # must exit 0

# --- AC2: --security flag wired ---
grep -n -- '--security' commands/code-review.md               # >= 1
grep -n 'argument-hint:.*--security' commands/code-review.md  # >= 1

# --- AC3: security pipeline steps wired ---
grep -n 'security-model.json' commands/code-review.md         # >= 1
grep -n '/tmp/security-model.json' commands/code-review.md    # >= 1
grep -n 'SECURITY_MODEL_FILE' commands/code-review.md         # >= 1
grep -n 'security-verifier' commands/code-review.md           # >= 1

# --- AC4: report sections encoded ---
grep -n 'Security Findings' commands/code-review.md           # >= 1
grep -n 'Security Model' commands/code-review.md              # >= 1
grep -n 'model refresh' commands/code-review.md               # >= 1

# --- AC5: audit-mode whole-repo scope (no diff anchoring) ---
grep -n 'whole' commands/code-review.md                       # >= 1
grep -n 'no diff anchoring' commands/code-review.md           # >= 1 (audit scope literal)

# --- AC6: frozen contract byte-unchanged (container form; the repo diff/status guard runs operator-side) ---
sha256sum -c /tmp/df010-frozen.sha256                         # all files: OK

# --- no PR-mode diff-anchoring wording in the audit command ---
grep -n 'changed lines' commands/code-review.md               # must return 0 lines
```
</verification>

<!-- OPEN QUESTION for the human reviewer: (1) RESOLVED in req 3c — the `--security` × `--refresh-baseline` interaction is now bound: a baseline-refresh invocation writes `.code-review-baseline.yaml` and exits without a report, so no security pipeline runs on it (there is no review to attach it to); this is a maintenance-write exit, not a silent ignore of the flag. (2) RESOLVED in req 5 — Security Findings is a baseline-independent whole-repo inventory: the Step 6 baseline diff and Step 7 severity filter (incl. `--include-optional`) govern only the normal severity buckets, never the security section. (3) The `--security` × explicit `short`/`full` mode-token interaction is bound in req 3b: the security pipeline runs in-session regardless of mode token; short mode's "skip Step 5 entirely" applies only to the non-security adjudication. (4) The frozen `docs/selector-mode-guide.md` sentence "No command sets that signal yet" becomes historically stale after wiring — accepted residual staleness per the frozen-contract constraint. -->
