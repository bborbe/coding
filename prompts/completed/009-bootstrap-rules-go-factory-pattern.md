---
status: completed
summary: 'Appended four ### RULE blocks to docs/go-factory-pattern.md (go-factory/no-error-return, go-factory/no-conditional-in-body, go-factory/no-cleanup-return, go-factory/no-impl-in-factory-pkg), created three ast-grep YAML detectors, and grew rules/index.json from 13 to 17 entries.'
container: coding-bootstrap-go-factory-exec-009-bootstrap-rules-go-factory-pattern
dark-factory-version: v0.173.0
created: "2026-06-01T21:50:49Z"
queued: "2026-06-01T22:04:08Z"
started: "2026-06-01T22:04:15Z"
completed: "2026-06-01T22:07:06Z"
---

<summary>
- Fourth bootstrap prompt — migrates `docs/go-factory-pattern.md` from prose-only to rule-blocks-inline (Model A)
- Appends 4 `### RULE` blocks (3 MUST mechanical + 1 MUST judgment) corresponding to the doc's `## 1. Core Principles` + `## Summary > Factory Checklist`
- Adds 3 `rules/go/*.yml` ast-grep YAMLs for the mechanical rules; the judgment rule carries `Enforcement: judgment`
- Runs `make build-index` so `rules/index.json` grows from 13 entries to 17
- Mirrors the proven go-time + go-errors + go-security bootstrap templates (3 prior PRs merged to master)
- Scope note: doc has ~10 distinct rules across the Checklist; this prompt extracts 4 that are mechanically tractable + 1 judgment for impl-in-factory-pkg. Skipped (covered by judgment-tier or too judgment-heavy): naming `Create*` vs `New*` (file-path + AST = fragile), inline business logic / loops / anon functions (overlaps with no-conditional), boot-time validation (judgment), singletons (judgment), split-across-files (file-system check, not AST). Will revisit in a future PR if the dispatcher needs them.
</summary>

<objective>
Following the schema in `docs/rule-block-schema.md` and the ast-grep conventions in `docs/ast-grep-rule-writing-guide.md`, extract four rules from `docs/go-factory-pattern.md` as inline `### RULE` blocks, write ast-grep YAML detectors for the three mechanical rules, and refresh `rules/index.json` via the walker. Every block must conform to the schema (Owner, Applies when, Enforcement fields, ID format `<lang>/<topic>/<slug>`, anchor = id verbatim).
</objective>

<context>
Read `CLAUDE.md` for project conventions, including the doc-agent alignment table (`go-factory-pattern.md` → `go-factory-pattern-assistant`).
Read `docs/rule-block-schema.md` for the rule-block contract.
Read `docs/ast-grep-rule-writing-guide.md` for the YAML conventions — especially the `main.go` + `**/main.go` dual-ignore, the `**/mocks/**` default, and the ast-grep 0.43.0 limitation on metavariable constraints (enumeration > inverted-match in this version).
Read `docs/go-factory-pattern.md` — the doc to migrate. The `## 1. Core Principles` section (around line 5) lists what factories MUST NOT do; `## Summary > Factory Checklist` (around line 408) restates them; section 6 (Bad Factory Patterns) provides concrete Bad/Good code; section 7 (Pass-through Wrappers) carves out the one acceptable exception for `error`-returning factories.
Read `docs/go-context-cancellation-in-loops.md` lines 160-192 — the canonical pilot `### RULE` block.
Read three canonical small ast-grep YAMLs: `rules/go/no-fmt-errorf.yml`, `rules/go/no-time-now-direct.yml`, `rules/go/file-perms-too-permissive.yml`.
Read `scripts/build-index.py` and run `python3 scripts/build-index.py` once to see the current `rules/index.json` shape (13 entries) before changes.
</context>

<requirements>
1. Append four `### RULE` blocks at the END of `docs/go-factory-pattern.md` (after the existing `## Summary` section). Do NOT modify any prose above. The four blocks, in order:

**Rule 1 — MUST mechanical**
- Heading: `### RULE go-factory/no-error-return (MUST)`
- Owner: `go-factory-pattern-assistant`
- Applies when: a Go function whose name starts with `Create` declared in a `*.go` file outside `*_test.go` and `vendor/` has a return type list that includes `error`. The single permitted exception is a pass-through wrapper per the doc's section 7 — a one-statement factory that immediately returns an error-returning constructor call without adding wiring, logging, or validation. The mechanical layer flags every match; the judgment tier filters legitimate pass-throughs.
- Enforcement: `rules/go/factory-no-error-return.yml`
- Why: factories are pure composition. Errors are runtime concerns and belong in `main.go Run` or behind a Provider interface (section 5). A factory returning `error` typically signals boot-time validation, dispatch logic, or constructor failure handling living in the wrong layer.
- Bad/Good snippets: reuse `## 6.2 Boot-time Conditional Wiring` Bad/Good pair (the `CreateDeliverer` example).

**Rule 2 — MUST mechanical**
- Heading: `### RULE go-factory/no-conditional-in-body (MUST)`
- Owner: `go-factory-pattern-assistant`
- Applies when: a Go function whose name starts with `Create` declared in a `*.go` file outside `*_test.go` and `vendor/` contains an `if`, `switch`, or `for` statement anywhere in its body. Anonymous functions inside the body that are pure pass-throughs (single method call, no logic — see section 4.3 `Run Function Wrapper`) are an acceptable exception adjudicated by the judgment tier.
- Enforcement: `rules/go/factory-no-conditional-in-body.yml`
- Why: conditionals in a factory mean the factory is making a decision. Decisions belong in `main.go Run` (boot-time) or behind a Provider interface (runtime dispatch). The factory's job is to wire pre-validated dependencies into a constructor call tree.
- Bad/Good snippets: reuse `## 5 > BAD: Dispatch inside the factory` (`CreateAgentForTaskType` switch) paired with `## 5 > GOOD: Provider interface owns dispatch` (`CreateAgentProvider`).

**Rule 3 — MUST mechanical**
- Heading: `### RULE go-factory/no-cleanup-return (MUST)`
- Owner: `go-factory-pattern-assistant`
- Applies when: a Go function whose name starts with `Create` declared in a `*.go` file outside `*_test.go` and `vendor/` has a return type list that includes `func()` (a cleanup closure). Common shapes: `(T, func())`, `(T, func(), error)`, `(func(), error)`.
- Enforcement: `rules/go/factory-no-cleanup-return.yml`
- Why: cleanup lifecycle is `main.go`'s concern via `defer`. A factory returning a cleanup closure forces the caller to know about lifecycle semantics the factory shouldn't own. Lift cleanup to the call site.
- Bad/Good snippets: reuse `## 6.2` `CreateDeliverer` example (which returns `(Deliverer, func(), error)`) → the fixed `CreateNoopDeliverer` / `CreateKafkaDeliverer` pair.

**Rule 4 — MUST judgment**
- Heading: `### RULE go-factory/no-impl-in-factory-pkg (MUST)`
- Owner: `go-factory-pattern-assistant`
- Applies when: a `*.go` file inside `pkg/factory/` (any path matching `**/pkg/factory/*.go`) contains a struct type declaration with non-trivial methods (i.e. methods with logic beyond a trivial accessor), an interface declaration with multiple methods, or any function declaration that is NOT a `Create*` factory function. Detecting "non-trivial" requires reading the method body — pure ast-grep can match `type X struct` and method declarations but cannot reliably decide which methods are "trivial".
- Enforcement: `judgment` (no ast-grep — implementation-vs-trivial-helper distinction needs whole-method reasoning).
- Why: `pkg/factory/` is wiring-only. Implementation types belong in `pkg/` (flat) or `pkg/<subpkg>/` (grouped). A struct like `mocoRoundTripper` inside `pkg/factory/roundtripper.go` is wrong — move it.
- Bad/Good snippets: synthesize from the doc's section 3 prose (the doc doesn't have explicit Bad/Good code here). **Note: the impl code is identical in Bad and Good — the rule is about file location, expressed in the path comment above each code block.** Lead the Bad/Good with a one-line "Same impl, wrong directory" / "Same impl, right directory" caption so readers don't miss the point.

  Bad — `pkg/factory/roundtripper.go`:
  ```go
  type mocoRoundTripper struct { /* impl */ }
  func (r *mocoRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) { /* logic */ }
  ```

  Good — `pkg/roundtripper/roundtripper.go`:
  ```go
  type mocoRoundTripper struct { /* impl */ }
  func (r *mocoRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) { /* logic */ }
  ```
  with `pkg/factory/factory.go` containing only:
  ```go
  func CreateRoundTripper() http.RoundTripper { return roundtripper.NewMocoRoundTripper() }
  ```

Each block must follow the canonical pilot's exact formatting (`docs/go-context-cancellation-in-loops.md:160-192`) — verbatim field labels with `**` bolding, blank line between fields, `#### Bad` / `#### Good` H4 headings for the example code blocks.

2. Create `rules/go/factory-no-error-return.yml`:
   - `id: go-factory/no-error-return`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect a function declaration whose name starts with `Create` and whose return type list includes `error`. Pattern guidance — use `any:` alternation across the two common shapes (single-error return and tuple-with-error):
     ```yaml
     rule:
       any:
         - pattern: |
             func Create$NAME($$$ARGS) error {
               $$$BODY
             }
         - pattern: |
             func Create$NAME($$$ARGS) ($$$RET, error) {
               $$$BODY
             }
     ```
     Verify the patterns trigger on a synthetic `func CreateX(a A) error { ... }` and `func CreateX(a A) (B, error) { ... }` BEFORE committing. If ast-grep's pattern parsing rejects the multi-line shape, fall back to `kind: function_declaration` with a constraint on the identifier regex (`^Create`) plus a `has` clause for the return type.
   - `ignores`: `main.go`, `**/main.go`, `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`

3. Create `rules/go/factory-no-conditional-in-body.yml`:
   - `id: go-factory/no-conditional-in-body`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect a function declaration whose name starts with `Create` and whose body contains an `if_statement`, `switch_statement`, or `for_statement`. Pattern guidance using `kind` + `inside`:
     ```yaml
     rule:
       any:
         - kind: if_statement
         - kind: expression_switch_statement
         - kind: type_switch_statement
         - kind: for_statement
       inside:
         stopBy: end
         kind: function_declaration
         has:
           kind: identifier
           regex: '^Create'
     ```
     If the `inside`/`has` composition doesn't filter correctly, fall back to `kind: function_declaration` + `regex` on identifier + `has` for the conditional kinds. Verify on synthetic Bad/Good before committing.
   - `ignores`: same as rule 1

4. Create `rules/go/factory-no-cleanup-return.yml`:
   - `id: go-factory/no-cleanup-return`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect a `Create*` function whose return type list includes `func()`. Pattern guidance:
     ```yaml
     rule:
       any:
         - pattern: |
             func Create$NAME($$$ARGS) ($$$T, func()) {
               $$$BODY
             }
         - pattern: |
             func Create$NAME($$$ARGS) ($$$T, func(), error) {
               $$$BODY
             }
         - pattern: |
             func Create$NAME($$$ARGS) (func(), error) {
               $$$BODY
             }
     ```
     If pattern parsing rejects multi-line, fall back to `kind: function_declaration` + identifier regex + `has` clause walking the return type list for `func()`.
   - `ignores`: same as rule 1

5. Rule 4 (`no-impl-in-factory-pkg`) has NO ast-grep YAML. Its `### RULE` block carries `Enforcement: judgment`.

6. No ast-grep smoke inside this prompt — operator runs `scripts/scan.sh <target-repo>` post-merge to confirm the detectors fire correctly on real code (any bborbe Go service repo has `pkg/factory/factory.go` files to exercise).

7. Run `make build-index` to refresh `rules/index.json`. It must grow from 13 entries to **17 entries** (existing 13 + 4 new go-factory), with entries sorted by `id`.

8. Verify each new index entry has:
   - `owner: "go-factory-pattern-assistant"`
   - `doc_path: "docs/go-factory-pattern.md"`
   - `anchor == id`
   - `level in ("MUST","SHOULD","MAY")`
   - non-empty `applies_when` and `enforcement`
   - For rule 4: `enforcement: "judgment"` (literal string)

9. Run `make precommit` — must pass.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT modify the existing rule blocks or YAMLs in `docs/go-context-cancellation-in-loops.md`, `docs/go-time-injection.md`, `docs/go-error-wrapping-guide.md`, `docs/go-security-linting.md`, or their YAMLs
- Do NOT modify the schema doc, the ast-grep guide, or `scripts/build-index.py`
- Do NOT rewrite `docs/go-factory-pattern.md`'s existing prose — only APPEND the four `### RULE` blocks at the END of the file (after `## Summary`)
- Do NOT wire ast-grep into `make precommit`
- Do NOT attempt `ast-grep scan` from inside the container
- Use the same Bad/Good code snippets shown in `docs/go-factory-pattern.md` itself where they exist; for rule 4, synthesize minimal generic examples per the prompt's inline scaffold
- Generic examples only — no Candle/Epic/Broker/SignalStore (use User, Order, Product, Customer if synthesizing)
- No personal paths anywhere
- No `Co-Authored-By:` or attribution trailers
</constraints>

<verification>
Run from repo root:
```bash
# Four new ### RULE blocks added to the doc
grep -c '^### RULE go-factory/' docs/go-factory-pattern.md
# Must return: 4

# Three ast-grep YAMLs created
test -f rules/go/factory-no-error-return.yml && \
test -f rules/go/factory-no-conditional-in-body.yml && \
test -f rules/go/factory-no-cleanup-return.yml && \
echo "yamls present: ok"

# YAMLs reference the correct ids on their first line
head -1 rules/go/factory-no-error-return.yml | grep -q '^id: go-factory/no-error-return' && echo "yaml1 id: ok"
head -1 rules/go/factory-no-conditional-in-body.yml | grep -q '^id: go-factory/no-conditional-in-body' && echo "yaml2 id: ok"
head -1 rules/go/factory-no-cleanup-return.yml | grep -q '^id: go-factory/no-cleanup-return' && echo "yaml3 id: ok"

# All three YAMLs use severity: error
for f in rules/go/factory-no-error-return.yml rules/go/factory-no-conditional-in-body.yml rules/go/factory-no-cleanup-return.yml; do
  head -5 "$f" | grep -q '^severity: error' || { echo "FAIL: $f missing severity: error"; exit 1; }
done
echo "severity: ok"

# No YAML for the judgment rule (rule 4)
test ! -f rules/go/factory-no-impl-in-factory-pkg.yml && echo "rule 4 has no YAML: ok"

# rules/index.json now has 17 entries
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 17, f'expected 17 entries, got {len(d)}'
print(f'entries: {len(d)} ok')
"

# Expected ids present and sorted
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

# Four new entries owned by go-factory-pattern-assistant + point at the right doc
python3 -c "
import json
go_fact = [e for e in json.load(open('rules/index.json')) if e['id'].startswith('go-factory/')]
assert len(go_fact) == 4, f'expected 4 go-factory/* entries, got {len(go_fact)}'
for e in go_fact:
    assert e['owner'] == 'go-factory-pattern-assistant', f\"owner mismatch for {e['id']}: {e['owner']}\"
    assert e['doc_path'] == 'docs/go-factory-pattern.md', f\"doc_path mismatch for {e['id']}\"
    assert e['anchor'] == e['id'], f\"anchor != id for {e['id']}: {e['anchor']}\"
    assert e['level'] in ('MUST','SHOULD','MAY'), f\"invalid level for {e['id']}: {e['level']}\"
    assert e['applies_when'], f\"empty applies_when for {e['id']}\"
    assert e['enforcement'], f\"empty enforcement for {e['id']}\"
judgment_ids = {'go-factory/no-impl-in-factory-pkg'}
for e in go_fact:
    if e['id'] in judgment_ids:
        assert e['enforcement'] == 'judgment', f\"{e['id']} enforcement must be literal 'judgment', got: {e['enforcement']}\"
print('go-factory entries: ok')
"

# Determinism — running build-index again produces identical bytes
make build-index
git diff --exit-code rules/index.json && echo "deterministic: ok"

# make precommit clean
make precommit
```
</verification>
