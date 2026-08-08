---
status: completed
spec: [004-bench-review-environment-control]
summary: Replaced bench runner plugin-resolution preflight to hash the install-record load path instead of marketplace path, with fail-closed aborts for no record, stale path, wrong scope, and out-of-tree path; rewrote test harness; added 10 new tests (62 total, up from 55)
execution_id: coding-bench-env-exec-018-spec-004-plugin-load-path-resolution
dark-factory-version: v0.192.9
created: "2026-08-08T10:05:00Z"
queued: "2026-08-08T08:19:41Z"
started: "2026-08-08T08:19:43Z"
completed: "2026-08-08T08:37:39Z"
---

<summary>
- The benchmark's plugin preflight now checks the directory Claude Code will really load rules from, instead of a directory nothing loads from
- The runner reads the isolated config directory's own install record to find that directory, and hashes exactly the version the record names
- If several versions of the plugin sit on disk, the recorded one is hashed — never the newest or the first one found
- A run aborts immediately, before any pull request is touched, when there is no install record, when the record cannot be read, when it points at a directory that is not there, when it points outside the config directory's own plugin tree, or when it only applies to a different working directory
- Each abort says what was found and where, so the operator fixes it without reading the runner's source
- The old marketplace directory is never hashed and never used as a rescue path — an ambiguous plugin state stops the run rather than producing a measurement that cannot be attributed
- A passing preflight now prints one line naming the directory it resolved, the version recorded for it, and the content hash, so the claim can be cross-checked against the filesystem
- The shared test scaffolding grows an install-record shape, and every test that builds an isolated config directory is updated to it
- Only the three tests whose whole subject was the old marketplace lookup go away; each is replaced by a load-path equivalent that asserts the same or more
- The test suite gets strictly bigger, and no surviving assertion is relaxed to make the new preflight fit
</summary>

<objective>
Replace the bench runner's plugin-resolution preflight so it hashes the plugin directory named by the isolated config directory's install record — the directory Claude Code actually loads from — instead of the marketplace directory it currently hashes. Any condition that would stop the plugin loading at all (no record, unreadable record, recorded path missing on disk, recorded path outside the config dir's own plugin tree, record applicable only to a different working directory) aborts the whole run by name before the first review starts, with no fallback to the marketplace path. A passing preflight prints one line naming the resolved load path, the recorded version, and the content hash.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, never commit — dark-factory handles git).

Read `specs/in-progress/004-bench-review-environment-control.md`. This prompt implements **Desired Behaviors 1 and 2** and **Acceptance Criteria AC2, AC3, AC4, AC5, AC6, AC7, AC13**. Load-bearing sections: the **Failure Modes** table (rows for load-path mismatch, no install record, stale install path, project-scoped record, unreadable record), **Security / Abuse Cases** ("File content becoming a read path", "Fail-closed, not fail-open"), and **Assumptions** (the record carries scope, install path, version, and a project path for project-scoped installs; the runner reads the recorded install path rather than reconstructing it from the naming convention).

Read `bench/run.py` in full. The parts you touch:

- `content_hash(root)` — hashes `root/rules` + `root/commands`; raises `BenchError` when neither subdirectory exists.
- `verify_config_dir()` — returns `pathlib.Path(HOME) / ".claude-verify"`. Unchanged by this prompt.
- `resolve_plugin_path(config_dir)` — the marketplace/`installLocation` resolver. **This function is deleted by this prompt.**
- `check_plugin_resolution(coding_repo, config_dir, expected_hash)` — the preflight. Rewritten by this prompt.
- `run_bench(...)` — calls `content_hash(coding_repo)` → `check_plugin_resolution(...)` → `config_hash(...)` → `results_dir.mkdir(...)` → prints the banner line `config <cfg[:16]> rules+commands <rc[:16]> model=… effort=… mode=… prs=…` → `with BenchLock(results_dir):` loop. `cache_root` is a parameter of `run_bench`.
- `repos_root(cache_root)` returns `cache_root / "repos"` — every prepared working copy the review runs in lives under it.
- `assert_under(path, root)` — strict containment check that raises `BenchError`. Use it as a naming/behaviour reference; this prompt adds a boolean helper rather than reusing it, because the preflight's abort messages must name the plugin tree, not the repo cache.
- `BenchError` — every abort that `main()` converts to exit code 2 by printing `str(err)` to stderr. That is why asserting on the `BenchError` message is equivalent to asserting on the process's stderr, and it is the convention the existing `test_plugin_resolution_mismatch_aborts_before_any_review` already uses.

Read `bench/testsupport.py`. `build_verify_config_dir(root, plugin_src, *, use_known_marketplaces=False)` currently either copies `plugin_src` to `<cfg>/plugins/marketplaces/coding` or writes `known_marketplaces.json`. **This function is rewritten by this prompt** and the `use_known_marketplaces` parameter is removed. It has 14 call sites:

```
bench/test_config.py:191, 227, 240, 330
bench/test_resolve.py:272
bench/test_review.py:63, 135, 224, 492, 570, 642, 733, 795, 1168
```

Read `bench/test_config.py` — the class `TestPluginResolution` holds the four preflight tests; `TestCliContract.test_missing_model_and_effort_flags_exit_two` also builds a config dir.

Read `bench/test_review.py` lines 23-79 (`run_one_pr_with_payload`) for the established one-PR harness shape: seed a merge repo under `<cache_root>/repos/<owner>/<repo>`, write a one-entry manifest, build a coding repo and a config dir, install the stub `claude`, call `run.run_bench(...)` inside `with mock.patch.dict(os.environ, env):`.

Read `docs/dod.md` — no personal paths, `## Unreleased` CHANGELOG entry.

**The real install-record shape.** This is the verbatim structure of a real Claude Code `plugins/installed_plugins.json` (read from a live config directory — do not invent a different shape):

```json
{
  "version": 2,
  "plugins": {
    "coding@coding": [
      {
        "scope": "project",
        "projectPath": "/some/project",
        "installPath": "/home/user/.claude/plugins/cache/coding/coding/0.2.0",
        "version": "0.2.0",
        "installedAt": "2026-04-01T10:07:06.974Z",
        "lastUpdated": "2026-06-24T17:12:19.553Z",
        "gitCommitSha": "7bb3ffb8ecd62013a35ec9487d3dfa779d287e3f"
      }
    ],
    "dark-factory@dark-factory": [
      {
        "scope": "user",
        "installPath": "/home/user/.claude/plugins/cache/dark-factory/dark-factory/0.192.3",
        "version": "0.192.3",
        "installedAt": "2026-07-13T15:17:01.273Z",
        "lastUpdated": "2026-07-13T15:17:01.273Z"
      }
    ]
  }
}
```

Key facts: the file is `<config_dir>/plugins/installed_plugins.json`; `plugins` maps `<plugin>@<marketplace>` to a **list** of records; `projectPath` is present only on `scope: project` records; `installPath` points under `<config_dir>/plugins/cache/<marketplace>/<plugin>/<version>/`.
</context>

<requirements>

## 1. Delete the marketplace resolver

Delete `resolve_plugin_path` from `bench/run.py` entirely. No code path in the runner may read `known_marketplaces.json`, construct `<config_dir>/plugins/marketplaces/...`, or use either as a fallback after any failure. The string `marketplaces` must not appear in any abort message this prompt produces — AC6 asserts its absence in stderr for three separate abort cases.

## 2. Constants in `bench/run.py`

Add next to the existing module constants:

```python
PLUGIN_NAME = "coding"
INSTALLED_PLUGINS_FILENAME = "installed_plugins.json"

# Preflight abort markers (frozen literals — tests and the README quote them)
PLUGIN_RESOLUTION_MISMATCH_MARKER = "PLUGIN RESOLUTION MISMATCH"
NO_INSTALL_RECORD_MARKER = "NO PLUGIN INSTALL RECORD"
UNREADABLE_INSTALL_RECORD_MARKER = "UNREADABLE PLUGIN INSTALL RECORD"
STALE_INSTALL_PATH_MARKER = "STALE PLUGIN INSTALL PATH"
OUT_OF_TREE_INSTALL_PATH_MARKER = "PLUGIN INSTALL PATH OUT OF TREE"
SCOPE_MISMATCH_MARKER = "PLUGIN INSTALL SCOPE MISMATCH"
```

The existing `PLUGIN RESOLUTION MISMATCH` message already uses that literal; keep it byte-identical and reference it through the new constant.

## 3. Path helpers

```python
def installed_plugins_path(config_dir: pathlib.Path) -> pathlib.Path:
    return config_dir / "plugins" / INSTALLED_PLUGINS_FILENAME


def plugin_cache_root(config_dir: pathlib.Path) -> pathlib.Path:
    return config_dir / "plugins" / "cache"


def path_is_under(path: pathlib.Path, root: pathlib.Path) -> bool:
    """True when path resolves strictly under root (never equal to it)."""
    resolved = pathlib.Path(path).resolve()
    root_resolved = pathlib.Path(root).resolve()
    return resolved != root_resolved and resolved.is_relative_to(root_resolved)
```

`pathlib.Path.resolve()` on a path that does not exist returns the normalised absolute path without raising (non-strict mode), which is what both the stale-path and the out-of-tree checks need.

## 4. Record dataclasses

```python
@dataclasses.dataclass
class PluginInstallRecord:
    plugin_key: str
    scope: str
    install_path: pathlib.Path
    version: str
    project_path: pathlib.Path | None


@dataclasses.dataclass
class PluginResolution:
    load_path: pathlib.Path
    version: str
    content_hash: str
```

`dataclasses` is already imported.

## 5. `load_install_records(config_dir)`

```python
def load_install_records(config_dir: pathlib.Path) -> list[PluginInstallRecord]:
    """Read every install record the config dir holds for the coding plugin.

    Records are returned in file order.  Raises BenchError naming the record file
    when the file is absent, unreadable, not JSON, structurally wrong, or holds no
    entry for the plugin.  There is no fallback: an unresolvable record aborts.
    """
```

Behaviour, in order:

1. `record_file = installed_plugins_path(config_dir)`. If it is not a file, raise
   `BenchError(f"{NO_INSTALL_RECORD_MARKER}: {record_file} does not exist; the isolated config directory {config_dir} holds no install record for plugin {PLUGIN_NAME!r}. Install the plugin into that config directory and re-run.")`
2. Read and `json.loads` it. On `OSError` or `json.JSONDecodeError` raise
   `BenchError(f"{UNREADABLE_INSTALL_RECORD_MARKER}: cannot read {record_file}: {err}")`.
3. If the parsed value is not a dict, or `data.get("plugins")` is not a dict, raise
   `BenchError(f"{UNREADABLE_INSTALL_RECORD_MARKER}: {record_file} has no 'plugins' object")`.
4. Collect every key of `data["plugins"]` that equals `PLUGIN_NAME` or starts with `PLUGIN_NAME + "@"`. For each such key, iterate its value; if the value is not a list, or an element is not a dict, raise `BenchError(f"{UNREADABLE_INSTALL_RECORD_MARKER}: {record_file}: entry {key!r} is not a list of records")`.
5. For each element build a `PluginInstallRecord` with `scope=str(elem.get("scope", ""))`, `version=str(elem.get("version", ""))`, `install_path=pathlib.Path(str(elem.get("installPath", "")))`, and `project_path=pathlib.Path(str(elem["projectPath"])) if elem.get("projectPath") else None`. An element whose `installPath` is missing or empty raises `BenchError(f"{UNREADABLE_INSTALL_RECORD_MARKER}: {record_file}: entry {key!r} has no 'installPath'")`.
6. If no record was collected, raise
   `BenchError(f"{NO_INSTALL_RECORD_MARKER}: {record_file} holds no install record for plugin {PLUGIN_NAME!r}; the isolated config directory {config_dir} will not load it. Install the plugin into that config directory and re-run.")`

## 6. `record_applies(record, review_root)` and `select_install_record(...)`

```python
def record_applies(record: PluginInstallRecord, review_root: pathlib.Path) -> bool:
    """True when this record is one Claude Code would load for the review's cwd.

    A user-scoped record always applies.  A project-scoped record applies only when
    review_root is the recorded project path or lives under it — every working copy
    the review runs in is created under review_root.  Any other scope value never
    applies; an unrecognised scope is treated as not-loading, which is the
    fail-closed reading the spec requires.
    """
```

Implementation: `scope == "user"` → `True`. `scope == "project"` → `record.project_path is not None and (review_root.resolve() == record.project_path.resolve() or review_root.resolve().is_relative_to(record.project_path.resolve()))`. Anything else → `False`.

```python
def select_install_record(records: list[PluginInstallRecord],
                          *, config_dir: pathlib.Path,
                          review_root: pathlib.Path) -> PluginInstallRecord:
    """Return the first record that applies to this run, or abort naming all of them."""
```

If no record applies, raise a `BenchError` beginning with `SCOPE_MISMATCH_MARKER` that names, for **every** record inspected, its `scope`, its `project_path`, its `version` and its `install_path`, plus `review_root` as the directory the review would have run in, plus the resolution: install the plugin at user scope in `config_dir`. Format each record as `[scope=<scope> projectPath=<project_path> version=<version> installPath=<install_path>]`. AC5 Case A asserts the record's project path **and** the review's working directory both appear in the message.

Return the first applicable record — file order. AC5 Case B (a project-scoped record that does not apply, followed by a valid user-scoped one) must proceed, so a non-applicable record is skipped and never aborts on its own.

## 7. `resolve_plugin_load_path(config_dir, review_root)`

```python
def resolve_plugin_load_path(config_dir: pathlib.Path,
                             review_root: pathlib.Path) -> PluginResolution:
    """Resolve and hash the directory the review will really load the plugin from."""
```

Sequence, fail-closed at every step:

1. `records = load_install_records(config_dir)`.
2. `record = select_install_record(records, config_dir=config_dir, review_root=review_root)`.
3. **Out-of-tree guard, before anything is read from the path.** If `not path_is_under(record.install_path, plugin_cache_root(config_dir))`, raise
   `BenchError(f"{OUT_OF_TREE_INSTALL_PATH_MARKER}: install path {record.install_path} recorded in {installed_plugins_path(config_dir)} is not under {plugin_cache_root(config_dir)}; refusing to read a plugin from outside the isolated config directory's own plugin tree")`.
   This is the "file content becoming a read path" control from the spec's Security section: the record is attacker-influenceable input that the runner turns into a directory it reads.
4. **Stale-path guard.** If `not record.install_path.is_dir()`, raise
   `BenchError(f"{STALE_INSTALL_PATH_MARKER}: {installed_plugins_path(config_dir)} records version {record.version} at {record.install_path}, which does not exist on disk; the plugin will not load and every slash command would be unknown. Reinstall the plugin and re-run.")`
   AC4 asserts the marker literal, the recorded path **and** the recorded version all appear.
5. Compute `digest = content_hash(record.install_path)`. Wrap the `BenchError` `content_hash` raises for a directory with neither `rules/` nor `commands/`:
   ```python
   try:
       digest = content_hash(record.install_path)
   except BenchError as err:
       raise BenchError(
           f"{STALE_INSTALL_PATH_MARKER}: {installed_plugins_path(config_dir)} records "
           f"version {record.version} at {record.install_path}, which is not a usable "
           f"plugin directory: {err}"
       )
   ```
6. Return `PluginResolution(load_path=record.install_path, version=record.version, content_hash=digest)`.

The recorded `installPath` is the only source of the load path. Do not glob `plugin_cache_root(config_dir)`, do not sort version directories, do not take the newest, the highest-numbered, or the first found. AC3 exists specifically to fail an implementation that globs.

## 8. `check_plugin_resolution(...)` — rewritten

```python
def check_plugin_resolution(coding_repo: pathlib.Path, config_dir: pathlib.Path,
                            expected_hash: str,
                            review_root: pathlib.Path) -> PluginResolution:
    """Verify the isolated config dir will load the coding plugin from coding_repo.

    Resolves the load path from the install record, hashes it, and raises
    BenchError (PLUGIN RESOLUTION MISMATCH) when that hash differs from
    expected_hash.  Runs before any PR is resolved and before any review subprocess
    starts.
    """
```

Implementation: `resolution = resolve_plugin_load_path(config_dir, review_root)`; if `resolution.content_hash != expected_hash`, raise

```python
raise BenchError(
    f"{PLUGIN_RESOLUTION_MISMATCH_MARKER}: config_dir={config_dir} "
    f"load_path={resolution.load_path} recorded_version={resolution.version} "
    f"actual_hash={resolution.content_hash} "
    f"coding_repo={coding_repo} expected_hash={expected_hash} "
    f"refusing to record a configuration hash that did not run"
)
```

Return `resolution` on success. The `<missing>` and `<no-rules-or-commands>` sentinel hashes the old implementation used are gone — those states now abort with their own markers at step 4/5 of `resolve_plugin_load_path`.

## 9. The resolution line

```python
def resolution_line(resolution: PluginResolution) -> str:
    """One-line statement of what the preflight resolved, for the operator to cross-check."""
    return (
        f"plugin load path: {resolution.load_path} "
        f"version={resolution.version} hash={resolution.content_hash}"
    )
```

Carry the **full** hash, not a prefix — the existing banner line prints `rules+commands <rc_hash[:16]>`, so a full-hash resolution line is the only stdout line that matches all three of load path, version and hash. AC7 counts matching lines and requires exactly 1.

## 10. Wire it into `run_bench`

`run_bench` already has `cache_root`. Replace the existing preflight call with:

```python
    resolution = check_plugin_resolution(
        coding_repo, config_dir, rc_hash, repos_root(cache_root)
    )
    print(resolution_line(resolution))
```

Print it **before** the existing `config … rules+commands …` banner, and exactly once per run. `repos_root(cache_root)` is the directory every prepared working copy is created under, and therefore the directory the review is invoked from for the purpose of scope evaluation.

Nothing else in `run_bench` changes: not the banner, not `BenchLock`, not the per-PR loop, not the outcome counting, not the summary, not the return-code logic.

## 11. Rewrite `build_verify_config_dir` in `bench/testsupport.py`

Replace the existing function (drop `use_known_marketplaces` entirely):

```python
def build_verify_config_dir(
    root: pathlib.Path,
    plugin_src: pathlib.Path,
    *,
    version: str = "0.35.2",
    scope: str = "user",
    project_path: pathlib.Path | None = None,
    install_path: pathlib.Path | None = None,
    extra_versions: dict | None = None,
    extra_records: list | None = None,
    marketplace_src: pathlib.Path | None = None,
    record_text: str | None = None,
    write_record: bool = True,
) -> pathlib.Path:
    """Create an isolated .claude-verify directory shaped like a real Claude Code config dir.

    Copies plugin_src to <cfg>/plugins/cache/coding/coding/<version> and writes
    <cfg>/plugins/installed_plugins.json with one record for "coding@coding".

    version         version string recorded and used as the cache directory name
    scope           "user" or "project"
    project_path    written as projectPath; required shape for scope="project"
    install_path    overrides the recorded installPath (used to record a path that is
                    stale, or one outside the config dir's plugin tree)
    extra_versions  {version: source_dir} copied to additional cache version dirs
    extra_records   raw record dicts appended after the primary record, in order
    marketplace_src copied to <cfg>/plugins/marketplaces/coding when given, so a test
                    can prove the marketplace path is not what gets hashed
    record_text     when given, written verbatim as installed_plugins.json instead of
                    the JSON structure (malformed-record cases)
    write_record    when False, installed_plugins.json is not written at all
    Returns the .claude-verify path.
    """
```

Implementation notes:

- `cfg = pathlib.Path(root) / ".claude-verify"`; create `cfg / "plugins" / "cache" / "coding" / "coding"`.
- Copy `plugin_src` to `<cache>/coding/coding/<version>` with `shutil.copytree`. Copy every `extra_versions` entry the same way.
- Primary record dict: `{"scope": scope, "installPath": str(install_path) if install_path is not None else str(default_dir), "version": version, "installedAt": "2026-08-08T00:00:00.000Z", "lastUpdated": "2026-08-08T00:00:00.000Z"}`, plus `"projectPath": str(project_path)` when `project_path is not None`.
- Records list is `[primary] + list(extra_records or [])`. File shape: `{"version": 2, "plugins": {"coding@coding": records}}`, written with `json.dumps`.
- `record_text is not None` → write that string verbatim and skip the JSON build. `write_record is False` → write no file at all (still create the cache directories).
- `marketplace_src is not None` → `shutil.copytree(marketplace_src, cfg / "plugins" / "marketplaces" / "coding")`.

## 12. Add a one-PR manifest helper to `bench/testsupport.py`

```python
def seed_one_pr_manifest(td: pathlib.Path, cache_root: pathlib.Path) -> pathlib.Path:
    """Seed one merge repo under cache_root and write a one-entry manifest.

    Creates <cache_root>/repos/testowner/repo_a via make_merge_repo and writes
    <td>/manifest.json with a single entry id "test#1", number 1, merge_strategy
    "merge-commit" and that repo's three SHAs.  Returns the manifest path.
    """
```

Do not change `run_one_pr_with_payload` in `bench/test_review.py`; it stays as it is apart from the `build_verify_config_dir` call-site update in requirement 13.

## 13. Update all 14 `build_verify_config_dir` call sites

Every call currently passing `use_known_marketplaces=True` drops that argument: `testsupport.build_verify_config_dir(td / "cfg", plugin_src)`. The one positional call (`bench/test_config.py:191`) is already in the new form and needs no edit beyond whatever the surrounding test requires.

Update payloads and call sites only. Do not delete a test, do not remove an assertion, do not relax an assertion, do not change an expected count, do not add a skip.

## 14. Remove exactly three tests from `bench/test_config.py`

Delete only these three, whose entire subject is marketplace-path resolution:

| Deleted test | Replaced by |
|---|---|
| `test_plugin_resolution_honors_install_location` | `test_recorded_install_path_is_the_load_path` (requirement 15.1) |
| `test_plugin_resolution_falls_back_to_marketplaces_dir` | `test_missing_install_record_aborts_without_marketplace_fallback` (requirement 15.7) |
| `test_known_marketplaces_invalid_json_raises` | `test_malformed_install_record_aborts_without_marketplace_fallback` (requirement 15.8) |

`test_plugin_resolution_mismatch_aborts_before_any_review` stays. Update it to the new harness: build `repo_a` and `repo_b` with different content, build the config dir from `repo_b`, keep every existing assertion (`msg.startswith("PLUGIN RESOLUTION MISMATCH")`, `actual_hash=` present, `expected_hash=` present, counter file empty), and add an assertion that the message names the resolved load path. No other test may be deleted or renamed — AC13 permits at most three deletions, all with `marketplace` or `install_location` in the name.

## 15. New tests in `bench/test_config.py`

Add `import contextlib`, `import io`, `import json`, `import shutil` and `from unittest import mock` as needed. Put the new tests in a class `TestPluginLoadPathResolution(unittest.TestCase)`.

Every test that must prove "no review was invoked" installs `testsupport.stub_claude(bin_dir, counter, testsupport.CLEAN_REVIEW_REPORT)` and asserts the counter file is absent or has 0 lines. Every test that must prove "the run proceeded" asserts the counter file has exactly 1 line for the one-PR manifest built by `testsupport.seed_one_pr_manifest`. Aborts are asserted on the `BenchError` message via `self.assertRaises(run.BenchError)` — `run.main()` prints exactly that string to stderr, so the message content is the criterion the ACs describe as stderr content. Every test runs offline: no network, no real `claude`, no GitHub access.

1. **`test_recorded_install_path_is_the_load_path`** (AC2 Case A) — a config dir whose **marketplace** copy is byte-identical to `--coding-repo` while the recorded load path holds one mutated byte. Build `repo_good` and `repo_mutated` (same file set, one byte different in one rules file); `cfg = testsupport.build_verify_config_dir(td / "cfg", repo_mutated, marketplace_src=repo_good)`; run with `coding_repo=repo_good`. Assert: `BenchError` whose message starts with `run.PLUGIN_RESOLUTION_MISMATCH_MARKER`, contains `str(cfg / "plugins" / "cache" / "coding" / "coding" / "0.35.2")`, contains `actual_hash=` and `expected_hash=`; counter file has 0 lines; the results file gained 0 lines.

2. **`test_marketplace_path_mismatch_does_not_block_the_run`** (AC2 Case B) — the reverse: `build_verify_config_dir(td / "cfg", repo_good, marketplace_src=repo_mutated)`, run with `coding_repo=repo_good`. Assert: `run_bench` returns `0`; counter file has exactly 1 line. Without this case, hashing both paths and requiring both to match would pass Case A while breaking every legitimate host.

3. **`test_recorded_version_is_hashed_not_the_newest_on_disk`** (AC3) — `build_verify_config_dir(td / "cfg", repo_low, version="0.16.0", extra_versions={"9.99.0": repo_high})`, where `repo_low` and `repo_high` hold different content. Two runs, separate results dirs and separate cache roots:
   - `coding_repo=repo_low` → returns `0`, counter has 1 line.
   - `coding_repo=repo_high` → `BenchError` starting with the mismatch marker whose message contains the string `0.16.0`.

   This is the test an implementation that globs the cache directory and takes the maximum version fails.

4. **`test_stale_install_path_aborts_before_any_review`** (AC4) — `build_verify_config_dir(..., version="0.16.0", install_path=<cfg>/plugins/cache/coding/coding/0.16.0-missing)` where that directory is never created. Assert: `BenchError` containing `run.STALE_INSTALL_PATH_MARKER`, the recorded path string, and `0.16.0`; counter file 0 lines; results file gained 0 lines.

5. **`test_project_scoped_record_for_another_directory_aborts`** (AC5 Case A) — the only record is `scope="project", project_path=td / "elsewhere"`, while the review runs under `run.repos_root(cache_root)`. Assert: `BenchError` containing `run.SCOPE_MISMATCH_MARKER`, `str(td / "elsewhere")`, and `str(run.repos_root(cache_root))`; counter file 0 lines; results file gained 0 lines.

6. **`test_user_scoped_record_alongside_a_project_scoped_one_is_used`** (AC5 Case B) — the same file carries the non-applicable project-scoped record **first** and a valid user-scoped record after it (`extra_records=[{"scope": "user", "installPath": str(<cache dir>), "version": "0.35.2"}]`). Assert: `run_bench` returns `0`; counter file has exactly 1 line. Without this case, aborting whenever a project-scoped record appears would pass Case A.

7. **`test_missing_install_record_aborts_without_marketplace_fallback`** (AC6 case 1) — `build_verify_config_dir(..., write_record=False, marketplace_src=repo_good)` with `coding_repo=repo_good`, so a marketplace fallback would have made the run pass. Assert: `BenchError` containing `run.NO_INSTALL_RECORD_MARKER` and `str(run.installed_plugins_path(cfg))`; the message does **not** contain the substring `marketplaces`; counter file 0 lines.

8. **`test_malformed_install_record_aborts_without_marketplace_fallback`** (AC6 case 2) — `record_text="{ this is not json"`, `marketplace_src=repo_good`, `coding_repo=repo_good`. Assert: `BenchError` containing `run.UNREADABLE_INSTALL_RECORD_MARKER` and the record file path; the message does **not** contain `marketplaces`; counter file 0 lines.

9. **`test_out_of_tree_install_path_is_refused`** (AC6 case 3) — `install_path=td / "outside-plugin-tree"` (create that directory and populate it with `testsupport.build_coding_repo`, so the only reason to refuse is its location), `marketplace_src=repo_good`, `coding_repo` matching the outside directory's content. Assert: `BenchError` containing `run.OUT_OF_TREE_INSTALL_PATH_MARKER`, the outside path, and `str(run.plugin_cache_root(cfg))`; the message does **not** contain `marketplaces`; counter file 0 lines. This is the control that stops a tampered record redirecting the preflight at an arbitrary host directory.

10. **`test_passing_preflight_prints_one_resolution_line`** (AC7) — a successful one-PR run captured with `contextlib.redirect_stdout(io.StringIO())`. Compute `expected_path = str(cfg / "plugins" / "cache" / "coding" / "coding" / "0.35.2")`, `expected_hash = run.content_hash(plugin_src)`. Assert: `run_bench` returns `0`; exactly one captured stdout line contains **all three** of `expected_path`, the version string `0.35.2`, and `expected_hash`. Build the count as `sum(1 for ln in captured.splitlines() if expected_path in ln and "0.35.2" in ln and expected_hash in ln)` and assert it equals `1`, with the full captured stdout in the assertion message.

## 16. Do not modify

`bench/prs.json`, `bench/testdata/`, `bench/README.md`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`, `CHANGELOG.md`.

Do not change `content_hash`, `config_hash`, `load_manifest`, `verify_config_dir`, `assert_under`, the git helpers, `resolve_pr`, `prepare_worktree`, `invoke_review`, `review_env`, the harvest functions, the non-review gate, `build_row`, `append_row`, or the CLI parser. `bench/README.md` and the CHANGELOG entry are prompt 4 of this spec; ref pruning is prompt 2; failure artifacts are prompt 3.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no third-party imports, no new top-level files outside `bench/`
- Changes land only in `bench/run.py`, `bench/testsupport.py`, `bench/test_config.py`, `bench/test_resolve.py` and `bench/test_review.py` (the last two only for the mechanical `build_verify_config_dir` call-site update)
- The existing tests keep passing and their assertions are not weakened. Updating call sites to the new harness is expected and correct; deleting a test, removing an assertion, or relaxing an assertion to accommodate the new preflight is not. The only removals permitted are the three named in requirement 14, each replaced by a load-path equivalent asserting the same or stronger behaviour. The suite's test count after this prompt is strictly greater than 55
- Fail-closed, not fail-open: every ambiguity in plugin resolution aborts the whole run before any PR is resolved and before any review subprocess starts. A false abort costs one operator fix and a re-run; a false pass writes a hash that did not run into an append-only ledger
- The marketplace / `installLocation` path is never hashed and never used as a fallback. No abort message may contain the substring `marketplaces`
- The recorded `installPath` is validated to lie under `<config_dir>/plugins/cache/` **before** anything is read or hashed from it — the record is file content the runner turns into a filesystem path it reads
- The version hashed is the one the record names — never the newest, the highest-numbered, or the first one found. No globbing of the plugin cache directory
- Do NOT add a field to the result row (no plugin version, no load path). The content hash already pins what ran
- Do NOT make any of this configurable: no flag, no environment variable, no config field for the config directory, the record filename, or the plugin name
- Frozen invariants: the isolated config directory `$HOME/.claude-verify`; the 45-minute review timeout; the cache, results and failure-artifact locations; the three required section names; the `--golden` exit-2 rejection
- Do NOT make `review_env()` supply an authentication token. Any value of `ANTHROPIC_AUTH_TOKEN` switches Claude Code into API-key mode and bypasses the OAuth path for every operator
- Do NOT add environment scrubbing or an inherited-variable allowlist — the review subprocess inherits exactly what it inherits today
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`
- Subprocesses are invoked with argument lists, never shell strings; no record value is interpolated into a shell command
- No credential material is read, logged, or written; no abort message quotes an environment variable value
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file including test data (`docs/dod.md`)
- All new tests run offline: no network, no real `claude` binary, no GitHub access
- Do NOT re-harvest, migrate or re-validate anything already under `bench/.cache/` or `bench/results/`
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# New preflight surface exists; the marketplace resolver is gone
grep -n 'def load_install_records\|def select_install_record\|def record_applies\|def resolve_plugin_load_path\|def check_plugin_resolution\|def resolution_line\|def installed_plugins_path\|def plugin_cache_root\|def path_is_under' bench/run.py
grep -n 'resolve_plugin_path\|known_marketplaces\|installLocation' bench/run.py ; echo "marketplace-resolver grep exit=$?  (expect 1)"

# All abort markers are defined and used
grep -n 'PLUGIN_RESOLUTION_MISMATCH_MARKER\|NO_INSTALL_RECORD_MARKER\|UNREADABLE_INSTALL_RECORD_MARKER\|STALE_INSTALL_PATH_MARKER\|OUT_OF_TREE_INSTALL_PATH_MARKER\|SCOPE_MISMATCH_MARKER' bench/run.py

# The preflight still runs before the loop, and prints one resolution line
grep -n 'check_plugin_resolution\|resolution_line\|BenchLock' bench/run.py

# No call site still passes the removed parameter
grep -rn 'use_known_marketplaces' bench/ ; echo "removed-param grep exit=$?  (expect 1)"

# Full suite, verbose
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
python3 -m unittest discover -s bench -p 'test_*.py' 2>&1 | grep -E '^Ran |^OK|^FAILED'

# New tests present by name
grep -n 'def test_recorded_install_path_is_the_load_path\|def test_marketplace_path_mismatch_does_not_block_the_run\|def test_recorded_version_is_hashed_not_the_newest_on_disk\|def test_stale_install_path_aborts_before_any_review\|def test_project_scoped_record_for_another_directory_aborts\|def test_user_scoped_record_alongside_a_project_scoped_one_is_used\|def test_missing_install_record_aborts_without_marketplace_fallback\|def test_malformed_install_record_aborts_without_marketplace_fallback\|def test_out_of_tree_install_path_is_refused\|def test_passing_preflight_prints_one_resolution_line' bench/test_config.py

# Exactly three tests removed, all marketplace/install_location — nothing else disappeared
for t in test_content_hash_ignores_git_history_and_dirty_tree test_content_hash_is_order_independent \
         test_config_hash_distinguishes_mode test_config_hash_identical_inputs \
         test_load_manifest_rejects_missing_field test_load_manifest_rejects_invalid_json \
         test_load_manifest_rejects_traversal_owner test_load_manifest_accepts_real_fixture \
         test_plugin_resolution_mismatch_aborts_before_any_review \
         test_verify_config_dir_without_home_raises test_golden_flag_exits_two \
         test_print_config_hash_matches_content_hash test_missing_required_flag_exits_two \
         test_missing_model_and_effort_flags_exit_two; do
  grep -q "def $t" bench/test_config.py || echo "MISSING TEST: $t"
done
# ALL 12 pre-existing tests in test_resolve.py — no deletions are permitted in this file.
for t in test_parent_count_drives_merge_range test_single_parent_uses_manifest_base_not_parent_derived \
         test_mismatch_is_noted_not_obeyed test_empty_diff_raises_empty_diff_error \
         test_fetch_url_exact_format test_fetch_url_not_from_origin test_fetch_url_same_when_no_origin \
         test_git_invocation_confined_to_cache_repos test_assert_under_rejects_absolute_outside \
         test_assert_under_rejects_root_itself test_second_pr_runs_after_first_fails \
         test_worktree_under_repos_root_head_at_sha; do
  grep -q "def $t" bench/test_resolve.py || echo "MISSING TEST: $t"
done
# ALL 26 pre-existing tests in test_review.py — no deletions are permitted in this file.
for t in test_second_run_is_cache_hit_and_invokes_zero_reviews test_mode_change_is_cache_miss \
         test_cache_path_differs_when_only_mode_differs test_harvest_normalizes_sample_report \
         test_harvest_keeps_finding_without_any_rule_id test_harvest_ignores_empty_section \
         test_ledger_is_append_only_and_atomic test_second_runner_exits_without_touching_ledger \
         test_row_carries_every_required_field test_raw_output_is_cached_verbatim \
         test_failed_review_leaves_no_row_and_no_cache_entry test_failed_pr_does_not_prevent_later_prs \
         test_corrupt_cache_row_is_treated_as_miss test_real_capture_harvests_to_zero_findings \
         test_trailing_prose_does_not_swallow_a_real_finding test_heading_level_does_not_change_harvest \
         test_heading_section_name_rejects_prose_and_fence test_fence_contains_heading_not_a_section \
         test_thematic_break_ends_a_section test_prose_before_a_list_item_opens_nothing \
         test_non_review_output_is_rejected test_section_names_outside_headings_do_not_satisfy_the_gate \
         test_missing_section_names_are_reported_exactly test_rejection_excerpt_is_bounded \
         test_review_shaped_output_at_either_heading_level_produces_a_row \
         test_gate_does_not_apply_to_a_cache_hit; do
  grep -q "def $t" bench/test_review.py || echo "MISSING TEST: $t"
done
# BINDING, not informational: the ONLY test removals permitted anywhere are the three
# marketplace-resolver tests in test_config.py named in requirement 13. Any other removed
# `def test_` line is a failure of this prompt, not a judgement call.
git diff origin/master -- bench/ | grep '^-.*def test_' | grep -vE 'marketplace|install_location' \
  && echo "FORBIDDEN TEST DELETION (see line above)" || echo "test-deletion check: clean"

# Informational: which test names the diff removed (needs origin/master; the loops above are the binding check)
git diff origin/master -- bench/test_config.py bench/test_resolve.py bench/test_review.py | grep '^-.*def test_' || echo "origin/master unavailable or no test removed"

# The resolution contract, exercised directly
python3 -c "
import sys, pathlib, tempfile; sys.path.insert(0, 'bench')
import run, testsupport
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    src = testsupport.build_coding_repo(td / 'src')
    cfg = testsupport.build_verify_config_dir(td / 'cfg', src)
    res = run.resolve_plugin_load_path(cfg, run.repos_root(td / 'cache'))
    print('load_path  ->', res.load_path)
    print('version    ->', res.version)
    print('hash match ->', res.content_hash == run.content_hash(src))
    print('line       ->', run.resolution_line(res))
    assert res.content_hash == run.content_hash(src)
    assert str(res.load_path).endswith('plugins/cache/coding/coding/0.35.2')
    print('OK')
"

# No personal paths, stdlib-only imports
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py

# CLI contract unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; the unittest run reports `OK` with `Ran N tests` where `N > 55`; all three `MISSING TEST:` loops print nothing, the test-deletion check prints `clean`; the marketplace-resolver grep and the removed-param grep both exit 1 with no output; the inline Python prints a load path ending in `plugins/cache/coding/coding/0.35.2`, `hash match -> True` and `OK`; the personal-path grep exits 1 with no output; both `run.py` invocations exit 2.
</verification>
