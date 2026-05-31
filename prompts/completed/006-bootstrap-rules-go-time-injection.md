---
status: completed
summary: Migrated docs/go-time-injection.md with three inline RULE blocks (go-time/no-time-now-direct, go-time/no-time-time-in-fields, go-time/inject-getter-not-create), created two ast-grep YAML detectors, and refreshed rules/index.json to 4 entries.
container: coding-rule-base-pilot-exec-006-bootstrap-rules-go-time-injection
dark-factory-version: v0.173.0
created: "2026-05-31T20:22:38Z"
queued: "2026-05-31T20:34:07Z"
started: "2026-05-31T20:34:18Z"
completed: "2026-05-31T20:36:09Z"
---

<summary>
- First bootstrap prompt — migrates `docs/go-time-injection.md` from prose-only to rule-blocks-inline (Model A: hand-author the contract once)
- Appends 3 `### RULE` blocks (2 MUST mechanical + 1 MUST judgment) corresponding to the doc's anti-patterns
- Adds 2 `rules/go/*.yml` ast-grep YAMLs for the mechanical rules; the judgment rule has `Enforcement: judgment`
- Runs `make build-index` so `rules/index.json` grows from 1 entry (pilot) to 4 entries
- This prompt's shape is the template to mirror across the remaining 60+ guides
</summary>

<objective>
Following the schema in `docs/rule-block-schema.md`, extract three rules from `docs/go-time-injection.md`'s Anti-Patterns section as inline `### RULE` blocks, write ast-grep YAML detectors for the two MUST mechanical rules, and refresh `rules/index.json` via the walker. Every block must conform to the schema (Owner, Applies when, Enforcement fields, ID format `<lang>/<topic>/<slug>`, anchor = id verbatim).
</objective>

<context>
Read `CLAUDE.md` for project conventions, including the doc-agent alignment table (`go-time-injection.md` → `go-time-assistant`).
Read `docs/rule-block-schema.md` for the rule-block contract — required fields, level tokens, ID format, anchor rule (`anchor == id` verbatim).
Read `docs/go-time-injection.md` — the doc to migrate. The `## Anti-Patterns` section (around line 126) lists the rules to extract; the rest of the doc provides Bad/Good code snippets to cite.
Read `docs/go-context-cancellation-in-loops.md` lines 160-192 — the canonical pilot `### RULE` block. The new blocks MUST match its formatting exactly: heading line `### RULE <id> (LEVEL)`, then bolded fields `**Owner**:`, `**Applies when**:`, `**Enforcement**:`, then `**Why**:`, then `#### Bad` / `#### Good` code blocks.
Read `rules/go/cancel-check-in-loop.yml` — the canonical pilot ast-grep YAML. The new YAMLs MUST match its shape (frontmatter keys: `id`, `language`, `severity`, `message`, `rule`, `ignores`).
Read `scripts/build-index.py` and run `python3 scripts/build-index.py` once to see the current `rules/index.json` shape before changes.
</context>

<requirements>
1. Append three `### RULE` blocks at the END of `docs/go-time-injection.md` (after the existing `## Anti-Patterns` section). Do NOT modify any prose above. The three blocks, in order:

**Rule 1 — MUST mechanical**
- Heading: `### RULE go-time/no-time-now-direct (MUST)`
- Owner: `go-time-assistant`
- Applies when: any `*.go` file outside `main.go`, `*_test.go`, `vendor/` calls `time.Now()` directly.
- Enforcement: `rules/go/no-time-now-direct.yml`
- Why: `time.Now()` is non-deterministic and untestable; production code must inject a `libtime.CurrentDateTimeGetter` and tests must use `libtime.SetNow()`.
- Bad/Good snippets: reuse the Anti-Patterns line "`time.Now()` in production → inject `CurrentDateTimeGetter`" plus a 3-5 line Bad example showing direct `time.Now()` in a service method, and the corresponding Good example from the Constructor section.

**Rule 2 — MUST mechanical**
- Heading: `### RULE go-time/no-time-time-in-fields (MUST)`
- Owner: `go-time-assistant`
- Applies when: any Go struct field is declared with stdlib type `time.Time` or `time.Duration`.
- Enforcement: `rules/go/no-time-time-in-fields.yml`
- Why: `libtime.DateTime` and `libtime.Duration` carry marshalling and timezone discipline; stdlib types lose both at the type boundary.
- Bad/Good snippets: reuse the Domain Objects section — Bad shows `Created time.Time`, Good shows `Created libtime.DateTime` inside an `Order` struct.

**Rule 3 — MUST judgment**
- Heading: `### RULE go-time/inject-getter-not-create (MUST)`
- Owner: `go-time-assistant`
- Applies when: a factory or constructor file outside `main.go` calls `libtime.NewCurrentDateTime()`.
- Enforcement: `judgment` (no ast-grep — factory/constructor identification requires whole-function context; ast-grep cannot reliably distinguish a factory call site from a test fixture).
- Why: factories must be pure composition; creating `libtime.CurrentDateTime` inside a factory hardcodes the clock and breaks the test-time `SetNow` override.
- Bad/Good snippets: reuse the Creation section — Bad shows `NewCurrentDateTime()` called inside a factory function, Good shows the factory accepting `currentDateTimeGetter libtime.CurrentDateTimeGetter` as a parameter.

Each block must follow the canonical pilot's exact formatting (`docs/go-context-cancellation-in-loops.md:160-192`) — verbatim field labels with `**` bolding, blank line between fields, `#### Bad` / `#### Good` H4 headings for the example code blocks.

2. Create `rules/go/no-time-now-direct.yml` matching the shape of `rules/go/cancel-check-in-loop.yml`:
   - `id: go-time/no-time-now-direct`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block: short summary, then "See docs/go-time-injection.md (RULE go-time/no-time-now-direct)."
   - `rule`: `pattern: time.Now()`
   - `ignores`: `**/main.go`, `**/*_test.go`, `vendor/**`, `**/vendor/**`

3. Create `rules/go/no-time-time-in-fields.yml` matching the same shape:
   - `id: go-time/no-time-time-in-fields`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detect `time.Time` (and `time.Duration`) appearing as the TYPE of a struct field. Patterns to consider:
     - One rule using `pattern: $NAME time.Time` (matches `Created time.Time` style field declarations)
     - Use `any:` block to also match `pattern: $NAME time.Duration`
     - OR use a tree-sitter kind matcher: `kind: field_declaration` with a `has: { kind: qualified_type, regex: '^time\.(Time|Duration)$' }` child
     - Either approach is acceptable as long as the bad case in the smoke (Step 4) matches and the good case (using `libtime.DateTime`) does not.
   - `ignores`: same as rule 2

4. There is NO Step 4 ast-grep smoke inside this prompt — the container may not yet have `ast-grep` on `$PATH` (claude-yolo image bump to v0.9.0 is mid-flight). YAML validity is verified mechanically by `make build-index` reading the index and the file existence/content checks below. Operator runs `ast-grep scan` post-merge to confirm the detectors fire correctly.

5. Run `make build-index` to refresh `rules/index.json`. It must grow from 1 entry to **4 entries** (pilot `go-context/cancel-check-in-loop` + 3 new `go-time/*` rules), with entries sorted by `id` and each entry's keys alphabetically sorted.

6. Verify each new index entry has:
   - `owner: "go-time-assistant"`
   - `doc_path: "docs/go-time-injection.md"`
   - `anchor == id` (the rule ID verbatim)
   - non-empty `applies_when` and `enforcement`
   - For rule 3: `enforcement: "judgment"` (literal string)

7. Run `make precommit` — must pass (link check + JSON validity unchanged).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT modify the existing pilot rule (`docs/go-context-cancellation-in-loops.md` rule block OR `rules/go/cancel-check-in-loop.yml`)
- Do NOT modify the schema doc (`docs/rule-block-schema.md`)
- Do NOT rewrite `docs/go-time-injection.md`'s existing prose — only APPEND the three `### RULE` blocks at the END of the file (after the Anti-Patterns section)
- Do NOT wire ast-grep into `make precommit` — that is Phase 1 territory and out of scope
- Do NOT attempt `ast-grep scan` from inside the container (binary likely absent until claude-yolo:v0.9.0 propagates to dark-factory's default); leave smoke to operator post-merge
- Use the same Bad/Good code snippets shown in `docs/go-time-injection.md` itself; do NOT invent new ones
- Generic examples only (User, Order, Product, Customer) — no Candle/Epic/Broker/SignalStore
- No personal paths (`~/Documents/`, `/Users/`) anywhere
- No `Co-Authored-By:` or attribution trailers (project convention)
</constraints>

<verification>
Run from repo root:
```bash
# Three new ### RULE blocks added to the doc
grep -c '^### RULE go-time/' docs/go-time-injection.md
# Must return: 3

# Two ast-grep YAMLs created
test -f rules/go/no-time-now-direct.yml && \
test -f rules/go/no-time-time-in-fields.yml && \
echo "yamls present: ok"

# YAMLs reference the correct ids on their first line
head -1 rules/go/no-time-now-direct.yml | grep -q '^id: go-time/no-time-now-direct' && echo "yaml1 id: ok"
head -1 rules/go/no-time-time-in-fields.yml | grep -q '^id: go-time/no-time-time-in-fields' && echo "yaml2 id: ok"

# rules/index.json now has 4 entries
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 4, f'expected 4 entries, got {len(d)}'
print(f'entries: {len(d)} ok')
"

# All four expected ids present and sorted
python3 -c "
import json
ids = [e['id'] for e in json.load(open('rules/index.json'))]
expected = ['go-context/cancel-check-in-loop', 'go-time/inject-getter-not-create', 'go-time/no-time-now-direct', 'go-time/no-time-time-in-fields']
assert ids == expected, f'ids mismatch:\n  got: {ids}\n  expected: {expected}'
print('ids sorted: ok')
"

# Three new entries are owned by go-time-assistant + point at the right doc
python3 -c "
import json
go_time = [e for e in json.load(open('rules/index.json')) if e['id'].startswith('go-time/')]
assert len(go_time) == 3, f'expected 3 go-time/* entries, got {len(go_time)}'
for e in go_time:
    assert e['owner'] == 'go-time-assistant', f\"owner mismatch for {e['id']}: {e['owner']}\"
    assert e['doc_path'] == 'docs/go-time-injection.md', f\"doc_path mismatch for {e['id']}\"
    assert e['anchor'] == e['id'], f\"anchor != id for {e['id']}: {e['anchor']}\"
    assert e['level'] in ('MUST','SHOULD','MAY'), f\"invalid level for {e['id']}: {e['level']}\"
    assert e['applies_when'], f\"empty applies_when for {e['id']}\"
    assert e['enforcement'], f\"empty enforcement for {e['id']}\"
judgment = [e for e in go_time if e['id'] == 'go-time/inject-getter-not-create'][0]
assert judgment['enforcement'] == 'judgment', f\"rule 3 enforcement must be literal 'judgment', got: {judgment['enforcement']}\"
print('go-time entries: ok')
"

# Determinism — running build-index again produces identical bytes
make build-index
git diff --exit-code rules/index.json && echo "deterministic: ok"

# make precommit clean
make precommit
```
</verification>
