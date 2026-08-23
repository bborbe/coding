---
status: draft
---

# Scenario 009: Toolchain findings pass citation validation while invariant findings fail closed without a security model

Validates that the polymorphic citation contract holds both ways: a `kind: toolchain` finding (osv-scanner/trivy output) passes `scripts/validate-citations.sh` with no `rule_id` (exit 0, kept), while a `kind: invariant` finding run without `SECURITY_MODEL_FILE` drops fail-closed (exit 1, `WARN: dropped` on stderr naming the `invariant_id`); and that a `--security` review surfaces the toolchain finding as a Must-Fix item in the report, never a silent skip.

## Test PR

The fixture is built inline in Setup (no perpetual fixture PR): a minimal generic Go app scaffolded under `$WORK` whose `go.mod` requires the vulnerable `golang.org/x/crypto v0.17.0`, imported (e.g. via `golang.org/x/crypto/bcrypt` in `main.go`) so govulncheck/osv-scanner flag it, plus a minimal `main.go`. The derived security model registers invariant `INV-1`. The validator half needs no fixture repo — it runs over two hand-built findings JSON files from the coding repo root.

## Setup

- [ ] Build the toolchain findings JSON: `printf '%s' '[{"kind": "toolchain", "tool": "osv-scanner", "package": "golang.org/x/crypto", "version": "v0.17.0", "advisory": "GHSA-45x7-px36-r8r7", "file": "go.mod", "line": 5}]' > /tmp/scen009-toolchain-findings.json`
- [ ] Build the invariant findings JSON: `printf '%s' '[{"kind": "invariant", "invariant_id": "INV-1", "file": "pkg/authz/order.go", "line": 33}]' > /tmp/scen009-invariant-findings.json`
- [ ] Do NOT set `SECURITY_MODEL_FILE` for the invariant run — the absent model is the fail-closed condition
- [ ] Scaffold the vulnerable-app fixture: `WORK=$(mktemp -d) && cd "$WORK" && go mod init example.com/order-app && git init -q && git config user.email fixture@example.com && git config user.name fixture`
- [ ] Write `go.mod` requiring `golang.org/x/crypto v0.17.0` and a minimal `main.go` importing `golang.org/x/crypto/bcrypt`; commit on `master`: `git add -A && git commit -qm 'app with vulnerable x/crypto'`
- [ ] Derive the session security model per `docs/security/security-review-pipeline.md` — the model registers invariant `INV-1`

## Action

- [ ] Run the validator over the toolchain findings (from the coding repo root, where `rules/index.json` resolves — NOT inside `$WORK`): `bash scripts/validate-citations.sh /tmp/scen009-toolchain-findings.json > /tmp/scen009-toolchain-out.json 2> /tmp/scen009-toolchain-err; echo $? > /tmp/scen009-toolchain-exit`
- [ ] Run the validator over the invariant findings without a model: `bash scripts/validate-citations.sh /tmp/scen009-invariant-findings.json > /tmp/scen009-invariant-out.json 2> /tmp/scen009-invariant-err; echo $? > /tmp/scen009-invariant-exit`
- [ ] Run the security-mode review over `$WORK` in a fresh Claude Code session (in-place — the fixture is a local-only branch with no origin remote, which `/coding:pr-review`'s worktree flow does not support; plugin pinned to the branch under test): `/coding:local-review --security`; tee stdout to `/tmp/scen009-stdout.log`, stderr to `/tmp/scen009-stderr.log`, capture exit code to `/tmp/scen009-exit`

## Expected

- [ ] Toolchain findings pass citation validation: `cat /tmp/scen009-toolchain-exit` prints `0` and the finding is kept — `jq '.findings | length' /tmp/scen009-toolchain-out.json` prints `1`, with no `rule_id` required
- [ ] Invariant findings without a model drop fail-closed: `cat /tmp/scen009-invariant-exit` prints `1`
- [ ] The drop is logged to stderr as `WARN: dropped` naming the `invariant_id`: `grep -c 'WARN: dropped' /tmp/scen009-invariant-err` ≥ 1 and `grep -c 'INV-1' /tmp/scen009-invariant-err` ≥ 1
- [ ] The kept set is empty for the fail-closed run: `jq '.findings | length' /tmp/scen009-invariant-out.json` prints `0`
- [ ] The walk completes cleanly: `cat /tmp/scen009-exit` prints `0`
- [ ] The toolchain finding surfaces as a Must-Fix item in the report, never a silent skip: `grep -c 'GHSA-45x7-px36-r8r7' /tmp/scen009-stdout.log` ≥ 1 and `grep -c 'golang.org/x/crypto' /tmp/scen009-stdout.log` ≥ 1
- [ ] The session security model never lands in the fixture repo — `find "$WORK" -name security-model.json` returns nothing
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen009-*`

---

**Status**: draft — walkable after the `--security` command wiring (spec 010) merges; not promoted to active.
