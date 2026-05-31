---
status: completed
spec: [001-rule-base-interfaces-and-walker]
summary: 'Created scripts/build-index.py — deterministic walker that extracts ### RULE blocks from docs/*.md and emits rules/index.json'
container: coding-rule-base-pilot-exec-003-spec-001-build-index-py-walker
dark-factory-version: v0.173.0
created: "2026-05-31T19:51:00Z"
queued: "2026-05-31T20:01:51Z"
started: "2026-05-31T20:04:59Z"
completed: "2026-05-31T20:09:41Z"
branch: dark-factory/rule-base-interfaces-and-walker
---

<summary>
- `scripts/build-index.py` reads all `docs/*.md` files
- Finds every `### RULE` heading and parses the three required fields beneath it
- Validates level token (MUST/SHOULD/MAY), ID format (`<lang>/<topic>/<slug>`), and required fields
- Detects duplicate IDs across docs
- Emits sorted-key JSON array to stdout with 2-space indent and trailing newline
- Exits non-zero with diagnostic message on any validation error
</summary>

<objective>
Write the deterministic walker that extracts every `### RULE` block from `docs/*.md` and produces a byte-stable `rules/index.json`. This is the mechanical core of the rule-base index pipeline.
</objective>

<context>
Read `scripts/check-versions.sh` — follow its header comment block style (purpose, exit semantics, repo-root resolution, `set` failure mode). The walker must follow the same conventions.
Read `docs/rule-block-schema.md` (the file created by prompt 1) — the walker's validation rules must match the schema exactly: required fields, level tokens, ID regex, anchor derivation.
Read `docs/go-context-cancellation-in-loops.md` lines 160–192 — this is the only `### RULE` block in the repo at spec-completion time; use it to verify the walker's output manually before running `make build-index`.
</context>

<requirements>
1. Create the file `scripts/build-index.py` as an executable Python 3 script.
2. Begin with a header comment block (≥8 lines) in the style of `scripts/check-versions.sh`. Include:
   - Purpose: what the script does
   - Exit semantics: 0 on success, non-zero on any parse error, validation error, or missing directory
   - How repo root is computed (from script's own location via `__file__`)
   - No external dependencies — Python stdlib only
3. Add `#!/usr/bin/env python3` shebang line after the comment block.
4. Robust failure: let unhandled exceptions propagate to Python's default handler (which exits non-zero with a traceback), OR wrap `main()` in `try / except Exception as e: print(f"build-index: {e}", file=sys.stderr); sys.exit(1)`. Either is acceptable. Do NOT invent attributes like `sys.exit_hook` — that does not exist in stdlib. The required behavior is: script exits non-zero on ANY parse/validation error or unexpected exception, with a diagnostic on stderr.
5. Compute the repo root as: `Path(__file__).resolve().parent.parent` (script is at `scripts/build-index.py`, parent.parent is repo root).
6. Walk all `*.md` files under `docs/` relative to repo root:
   - If `docs/` does not exist or contains no `.md` files, exit 1 with message: `docs/ directory not found or empty`.
   - Use `pathlib.Path` from stdlib only.
7. For each `.md` file, read its contents and find every `### RULE <id> (<level>)` heading using a regex.
   - The heading line must match the pattern: `^### RULE\s+([a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+)\s+\((MUST|SHOULD|MAY)\)` (i.e., three slash-separated components, all lowercase letters/digits/hyphens).
   - If the ID format does not match, exit non-zero and print: `Invalid rule ID in <doc_path>: <id>` to stderr.
   - If the level token is not one of `MUST`, `SHOULD`, `MAY`, exit non-zero and print: `Invalid level in <doc_path> rule <id>: <level>` to stderr.
8. After finding a `### RULE` heading, parse the lines immediately beneath it (until a line that is not a field line or until a heading of the same or higher level) to extract:
   - `Owner:` field (required) — extract the agent name from the line `**Owner**: <value>` or `Owner: <value>`
   - `Applies when:` field (required) — extract from `**Applies when**: <value>` or `Applies when: <value>`
   - `Enforcement:` field (required) — extract from `**Enforcement**: <value>` or `Enforcement: <value>`
   - If any required field is missing, exit non-zero and print: `Missing required field '<field>' in <doc_path> rule <id>` to stderr.
9. Compute the `anchor` field as **the rule ID verbatim** — same string as the `id` field, with slashes preserved. NOT a GitHub heading slug. No transformation: `anchor == id` for every entry. This is a machine-readable cross-reference key used by the dispatcher (`grep "^### RULE <anchor>" <doc_path>`); browser-anchor semantics are not needed.
   - Example: `### RULE go-context/cancel-check-in-loop (SHOULD)` → `anchor: "go-context/cancel-check-in-loop"`
10. Compute the `doc_path` field as the relative path from repo root to the doc (e.g. `docs/go-context-cancellation-in-loops.md`).
11. After processing all files, check for duplicate IDs:
    - If two entries share the same ID, exit non-zero and print both doc paths and the duplicate ID: `Duplicate rule ID '<id>' found in: <doc_path1>, <doc_path2>` to stderr.
12. Sort entries by `id` (alphabetical).
13. Sort each entry's keys alphabetically before serialization.
14. Write JSON to stdout with 2-space indent, keys sorted, and a trailing newline at end of file.
    - Use `json.dump` with `indent=2` and `sort_keys=True`; ensure the output ends with a newline.
15. Import only stdlib modules: `json`, `pathlib`, `re`, `sys`. No third-party imports.
16. Do NOT use `pip`, no `requirements.txt`, no external dependencies.

Verification at prompt-execution time:
- Run `python3 scripts/build-index.py` manually against the current `docs/`. It should exit 0 and emit one JSON entry for the `go-context/cancel-check-in-loop` rule.
- Confirm the output is valid JSON: `python3 scripts/build-index.py | python3 -m json.tool > /dev/null`.
- Confirm determinism: run twice, diff outputs, should be identical.
- Test the missing-field error: temporarily add a rule block without an `Owner:` line to a copy of a doc under `/tmp` and run the walker against `/tmp/that-copy/docs/`. It must exit non-zero with the doc path in stderr.
- Test the invalid-ID error: temporarily create a doc with `### RULE BadID (SHOULD)` (no slashes) under `/tmp` and run the walker. It must exit non-zero with `BadID` in stderr.
- Test the duplicate-ID error: temporarily create two docs under `/tmp` each with `### RULE go-context/cancel-check-in-loop (SHOULD)` and run the walker. It must exit non-zero naming both doc paths.
</requirements>

<constraints>
- Python stdlib only — no `pip install`, no `requirements.txt`, no third-party YAML/markdown parsers
- No personal paths anywhere (no `~/Documents/`, no `/Users/`)
- The existing `docs/go-context-cancellation-in-loops.md` is NOT modified by this prompt
- `make precommit` exit behavior is unchanged by this prompt
</constraints>

<verification>
Run the following from the repo root:
```
# Is executable
test -x scripts/build-index.py && echo "executable: ok"

# Only stdlib imports
grep -nE '^(import |from .* import )' scripts/build-index.py

# Runs clean against current docs
python3 scripts/build-index.py | python3 -m json.tool > /dev/null && echo "valid JSON: ok"

# Determinism
python3 scripts/build-index.py > /tmp/index-a.json
python3 scripts/build-index.py > /tmp/index-b.json
diff /tmp/index-a.json /tmp/index-b.json && echo "deterministic: ok"

# Entry count and fields
python3 scripts/build-index.py | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert isinstance(d, list) and len(d) == 1, f'expected 1 entry, got {len(d)}'
e = d[0]
for field in ['id','level','doc_path','anchor','owner','applies_when','enforcement']:
    assert field in e, f'missing field: {field}'
    assert e[field], f'empty field: {field}'
print('all fields present and non-empty: ok')
"

# make precommit still passes
make precommit
```
</verification>
