# Security Review Guide

Companion to [go-security-linting.md](go-security-linting.md) (the gosec workflow), [teamvault-conventions.md](teamvault-conventions.md) (secret handling), and [rule-block-schema.md](../rule-block-schema.md) (the `### RULE` block contract). This guide is the source of truth for the mechanical security rule base that Security Review Mode enforces: every rule maps to a detector in `rules/security/*.yml` and an entry in `rules/index.json` owned by `go-security-specialist`.

## Tiers

Security Review Mode organizes rules into three tiers:

- **Mechanical tier** — MUST-level rules enforced by ast-grep detectors (`rules/security/*.yml`). A detector either fires or it does not; enforcement is the YAML path.
- **Judgment tier** — MUST-level rules that require LLM adjudication at review time (SSRF, authorization/IDOR, invariant-preservation concerns).
- **Invariant tier** — rules that require whole-repo reasoning rather than a single AST shape.

This guide is the source of truth for the mechanical and judgment tiers of the security rule base; the invariant-tier rules land with the walker `Class` support.

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
**Enforcement**: `rules/security/crypto-insecure-random.yml` (mechanical flag — fires on every import of `math/rand`/`math/rand/v2`; the detector over-flags legitimate non-security uses by design; the judgment-tier adjudication of whether a flagged usage is security-relevant lives with the judgment rules and applies at review time)
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
- **Judgment-tier RULE blocks are in scope for this guide** — the judgment tier is live here alongside the mechanical tier, and the invariant-tier rules land with the walker `Class` support.
- **A security finding without provenance** — findings must cite a `rule_id` that resolves in `rules/index.json`; invented security policy is rejected by `validate-citations.sh`.
- **`InsecureSkipVerify: true` "temporarily"** — there is no temporary; it is a permanent MITM acceptance.
- **Secrets in source** — hardcoded credentials, tokens, and keys are rejected by `hardcoded-secret`; read them from environment or a secrets manager.
- **Trading-specific examples** — this repo serves anyone learning Go; examples stay generic (User, Order, Product).

## Judgment-tier rules

### RULE go-security/ssrf-user-controlled-url (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go file outside `*_test.go`, `vendor/`, `mocks/` issues an outbound HTTP request (`http.Get`, `http.NewRequest`, `http.Client.Do`) where the URL or host is derived from a request parameter, header, body field, or other user-controlled source without an allow-list / scheme-and-host validation step.
**Enforcement**: judgment — LLM adjudicator checks the request URL's data flow back to a user-controlled source. No mechanical YAML.
**Trigger**: **/*.go
**Why**: SSRF turns the server into a proxy for the attacker's reach — internal services (cloud metadata `169.254.169.254`, localhost, RFC1918 ranges), partner APIs reachable from the VPC, and arbitrary outbound traffic become attacker-accessible. URL allow-listing plus scheme-and-host pinning is the standard mitigation.

#### Bad

```go
func FetchUserAvatar(w http.ResponseWriter, r *http.Request) {
    avatarURL := r.URL.Query().Get("url")
    resp, err := http.Get(avatarURL)
    _ = resp
    _ = err
}
```

#### Good

```go
var allowedHosts = map[string]struct{}{"cdn.example.com": {}}

func FetchUserAvatar(ctx context.Context, w http.ResponseWriter, r *http.Request) {
    avatarURL, err := url.Parse(r.URL.Query().Get("url"))
    if err != nil {
        http.Error(w, "invalid url", http.StatusBadRequest)
        return
    }
    if avatarURL.Scheme != "https" {
        http.Error(w, "https required", http.StatusBadRequest)
        return
    }
    if _, ok := allowedHosts[avatarURL.Hostname()]; !ok {
        http.Error(w, "host not allowed", http.StatusBadRequest)
        return
    }
    resp, err := http.Get(avatarURL.String())
    _ = resp
    _ = err
}
```

### RULE go-security/xss-untrusted-html (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go file outside `*_test.go`, `vendor/`, `mocks/` writes user-supplied data into an HTML response (template `html/template` is fine; `text/template`, `fmt.Fprintf(w, ...)`, raw concatenation into HTML is not) without HTML-escaping or a sanitizer.
**Enforcement**: judgment — LLM adjudicator checks the response writer and the data-flow provenance of the interpolated value.
**Trigger**: **/*.go
**Why**: stored / reflected XSS lets an attacker run JavaScript in the victim's session, exfiltrating cookies, hijacking actions, or pivoting to admin-only routes. `html/template` is context-aware escaping; `text/template` and manual concatenation are not.

#### Bad

```go
func RenderGreeting(w http.ResponseWriter, r *http.Request) {
    name := r.URL.Query().Get("name")
    fmt.Fprintf(w, "<h1>Hello, %s</h1>", name)
}
```

#### Good

```go
func RenderGreeting(w http.ResponseWriter, r *http.Request) {
    name := r.URL.Query().Get("name")
    if err := htmlTemplate.Execute(w, map[string]string{"Name": name}); err != nil {
        http.Error(w, "render failed", http.StatusInternalServerError)
        return
    }
}
```

### RULE go-security/deserialization-unsafe (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go file outside `*_test.go`, `vendor/`, `mocks/` calls `json.Unmarshal` / `gob.NewDecoder` / `yaml.Unmarshal` / `xml.Unmarshal` on data received from an untrusted source (HTTP request body, message-bus payload, file uploaded by a user) into a struct without a schema gate — i.e. fields are bound directly without `json.Decoder.DisallowUnknownFields` or equivalent strict-mode flags.
**Enforcement**: judgment — LLM adjudicator checks the source provenance of the bytes and the presence of a strict-mode decoder. No mechanical YAML.
**Trigger**: **/*.go
**Why**: lenient decoders accept extra fields the receiver never validated. Attacker-supplied fields (e.g. `IsAdmin: true`, role claims, internal flags) ride along into the parsed struct and downstream authorization decisions. Strict mode plus a typed DTO per request is the standard mitigation.

#### Bad

```go
var u User
if err := json.Unmarshal(reqBody, &u); err != nil {
    return err
}
if u.IsAdmin {
    // ...
}
```

#### Good

```go
dec := json.NewDecoder(req.Body)
dec.DisallowUnknownFields()
var u User
if err := dec.Decode(&u); err != nil {
    return err
}
if u.IsAdmin {
    // ...
}
```

### RULE go-security/open-redirect (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go HTTP handler outside `*_test.go`, `vendor/`, `mocks/` reads a `next` / `return_to` / `redirect` query parameter (or similar) and forwards the user to the parsed URL via `http.Redirect` / `http.RedirectHandler` / manual `Location:` header without an allow-list of permitted hosts / paths.
**Enforcement**: judgment — LLM adjudicator checks the data flow from the request parameter to the redirect target. No mechanical YAML.
**Trigger**: **/*.go
**Why**: open redirects become phishing landing pages — the attacker crafts `https://your-app.com/login?next=https://evil.example.com/steal-cookie` and the victim's click traverses the trusted domain first. An allow-list of internal paths (or absolute-URL rejection) closes the path.

#### Bad

```go
func LoginHandler(w http.ResponseWriter, r *http.Request) {
    next := r.URL.Query().Get("next")
    http.Redirect(w, r, next, http.StatusFound)
}
```

#### Good

```go
func LoginHandler(w http.ResponseWriter, r *http.Request) {
    next := r.URL.Query().Get("next")
    if !isInternalPath(next) {
        next = "/dashboard"
    }
    http.Redirect(w, r, next, http.StatusFound)
}
```

### RULE go-security/webhook-verification (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go HTTP handler outside `*_test.go`, `vendor/`, `mocks/` exposes a webhook-receiving endpoint that processes the request body without verifying a provider signature (`X-Hub-Signature-256` / `Stripe-Signature` / equivalent HMAC header) before treating the payload as trusted.
**Enforcement**: judgment — LLM adjudicator checks the signature-verification step preceding payload processing. No mechanical YAML.
**Trigger**: **/*.go
**Why**: unsigned webhook endpoints accept attacker-fabricated events — order confirmations, payment successes, account-status changes — that drive automated workflows. HMAC verification with a shared secret is the standard mitigation; constant-time comparison prevents timing oracles.

#### Bad

```go
func WebhookHandler(w http.ResponseWriter, r *http.Request) {
    var order Order
    if err := json.NewDecoder(r.Body).Decode(&order); err != nil {
        http.Error(w, "bad payload", http.StatusBadRequest)
        return
    }
    orderService.MarkPaid(order)
}
```

#### Good

```go
func WebhookHandler(w http.ResponseWriter, r *http.Request) {
    sig := r.Header.Get("X-Signature")
    body, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "bad body", http.StatusBadRequest)
        return
    }
    if !verifyHMAC(body, []byte(sig), []byte(secret)) {
        http.Error(w, "invalid signature", http.StatusUnauthorized)
        return
    }
    var order Order
    if err := json.Unmarshal(body, &order); err != nil {
        http.Error(w, "bad payload", http.StatusBadRequest)
        return
    }
    orderService.MarkPaid(order)
}
```

### RULE go-security/mass-assignment (SHOULD)

**Owner**: go-security-specialist
**Applies when**: a Go file outside `*_test.go`, `vendor/`, `mocks/` binds an HTTP request body or query directly into a domain struct that carries authorization-relevant fields (role flags, ownership pointers, billing status) without an explicit allow-list of bindable fields.
**Enforcement**: judgment — LLM adjudicator checks the struct-to-DTO separation and the bind path. No mechanical YAML.
**Trigger**: **/*.go
**Why**: mass-assignment lets an attacker upgrade their own role, change ownership pointers, or flip internal state via fields the API surface never advertised. A typed input DTO that exposes only the user-settable fields is the standard mitigation.

#### Bad

```go
func UpdateUser(w http.ResponseWriter, r *http.Request) {
    var u User
    if err := json.NewDecoder(r.Body).Decode(&u); err != nil {
        return
    }
    userRepo.Save(u) // u.Role, u.OwnerID, u.Balance all settable by the client
}
```

#### Good

```go
func UpdateUser(w http.ResponseWriter, r *http.Request) {
    var input UpdateUserInput
    if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
        return
    }
    userRepo.UpdateName(r.Context(), input.ID, input.Name) // only Name is bindable
}
```

### RULE go-security/insecure-defaults (SHOULD)

**Owner**: go-security-specialist
**Applies when**: a Go file outside `*_test.go`, `vendor/`, `mocks/` ships a security-relevant default (TLS min version, cookie `Secure`/`HttpOnly`/`SameSite`, password hashing cost, session timeout, CORS wildcard, CSP `unsafe-inline`) at a value weaker than the secure baseline, instead of failing closed to the secure value.
**Enforcement**: judgment — LLM adjudicator compares the shipped default against the secure baseline (e.g. `MinVersion: tls.VersionTLS12`, cookie `Secure`/`HttpOnly`/`SameSite` set, non-wildcard CORS, no `unsafe-inline` CSP) and flags any security-relevant default weaker than it. No mechanical YAML.
**Trigger**: **/*.go
**Why**: insecure defaults turn every deployment into a vulnerable one — operators who don't override the default get the weak value. Secure defaults plus an explicit override knob is the standard posture.

#### Bad

```go
var cookieCfg = http.Cookie{
    Name:     "session",
    Secure:   false,
    HttpOnly: false,
    SameSite: http.SameSiteNoneMode,
}
```

#### Good

```go
var cookieCfg = http.Cookie{
    Name:     "session",
    Secure:   true,
    HttpOnly: true,
    SameSite: http.SameSiteStrictMode,
}
```

## Invariant-tier rules

### RULE go-security/resource-ownership (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go handler / service method outside `*_test.go`, `vendor/`, `mocks/` reads, mutates, or deletes a resource (DB row, file, third-party-API object) addressed by a path parameter, query parameter, body field, or header value, without first verifying that the authenticated user owns the resource. "Owns" is defined per resource by the `authorization_functions` field in the derived session security model (see `docs/security/security-review-pipeline.md`).
**Enforcement**: judgment — LLM adjudicator resolves the resource's `authorization_functions` from the derived session security model per `docs/security/security-review-pipeline.md`, fires when the diff accesses a resource by identifier without the owning authorization function enforced, and emits findings as `kind=invariant` with `invariant_id` resolving in the session model.
**Trigger**: @commits
**Class**: security-invariant
**Why**: resource-ownership gaps are the canonical IDOR / BOLA class — the attacker authenticates as a legitimate user and accesses another user's data via a guessed or harvested identifier. Generic linters cannot detect these: the missing check is the absence of an authorization call, not the presence of a forbidden call. Whole-repo reasoning against the derived model is the only enforcement path.

#### Bad

```go
func GetOrder(w http.ResponseWriter, r *http.Request) {
    orderID := chi.URLParam(r, "orderID")
    order, err := orderRepo.Find(r.Context(), orderID)
    if err != nil {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    json.NewEncoder(w).Encode(order)
}
```

#### Good

```go
func GetOrder(w http.ResponseWriter, r *http.Request) {
    user := userFromCtx(r.Context())
    orderID := chi.URLParam(r, "orderID")
    order, err := orderRepo.FindOwnedBy(r.Context(), orderID, user.ID)
    if err != nil {
        http.Error(w, "not found", http.StatusNotFound)
        return
    }
    json.NewEncoder(w).Encode(order)
}
```

### RULE go-security/tenant-isolation (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go handler / service method outside `*_test.go`, `vendor/`, `mocks/` issues a query, mutation, or third-party call scoped by an account / tenant / org identifier without first verifying the authenticated user belongs to that tenant. "Belongs" is defined per tenant resource by the `authorization_functions` field in the derived session security model (see `docs/security/security-review-pipeline.md`).
**Enforcement**: judgment — LLM adjudicator resolves the tenant resource's `authorization_functions` from the derived session security model per `docs/security/security-review-pipeline.md`, fires when the diff scopes the call by tenant without the owning authorization function enforced, and emits findings as `kind=invariant` with `invariant_id` resolving in the session model.
**Trigger**: @commits
**Class**: security-invariant
**Why**: tenant isolation gaps let an authenticated user in tenant A read or mutate tenant B's data via a guessed tenant identifier — cross-tenant data leakage at scale. The authorization check is a missing-call absence, not a forbidden-call presence; whole-repo reasoning against the derived model is required.

#### Bad

```go
func ListInvoices(w http.ResponseWriter, r *http.Request) {
    tenantID := r.URL.Query().Get("tenant_id")
    invoices, err := invoiceRepo.List(r.Context(), tenantID)
    if err != nil {
        http.Error(w, "list failed", http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(invoices)
}
```

#### Good

```go
func ListInvoices(w http.ResponseWriter, r *http.Request) {
    user := userFromCtx(r.Context())
    invoices, err := invoiceRepo.ListForTenant(r.Context(), user.TenantID)
    if err != nil {
        http.Error(w, "list failed", http.StatusInternalServerError)
        return
    }
    json.NewEncoder(w).Encode(invoices)
}
```
