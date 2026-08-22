---
status: approved
spec: [007-security-rule-base]
created: "2026-08-22T23:25:00Z"
queued: "2026-08-22T21:36:42Z"
branch: dark-factory/security-rule-base
---

<summary>
- Ships the 4 new mechanical security detectors under `rules/security/`: `crypto-insecure-random` (flags the `math/rand` import), `crypto-weak-algorithm` (flags `md5`/`sha1`/`des` `Sum`/`New`/`NewCipher`/`NewTripleDESCipher` calls), `sql-string-interpolation` (flags `$DB.QueryContext`/`$DB.Query`/`$DB.ExecContext`/`$DB.Exec` called with a string-concatenation statement argument), and `hardcoded-secret` (flags short-declaration / assignment / `const` / `var` forms where the variable name matches a secret identifier and the value is a double-quoted literal ≥12 characters)
- Adds the four matching `rule-tests/security/*-test.yml` fixtures (valid → 0 findings, invalid → ≥1 finding) and generates their snapshots via `ast-grep test -c sgconfig.yml -U`
- Grows `docs/security/security-review-guide.md` from 1 to exactly 5 `### RULE go-security/<slug>` blocks by appending the four new blocks under its `## Rules` section
- Regenerates `rules/index.json` (171 entries) so all 5 security rules are index-visible as `mechanical`, owner `go-security-specialist`
- `make precommit` exits 0 at the end — the new detector YAMLs and their index references land in the same prompt, so `check-coverage`'s orphan-YAML / missing-file checks both pass
- DEVIATION FROM SPEC (open question for the auditor): the spec's reference note 4 pins `pattern: $DB.Query($A + $B)` and `pattern: $DB.Exec($A + $B)` for sql-string-interpolation, but ast-grep 0.45.1 mis-parses both as `type_conversion_expression` (the exact silent-zero bug class documented in `rules/go/no-fmt-errorf.yml` and fixed by this very task) — verified 2026-08-22 that they match zero call sites. The requirement below pins a fully structural `kind: call_expression` rule (function = `selector_expression` on `QueryContext|Query|ExecContext|Exec`, arguments containing a `binary_expression` with a string-literal child) that provably fires on all four shapes and stays silent on parameterized queries. All four detector patterns were empirically verified on ast-grep 0.45.1 before being written here.
</summary>

<objective>
Ship the remaining four mechanical security detectors, their native rule-tests and snapshots, grow the security review guide to its full 5 RULE blocks, and regenerate the index — leaving `make precommit` green. This is prompt 2 of 4; it depends on prompt 1 (the `check-rule-tests` Makefile gate, `rule-tests/__snapshots__/go-security/`, `docs/security/security-review-guide.md`, and the `docs/security/*.md` walk extension all exist).
</objective>

<context>
Read `CLAUDE.md` (repo root) for project conventions.
Read `docs/rule-block-schema.md` (the `### RULE` block contract) and `docs/ast-grep-rule-writing-guide.md` (YAML detector conventions: six top-level keys, 3-line `message` with `See docs/...md (RULE <id>).` citation, `constraints` as a TOP-LEVEL sibling of `rule:` — NOT nested under `rule:` — and the pitfalls section, which documents why the `$DB.Query($A + $B)` form fails: a bare `Selector($Arg)` pattern parses as a Go type conversion, not a call expression).
Read `docs/security/security-review-guide.md` (the file from prompt 1) — you will append four blocks under its `## Rules` section. Keep its prose untouched.
Read `rules/security/tls-insecure-skip-verify.yml` and `rule-tests/security/tls-insecure-skip-verify-test.yml` (the prompt-1 exemplars) to mirror the frontmatter, `ignores`, and test-file shape.
Read `rules/go/no-fmt-errorf.yml` — its inline comment documents the same `type_conversion_expression` mis-parse that forced the sql-string-interpolation structural form below.
Read `scripts/check-coverage.sh` to confirm why each YAML must be index-referenced before `make precommit` passes (the four new YAMLs and their four index entries land together in this prompt).
Read `scripts/build-index.py` — the walk extension from prompt 1 is already in place; verify it is present (`grep -n 'security/\*\.md' scripts/build-index.py`) before relying on it.
Verify `ast-grep --version` reports 0.45.1.
</context>

<requirements>
1. Create the four detector YAMLs in `rules/security/` with EXACTLY the content below (each pattern was empirically verified on ast-grep 0.45.1 — do not re-derive, do not paraphrase; the only edits allowed are inside the `message:` text, which must keep the 3-line shape ending in `See docs/security/security-review-guide.md (RULE go-security/<slug>).`). All four use the standard `ignores` block:
   ```yaml
   ignores:
     - "**/*_test.go"
     - "vendor/**"
     - "**/vendor/**"
     - "**/mocks/**"
   ```

   a) `rules/security/crypto-insecure-random.yml`:
   ```yaml
   id: go-security/crypto-insecure-random
   language: go
   severity: error
   message: |
     math/rand must not be used for security-relevant randomness.
     Use crypto/rand for tokens, IDs, and nonces.
     See docs/security/security-review-guide.md (RULE go-security/crypto-insecure-random).
   rule:
     kind: import_spec
     has:
       field: path
       regex: '^"math/rand"$'
   ```
   (Append the standard `ignores` block.)

   b) `rules/security/crypto-weak-algorithm.yml`:
   ```yaml
   id: go-security/crypto-weak-algorithm
   language: go
   severity: error
   message: |
     MD5, SHA-1, and DES are cryptographically broken and must not be used.
     Use SHA-256+ or AES instead.
     See docs/security/security-review-guide.md (RULE go-security/crypto-weak-algorithm).
   rule:
     kind: call_expression
     has:
       kind: selector_expression
       all:
         - has:
             kind: identifier
             regex: '^(md5|sha1|des)$'
         - has:
             field: field
             kind: field_identifier
             regex: '^(Sum|New|NewCipher|NewTripleDESCipher)$'
   ```
   (Append the standard `ignores` block.)

   c) `rules/security/sql-string-interpolation.yml` — use the STRUCTURAL form (see summary for why the spec's pinned `any:` pattern silently matches zero):
   ```yaml
   id: go-security/sql-string-interpolation
   language: go
   severity: error
   message: |
     SQL statements must not be built by string concatenation.
     Use parameterized queries (?) or prepared statements.
     See docs/security/security-review-guide.md (RULE go-security/sql-string-interpolation).
   rule:
     # Structural form required: a bare pattern like `$DB.Query($A + $B)` parses
     # as a Go type_conversion_expression in ast-grep 0.45.1 (same silent-zero
     # bug class as rules/go/no-fmt-errorf.yml) and matches nothing. This rule
     # matches a call_expression whose function is a selector_expression on
     # QueryContext/Query/ExecContext/Exec (operand = any expression $DB) and
     # whose argument list contains a binary_expression with a string-literal
     # child (the interpolated SQL statement). Verified 2026-08-22: fires on all
     # four call shapes, silent on parameterized queries.
     kind: call_expression
     all:
       - has:
           field: function
           kind: selector_expression
           all:
             - has:
                 field: operand
                 pattern: $DB
             - has:
                 field: field
                 kind: field_identifier
                 regex: '^(QueryContext|Query|ExecContext|Exec)$'
       - has:
           field: arguments
           kind: argument_list
           has:
             kind: binary_expression
             has:
               kind: interpreted_string_literal
   ```
   (Append the standard `ignores` block.)

   d) `rules/security/hardcoded-secret.yml` — note `constraints:` is a TOP-LEVEL sibling of `rule:` (ast-grep rejects it nested):
   ```yaml
   id: go-security/hardcoded-secret
   language: go
   severity: error
   message: |
     Secrets must not be hardcoded as string literals.
     Use environment variables or a secrets manager.
     See docs/security/security-review-guide.md (RULE go-security/hardcoded-secret).
   rule:
     any:
       - pattern: $NAME := $VALUE
       - pattern: $NAME = $VALUE
       - pattern: const $NAME = $VALUE
       - pattern: var $NAME = $VALUE
   constraints:
     NAME:
       regex: '(?i)(token|secret|password|credential|apikey|api_key|api-key|auth_key|auth-token)'
     VALUE:
       regex: '^".{12,}"$'
   ```
   (Append the standard `ignores` block. Keep both regexes EXACTLY as written — they are anchored/bounded by design: NAME is a substring match on the identifier, VALUE requires a double-quoted literal of at least 12 characters. Do not widen either.)

2. Create the four test files in `rule-tests/security/` with EXACTLY the content below (each `id:` MUST match its rule; snippets are repo-controlled Go — ast-grep parses them, they do not need to compile):

   a) `rule-tests/security/crypto-insecure-random-test.yml`:
   ```yaml
   id: go-security/crypto-insecure-random
   valid:
     - |
       package main

       import "crypto/rand"

       func main() {
           b := make([]byte, 16)
           _, _ = rand.Read(b)
       }
   invalid:
     - |
       package main

       import "math/rand"

       func main() {
           _ = rand.Intn(100)
       }
   ```

   b) `rule-tests/security/crypto-weak-algorithm-test.yml`:
   ```yaml
   id: go-security/crypto-weak-algorithm
   valid:
     - |
       package main

       import "crypto/sha256"

       func main() {
           _ = sha256.Sum256([]byte("data"))
       }
   invalid:
     - |
       package main

       import "crypto/md5"

       func main() {
           _ = md5.Sum([]byte("data"))
       }
   ```

   c) `rule-tests/security/sql-string-interpolation-test.yml`:
   ```yaml
   id: go-security/sql-string-interpolation
   valid:
     - |
       package main

       import "database/sql"

       func main() {
           db := &sql.DB{}
           ctx := context.Background()
           _ = db.QueryContext(ctx, "SELECT * FROM users WHERE name = ?", "alice")
           _ = db.Query("SELECT * FROM users WHERE id = ?", 1)
       }
   invalid:
     - |
       package main

       import "database/sql"

       func main() {
           db := &sql.DB{}
           ctx := context.Background()
           name := "alice"
           id := "1"
           _ = db.QueryContext(ctx, "SELECT * FROM users WHERE name = '" + name + "'")
           _ = db.Query("SELECT * FROM users WHERE id = " + id)
           _ = db.ExecContext(ctx, "UPDATE users SET name = '" + name + "'")
           _ = db.Exec("DELETE FROM users WHERE id = " + id)
       }
   ```

   d) `rule-tests/security/hardcoded-secret-test.yml`:
   ```yaml
   id: go-security/hardcoded-secret
   valid:
     - |
       package main

       import "os"

       func main() {
           apiKey := os.Getenv("API_KEY")
           _ = apiKey
           name := "Alice"
           _ = name
       }
   invalid:
     - |
       package main

       func main() {
           token := "sk-live-1234567890"
           _ = token
       }
   ```

3. Generate snapshots and prove each detector fires/turns off (the rule-test gate prompt 1 installed):
   - For each of the four detectors run `ast-grep test -c sgconfig.yml -U -f <detector>` — must exit 0. (`-f` takes the rule id or a substring regex; it limits the snapshot update to that rule.) Confirm `rule-tests/__snapshots__/go-security/<slug>-snapshot.yml` was created for each (do NOT hand-write them).
   - Then run the full `ast-grep test -c sgconfig.yml` — must exit 0 with 51 passed (46 baseline + tls + 4 new) and 0 failed.
   - If any detector FAILS on its invalid snippet (0 findings) or its valid snippet (≥1 finding), fix the YAML pattern in requirement 1 — the pinned forms are verified, so first re-check the file bytes — and re-run until green. Do not proceed past a failing detector: a detector whose fixture contract is not met is the exact "silent zero" regression this task exists to prevent.

4. Append exactly four `### RULE go-security/<slug> (MUST)` blocks to `docs/security/security-review-guide.md`, immediately after the existing tls block, still under the `## Rules` section (insert before the end of file). Do NOT modify the tls block or any prose above it. Use EXACTLY these blocks (schema-compliant: Owner → Applies when → Enforcement order, `**Why**:`, `#### Bad`/`#### Good`, no `**Trigger**:`):

   a) crypto-insecure-random:
   ```markdown
   ### RULE go-security/crypto-insecure-random (MUST)

   **Owner**: go-security-specialist
   **Applies when**: a `*.go` file outside `*_test.go` and `vendor/` imports `math/rand` (the Go standard library's predictable PRNG).
   **Enforcement**: `rules/security/crypto-insecure-random.yml` (mechanical flag; judgment-tier LLM adjudication decides whether the usage is security-relevant)
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
   ```

   b) crypto-weak-algorithm:
   ```markdown
   ### RULE go-security/crypto-weak-algorithm (MUST)

   **Owner**: go-security-specialist
   **Applies when**: a `*.go` file outside `*_test.go` and `vendor/` calls `md5`/`sha1`/`des` `Sum`/`New`/`NewCipher`/`NewTripleDESCipher`.
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
   ```

   c) sql-string-interpolation:
   ```markdown
   ### RULE go-security/sql-string-interpolation (MUST)

   **Owner**: go-security-specialist
   **Applies when**: a `*.go` file outside `*_test.go` and `vendor/` calls `$DB.QueryContext`, `$DB.Query`, `$DB.ExecContext`, or `$DB.Exec` with a statement argument built by string concatenation.
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
   ```

   d) hardcoded-secret:
   ```markdown
   ### RULE go-security/hardcoded-secret (MUST)

   **Owner**: go-security-specialist
   **Applies when**: a `*.go` file outside `*_test.go` and `vendor/` assigns a double-quoted string literal of at least 12 characters to a variable or constant whose name matches a secret identifier (token, secret, password, credential, apiKey, or underscored/hyphenated variants like api_key and auth-token), in short-declaration, assignment, `const`, or `var` form.
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
   ```

5. Regenerate the index:
   - Run `make build-index` (exits 0).
   - `rules/index.json` must now have 171 entries (167 from prompt 1 + 4 new), each new entry with `level: "MUST"`, `doc_path: "docs/security/security-review-guide.md"`, `anchor == id`, `owner: "go-security-specialist"`, `enforcement_type: "mechanical"`.

6. Run `make precommit` — must exit 0. If `check-coverage` reports an orphan YAML or a missing file, the four YAMLs and their four index entries are out of sync — all five `rules/security/*.yml` files must be referenced by the regenerated index. If `check-rule-tests` fails, a fixture contract is unmet — fix per requirement 3.

7. Do NOT touch: `README.md`, `llms.txt`, `agents/go-security-specialist.md` (prompt 3), `commands/*.md`, `scripts/validate-citations.sh`, `CHANGELOG.md`. Do NOT create any rule beyond the five (tls + these four). Do NOT add judgment/invariant-tier RULE blocks (ssrf / authz / invariant) — they are explicitly out of scope.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. `.git` is a worktree pointer file, unusable inside the container; do NOT run `git` commands.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt.
- Rule identity: two-component `go-security/<slug>` ids, owner `go-security-specialist` in every block and every index entry.
- No new agent file, no command change: do not create `agents/security-verifier.md`, do not modify `commands/code-review.md` or any `commands/*.md`.
- `scripts/build-index.py` stays Python stdlib only. Do NOT modify it in this prompt (the walk extension shipped in prompt 1).
- Rule-test discipline: snapshots are generated via `ast-grep test -c sgconfig.yml -U` (never hand-written); the plain `ast-grep test -c sgconfig.yml` must pass in CI.
- Snippet contract: every `valid:` snippet yields 0 findings against its own rule; every `invalid:` snippet yields ≥1. Valid snippets avoid their own rule's trigger shapes (rand valid snippet imports `crypto/rand`, not `math/rand`; secrets valid snippet reads via `os.Getenv`, not a literal). Snippets are repo-controlled Go files, never generated at runtime.
- Do NOT ship judgment-tier or invariant-tier RULE blocks (SSRF, authz/IDOR, invariant-preservation) — a later task.
- Do NOT split detectors per language (`rules/security/{go,python,node}/`) — v1 ships flat under `rules/security/`.
- No config knobs, opt-out flags, or tunable thresholds on the detectors or the harness.
- Keep both hardcoded-secret regexes exactly as specified — anchored/bounded by design; no ReDoS surface, no threshold widening.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — `.git` is masked).
```bash
# --- Requirement 1: exactly 5 detector YAMLs in rules/security ---
ls rules/security/*.yml | wc -l    # must return 5
for f in crypto-insecure-random crypto-weak-algorithm sql-string-interpolation hardcoded-secret; do
  head -1 "rules/security/$f.yml" | grep -q "^id: go-security/$f" && echo "$f yaml id: ok"
done

# --- Requirements 2-3: 5 test files + 5 snapshots; full harness passes ---
ls rule-tests/security/*-test.yml | wc -l    # must return 5
ls rule-tests/__snapshots__/go-security/*-snapshot.yml | wc -l    # must return 5
ast-grep test -c sgconfig.yml 2>&1 | tail -1    # must show 51 passed; 0 failed
# per-detector PASS evidence (each must print a PASS line):
for f in crypto-insecure-random crypto-weak-algorithm sql-string-interpolation hardcoded-secret; do
  ast-grep test -c sgconfig.yml -f "$f" 2>&1 | grep -q "PASS go-security/$f" && echo "$f test PASS: ok"
done

# --- Requirement 4: guide has exactly 5 blocks; no forbidden content ---
grep -c '^### RULE go-security/' docs/security/security-review-guide.md   # must return 5
grep -cE 'RULE go-security/(ssrf|authz|invariant)' docs/security/security-review-guide.md   # must return 0
grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md   # must return 0 lines

# --- Requirement 5: index has 171 entries, 5 go-security/security-review-guide entries, all mechanical ---
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 171, f"expected 171 entries, got {len(d)}'
new = [x for x in d if x['doc_path'] == 'docs/security/security-review-guide.md']
assert len(new) == 5, f'expected 5 security-review-guide entries, got {len(new)}'
ids = {'go-security/tls-insecure-skip-verify','go-security/crypto-insecure-random','go-security/crypto-weak-algorithm','go-security/sql-string-interpolation','go-security/hardcoded-secret'}
assert {x['id'] for x in new} == ids, {x['id'] for x in new}
for x in new:
    assert x['level'] == 'MUST', x
    assert x['anchor'] == x['id'], x
    assert x['owner'] == 'go-security-specialist', x
    assert x['enforcement_type'] == 'mechanical', x
print('5 security index entries: ok')
"

# --- Requirement 6: full precommit green ---
make precommit   # must exit 0
```
</verification>
