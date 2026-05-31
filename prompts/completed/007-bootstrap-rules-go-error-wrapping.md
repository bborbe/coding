---
status: completed
summary: Migrated docs/go-error-wrapping-guide.md with five inline RULE blocks (3 mechanical + 2 judgment) and created three ast-grep YAML detectors; rules/index.json grew from 4 to 9 entries.
container: coding-bootstrap-error-wrapping-exec-007-bootstrap-rules-go-error-wrapping
dark-factory-version: v0.173.0
created: "2026-05-31T22:00:56Z"
queued: "2026-05-31T22:06:08Z"
started: "2026-05-31T22:06:13Z"
completed: "2026-05-31T22:08:17Z"
---

<summary>
- Second bootstrap prompt — migrates `docs/go-error-wrapping-guide.md` from prose-only to rule-blocks-inline (Model A: hand-author the contract once)
- Appends 5 `### RULE` blocks (3 MUST mechanical + 2 SHOULD judgment) corresponding to the doc's `## Key Rules` + `## Anti-Patterns`
- Adds 3 `rules/go/*.yml` ast-grep YAMLs for the mechanical rules; the 2 judgment rules carry `Enforcement: judgment`
- Runs `make build-index` so `rules/index.json` grows from 4 entries to 9
- Mirrors the proven `bootstrap-rules-go-time-injection.md` shape; this is the second pass of the mirror pattern
- Scope note: `## Key Rules` lists 7 items; this prompt extracts 5. Skipped: #4 "Multi-return wrapping" (snippet variation of rules 1+2, not a distinct rule) and #6 "Remove unused imports" (goimports' job, not a content rule)
</summary>

<objective>
Following the schema in `docs/rule-block-schema.md` and the ast-grep conventions in `docs/ast-grep-rule-writing-guide.md`, extract five rules from `docs/go-error-wrapping-guide.md` as inline `### RULE` blocks, write ast-grep YAML detectors for the three MUST mechanical rules, and refresh `rules/index.json` via the walker. Every block must conform to the schema (Owner, Applies when, Enforcement fields, ID format `<lang>/<topic>/<slug>`, anchor = id verbatim).
</objective>

<context>
Read `CLAUDE.md` for project conventions, including the doc-agent alignment table (`go-error-wrapping-guide.md` → `go-error-assistant`).
Read `docs/rule-block-schema.md` for the rule-block contract — required fields, level tokens, ID format, anchor rule (`anchor == id` verbatim).
Read `docs/ast-grep-rule-writing-guide.md` for the YAML conventions — frontmatter shape, pattern strategies, pitfalls (especially the `main.go` + `**/main.go` dual-ignore), smoke testing, when NOT to write a YAML.
Read `docs/go-error-wrapping-guide.md` — the doc to migrate. The `## Key Rules` section (around line 97) and `## Anti-Patterns` section (around line 172) list the rules to extract; the rest of the doc provides Bad/Good code snippets to cite.
Read `docs/go-context-cancellation-in-loops.md` lines 160-192 — the canonical pilot `### RULE` block. The new blocks MUST match its formatting exactly: heading line `### RULE <id> (LEVEL)`, then bolded fields `**Owner**:`, `**Applies when**:`, `**Enforcement**:`, then `**Why**:`, then `#### Bad` / `#### Good` code blocks.
Read `rules/go/cancel-check-in-loop.yml`, `rules/go/no-time-now-direct.yml`, `rules/go/no-time-time-in-fields.yml` — canonical ast-grep YAMLs. Match their shape (frontmatter keys: `id`, `language`, `severity`, `message`, `rule`, `ignores`).
Read `scripts/build-index.py` and run `python3 scripts/build-index.py` once to see the current `rules/index.json` shape (4 entries) before changes.
</context>

<requirements>
1. Append five `### RULE` blocks at the END of `docs/go-error-wrapping-guide.md` (after the existing `## Testing` section). Do NOT modify any prose above. The five blocks, in order:

**Rule 1 — MUST mechanical**
- Heading: `### RULE go-errors/no-fmt-errorf (MUST)`
- Owner: `go-error-assistant`
- Applies when: any `*.go` file outside `main.go`, `*_test.go`, `vendor/` calls `fmt.Errorf(...)`.
- Enforcement: `rules/go/no-fmt-errorf.yml`
- Why: `fmt.Errorf` loses ctx-derived structured data and stack traces. Use `errors.Wrapf(ctx, err, "...")` (wrapping) or `errors.Errorf(ctx, "...", args...)` (new error) from `github.com/bborbe/errors` instead.
- Bad/Good snippets: reuse `## Examples > Fix: Replace fmt.Errorf` and `## Examples > Fix: New Error Without Cause` blocks from the doc itself.

**Rule 2 — MUST mechanical**
- Heading: `### RULE go-errors/no-bare-return-err (MUST)`
- Owner: `go-error-assistant`
- Applies when: a Go `return err` statement appears inside an `if err != nil { ... }` block, outside `*_test.go` and `vendor/`. Inner closures (e.g. `db.Update(func(tx *bolt.Tx) error { ... })`) where the outer scope already wraps are an exception — see RULE `go-errors/inner-closure-no-double-wrap` below; ast-grep flags them and the judgment tier drops false positives.
- Enforcement: `rules/go/no-bare-return-err.yml`
- Why: bare `return err` propagates errors without context or stack trace. Wrap with `errors.Wrapf(ctx, err, "operation description")` at every layer that adds meaning.
- Bad/Good snippets: reuse `## Anti-Patterns > Bare return` block + the corresponding `### Wrapping an Existing Error` block from `## Core Patterns`.

**Rule 3 — MUST mechanical**
- Heading: `### RULE go-errors/no-context-background-in-business-logic (MUST)`
- Owner: `go-error-assistant`
- Applies when: a Go `context.Background()` call appears outside `main.go`, `cmd/**`, `*_test.go`, `vendor/`. Top-level goroutine spawners in `main` are exempt by path filter; non-business-logic uses get adjudicated by the judgment tier.
- Enforcement: `rules/go/no-context-background-in-business-logic.yml`
- Why: `context.Background()` discards any context data the caller added via `errors.AddToContext`, making subsequent wrapping pointless. Add `ctx context.Context` as a function parameter and propagate from callers.
- Bad/Good snippets: reuse `## Anti-Patterns > context.Background() in business logic` block + the `### Fix: Function Missing ctx` block from `## Examples`.

**Rule 4 — SHOULD judgment**
- Heading: `### RULE go-errors/inner-closure-no-double-wrap (SHOULD)`
- Owner: `go-error-assistant`
- Applies when: an inner closure (passed to `db.Update`, `filepath.WalkDir`, or similar callback APIs) calls `errors.Wrap`/`errors.Wrapf` while the surrounding function ALSO wraps the closure's return value. Distinguishing this case from "the outer doesn't wrap" requires whole-function reasoning.
- Enforcement: `judgment` (no ast-grep — closure double-wrap detection requires reading both the closure body AND the calling function's wrap layer).
- Why: double-wrapping inflates error messages with redundant prefixes (`save data X: update: put: bolt: connection refused`) and doesn't add new information. The outer wrap is enough.
- Bad/Good snippets: reuse `## Anti-Patterns > Double-wrapping inner closures` block + the `### Inner Closures — Do Not Double-Wrap` block from `## Examples`.

**Rule 5 — SHOULD judgment**
- Heading: `### RULE go-errors/sentinel-err-prefix-naming (SHOULD)`
- Owner: `go-error-assistant`
- Applies when: a package-level sentinel error variable uses the legacy `XxxError` / `XxxErr` naming convention (e.g. `BucketNotFoundErr`, `ConnectionError`) instead of the stdlib-style `ErrXxx` prefix (`ErrBucketNotFound`, `ErrConnection`). Detection is semantic — distinguishing a sentinel error variable from any other `ErrXxx`-shaped identifier requires understanding the value's type.
- Enforcement: `judgment` (no ast-grep — naming conventions are pattern-recognition for the LLM, not syntactic).
- Why: stdlib uses `Err` prefix (`io.EOF`, `sql.ErrNoRows`); matching it makes the convention discoverable and consistent. Legacy projects may keep the old name as a `Deprecated:` alias during transition.
- Bad/Good snippets: reuse the `### Sentinel Errors` block from `## Core Patterns` (showing `var ErrNotFound = stderrors.New(...)`) + the `### Renaming Sentinel Errors (Backwards-Compat Alias)` block.

Each block must follow the canonical pilot's exact formatting (`docs/go-context-cancellation-in-loops.md:160-192`) — verbatim field labels with `**` bolding, blank line between fields, `#### Bad` / `#### Good` H4 headings for the example code blocks.

2. Create `rules/go/no-fmt-errorf.yml` matching the shape of `rules/go/no-time-now-direct.yml`:
   - `id: go-errors/no-fmt-errorf`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block — short summary, blank line, then `See docs/go-error-wrapping-guide.md (RULE go-errors/no-fmt-errorf).`
   - `rule`: `pattern: fmt.Errorf($$$ARGS)`
   - `ignores`: `main.go`, `**/main.go`, `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`

3. Create `rules/go/no-bare-return-err.yml`:
   - `id: go-errors/no-bare-return-err`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect `return err` inside an `if err != nil { ... }` block. Pattern guidance:
     ```yaml
     rule:
       pattern: return err
       inside:
         kind: if_statement
         has:
           pattern: err != nil
     ```
     Alternative shape using `any:` for multi-line bodies is acceptable as long as a synthetic `if err != nil { return err }` matches and a `return errors.Wrapf(ctx, err, "...")` inside the same shape does NOT match.
   - `ignores`: same as rule 1

4. Create `rules/go/no-context-background-in-business-logic.yml`:
   - `id: go-errors/no-context-background-in-business-logic`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: `pattern: context.Background()`
   - `ignores`: `main.go`, `**/main.go`, `cmd/**`, `**/cmd/**`, `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**` — the `cmd/**` additions are critical because top-level goroutine spawners in `main` are exempt per the doc's `## Where context.Background() Is Allowed` section.

5. The two judgment rules (rule 4, rule 5) have NO ast-grep YAMLs. Their `### RULE` blocks carry `Enforcement: judgment` (literal string, no path).

6. There is NO ast-grep smoke inside this prompt — operator runs `scripts/scan.sh <target-repo>` post-merge to confirm the detectors fire correctly on real code. YAML validity is verified mechanically by `make build-index` reading the index and the file existence/content checks below.

7. Run `make build-index` to refresh `rules/index.json`. It must grow from 4 entries to **9 entries** (pilot + 3 go-time + 5 new go-errors rules), with entries sorted by `id` and each entry's keys alphabetically sorted.

8. Verify each new index entry has:
   - `owner: "go-error-assistant"`
   - `doc_path: "docs/go-error-wrapping-guide.md"`
   - `anchor == id` (the rule ID verbatim)
   - `level` in `("MUST","SHOULD","MAY")`
   - non-empty `applies_when` and `enforcement`
   - For rules 4 + 5: `enforcement: "judgment"` (literal string)

9. Run `make precommit` — must pass (link check + JSON validity unchanged).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT modify the existing pilot rule (`docs/go-context-cancellation-in-loops.md` rule block or `rules/go/cancel-check-in-loop.yml`)
- Do NOT modify the existing go-time rule blocks in `docs/go-time-injection.md` or `rules/go/no-time-*.yml`
- Do NOT modify the schema doc (`docs/rule-block-schema.md`) or the ast-grep guide (`docs/ast-grep-rule-writing-guide.md`)
- Do NOT rewrite `docs/go-error-wrapping-guide.md`'s existing prose — only APPEND the five `### RULE` blocks at the END of the file (after the `## Testing` section)
- Do NOT wire ast-grep into `make precommit` — that is Phase 1 territory and out of scope
- Do NOT attempt `ast-grep scan` from inside the container (binary may be absent until claude-yolo:v0.9.0 propagates to dark-factory's default image)
- Use the same Bad/Good code snippets shown in `docs/go-error-wrapping-guide.md` itself; do NOT invent new ones
- Generic examples only (User, Order, Product, Customer) — no Candle/Epic/Broker/SignalStore
- No personal paths (`~/Documents/`, `/Users/`) anywhere
- No `Co-Authored-By:` or attribution trailers (project convention)
</constraints>

<verification>
Run from repo root:
```bash
# Five new ### RULE blocks added to the doc
grep -c '^### RULE go-errors/' docs/go-error-wrapping-guide.md
# Must return: 5

# Three ast-grep YAMLs created
test -f rules/go/no-fmt-errorf.yml && \
test -f rules/go/no-bare-return-err.yml && \
test -f rules/go/no-context-background-in-business-logic.yml && \
echo "yamls present: ok"

# YAMLs reference the correct ids on their first line
head -1 rules/go/no-fmt-errorf.yml | grep -q '^id: go-errors/no-fmt-errorf' && echo "yaml1 id: ok"
head -1 rules/go/no-bare-return-err.yml | grep -q '^id: go-errors/no-bare-return-err' && echo "yaml2 id: ok"
head -1 rules/go/no-context-background-in-business-logic.yml | grep -q '^id: go-errors/no-context-background-in-business-logic' && echo "yaml3 id: ok"

# All three YAMLs use severity: error (MUST rules → mechanical layer → error severity per the ast-grep guide)
for f in rules/go/no-fmt-errorf.yml rules/go/no-bare-return-err.yml rules/go/no-context-background-in-business-logic.yml; do
  head -5 "$f" | grep -q '^severity: error' || { echo "FAIL: $f missing severity: error"; exit 1; }
done
echo "severity: ok"

# No YAML for the judgment rules (rule 4, rule 5)
test ! -f rules/go/inner-closure-no-double-wrap.yml && echo "rule 4 has no YAML: ok"
test ! -f rules/go/sentinel-err-prefix-naming.yml && echo "rule 5 has no YAML: ok"

# rules/index.json now has 9 entries
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 9, f'expected 9 entries, got {len(d)}'
print(f'entries: {len(d)} ok')
"

# All nine expected ids present and sorted
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
    'go-time/inject-getter-not-create',
    'go-time/no-time-now-direct',
    'go-time/no-time-time-in-fields',
]
assert ids == expected, f'ids mismatch:\n  got: {ids}\n  expected: {expected}'
print('ids sorted: ok')
"

# Five new entries owned by go-error-assistant + point at the right doc
python3 -c "
import json
go_errors = [e for e in json.load(open('rules/index.json')) if e['id'].startswith('go-errors/')]
assert len(go_errors) == 5, f'expected 5 go-errors/* entries, got {len(go_errors)}'
for e in go_errors:
    assert e['owner'] == 'go-error-assistant', f\"owner mismatch for {e['id']}: {e['owner']}\"
    assert e['doc_path'] == 'docs/go-error-wrapping-guide.md', f\"doc_path mismatch for {e['id']}\"
    assert e['anchor'] == e['id'], f\"anchor != id for {e['id']}: {e['anchor']}\"
    assert e['level'] in ('MUST','SHOULD','MAY'), f\"invalid level for {e['id']}: {e['level']}\"
    assert e['applies_when'], f\"empty applies_when for {e['id']}\"
    assert e['enforcement'], f\"empty enforcement for {e['id']}\"
judgment_ids = {'go-errors/inner-closure-no-double-wrap', 'go-errors/sentinel-err-prefix-naming'}
for e in go_errors:
    if e['id'] in judgment_ids:
        assert e['enforcement'] == 'judgment', f\"{e['id']} enforcement must be literal 'judgment', got: {e['enforcement']}\"
print('go-errors entries: ok')
"

# Determinism — running build-index again produces identical bytes
make build-index
git diff --exit-code rules/index.json && echo "deterministic: ok"

# make precommit clean
make precommit
```
</verification>
