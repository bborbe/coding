---
status: draft
spec: [010-security-review-command-wiring]
created: "2026-08-23T17:18:00Z"
branch: dark-factory/security-review-command-wiring
---

# Author the four security-mode acceptance scenarios (007/008/009 finalize, 010 new)

<summary>
- The three draft security scenarios (007 IDOR-confirmed, 008 IDOR-rejected-by-verifier, 009 toolchain-fail-closed) are finalized: their `TBD — task 4` fixture blocks are replaced with inline-built generic fixture instructions and the exact `--security` invocation, so they become walkable end-to-end acceptance walks
- A fourth scenario (010 security-zero-findings) is authored for the clean-app walk that proves a `--security` review on a clean generic Go app reports zero findings with the Security Model provenance block and no merge blocking
- Each scenario builds its fixture inline in Setup (minimal generic Go app scaffolded and committed in a temp dir) per the 002 precedent — no new perpetual fixture PR required
- All four scenarios stay `status: draft`, keep the five-section format (Test PR / Setup / Action / Expected / Cleanup), carry only observable assertions, and each contains the literal `--security` flag
- Scenario 009 preserves its container-executable validator half (toolchain findings pass, invariant findings fail closed without a model) and adds the dependency-flag walk half
- The session-local security model is asserted to never land inside the fixture repo in every walk
</summary>

<objective>
Produce the four mandated acceptance scenarios under `scenarios/` — finalize the existing drafts 007 (IDOR-confirmed), 008 (IDOR-rejected-by-verifier), 009 (toolchain-fail-closed) by replacing their `TBD — task 4` fixture blocks with inline-built generic fixtures plus the exact `--security` invocation, and author the new 010 (security-zero-findings) — so each is a walkable end-to-end checklist with `status: draft`, observable assertions only, and the exact evidence strings the spec's operator rung greps for.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the generic-content rule (User, Order, Product, Customer only; no trading terms, no personal paths).

Read the four scenario files in full: `scenarios/007-security-idor-confirmed.md`, `scenarios/008-security-idor-rejected-by-verifier.md`, `scenarios/009-security-toolchain-fail-closed.md` (the drafts to finalize) and `scenarios/002-clean-pr-zero-findings.md` (the inline-fixture precedent: `WORK=$(mktemp -d) && cd "$WORK" && git clone ... . && git checkout -b <branch>` then apply an edit, commit, and diff — Setup / Action / Expected / Cleanup checkbox format). Also skim `scenarios/005-selector-clean-short-circuit.md` for the walk format (`tee stdout to /tmp/scenNNN-stdout.log, stderr to /tmp/scenNNN-stderr.log, capture exit code to /tmp/scenNNN-exit`). Note the 002/005 precedent that the walk runs in-place on a local-only branch — no origin remote, so `/coding:pr-review`'s worktree flow does not apply.

Read the scenario format guide at the in-container path `/home/node/.claude/plugins/marketplaces/dark-factory/docs/rules/scenario-writing.md` — frontmatter `status: draft`, H1 `# Scenario NNN: <one-line what-this-proves>`, a one-sentence "Validates that ..." description, checkbox sections, observable outcomes only, self-contained, one journey per file.

Read `docs/security/security-review-pipeline.md` (the model schema — `entry_points`, `resources[].authorization_functions`, `invariants[]` with `id`/`statement`/`evidence`/`attack_surfaces`; the session-local `/tmp/security-model.json` lifecycle) and `docs/security/security-review-guide.md` (the rule ids) — the concrete fixture details the scenarios cite.

Read `agents/security-verifier.md` (the verdict contract — `confirmed | plausible | rejected`, `counterevidence_checked`, `reject_reason`) and `scripts/validate-citations.sh` (the `SECURITY_MODEL_FILE` env var and the fail-closed `WARN: dropped` stderr line) — the exact strings the scenarios' Expected sections grep for.

Read the wired commands to confirm the surface the scenarios walk: `commands/pr-review.md` and `commands/local-review.md` (the `#### Security mode (under \`--security\` only)` subsection shipped by prompts 1 and 3) — the exact `--security` invocation and the Security Findings / Security Model report-section names.
</context>

<requirements>
1. **Hard dependency guard.** Verify all three command wirings shipped before editing the scenarios: `grep -l -- '--security' commands/pr-review.md commands/code-review.md commands/local-review.md | wc -l` must return `3`. If any command lacks the flag, STOP and report that prompts 1–3 must execute first — the walks exercise the wired commands and will fail without them.

2. **Shared format for all four scenario files.** Each file has frontmatter `status: draft`; an H1 `# Scenario NNN: <what this proves in one line>`; a one-sentence "Validates that ..." description; EXACTLY these five `## ` sections in this order: `## Test PR`, `## Setup`, `## Action`, `## Expected`, `## Cleanup`; and a closing walk-status line. Each `## Test PR` section describes the INLINE-BUILT generic fixture (no perpetual fixture PR, no TBD). Each `## Setup` / `## Action` / `## Expected` block is a list of `- [ ]` checkboxes with observable outcomes only (files on disk, git state, command output, exit codes, grep counts — never internal reasoning). Each file must contain at least 8 unchecked checkboxes total across Setup/Action/Expected/Cleanup, and at least one literal `--security` token in the Action block. Generic content only (User, Order, Product, Customer); no trading/project-specific content; no personal paths; no `~/`-only paths in fixture commands (use `$WORK` under `mktemp -d`). No `TBD` string anywhere in the 007/008/009 files (the fixture-PR TBD blocks are replaced).

3. **Scenario 007 — IDOR confirmed (finalize `scenarios/007-security-idor-confirmed.md`).**
   - `## Test PR`: replace the TBD block — the fixture is built inline: a minimal generic Go order app whose handler `pkg/handler/order.go` exposes `GET /orders/{order_id}` and resolves the order by ID with NO ownership authorization check (the IDOR bypass), while `pkg/authz/order.go` defines the `RequireOrderAccess` authorization function the handler should call but does not; the derived model registers invariant `INV-1` ("a member may only read orders they own") with `evidence: pkg/authz/order.go`.
   - `## Setup`: build the fixture inline. Use a two-commit shape so the review has a diff: on `master` commit the app WITH the ownership check called in the handler; on a feature branch remove the `RequireOrderAccess` call in `pkg/handler/order.go` and commit — the diff touches `pkg/handler/order.go` (the invariant's attack surface), forcing `INV-1` into the applicable set (deterministic invariant selection). Scaffold with `WORK=$(mktemp -d) && cd "$WORK" && go mod init example.com/order-app && mkdir -p pkg/handler pkg/authz && git init -q && git config user.email fixture@example.com && git config user.name fixture`. Include the Setup precondition that the session model carries `resources[order].authorization_functions` and `INV-1`, and that `SECURITY_MODEL_FILE` points at the session model so `scripts/validate-citations.sh` resolves `INV-1` (exit 0, kept).
   - `## Action`: run `/coding:local-review --security` in a fresh Claude Code session against `$WORK` (in-place — the fixture is a local-only branch with no origin remote; pr-review's worktree flow requires an origin, per the 005 precedent; plugin pinned to the branch under test); tee stdout to `/tmp/scen007-stdout.log`, stderr to `/tmp/scen007-stderr.log`, capture exit code to `/tmp/scen007-exit`. Confirm the verifier gate runs post-adjudication, pre-emission on the severity=critical candidate. With the two-commit shape, `HEAD~1` (local-review's diff) is the commit that removed the check, so the diff-relevant assertions hold.
   - `## Expected` (exact grep strings, matching AC10): `cat /tmp/scen007-exit` prints `0`; `grep -c '"confidence": "confirmed"' /tmp/scen007-stdout.log` ≥ 1; `grep -c 'attack_path' /tmp/scen007-stdout.log` ≥ 1; `grep -c 'counterevidence_checked' /tmp/scen007-stdout.log` ≥ 1; `grep -c '"exploitability": "high"' /tmp/scen007-stdout.log` ≥ 1 AND `grep -c '"impact": "high"' /tmp/scen007-stdout.log` ≥ 1; `grep -c '"blocking": true' /tmp/scen007-stdout.log` ≥ 1 (blocking formula holds); the finding survives at `severity=critical` in the final report; no `security-model.json` exists anywhere inside `$WORK` (`find "$WORK" -name security-model.json` returns nothing — the session model was never committed to the fixture repo); run completes in under 10 minutes (wall clock `real` < 10m).
   - `## Cleanup`: `rm -rf "$WORK" /tmp/scen007-*`.

4. **Scenario 008 — IDOR rejected by verifier (finalize `scenarios/008-security-idor-rejected-by-verifier.md`).**
   - `## Test PR`: replace the TBD block — the fixture is built inline: a minimal generic Go order app whose handler `pkg/handler/order.go` exposes `GET /orders/{order_id}` and IS guarded by a service-layer ownership check `RequireOrderAccess(orderID, userID)` defined in `pkg/authz/order.go`; the derived model's `resources[order].authorization_functions` lists the check with its `file:line` evidence and registers invariant `INV-1`.
   - `## Setup`: build the fixture inline (same scaffold shape as 007). Two-commit shape: on `master` commit the guarded app; on a feature branch touch `pkg/handler/order.go` (e.g. a cosmetic change that still exercises the handler path) and commit — the diff touches the invariant's attack surface so `INV-1` lands in the applicable set, and a candidate invariant-kind IDOR finding is raised during adjudication (`kind=invariant`, `invariant_id=INV-1`, `severity=major`, claiming `GET /orders/{order_id}` lacks an ownership check). Include the Setup precondition that `SECURITY_MODEL_FILE` points at the session model and the model's `resources[order].authorization_functions` lists the service-layer ownership check.
   - `## Action`: run `/coding:local-review --security` in a fresh Claude Code session against `$WORK` (in-place — the fixture is a local-only branch with no origin remote; pr-review's worktree flow requires an origin, per the 005 precedent; plugin pinned to the branch under test); tee stdout to `/tmp/scen008-stdout.log`, stderr to `/tmp/scen008-stderr.log`, capture exit code to `/tmp/scen008-exit`. Confirm the verifier gate runs on the candidate (security signal set, severity=major).
   - `## Expected` (exact grep strings, matching AC11): `cat /tmp/scen008-exit` prints `0`; `grep -c '"confidence": "rejected"' /tmp/scen008-stdout.log` ≥ 1; `grep -c 'reject_reason' /tmp/scen008-stdout.log` ≥ 1; the rejected finding does NOT emit — no `INV-1` entry appears in the final report's findings (absence assertion: `grep -c 'INV-1' /tmp/scen008-stdout.log` inside the findings region returns 0, or the report's findings list contains no INV-1 finding); `grep -c '"blocking": true' /tmp/scen008-stdout.log` returns 0 (a `rejected` verdict never satisfies the blocking formula); no `security-model.json` exists anywhere inside `$WORK`; run completes in under 10 minutes.
   - `## Cleanup`: `rm -rf "$WORK" /tmp/scen008-*`.

5. **Scenario 009 — toolchain fail-closed (finalize `scenarios/009-security-toolchain-fail-closed.md`).**
   - The validator half (already container-executable) stays: build a toolchain findings JSON `[{"kind": "toolchain", "tool": "osv-scanner", "package": "golang.org/x/crypto", "version": "v0.17.0", "advisory": "GHSA-45x7-px36-r8r7", "file": "go.mod", "line": 5}]` and an invariant findings JSON `[{"kind": "invariant", "invariant_id": "INV-1", "file": "pkg/authz/order.go", "line": 33}]`; run the validator over each with and without `SECURITY_MODEL_FILE`; assert toolchain passes (exit 0, kept, `jq '.findings | length'` = 1, no `rule_id` required) and the invariant run WITHOUT a model drops fail-closed (exit 1, `WARN: dropped` on stderr naming `INV-1`, kept set empty).
   - `## Test PR`: replace the TBD block — the walk half fixture is built inline: a minimal generic Go app whose `go.mod` requires the vulnerable `golang.org/x/crypto v0.17.0` (imported, e.g. `golang.org/x/crypto/bcrypt`, so govulncheck/osv-scanner flag it) plus a minimal `main.go`; the derived model registers invariant `INV-1`.
   - `## Setup`: include both the validator JSON fixtures (from the existing draft) and the inline-built vulnerable-app fixture (scaffold shape as in requirement 3; on `master` commit the app with the vulnerable dependency).
   - `## Action`: run the two validator invocations exactly as the existing draft does (`bash scripts/validate-citations.sh toolchain-findings.json` and `bash scripts/validate-citations.sh invariant-findings.json` with `SECURITY_MODEL_FILE` UNSET for the invariant run), capturing exit codes and stdout/stderr to `/tmp/scen009-*`; AND run `/coding:local-review --security` in a fresh Claude Code session against the vulnerable-app fixture `$WORK` (plugin pinned to the branch under test), teeing stdout to `/tmp/scen009-stdout.log`, stderr to `/tmp/scen009-stderr.log`, exit code to `/tmp/scen009-exit`.
   - `## Expected` (exact grep strings, matching AC12): the validator half — `cat /tmp/scen009-toolchain-exit` prints `0`, `jq '.findings | length' /tmp/scen009-toolchain-out.json` prints `1`; `cat /tmp/scen009-invariant-exit` prints `1`; `grep -c 'WARN: dropped' /tmp/scen009-invariant-err` ≥ 1 AND `grep -c 'INV-1' /tmp/scen009-invariant-err` ≥ 1; `jq '.findings | length' /tmp/scen009-invariant-out.json` prints `0`. The walk half — `cat /tmp/scen009-exit` prints `0`; the toolchain finding surfaces as a Must-Fix item in the report, never a silent skip: `grep -c 'GHSA-45x7-px36-r8r7' /tmp/scen009-stdout.log` ≥ 1 AND `grep -c 'golang.org/x/crypto' /tmp/scen009-stdout.log` ≥ 1; no `security-model.json` exists anywhere inside `$WORK`; run completes in under 10 minutes.
   - `## Cleanup`: `rm -rf "$WORK" /tmp/scen009-*`.

6. **Scenario 010 — security-zero-findings (author new `scenarios/010-security-zero-findings.md`).**
   - `## Test PR`: the fixture is built inline — a clean minimal generic Go HTTP app with a properly guarded order resource (ownership check called in the handler), no weak crypto, no hardcoded secrets, no string-interpolated SQL — a diff with no security-relevant violations.
   - `## Setup`: scaffold as in requirement 3; on `master` commit the clean app; on a feature branch make a benign Go change that introduces nothing security-relevant (e.g. add a pure helper function or a doc comment) and commit, so the review has a Go diff with no security findings.
   - `## Action`: run `/coding:local-review --security` in a fresh Claude Code session against `$WORK` (in-place — the fixture is a local-only branch with no origin remote; pr-review's worktree flow requires an origin, per the 005 precedent; plugin pinned to the branch under test); tee stdout to `/tmp/scen010-stdout.log`, stderr to `/tmp/scen010-stderr.log`, capture exit code to `/tmp/scen010-exit`.
   - `## Expected` (exact grep strings, matching AC9): `cat /tmp/scen010-exit` prints `0`; `grep -c 'Security Findings' /tmp/scen010-stdout.log` ≥ 1 (the section is present with zero rule/invariant findings — no finding blocks); `grep -c 'Security Model' /tmp/scen010-stdout.log` ≥ 1 (the provenance block is present — `derived_from`, entry-point count, inventory counts); `grep -c '"blocking": true' /tmp/scen010-stdout.log` returns 0; no `security-model.json` exists anywhere inside `$WORK`; run completes in under 10 minutes.
   - `## Cleanup`: `rm -rf "$WORK" /tmp/scen010-*`.
   - The H1 title follows the other security scenarios, e.g. `# Scenario 010: Security mode on a clean generic Go app reports zero findings with a Security Model provenance block`.

7. **Closing walk-status lines.** Each of the four files ends with a status line reflecting that they are now walkable, e.g. `**Status**: draft — walkable after the \`--security\` command wiring (spec 010) merges; not promoted to active.` (no `TBD`, no `active`). Do NOT promote any scenario to `active` — they are walked on the operator rung after merge.

8. **Do NOT touch** (beyond the four scenario files): any `commands/*.md`, any `docs/*`, `scripts/*`, `agents/*`, `rules/*`, `README.md`, `llms.txt`, `CHANGELOG.md`, or any other `scenarios/*.md`. Do NOT add the new scenario files to the README or llms scenario tables (prompt 5 owns the README rows).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands inside this prompt's container verification; the `git clone`/`git init`/`git commit` commands the scenarios' Setup sections describe are instructions for the HOST-side walker (operator rung), not commands this prompt executes.
- Scenarios live in `scenarios/` (next after 006); the existing drafts 007/008/009 are finalized in place (same filenames), 010 is new. Fixtures are built inline in each scenario's Setup (scaffold a minimal generic Go app + apply the violating code, per the 002 precedent) — no new perpetual fixture PR required.
- Each scenario stays `status: draft` — none is promoted to `active` (walkable only after the `--security` wiring merges and is walked on the host).
- Scenario 007/008/009 must contain ZERO `TBD` (the `TBD — task 4` fixture blocks are replaced). Each of the four files must contain ≥1 literal `--security` token and ≥8 unchecked checkboxes.
- The session-local security model (`security-model.json`) is never committed to any repo — every walk's Expected block asserts no `security-model.json` inside the fixture `$WORK`.
- Generic content only: fixtures and examples use User, Order, Product, Customer — never trading/project-specific content, never personal paths (`~/`/`/Users/bborbe/`), and fixture commands use `$WORK` under `mktemp -d`.
- Observable assertions only — no internal struct/function checks, no references to unreleased internals.
- The scenario WALKS (AC9–AC12) are operator-executable on the host after merge — they do NOT run inside this prompt's container. This prompt only authors the four files.
- Existing tests must still pass: `make precommit` (incl. `check-links`, which validates README/llms links only — the scenario files are not linked until prompt 5 adds the README rows) exits 0.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- AC7: scenario files present and finalized ---
ls scenarios/010-security-zero-findings.md                    # must succeed
grep -c 'status: draft' scenarios/010-security-zero-findings.md   # >= 1

# No TBD anywhere in the three finalized drafts (count must print 0 per file)
grep -c 'TBD' scenarios/007-security-idor-confirmed.md scenarios/008-security-idor-rejected-by-verifier.md scenarios/009-security-toolchain-fail-closed.md
! grep -q 'TBD' scenarios/007-security-idor-confirmed.md scenarios/008-security-idor-rejected-by-verifier.md scenarios/009-security-toolchain-fail-closed.md

# Per-file: --security present, >=8 unchecked checkboxes, the five required sections
for f in 007-security-idor-confirmed 008-security-idor-rejected-by-verifier 009-security-toolchain-fail-closed 010-security-zero-findings; do
  echo "== $f =="
  grep -c -- '--security' "scenarios/$f.md"    # >= 1 per file
  grep -c '^- \[ \]' "scenarios/$f.md"          # >= 8 per file
  grep -c '^## Test PR' "scenarios/$f.md"       # == 1 per file
  grep -c '^## Setup' "scenarios/$f.md"         # == 1 per file
  grep -c '^## Action' "scenarios/$f.md"        # == 1 per file
  grep -c '^## Expected' "scenarios/$f.md"      # == 1 per file
  grep -c '^## Cleanup' "scenarios/$f.md"       # == 1 per file
done

# Every walk asserts the session model never lands in the fixture repo
for f in 007-security-idor-confirmed 008-security-idor-rejected-by-verifier 009-security-toolchain-fail-closed 010-security-zero-findings; do
  grep -c 'security-model.json' "scenarios/$f.md"   # >= 1 per file
done

# --- AC1: repo integrity ---
make precommit    # must exit 0
```
</verification>

<!-- OPEN QUESTION for the human reviewer: (1) RESOLVED — all four walks use `/coding:local-review --security` (in-place), because the inline-built fixtures are local-only branches with no origin remote and pr-review's worktree flow unconditionally runs `git fetch origin` (commands/pr-review.md Step 0b; documented in scenario 005). The spec's operator rung is reconciled to match. (2) The scenario Expected blocks assert the verifier's JSON field strings (`"confidence": "confirmed"`, `counterevidence_checked`, `reject_reason`, `"blocking": true`) appear in the review stdout — the wired commands must surface these fields for the walks to pass; if the report renders verdicts as prose instead of JSON, AC10/AC11/AC12's grep evidence will need adjusting at walk time. (3) The `## Test PR` section (present in the existing drafts) is kept as the first of the five sections alongside Setup/Action/Expected/Cleanup — this matches the repo's own scenario convention and the draft files' current shape. -->
