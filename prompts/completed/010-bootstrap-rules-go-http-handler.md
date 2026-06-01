---
status: completed
summary: 'Appended 4 ### RULE blocks to docs/go-http-handler-refactoring-guide.md, created 2 ast-grep YAMLs (handler-no-inline-error-handler.yml, handler-no-inline-background-handler.yml), grew rules/index.json from 17 to 21 entries, updated CHANGELOG.md'
container: coding-bootstrap-go-http-handler-exec-010-bootstrap-rules-go-http-handler
dark-factory-version: v0.173.0
created: "2026-06-01T22:32:38Z"
queued: "2026-06-01T22:46:42Z"
started: "2026-06-01T22:46:49Z"
completed: "2026-06-01T22:48:25Z"
---

<summary>
- Fifth bootstrap prompt — migrates `docs/go-http-handler-refactoring-guide.md` from prose-only to rule-blocks-inline (Model A)
- Appends 4 `### RULE` blocks (2 MUST mechanical + 2 MUST judgment) corresponding to the doc's `### Problems with Inline Handlers in main.go` + `## Naming Conventions` sections
- Adds 2 `rules/go/*.yml` ast-grep YAMLs for the mechanical rules; the 2 judgment rules carry `Enforcement: judgment`
- Runs `make build-index` so `rules/index.json` grows from 17 entries to 21
- Mirrors the proven 4-prior-PR bootstrap template (go-time, go-errors, go-security, go-factory all merged)
- Path-filter pivot: prior rules ignored `main.go` (entry point exemption). THIS rule INVERTS — `main.go` is exactly where inline handlers are illegitimate; the legitimate location is `pkg/handler/**`. So this prompt's mechanical rules ignore `pkg/handler/**` instead of `main.go`.
- ast-grep 0.43.0 lesson learned (PR #4): rule-level `regex` matches whole-node text, not a specific field. Use `has: { field: name, regex: ... }` shape. Patterns also work for call expressions with anonymous-func arguments.
</summary>

<objective>
Following the schema in `docs/rule-block-schema.md` and the ast-grep conventions in `docs/ast-grep-rule-writing-guide.md`, extract four rules from `docs/go-http-handler-refactoring-guide.md` as inline `### RULE` blocks, write ast-grep YAML detectors for the two mechanical rules, and refresh `rules/index.json` via the walker.
</objective>

<context>
Read `CLAUDE.md` for project conventions, including the doc-agent alignment table (`go-http-handler-refactoring-guide.md` → `go-http-handler-assistant`).
Read `docs/rule-block-schema.md` for the rule-block contract.
Read `docs/ast-grep-rule-writing-guide.md` — especially the ast-grep 0.43.0 pitfalls section.
Read `docs/go-http-handler-refactoring-guide.md` — the doc to migrate. Section "Problems with Inline Handlers in main.go" (~line 11) and "Naming Conventions" (~line 228) list the rules; the Before/After Example (~line 95) provides concrete Bad/Good code.
Read `docs/go-context-cancellation-in-loops.md` lines 160-192 — canonical pilot `### RULE` block formatting.
Read three canonical small ast-grep YAMLs: `rules/go/no-fmt-errorf.yml`, `rules/go/no-time-now-direct.yml`, `rules/go/factory-no-error-return.yml` (the most recent example, which uses the `kind + all + has + field` pattern).
Read `scripts/build-index.py` and run `python3 scripts/build-index.py` once to see the current `rules/index.json` shape (17 entries) before changes.
</context>

<requirements>
1. Append four `### RULE` blocks at the END of `docs/go-http-handler-refactoring-guide.md` (after the existing `## Reference Examples` section). Do NOT modify any prose above. The four blocks, in order:

**Rule 1 — MUST mechanical**
- Heading: `### RULE go-http-handler/no-inline-error-handler (MUST)`
- Owner: `go-http-handler-assistant`
- Applies when: `libhttp.WithErrorFunc(func ...)` is called with an inline anonymous function as its argument in a `*.go` file OUTSIDE `**/pkg/handler/**`, `*_test.go`, and `vendor/`. The legitimate place for inline error handler closures is inside `pkg/handler/New*Handler` factory functions; anywhere else (typically `main.go`) the closure should be extracted into the handler package.
- Enforcement: `rules/go/handler-no-inline-error-handler.yml`
- Why: inline error-handler closures inside `main.go` mix bootstrap code with business logic, make the handler untestable in isolation, and cannot be reused. The Before/After Example in the doc shows the same logic moved from `main.go` to `pkg/handler/exists.go` with no behavioral change.
- Bad/Good snippets: reuse the doc's `## Before/After Example` `Before` block (the inline `router.Path("/exists/...").Handler(libhttp.NewErrorHandler(libhttp.WithErrorFunc(func(...) error { ... })))`) and the corresponding `After` blocks (`pkg/handler/exists.go` + `pkg/factory/factory.go` + `main.go` showing the three-file split).

**Rule 2 — MUST mechanical**
- Heading: `### RULE go-http-handler/no-inline-background-handler (MUST)`
- Owner: `go-http-handler-assistant`
- Applies when: `libhttp.NewBackgroundRunHandler(ctx, func ...)` is called with an inline anonymous function as its second argument in a `*.go` file OUTSIDE `**/pkg/handler/**`, `*_test.go`, and `vendor/`. The legitimate place is inside `pkg/handler/New*Handler` factories (returning `run.Func`).
- Enforcement: `rules/go/handler-no-inline-background-handler.yml`
- Why: same as rule 1 — testability, reusability, separation of concerns. The `## The Go Handler Pattern > Background Task Handlers` section shows the correct pattern: a `New[Purpose]Handler` function returning `run.Func` that the factory wraps with `libhttp.NewBackgroundRunHandler`.
- Bad/Good snippets: synthesize a minimal Bad/Good pair from the doc's `### Background Task Handlers` example:

  Bad — `main.go`:
  ```go
  router.Path("/forward-all").Handler(libhttp.NewBackgroundRunHandler(ctx, func(ctx context.Context) error {
      return processor.ProcessAll(ctx)
  }))
  ```

  Good — `pkg/handler/forward-all-invoices.go`:
  ```go
  func NewForwardAllInvoicesHandler(processor pkg.InvoiceForwarder) run.Func {
      return func(ctx context.Context) error {
          return processor.ProcessAll(ctx)
      }
  }
  ```

  `main.go`:
  ```go
  router.Path("/forward-all").Handler(factory.CreateForwardAllInvoicesHandler(ctx, forwarder))
  ```

**Rule 3 — MUST judgment**
- Heading: `### RULE go-http-handler/new-prefix-naming (MUST)`
- Owner: `go-http-handler-assistant`
- Applies when: a function declared in a `*.go` file inside `**/pkg/handler/**` returning `libhttp.WithError`, `run.Func`, or `http.Handler` does not follow the `New[Purpose]Handler` naming pattern. Pure ast-grep can match the function's return type but cannot reliably check whether the chosen name is descriptive enough (the convention prefers `NewForwardInvoiceHandler` over generic names like `NewSendHandler`) — that semantic check needs a reviewer.
- Enforcement: `judgment` (name-descriptiveness check needs whole-handler reasoning).
- Why: consistent `New*Handler` naming makes the handler discoverable across services, matches the constructor naming used elsewhere in bborbe Go projects (`New*` for constructors, `Create*` for factories), and signals the function's role as a handler factory.
- Bad/Good snippets: reuse the doc's `## Naming Conventions > Handler Functions` examples (`NewForwardInvoiceHandler`, `NewFetchDetailsHandler`).

**Rule 4 — SHOULD judgment**
- Heading: `### RULE go-http-handler/kebab-case-handler-files (SHOULD)`
- Owner: `go-http-handler-assistant`
- Applies when: a `*.go` file under `**/pkg/handler/**` is named with non-kebab-case-style (e.g. `exists_handler.go`, `existshandler.go`, or `handler.go`) instead of the documented `<action>-<noun>.go` kebab-case (e.g. `exists.go`, `forward-invoice.go`). Pure ast-grep operates on file contents, not filenames — this is a filesystem convention check.
- Enforcement: `judgment` (filename pattern check is outside ast-grep's content matching).
- Why: kebab-case action-oriented names (`forward-invoice.go`, `fetch-details.go`) immediately signal what the handler does without opening the file. Generic names (`handler.go`, `send.go`) require reading the file to discover its purpose; that's friction at scale.
- Bad/Good snippets: reuse the doc's `## Naming Conventions > Handler Files` examples (good: `forward-invoice.go`, `fetch-details.go`; avoid: `handler.go`, `send.go`).

Each block must follow the canonical pilot's exact formatting (`docs/go-context-cancellation-in-loops.md:160-192`).

2. Create `rules/go/handler-no-inline-error-handler.yml`:
   - `id: go-http-handler/no-inline-error-handler`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect a call to `libhttp.WithErrorFunc` whose argument is an inline anonymous `func` literal. Pattern guidance — the call site looks like `libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error { ... })`. Use a pattern with metavariable arguments:
     ```yaml
     rule:
       pattern: 'libhttp.WithErrorFunc(func($$$PARAMS) error { $$$BODY })'
     ```
     **Verify locally before committing.** If multi-line pattern parsing fails or doesn't fire, fall back to:
     ```yaml
     rule:
       kind: call_expression
       all:
         - has:
             field: function
             regex: '^libhttp\.WithErrorFunc$'
         - has:
             field: arguments
             has:
               kind: func_literal
     ```
   - `ignores`: **`**/pkg/handler/**`** (the legitimate location), `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`. Do NOT include `main.go` / `**/main.go` — `main.go` is precisely where this rule should fire.

3. Create `rules/go/handler-no-inline-background-handler.yml`:
   - `id: go-http-handler/no-inline-background-handler`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect a call to `libhttp.NewBackgroundRunHandler` whose second argument is an inline anonymous `func` literal. Pattern guidance:
     ```yaml
     rule:
       pattern: 'libhttp.NewBackgroundRunHandler($CTX, func($$$PARAMS) error { $$$BODY })'
     ```
     Fallback to `kind: call_expression` + field-based has if needed (same shape as rule 2 above, function name `libhttp.NewBackgroundRunHandler`).
   - `ignores`: same as rule 1 (`**/pkg/handler/**`, `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`)

4. Rules 3 + 4 (judgment) have NO ast-grep YAML. Their `### RULE` blocks carry the literal one-word value: `**Enforcement**: judgment` — no backticks, no parentheticals, no qualifying clauses. Reasoning/why-judgment text belongs in the `**Why**:` field below, NOT in `**Enforcement**:`. The walker copies `**Enforcement**:` verbatim into `rules/index.json`, and downstream coverage lint asserts the field equals exactly `"judgment"` for judgment-only rules.

5. **Verify ast-grep patterns locally** if `ast-grep` is on `$PATH` inside the container; if not (the container may lag the host-side claude-yolo:v0.9.0 image), defer verification to the operator's post-merge `scripts/scan.sh` pass. Either way, the patterns must be SYNTACTICALLY valid YAML and ast-grep-recognized — do not invent fields. Field-based `has` with `field: name` / `field: function` / `field: arguments` is the established shape from the prior PRs.

6. Run `make build-index` to refresh `rules/index.json`. It must grow from 17 entries to **21 entries**, sorted by `id`.

7. Verify each new index entry has:
   - `owner: "go-http-handler-assistant"`
   - `doc_path: "docs/go-http-handler-refactoring-guide.md"`
   - `anchor == id`
   - `level in ("MUST","SHOULD","MAY")`
   - non-empty `applies_when` and `enforcement`
   - For rules 3 + 4: `enforcement: "judgment"` (literal string)

8. Run `make precommit` — must pass.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT modify the existing rule blocks or YAMLs in `docs/go-context-cancellation-in-loops.md`, `docs/go-time-injection.md`, `docs/go-error-wrapping-guide.md`, `docs/go-security-linting.md`, `docs/go-factory-pattern.md`, or their YAMLs
- Do NOT modify the schema doc, the ast-grep guide, or `scripts/build-index.py`
- Do NOT rewrite `docs/go-http-handler-refactoring-guide.md`'s existing prose — only APPEND the four `### RULE` blocks at the END of the file (after `## Reference Examples`)
- Do NOT wire ast-grep into `make precommit`
- Do NOT invent ast-grep syntax — use only fields/kinds documented in `docs/ast-grep-rule-writing-guide.md` or shown in the canonical YAMLs cited in `<context>`
- Use the same Bad/Good code snippets shown in `docs/go-http-handler-refactoring-guide.md` itself where they exist; for rule 2, use the inline snippets in the prompt
- Generic examples only — no Candle/Epic/Broker/SignalStore. The doc uses `Invoice` / `Forward` / `Exists` examples; these are domain-neutral and acceptable
- No personal paths anywhere
- No `Co-Authored-By:` or attribution trailers
</constraints>

<verification>
Run from repo root:
```bash
# Four new ### RULE blocks added to the doc
grep -c '^### RULE go-http-handler/' docs/go-http-handler-refactoring-guide.md
# Must return: 4

# Two ast-grep YAMLs created
test -f rules/go/handler-no-inline-error-handler.yml && \
test -f rules/go/handler-no-inline-background-handler.yml && \
echo "yamls present: ok"

# YAMLs reference correct ids
head -1 rules/go/handler-no-inline-error-handler.yml | grep -q '^id: go-http-handler/no-inline-error-handler' && echo "yaml1 id: ok"
head -1 rules/go/handler-no-inline-background-handler.yml | grep -q '^id: go-http-handler/no-inline-background-handler' && echo "yaml2 id: ok"

# Severity: error on both
for f in rules/go/handler-no-inline-error-handler.yml rules/go/handler-no-inline-background-handler.yml; do
  head -5 "$f" | grep -q '^severity: error' || { echo "FAIL: $f missing severity: error"; exit 1; }
done
echo "severity: ok"

# Both YAMLs ignore pkg/handler/** (the legitimate location) AND the always-include set
for f in rules/go/handler-no-inline-error-handler.yml rules/go/handler-no-inline-background-handler.yml; do
  grep -q 'pkg/handler' "$f" || { echo "FAIL: $f does not ignore pkg/handler/**"; exit 1; }
  for pat in '\*_test\.go' 'vendor' 'mocks'; do
    grep -qE "$pat" "$f" || { echo "FAIL: $f missing ignore $pat"; exit 1; }
  done
done
echo "ignores complete (pkg/handler + tests + vendor + mocks): ok"

# Both YAMLs do NOT include main.go in ignores (this rule fires in main.go on purpose)
for f in rules/go/handler-no-inline-error-handler.yml rules/go/handler-no-inline-background-handler.yml; do
  grep -E '^\s*- "main\.go"' "$f" && { echo "FAIL: $f wrongly ignores main.go (rule must fire there)"; exit 1; }
done
echo "main.go not in ignores: ok"

# No YAMLs for the judgment rules
test ! -f rules/go/handler-new-prefix-naming.yml && echo "rule 3 has no YAML: ok"
test ! -f rules/go/handler-kebab-case-handler-files.yml && echo "rule 4 has no YAML: ok"

# 21 entries
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 21, f'expected 21 entries, got {len(d)}'
print(f'entries: {len(d)} ok')
"

# Expected sorted ids
python3 -c "
import json
ids = [e['id'] for e in json.load(open('rules/index.json'))]
expected = [
    'go-context/cancel-check-in-loop',
    'go-errors/inner-closure-no-double-wrap',
    'go-errors/no-bare-return-err',
    'go-errors/no-context-background-in-business-logic',
    'go-errors/no-fmt-errorf',
    'go-errors/sentinel-err-prefix-naming',
    'go-factory/no-cleanup-return',
    'go-factory/no-conditional-in-body',
    'go-factory/no-error-return',
    'go-factory/no-impl-in-factory-pkg',
    'go-http-handler/kebab-case-handler-files',
    'go-http-handler/new-prefix-naming',
    'go-http-handler/no-inline-background-handler',
    'go-http-handler/no-inline-error-handler',
    'go-security/chmod-return-checked',
    'go-security/dir-perms-too-permissive',
    'go-security/file-perms-too-permissive',
    'go-security/nosec-requires-reason',
    'go-time/inject-getter-not-create',
    'go-time/no-time-now-direct',
    'go-time/no-time-time-in-fields',
]
assert ids == expected, f'ids mismatch:\n  got: {ids}\n  expected: {expected}'
print('ids sorted: ok')
"

# Four new entries owned by go-http-handler-assistant + point at the right doc
python3 -c "
import json
go_h = [e for e in json.load(open('rules/index.json')) if e['id'].startswith('go-http-handler/')]
assert len(go_h) == 4, f'expected 4 go-http-handler/* entries, got {len(go_h)}'
for e in go_h:
    assert e['owner'] == 'go-http-handler-assistant', f\"owner mismatch for {e['id']}: {e['owner']}\"
    assert e['doc_path'] == 'docs/go-http-handler-refactoring-guide.md', f\"doc_path mismatch for {e['id']}\"
    assert e['anchor'] == e['id'], f\"anchor != id for {e['id']}: {e['anchor']}\"
    assert e['level'] in ('MUST','SHOULD','MAY'), f\"invalid level for {e['id']}: {e['level']}\"
    assert e['applies_when'], f\"empty applies_when for {e['id']}\"
    assert e['enforcement'], f\"empty enforcement for {e['id']}\"
judgment_ids = {'go-http-handler/new-prefix-naming', 'go-http-handler/kebab-case-handler-files'}
for e in go_h:
    if e['id'] in judgment_ids:
        assert e['enforcement'] == 'judgment', f\"{e['id']} enforcement must be literal 'judgment', got: {e['enforcement']}\"
print('go-http-handler entries: ok')
"

# Determinism
make build-index
git diff --exit-code rules/index.json && echo "deterministic: ok"

# Precommit clean
make precommit
```
</verification>
