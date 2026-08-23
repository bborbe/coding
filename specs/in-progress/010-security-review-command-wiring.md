---
status: verifying
tags:
    - dark-factory
    - spec
approved: "2026-08-23T14:23:48Z"
generating: "2026-08-23T14:23:49Z"
prompted: "2026-08-23T14:40:03Z"
verifying: "2026-08-23T14:52:08Z"
branch: dark-factory/security-review-command-wiring
---

## Summary

- Add a `--security` flag to `/coding:pr-review`, `/coding:code-review`, and `/coding:local-review`. When set, the review runs the full security pipeline on top of the normal selector flow: derived security model, six-classifier trait groups with non-negotiable authz over-selection, deterministic invariant selection, an adjudicator fed the model subset, a falsification-gate verifier, derived blocking, and a Security Findings report section.
- The `--security` wiring only sets the **security-review signal** that activates the already-documented dormant `## Security Extension` in `docs/selector-mode-guide.md`. The classify/adjudicate steps 4c-sel/4d-sel and the shipped pipeline/verifier/blocking docs and agents are NOT re-authored.
- The per-review security model (`security-model.json`) is derived in-session, written under `/tmp` (mirroring `/tmp/pr-review-findings.json`), and never committed to any repo.
- Blocking is derived from the verifier verdict (`confidence==confirmed ∧ exploitability==high ∧ impact≥medium`), never stored as a severity label.
- Diff anchoring: PR mode (pr-review, local-review) reports findings only on diff-changed lines / invariants whose attack surface the diff touched; audit mode (code-review) is whole-repo.
- Ships the 4 mandated acceptance scenarios in `scenarios/`: finalizes the existing drafts 007 (IDOR-confirmed), 008 (IDOR-rejected-by-verifier), 009 (toolchain-fail-closed) by replacing their `TBD — task 4` fixture blocks with inline-built generic fixtures and the exact `--security` invocation, and authors the new 010 (security-zero-findings). Plus README.md / llms.txt / agent-list integration.

## Problem

The security pipeline — recon, evidence-pointered security model, six security trait groups, deterministic invariant selection, the `security-verifier` falsification gate, derived blocking, and the polymorphic finding contract — is fully documented and shipped (docs, agents, validator), but no slash command sets the **security-review signal** that activates it. The dormant Security Extension in `docs/selector-mode-guide.md` is inert. As a result the pipeline is unexercisable: an operator cannot run a security review on a real diff, the verifier gate never fires, and a future `security-review-agent` Go program has no callable entry point. Worse, the wiring is a silent-failure hazard — a `--security` review that runs the pipeline partially (mechanical findings only, no recon, no verifier) looks complete but ships unverified security findings. This task makes the pipeline a usable review domain behind a single flag.

## Goal

After this work, running `/coding:pr-review --security` (and the code-review / local-review equivalents) on a real repo diff produces a security review: the session derives a per-review evidence-pointered security model, the classifier activates the six security trait groups and deterministically selects invariants, the adjudicator judges the applicable invariants against the diff, high-severity findings pass the verifier falsification gate before emission, blocking is derived from the verdict (never stored as severity), findings are diff-anchored in PR mode and whole-repo in audit mode, and the report carries a Security Findings section plus a Security Model provenance block, alongside the normal traceability section. The four acceptance scenarios exist and pass, and README.md / llms.txt / agent tables reflect the new mode.

## Non-goals

- **The Go `security-review-agent` program (task 5)** — this is the slash-command surface that program calls; the program itself is a separate task and out of scope.
- **The comprehensive judgment/invariant-tier security rules (task 6)** — no new detection rules beyond wiring the existing 5 mechanical rules and the dormant judgment/invariant tier contract.
- **Bot deployment / `.maintainer.yaml`-gated watcher (iteration 2)** — local plugin surface only.
- **Runtime / network probing (design phase 2)** — static review only.
- **Re-authoring `scripts/validate-citations.sh`** — it is already polymorphic (`kind` rule|invariant|toolchain, `SECURITY_MODEL_FILE`, fail-closed); the wiring only passes the model file to it.
- **Editing `docs/selector-mode-guide.md` steps 4c-sel/4d-sel or the dormant Security Extension** — the extension is the frozen classify/adjudicate contract; the `--security` wiring activates it without editing it.
- **Per-surface configurable blocking thresholds** — the v1 fixed formula applies to all surfaces; tuning is a separate task.
- **Backfilling README scenario-table rows for 005/006** — pre-existing staleness, not part of this mode.

## Acceptance Criteria

**Container-executable rung** (runs in the YOLO container at prompt time; plugin repo — no Post-Deploy markers, no cluster):

- [ ] **AC1 — repo integrity:** `make precommit` exits 0 in the worktree — evidence: exit code (link validation + JSON syntax + check-rule-tests).
- [ ] **AC2 — `--security` flag wired into all three commands:** `grep -n -- '--security' commands/pr-review.md commands/code-review.md commands/local-review.md` returns ≥1 matching line per file, and `grep -n 'argument-hint:.*--security' commands/pr-review.md commands/code-review.md commands/local-review.md` returns ≥1 per file (each `argument-hint` names the flag) — evidence: file-content grep.
- [ ] **AC3 — security pipeline steps wired in the commands:** `grep -n 'security-model.json' commands/pr-review.md commands/code-review.md commands/local-review.md` returns ≥1 per file; `grep -n '/tmp/security-model.json' commands/*.md` returns ≥1 (session-local model path); `grep -n 'SECURITY_MODEL_FILE' commands/*.md` returns ≥1 (validator receives the session model); `grep -n 'security-verifier' commands/*.md` returns ≥1 (the falsification gate is invoked) — evidence: grep counts.
- [ ] **AC4 — report sections encoded:** `grep -n 'Security Findings' commands/*.md` returns ≥1 (the findings section with provenance + derived blocking); `grep -n 'Security Model' commands/*.md` returns ≥1 (the provenance block: `derived_from`, entry-point count, inventory counts, `model refresh:` lines); `grep -n 'model refresh' commands/*.md` returns ≥1 — evidence: grep counts.
- [ ] **AC5 — diff anchoring encoded:** `grep -n 'changed lines' commands/pr-review.md commands/local-review.md` returns ≥1 per file (PR mode: findings only on diff-changed lines / invariants whose attack surface the diff touched) and `grep -n 'whole' commands/code-review.md` returns ≥1 (audit mode: whole-repo, no diff anchoring) — evidence: grep counts.
- [ ] **AC6 — dormant contract and shipped artifacts untouched (negative):** `git diff origin/master -- docs/selector-mode-guide.md scripts/validate-citations.sh agents/security-verifier.md agents/go-security-specialist.md docs/security/` returns empty AND `git status --porcelain -- docs/selector-mode-guide.md scripts/validate-citations.sh agents/security-verifier.md agents/go-security-specialist.md docs/security/` returns empty (no modified, no untracked) — evidence: empty git diff + empty git status (steps 4c-sel/4d-sel and the Security Extension are not renumbered or rewritten; the validator, verifier, and rule-base docs are not re-authored).
- [ ] **AC7 — scenario files present and finalized:** `ls scenarios/010-security-zero-findings.md` succeeds and `grep -c 'status: draft' scenarios/010-security-zero-findings.md` returns ≥1; `grep -c 'TBD' scenarios/007-security-idor-confirmed.md scenarios/008-security-idor-rejected-by-verifier.md scenarios/009-security-toolchain-fail-closed.md` returns 0 (the `TBD — task 4` fixture blocks are replaced); `grep -c -- '--security' scenarios/007-security-idor-confirmed.md scenarios/008-security-idor-rejected-by-verifier.md scenarios/009-security-toolchain-fail-closed.md scenarios/010-security-zero-findings.md` returns ≥1 per file (each names the exact `--security` invocation); each of the 4 files has ≥8 unchecked checkboxes across Setup/Action/Expected/Cleanup (`grep -c '^- \[ \]'` ≥8 per file) — evidence: file presence + grep counts.
- [ ] **AC8 — repo surfaces updated:** `grep -n -- '--security' README.md` returns ≥1 (commands table and/or Quick Start); `grep -n '010-security-zero-findings' README.md` returns ≥1 (Acceptance Scenarios table gains the 4 security scenario rows); `grep -c 'security-review-pipeline' llms.txt` ≥1 and `grep -c 'security-verifier' llms.txt` ≥1 (llms.txt stays aligned; the mode adds no new guide or agent, so no new llms entry is required); `git diff origin/master --stat -- agents/` shows no new files AND `git status --porcelain -- agents/` returns empty (no modified, no untracked; no new agent; `security-verifier` stays registered in the README agent tables) — evidence: grep counts + git diff + git status.

**Operator-executable rung** (host-side scenario walks after merge; each against an inline-built generic fixture in a fresh Claude Code session, plugin pinned to the branch under test):

- [ ] **AC9 — security-zero-findings walk passes:** a `--security` review of a clean generic Go app reports the `Security Findings` section with zero rule/invariant findings and the `Security Model` provenance block present, and no finding blocks — evidence: scenario 010 Expected checkboxes + `cat /tmp/scen010-exit` prints 0 and stdout greps (`Security Findings` ≥1, `Security Model` ≥1, `grep -c '"blocking": true' /tmp/scen010-stdout.log` returns 0).
- [ ] **AC10 — IDOR-confirmed walk passes:** a `--security` review of a generic order app with a seeded ownership-check bypass emits the invariant-kind IDOR finding, the verifier verdict is `confirmed` with `counterevidence_checked` populated, and the finding blocks (formula holds) — evidence: scenario 007 Expected checkboxes + stdout greps (`"confidence": "confirmed"` ≥1, `counterevidence_checked` ≥1, `"exploitability": "high"` ≥1, `"impact": "high"` ≥1, `grep -c '"blocking": true' /tmp/scen007-stdout.log` ≥1).
- [ ] **AC11 — IDOR-rejected walk passes:** a `--security` review of a generic order app guarded by a service-layer ownership check rejects the naive IDOR claim — verdict `rejected`, `reject_reason` recorded, the finding does NOT emit, no blocking — evidence: scenario 008 Expected checkboxes + stdout greps (`"confidence": "rejected"` ≥1, `reject_reason` ≥1, absence grep for the finding id = 0, `grep -c '"blocking": true' /tmp/scen008-stdout.log` returns 0).
- [ ] **AC12 — toolchain-fail-closed walk passes:** a `--security` review whose dependency toolchain pass flags a vulnerable dependency reports the toolchain finding as a Must-Fix item (never a silent skip), and the validator half of scenario 009 still passes toolchain findings and fail-closes invariant findings without a model — evidence: scenario 009 Expected checkboxes + stdout greps (toolchain finding id/advisory ≥1 in the report, `WARN: dropped` on the no-model run).

## Verification

No Post-Deploy markers — plugin repo, no cluster.

## Container-executable (runs inside the YOLO container at prompt time)

- `make precommit` — link validation + JSON syntax + check-rule-tests clean.
- `grep -n -- '--security' commands/pr-review.md commands/code-review.md commands/local-review.md` — ≥1 line per file.
- `grep -n 'security-model.json' commands/pr-review.md commands/code-review.md commands/local-review.md` — ≥1 per file; `grep -n '/tmp/security-model.json' commands/*.md` — ≥1.
- `grep -n 'SECURITY_MODEL_FILE' commands/*.md` — ≥1; `grep -n 'security-verifier' commands/*.md` — ≥1.
- `grep -n 'Security Findings' commands/*.md` — ≥1; `grep -n 'Security Model' commands/*.md` — ≥1; `grep -n 'model refresh' commands/*.md` — ≥1.
- `grep -n 'changed lines' commands/pr-review.md commands/local-review.md` — ≥1 each; `grep -n 'whole' commands/code-review.md` — ≥1.
- `git diff origin/master -- docs/selector-mode-guide.md scripts/validate-citations.sh agents/security-verifier.md agents/go-security-specialist.md docs/security/` — empty.
- `ls scenarios/010-security-zero-findings.md` — succeeds; `grep -c 'TBD' scenarios/007-security-idor-confirmed.md scenarios/008-security-idor-rejected-by-verifier.md scenarios/009-security-toolchain-fail-closed.md` — 0; `grep -c -- '--security' scenarios/007-*.md scenarios/008-*.md scenarios/009-*.md scenarios/010-*.md` — ≥1 per file.
- `grep -n -- '--security' README.md` — ≥1; `grep -n '010-security-zero-findings' README.md` — ≥1; `grep -c 'security-review-pipeline' llms.txt` — ≥1; `git diff origin/master --stat -- agents/` — no new files.

## Operator-executable (runs on the host after PR merge, spec verification ladder)

All four walks run `/coding:local-review --security` (in-place) against the inline-built fixtures — the fixtures are local-only branches with no origin remote, and pr-review's worktree flow unconditionally runs `git fetch origin` (commands/pr-review.md Step 0b; precedent: scenario 005). With the two-commit fixture shape, `HEAD~1` (local-review's diff) equals `master..HEAD` (pr-review's diff), so the diff-relevant assertions hold.

- Walk scenario 010 (security-zero-findings): inline-build a clean generic Go app, run `/coding:local-review --security`, assert clean Security Findings + Security Model provenance + no blocking.
- Walk scenario 007 (IDOR-confirmed): inline-build a generic order app with a seeded ownership-check bypass, run `/coding:local-review --security`, assert verifier `confirmed` + `counterevidence_checked` + blocking.
- Walk scenario 008 (IDOR-rejected): inline-build a generic order app with a service-layer ownership check, run `/coding:local-review --security`, assert verifier `rejected` + `reject_reason` + no emission + no blocking.
- Walk scenario 009 (toolchain-fail-closed): run the validator half (toolchain passes, invariant fail-closed without model) plus a `/coding:local-review --security` review walk whose dependency scan flags a vulnerable dependency; assert the toolchain finding surfaces as Must-Fix, never a silent skip.

## Desired Behavior

1. **`--security` flag parsing and signal (all three commands).** Each command parses `--security` as a position-independent boolean flag from its arguments (alongside the existing mode token — short/full/selector, selector default). When present, the command sets the security-review signal, which activates the dormant `## Security Extension` in `docs/selector-mode-guide.md` (steps 4c-sel/4d-sel run byte-for-byte as before when the signal is absent). The `argument-hint` of each command gains the flag. Setting `--security` must never be silently ignored: the mode runs the security pipeline for the reviewed scope, and a scope containing Go source always produces the Security Model provenance block (never a silent skip).
2. **Security recon and the session-local derived model.** Before classify, the command runs the recon pass per `docs/security/security-review-pipeline.md`: enumerate entry points (recall-oriented), resolve identities and auth mechanisms, resolve resources and their `authorization_functions`, and derive invariants (`resource → identifier → authorization_function`) with `file:line` evidence. The result is written to `/tmp/security-model.json` (session-local, mirroring `/tmp/pr-review-findings.json`) and never to any path inside the reviewed repo. The model carries `derived_from` (repo, head, review_id), the freshness gate (changed-evidence entries re-derived, unchanged carried forward), diff-relevant truncation on large repos, and the countable attack-surface inventory.
3. **Classifier security trait groups and deterministic invariant selection.** Under the signal, security-relevant selection uses exactly the six trait groups `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. The `authz` group is non-negotiable: any diff touching a file cited as evidence by an entry point operating on a modeled resource, or cited as evidence by a modeled resource's `authorization_function`, MUST select `authz`. Invariant selection is fully deterministic via the drift bridge and the invariant's `attack_surfaces`: the diff touching an invariant's attack surface or its evidence source forces that `invariant_id` into the applicable set (no LLM judgment, never skipped). The HARD INVARIANT holds: the applicable set is a subset of the Step 4b-i candidate set — trait groups never add a rule the glob did not produce.
4. **Adjudicator extension and the verifier gate.** The Step 4d-sel adjudicator input gains the diff-relevant model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal. Each applicable invariant is judged against the diff slice with the single question: does this change preserve the invariant? Invariant-kind findings cite `invariant_id`. After adjudication, before emission, a verifier gate runs per the contract in `agents/security-verifier.md` (7-item falsification checklist; verdict `confirmed | plausible | rejected` with `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, and `reject_reason` required on rejection). The gate is a hard pre-emission step for `severity=critical` and for `severity=major` when `confidence=confirmed`; every surviving high-severity finding carries a populated `counterevidence_checked`. Execution mechanism (in-session role vs sub-agent spawn) is an implementation detail — agent decides at impl time, preserving the gate's hard pre-emission property.
5. **Blocking derived, never stored as severity.** Under the signal, each finding's blocking state is derived as `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`. The formula is the uniform v1 default for all three surfaces (local, bot, audit); there are no per-surface config fields and no opt-out flags. Blocking never consults the finding's `severity` label; a `plausible` critical does not block merge and is reported as a required human review item.
6. **Diff anchoring and scope.** In PR mode (pr-review, local-review), findings are reported ONLY for lines the diff changed or invariants whose attack surface the diff touched; whole-file context is permitted for reasoning, never for gating. In audit mode (code-review), the scope is the whole repo — no diff anchoring — and the recon derives a whole-repo model.
7. **Report: Security Findings + Security Model provenance + traceability.** Under the signal, the Step 5 report gains a `Security Findings` section listing every security finding (rule and invariant, and toolchain findings from the deps pass) with its `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields, and derived blocking state, plus a `Security Model` provenance block recording `derived_from`, entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. The normal severity buckets and the selector traceability section still appear. Whether individual security findings are additionally duplicated into the severity buckets is an implementation detail — agent decides at impl time; the Security Findings section is the authoritative carrier of verdict and blocking data.
8. **Citation validation integration.** The mode's citation-validation invocation passes `SECURITY_MODEL_FILE` pointing at `/tmp/security-model.json`, so invariant-kind findings resolve against the session model's `invariants[].id`. A finding cites exactly one provenance (`kind=rule` → `rule_id` in `rules/index.json`; `kind=invariant` → `invariant_id` in the model; `kind=toolchain` → no id). Absent an unset/missing/unreadable/unparseable model, invariant findings drop fail-closed with a WARN to stderr and are never kept — the existing validator enforces this; the command only supplies the model file. The toolchain/deps pass is fail-closed: a dependency-scan failure surfaces as a Must-Fix toolchain finding in the report, never a silent skip.

## Constraints

- **Dormant contract frozen:** the `## Security Extension` in `docs/selector-mode-guide.md` is the classify/adjudicate contract for this mode; steps 4c-sel/4d-sel and the extension text MUST NOT be renumbered, rewritten, or edited. The `--security` command wiring sets the security-review signal that activates it; when the signal is absent the existing procedure runs byte-for-byte.
- **Shipped artifacts not re-authored:** `docs/security/security-review-pipeline.md`, `docs/security/security-review-guide.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, and `scripts/validate-citations.sh` already exist and are NOT modified by this spec. No new security detection rules (the 5 mechanical rules + the dormant judgment/invariant tier are the full rule set).
- **Blocking:** derived per formula, never stored as severity; per-surface configurable thresholds are out of scope (v1 fixed formula, no config fields, no opt-out flags).
- **Finding provenance:** exactly one of `rule_id ∈ rules/index.json`, `invariant_id ∈ derived model`, or `kind=toolchain` (no id). No new validation-script work.
- **Model location:** `security-model.json` is session-local under `/tmp`, never committed to any repo; if it is ever written inside the reviewed repo tree it is deleted and rewritten to the session-local path.
- **Commands are thin wrappers:** no inline rules; all agent references use the `coding:` prefix; the classify/adjudicate/verifier procedure is executed per the guides, not re-implemented in the command.
- **HARD INVARIANT preserved:** the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
- **Selector-mode zero-sub-agent-spawn property preserved** for the classify/adjudicate steps; the verifier execution mechanism is the only deviation point and is reversible (agent decides at impl time).
- **Generic content only:** fixtures and examples use User, Order, Product, Customer — never trading/project-specific content, never personal paths.
- **Scenario location and numbering:** scenarios live in `scenarios/` (next after 006); existing drafts 007/008/009 are finalized, 010 is new. Fixtures are built inline in each scenario's Setup (clone/scaffold a minimal generic Go app + apply the violating code, per 002 precedent) — no new perpetual fixture PR required.

## Failure Modes

| Trigger | Expected behavior | Recovery |
|---------|-------------------|----------|
| Recon aborts mid-derivation or the model is unreadable/unparseable | The partial model is discarded; invariant-kind findings drop fail-closed (WARN to stderr, never kept); the review continues with rule/toolchain findings | Re-run the recon with a wider package scope, merge into the model, re-run the review |
| `SECURITY_MODEL_FILE` unset/missing at validation | Invariant findings fail closed (exit 1, `WARN: dropped` naming the `invariant_id`), never kept — never a silent pass | Confirm the command passes `/tmp/security-model.json` to the validator |
| ast-grep/sg not in PATH (Step 4.0) | Existing fail-fast: report "Must Fix toolchain failure" and stop the funnel — the `--security` mode must not bypass or soften this | Install ast-grep, re-run |
| Toolchain/deps pass fails (osv-scanner/trivy/govulncheck error or flagged vulnerability) | Fail-closed: the toolchain failure or the dependency finding surfaces as a Must-Fix item in the report — never a silent skip | Fix the dependency or toolchain, re-run |
| The model is accidentally written inside the reviewed repo tree | The pipeline detects the in-tree path and rewrites the model to the session-local path | Delete the in-tree file and re-run; the scenario walk asserts no `security-model.json` inside the fixture repo |
| Model stale (an entry's evidence lines changed in the diff, or an evidence symbol no longer resolves) | Freshness gate re-derives the changed entry / drops the non-resolving one; the report carries the `model refresh:` line verbatim | Re-run the review with the refreshed model; no manual model maintenance |
| The verifier kills a real vulnerability (false kill) | Residual risk is caught by the `ai_review` post-post backstop (dismiss + COMMENT + human_review) | Human review resolves the finding; the judge's recall covers the miss direction by design |
| Mega-PR too large to enumerate | Model derivation is limited to the touched entry points/invariants; the report notes the truncation | Re-run the recon with a wider package scope and merge |
| Two concurrent review sessions on the same repo | Each session derives its own session-local model under `/tmp`; there is no shared state to race on | None — by construction |
| osv-scanner/trivy database fetch times out or is throttled during the walk | The toolchain pass reports the failure as a Must-Fix toolchain item (fail-closed), not a silent empty scan | Retry the scan with the local cache warm, re-run |

## Security / Abuse Cases

This feature reads and analyzes repo content (potentially attacker-authored PRs) and produces advisory findings; it never executes reviewed code.

- **What an attacker controls:** the contents of the reviewed repo — file text, diff lines, and any file referenced in evidence. An attacker-authored PR can attempt to steer the recon/adjudicator through adversarial content.
- **What crosses a trust boundary:** reviewed-repo content enters the review session and the LLM-derived model. The model is never executed, never parsed as code, never fed into a shell or build step; `file:line` evidence strings are display-only references and the recon writes no files to those paths.
- **No invented security policy:** every finding resolves exactly one provenance (`rule_id` in `rules/index.json`, `invariant_id` in the derived model, or `kind=toolchain`); the validator drops anything unprovenanced. An attacker cannot inject a fake `rule_id` or `invariant_id` into a passing report.
- **Blocking is verifier-gated:** a finding blocks only when `confidence==confirmed ∧ exploitability==high ∧ impact≥medium`, and a confirmation requires a concrete attacker scenario plus a populated `counterevidence_checked`. An attacker cannot self-certify a finding or force a merge block through planted plausible findings; conversely a naive claim is rejected when the verifier finds real authorization.
- **What can hang/race:** toolchain scans (osv-scanner/trivy DB fetches) can hang on the network — bounded by the fail-closed toolchain reporting; two concurrent sessions derive independent session-local models (no shared state).
- **Validation discipline:** the verifier's counterevidence must resolve in code or in the model's evidence — a hopeful reference is not counterevidence; findings cite only paths seen in the reviewed scope.

## Suggested Decomposition

Prompts are generated in this order — each row is a single prompt with a clear scope. This spec spans 3 command files + scenarios + repo surfaces (5 layers), so the decomposition is mandatory.

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Wire `--security` into `commands/pr-review.md`: flag parsing + signal, recon → `/tmp/security-model.json` derivation, classifier trait groups + authz over-selection + deterministic invariant selection, adjudicator inputs, verifier gate invocation, blocking derivation, PR-mode diff anchoring, Security Findings + Security Model report sections, `SECURITY_MODEL_FILE`-passed citation validation | 1, 2, 3, 4, 5, 6 (PR), 7, 8 | 1-6 | — |
| 2 | Mirror the wiring into `commands/code-review.md` (audit mode: whole-repo scope, no diff anchoring, whole-repo model) | 1, 2, 3, 4, 5, 6 (audit), 7, 8 | 2, 3, 4, 5, 6 | prompt 1 |
| 3 | Mirror the wiring into `commands/local-review.md` (local mode: diff anchoring) | 1, 2, 3, 4, 5, 6 (PR), 7, 8 | 2, 3, 4, 5, 6 | prompt 1 |
| 4 | Author the 4 acceptance scenarios in `scenarios/`: finalize 007/008/009 (replace `TBD — task 4` fixture blocks with inline-built generic fixtures + the exact `--security` invocation) and author 010 security-zero-findings; each with `status: draft`, Setup/Action/Expected/Cleanup checkboxes, observable assertions only | 1-8 (end-to-end) | 7, 9-12 | prompts 1-3 (the walks exercise the wired commands) |
| 5 | Repo-surface integration: README.md commands table + Quick Start + Acceptance Scenarios table rows (007-010), llms.txt alignment check, agent-table verification (no new agent) | — | 8 | — |

Rationale: prompt 1 establishes the canonical full pipeline in the reference command (pr-review), so prompts 2 and 3 mirror a proven shape rather than each re-deriving the security procedure — this keeps each command independently reviewable and prevents three divergent interpretations of the dormant extension. Prompts 2 and 3 depend on 1 because the Security Findings/model-provenance/report-section wording and the diff-anchoring rule must be consistent across all three commands. Every wiring prompt (1-3) claims AC6 (the frozen-contract negative guard) and the command-spanning AC2/AC4 so the daemon's AC-coverage pass never orphans them. Prompt 4 requires all three commands wired before its walks can pass. Prompt 5 is independent of the command internals and can run last (or in parallel).

## Do-Nothing Option

If this task is not done, the security pipeline remains documented but inert: the dormant Security Extension stays dormant, no operator can run a security review on a real diff, the verifier gate and derived blocking never fire, and the future `security-review-agent` Go program has no callable slash-command entry. The shipped docs/agents/validator carry a one-time sunk cost with zero exercised value, and the wiring gap would eventually be discovered only when a partial security review silently ships unverified findings. The current state is not acceptable for the security-review rollout: the pipeline exists but is unusable, so the mode must be wired.
