---
status: approved
spec: [001-rule-base-interfaces-and-walker]
created: "2026-05-31T19:51:00Z"
queued: "2026-05-31T20:01:51Z"
branch: dark-factory/rule-base-interfaces-and-walker
---

<summary>
- `Makefile` gains a `build-index` target that runs `python3 scripts/build-index.py > rules/index.json`
- `build-index` is listed in `.PHONY` but is NOT a prerequisite of `precommit` or `release-check`
- `make build-index` is run, producing `rules/index.json` with exactly one entry for `go-context/cancel-check-in-loop`
- `rules/index.json` is committed to the repository
</summary>

<objective>
Wire the walker into the Makefile and produce the first committed `rules/index.json`. The index is manually generated (not part of precommit) so that future PRs show the index diff when rule blocks change.
</objective>

<context>
Read the current `Makefile` — it has `precommit`, `release-check`, `check-links`, `check-json`, `check-versions` targets. Add `build-index` following the same pattern.
Read `scripts/build-index.py` (the file created by prompt 2) — understand what it does so you can write the correct Makefile recipe.
Read `rules/go/cancel-check-in-loop.yml` — understand the existing ast-grep rule for context.
</context>

<requirements>
1. Add a new `.PHONY: build-index` declaration to the `Makefile`. **Follow the existing per-target pattern** — the Makefile already uses one `.PHONY:` line per target (see `.PHONY: precommit`, `.PHONY: release-check`, `.PHONY: check-links`, `.PHONY: check-json`, `.PHONY: check-versions` — each is its own line above its target). Add `.PHONY: build-index` immediately above the new `build-index:` target in the same style.
2. Add a `build-index` target with the recipe:
   ```
   .PHONY: build-index
   build-index:
   	@python3 scripts/build-index.py > rules/index.json
   	@echo "rules/index.json updated"
   ```
   - The target must be `.PHONY` so it always runs.
   - Do NOT add `build-index` as a prerequisite to `precommit` or `release-check`.
3. Verify that `build-index` is NOT on the `precommit:` or `release-check:` recipe lines by running:
   ```
   grep -n 'build-index' Makefile
   ```
   and confirming `precommit:` and `release-check:` lines do not contain it.
4. Run `make build-index` from the repo root. It must exit 0.
5. Verify the generated `rules/index.json`:
   - Parses as valid JSON (top-level array, length 1)
   - The one entry has `id == "go-context/cancel-check-in-loop"`, `level == "SHOULD"`, `doc_path == "docs/go-context-cancellation-in-loops.md"`, `owner == "go-context-assistant"`, and non-empty `anchor`, `applies_when`, `enforcement`
   - Keys are in alphabetical order within the entry
   - File ends with a trailing newline
6. Stage the generated `rules/index.json` with `git add rules/index.json` and leave the commit to dark-factory's `workflow: direct` post-prompt commit (it commits all dirty files on completion). Do NOT run `git commit` from inside the prompt — that conflicts with the daemon's commit logic. Do NOT add any `Co-Authored-By:` or attribution trailer (forbidden by project convention).
7. Run `make precommit` and confirm it still exits 0.

Note on execution order: prompts 1 and 2 must be executed before this prompt (prompt 3 depends on `docs/rule-block-schema.md` existing and `scripts/build-index.py` being executable). If running prompts individually, run 1, then 2, then 3.
</requirements>

<constraints>
- `build-index` is NOT a prerequisite of `precommit` or `release-check` — that waits for coverage lint
- Do NOT modify `scripts/check-versions.sh` or the four-version-alignment surface
- `make precommit` exit behavior is unchanged
- dark-factory handles git — do NOT create commits unless the `<verification>` commands for this prompt pass (the file must be valid before committing)
</constraints>

<verification>
Run the following from the repo root:
```
# build-index target exists and is .PHONY
grep -n 'build-index' Makefile
# Should show: .PHONY line has build-index, and build-index: target exists

# build-index is NOT a prerequisite of precommit or release-check
grep -nE '^precommit:|^release-check:' Makefile
# Neither should mention build-index

# make build-index runs clean
make build-index

# rules/index.json is valid JSON array of length 1
python3 -c "import json; d=json.load(open('rules/index.json')); assert isinstance(d, list) and len(d)==1; print('length 1: ok')"

# Entry has correct fields
python3 -c "
import json
e = json.load(open('rules/index.json'))[0]
assert e['id'] == 'go-context/cancel-check-in-loop', f\"id mismatch: {e['id']}\"
assert e['level'] == 'SHOULD', f\"level mismatch: {e['level']}\"
assert e['doc_path'] == 'docs/go-context-cancellation-in-loops.md', f\"doc_path mismatch: {e['doc_path']}\"
assert e['owner'] == 'go-context-assistant', f\"owner mismatch: {e['owner']}\"
for f in ['anchor', 'applies_when', 'enforcement']:
    assert e[f], f'empty field: {f}'
print('all fields correct: ok')
"

# Keys are sorted alphabetically in the entry
python3 -c "
import json
e = json.load(open('rules/index.json'))[0]
keys = list(e.keys())
assert keys == sorted(keys), f'keys not sorted: {keys}'
print('keys sorted: ok')
"

# Ends with trailing newline
python3 -c "
with open('rules/index.json', 'rb') as f:
    f.seek(-1, 2)
    last_byte = f.read(1)
assert last_byte == b'\\n', f'last byte is {last_byte!r}, expected newline'
print('trailing newline: ok')
"

# Committed to git
git ls-files rules/index.json

# make precommit still passes
make precommit
```
</verification>
