---
status: draft
---

# Scenario 008: Verifier rejects an IDOR claim because service-layer authorization is found

Validates that in security mode, the verifier gate rejects an invariant-kind IDOR claim on a generic order-resource handler when an ownership authorization check is found — verdict `rejected` with `reject_reason` recorded, the finding does NOT emit, and the blocking model does not block merge.

## Test PR

TBD — task 4 names the security-mode fixture PR; expected shape: a public fixture repo whose `order` resource handler (e.g. `pkg/handler/order.go` exposing `GET /orders/{order_id}`) looks like it exposes cross-member data but is actually guarded by a service-layer ownership authorization check (e.g. `RequireOrderAccess(orderID, userID)` in `pkg/authz/order.go`), and whose derived security model registers the invariant `INV-1`.

## Setup

- [ ] Diff touches `pkg/handler/order.go`, so the model's invariant `INV-1` lands in the applicable set (deterministic invariant selection)
- [ ] A candidate IDOR finding is raised: `kind=invariant`, `invariant_id=INV-1`, `severity=major`, `file=pkg/handler/order.go`, claiming `GET /orders/{order_id}` lacks an ownership check
- [ ] `SECURITY_MODEL_FILE` points at the session model; the model's `resources[order].authorization_functions` lists the service-layer ownership check with its `file:line` evidence

## Action

- [ ] Run the security-mode review over the fixture repo in a fresh Claude Code session; tee stdout to `/tmp/scen008-stdout.log`, stderr to `/tmp/scen008-stderr.log`, capture exit code to `/tmp/scen008-exit`
- [ ] Confirm the verifier gate runs on the candidate (security signal set, severity=major)

## Expected

- [ ] `cat /tmp/scen008-exit` prints `0`
- [ ] The candidate's verifier verdict is `rejected`: `grep -c '"confidence": "rejected"' /tmp/scen008-stdout.log` ≥ 1
- [ ] `reject_reason` is recorded naming the checklist item or counterevidence that killed the finding — item 3 (authorization-absence search) found the service-layer ownership check: `grep -c 'reject_reason' /tmp/scen008-stdout.log` ≥ 1
- [ ] The rejected finding does NOT emit — no `INV-1` entry appears in the final report's findings
- [ ] No merge block is produced for this finding — the blocking formula `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` is not satisfied by a `rejected` verdict
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen008-*`

---

**Status**: draft — not walked; walkable after task 4 wires the security-review signal. Not promoted to active.
