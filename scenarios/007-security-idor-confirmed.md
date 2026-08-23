---
status: draft
---

# Scenario 007: Verifier confirms a critical IDOR finding on an order-resource handler and blocks merge

Validates that in security mode, the verifier gate confirms an invariant-kind IDOR finding on a generic order-resource handler — verdict `confirmed` with a concrete attacker scenario and a populated `counterevidence_checked` — the finding survives at severity=critical, and the blocking model blocks merge because `confidence==confirmed ∧ exploitability==high ∧ impact≥medium`.

## Test PR

TBD — task 4 names the security-mode fixture PR; expected shape: a public fixture repo whose `order` resource handler (e.g. `pkg/handler/order.go` exposing `GET /orders/{order_id}`) resolves the order by ID with no ownership authorization check, and whose derived security model registers the invariant `INV-1` ("a member may only read orders they own") with evidence in `pkg/authz/order.go`.

## Setup

- [ ] Derive the session security model per `docs/security/security-review-pipeline.md` — the model carries `resources[order].authorization_functions` and the invariant `INV-1` with `evidence: pkg/authz/order.go:33`
- [ ] Diff touches `pkg/handler/order.go` — the invariant's attack surface — so `INV-1` lands in the applicable set (deterministic invariant selection)
- [ ] Adjudication emits an invariant-kind finding: `kind=invariant`, `invariant_id=INV-1`, `severity=critical`, `file=pkg/handler/order.go`, citing `GET /orders/{order_id}` as the sink
- [ ] `SECURITY_MODEL_FILE` points at the session model so `scripts/validate-citations.sh` resolves `INV-1` (exit 0, kept)

## Action

- [ ] Run the security-mode review over the fixture repo in a fresh Claude Code session; tee stdout to `/tmp/scen007-stdout.log`, stderr to `/tmp/scen007-stderr.log`, capture exit code to `/tmp/scen007-exit`
- [ ] Confirm the verifier gate runs post-adjudication, pre-emission on the severity=critical candidate (per the `docs/selector-mode-guide.md` Verifier gate section)

## Expected

- [ ] `cat /tmp/scen007-exit` prints `0`
- [ ] The finding's verifier verdict is `confirmed`: `grep -c '"confidence": "confirmed"' /tmp/scen007-stdout.log` ≥ 1
- [ ] The verdict carries a concrete step-by-step attacker scenario in `attack_path`: `grep -c 'attack_path' /tmp/scen007-stdout.log` ≥ 1
- [ ] `counterevidence_checked` is populated with the counterevidence actually checked and why it does not hold (no route middleware guard on the sink; the ownership check covers another path only): `grep -c 'counterevidence_checked' /tmp/scen007-stdout.log` ≥ 1
- [ ] The finding survives at `severity=critical` in the final report
- [ ] The blocking model blocks merge — `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` holds: `grep -c '"exploitability": "high"' /tmp/scen007-stdout.log` ≥ 1 and `grep -c '"impact": "high"' /tmp/scen007-stdout.log` ≥ 1
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen007-*`

---

**Status**: draft — not walked; walkable after task 4 wires the security-review signal. Not promoted to active.
