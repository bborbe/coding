---
status: completed
spec: [002-pr-review-bench-runner]
summary: Extended bench/run.py with review invocation via /coding:pr-review in isolated CLAUDE_CONFIG_DIR, mode-aware raw-output cache, findings harvester, append-only ledger with atomic writes, single-instance BenchLock, plus 13 new unit tests in bench/test_review.py and bench/testdata/sample-report.md fixture
execution_id: coding-bench-runner-exec-013-spec-002-review-invocation-and-ledger
dark-factory-version: v0.192.9
created: "2026-08-06T22:29:56Z"
queued: "2026-08-06T22:39:41Z"
started: "2026-08-06T22:39:45Z"
completed: "2026-08-07T07:44:28Z"
---

<summary>
- The benchmark runner finally invokes the real review command instead of reporting "not implemented"
- Reviews run inside a dedicated, isolated Claude configuration directory with the autoupdater switched off, so nothing picks up a plugin update mid-run
- The raw review output is kept verbatim before anything parses it, so a later change to the parser can re-derive findings from an old run without spending tokens again
- Repeating the exact same configuration costs zero reviews — already-finished pull requests are served from cache and invoke nothing at all
- Changing only the review mode is treated as a different configuration, so two modes can never be silently conflated under one cached answer
- Review output is normalized into a flat list of findings, and a finding that names a rule but no file location is kept rather than dropped
- Results form an append-only ledger: one row per completed pull request, never rewritten, never deleted, written so a crash can never leave half a row behind
- A second benchmark run started while one is already in progress refuses to start instead of interleaving into the same ledger
- A review that fails or times out leaves no row and no cache entry, keeps its error output for diagnosis, and lets the remaining pull requests finish
</summary>

<objective>
Extend `bench/run.py` so a resolved pull request is actually reviewed: invoke `/coding:pr-review` through the `claude` executable in the isolated `$HOME/.claude-verify` configuration directory, cache the raw output under a mode-aware per-(PR, configuration) key, normalize the report into `{path, line, rule_id, body}` findings, and append exactly one row per completed pair to an append-only, atomically-written ledger guarded by a single-instance lock. This is the last piece that turns the runner from a resolver into a measuring instrument, and it is the only prompt in this spec that touches the review subprocess.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, `make precommit` must stay green).
Read `specs/in-progress/002-pr-review-bench-runner.md` — this prompt implements Desired Behaviors 7 and 8 and Acceptance Criteria AC4, AC5, AC10. Its **Constraints** section lists the required result-row fields verbatim; its **Failure Modes** table defines the timeout, crash, and two-runners rows you must satisfy.

Read `bench/run.py` — you are extending it. It already contains everything you build on; reuse it, do not restructure it:
- `BenchError` — the single exception type that maps to exit code 2 at the top level and to a per-PR `failed:` outcome inside the loop
- `RUNNER_VERSION`, `REVIEW_TIMEOUT_SECONDS` (45 × 60), `BENCH_DIR`, `REPO_ROOT`, `VALID_MODES`
- `content_hash(root)` and `config_hash(rules_commands_hash, model, effort, mode, prs_version)` — `config_hash` already mixes `mode` into the digest, which is the entire mechanism behind AC5
- `load_manifest(path)`, `safe_pr_key(pr_id)` (replaces `#` with `_`, filename-safe)
- `repos_root(cache_root)`, `assert_under(path, root)` — the containment helper that every destructive or path-taking operation must go through
- `git(args, *, repo_dir, cache_root, check=True, timeout=600)` — the single git chokepoint; it is `-C`-only and never passes `cwd=`
- `resolve_pr(cache_root, entry) -> PrCheckout` and the `PrCheckout` dataclass with fields `pr_id`, `repo_dir`, `worktree`, `base_branch`, `head_branch`, `diff_range`, `base_sha`, `head_sha`, `changed_files`, `parent_count`, `notes`
- `run_bench(*, coding_repo, manifest_path, results_dir, cache_root, model, effort, mode, config_dir) -> int` — keyword-only; already prints the config banner, loops over `manifest["prs"]`, catches `subprocess.TimeoutExpired` / `OSError` / `BenchError` per PR, prints `f"{pr_id}: {outcome}"` per PR and a `summary:` line, and counts outcome strings by the prefixes `"ok:"`, `"cache hit:"`, `"failed:"`
- `process_pr(*, entry, coding_repo, results_dir, cache_root, model, effort, mode, config_dir, cfg_hash, rc_hash, prs_version) -> tuple[str, str]` — currently calls `resolve_pr` and returns the `("failed", "review invocation not yet implemented (prompt 3 of spec 002)")` stub you are replacing
- `main(argv)` — builds the parser, rejects `--golden` with exit 2, requires `--model`/`--effort`/`--mode`, and calls `run_bench(... config_dir=verify_config_dir())`

Read `bench/testsupport.py` — you are extending it. It already has `make_coding_repo`, `make_verify_config_dir`, `make_stub_bin`, `stub_claude`, `with_path`, `init_git_repo`, `commit_file`, `make_merge_repo`, `make_squash_repo`, `make_empty_diff_repo`, `stub_git`, `make_manifest`.

Read `bench/test_config.py` and `bench/test_resolve.py` — the established test style: plain `unittest.TestCase` classes with docstrings naming the AC, `tempfile.TemporaryDirectory()`, `import run` / `import testsupport` (discovery inserts `bench/` onto `sys.path`). 29 tests currently pass via `python3 -m unittest discover -s bench -p 'test_*.py'`. Match that style; do not introduce a test framework.

Read `commands/pr-review.md` — the subprocess you are invoking. Its frontmatter `argument-hint` is `"<target-branch> [short|full|selector]"`, so the mode is the second positional word of the slash-command string. Step 0c diffs `origin/<TARGET_BRANCH>...HEAD`, which is why prompt 2 published `refs/remotes/origin/bench-base-<number>` — pass `PrCheckout.base_branch` as the target branch. Step 5 is the report you harvest: three mandatory headings `Must Fix (Critical)`, `Should Fix (Important)`, `Nice to Have (Optional)`, each holding bullet findings that cite a rule by ID, with the literal `None.` written when a section is empty. Selector mode appends a traceability section after those three.

Read `rules/index.json` — a JSON **list** of objects; each object's rule identifier is under the key `id` (not `rule_id`). 166 entries today. This file is the boundary that makes mechanical harvesting possible: `commands/pr-review.md` Step 4's citation validator already guarantees every emitted finding cites an ID from it.

Read `scripts/build-index.py` — the repo's stdlib-only Python precedent for header-comment style and `sys.exit(main())` shape.
</context>

<requirements>

## 1. Imports

Add `datetime`, `shlex`, `tempfile` and `time` to `bench/run.py`'s stdlib import list (`json`, `os`, `pathlib`, `subprocess` are already imported). No third-party imports, no new files outside `bench/`.

## 2. Cache and ledger path helpers

All of these are pure functions in `bench/run.py`:

```python
def reviews_root(cache_root: pathlib.Path) -> pathlib.Path      # cache_root / "reviews"
def failures_root(cache_root: pathlib.Path) -> pathlib.Path     # cache_root / "failures"
def cache_key(cfg_hash: str, pr_id: str) -> str                 # f"{cfg_hash}__{safe_pr_key(pr_id)}"
def cache_row_path(cache_root, cfg_hash, pr_id) -> pathlib.Path   # reviews_root / f"{key}.json"
def cache_raw_path(cache_root, cfg_hash, pr_id) -> pathlib.Path   # reviews_root / f"{key}.stdout.txt"
def failure_log_path(cache_root, cfg_hash, pr_id) -> pathlib.Path # failures_root / f"{key}.stderr.txt"
def ledger_path(results_dir: pathlib.Path) -> pathlib.Path        # results_dir / "results.jsonl"
def lock_path(results_dir: pathlib.Path) -> pathlib.Path          # results_dir / ".lock"
```

**The cache key is mode-aware because it is derived from `cfg_hash`, and `config_hash` already mixes `mode` into its digest.** Do not build the key from `rc_hash`, and do not add a separate mode component — deriving it from `cfg_hash` is what makes "same everything except `--mode`" land on a different file, which is the whole of AC5.

Failure logs live under `failures/`, deliberately **not** under `reviews/`: AC3 (shipped in prompt 2) asserts that an aborted PR creates no new file in `bench/.cache/reviews/`, while the spec's Failure Modes table requires a failed review's stderr to be preserved. Separate directories satisfy both with no conditional.

## 3. Single-instance lock

```python
class BenchLock:
    def __init__(self, results_dir: pathlib.Path) -> None
    def __enter__(self) -> "BenchLock"
    def __exit__(self, exc_type, exc, tb) -> None
```

- Acquire in `__enter__`, **not** in `__init__` — constructing a `BenchLock` must have no filesystem side effect, so a caller can build one and still choose not to enter it. Acquire with `os.open(lock_path(results_dir), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)`; write the current pid and an ISO-8601 UTC timestamp into it, then close the descriptor.
- `FileExistsError` → raise `BenchError` stating that another bench run is in progress, naming the lock file path verbatim, and telling the operator that a stale lock from a killed process is removed by deleting that file. The spec's Failure Modes table requires the message to name the removable file.
- `__exit__` unlinks the lock file, tolerating `FileNotFoundError`.
- The lock must be released on every exit path — acquire it with a `with` statement in `run_bench`, never with a bare try/finally reimplementation.

## 4. Atomic append-only ledger

```python
def atomic_write_bytes(path: pathlib.Path, data: bytes) -> None
def append_row(results_dir: pathlib.Path, row: dict) -> None
```

- `atomic_write_bytes` writes to a temporary file **in the same directory** as `path` (use `tempfile.NamedTemporaryFile(dir=path.parent, delete=False)`), flushes, `os.fsync`es the descriptor, closes it, then `os.replace`s it onto `path`. Same-directory is required so the replace is a rename within one filesystem and therefore atomic. On any exception, remove the temporary file before re-raising so no `.tmp` debris survives.
- `append_row` serializes the row with `json.dumps(row, sort_keys=True, ensure_ascii=False)`, appends `"\n"`, concatenates it after the ledger's existing bytes (empty when the ledger does not exist), and hands the whole result to `atomic_write_bytes`. Never open the ledger in `"a"` mode, never rewrite or delete an existing line. The ledger is small (one row per fixture PR), so read-modify-write is cheap and gives the spec's stated "atomic write-then-rename means no truncated row is ever observed" literally.

## 5. Review invocation

```python
def build_review_argv(*, model: str, effort: str, mode: str, base_branch: str) -> list[str]
```

Returns exactly:

```python
[
    "claude",
    "--print",
    "--model", model,
    "--effort", effort,
    "--permission-mode", "bypassPermissions",
    f"/coding:pr-review {base_branch} {mode}",
]
```

The mode is the slash command's second positional word, matching `commands/pr-review.md`'s `argument-hint`. `--permission-mode bypassPermissions` is required because the review runs `git` commands and spawns agents non-interactively; without it a one-shot run stalls or silently loses tool access. The argv is a list — no shell string, and no manifest value is interpolated into one argument.

```python
def review_env(config_dir: pathlib.Path) -> dict
```

Returns `dict(os.environ)` with `CLAUDE_CONFIG_DIR` set to `str(config_dir)` and `DISABLE_AUTOUPDATER` set to `"1"`. `CLAUDE_CONFIG_DIR` is the variable `commands/pr-review.md` itself reads (`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/...`), which is what makes the isolated directory actually take effect. Do not copy, filter, log or record any other environment variable, and never write environment values into a result row or cache file.

```python
def invoke_review(*, argv: list[str], worktree: pathlib.Path, cache_root: pathlib.Path,
                  config_dir: pathlib.Path) -> subprocess.CompletedProcess
```

1. `assert_under(worktree, repos_root(cache_root))` before anything else — the worktree becomes the subprocess's working directory and must be inside the runner's own cache.
2. `subprocess.run(argv, cwd=str(worktree), env=review_env(config_dir), capture_output=True, text=True, timeout=REVIEW_TIMEOUT_SECONDS)`.
3. Return the completed process unchanged; the caller decides what a non-zero exit means. Let `subprocess.TimeoutExpired` propagate.

**This is the only `cwd=` in `bench/run.py`.** The "`-C` only, never `cwd=`" rule belongs to the `git()` chokepoint and stays intact — `git()` is untouched by this prompt. Do not route the review through `git()`, and do not add a second `cwd=` anywhere.

`REVIEW_TIMEOUT_SECONDS` is a fixed invariant. Do not add a flag, an environment variable, or a parameter for it.

## 6. Harvesting a report into normalized findings

```python
def load_rule_ids(coding_repo: pathlib.Path) -> set
```

Reads `<coding_repo>/rules/index.json`, which is a JSON list of objects, and returns the set of every entry's `id` value. An unreadable or non-list file raises `BenchError` naming the path.

```python
def harvest(report_text: str, known_rule_ids) -> list
```

Returns a list of dicts, in document order, each with exactly the keys `path`, `line`, `rule_id`, `body`. Contract:

1. **Sections.** A finding section starts at a markdown heading (any level, `#` through `######`) whose text — after stripping `#`, `*`, and any trailing parenthesised severity like `(Critical)` — case-insensitively equals `Must Fix`, `Should Fix`, or `Nice to Have`. The section ends at the next markdown heading of any level, or end of text.
2. **Everything outside those three sections is ignored.** Preamble prose, the selector-mode traceability section, and any trailing notes contribute zero findings even when they mention rule IDs.
3. **Findings.** Inside a section, a line matching `^\s{0,3}[-*]\s+` starts a new finding. Following lines that are more deeply indented, or non-empty and not a new bullet and not a heading, are continuation lines of the current finding.
4. **Empty sections.** A section whose entire body strips to `None.` or `None` yields zero findings.
5. **`rule_id`.** Split the finding text on characters that cannot appear in a rule ID (whitespace, backticks, parentheses, brackets, commas, colons at token end) and take the first resulting token that is a member of `known_rule_ids`. No member → `None`. Membership in the real index — not a regex shape — is the discriminator, because a file path like `pkg/config/config.go` matches any plausible rule-ID regex.
6. **`path` / `line`.** From the first match of a file-with-line reference in the finding text: a token of `[A-Za-z0-9_./-]+` containing a `.` extension, immediately followed by `:` and one or more digits. `path` is the string, `line` is an `int`. No match → both `None`. A token that is a member of `known_rule_ids` is never treated as a path.
7. **`body`.** The finding text with the leading bullet marker removed, continuation lines joined by a single space, internal whitespace collapsed to single spaces, stripped.
8. **Nothing is dropped.** A finding citing a `rule_id` with no `path:line` is kept with `path` and `line` both `None` — this exact case is AC10. A finding citing no known rule ID at all is also kept, with `rule_id` `None`.

## 7. Result row assembly

```python
def build_row(*, checkout, cfg_hash, rc_hash, model, effort, mode, prs_version,
              review_command: str, started_at: str, duration_seconds: float,
              findings: list, raw_output_ref: str) -> dict
```

The spec's Constraints section makes these fields required — every one must be present and non-null (an empty `findings` list is a value, not null):

`config_hash`, `rules_commands_hash`, `model`, `effort`, `mode`, `prs_version`, `pr_id`, `base_sha`, `head_sha`, `diff_range`, `changed_files`, `review_command`, `started_at`, `duration_seconds`, `findings`, `raw_output_ref`, `runner_version`.

- `started_at` — `datetime.datetime.now(datetime.timezone.utc).isoformat()`, captured immediately before the subprocess starts, so it carries an explicit UTC offset (the spec's clock-skew failure mode requires an explicit offset).
- `duration_seconds` — measured with `time.monotonic()` around the subprocess, rounded to 3 decimals. Never derive it from wall-clock timestamps.
- `review_command` — `shlex.join(argv)`, so the mode literal appears in the row (AC5).
- `raw_output_ref` — the raw-stdout cache path relative to `REPO_ROOT` as a POSIX string when it is under `REPO_ROOT`, otherwise the absolute path (temp-dir test runs land in the second case).
- `runner_version` — `RUNNER_VERSION`.
- Additional fields are permitted: also record `parent_count` and `notes` from the `PrCheckout`.

## 8. Rewrite `process_pr`

Add `known_rule_ids` to the keyword-only parameter list; keep every existing parameter and its name. Sequence:

1. **Cache check first, before any git work.** If `cache_row_path(...)` exists and parses as JSON, print nothing extra and return `("cache hit", <detail>)` where `<detail>` names the cache key and the cached row's finding count. Do **not** call `resolve_pr`, do **not** invoke the subprocess, do **not** append a row. `run_bench` renders this as `"{pr_id}: cache hit: {detail}"`, so the literal `cache hit` appears exactly once per PR — the detail string must not contain that literal a second time. Checking the cache before resolution is what makes a repeat run fast and network-free (AC4, AC18). A cache file that fails to parse as JSON is treated as a miss and overwritten at the end of a successful run.
2. `checkout = resolve_pr(cache_root, entry)` — unchanged behaviour, may raise `BenchError`.
3. `argv = build_review_argv(model=..., effort=..., mode=..., base_branch=checkout.base_branch)`; capture `started_at` and the monotonic start.
4. `proc = invoke_review(argv=argv, worktree=checkout.worktree, cache_root=cache_root, config_dir=config_dir)`.
   - `subprocess.TimeoutExpired` — write whatever partial stderr the exception carries to `failure_log_path(...)` (creating `failures/` first; the exception's `stderr` may be `None` or `bytes`), then re-raise so `run_bench` records `failed: timeout`. No row, no cache entry.
   - Non-zero `returncode` — write `proc.stderr` to `failure_log_path(...)`, then raise `BenchError` whose message names the PR id and the literal `exit <code>` so the summary reads `failed: ... exit <code>`. No row, no cache entry.
5. **Write the raw stdout verbatim to `cache_raw_path(...)` before any parsing** (create `reviews/` first). Desired Behavior 7 requires the untouched bytes so a future harvester change can re-normalize old runs without re-spending tokens. Write it with `atomic_write_bytes`.
6. `findings = harvest(proc.stdout, known_rule_ids)`.
7. `row = build_row(...)`; `append_row(results_dir, row)`; **then** write the cache marker `cache_row_path(...)` with `atomic_write_bytes(json.dumps(row, sort_keys=True).encode("utf-8"))`. Ledger first, marker second: a crash between the two costs a duplicate row on re-run, which is visible and harmless in an append-only ledger, whereas the reverse order would serve a cache hit for a PR that has no row and silently lose it forever.
8. Return `("ok", <detail>)` where `<detail>` names the finding count and the duration.

## 9. Wire `run_bench`

Only these changes; leave the banner, the per-PR exception handling, the outcome counting and the summary printing exactly as they are:

1. After the plugin-resolution preflight and before the loop, `results_dir.mkdir(parents=True, exist_ok=True)`, then compute `known_rule_ids = load_rule_ids(coding_repo)`.
2. Wrap the whole per-PR loop in `with BenchLock(results_dir):`. A `BenchError` raised while acquiring the lock must propagate out of `run_bench` so `main`'s existing handler prints it to stderr and returns exit code 2 — do not catch it inside the loop's per-PR handler.
3. Pass `known_rule_ids=known_rule_ids` through to `process_pr`.

`main` needs no change: it already resolves `--coding-repo`, rejects `--golden` with exit 2, enforces the three mandatory flags, and passes `config_dir=verify_config_dir()`.

## 10. Extend `bench/testsupport.py`

1. **Fix `stub_claude`.** Its current body is `printf '%s\n' '$*' >> '<counter>'` — the single quotes make `sh` write the literal two characters `$*` instead of the invocation's arguments. Change it to double quotes (`"$*"`) so each counter line records the actual argument list. Line counting still works exactly as before, and the mode-cache-miss test can now assert the mode literal reached the subprocess.
2. Add `stub_claude_failing(bin_dir, counter_file, exit_code=3)` — appends its arguments to `counter_file` exactly like `stub_claude`, writes a short message to stderr, and exits with `exit_code`.
3. Add `seed_cached_repo(cache_root, owner, repo, builder)` — creates `<cache_root>/repos/<owner>/<repo>`, runs the given repo builder (`make_merge_repo` / `make_squash_repo` / `make_empty_diff_repo`) against it, and returns the builder's dict. This is the existing seeding idiom in `bench/test_resolve.py`, extracted so `bench/test_review.py` does not duplicate it; update `bench/test_resolve.py` only if the extraction leaves it broken.

## 11. Create `bench/testdata/sample-report.md`

A realistic `/coding:pr-review` Step 5 report, checked in as the fixture AC10 names. It must contain, in this order:

1. Two or three lines of preamble prose before the first heading, mentioning at least one rule ID — these must produce zero findings.
2. `#### Must Fix (Critical)` with at least two bullets: one citing a rule ID **and** a `` `path/to/file.ext:NN` `` reference, and one citing a rule ID with **no** file reference anywhere in the bullet.
3. `#### Should Fix (Important)` with one bullet whose text continues onto an indented second line.
4. `#### Nice to Have (Optional)` whose entire body is the literal `None.`.
5. `#### Selector Mode: Classify Traceability` with two or more bullets that mention rule IDs — these must produce zero findings.

Every rule ID written into the fixture must be an `id` that actually exists in `rules/index.json`. Do not invent IDs, and do not edit `rules/index.json`.

## 12. Create `bench/test_review.py`

`import json`, `import os`, `import pathlib`, `import tempfile`, `import unittest`, `from unittest import mock`, `import run`, `import testsupport`. Every test runs offline: no network, no real `claude` binary, no GitHub access.

`invoke_review` builds its environment from `os.environ` at call time, so a test that needs the stub `claude` on `PATH` must patch the process environment for the duration of the call:

```python
with mock.patch.dict(os.environ, {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}):
    rc = run.run_bench(...)
```

Tests:

1. **`test_second_run_is_cache_hit_and_invokes_zero_reviews`** (AC4) — seed two merge repos under `<cache_root>/repos/`, build a two-PR manifest, build a matching `.claude-verify` config dir so the preflight passes, install `stub_claude` with a counter file and a report body. Run `run_bench` twice with identical arguments, capturing stdout both times. Assert: both runs return 0; the counter file has exactly 2 lines after the first run and still exactly 2 after the second; the ledger has the same line count after both runs (2); the second run's stdout contains `cache hit` exactly twice (once per PR).
2. **`test_mode_change_is_cache_miss`** (AC5) — one-PR manifest, same harness. Run once with `mode="selector"`, then again with every argument identical except `mode="full"`. Assert: counter file has 1 line after the first run and 2 after the second; the ledger has 2 rows; the two rows' `mode` values differ; row 1's `review_command` contains `selector` and row 2's contains `full`; the counter file's second line contains `full` (proving the mode literal reached the subprocess argv, not just the row). Add an assertion message printing both `review_command` values.
3. **`test_cache_path_differs_when_only_mode_differs`** — unit-level guard on the key itself: compute two `config_hash` values differing only in `mode` and assert `cache_row_path` and `cache_raw_path` differ for both.
4. **`test_harvest_normalizes_sample_report`** (AC10) — read `pathlib.Path(run.__file__).parent / "testdata" / "sample-report.md"`, call `run.harvest(text, run.load_rule_ids(run.REPO_ROOT))`, and assert the returned list equals the full expected list of `{path, line, rule_id, body}` dicts. The expectation must include the finding whose `path` and `line` are both `None`, and must contain no entry originating from the preamble or the traceability section. Additionally assert every non-`None` `rule_id` in the result is a member of `run.load_rule_ids(run.REPO_ROOT)` — this is the boundary check against the real index.
5. **`test_harvest_keeps_finding_without_any_rule_id`** — a small inline report whose bullet cites no known ID yields one finding with `rule_id is None`, not zero findings.
6. **`test_harvest_ignores_empty_section`** — a section whose body is `None.` yields zero findings.
7. **`test_ledger_is_append_only_and_atomic`** — call `run.append_row` three times against a temp results dir. Assert the ledger has 3 lines, each parses as JSON, the first two lines are byte-identical to what they were after the second call, and no leftover temporary file remains in the directory.
8. **`test_second_runner_exits_without_touching_ledger`** — pre-create the lock file, then call `run_bench` with the full harness. Assert: return code 2 (the `BenchError` propagates to `main`'s handler — call `run.main([...])` for this test so the exit code contract is exercised end to end); stderr names the lock file path and states that another bench run is in progress; the ledger is unchanged; the stub-`claude` counter file has 0 lines.
9. **`test_row_carries_every_required_field`** — after one successful run, load the single ledger row and assert every field named in requirement 7 is present and not `None`.
10. **`test_raw_output_is_cached_verbatim`** — after one successful run, assert the file at `cache_raw_path(...)` contains the stub's report text exactly, and that the row's `raw_output_ref` resolves to that file.
11. **`test_failed_review_leaves_no_row_and_no_cache_entry`** — install `stub_claude_failing` with exit code 3. Assert: `run_bench` returns 1; the summary line for that PR contains `failed` and `exit 3`; the ledger is absent or has 0 lines; `<cache_root>/reviews/` contains no files; a stderr log exists under `<cache_root>/failures/`.
12. **`test_failed_pr_does_not_prevent_later_prs`** — a two-PR manifest where the first PR's `merge_sha` is unresolvable and the second reviews cleanly; assert the second PR still produces a row, both PRs appear in the summary, and `run_bench` returns 1.
13. **`test_corrupt_cache_row_is_treated_as_miss`** — requirement 1 states a cache file that fails to parse as JSON is treated as a miss and overwritten at the end of a successful run. Write a cache file containing malformed JSON, run, and assert the review subprocess *was* invoked (stub counter incremented), a row was appended, and the cache file now parses. Untested, a corrupt cache silently becomes either a crash or a permanent cache hit that can never be repaired without manual deletion.

## 13. CHANGELOG

Add bullets under the existing `## Unreleased` heading in `CHANGELOG.md` describing the review invocation, the mode-aware raw-output cache, the harvester, the append-only ledger and its single-instance lock, the new `bench/testdata/sample-report.md` fixture, and the new test file. Match the existing `bench: ...` bullet style already under that heading. Do not create a new version section and do not touch any released section.

## 14. Do not modify

`Makefile`, `bench/README.md`, `bench/prs.json`, `rules/`, `commands/`, `agents/`, `docs/`, `scripts/`, `specs/`. The `make bench` / `make bench-test` targets, the precommit wiring and the README rewrite are prompt 4 of this spec.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no `requirements.txt`, no `pyproject.toml`, no `setup.py`, no third-party imports. This repo is a Claude Code plugin distributed as a git clone; a packaged artifact is the wrong shape
- All new code stays in `bench/run.py`, `bench/testsupport.py`, `bench/test_review.py` and `bench/testdata/`
- Review mode is part of the configuration identity — the cache key derives from `config_hash`, which already mixes mode. Changing only `--mode` MUST be a cache miss
- A cache hit invokes zero subprocesses, does no git work, and appends no duplicate row
- Raw subprocess stdout is stored verbatim before any parsing
- Rows are append-only: never rewritten, never deleted; writes go through write-then-`os.replace`
- A second runner started against the same output directory exits without touching the ledger or the cache; the error names the lock file so a stale lock can be removed
- A PR that fails, times out, or exits non-zero produces no row and no cache entry; the remaining PRs still run; the process exits non-zero
- Do NOT add a retry loop around a failed review
- Fixed invariants, not configurable: 45-minute review timeout, cache under `bench/.cache/`, results under `bench/results/`, isolated config directory `$HOME/.claude-verify` with `DISABLE_AUTOUPDATER=1`. Do NOT add flags, env vars or parameters for any of them
- Every subprocess is invoked with an argument list; no manifest value is ever interpolated into a shell command
- `invoke_review` is the only `cwd=` in `bench/run.py`; the `git()` chokepoint stays `-C`-only and is not modified by this prompt
- `assert_under(worktree, repos_root(cache_root))` runs before the worktree is used as a working directory
- The runner records the command string it invoked but never copies environment variables, tokens or credential material into any artifact
- No personal paths anywhere in shipped files (`/Users/`, `~/Documents/`) — `docs/dod.md` forbids them. Reading `$HOME/.claude-verify` from `os.environ` at call time is fine
- `bench/prs.json` is a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited — the measured configuration must stay exactly as it is while the measuring device is built
- All new tests run offline: no network, no real `claude` binary, no GitHub access
- `CHANGELOG.md` gains an entry under `## Unreleased` (`docs/dod.md`)
- Do NOT commit — dark-factory handles git
- Existing tests must still pass (29 today)
</constraints>

<verification>
```
# Stdlib-only imports across every bench module
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_review.py

# No personal paths
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"

# Exactly one cwd= in run.py, inside invoke_review
grep -n 'cwd=' bench/run.py

# Expect exactly TWO subprocess.run calls in the file after this prompt: the pre-existing one
# inside git() (the confinement chokepoint, unchanged) and the new one inside invoke_review().
# Any third means git invocation escaped the chokepoint — that is a failure, not a style nit.
grep -n 'subprocess.run' bench/run.py

# The sample-report fixture exists
ls -l bench/testdata/

# Full unit-test run, including the new AC tests
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tee /tmp/bench-tests.log
grep -c 'cache_hit\|cache_miss' /tmp/bench-tests.log
grep -c 'harvest' /tmp/bench-tests.log
grep -c 'append_only' /tmp/bench-tests.log
grep -c 'second_runner' /tmp/bench-tests.log
tail -3 /tmp/bench-tests.log

# Every rule ID used by the fixture really exists in the index
python3 -c "
import sys, pathlib
sys.path.insert(0, 'bench')
import run
ids = run.load_rule_ids(run.REPO_ROOT)
text = (run.BENCH_DIR / 'testdata' / 'sample-report.md').read_text()
found = run.harvest(text, ids)
print('findings:', len(found))
for f in found:
    print(' ', f)
    assert f['rule_id'] is None or f['rule_id'] in ids, f
print('all cited rule ids exist in rules/index.json')
"

# Reserved and mandatory flags unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Repo checks still green
make precommit
```
</verification>
