Companion to [Rule Block Schema](rule-block-schema.md). The schema doc covers the `### RULE` block contract — WHAT to enforce. This guide covers the YAML side — HOW to enforce mechanically with ast-grep.

## File Location

```
rules/<lang>/<slug>.yml
```

- `<lang>` matches the rule ID's first segment (`go`, `python`, …)
- `<slug>` is the rule ID's last segment (e.g. `go-time/no-time-now-direct` → `rules/go/no-time-now-direct.yml`)
- One YAML per MUST mechanical rule. **No YAML** for judgment-tier rules — those carry `Enforcement: judgment` in the rule block instead.

## Required Frontmatter Shape

Every YAML uses six top-level keys. Canonical example (`rules/go/no-time-now-direct.yml`):

```yaml
id: go-time/no-time-now-direct
language: go
severity: error
message: |
  time.Now() must not be called directly in production code.
  Inject libtime.CurrentDateTimeGetter and call its Now() method instead.
  See docs/go-time-injection.md (RULE go-time/no-time-now-direct).
rule:
  pattern: time.Now()
ignores:
  - "main.go"
  - "**/main.go"
  - "**/*_test.go"
  - "vendor/**"
  - "**/vendor/**"
  - "**/mocks/**"
```

### Keys

| Key | Purpose |
|---|---|
| `id` | Must match the corresponding `### RULE <id>` exactly. The coverage lint (future Phase 8) fails on any mismatch. |
| `language` | `go`, `python`, etc. Determines the tree-sitter grammar. |
| `severity` | `error` / `warning` / `info`. **Decoupled from MUST/SHOULD level** — severity controls ast-grep tool exit codes; the rule-block level is the policy. Convention: MUST → `error`, SHOULD → `warning`, MAY → `info`. |
| `message` | Three-line block: short summary on line 1, blank line, then `See docs/<path>.md (RULE <id>).` on line 3. Keep the citation literal — the dispatcher uses it to surface the rule block to the reviewer. |
| `rule` | The ast-grep detector. See Pattern Strategies below. |
| `ignores` | Path patterns to exclude. Always include `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`. Other patterns per rule (e.g. `**/main.go` for production-only rules). |

## Pattern Strategies

### Simple presence

A literal call or expression. Use when the rule is "X must not appear in production code".

```yaml
rule:
  pattern: time.Now()
```

Canonical example: `rules/go/no-time-now-direct.yml`.

### Composition (`inside` / `has` / `not`)

For "X must contain Y" or "X must NOT contain Y" shapes. Combine selectors with traversal modifiers like `stopBy: end` (walks the whole subtree).

```yaml
rule:
  kind: for_statement
  not:
    has:
      stopBy: end
      pattern: <-ctx.Done()
```

This matches a `for` loop whose body, anywhere down the tree, does NOT contain `<-ctx.Done()`. Canonical example: `rules/go/cancel-check-in-loop.yml`.

### Kind matchers

When matching by AST node type rather than a literal pattern. Examples: `kind: for_statement`, `kind: field_declaration`, `kind: function_declaration`.

Combine with `any:` for alternation across multiple kinds or patterns:

```yaml
rule:
  any:
    - pattern: $NAME time.Time
    - pattern: $NAME time.Duration
```

Canonical example: `rules/go/no-time-time-in-fields.yml`.

Reference for available node kinds: <https://ast-grep.github.io/reference/yaml.html>. Per-language grammars: <https://ast-grep.github.io/reference/sgconfig.html>.

## Pitfalls Learned

- **Tree-sitter node-name guessing**. The pilot author tried `kind: communication_case` for Go `select` case clauses — that node name does not exist. Lesson: when uncertain, prefer a plain `pattern:` over a guessed `kind:` selector. Verify any `kind:` value against the ast-grep playground (<https://ast-grep.github.io/playground.html>) before committing.
- **Aliased imports defeat literal patterns**. `import t "time"; t.Now()` slips past `pattern: time.Now()`. Mechanical rules at the MUST level catch the 95% case. The dispatcher's judgment-tier review covers aliased imports.
- **`stopBy: end` walks the whole subtree** — expensive on large functions. Use targeted `inside` / `has` constraints when the search scope is known.
- **Generated code in `mocks/`**. Counterfeiter outputs to `mocks/` by convention across bborbe Go projects. Always include `**/mocks/**` in `ignores` — generated mock files create false positives (trivial copy loops, unconventional patterns).
- **`**/main.go` does NOT match the project's root `main.go`** in ast-grep's glob engine — `**/` requires at least one directory level, so `cmd/foo/main.go` matches but a repo-root `main.go` does not. Always include BOTH `main.go` (root) AND `**/main.go` (subdirs) in `ignores`. Verified on dark-factory: a single root-level `main.go` produced 11 false positives until the bare `main.go` pattern was added.
- **`pattern: $NAME time.Time` matches field declarations specifically**, not arbitrary `time.Time` usage. ast-grep's pattern-with-metavariable shape requires both a placeholder and the literal type — it does not match a bare `time.Time` mention.

## Smoke Testing

Before committing any new rule, smoke-test it against synthetic samples:

```bash
mkdir -p /tmp/astsample-<slug>

# Bad case: rule SHOULD fire
cat > /tmp/astsample-<slug>/bad.go <<'EOF'
package main
// minimal code that should match the rule
EOF

# Good case: rule must NOT fire
cat > /tmp/astsample-<slug>/good.go <<'EOF'
package main
// minimal code that satisfies the rule
EOF

# Test-file exclusion: rule must NOT fire (filtered by ignores)
cat > /tmp/astsample-<slug>/bad_test.go <<'EOF'
package main
// same bad pattern, but in a test file
EOF

ast-grep scan --rule rules/<lang>/<slug>.yml /tmp/astsample-<slug>/
```

Expected output: `bad.go` matched, `good.go` and `bad_test.go` not matched. Iterate the rule until smoke is clean **before** committing.

## When NOT to Write a YAML

Some rules cannot be expressed mechanically. The `### RULE` block carries `Enforcement: judgment` instead of a YAML path; the dispatcher's LLM call handles enforcement at review time, with rule-ID citation validation to prevent hallucination.

Common judgment-tier cases:

- **Factory-pattern violations** — requires whole-function context to distinguish a factory call site from a fixture or test setup.
- **SRP / architecture-level concerns** — cross-unit reasoning; no single AST shape matches.
- **"Useful error messages"** — semantic, not syntactic. The message content is the rule, not the syntax.
- **"Long-running enough to matter"** — heuristic. ast-grep flags every candidate; the judgment-tier LLM drops trivially-short loops.

If a rule is MUST-level but can't be mechanical, that is a smell. Either downgrade to SHOULD, or split into a mechanical sub-rule plus a judgment refinement.

## Relationship

- [Rule Block Schema](rule-block-schema.md) — the contract these YAMLs implement (companion)
- `scripts/build-index.py` — walker; reads each `Enforcement: rules/...yml` path and (in future Phase 8 coverage lint) verifies the file exists
- Canonical examples in this repo:
  - `rules/go/cancel-check-in-loop.yml` — `not.has` deep walk
  - `rules/go/no-time-now-direct.yml` — simple `pattern:` presence
  - `rules/go/no-time-time-in-fields.yml` — struct field detection via `any:` alternation
- ast-grep reference: <https://ast-grep.github.io/reference/yaml.html>
- ast-grep playground (verify node kinds before committing): <https://ast-grep.github.io/playground.html>
