# Security Review Guide

Companion to `go-security-linting.md` (the gosec workflow) and `teamvault-conventions.md` (secret handling). This guide is the source of truth for the mechanical security rule base that Security Review Mode enforces: every rule maps to a detector in `rules/security/*.yml` and an entry in `rules/index.json` owned by `go-security-specialist`.

## Tiers

Security Review Mode organizes rules into three tiers:

- **Mechanical tier** — MUST-level rules enforced by ast-grep detectors (`rules/security/*.yml`). A detector either fires or it does not; enforcement is the YAML path.
- **Judgment tier** — MUST-level rules that require LLM adjudication at review time (SSRF, authorization/IDOR, invariant-preservation concerns).
- **Invariant tier** — rules that require whole-repo reasoning rather than a single AST shape.

The judgment and invariant tiers ship in a follow-up task. This guide currently contains the 5 mechanical-tier rules below.

## Rules

### RULE go-security/tls-insecure-skip-verify (MUST)

**Owner**: go-security-specialist
**Applies when**: a `tls.Config` composite literal sets `InsecureSkipVerify: true` in a `*.go` file outside `*_test.go` and `vendor/`.
**Enforcement**: `rules/security/tls-insecure-skip-verify.yml`
**Why**: disabling certificate verification makes a TLS connection trivially vulnerable to man-in-the-middle attacks; the failure mode is silent exposure of credentials and secrets to an active attacker.

#### Bad

```go
client := &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
    },
}
```

#### Good

```go
client := &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12},
    },
}
```
