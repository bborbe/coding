---
status: draft
---

# Scenario 008: Verifier rejects an IDOR claim because service-layer authorization is found

Validates that in security mode, the verifier gate rejects an invariant-kind IDOR claim on a generic order-resource handler when an ownership authorization check is found — verdict `rejected` with `reject_reason` recorded, the finding does NOT emit, and the blocking model does not block merge.

## Test PR

The fixture is built inline in Setup (no perpetual fixture PR): a minimal generic Go order app scaffolded under `$WORK` whose handler `pkg/handler/order.go` exposes `GET /orders/{order_id}` and IS guarded by a service-layer ownership check `RequireOrderAccess(orderID, userID)` defined in `pkg/authz/order.go`. The derived security model's `resources[order].authorization_functions` lists the check with its `file:line` evidence and registers invariant `INV-1`. The review's diff (feature branch vs `HEAD~1`) touches the guarded handler but introduces no authorization gap.

## Setup

- [ ] Scaffold the fixture repo: `WORK=$(mktemp -d) && cd "$WORK" && go mod init example.com/order-app && mkdir -p pkg/handler pkg/authz && git init -q && git config user.email fixture@example.com && git config user.name fixture`
- [ ] Write the guarded app on `master`: `pkg/handler/order.go` exposes `GET /orders/{order_id}` and calls `RequireOrderAccess(orderID, userID)` before resolving; `pkg/authz/order.go` defines the service-layer ownership check; commit `git add -A && git commit -qm 'guarded order app'`
- [ ] Create the feature branch and touch `pkg/handler/order.go` (a cosmetic change that still exercises the handler path): `git checkout -b cosmetic-change && <make a cosmetic change to pkg/handler/order.go> && git add pkg/handler/order.go && git commit -qm 'cosmetic handler change'`
- [ ] The diff touches `pkg/handler/order.go` — the invariant's attack surface — so `INV-1` lands in the applicable set (deterministic invariant selection), and a candidate IDOR finding is raised during adjudication: `kind=invariant`, `invariant_id=INV-1`, `severity=major`, `file=pkg/handler/order.go`, claiming `GET /orders/{order_id}` lacks an ownership check
- [ ] `SECURITY_MODEL_FILE` points at the session model; the model's `resources[order].authorization_functions` lists the service-layer ownership check with its `file:line` evidence

## Action

- [ ] Run the security-mode review over `$WORK` in a fresh Claude Code session (in-place — the fixture is a local-only branch with no origin remote, which `/coding:pr-review`'s worktree flow does not support; plugin pinned to the branch under test): `/coding:local-review --security`; tee stdout to `/tmp/scen008-stdout.log`, stderr to `/tmp/scen008-stderr.log`, capture exit code to `/tmp/scen008-exit`
- [ ] Confirm the verifier gate runs on the candidate (security signal set, severity=major)

## Expected

- [ ] `cat /tmp/scen008-exit` prints `0`
- [ ] The candidate's verifier verdict is `rejected`: `grep -c '"confidence": "rejected"' /tmp/scen008-stdout.log` ≥ 1
- [ ] `reject_reason` is recorded naming the checklist item or counterevidence that killed the finding — item 3 (authorization-absence search) found the service-layer ownership check: `grep -c 'reject_reason' /tmp/scen008-stdout.log` ≥ 1
- [ ] The rejected finding does NOT emit — the final report's findings list contains no `INV-1` finding: `awk '/^#### Security Findings/{flag=1; next} /^#### /{flag=0} flag' /tmp/scen008-stdout.log | grep -c 'INV-1'` prints `0` (or the report's findings list contains no `INV-1` entry)
- [ ] No merge block is produced — a `rejected` verdict never satisfies `confidence==confirmed ∧ exploitability==high ∧ impact≥medium`: `grep -c '"blocking": true' /tmp/scen008-stdout.log` returns `0`
- [ ] The session security model never lands in the fixture repo — `find "$WORK" -name security-model.json` returns nothing
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen008-*`

---

**Status**: draft — walkable after the `--security` command wiring (spec 010) merges; not promoted to active.
