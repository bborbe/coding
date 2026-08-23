---
status: completed
spec: [011-security-comprehensive-rules]
summary: Landed 7 judgment-tier go-security RULE blocks (5 MUST, 2 SHOULD) in docs/security/security-review-guide.md, reconciled all deferral prose about the judgment/invariant tiers, and regenerated rules/index.json from 171 to 178 entries (7 new judgment entries, owner go-security-specialist, trigger **/*.go); make precommit green with only the two intended files touched
execution_id: coding-security-comprehensive-rules-exec-047-judgment-tier-rules-and-reconcile
dark-factory-version: dev
created: "2026-08-23T20:30:00Z"
queued: "2026-08-23T20:53:15Z"
started: "2026-08-23T20:53:17Z"
completed: "2026-08-23T20:54:33Z"
branch: dark-factory/security-comprehensive-rules
---

# Judgment-tier rules + guide reconciliation

<summary>
- Append 7 judgment-tier RULE blocks to `docs/security/security-review-guide.md` — SSRF, XSS/untrusted-html, deserialization, open redirect, webhook verification (MUST); mass assignment, insecure defaults (SHOULD)
- Every block is owner `go-security-specialist`, ID in the two-component `go-security/<slug>` form, carries `**Trigger**: **/*.go`, `**Why**:`, and `#### Bad` / `#### Good` generic examples, and its `**Enforcement**:` cites no `rules/<lang>/<slug>.yml` path so it derives `enforcement_type: judgment`
- Reconcile the guide's deferral prose: the "judgment and invariant tiers ship in a follow-up task" sentence, the crypto-insecure-random parenthetical "until then", the anti-pattern bullet refusing judgment/invariant blocks here, and the "currently contains the 5 mechanical-tier rules below" sentence
- Regenerate `rules/index.json` from 171 to 178 entries via `make build-index`; all existing entries stay byte-identical
- No walker, schema, detector, CHANGELOG, or out-of-scope file changes — those land in prompts 2/3
- Working-tree changes are left for the daemon's `workflow: direct` post-prompt commit; no git is run inside the container
</summary>

<objective>
The guide's judgment tier ships: 7 schema-conformant `### RULE go-security/<slug>` blocks land in `docs/security/security-review-guide.md`, every deferral claim about the judgment/invariant tiers is reconciled to the shipped state, and `rules/index.json` is regenerated to 178 entries (all 7 new entries `enforcement_type: judgment`, `trigger: ["**/*.go"]`, owner `go-security-specialist`) with `make precommit` green and the tree clean except for this prompt's two touched files.
</objective>

<context>
Spec 011 (`specs/in-progress/011-security-comprehensive-rules.md`) ships the comprehensive security v1 rule base. This is prompt **1 of 3**. It lands the judgment-tier surface (7 rules) plus a prose reconciliation so the guide no longer claims the judgment/invariant tiers "ship in a follow-up task". No walker or schema changes — those land in prompt 2.

Read fully before writing:

- `/workspace/CLAUDE.md` — project conventions, generic content only (User/Order/Product/Customer — never trading-domain), Doc↔Agent alignment table.
- `/workspace/docs/rule-block-schema.md` — the `### RULE` block contract: heading `### RULE <id> (LEVEL)`, required fields `**Owner**:` / `**Applies when**:` / `**Enforcement**:` in that order, optional `**Trigger**:` immediately after `**Enforcement**:` (judgment-tier rules MUST carry it), recommended `**Why**:` after `**Trigger**:`, then `#### Bad` / `#### Good`. ID format `<lang>/<topic>[/<slug>]`, anchor = id verbatim, level tokens MUST/SHOULD/MAY.
- `/workspace/docs/security/security-review-guide.md` — the file to extend. Today it contains 5 mechanical RULE blocks (`tls-insecure-skip-verify`, `crypto-insecure-random`, `crypto-weak-algorithm`, `sql-string-interpolation`, `hardcoded-secret`). Three reconciliation points plus a fourth: (1) the Tiers-section sentence "The judgment and invariant tiers ship in a follow-up task." and its following sentence "This guide currently contains the 5 mechanical-tier rules below."; (2) the `crypto-insecure-random` Enforcement parenthetical noting judgment-tier adjudication ships "until then"; (3) the anti-pattern bullet "Judgment/invariant-tier RULE blocks in this guide".
- `/workspace/scripts/build-index.py` — the walker. Its field-parse tuple today is `("Owner", "Applies when", "Enforcement", "Trigger")`; adding a `Class` key here is prompt 2's job, not this prompt's.
- `/workspace/Makefile` — `make build-index` regenerates `rules/index.json`; `make precommit` runs check-links/check-json/check-index/check-coverage/check-acceptance/check-rule-tests/bench-test.
- `/workspace/rules/index.json` — currently 171 entries; this prompt must grow it to 178.

The 7 new IDs (two-component `go-security/<slug>` form per spike Finding 1):

1. `go-security/ssrf-user-controlled-url` (MUST)
2. `go-security/xss-untrusted-html` (MUST)
3. `go-security/deserialization-unsafe` (MUST)
4. `go-security/open-redirect` (MUST)
5. `go-security/webhook-verification` (MUST)
6. `go-security/mass-assignment` (SHOULD)
7. `go-security/insecure-defaults` (SHOULD)

Owner: `go-security-specialist` for every block. Every block carries `**Trigger**: **/*.go` (judgment-tier scoping). None of the 7 enforcement fields cites a `rules/<lang>/<slug>.yml` path or `scripts/rule-checks.sh` — so every entry derives `enforcement_type: judgment`.
</context>

<requirements>

### 1. Append 7 RULE blocks to `docs/security/security-review-guide.md`

Append (do NOT modify the existing 5 mechanical blocks) after the existing `## Anti-patterns to refuse` section. Add a `## Judgment-tier rules` heading immediately before the 7 new blocks so they are not visually under the anti-patterns section. Each block conforms to `docs/rule-block-schema.md` exactly.

**Field order is frozen** (schema § Optional Field: Trigger; spec 011 Constraint "Schema contract"): `**Owner**:` → `**Applies when**:` → `**Enforcement**:` → `**Trigger**:` → `**Why**:`. `**Trigger**:` sits immediately after `**Enforcement**:`. Do not reorder. After the field block come `#### Bad` and `#### Good` code blocks. Generic User/Order/Product/Customer examples throughout.

The template each block follows:

```
### RULE go-security/<slug> (LEVEL)

**Owner**: go-security-specialist
**Applies when**: <free-text>
**Enforcement**: <judgment text — must NOT cite rules/<lang>/<slug>.yml or scripts/rule-checks.sh>
**Trigger**: **/*.go
**Why**: <failure-mode paragraph>

#### Bad
<go code>

#### Good
<go code>
```

**Block 1 — `go-security/ssrf-user-controlled-url` (MUST)**
- Applies when: a Go file outside `*_test.go`, `vendor/`, `mocks/` issues an outbound HTTP request (`http.Get`, `http.NewRequest`, `http.Client.Do`) where the URL or host is derived from a request parameter, header, body field, or other user-controlled source without an allow-list / scheme-and-host validation step.
- Enforcement: judgment — LLM adjudicator checks the request URL's data flow back to a user-controlled source. No mechanical YAML.
- Why: SSRF turns the server into a proxy for the attacker's reach — internal services (cloud metadata `169.254.169.254`, localhost, RFC1918 ranges), partner APIs reachable from the VPC, and arbitrary outbound traffic become attacker-accessible. URL allow-listing plus scheme-and-host pinning is the standard mitigation.
- Bad:
  ```go
  func FetchUserAvatar(w http.ResponseWriter, r *http.Request) {
      avatarURL := r.URL.Query().Get("url")
      resp, err := http.Get(avatarURL)
      _ = resp
      _ = err
  }
  ```
- Good:
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

**Block 2 — `go-security/xss-untrusted-html` (MUST)**
- Applies when: a Go file outside `*_test.go`, `vendor/`, `mocks/` writes user-supplied data into an HTML response (template `html/template` is fine; `text/template`, `fmt.Fprintf(w, ...)`, raw concatenation into HTML is not) without HTML-escaping or a sanitizer.
- Enforcement: judgment — LLM adjudicator checks the response writer and the data-flow provenance of the interpolated value.
- Why: stored / reflected XSS lets an attacker run JavaScript in the victim's session, exfiltrating cookies, hijacking actions, or pivoting to admin-only routes. `html/template` is context-aware escaping; `text/template` and manual concatenation are not.
- Bad:
  ```go
  func RenderGreeting(w http.ResponseWriter, r *http.Request) {
      name := r.URL.Query().Get("name")
      fmt.Fprintf(w, "<h1>Hello, %s</h1>", name)
  }
  ```
- Good:
  ```go
  func RenderGreeting(w http.ResponseWriter, r *http.Request) {
      name := r.URL.Query().Get("name")
      if err := htmlTemplate.Execute(w, map[string]string{"Name": name}); err != nil {
          http.Error(w, "render failed", http.StatusInternalServerError)
          return
      }
  }
  ```

**Block 3 — `go-security/deserialization-unsafe` (MUST)**
- Applies when: a Go file outside `*_test.go`, `vendor/`, `mocks/` calls `json.Unmarshal` / `gob.NewDecoder` / `yaml.Unmarshal` / `xml.Unmarshal` on data received from an untrusted source (HTTP request body, message-bus payload, file uploaded by a user) into a struct without a schema gate — i.e. fields are bound directly without `json.Decoder.DisallowUnknownFields` or equivalent strict-mode flags.
- Enforcement: judgment — LLM adjudicator checks the source provenance of the bytes and the presence of a strict-mode decoder. No mechanical YAML.
- Why: lenient decoders accept extra fields the receiver never validated. Attacker-supplied fields (e.g. `IsAdmin: true`, role claims, internal flags) ride along into the parsed struct and downstream authorization decisions. Strict mode plus a typed DTO per request is the standard mitigation.
- Bad:
  ```go
  var u User
  if err := json.Unmarshal(reqBody, &u); err != nil {
      return err
  }
  if u.IsAdmin {
      // ...
  }
  ```
- Good:
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

**Block 4 — `go-security/open-redirect` (MUST)**
- Applies when: a Go HTTP handler outside `*_test.go`, `vendor/`, `mocks/` reads a `next` / `return_to` / `redirect` query parameter (or similar) and forwards the user to the parsed URL via `http.Redirect` / `http.RedirectHandler` / manual `Location:` header without an allow-list of permitted hosts / paths.
- Enforcement: judgment — LLM adjudicator checks the data flow from the request parameter to the redirect target. No mechanical YAML.
- Why: open redirects become phishing landing pages — the attacker crafts `https://your-app.com/login?next=https://evil.example.com/steal-cookie` and the victim's click traverses the trusted domain first. An allow-list of internal paths (or absolute-URL rejection) closes the path.
- Bad:
  ```go
  func LoginHandler(w http.ResponseWriter, r *http.Request) {
      next := r.URL.Query().Get("next")
      http.Redirect(w, r, next, http.StatusFound)
  }
  ```
- Good:
  ```go
  func LoginHandler(w http.ResponseWriter, r *http.Request) {
      next := r.URL.Query().Get("next")
      if !isInternalPath(next) {
          next = "/dashboard"
      }
      http.Redirect(w, r, next, http.StatusFound)
  }
  ```

**Block 5 — `go-security/webhook-verification` (MUST)**
- Applies when: a Go HTTP handler outside `*_test.go`, `vendor/`, `mocks/` exposes a webhook-receiving endpoint that processes the request body without verifying a provider signature (`X-Hub-Signature-256` / `Stripe-Signature` / equivalent HMAC header) before treating the payload as trusted.
- Enforcement: judgment — LLM adjudicator checks the signature-verification step preceding payload processing. No mechanical YAML.
- Why: unsigned webhook endpoints accept attacker-fabricated events — order confirmations, payment successes, account-status changes — that drive automated workflows. HMAC verification with a shared secret is the standard mitigation; constant-time comparison prevents timing oracles.
- Bad:
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
- Good:
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

**Block 6 — `go-security/mass-assignment` (SHOULD)**
- Applies when: a Go file outside `*_test.go`, `vendor/`, `mocks/` binds an HTTP request body or query directly into a domain struct that carries authorization-relevant fields (role flags, ownership pointers, billing status) without an explicit allow-list of bindable fields.
- Enforcement: judgment — LLM adjudicator checks the struct-to-DTO separation and the bind path. No mechanical YAML.
- Why: mass-assignment lets an attacker upgrade their own role, change ownership pointers, or flip internal state via fields the API surface never advertised. A typed input DTO that exposes only the user-settable fields is the standard mitigation.
- Bad:
  ```go
  func UpdateUser(w http.ResponseWriter, r *http.Request) {
      var u User
      if err := json.NewDecoder(r.Body).Decode(&u); err != nil {
          return
      }
      userRepo.Save(u) // u.Role, u.OwnerID, u.Balance all settable by the client
  }
  ```
- Good:
  ```go
  func UpdateUser(w http.ResponseWriter, r *http.Request) {
      var input UpdateUserInput
      if err := json.NewDecoder(r.Body).Decode(&input); err != nil {
          return
      }
      userRepo.UpdateName(r.Context(), input.ID, input.Name) // only Name is bindable
  }
  ```

**Block 7 — `go-security/insecure-defaults` (SHOULD)**
- Applies when: a Go file outside `*_test.go`, `vendor/`, `mocks/` ships a security-relevant default (TLS min version, cookie `Secure`/`HttpOnly`/`SameSite`, password hashing cost, session timeout, CORS wildcard, CSP `unsafe-inline`) at a value weaker than the secure baseline, instead of failing closed to the secure value.
- Enforcement: judgment — LLM adjudicator compares the shipped default against the secure baseline (e.g. `MinVersion: tls.VersionTLS12`, cookie `Secure`/`HttpOnly`/`SameSite` set, non-wildcard CORS, no `unsafe-inline` CSP) and flags any security-relevant default weaker than it. No mechanical YAML.
- Why: insecure defaults turn every deployment into a vulnerable one — operators who don't override the default get the weak value. Secure defaults plus an explicit override knob is the standard posture.
- Bad:
  ```go
  var cookieCfg = http.Cookie{
      Name:     "session",
      Secure:   false,
      HttpOnly: false,
      SameSite: http.SameSiteNoneMode,
  }
  ```
- Good:
  ```go
  var cookieCfg = http.Cookie{
      Name:     "session",
      Secure:   true,
      HttpOnly: true,
      SameSite: http.SameSiteStrictMode,
  }
  ```

### 2. Reconcile the guide's prose

Four edits to existing prose in `docs/security/security-review-guide.md`:

(a) **Tiers section (line 13 area):** replace the two sentences "The judgment and invariant tiers ship in a follow-up task." AND "This guide currently contains the 5 mechanical-tier rules below." with a single sentence stating the shipped state, e.g. "This guide is the source of truth for the mechanical and judgment tiers of the security rule base; the invariant-tier rules land with the walker `Class` support." Keep the three-tier framing intact.

(b) **`crypto-insecure-random` Enforcement parenthetical:** the parenthetical "(the judgment-tier adjudication of whether the usage is security-relevant ships with the judgment tier in a follow-up task, so the detector over-flags legitimate non-security uses by design until then)" — rewrite to drop the deferral: "(the detector over-flags legitimate non-security uses by design; the judgment-tier adjudication of whether a flagged usage is security-relevant lives with the judgment rules and applies at review time)". The YAML detection behavior is unchanged — the detector still fires on every `math/rand` import.

(c) **Anti-patterns section:** replace the bullet "Judgment/invariant-tier RULE blocks in this guide — the judgment and invariant tiers ship in a follow-up task; until then only the 5 mechanical-tier rules live here." with: "Judgment-tier RULE blocks are in scope for this guide — the judgment tier is live here alongside the mechanical tier, and the invariant-tier rules land with the walker `Class` support."

**Do NOT touch** any of the 5 mechanical RULE blocks' field text or code examples. **Do NOT touch** the other anti-pattern bullets. **Do NOT touch** the `## Tiers` section's first three paragraphs.

### 3. Regenerate `rules/index.json`

Run:

```bash
make build-index
```

Expected: `rules/index.json` grows from 171 to **178 entries** (171 existing + 7 new). All 7 new entries must:
- have `id` in the `go-security/<slug>` two-component form
- have `owner == "go-security-specialist"`
- have `doc_path == "docs/security/security-review-guide.md"`
- have `anchor == id`
- have `level in ("MUST","SHOULD","MAY")`
- have `enforcement_type == "judgment"` (no `rules/<lang>/<slug>.yml` path in the Enforcement field)
- have a non-empty `trigger: ["**/*.go"]` array
- non-empty `applies_when` and `enforcement`

All 171 existing entries stay byte-identical.

Then run `make precommit` — must exit 0.

### 4. Do NOT commit

Do NOT run `git` of any kind — the container's `.git` is masked (`hideGit: true`) and dark-factory's `workflow: direct` post-prompt commit stages and commits all dirty files on completion (repo convention: "Do NOT commit — dark-factory handles git"). Touched paths expected in the daemon's commit: `docs/security/security-review-guide.md`, `rules/index.json` only.

</requirements>

<constraints>
- **Rule identity:** all 7 new IDs use the two-component `go-security/<slug>` form (spike Finding 1) — never the three-component `security/<topic>/<slug>` form.
- **Owner:** `go-security-specialist` in every new block and index entry.
- **Schema contract (frozen):** field order `**Owner**:` → `**Applies when**:` → `**Enforcement**:` → `**Trigger**:` → `**Why**:`; `**Trigger**:` immediately after `**Enforcement**:`. Judgment-tier rules MUST carry a Trigger; mechanical rules omit it. The 7 new blocks carry `**Trigger**: **/*.go`.
- **Enforcement-type derivation:** none of the 7 enforcement fields cites `rules/<lang>/<slug>.yml` or `scripts/rule-checks.sh`, so every new entry derives `enforcement_type: judgment`; `check-coverage.sh` must not flag an orphan.
- **Extend, don't create:** all changes land in the existing `docs/security/security-review-guide.md`; no new guide, no README/llms.txt/code-review.md changes.
- **No changes to:** `scripts/build-index.py` (`Class` support is prompt 2's), `docs/rule-block-schema.md` (prompt 2's), `scripts/validate-citations.sh`, `commands/*.md`, `agents/*.md`, `.maintainer.yaml`, `scenarios/`, `rules/security/` (no detector added/removed, still 5 YAMLs), `CHANGELOG.md` (prompt 3's).
- **Index freshness:** this prompt edits RULE blocks, so it must run `make build-index` and leave `make check-index` green — `make precommit` exits 0.
- **Generic content only:** Bad/Good examples use User, Order, Product, Customer — never trading or project-specific domains. No real provider URLs (use `X-Signature` placeholder).
- **Git discipline:** no git inside the container (hideGit masks `.git`); the daemon owns the post-prompt commit.
- **Scope split:** the 2 invariant-linked blocks (`class: security-invariant`), the walker `Class` field, the schema doc, the cross-language layout prose, and the CHANGELOG entry belong to prompts 2/3 — do not ship them here.
</constraints>

<verification>
All commands are container-executable (repo root). No git — `.git` is masked.

```bash
# 1. Seven new judgment RULE blocks in the guide
grep -Ec '^### RULE go-security/(ssrf-user-controlled-url|xss-untrusted-html|deserialization-unsafe|open-redirect|webhook-verification|mass-assignment|insecure-defaults)' docs/security/security-review-guide.md
# expect: 7

# 2. Total RULE count = 12 (5 mechanical + 7 new judgment; the 2 invariant blocks land in prompt 2, reaching 14 at the final state)
grep -c '^### RULE ' docs/security/security-review-guide.md
# expect: 12

# 3. Each block carries a **Why**, Bad, Good
grep -c '\*\*Why\*\*' docs/security/security-review-guide.md   # expect: 12
grep -c '^#### Bad' docs/security/security-review-guide.md     # expect: 12
grep -c '^#### Good' docs/security/security-review-guide.md    # expect: 12

# 4. Reconcile — deferral prose gone (AC9 negatives)
grep -cE 'follow-up task|ships in a follow-up|ship.*follow-up' docs/security/security-review-guide.md   # expect: 0
grep -c 'Judgment/invariant-tier RULE blocks in this guide' docs/security/security-review-guide.md     # expect: 0
grep -c 'until then' docs/security/security-review-guide.md                                            # expect: 0

# 5. Regenerate index, expect 178 entries
make build-index
python3 scripts/build-index.py | jq 'length'   # expect: 178

# 6. Seven new entries in the index with the right shape
python3 scripts/build-index.py | jq '[.[] | select(.id | test("go-security/(ssrf-user-controlled-url|xss-untrusted-html|deserialization-unsafe|open-redirect|webhook-verification|mass-assignment|insecure-defaults)")) | {id, level, enforcement_type, owner, trigger}]'
# expect: exactly 7 entries, levels MUST x5 / SHOULD x2, enforcement_type judgment, owner go-security-specialist, trigger ["**/*.go"]

# 7. Negative: no three-component security/... IDs; go-security count = 16 (9 existing + 7 new)
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("security/"))] | length'   # expect: 0
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("go-security/"))] | length'  # expect: 16

# 8. Determinism — second build-index run produces byte-identical output
cp rules/index.json /tmp/index-run1.json
make build-index
diff /tmp/index-run1.json rules/index.json   # expect: no output (byte-identical)

# 9. Precommit green
make precommit   # expect: exit 0

# 10. Scope-lock negatives — no prompt-2/3 files touched
grep -c '"Class"' scripts/build-index.py                                  # expect: 0 (no walker Class support — prompt 2's)
grep -c '\*\*Class\*\*' docs/rule-block-schema.md                          # expect: 0 (no schema change — prompt 2's)
grep -Ec '^### RULE go-security/(resource-ownership|tenant-isolation)' docs/security/security-review-guide.md   # expect: 0 (no invariant blocks — prompt 2's)
ls rules/security/*.yml | wc -l                                            # expect: 5 (no detector added/removed)

# 11. CHANGELOG entry is NOT added in this prompt (prompt 3 owns that)
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c 'security'
# expect: 0

# 12. Final state — only the two intended files carry changes (do NOT commit)
grep -c 'security' docs/security/security-review-guide.md   # sanity: guide edited
jq 'length' rules/index.json                                 # sanity: index regenerated
```

</verification>

<notes>
- **Trigger field placement (frozen):** `**Trigger**:` sits immediately after `**Enforcement**:`, before `**Why**:` — per `docs/rule-block-schema.md` and spec 011's frozen schema contract. No re-read decision needed; do not reorder.
- **No YAML detectors ship here.** None of the 7 enforcement fields cites a YAML path. `check-coverage.sh` (called by `make precommit`) must not flag this as an orphan.
- **Generic examples only.** All Bad/Good snippets use User/Order/Product/Customer-shaped entities. No trading domain. No real provider URLs in the webhook example (use `X-Signature` placeholder header).
- **Field line parsing:** `scripts/build-index.py`'s `FIELD_RE` accepts both `**Key**: value` and `Key: value` forms — bold is the existing convention; match it.
- **Prompt ordering matters.** Prompt 2 adds the `Class` field to the walker and the 2 invariant blocks; prompt 3 records the layout decision and the CHANGELOG entry. This prompt's 7 blocks stay byte-stable when the walker learns `Class` afterward.
- **DoD CHANGELOG item is deferred to prompt 3.** The injected `docs/dod.md` requires a CHANGELOG `## Unreleased` entry; that item is intentionally satisfied by prompt 3, not here. Do not report it as an unmet blocker.
- **The `crypto-insecure-random` parenthetical rewrite** must not change the YAML detection behavior — the detector still fires on every `math/rand` import; only the prose describing how the judgment adjudicator consumes those flags changes.
</notes>
