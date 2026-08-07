---
status: approved
spec: [002-pr-review-bench-runner]
created: "2026-08-06T22:29:56Z"
queued: "2026-08-06T22:39:41Z"
---

<summary>
- One command now runs the benchmark, and one command runs its tests
- The benchmark's own tests become part of the standard pre-commit gate, so every later change to the repo has to keep the measuring instrument working
- The benchmark documentation stops claiming the runner does not exist and describes how to actually run it
- The documented rule for reconstructing a squashed pull request's diff is corrected: it always comes from the manifest's recorded start and end commits, never from walking the merge commit's parents
- The old snippet only ever looked correct because the single squashed fixture pull request happens to end on its own merge commit — that coincidence is called out so nobody restores it
- The documentation records which knobs are deliberately fixed and not configurable, so a future reader does not add flags the design rules out
- A final sweep confirms no personal filesystem paths and no third-party dependencies were introduced anywhere in the benchmark
- Generated Python bytecode is kept out of version control now that the test suite runs on every pre-commit
- The changelog records the finished runner under the unreleased section
</summary>

<objective>
Package the finished benchmark runner: add `make bench` and `make bench-test`, wire the bench unit tests into `make precommit` so they gate every later change, rewrite `bench/README.md` to describe the shipped runner and to replace its superseded parent-derived squash snippet with the spec's authoritative `base_sha..head_sha` rule, and record the work in `CHANGELOG.md`. This is the last prompt of spec 002 and is deliberately last so the gate wired into `precommit` sees the finished tests.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, generic examples only).
Read `specs/in-progress/002-pr-review-bench-runner.md` — this prompt satisfies Acceptance Criteria AC1, AC12 and AC13. Two sections are load-bearing here:
- **Constraints** → *"This spec is the binding contract for diff-range mechanics, superseding `bench/README.md` where the two disagree"* and *"prompt 4 (packaging/docs) corrects the README snippet to match rather than the reverse"*. That is this prompt.
- **Desired Behavior 5** → the authoritative rule you are documenting: two or more parents means `<merge>^1..<merge>^2`; exactly one parent means the manifest's recorded `base_sha..head_sha`, derived from the manifest and never from parent traversal.

Read `Makefile` — five targets exist. `precommit` currently reads:

```make
.PHONY: precommit
precommit: check-links check-json check-index check-coverage check-acceptance
```

and the existing wrapper targets are one-liners of the shape `@bash scripts/<name>.sh` or `@python3 scripts/<name>.py`. Match that shape.

Read `scripts/check-coverage.sh` — the bash-wrapper precedent for a check target.
Read `scripts/build-index.py` — the stdlib-Python script precedent.

Read `bench/README.md` — the file you rewrite. It currently contains, and must stop containing:
- `Only `prs.json` exists — the runner, golden set, and scoring are not built yet.`
- a shell snippet whose squash line is `git diff <merge_sha>^1..<merge_sha>`
- a python snippet whose else-branch is `base, head = parents[0], merge_sha       # squash (or rebase)`

It also describes the configuration tuple as `(rules + commands state, model, effort level)`, which is now incomplete — review mode is part of the identity.

Read `bench/run.py` — the shipped runner you are documenting. Take the documented CLI surface from `build_parser` (`--coding-repo`, `--manifest`, `--out-dir`, `--model`, `--effort`, `--mode` with choices from `VALID_MODES`, `--golden`, `--print-config-hash`), the exit-code contract from the module header comment (0 = every PR produced a row, 1 = one or more PRs failed, 2 = usage / manifest / preflight failure), and the fixed invariants from the module constants (`REVIEW_TIMEOUT_SECONDS`, `VERIFY_CONFIG_DIR_NAME`). Do not restate anything the code does not do.

Read `bench/prs.json` — `node-skeleton#2` is the only `squash` entry and its `head_sha` equals its `merge_sha`; the other four are `merge-commit`. The five `changed_files` counts are 1 / 17 / 21 / 18 / 8 (`tts-mcp#20`, `github-pr-review-agent#11`, `quant#109`, `node-skeleton#2`, `python-skeleton#3`).

Read `docs/dod.md` — no personal paths anywhere, a `## Unreleased` CHANGELOG entry, and the 4-version alignment is not touched.

Read `.gitignore` — it already lists `/bench/results/` and `/bench/.cache/` but has no `__pycache__` entry.
</context>

<requirements>

## 1. Makefile — `bench` and `bench-test`

Add two targets in the existing style (`.PHONY` declaration immediately above each recipe, `@`-prefixed one-liner recipes):

```make
.PHONY: bench
bench:
	@python3 bench/run.py $(BENCH_ARGS)

.PHONY: bench-test
bench-test:
	@echo "bench-test: running bench unit tests..."
	@python3 -m unittest discover -s bench -p 'test_*.py' 2>&1
```

- `BENCH_ARGS` is the only variable and has no default. `--model`, `--effort` and `--mode` are mandatory precisely because a guessed default would mislabel every recorded row, so `make bench` with no `BENCH_ARGS` correctly fails with the runner's exit code 2. Do not add default values, and do not add variables for the cache directory, the results directory, the review timeout or the isolated config directory — the spec fixes all four as invariants.
- The `2>&1` on the unittest line is required: `unittest` writes its result summary (`OK` / `FAILED`) to stderr, and AC1 requires `make precommit`'s **stdout** to contain both `bench-test` and `OK`.
- `python3 -m unittest discover -s bench -p 'test_*.py'` is run from the repo root; discovery inserts `bench/` onto `sys.path`, which is what lets the test modules `import run` and `import testsupport`. Do not `cd` into `bench/` and do not add a `sys.path` shim.

## 2. Makefile — wire the gate into `precommit`

Append `bench-test` to the `precommit` prerequisite list, last:

```make
precommit: check-links check-json check-index check-coverage check-acceptance bench-test
```

Last position keeps its `OK` line near the end of the output and keeps the existing checks' ordering untouched. Do not add `bench` (the real benchmark spends tokens and needs a `claude` binary — it must never run in a pre-commit or in CI).

## 3. `.gitignore` — Python bytecode

Add `__pycache__/` so the newly-precommit-run test suite does not leave untracked bytecode in the working tree. It is invisible today only because of a machine-local global ignore file; a fresh clone or container has no such file. Keep the existing entries and their order; append the new line.

## 4. Rewrite `bench/README.md`

Keep the file's identity: the `# bench — code-review outcome benchmark` heading, the four-row test-pyramid table, the `Goal: [[PR Review Bench]]` wikilink, the `prs.json` description, and the `gh api repos/<owner>/<repo>/compare/<base_sha>...<head_sha> --jq '.files | length'` verification snippet with its five recorded counts. Everything below is what changes.

1. **Configuration tuple.** Update it to `(rules + commands content, model, effort level, review mode)`. Mode is not cosmetic — `short` / `full` / `selector` route through materially different code paths in `/coding:pr-review`, so a result row that did not distinguish mode would conflate two different instruments under one key.

2. **Current state.** Replace the sentence `Only `prs.json` exists — the runner, golden set, and scoring are not built yet.` with a description of what now exists: the runner drives the real `/coding:pr-review` command over the pinned manifest and writes one row per PR. State that the golden set and the scoring semantics belong to a later spec, and that `--golden` is therefore recognised and rejected with exit code 2 rather than silently ignored. **Do not reuse the phrase `runner, golden set, and scoring are not built yet` in any form** — AC13 greps for that exact string and requires zero matches.

3. **Running it.** A new section containing the literal `make bench`:

   ```bash
   make bench BENCH_ARGS="--model <model> --effort <effort> --mode <short|full|selector>"
   make bench-test
   ```

   Document that the three flags are mandatory because they are recorded identity, that results land in `bench/results/results.jsonl`, that `make bench-test` is also wired into `make precommit`, and that `python3 bench/run.py --print-config-hash` prints the content hash a result file refers to. Note the exit-code contract: 0 when every PR produced a row, 1 when one or more PRs failed, 2 for a usage, manifest or preflight failure.

4. **Diff-range rule — the correction.** Delete **both** stale artifacts, and delete each one's comment line together with its code line — a surviving `# squash: one parent — the squash commit IS the head` comment still reads as valid guidance even after the code beneath it is gone:
   - the shell snippet's `# squash: …` comment **and** its `git diff <merge_sha>^1..<merge_sha>` line
   - the whole python `parents` snippet, including `base, head = parents[0], merge_sha`

   AC13 greps for `parents\[0\], merge_sha` and requires zero matches — but note that grep alone does **not** prove the shell line is gone, so `<verification>` carries a second anchored grep for it. Deleting only the python snippet while leaving the shell line is a passing-but-wrong outcome: the README would still present the parent-derived form as usable, which the spec's Constraints section forbids. Replace them with the spec's rule, stated once and unambiguously:

   - two or more parents (merge commit) → `<merge_sha>^1..<merge_sha>^2`
   - exactly one parent (squash or rebase) → the manifest's recorded `base_sha..head_sha`

   The text must contain the literal `base_sha..head_sha` — AC13 greps for it and requires at least one match. Present this as the single rule, not as one option among alternatives; the README must not leave a reader able to choose the parent-derived form.

5. **Why the old snippet looked right.** Add a short paragraph: the deleted parent-derived form coincided with the correct answer on the only squash entry in the fixture (`node-skeleton#2`) purely because that PR's `head_sha` equals its `merge_sha`. A coincidence on one fixture entry is not a rule, and deriving head as "second parent, else the merge commit" yields `base == head` on any squash whose head is not the merge commit — an empty diff with no error, which scores as a clean review. Name `specs/in-progress/002-pr-review-bench-runner.md` as the binding contract for diff-range mechanics.

6. **Keep the empty-diff warning** already in the file and note that the runner now enforces it: a resolved range with zero changed files aborts that PR loudly with `EMPTY DIFF`, is never recorded as a zero-finding review, and produces no row and no cache entry.

7. **Fixed invariants.** A short list stating these are deliberately not configurable: the per-PR review timeout is 45 minutes; the cache lives under `bench/.cache/` and results under `bench/results/` (both gitignored, so no benchmark output is ever committed); the isolated Claude configuration directory is `$HOME/.claude-verify` with `DISABLE_AUTOUPDATER=1`. State that the runner aborts the whole run before the first review if that directory would resolve the `coding` plugin to content whose hash differs from `--coding-repo`'s — a hash claiming content that did not run is worse than no measurement.

8. **Safety invariant.** State that every `git` invocation the runner issues targets a path under `bench/.cache/repos/`; it never touches a clone the operator uses for real work. `/coding:pr-review` itself holds `git worktree`, `git fetch`, `git branch` and `rm -rf` permissions once invoked, so reusing a real clone could destructively mutate it.

9. **Result row.** List the recorded fields: `config_hash`, `rules_commands_hash`, `model`, `effort`, `mode`, `prs_version`, `pr_id`, `base_sha`, `head_sha`, `diff_range`, `changed_files`, `review_command`, `started_at`, `duration_seconds`, `findings`, `raw_output_ref`, `runner_version`. Note that repeating a configuration is free — completed (PR, configuration) pairs are served from cache and invoke nothing — and that the cache key includes the mode, so changing only `--mode` re-runs.

Write `<model>`, `<effort>`, `<owner>`, `<repo>` style placeholders. No personal paths (`/Users/`, `~/Documents/`) anywhere in the file.

## 5. CHANGELOG

Add bullets under the existing `## Unreleased` heading in `CHANGELOG.md`, matching the existing `bench: ...` style already there. At least one bullet must name the bench runner (AC13 greps `## Unreleased` for it). Cover: the `bench` and `bench-test` make targets, the precommit wiring, the `bench/README.md` rewrite including the corrected squash diff-range rule, and the `__pycache__` gitignore entry. Do not create a new version section, do not edit any released section, and do not touch the 4-version alignment.

## 6. Sweep — personal paths and stdlib-only (AC12)

Run these and fix anything they surface. Do not weaken a check to make it pass.

1. `grep -rn '/Users/\|~/Documents/' bench/` must return zero lines. `$HOME`-derived paths read from `os.environ` at call time are fine; a literal home path in a shipped file is not.
2. Every `import` / `from` line in `bench/run.py`, `bench/testsupport.py` and `bench/test_*.py` must name a Python 3 standard-library module (or the sibling modules `run` / `testsupport`). No third-party imports.
3. No `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg` or `Pipfile` exists anywhere in the repo — this plugin is distributed as a git clone and gains no packaging.

## 7. Do not modify

`bench/run.py`, `bench/testsupport.py`, `bench/test_*.py`, `bench/testdata/`, `bench/prs.json`, `rules/`, `commands/`, `agents/`, `docs/`, `scripts/`, `specs/`, `README.md`, `llms.txt`, `.claude-plugin/`. This prompt is packaging and documentation only. If `make precommit` fails because a bench test fails, report it rather than editing the test or the runner to make the gate pass.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no `requirements.txt`, no `pyproject.toml`, no `setup.py`. This repo is a Claude Code plugin distributed as a git clone; a packaged artifact is the wrong shape
- The `bench` target is a thin wrapper around `python3 bench/run.py`, consistent with the existing `check-*` targets that wrap `scripts/*.sh` and `scripts/*.py`
- The bench unit tests are wired into `precommit` so they gate every change; they must not require network, a real `claude` binary or GitHub access
- Never wire the real `bench` target into `precommit` or CI — it spends real tokens
- Fixed invariants, not configurable: 45-minute review timeout, cache under `bench/.cache/`, results under `bench/results/`, isolated config directory `$HOME/.claude-verify` with `DISABLE_AUTOUPDATER=1`. Do NOT add Makefile variables, flags or env vars for any of them
- `--model`, `--effort` and `--mode` stay mandatory — no defaults in the Makefile, because a guessed default would mislabel every recorded row
- **The spec supersedes `bench/README.md` where the two disagree.** The single-parent range is ALWAYS the manifest's recorded `base_sha..head_sha`, never derived by parent traversal. The README's parent-derived snippet is fully replaced, not presented as an alternative
- `bench/prs.json` is a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited — the measured configuration must stay exactly as it is
- No personal paths anywhere in shipped files (`/Users/`, `~/Documents/`) — `docs/dod.md` forbids them
- Generic examples only (User, Order, Product, Customer) — no trading-domain content
- `CHANGELOG.md` gains an entry under `## Unreleased`; released sections and the 4-version alignment are untouched
- Do NOT commit — dark-factory handles git
- Existing tests must still pass
</constraints>

<verification>
```
# AC1 — precommit is green and its output carries the bench gate
make precommit 2>&1 | tee /tmp/precommit.log ; echo "precommit exit=$?  (expect 0)"
grep -c 'bench-test' /tmp/precommit.log      # expect >= 1
grep -c '^OK' /tmp/precommit.log             # expect >= 1

# The bench-test target works standalone
make bench-test

# BENCH_ARGS really reaches the runner (no claude, no network needed)
make bench BENCH_ARGS="--print-config-hash"

# AC13 — documentation reflects the shipped runner
grep -n 'make bench' bench/README.md
grep -n 'runner, golden set, and scoring are not built yet' bench/README.md ; echo "stale-state grep exit=$?  (expect 1)"
grep -n 'parents\[0\], merge_sha' bench/README.md ; echo "parent-derived-python grep exit=$?  (expect 1)"
# The shell squash line must also be gone. Anchor on the absence of a ^2 suffix so this
# cannot false-positive against the CORRECT merge-commit line `git diff <merge_sha>^1..<merge_sha>^2`.
grep -nE 'git diff <merge_sha>\^1\.\.<merge_sha>$' bench/README.md ; echo "parent-derived-shell grep exit=$?  (expect 1)"
grep -n '# squash' bench/README.md ; echo "stale-squash-comment grep exit=$?  (expect 1)"
grep -n 'base_sha\.\.head_sha' bench/README.md
grep -n -A25 '## Unreleased' CHANGELOG.md

# AC12 — no personal paths, stdlib only, no packaging
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_*.py
ls requirements.txt pyproject.toml setup.py setup.cfg Pipfile 2>&1   # expect: No such file

# Bytecode stays out of the tree
grep -n '__pycache__' .gitignore

# Frozen manifest untouched
python3 -c "
import json
d = json.load(open('bench/prs.json'))
print(d['version'], len(d['prs']), 'entries')
"
```
</verification>
