---
status: completed
summary: 'Migrated docs/go-security-linting.md from prose-only to rule-blocks-inline: appended four ### RULE blocks (3 mechanical + 1 judgment), created three ast-grep YAML detectors, ran make build-index to grow rules/index.json from 9 to 13 entries, and added ## Unreleased to CHANGELOG.md.'
container: coding-bootstrap-go-security-exec-008-bootstrap-rules-go-security-linting
dark-factory-version: v0.173.0
created: "2026-06-01T19:53:46Z"
queued: "2026-06-01T19:57:23Z"
started: "2026-06-01T19:57:29Z"
completed: "2026-06-01T19:59:55Z"
---

<summary>
- Third bootstrap prompt — migrates `docs/go-security-linting.md` from prose-only to rule-blocks-inline (Model A)
- Appends 4 `### RULE` blocks (3 MUST mechanical + 1 MUST judgment) corresponding to the doc's `## Rules` section
- Adds 3 `rules/go/*.yml` ast-grep YAMLs for the mechanical rules; the judgment rule carries `Enforcement: judgment`
- Runs `make build-index` so `rules/index.json` grows from 9 entries to 13
- Mirrors the proven `bootstrap-rules-go-time-injection.md` + `bootstrap-rules-go-error-wrapping.md` shape
- Scope note: doc lists 6 rules; this prompt extracts 4. Skipped: #3 ("fix on first attempt" — process rule, not enforceable) and #6 ("lock/PID files 0600" — covered by rule 1 which already mandates 0600 for ALL files)
</summary>

<objective>
Following the schema in `docs/rule-block-schema.md` and the ast-grep conventions in `docs/ast-grep-rule-writing-guide.md`, extract four rules from `docs/go-security-linting.md` as inline `### RULE` blocks, write ast-grep YAML detectors for the three mechanical rules, and refresh `rules/index.json` via the walker. Every block must conform to the schema (Owner, Applies when, Enforcement fields, ID format `<lang>/<topic>/<slug>`, anchor = id verbatim).
</objective>

<context>
Read `CLAUDE.md` for project conventions, including the doc-agent alignment table (`go-security-linting.md` → `go-security-specialist`).
Read `docs/rule-block-schema.md` for the rule-block contract — required fields, level tokens, ID format, anchor rule (`anchor == id` verbatim).
Read `docs/ast-grep-rule-writing-guide.md` for the YAML conventions — frontmatter shape, pattern strategies, pitfalls (especially the `main.go` + `**/main.go` dual-ignore + `**/mocks/**` defaults), smoke testing.
Read `docs/go-security-linting.md` — the doc to migrate. The `## Rules` section (around line 41) lists the rules; the `## File Permissions`, `## File Path from Variable`, and `## Subprocess from Variable` sections provide Bad/Good code snippets.
Read `docs/go-context-cancellation-in-loops.md` lines 160-192 — the canonical pilot `### RULE` block. The new blocks MUST match its formatting exactly: heading line `### RULE <id> (LEVEL)`, then bolded fields `**Owner**:`, `**Applies when**:`, `**Enforcement**:`, then `**Why**:`, then `#### Bad` / `#### Good` code blocks.
Read `rules/go/no-fmt-errorf.yml`, `rules/go/no-time-now-direct.yml` — canonical small ast-grep YAMLs. Match their shape.
Read `scripts/build-index.py` and run `python3 scripts/build-index.py` once to see the current `rules/index.json` shape (9 entries) before changes.
</context>

<requirements>
1. Append four `### RULE` blocks at the END of `docs/go-security-linting.md` (after the existing `## Checklist` section). Do NOT modify any prose above. The four blocks, in order:

**Rule 1 — MUST mechanical**
- Heading: `### RULE go-security/file-perms-too-permissive (MUST)`
- Owner: `go-security-specialist`
- Applies when: `os.WriteFile($PATH, $DATA, $PERM)` or `os.OpenFile($PATH, $FLAGS, $PERM)` calls in a `*.go` file outside `*_test.go` and `vendor/`, where `$PERM` is a literal octal that is NOT `0600` / `0o600`.
- Enforcement: `rules/go/file-perms-too-permissive.yml`
- Why: world-readable file permissions (e.g. `0644`) expose configuration data, lock files, and other artifacts to any process on the host. gosec G306 flags this; the convention is owner-only `0600` for ALL files unless there is a specific reason documented via `#nosec` with explanation.
- Bad/Good snippets: reuse the doc's `## File Permissions` section (`os.WriteFile(path, data, 0644)` → `os.WriteFile(path, data, 0600)`).

**Rule 2 — MUST mechanical**
- Heading: `### RULE go-security/dir-perms-too-permissive (MUST)`
- Owner: `go-security-specialist`
- Applies when: `os.MkdirAll($PATH, $PERM)` or `os.Mkdir($PATH, $PERM)` calls in a `*.go` file outside `*_test.go` and `vendor/`, where `$PERM` is a literal octal that is NOT `0750` / `0o750`.
- Enforcement: `rules/go/dir-perms-too-permissive.yml`
- Why: world-readable directories (e.g. `0755`) expose contents to any process on the host. The convention is `0750` (owner-rwx + group-rx, no world) for ALL agent-created directories.
- Bad/Good snippets: reuse the doc's `## File Permissions` `MkdirAll` example.

**Rule 3 — MUST mechanical**
- Heading: `### RULE go-security/nosec-requires-reason (MUST)`
- Owner: `go-security-specialist`
- Applies when: a `// #nosec <CODE>` comment in a `*.go` file outside `*_test.go` and `vendor/` appears WITHOUT a `-- <reason>` text component on the same line.
- Enforcement: `rules/go/nosec-requires-reason.yml`
- Why: bare `#nosec` suppresses a finding without explaining why the input is trusted. The next reviewer has no audit trail. Mandate `// #nosec G304 -- path from internal ListQueued(), not user input` style.
- Bad/Good snippets: reuse the doc's `## File Path from Variable` + `## Subprocess from Variable` good examples.

**Rule 4 — MUST judgment**
- Heading: `### RULE go-security/chmod-return-checked (MUST)`
- Owner: `go-security-specialist`
- Applies when: an `os.Chmod($PATH, $PERM)` call in a `*.go` file outside `*_test.go` and `vendor/` whose return value is discarded (no `if err := os.Chmod(...); err != nil` wrapper, no `_ = os.Chmod(...)` with an explanatory comment). Detecting "return value used in error check" requires reading the surrounding statement — pure ast-grep cannot reliably distinguish a checked `os.Chmod(...)` from an unchecked one without false positives.
- Enforcement: `judgment` (no ast-grep — return-value-check semantics require whole-statement reasoning).
- Why: silent `os.Chmod` failures leave file permissions in an unexpected state. The convention is either `if err := os.Chmod(...); err != nil { return ... }` or explicit `_ = os.Chmod(...)` with a comment explaining why the error is ignored.
- Bad/Good snippets: inline the following minimal pair (the doc doesn't have explicit Bad/Good code for this rule):

  Bad:
  ```go
  os.Chmod(path, 0600)
  ```

  Good:
  ```go
  if err := os.Chmod(path, 0600); err != nil {
      return errors.Wrapf(ctx, err, "chmod %s", path)
  }
  ```

Each block must follow the canonical pilot's exact formatting (`docs/go-context-cancellation-in-loops.md:160-192`).

2. Create `rules/go/file-perms-too-permissive.yml`:
   - `id: go-security/file-perms-too-permissive`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block — short summary, blank line, `See docs/go-security-linting.md (RULE go-security/file-perms-too-permissive).`
   - `rule`: use `any:` alternation across known-bad permission patterns. Common bad values: `0644`, `0o644`, `0666`, `0o666`, `0777`, `0o777`. Pattern guidance:
     ```yaml
     rule:
       any:
         - pattern: os.WriteFile($PATH, $DATA, 0644)
         - pattern: os.WriteFile($PATH, $DATA, 0o644)
         - pattern: os.WriteFile($PATH, $DATA, 0666)
         - pattern: os.WriteFile($PATH, $DATA, 0o666)
         - pattern: os.WriteFile($PATH, $DATA, 0777)
         - pattern: os.WriteFile($PATH, $DATA, 0o777)
         - pattern: os.OpenFile($PATH, $FLAGS, 0644)
         - pattern: os.OpenFile($PATH, $FLAGS, 0o644)
         - pattern: os.OpenFile($PATH, $FLAGS, 0666)
         - pattern: os.OpenFile($PATH, $FLAGS, 0o666)
     ```
     Alternative: detect any `os.WriteFile`/`os.OpenFile` call with constraints on the perm metavariable — only acceptable if the constraint correctly excludes `0600` / `0o600` and the pattern is verified against a synthetic file.
   - `ignores`: `main.go`, `**/main.go`, `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`

3. Create `rules/go/dir-perms-too-permissive.yml`:
   - `id: go-security/dir-perms-too-permissive`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: similar `any:` alternation across `0755`, `0o755`, `0777`, `0o777`, `0700` (too restrictive for some workflows but uncommon as a bad value — include if simple) for `os.MkdirAll` and `os.Mkdir`. Bad values to cover at minimum:
     ```yaml
     rule:
       any:
         - pattern: os.MkdirAll($PATH, 0755)
         - pattern: os.MkdirAll($PATH, 0o755)
         - pattern: os.MkdirAll($PATH, 0777)
         - pattern: os.MkdirAll($PATH, 0o777)
         - pattern: os.Mkdir($PATH, 0755)
         - pattern: os.Mkdir($PATH, 0o755)
         - pattern: os.Mkdir($PATH, 0777)
         - pattern: os.Mkdir($PATH, 0o777)
     ```
   - `ignores`: same as rule 1

4. Create `rules/go/nosec-requires-reason.yml`:
   - `id: go-security/nosec-requires-reason`
   - `language: go`
   - `severity: error`
   - `message`: 3-line block referencing the doc
   - `rule`: detecting a comment's content is harder than detecting a Go AST node. ast-grep's `kind: comment` may suffice with a regex constraint. Pattern guidance:
     ```yaml
     rule:
       kind: comment
       regex: '#nosec'
       not:
         regex: '#nosec.*--'
     ```
     If `kind: comment` + `regex` + `not.regex` doesn't work in ast-grep's Go grammar, fall back to a simpler pattern that matches the `#nosec` literal text without the `--`:
     ```yaml
     rule:
       pattern-regex: '//\s*#nosec\b(?!.*--)'
     ```
     Either acceptable as long as the smoke shows bare `#nosec G304` matches and `#nosec G304 -- reason` does not.
   - `ignores`: same as rule 1

5. Rule 4 (`chmod-return-checked`) has NO ast-grep YAML. Its `### RULE` block carries `Enforcement: judgment` (literal string, no path).

6. No ast-grep smoke inside this prompt — operator runs `scripts/scan.sh <target-repo>` post-merge to confirm the detectors fire correctly on real code.

7. Run `make build-index` to refresh `rules/index.json`. It must grow from 9 entries to **13 entries** (existing pilot + 3 go-time + 5 go-errors + 4 new go-security), with entries sorted by `id`.

8. Verify each new index entry has:
   - `owner: "go-security-specialist"`
   - `doc_path: "docs/go-security-linting.md"`
   - `anchor == id`
   - `level in ("MUST","SHOULD","MAY")`
   - non-empty `applies_when` and `enforcement`
   - For rule 4: `enforcement: "judgment"` (literal string)

9. Run `make precommit` — must pass.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT modify the existing rule blocks in `docs/go-context-cancellation-in-loops.md`, `docs/go-time-injection.md`, or `docs/go-error-wrapping-guide.md`, or their YAMLs
- Do NOT modify the schema doc or the ast-grep guide
- Do NOT rewrite `docs/go-security-linting.md`'s existing prose — only APPEND the four `### RULE` blocks at the END of the file (after `## Checklist`)
- Do NOT wire ast-grep into `make precommit`
- Do NOT attempt `ast-grep scan` from inside the container
- Use the same Bad/Good code snippets shown in `docs/go-security-linting.md` itself where they exist; for rule 4, synthesize minimal generic examples (User/Order/Product) per CLAUDE.md
- Generic examples only — no Candle/Epic/Broker/SignalStore
- No personal paths anywhere
- No `Co-Authored-By:` or attribution trailers
</constraints>

<verification>
Run from repo root:
```bash
# Four new ### RULE blocks added to the doc
grep -c '^### RULE go-security/' docs/go-security-linting.md
# Must return: 4

# Three ast-grep YAMLs created
test -f rules/go/file-perms-too-permissive.yml && \
test -f rules/go/dir-perms-too-permissive.yml && \
test -f rules/go/nosec-requires-reason.yml && \
echo "yamls present: ok"

# YAMLs reference the correct ids on their first line
head -1 rules/go/file-perms-too-permissive.yml | grep -q '^id: go-security/file-perms-too-permissive' && echo "yaml1 id: ok"
head -1 rules/go/dir-perms-too-permissive.yml | grep -q '^id: go-security/dir-perms-too-permissive' && echo "yaml2 id: ok"
head -1 rules/go/nosec-requires-reason.yml | grep -q '^id: go-security/nosec-requires-reason' && echo "yaml3 id: ok"

# All three YAMLs use severity: error
for f in rules/go/file-perms-too-permissive.yml rules/go/dir-perms-too-permissive.yml rules/go/nosec-requires-reason.yml; do
  head -5 "$f" | grep -q '^severity: error' || { echo "FAIL: $f missing severity: error"; exit 1; }
done
echo "severity: ok"

# No YAML for the judgment rule (rule 4)
test ! -f rules/go/chmod-return-checked.yml && echo "rule 4 has no YAML: ok"

# rules/index.json now has 13 entries
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 13, f'expected 13 entries, got {len(d)}'
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

# Four new entries owned by go-security-specialist + point at the right doc
python3 -c "
import json
go_sec = [e for e in json.load(open('rules/index.json')) if e['id'].startswith('go-security/')]
assert len(go_sec) == 4, f'expected 4 go-security/* entries, got {len(go_sec)}'
for e in go_sec:
    assert e['owner'] == 'go-security-specialist', f\"owner mismatch for {e['id']}: {e['owner']}\"
    assert e['doc_path'] == 'docs/go-security-linting.md', f\"doc_path mismatch for {e['id']}\"
    assert e['anchor'] == e['id'], f\"anchor != id for {e['id']}: {e['anchor']}\"
    assert e['level'] in ('MUST','SHOULD','MAY'), f\"invalid level for {e['id']}: {e['level']}\"
    assert e['applies_when'], f\"empty applies_when for {e['id']}\"
    assert e['enforcement'], f\"empty enforcement for {e['id']}\"
judgment_ids = {'go-security/chmod-return-checked'}
for e in go_sec:
    if e['id'] in judgment_ids:
        assert e['enforcement'] == 'judgment', f\"{e['id']} enforcement must be literal 'judgment', got: {e['enforcement']}\"
print('go-security entries: ok')
"

# Determinism — running build-index again produces identical bytes
make build-index
git diff --exit-code rules/index.json && echo "deterministic: ok"

# make precommit clean
make precommit
```
</verification>
