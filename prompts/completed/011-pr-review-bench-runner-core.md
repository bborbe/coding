---
status: completed
spec: [002-pr-review-bench-runner]
summary: Created bench/run.py (configuration-identity core), bench/testsupport.py (test helpers), and bench/test_config.py (17 unit tests) implementing Desired Behaviors 1-3 and AC6/AC9/AC11 for the PR-review benchmark runner
execution_id: coding-bench-runner-exec-011-pr-review-bench-runner-core
dark-factory-version: v0.192.9
created: "2026-08-06T21:05:00Z"
queued: "2026-08-06T21:40:07Z"
started: "2026-08-06T21:40:18Z"
completed: "2026-08-06T21:45:55Z"
---

<summary>
- Creates the benchmark runner's entrypoint file and its configuration-identity core
- A run is identified by the *content* of the review rules and commands, not by a git commit — so an uncommitted rule edit can be benchmarked before it is committed
- The review mode (short / full / selector) is part of that identity, so two modes can never be conflated under one key
- The runner refuses to start if the isolated Claude configuration directory would load the plugin from somewhere other than the repo whose hash it is about to record
- The PR manifest is validated up front: a missing field or a suspicious owner/repo name aborts before anything runs
- `--model`, `--effort` and `--mode` are mandatory; a guessed default would mislabel every recorded row
- `--golden` is recognised and rejected rather than silently ignored, so nobody believes a run was scored when it was not
- A `--print-config-hash` helper lets an operator confirm which content a result file refers to
- PR processing itself is not shipped here — each PR reports a loud "not yet implemented" failure so the gap cannot be mistaken for success
- No new dependencies: Python 3 standard library only
</summary>

<objective>
Create `bench/run.py` with the benchmark runner's configuration-identity core: manifest loading and validation, content hashing of `rules/` + `commands/`, the plugin-resolution preflight that proves the recorded hash is the content that will actually run, and the full CLI surface with its exit-code contract. PR resolution and review invocation are stubbed with loud failures and land in later prompts.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python stdlib only, no personal paths, `make precommit` must stay green).
Read `specs/in-progress/002-pr-review-bench-runner.md` — this prompt implements Desired Behaviors 1, 2 and 3 and Acceptance Criteria AC6, AC9, AC11.
Read `bench/prs.json` — the frozen manifest this runner consumes. Note the exact field names on each entry: `id`, `owner`, `repo`, `number`, `language`, `merge_strategy`, `merge_sha`, `base_sha`, `head_sha`, `changed_files`, `additions`, `deletions`, `role`, `notes`; and the top-level fields `version`, `description`, `created`, `verified`, `prs`.
Read `bench/README.md` — current documentation (rewritten by prompt 4, not by this prompt).
Read `scripts/build-index.py` — the repo's existing stdlib-only Python script. Match its header-comment style (purpose, exit semantics, repo-root resolution from `__file__`, "no external dependencies") and its `sys.exit(main())` shape.
Read `scripts/check-coverage.sh` — the repo's precedent for a Python payload doing JSON + path work.

Plugin resolution — this is a real on-disk layout, verified in this container, not an assumption. A Claude configuration directory `$CFG` resolves the `coding` plugin as follows:

- `$CFG/plugins/known_marketplaces.json` is a JSON object keyed by marketplace name; the `coding` key holds an `installLocation` absolute path. Verified shape:
  ```json
  {
    "coding": {
      "source": { "source": "github", "repo": "bborbe/coding" },
      "installLocation": "/home/node/.claude/plugins/marketplaces/coding",
      "lastUpdated": "2026-07-13T15:30:51.004Z"
    }
  }
  ```
  Note `installLocation` may point outside `$CFG` entirely (other entries in the real file do), so it must be honoured verbatim when present.
- When that file is absent or has no usable `coding` entry, the conventional location is `$CFG/plugins/marketplaces/coding` — the same fallback `commands/pr-review.md` already uses:
  ```
  [ -x "$RUNNER" ] || RUNNER="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/scripts/ast-grep-runner.sh"
  ```
</context>

<requirements>

## 1. Create `bench/run.py`

Executable Python 3 script (`chmod +x`), `#!/usr/bin/env python3` shebang, followed by a header comment block (≥10 lines) in the style of `scripts/build-index.py` covering: purpose (benchmark runner for `/coding:pr-review`), exit semantics (0 = every PR produced a row; 1 = one or more PRs failed; 2 = usage, manifest or preflight error), how paths are resolved from `__file__`, and "Python 3 standard library only — no third-party dependencies".

Import only from the standard library. The permitted import set for this prompt is exactly: `argparse`, `hashlib`, `json`, `os`, `pathlib`, `re`, `sys`. Do not import anything else.

## 2. Module constants

```python
RUNNER_VERSION = "1"
REVIEW_TIMEOUT_SECONDS = 45 * 60
BENCH_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
VERIFY_CONFIG_DIR_NAME = ".claude-verify"
HASHED_SUBDIRS = ("rules", "commands")
VALID_MODES = ("short", "full", "selector")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PR_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*#[0-9]+$")
REQUIRED_ENTRY_FIELDS = (
    "id", "owner", "repo", "number",
    "merge_strategy", "merge_sha", "base_sha", "head_sha", "changed_files",
)
```

`REVIEW_TIMEOUT_SECONDS` is declared here and consumed in prompt 3. It is a fixed invariant — do NOT expose it as a CLI flag or an environment variable.

## 3. `class BenchError(Exception)`

A single exception type for every abort that maps to exit code 2 (manifest problems, preflight failures, lock contention). Its string form is printed to stderr by `main`. Define it directly under the constants.

## 4. `def content_hash(root: pathlib.Path) -> str`

Content-derived hash of the review configuration. Requirements:

- Collect every regular file under `root/"rules"` and `root/"commands"` (recursively, via `pathlib.Path.rglob("*")`, keeping only `p.is_file()`).
- Skip any path that has a component named `.git`.
- Sort the collected paths by their POSIX-style path relative to `root` (`p.relative_to(root).as_posix()`), so the digest is independent of filesystem iteration order.
- Feed a SHA-256 with, for each file in that order: the relative POSIX path bytes, a `b"\0"` separator, the decimal byte length of the file, another `b"\0"`, then the raw file bytes. Length-framing prevents two different file layouts from producing the same byte stream.
- Return `h.hexdigest()`.
- If neither `root/"rules"` nor `root/"commands"` exists, raise `BenchError` naming `root` and stating that it does not look like a coding-plugin checkout.
- Never consult git. The digest must be identical for two directories with byte-identical `rules/` + `commands/` content regardless of git history, uncommitted edits elsewhere in the tree, or the presence/absence of `.git`.

## 5. `def config_hash(rules_commands_hash, model, effort, mode, prs_version) -> str`

SHA-256 hex digest over the five values joined with a separator that cannot appear in any of them:

```python
payload = "\0".join([rules_commands_hash, model, effort, mode, prs_version])
return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

Mode is a first-class component. Changing only `mode` must produce a different digest.

## 6. `def load_manifest(path: pathlib.Path) -> dict`

- Read and `json.loads` the file. On `OSError` raise `BenchError(f"cannot read manifest {path}: {err}")`. On `json.JSONDecodeError` raise `BenchError(f"manifest {path} is not valid JSON: {err}")`.
- Require top-level `version` (non-empty string) and `prs` (non-empty list). Missing or wrong-typed → `BenchError` naming the field.
- For each entry, in list order:
  - Every field in `REQUIRED_ENTRY_FIELDS` must be present and non-empty (`0` counts as present but `changed_files` must be an `int`). On failure raise `BenchError(f"manifest entry {index} (id={entry.get('id')!r}): missing or empty required field {field!r}")` — the message must name both the entry id and the field.
  - `id` must match `PR_ID_RE`, `owner` and `repo` must match `NAME_RE`, `number` must be an `int` greater than 0. On failure raise `BenchError` naming the entry id and the offending value. This is the path-traversal guard: `owner`/`repo` flow into filesystem paths and `git` argument lists, so values like `../evil` or `a/b` must be rejected here and nowhere else.
  - `merge_sha`, `base_sha`, `head_sha` must each match `^[0-9a-f]{7,40}$`.
- Return the parsed dict unchanged (do not normalise or rewrite it — `bench/prs.json` is a frozen input).

## 7. `def safe_pr_key(pr_id: str) -> str`

Return `pr_id` with `#` replaced by `_`. Assume `pr_id` already passed `PR_ID_RE`, so no other character can appear. Used by prompts 2 and 3 for cache filenames.

## 8. Plugin-resolution preflight

```python
def verify_config_dir() -> pathlib.Path
```
Return `pathlib.Path(os.environ["HOME"]) / VERIFY_CONFIG_DIR_NAME`. If `HOME` is unset or empty, raise `BenchError` explaining that the isolated Claude config directory `~/.claude-verify` cannot be located. Read `HOME` from `os.environ` at call time (never cache it at import time) — this is what lets tests point the runner at a temporary config directory without adding a CLI knob.

```python
def resolve_plugin_path(config_dir: pathlib.Path) -> pathlib.Path
```
1. If `config_dir/"plugins"/"known_marketplaces.json"` is a file, parse it; on invalid JSON raise `BenchError` naming the file. If the parsed object has a `"coding"` key whose value is a dict with a non-empty `"installLocation"` string, return `pathlib.Path(that_value)`.
2. Otherwise return `config_dir / "plugins" / "marketplaces" / "coding"`.

```python
def check_plugin_resolution(coding_repo, config_dir, expected_hash) -> pathlib.Path
```
- `plugin_path = resolve_plugin_path(config_dir)`.
- If `plugin_path` is not a directory, set `actual = "<missing>"`. Otherwise `actual = content_hash(plugin_path)`, and if `content_hash` itself raises `BenchError` (no `rules/`/`commands/` under it) set `actual = "<no-rules-or-commands>"`.
- If `actual != expected_hash`, raise `BenchError` whose message begins with the literal `PLUGIN RESOLUTION MISMATCH` and additionally contains: `config_dir`, `plugin_path`, `actual`, `coding_repo`, `expected_hash`, and the sentence `refusing to record a configuration hash that did not run`. Both hashes must appear in the message.
- On success return `plugin_path`.

This check runs before the PR loop, so a mismatch invokes zero reviews.

## 9. CLI surface

```python
def build_parser() -> argparse.ArgumentParser
```

| Flag | Type | Default | Notes |
|---|---|---|---|
| `--coding-repo` | path | `REPO_ROOT` | repo whose `rules/` + `commands/` are hashed and measured |
| `--manifest` | path | `BENCH_DIR / "prs.json"` | PR manifest |
| `--out-dir` | path | `BENCH_DIR / "results"` | result ledger directory |
| `--model` | str | `None` | mandatory except with `--golden` / `--print-config-hash` |
| `--effort` | str | `None` | mandatory except with `--golden` / `--print-config-hash` |
| `--mode` | str, `choices=VALID_MODES` | `None` | mandatory except with `--golden` / `--print-config-hash`; passed verbatim as `/coding:pr-review`'s second positional argument |
| `--golden` | path | `None` | reserved — always rejected |
| `--print-config-hash` | flag | `False` | print the `rules/`+`commands/` hash for `--coding-repo` and exit 0 |

Do NOT declare `--model`/`--effort`/`--mode` as `required=True` — `--print-config-hash` and `--golden` must work without them. Enforce them after parsing (step 10).

Do NOT add any other flag. In particular: no `--timeout`, no `--cache-dir`, no `--config-dir`, no `--jobs`, no `--retry`. The spec lists these as explicit non-goals.

## 10. `def main(argv=None) -> int`

In this exact order:

1. `args = build_parser().parse_args(argv)`.
2. Wrap everything below in `try: ... except BenchError as err: print(str(err), file=sys.stderr); return 2`.
3. If `args.golden is not None`: print to stderr
   `--golden is reserved but scoring is not implemented in this runner. Precision/recall and golden-set matching are future work in a separate spec; the runner stops at normalized findings. Re-run without --golden.`
   and `return 2`.
4. If `args.print_config_hash`: `print(content_hash(args.coding_repo.resolve()))` and `return 0`.
5. Collect missing mandatory flags among `--model`, `--effort`, `--mode`. If any are missing, print to stderr `missing required argument(s): <comma-separated>. These are part of the configuration identity recorded in every result row and have no safe default.` and `return 2`.
6. Otherwise call and return `run_bench(...)` (step 11), binding the fixed invariants here and only here:
   - `cache_root=BENCH_DIR / ".cache"`
   - `config_dir=verify_config_dir()`
   - `results_dir=args.out_dir`
   - `coding_repo=args.coding_repo.resolve()`, `manifest_path=args.manifest`

End the file with:
```python
if __name__ == "__main__":
    sys.exit(main())
```

## 11. `def run_bench(*, coding_repo, manifest_path, results_dir, cache_root, model, effort, mode, config_dir) -> int`

Keyword-only. This signature is the seam that later prompts extend and that tests bind to temporary directories — the fixed invariants are bound in `main`, never here, so no operator-facing knob is created.

Body for this prompt:

1. `manifest = load_manifest(manifest_path)`.
2. `rc_hash = content_hash(coding_repo)`.
3. `check_plugin_resolution(coding_repo, config_dir, rc_hash)` — raises on mismatch, aborting before any PR is touched.
4. `cfg_hash = config_hash(rc_hash, model, effort, mode, manifest["version"])`.
5. Print one configuration banner line to stdout: `config <cfg_hash[:16]> rules+commands <rc_hash[:16]> model=<model> effort=<effort> mode=<mode> prs=<version>`.
6. For each entry in `manifest["prs"]`, call `process_pr(...)` (step 12) inside a `try/except BenchError` so a failing PR never aborts the remaining ones. Record a per-PR outcome of `ok`, `cache hit`, or `failed: <reason>`.
7. Print one summary line per PR to stdout in the form `<pr_id>: <outcome>`, then a final line `summary: <n_ok> ok, <n_cached> cache hit, <n_failed> failed`.
8. Return `0` if every PR produced `ok` or `cache hit`, otherwise `1`.

## 12. `def process_pr(...) -> tuple[str, str]` — fail-loud stub

Signature (keyword-only): `entry, coding_repo, results_dir, cache_root, model, effort, mode, config_dir, cfg_hash, rc_hash, prs_version`.

For this prompt the body is a single loud failure — PR resolution ships in prompt 2 and review invocation in prompt 3:

```python
return ("failed", "pr resolution not yet implemented (prompt 2 of spec 002)")
```

Do not return a success outcome, do not write a row, do not create a cache entry. A stub that looked like a valid result would hide the gap.

## 13. Create `bench/testsupport.py` — shared test helpers

Not a `test_*.py` file, so `unittest discover -p 'test_*.py'` will not collect it as a suite, but tests can `import testsupport`. Stdlib only (`json`, `os`, `pathlib`, `shutil`, `subprocess`, `stat` as needed).

```python
def make_coding_repo(root, *, rules=None, commands=None) -> pathlib.Path
```
Create `root/"rules"` and `root/"commands"` and write the given `{relative_path: text}` mappings (defaults: one file each, e.g. `rules/go/sample.yml` and `commands/sample.md`). Return `root`.

```python
def make_verify_config_dir(root, plugin_src, *, use_known_marketplaces=False) -> pathlib.Path
```
Create `root/".claude-verify"`. When `use_known_marketplaces` is False, `shutil.copytree(plugin_src, cfg/"plugins"/"marketplaces"/"coding")`. When True, create `cfg/"plugins"` and write `known_marketplaces.json` containing `{"coding": {"source": {"source": "github", "repo": "bborbe/coding"}, "installLocation": str(plugin_src)}}`. Return the `.claude-verify` path.

```python
def make_stub_bin(bin_dir, name, body) -> pathlib.Path
```
Write `bin_dir/name` with `#!/bin/sh\n` + `body`, `chmod 0o755`, return the path.

```python
def stub_claude(bin_dir, counter_file, report_text="") -> pathlib.Path
```
Install a stub `claude` that appends its full argument list as one line to `counter_file` and prints `report_text` to stdout, exiting 0. Body shape:
```sh
printf '%s\n' "$*" >> "<counter_file>"
cat <<'REPORT_EOF'
<report_text>
REPORT_EOF
```
Return the stub path.

```python
def with_path(bin_dir) -> dict
```
Return a copy of `os.environ` with `bin_dir` prepended to `PATH`. (Used by prompts 2 and 3.)

## 14. Create `bench/test_config.py`

`import unittest`, `import run`, `import testsupport` (flat imports — `unittest discover -s bench` puts `bench/` on `sys.path`, and there is deliberately no `bench/__init__.py`).

Tests, at minimum:

1. **`test_content_hash_ignores_git_history_and_dirty_tree`** (AC6) — build two temp directories with byte-identical `rules/` + `commands/` content. Give one a `.git` directory containing arbitrary bytes plus an untracked junk file at its root (outside `rules/`/`commands/`); leave the other bare. Assert the two hashes are equal. Then mutate exactly one byte inside one directory's `rules/` file, recompute, assert inequality, and `print()` both hashes so the inequality case is visible in test output.
2. **`test_content_hash_is_order_independent`** — build the same content twice with files created in reverse order; hashes must match.
3. **`test_config_hash_distinguishes_mode`** — same `rc_hash`/model/effort/version, `mode="selector"` vs `mode="full"` → different digests; identical inputs → identical digests.
4. **`test_load_manifest_rejects_missing_field`** — an entry missing `head_sha` raises `BenchError` whose message contains both the entry id and `head_sha`.
5. **`test_load_manifest_rejects_invalid_json`** — raises `BenchError` naming the path.
6. **`test_load_manifest_rejects_traversal_owner`** — `owner="../evil"` and separately `repo="a/b"` each raise `BenchError`.
7. **`test_load_manifest_accepts_real_fixture`** — `run.load_manifest(run.BENCH_DIR / "prs.json")` succeeds and returns `version == "dev-1"` with 5 entries. This is the boundary test: the shipped frozen manifest must pass the shipped validator.
8. **`test_plugin_resolution_mismatch_aborts_before_any_review`** (AC9) — build coding repo A and a `.claude-verify` whose copied plugin has different `rules/` content; install `stub_claude` with a counter file on `PATH`; call `run.run_bench(...)` with `config_dir` pointed at that `.claude-verify` and assert: `BenchError` is raised, `str(err)` starts with `PLUGIN RESOLUTION MISMATCH`, contains both hex hashes, and the counter file does not exist or has 0 lines.
9. **`test_plugin_resolution_honors_install_location`** — with `use_known_marketplaces=True` pointing at the same coding repo, `check_plugin_resolution` succeeds and `resolve_plugin_path` returns exactly `plugin_src`.
10. **`test_plugin_resolution_falls_back_to_marketplaces_dir`** — with no `known_marketplaces.json`, `resolve_plugin_path` returns `<cfg>/plugins/marketplaces/coding`.
11. **`test_golden_flag_exits_two`** (AC11) — run the real process: `subprocess.run([sys.executable, str(run.BENCH_DIR / "run.py"), "--golden", "bench/golden.json"], capture_output=True, text=True)`; assert `returncode == 2` and that stderr contains `scoring` and `future`.
12. **`test_print_config_hash_matches_content_hash`** — subprocess `[sys.executable, run.py, "--print-config-hash", "--coding-repo", <temp repo>]` exits 0 and its stdout stripped equals `run.content_hash(temp_repo)`.
13. **`test_missing_required_flag_exits_two`** — invoking with `--model x --effort y` but no `--mode` exits 2 with `--mode` named in stderr.
14. **`test_missing_model_and_effort_flags_exit_two`** — the same check for `--model` and for `--effort` individually, each naming the missing flag in stderr. The three flags are the configuration identity; a default silently applied to any one of them mislabels every row in the run, so all three are asserted, not just the one that happened to be written first.
15. **`test_known_marketplaces_invalid_json_raises`** — requirement 8.1 specifies `BenchError` naming the file when `known_marketplaces.json` is present but unparseable. Write a temp config dir containing that file with malformed JSON and assert the raise and the filename in the message. Untested, this path degrades to a silent fallback to the marketplaces dir, which is exactly the wrong plugin source and the failure DB3 exists to catch.
16. **`test_verify_config_dir_without_home_raises`** — with `HOME` removed from the environment, `verify_config_dir` raises `BenchError` naming the isolated config dir. Behaviour is specified in requirement 8; asserting it keeps the env read at call time rather than drifting to import time.

Every test that needs temp directories uses `tempfile.TemporaryDirectory` and cleans up. No test may require network, a real `claude` binary, or GitHub access.

## 14a. Do not modify

Do not touch `Makefile`, `bench/README.md`, `CHANGELOG.md`, `bench/prs.json`, or anything under `rules/`, `commands/`, `agents/`, `docs/` — those belong to prompt 4 or are frozen inputs. `make precommit`'s target list is unchanged by this prompt.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no `requirements.txt`, no `pyproject.toml`, no third-party imports
- One runner file at `bench/run.py`; test helpers in `bench/testsupport.py`; tests in `bench/test_*.py`. No `bench/__init__.py`
- No personal paths anywhere (`/Users/`, `~/Documents/`) in any file created or edited
- `bench/prs.json` is a frozen input — its schema, its five entries and its `dev-1` version are not modified
- No rule, agent, command or doc that participates in a review is edited — measuring the current configuration is the point
- Fixed invariants, not configurable: 45-minute review timeout, cache under `bench/.cache/`, results under `bench/results/`, isolated config dir `$HOME/.claude-verify`. Do NOT add flags or env vars for any of them
- Do NOT add a retry loop, a parallelism knob, or any scoring logic
- Do NOT commit — dark-factory handles git
- Existing checks must still pass: `make precommit` exits 0
</constraints>

<verification>
```
# Runner exists, is executable, stdlib-only
test -x bench/run.py && echo "executable: ok"
grep -nE '^(import |from )' bench/run.py

# No personal paths
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"

# Unit tests pass
python3 -m unittest discover -s bench -p 'test_*.py' -v

# Reserved --golden flag
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"

# Mandatory flags enforced
python3 bench/run.py --model m --effort e ; echo "missing-mode exit=$?  (expect 2)"

# Config hash is printable and stable
python3 bench/run.py --print-config-hash ; echo "print-hash exit=$?  (expect 0)"
A=$(python3 bench/run.py --print-config-hash)
B=$(python3 bench/run.py --print-config-hash)
[ "$A" = "$B" ] && echo "hash stable: ok"

# Frozen manifest still validates
python3 -c "
import sys, pathlib
sys.path.insert(0, 'bench')
import run
m = run.load_manifest(pathlib.Path('bench/prs.json'))
assert m['version'] == 'dev-1', m['version']
assert len(m['prs']) == 5, len(m['prs'])
print('manifest ok:', m['version'], len(m['prs']), 'entries')
"

# Repo checks unchanged
make precommit
```
</verification>
