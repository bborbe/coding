---
status: verifying
tags:
    - dark-factory
    - spec
approved: "2026-05-31T19:50:31Z"
generating: "2026-05-31T19:50:32Z"
prompted: "2026-05-31T19:56:25Z"
verifying: "2026-05-31T20:10:47Z"
branch: dark-factory/rule-base-interfaces-and-walker
---

## Summary

- Lock the contract for inline `### RULE` blocks in `docs/*.md` so future rules are written to one shape, not invented per author.
- Lock the shape of `rules/index.json` — the lookup table downstream agents read to find which rule lives in which doc and who owns it.
- Add a deterministic walker that builds the index from the docs, run by a manual Makefile target.
- Commit the generated index so any drift between docs and index shows up in PR diffs.
- Foundational only — dispatcher, coverage lint, per-agent slicing, bootstrap pass are separate specs that consume what this ships.

## Problem

The pilot rule (`go-context/cancel-check-in-loop`) is in place, but nothing downstream can use it without a contract. There is no documented schema for `### RULE` blocks, no documented shape for `rules/index.json`, and no tool that turns docs into an index. Every downstream piece (dispatcher refactor in `commands/pr-review.md`, coverage lint, bootstrap pass that adds rule blocks across docs) will guess at the schema and diverge. Locking the interfaces now — once, before the second rule lands — is what makes the rest of the pipeline cheap to build.

## Goal

After this work:

- A reader can open one doc and learn exactly what a `### RULE` block must contain, what its ID looks like, and how its anchor is derived.
- A reader can open one doc and learn exactly what each entry in `rules/index.json` contains and what each field means.
- Running `make build-index` against the current `docs/` produces a byte-stable `rules/index.json` containing the pilot rule with every field populated from the doc.
- The generated `rules/index.json` is committed, so any future PR that edits a rule block or adds/removes one shows the resulting index change in its diff.

## Non-goals

- Do NOT wire `build-index` into `make precommit` — that waits until a coverage lint exists.
- Do NOT add coverage / orphan-rule checking (`check-coverage.sh`).
- Do NOT refactor `commands/pr-review.md` to use the index.
- Do NOT write a citation validator that confirms agents reference real anchors.
- Do NOT materialize per-agent rule slices on disk.
- Do NOT install or wire `ast-grep` into precommit.
- Do NOT add a second rule block to any other doc — bootstrap pass is its own spec.
- Do NOT add knobs for output path, sort order, or pretty-printing — invariant; if a future consumer demands variation, that is a separate spec.
- Do NOT touch the 4-version alignment surface (`scripts/check-versions.sh`, manifests, CHANGELOG).

## Desired Behavior

1. A schema doc exists in `docs/` defining the `### RULE` block contract: required fields (`Owner`, `Applies when`, `Enforcement`), level token (`MUST` / `SHOULD` / `MAY`), ID format (`<lang>/<topic>/<slug>`), and the anchor derivation rule (GitHub-style heading slug). The block already shipped in `docs/go-context-cancellation-in-loops.md` is cited by path as the canonical example.
2. The same schema doc defines the `rules/index.json` shape: a top-level JSON array, each entry an object with exactly these keys — `id`, `level`, `doc_path`, `anchor`, `owner`, `applies_when`, `enforcement` — each documented with type and source (which line of the rule block it comes from).
3. The schema doc is linked from `README.md` (in the appropriate guide table) and listed in `llms.txt`, per the "Adding a new guide" checklist in `CLAUDE.md`.
4. A walker script at `scripts/build-index.py` (Python 3 stdlib only — no `pip` dependencies) reads every `*.md` file under `docs/`, finds every `### RULE` heading, parses the fields beneath it, and writes the index as JSON to stdout. The script follows the conventions of `scripts/check-versions.sh`: header comment block explaining purpose and exit semantics, repo-root computed from the script's own location, `set`-style strict failure on parse error.
5. The walker is deterministic — two runs over the same docs produce byte-identical output. Entries are sorted by `id`; JSON keys are sorted; indent is 2 spaces; trailing newline at end of file.
6. A `Makefile` target `build-index` invokes the walker and writes its output to `rules/index.json`. Manual-only; not added to `precommit` or `release-check`.
7. Running `make build-index` against the docs that exist at spec-completion time produces a `rules/index.json` containing exactly one entry, with `id = "go-context/cancel-check-in-loop"`, `level = "SHOULD"`, `doc_path = "docs/go-context-cancellation-in-loops.md"`, `anchor` matching the GitHub slug of the rule heading, `owner = "go-context-assistant"`, and `applies_when` / `enforcement` strings copied verbatim from the rule block.
8. The generated `rules/index.json` is committed to the repository.
9. A malformed rule block (missing one of `Owner` / `Applies when` / `Enforcement`, or a level token that is not `MUST` / `SHOULD` / `MAY`, or an ID not matching `<lang>/<topic>/<slug>`) causes the walker to exit non-zero with a message naming the offending doc and heading.

## Constraints

- Python stdlib only in `scripts/build-index.py`. No `pip install`, no `requirements.txt`, no third-party YAML/markdown parsers.
- No personal paths anywhere (no `~/Documents/`, no `/Users/`).
- Examples in the schema doc are generic only (no trading-domain identifiers like `Candle`, `Epic`, `Broker`).
- `scripts/check-versions.sh` and the four-version-alignment surface are not modified.
- The container-autonomous constraint holds — no `docker build`, no `kubectl`, no host paths invoked from any script touched here.
- The existing rule block in `docs/go-context-cancellation-in-loops.md` is NOT rewritten by this spec; the schema doc must describe what is already there, not require edits to it.
- The existing `rules/go/cancel-check-in-loop.yml` is NOT modified.
- `make precommit` exit behavior is unchanged.

## Failure Modes

| Trigger | Detection | Expected behavior | Recovery |
|---------|-----------|-------------------|----------|
| A `### RULE` heading is missing one of the three required fields (`Owner`, `Applies when`, `Enforcement`) | Walker exit code non-zero on `make build-index` | Walker exits non-zero; stderr names the doc path and the rule heading; no `rules/index.json` is written that run | Author adds the missing field to the doc, re-runs `make build-index` |
| Level token is not one of `MUST` / `SHOULD` / `MAY` | Walker exit code non-zero on `make build-index` | Walker exits non-zero; stderr names the doc path, the rule heading, and the offending token | Author fixes the heading, re-runs |
| ID does not match `<lang>/<topic>/<slug>` (e.g. spaces, capitals, missing slashes) | Walker exit code non-zero on `make build-index` | Walker exits non-zero; stderr names the doc path and the offending ID | Author fixes the ID, re-runs |
| Two `### RULE` blocks share the same ID across different docs | Walker exit code non-zero on `make build-index` | Walker exits non-zero; stderr names both doc paths and the duplicate ID | Author renames one ID, re-runs |
| `docs/` is missing or empty | Walker exit code non-zero on `make build-index` | Walker exits non-zero with a message naming `docs/` | Author restores `docs/`, re-runs |
| `python3` is not on PATH | `make build-index` exit code non-zero | Make target fails with the shell's standard "command not found" error | Author installs Python 3, re-runs |
| Walker output differs between runs over identical input | A second `make build-index` produces a `git diff` against the just-committed `rules/index.json` | This is a bug in the walker — must not happen | Author fixes the walker; this case is what determinism (sorted entries, sorted keys, fixed indent, trailing newline) prevents |

## Security / Abuse Cases

Not applicable in the threat-model sense — the walker reads a fixed in-repo directory, parses markdown, and writes a single JSON file. No network I/O, no user-supplied input, no shelling out to arbitrary commands. The only "input" is `docs/*.md` which lives in the same repo as the script and passes through normal code review.

## Acceptance Criteria

- [ ] A schema doc exists at a path under `docs/` (agent decides at impl time which filename) and contains a section defining the `### RULE` block contract (required fields, level tokens, ID format, anchor derivation rule) — evidence: file exists; `grep -nE '^(### |#### )?(Owner|Applies when|Enforcement|MUST|SHOULD|MAY|Anchor)' <doc>` returns ≥6 matches across the listed terms.
- [ ] The same schema doc contains a section defining the seven fields of each `rules/index.json` entry (`id`, `level`, `doc_path`, `anchor`, `owner`, `applies_when`, `enforcement`) — evidence: `grep -nE '\b(id|level|doc_path|anchor|owner|applies_when|enforcement)\b' <doc>` returns each of the seven names at least once.
- [ ] The schema doc cites `docs/go-context-cancellation-in-loops.md` by path as the canonical example — evidence: `grep -n 'go-context-cancellation-in-loops' <doc>` returns ≥1 match.
- [ ] The schema doc is linked from `README.md` — evidence: `grep -n '<doc-filename>' README.md` returns ≥1 match.
- [ ] The schema doc is listed in `llms.txt` — evidence: `grep -n '<doc-filename>' llms.txt` returns ≥1 match.
- [ ] `scripts/build-index.py` exists, is executable as `python3 scripts/build-index.py`, has a header comment block describing purpose and exit semantics in the style of `scripts/check-versions.sh` — evidence: file exists; `head -20 scripts/build-index.py` shows a leading comment block of ≥5 comment lines.
- [ ] The walker imports only from the Python standard library — evidence: `grep -nE '^(import|from) ' scripts/build-index.py` lists only stdlib module names (`json`, `os`, `re`, `pathlib`, `sys`, etc.).
- [ ] `Makefile` contains a `build-index` target that runs `python3 scripts/build-index.py > rules/index.json` — evidence: `grep -n 'build-index' Makefile` returns ≥2 matches (the `.PHONY:` line and the target line).
- [ ] `build-index` is NOT a prerequisite of `precommit` or `release-check` — evidence: `grep -n 'build-index' Makefile` shows no occurrence on the `precommit:` or `release-check:` recipe lines.
- [ ] Running `make build-index` against the docs at spec-completion time exits 0 — evidence: exit code 0.
- [ ] After that run, `rules/index.json` parses as JSON and is a top-level array of length 1 — evidence: `python3 -c "import json; d=json.load(open('rules/index.json')); assert isinstance(d, list) and len(d)==1"` exits 0.
- [ ] That one entry has `id == "go-context/cancel-check-in-loop"`, `level == "SHOULD"`, `doc_path == "docs/go-context-cancellation-in-loops.md"`, `owner == "go-context-assistant"`, and non-empty `anchor`, `applies_when`, `enforcement` strings — evidence: `python3 -c "import json; e=json.load(open('rules/index.json'))[0]; assert e['id']=='go-context/cancel-check-in-loop' and e['level']=='SHOULD' and e['doc_path']=='docs/go-context-cancellation-in-loops.md' and e['owner']=='go-context-assistant' and e['anchor'] and e['applies_when'] and e['enforcement']"` exits 0.
- [ ] Running `make build-index` twice in a row produces byte-identical `rules/index.json` — evidence: `make build-index && cp rules/index.json /tmp/a && make build-index && diff /tmp/a rules/index.json` produces no output and exits 0.
- [ ] The walker emits sorted-key JSON with 2-space indent and a trailing newline — evidence: `tail -c1 rules/index.json | xxd` shows `0a` (LF); the entry's keys appear in alphabetical order when read top-to-bottom.
- [ ] `rules/index.json` is committed to the repository — evidence: `git ls-files rules/index.json` returns the path.
- [ ] A rule block with a missing required field (e.g. delete the `Owner:` line in a copy) causes the walker to exit non-zero and print the offending doc path to stderr — evidence: walker exit code non-zero; stderr contains the doc path. (Verifier may demonstrate by feeding the walker a temporary doc tree under `/tmp` rather than mutating the real `docs/`.)
- [ ] An ID not matching `<lang>/<topic>/<slug>` causes the walker to exit non-zero and print the offending ID to stderr — evidence: walker exit code non-zero; stderr contains the bad ID.
- [ ] Two rule blocks sharing the same ID across different docs cause the walker to exit non-zero and print both doc paths to stderr — evidence: walker exit code non-zero; stderr contains both doc paths.
- [ ] `make precommit` continues to exit 0 — evidence: exit code 0.

No new scenario test required. The walker is a deterministic local script with no I/O beyond reading `docs/` and writing one JSON file; unit-style verification via the AC commands above is sufficient and the test-pyramid rule rejects an E2E test here.

## Verification

Run each from the repo root:

```
make precommit
make build-index
python3 -c "import json; d=json.load(open('rules/index.json')); assert isinstance(d, list) and len(d)==1; e=d[0]; assert e['id']=='go-context/cancel-check-in-loop' and e['level']=='SHOULD' and e['doc_path']=='docs/go-context-cancellation-in-loops.md' and e['owner']=='go-context-assistant' and e['anchor'] and e['applies_when'] and e['enforcement']; print('ok')"
make build-index && cp rules/index.json /tmp/index-a.json && make build-index && diff /tmp/index-a.json rules/index.json && echo "deterministic OK"
git ls-files rules/index.json
```

All commands exit 0; the python one-liner prints `ok`; the diff produces no output.

## Do-Nothing Option

If we skip this work, every downstream piece of the doc-driven pipeline (dispatcher, coverage lint, bootstrap pass, per-agent slicing) starts by inventing its own answer to "what shape is a rule block?" and "what shape is the index?". The schema diverges across features and the cost to consolidate later is paid in retrofits and broken citations. The pilot rule block in `docs/go-context-cancellation-in-loops.md` already exists; without this spec it remains a one-off whose conventions are only readable by inspection. The cheap moment to lock the contract is now, before the second rule lands.
