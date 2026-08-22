# Security Review Guide

Companion to [go-security-linting.md](go-security-linting.md) (the gosec workflow), [teamvault-conventions.md](teamvault-conventions.md) (secret handling), and [rule-block-schema.md](../rule-block-schema.md) (the `### RULE` block contract). This guide is the source of truth for the mechanical security rule base that Security Review Mode enforces: every rule maps to a detector in `rules/security/*.yml` and an entry in `rules/index.json` owned by `go-security-specialist`.

## Tiers

Security Review Mode organizes rules into three tiers:

- **Mechanical tier** — MUST-level rules enforced by ast-grep detectors (`rules/security/*.yml`). A detector either fires or it does not; enforcement is the YAML path.
- **Judgment tier** — MUST-level rules that require LLM adjudication at review time (SSRF, authorization/IDOR, invariant-preservation concerns).
- **Invariant tier** — rules that require whole-repo reasoning rather than a single AST shape.

The judgment and invariant tiers ship in a follow-up task. This guide currently contains the 5 mechanical-tier rules below.

## Rules

### RULE go-security/tls-insecure-skip-verify (MUST)

**Owner**: go-security-specialist
**Applies when**: a `tls.Config` composite literal sets `InsecureSkipVerify: true` in a `*.go` file outside `*_test.go`, `vendor/`, and `mocks/`.
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

### RULE go-security/crypto-insecure-random (MUST)

**Owner**: go-security-specialist
**Applies when**: a `*.go` file outside `*_test.go`, `vendor/`, and `mocks/` imports `math/rand` or `math/rand/v2` (the Go standard library's predictable PRNGs).
**Enforcement**: `rules/security/crypto-insecure-random.yml` (mechanical flag — fires on every import of `math/rand`/`math/rand/v2`; the judgment-tier adjudication of whether the usage is security-relevant ships with the judgment tier in a follow-up task, so the detector over-flags legitimate non-security uses by design until then)
**Why**: `math/rand` is deterministic and guessable; tokens, IDs, and nonces generated from it are predictable by an attacker. `crypto/rand` is the only source of security-relevant randomness.

#### Bad

```go
import "math/rand"

token := rand.Intn(1000000) // predictable — an attacker can guess the token
```

#### Good

```go
import "crypto/rand"

token := make([]byte, 32)
_, _ = rand.Read(token)
```

### RULE go-security/crypto-weak-algorithm (MUST)

**Owner**: go-security-specialist
**Applies when**: a `*.go` file outside `*_test.go`, `vendor/`, and `mocks/` calls `md5.Sum`, `sha1.Sum`, `md5.New`, `sha1.New`, `des.NewCipher`, or `des.NewTripleDESCipher`.
**Enforcement**: `rules/security/crypto-weak-algorithm.yml`
**Why**: MD5 and SHA-1 are collision-broken; DES uses a 56-bit key that is brute-forceable. Any use in a security context is a cryptographic failure. Use SHA-256+ or AES instead.

#### Bad

```go
sum := md5.Sum([]byte("password")) // collision-broken
h := sha1.New()                    // collision-broken
c, _ := des.NewCipher(key)         // 56-bit key, brute-forceable
```

#### Good

```go
sum := sha256.Sum256([]byte("password"))
c, _ := aes.NewCipher(key)
```

### RULE go-security/sql-string-interpolation (MUST)

**Owner**: go-security-specialist
**Applies when**: a `*.go` file outside `*_test.go`, `vendor/`, and `mocks/` calls `$DB.QueryContext`, `$DB.Query`, `$DB.ExecContext`, or `$DB.Exec` with a statement argument built by string concatenation.
**Enforcement**: `rules/security/sql-string-interpolation.yml`
**Why**: string-concatenated SQL lets untrusted input change the query's structure — the canonical SQL-injection path. Parameterized queries (`?` placeholders) or prepared statements keep data and code separate.

#### Bad

```go
rows, err := db.QueryContext(ctx, "SELECT * FROM users WHERE name = '" + name + "'")
```

#### Good

```go
rows, err := db.QueryContext(ctx, "SELECT * FROM users WHERE name = ?", name)
```

### RULE go-security/hardcoded-secret (MUST)

**Owner**: go-security-specialist
**Applies when**: a `*.go` file outside `*_test.go`, `vendor/`, and `mocks/` assigns a double-quoted string literal of at least 12 characters to a variable or constant whose name matches a secret identifier (token, secret, password, credential, apiKey, or underscored/hyphenated variants like api_key and auth-token), in short-declaration, assignment, `const`, or `var` form.
**Enforcement**: `rules/security/hardcoded-secret.yml`
**Why**: hardcoded credentials end up in source control, survive rotation, and leak through every artifact that ships the code. Read secrets from environment variables or a secrets manager at runtime.

#### Bad

```go
const apiKey = "sk-live-1234567890abcdef"
```

#### Good

```go
apiKey := os.Getenv("API_KEY")
```

## Anti-patterns to refuse

- **A mechanical rule without a rule-test** — every `rules/security/*.yml` must carry a `rule-tests/security/*-test.yml` (valid → 0, invalid → ≥1) and a snapshot; the `check-rule-tests` precommit gate fails otherwise.
- **Silent-zero detectors** — a detector that matches nothing is dead coverage; the acceptance bar is every Bad sample → ≥1 finding and every Good sample → 0.
- **Judgment/invariant-tier RULE blocks in this guide** — the judgment and invariant tiers ship in a follow-up task; until then only the 5 mechanical-tier rules live here.
- **A security finding without provenance** — findings must cite a `rule_id` that resolves in `rules/index.json`; invented security policy is rejected by `validate-citations.sh`.
- **`InsecureSkipVerify: true` "temporarily"** — there is no temporary; it is a permanent MITM acceptance.
- **Secrets in source** — hardcoded credentials, tokens, and keys are rejected by `hardcoded-secret`; read them from environment or a secrets manager.
- **Trading-specific examples** — this repo serves anyone learning Go; examples stay generic (User, Order, Product).
