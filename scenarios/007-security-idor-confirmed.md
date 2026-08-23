---
status: draft
---

# Scenario 007: Verifier confirms a critical IDOR finding on an order-resource handler and blocks merge

Validates that in security mode, the verifier gate confirms an invariant-kind IDOR finding on a generic order-resource handler — verdict `confirmed` with a concrete attacker scenario and a populated `counterevidence_checked` — the finding survives at severity=critical, and the blocking model blocks merge because `confidence==confirmed ∧ exploitability==high ∧ impact≥medium`.

## Test PR

The fixture is built inline in Setup (no perpetual fixture PR): a minimal generic Go order app scaffolded under `$WORK` whose handler `pkg/handler/order.go` exposes `GET /orders/{order_id}` and resolves the order by ID with NO ownership authorization check (the IDOR bypass), while `pkg/authz/order.go` defines the `RequireOrderAccess` authorization function the handler should call but does not. The derived session security model registers invariant `INV-1` ("a member may only read orders they own") with `evidence: pkg/authz/order.go`. The review's diff (feature branch vs `HEAD~1`) is the commit that removed the ownership check from `pkg/handler/order.go`, so the invariant's attack surface is touched.

## Setup

- [ ] Scaffold the fixture repo: `WORK=$(mktemp -d) && cd "$WORK" && go mod init example.com/order-app && mkdir -p pkg/handler pkg/authz && git init -q && git config user.email fixture@example.com && git config user.name fixture`
- [ ] Write the guarded app on `master`: `pkg/handler/order.go` exposes `GET /orders/{order_id}` and calls `RequireOrderAccess` before resolving the order; `pkg/authz/order.go` defines the ownership authorization function; commit `git add -A && git commit -qm 'order app with ownership check'`
- [ ] Create the feature branch and remove the `RequireOrderAccess` call in `pkg/handler/order.go` so the handler resolves orders by ID unguarded: `git checkout -b idor-removed && <remove the RequireOrderAccess call> && git add pkg/handler/order.go && git commit -qm 'remove ownership check'`
- [ ] The review's diff touches `pkg/handler/order.go` — the invariant's attack surface — so `INV-1` lands in the applicable set (deterministic invariant selection), and `HEAD~1` (local-review's diff scope) is the commit that removed the check
- [ ] Derive the session security model per `docs/security/security-review-pipeline.md` — the model carries `resources[order].authorization_functions` and the invariant `INV-1` with `evidence: pkg/authz/order.go`
- [ ] Adjudication emits an invariant-kind finding: `kind=invariant`, `invariant_id=INV-1`, `severity=critical`, `file=pkg/handler/order.go`, citing `GET /orders/{order_id}` as the sink
- [ ] `SECURITY_MODEL_FILE` points at the session model (`/tmp/security-model.json`) so `scripts/validate-citations.sh` resolves `INV-1` (exit 0, kept)

## Action

- [ ] Run the security-mode review over `$WORK` in a fresh Claude Code session (in-place — the fixture is a local-only branch with no origin remote, which `/coding:pr-review`'s worktree flow does not support; plugin pinned to the branch under test): `/coding:local-review --security`; tee stdout to `/tmp/scen007-stdout.log`, stderr to `/tmp/scen007-stderr.log`, capture exit code to `/tmp/scen007-exit`
- [ ] Confirm the verifier gate runs post-adjudication, pre-emission on the severity=critical candidate (per the `docs/selector-mode-guide.md` Verifier gate section)

## Expected

- [ ] `cat /tmp/scen007-exit` prints `0`
- [ ] The finding's verifier verdict is `confirmed`: `grep -c '"confidence": "confirmed"' /tmp/scen007-stdout.log` ≥ 1
- [ ] The verdict carries a concrete step-by-step attacker scenario in `attack_path`: `grep -c 'attack_path' /tmp/scen007-stdout.log` ≥ 1
- [ ] `counterevidence_checked` is populated with the counterevidence actually checked and why it does not hold (no route middleware guard on the sink; the ownership check is no longer called from this handler): `grep -c 'counterevidence_checked' /tmp/scen007-stdout.log` ≥ 1
- [ ] The finding survives at `severity=critical` in the final report
- [ ] The blocking model blocks merge — `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` holds: `grep -c '"exploitability": "high"' /tmp/scen007-stdout.log` ≥ 1 and `grep -c '"impact": "high"' /tmp/scen007-stdout.log` ≥ 1
- [ ] The derived blocking state is `blocking=true` for the finding: `grep -c '"blocking": true' /tmp/scen007-stdout.log` ≥ 1
- [ ] The session security model never lands in the fixture repo — `find "$WORK" -name security-model.json` returns nothing
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen007-*`

---

**Status**: draft — walkable after the `--security` command wiring (spec 010) merges; not promoted to active.
