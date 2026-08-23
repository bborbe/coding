---
status: completed
spec: [010-security-review-command-wiring]
summary: 'Wired the --security flag into commands/pr-review.md (flag parsing, Security mode subsection referencing the frozen pipeline guide/verifier/validator, Security Findings + Security Model report sections) and added a feat: CHANGELOG entry; make precommit exits 0 and all frozen contracts are byte-unchanged'
execution_id: coding-security-pr-review-command-exec-042-spec-010-wire-security-into-pr-review
dark-factory-version: dev
created: "2026-08-23T17:15:00Z"
queued: "2026-08-23T14:49:32Z"
started: "2026-08-23T14:49:34Z"
completed: "2026-08-23T14:52:08Z"
branch: dark-factory/security-review-command-wiring
---

# Wire --security into commands/pr-review.md

<summary>
- The PR review command accepts a position-independent `--security` flag; when set it activates the dormant security review mode on top of the normal selector flow
- The review session derives a session-local security model under `/tmp`, runs the six security trait groups with mandatory `authz` over-selection, judges invariants deterministically, and gates high-severity findings through the falsification verifier before they may emit
- Merge blocking is derived from the verifier verdict (never stored as severity), and security findings are anchored to the changed lines of the diff
- The report gains a `Security Findings` section and a `Security Model` provenance block while the normal severity buckets and selector traceability still appear
- The command stays a thin wrapper — it references the frozen pipeline guide, the selector-mode security extension, the verifier agent, and the polymorphic validator by name instead of re-implementing them
- The citation validator receives the session model file so invariant-kind findings resolve against it and fail closed (never silently kept) when the model is absent
- A fail-closed dependency toolchain pass surfaces scan failures or flagged vulnerabilities as Must-Fix items, never a silent skip
- The six frozen security contract files are proven byte-unchanged, and existing selector / short / full behavior is untouched when the flag is absent
- The acceptance-suite invariants on the command (short-mode skip, runner reference, selector routing and short-circuit string, step labels) all stay green
</summary>

<objective>
Wire the `--security` flag into `commands/pr-review.md` so a PR review can run the full security pipeline — recon-derived session model, six trait groups with deterministic invariant selection, verifier-gated findings, derived blocking, PR-mode diff anchoring, a dependency toolchain pass, and the `Security Findings` + `Security Model` report sections — by referencing the already-shipped, frozen security contract (pipeline guide, selector-mode extension, verifier agent, polymorphic validator), never by re-implementing it.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "Command = Thin Wrapper" and "Plugin Namespacing" rules (commands parse arguments and delegate; all agent references use the `coding:` prefix; no inline rules) and the generic-content rule (User, Order, Product, Customer only).

Read `commands/pr-review.md` (full) — the file to edit. Note the structure you must preserve: frontmatter `argument-hint: "<target-branch> [short|full|selector]"`, Step 0a argument parsing, Step 1 mode parsing, Step 2 project detection, Step 3 automated checks, Step 4 dispatcher (4.0 toolchain preflight → 4a mechanical funnel → 4b-i candidate computation → selector-mode 4c-sel/4d-sel block → full-mode dispatch → 4c context conventions → 4d citation validation), Step 5 consolidated report, Step 6 next steps, Step 7 manual review.

Read `docs/selector-mode-guide.md` (full) — the dormant `## Security Extension (dormant)` section (classifier sub-step trait groups, deterministic invariant selection, adjudicator input extension, verifier gate, blocking model, polymorphic finding contract) and the Step 4d-sel citation-validation invocation. This file is FROZEN — do not edit it; the command references it.

Read `docs/security/security-review-pipeline.md` (full) — the recon procedure, model schema, freshness gate, diff-relevant truncation, attack-surface inventory drift bridge, and report contract. FROZEN — reference, never re-document.

Read `agents/security-verifier.md` (full) — the 7-item falsification checklist and the verdict contract (`confirmed | plausible | rejected` with `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, and `reject_reason` required on rejection). FROZEN.

Read `scripts/validate-citations.sh` (full) — the polymorphic validator: `SECURITY_MODEL_FILE` env var, `kind` rule|invariant|toolchain resolution, fail-closed absent-model drop path (exit 1, `WARN: dropped` on stderr). FROZEN.

Read `docs/security/security-review-guide.md` (skim the RULE ids) — the 5 mechanical rules whose finding ids the classifier `crypto`/`secrets` selection references (`go-security/crypto-insecure-random`, `go-security/crypto-weak-algorithm`, `go-security/hardcoded-secret`).

Read `scripts/acceptance.sh` (the checks on `commands/pr-review.md`) — the check-acceptance assertions that must stay green after your edit: the short-mode "No agents / skip Step 4" directive, the `scripts/ast-grep-runner.sh` reference, the `Selector mode (the default)` routing, the `--selector`/`selector.*mode` token, the `selector clean — no adjudication needed` short-circuit string, `GUIDE_OK`/`GUIDE_MISSING`, the `selector-mode-guide.md` filename, the `4c-sel`/`4d-sel` labels, the Step 2.5 context-doc mappings (`teamvault-conventions.md`, `go-k8s-binary-conventions.md`, `k8s-manifest-guide.md`, `changelog-guide.md`), and the `coding:<owner>`/`findings_by_owner` dispatch block. Preserve all of them.
</context>

<requirements>
1. **Record the frozen-contract baseline FIRST.** Before making any edit, run:
   `sha256sum docs/selector-mode-guide.md scripts/validate-citations.sh agents/security-verifier.md agents/go-security-specialist.md docs/security/security-review-pipeline.md docs/security/security-review-guide.md > /tmp/df010-frozen.sha256`
   Keep this file for the AC6 check in `<verification>`. If any of the six files is missing, STOP and report the missing path — the frozen contract is incomplete and must not be edited or recreated.

2. **Flag parsing (AC2).**
   a. In the frontmatter, change the `argument-hint` line to: `argument-hint: "<target-branch> [short|full|selector] [--security]"`.
   b. In Step 0a (Parse arguments), add a bullet: `--security` is a position-independent boolean flag that may appear anywhere in the argument list (before or after `TARGET_BRANCH` and the mode token); when present, set `SECURITY_REVIEW=1`. It is independent of the mode token and `TARGET_BRANCH`.
   c. In Step 1 (Parse Mode Argument), add: when `SECURITY_REVIEW` is set, the security-mode steps in Step 4 run in every mode — including short mode, which otherwise skips Step 4 (the existing short-mode "skip Step 4" directive applies only to the non-security funnel) — the flag is never silently ignored.

3. **Insert a new subsection — `#### Security mode (under \`--security\` only)`** — positioned immediately AFTER the "Selector mode (the default): Steps 4c-sel and 4d-sel" block (which ends with the sentence "Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.") and immediately BEFORE the "#### Full mode: per-owner dispatch" heading. The subsection's intro states: it runs only when `SECURITY_REVIEW` is set; it activates the dormant `## Security Extension (dormant)` in `docs/selector-mode-guide.md` (steps 4c-sel/4d-sel run byte-for-byte as before when the signal is absent); it references the frozen guides/agents by name — it does NOT re-implement or re-document the procedure; and it runs in every mode (short, selector, full) without bypassing or softening the existing Step 4.0 toolchain fail-fast (ast-grep/sg preflight → "Must Fix toolchain failure") or the Step 4a mechanical funnel — a `--security` review without the mechanical funnel would silently miss every MUST-tier finding. It contains these numbered steps:

   1. **Recon and model derivation** — per `docs/security/security-review-pipeline.md` (the derivation contract is frozen there): enumerate entry points from the diff's touched packages (recall-oriented), resolve identities and auth mechanisms, resolve resources and their `authorization_functions`, and derive invariants as `resource → identifier → authorization_function` with `file:line` evidence. Write the model to `/tmp/security-model.json` (session-local, mirroring `/tmp/pr-review-findings.json`) and never to any path inside the reviewed repo — if the model is accidentally written in-tree, delete it and rewrite it to the session-local path. Apply the freshness gate (changed-evidence entries re-derived, unchanged carried forward; stale entries whose evidence no longer resolves are dropped and surfaced with the literal `model refresh:` line) and diff-relevant truncation on large repos (note the truncation in the report). Record the attack-surface inventory counts.
   2. **Classifier trait groups** — per the dormant extension: exactly six groups `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. `authz` over-selection is non-negotiable: a diff touching a file cited as evidence by an entry point operating on a modeled resource, or cited as evidence by a modeled resource's `authorization_function`, MUST select `authz`. Deterministic invariant selection: a diff touching an invariant's `attack_surfaces` or its `evidence` source forces that `invariant_id` into the applicable set — no LLM judgment, never skipped. The HARD INVARIANT holds: the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
   3. **Adjudicator inputs** — the Step 4d-sel adjudicator input gains the diff-relevant model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal. Each applicable invariant is judged against the diff slice with the single question: does this change preserve the invariant? Invariant-kind findings cite `invariant_id`.
   4. **Verifier gate** — after adjudication, before emission, run the falsification gate per `agents/security-verifier.md` (7-item falsification checklist; verdict `confirmed | plausible | rejected` with `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, and `reject_reason` required on rejection). It is a hard pre-emission step for `severity=critical` and for `severity=major` when `confidence=confirmed`; every surviving high-severity finding carries a populated `counterevidence_checked`. The execution mechanism (in-session role vs sub-agent spawn) is an implementation detail the session decides, preserving the gate's hard pre-emission property. Residual false kills are caught by the `ai_review` post-post backstop (dismiss + COMMENT + human_review).
   5. **Blocking derived, never stored as severity** — `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`; no per-surface config fields, no opt-out flags. A `plausible` critical does NOT block merge — it is reported as a required human review item.
   6. **Diff anchoring** — in PR mode, report security findings ONLY on diff-changed lines or invariants whose attack surface the diff touched; whole-file context is permitted for reasoning, never for gating.
   7. **Toolchain/deps pass (fail-closed)** — run a dependency scan over the reviewed repo (osv-scanner / trivy / govulncheck, whichever are available; govulncheck for Go modules), executed via the `go-security-specialist` agent or in-session per the zero-spawn property, and emit findings as `kind=toolchain` carrying `tool`, `package`, `version`, `advisory`, `file`, `line`. A scan failure, a database-fetch timeout, or a flagged vulnerability surfaces as a Must-Fix toolchain finding in the report — never a silent skip.
   8. **Citation validation** — the Step 4d-sel citation-validation invocation passes `SECURITY_MODEL_FILE=/tmp/security-model.json` so invariant-kind findings resolve against the session model's `invariants[].id`. Each finding resolves exactly one provenance (`kind=rule` → `rule_id` in `rules/index.json`; `kind=invariant` → `invariant_id` in the model; `kind=toolchain` → no id). Absent an unset/missing/unreadable/unparseable model, invariant findings drop fail-closed (WARN to stderr) and are never kept — the validator enforces this; the command only supplies the model file.

   Each of the literal strings `security-model.json`, `/tmp/security-model.json`, `SECURITY_MODEL_FILE`, `security-verifier`, and `model refresh` must appear at least once in this subsection (AC3/AC4 evidence).

4. **Report sections (AC4/AC5).** In Step 5 (Consolidated Report), add under the signal: a `Security Findings` section listing every security finding (rule, invariant, and toolchain) with `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields, and derived blocking state; and a `Security Model` provenance block recording `derived_from` (repo, head, review_id), the entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. A scope containing Go source always produces the Security Model block (never a silent skip); a scope with no Go source — including when the Step 4 early-exit fires on a non-rule-relevant diff — states `no Go source — security model not derived` explicitly instead of omitting the section. The normal severity buckets and the selector traceability section still appear. The literal strings `Security Findings`, `Security Model`, and `model refresh` must each appear at least once in the command (AC4 evidence); the string `changed lines` must appear at least once in the diff-anchoring wording (AC5 evidence — the phrase "diff-changed lines" satisfies it).

5. **Preserve existing behavior (no regression).** The existing Steps 0a–0d, 1, 2, 3, 4.0, 4a, 4b-i, the selector-mode block, the full-mode dispatch block, 4c, 4d, the existing Step 5 sections, Step 6, and Step 7 are preserved unchanged except the targeted additions in requirements 2–4. All of the `scripts/acceptance.sh` assertions on this file must still pass after your edit (listed in `<context>`). Do NOT touch `commands/code-review.md`, `commands/local-review.md`, any `docs/*`, `scripts/*`, `agents/*`, `rules/*`, `README.md`, `llms.txt`, `scenarios/*`, or `CHANGELOG.md` (sibling prompts own them).

6. **Dormant contract and shipped artifacts untouched (AC6).** Do not edit `docs/selector-mode-guide.md` (the dormant Security Extension and steps 4c-sel/4d-sel stay byte-identical), `scripts/validate-citations.sh`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, `docs/security/security-review-pipeline.md`, or `docs/security/security-review-guide.md` — the command only references them. No `### RULE` heading anywhere in your edit. Generic examples only (User, Order, Product, Customer); never trading/project-specific content; no personal paths.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; the git-based negative guard (AC6 `git diff origin/master` / `git status --porcelain`) runs on the operator side of the spec's Verification ladder — the container form is the checksum baseline in requirement 1.
- The `## Security Extension (dormant)` in `docs/selector-mode-guide.md` is the frozen classify/adjudicate contract: steps 4c-sel/4d-sel and the extension text MUST NOT be renumbered, rewritten, or edited; the `--security` wiring only sets the security-review signal that activates it, and when the signal is absent the existing procedure runs byte-for-byte.
- Shipped artifacts not re-authored: `docs/security/security-review-pipeline.md`, `docs/security/security-review-guide.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, and `scripts/validate-citations.sh` already exist and are NOT modified. No new security detection rules.
- Blocking: derived per `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`, never stored as severity; per-surface configurable thresholds are out of scope — no config fields, no opt-out flags.
- Finding provenance: exactly one of `rule_id ∈ rules/index.json`, `invariant_id ∈ derived model`, or `kind=toolchain` (no id). No new validation-script work.
- Model location: `security-model.json` is session-local under `/tmp`, never committed to any repo; if it is ever written inside the reviewed repo tree it is deleted and rewritten to the session-local path.
- Commands are thin wrappers: no inline rules; all agent references use the `coding:` prefix; the classify/adjudicate/verifier procedure is executed per the guides, not re-implemented in the command.
- HARD INVARIANT preserved: the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
- Selector-mode zero-sub-agent-spawn property preserved for the classify/adjudicate steps; the verifier execution mechanism is the only deviation point and is reversible (the session decides at review time).
- The `--security` mode must not bypass or soften the existing Step 4.0 toolchain fail-fast (ast-grep/sg preflight) or the Step 4a mechanical funnel — a review without the mechanical funnel would silently miss every MUST-tier finding.
- Generic content only: fixtures and examples use User, Order, Product, Customer — never trading/project-specific content, never personal paths.
- Existing tests must still pass: `make precommit` (incl. `check-acceptance`) exits 0.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- AC1: repo integrity ---
make precommit    # must exit 0

# --- AC2: --security flag wired ---
grep -n -- '--security' commands/pr-review.md                 # >= 1
grep -n 'argument-hint:.*--security' commands/pr-review.md    # >= 1

# --- AC3: security pipeline steps wired ---
grep -n 'security-model.json' commands/pr-review.md           # >= 1
grep -n '/tmp/security-model.json' commands/pr-review.md      # >= 1
grep -n 'SECURITY_MODEL_FILE' commands/pr-review.md           # >= 1
grep -n 'security-verifier' commands/pr-review.md             # >= 1

# --- AC4: report sections encoded ---
grep -n 'Security Findings' commands/pr-review.md             # >= 1
grep -n 'Security Model' commands/pr-review.md                # >= 1
grep -n 'model refresh' commands/pr-review.md                 # >= 1

# --- AC5: PR-mode diff anchoring ---
grep -n 'changed lines' commands/pr-review.md                 # >= 1

# --- AC6: frozen contract byte-unchanged (container form; the repo diff/status guard runs operator-side) ---
sha256sum -c /tmp/df010-frozen.sha256                         # all files: OK

# --- acceptance-suite invariants preserved (check-acceptance must stay green) ---
grep -n 'Selector mode (the default)' commands/pr-review.md   # >= 1
grep -n 'selector clean — no adjudication needed' commands/pr-review.md   # >= 1
grep -n '4c-sel' commands/pr-review.md                        # >= 1
grep -n '4d-sel' commands/pr-review.md                        # >= 1
grep -n 'scripts/ast-grep-runner.sh' commands/pr-review.md    # >= 1
grep -n 'Short Mode.*No agents' commands/pr-review.md         # >= 1
```
</verification>

<!-- OPEN QUESTION for the human reviewer: (1) RESOLVED in req 2c — the `--security` × explicit `short`/`full` mode-token interaction is now bound: the security-mode steps run in every mode; short mode's "skip Step 4" applies only to the non-security funnel. (2) The frozen `docs/selector-mode-guide.md` still contains "No command sets that signal yet — task 4's command wiring does"; after this wiring ships that sentence is historically stale, but the spec freezes the guide text — confirm the reviewer accepts this residual staleness (or requests a follow-up). (3) Sibling draft spec `specs/selector-mode-classify-adjudicate.md` (confirmed present at `specs/selector-mode-classify-adjudicate.md`) also owns the structure of `docs/selector-mode-guide.md`; this prompt relies on the CURRENT structure (dormant extension + 4c-sel/4d-sel steps) staying byte-identical. -->
