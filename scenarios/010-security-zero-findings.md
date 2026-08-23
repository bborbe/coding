---
status: draft
---

# Scenario 010: Security mode on a clean generic Go app reports zero findings with a Security Model provenance block

Validates that in security mode, `/coding:local-review --security` over a clean generic Go HTTP app with a properly guarded order resource and a diff with no security-relevant violations reports a `Security Findings` section with zero rule/invariant findings, still emits the `Security Model` provenance block (`derived_from`, entry-point count, inventory counts), and blocks nothing.

## Test PR

The fixture is built inline in Setup (no perpetual fixture PR): a clean minimal generic Go HTTP app scaffolded under `$WORK` with a properly guarded order resource — the ownership check is called in the handler, no weak crypto, no hardcoded secrets, no string-interpolated SQL — and a feature-branch diff that introduces nothing security-relevant.

## Setup

- [ ] Scaffold the fixture repo: `WORK=$(mktemp -d) && cd "$WORK" && go mod init example.com/order-app && mkdir -p pkg/handler pkg/authz && git init -q && git config user.email fixture@example.com && git config user.name fixture`
- [ ] Write the clean app on `master`: `pkg/handler/order.go` exposes `GET /orders/{order_id}` and calls `RequireOrderAccess(orderID, userID)` before resolving; `pkg/authz/order.go` defines the service-layer ownership check; no weak crypto, no hardcoded secrets, no string-interpolated SQL anywhere; commit `git add -A && git commit -qm 'clean guarded order app'`
- [ ] Create the feature branch and make a benign Go change that introduces nothing security-relevant (e.g. add a pure helper function or a doc comment): `git checkout -b benign-helper && <add the benign Go change> && git add -A && git commit -qm 'add benign helper'`
- [ ] The review's diff (`HEAD~1`) is a Go diff with no security-relevant violations
- [ ] Derive the session security model per `docs/security/security-review-pipeline.md` — the model derives with the guarded resource and its authorization function

## Action

- [ ] Run the security-mode review over `$WORK` in a fresh Claude Code session (in-place — the fixture is a local-only branch with no origin remote, which `/coding:pr-review`'s worktree flow does not support; plugin pinned to the branch under test): `/coding:local-review --security`; tee stdout to `/tmp/scen010-stdout.log`, stderr to `/tmp/scen010-stderr.log`, capture exit code to `/tmp/scen010-exit`

## Expected

- [ ] `cat /tmp/scen010-exit` prints `0`
- [ ] The `Security Findings` section is present: `grep -c 'Security Findings' /tmp/scen010-stdout.log` ≥ 1
- [ ] The `Security Findings` section lists zero rule/invariant findings — no finding blocks with `file:` evidence inside the region (or the section reads `None.`): `awk '/^#### Security Findings/{flag=1; next} /^#### /{flag=0} flag' /tmp/scen010-stdout.log | grep -c 'file:'` prints `0`
- [ ] The `Security Model` provenance block is present — `derived_from`, entry-point count, inventory counts: `grep -c 'Security Model' /tmp/scen010-stdout.log` ≥ 1
- [ ] No finding is blocking — no verifier verdict satisfies `confidence==confirmed ∧ exploitability==high ∧ impact≥medium`: `grep -c '"blocking": true' /tmp/scen010-stdout.log` returns `0`
- [ ] The session security model never lands in the fixture repo — `find "$WORK" -name security-model.json` returns nothing
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen010-*`

---

**Status**: draft — walkable after the `--security` command wiring (spec 010) merges; not promoted to active.
