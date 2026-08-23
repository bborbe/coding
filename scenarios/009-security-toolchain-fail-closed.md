---
status: draft
---

# Scenario 009: Toolchain findings pass citation validation while invariant findings fail closed without a security model

Validates that the polymorphic citation contract holds both ways: a `kind: toolchain` finding (osv-scanner/trivy output) passes `scripts/validate-citations.sh` with no `rule_id` (exit 0, kept), while a `kind: invariant` finding run without `SECURITY_MODEL_FILE` drops fail-closed (exit 1, `WARN: dropped` on stderr naming the `invariant_id`).

## Test PR

TBD — task 4 names the security-mode fixture PR; expected shape: a public fixture repo whose `go.mod` carries a vulnerable dependency flagged by osv-scanner/trivy (the toolchain finding) and an `order` resource handler whose derived security model registers the invariant `INV-1` (the invariant finding).

## Setup

- [ ] Build a toolchain findings JSON from osv-scanner/trivy output: `[{"kind": "toolchain", "tool": "osv-scanner", "package": "golang.org/x/crypto", "version": "v0.17.0", "advisory": "GHSA-45x7-px36-r8r7", "file": "go.mod", "line": 5}]`
- [ ] Build an invariant findings JSON: `[{"kind": "invariant", "invariant_id": "INV-1", "file": "pkg/authz/order.go", "line": 33}]`
- [ ] Do NOT set `SECURITY_MODEL_FILE` for the invariant run — the absent model is the fail-closed condition

## Action

- [ ] Run the validator over the toolchain findings: `bash scripts/validate-citations.sh toolchain-findings.json > /tmp/scen009-toolchain-out.json; echo $? > /tmp/scen009-toolchain-exit`
- [ ] Run the validator over the invariant findings without a model: `bash scripts/validate-citations.sh invariant-findings.json > /tmp/scen009-invariant-out.json 2> /tmp/scen009-invariant-err; echo $? > /tmp/scen009-invariant-exit`

## Expected

- [ ] Toolchain findings pass citation validation: `cat /tmp/scen009-toolchain-exit` prints `0` and the finding is kept — `jq '.findings | length' /tmp/scen009-toolchain-out.json` prints `1`, with no `rule_id` required
- [ ] Invariant findings without a model drop fail-closed: `cat /tmp/scen009-invariant-exit` prints `1`
- [ ] The drop is logged to stderr as `WARN: dropped` naming the `invariant_id`: `grep -c 'WARN: dropped' /tmp/scen009-invariant-err` ≥ 1 and `grep -c 'INV-1' /tmp/scen009-invariant-err` ≥ 1
- [ ] The kept set is empty for the fail-closed run: `jq '.findings | length' /tmp/scen009-invariant-out.json` prints `0`
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen009-*`

---

**Status**: draft — not walked; the validator half is container-executable now, the fixture-PR half becomes walkable after task 4 wires the security-review signal. Not promoted to active.
