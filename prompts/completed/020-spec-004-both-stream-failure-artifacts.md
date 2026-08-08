---
status: completed
spec: [004-bench-review-environment-control]
summary: Added both-stream failure artifact to all three failure paths in bench/run.py, with 6 new tests covering AC10/AC11/AC12 and the diagnostic-not-cache-entry constraint
execution_id: coding-bench-env-exec-020-spec-004-both-stream-failure-artifacts
dark-factory-version: v0.192.9
created: "2026-08-08T08:07:00Z"
queued: "2026-08-08T08:19:41Z"
started: "2026-08-08T08:41:26Z"
completed: "2026-08-08T08:45:25Z"
---

<summary>
- When a review fails, the benchmark now keeps both halves of what the failing process printed, not just one
- The half it used to throw away is the half the real error is written on, which once caused a confident wrong diagnosis
- Each half is written under a label naming which one it is, so the operator can tell them apart at a glance
- A half that produced nothing is written out as explicitly empty instead of being silently omitted
- All three ways a review can fail — running out of time, exiting with an error, and producing output that is not a review — now leave the same complete artifact
- Nothing about when a review is accepted or rejected changes; only what is kept behind when it fails
- A failed pull request still records no result and still gets retried on the next run, exactly as before
- The preserved artifact is a diagnostic, never a cache entry, so a failure can never look like a completed review
- The bounded error excerpt printed on screen stays bounded; the artifact on disk carries the full output
- The test suite grows and proves the behaviour with a fake review binary rather than a real one
</summary>

<objective>
Make every failed review leave behind one artifact carrying both of the subprocess's output streams, each under a label naming which stream it is, with an empty stream explicitly marked empty. Claude Code writes its real errors to **stdout** — the observed failure preserved a harmless model-name warning from stderr while `Failed to authenticate: OAuth session expired and could not be refreshed` was on stdout and discarded, which produced a wrong root-cause diagnosis — so an artifact that holds only stderr systematically preserves the wrong half.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, never commit — dark-factory handles git).

Read `specs/in-progress/004-bench-review-environment-control.md`. This prompt implements **Desired Behavior 4** and **Acceptance Criteria AC10, AC11 and AC12**. Load-bearing sections:

- **Reference: observed evidence → D3** — `bench/.cache/failures/*.stderr.txt` contained only a model-name warning while the actual cause was on stdout and discarded, and the run was misdiagnosed on the strength of the preserved half.
- **Failure Modes** rows: "Review subprocess exits non-zero after writing its real error to stdout"; "Review subprocess exceeds the 45-minute timeout" (the artifact carries whatever both streams produced before termination, **including the case where one of them is empty**); "Review subprocess exits 0 but prints a non-review (the v0.35.2 gate fires)" — unchanged rejection semantics **plus** an artifact carrying both streams; "Failed subprocess produced megabytes of output" — the artifact holds it, and the bounded stderr excerpt printed by the v0.35.2 gate is unchanged and stays bounded.
- **Constraints → "The failure artifact is a diagnostic, not a cache entry"**: writing it does not create a review cache entry, does not append a ledger row, and does not make a failed PR look cached on the next run. The v0.35.2 invariant that a rejected non-review leaves nothing under `bench/.cache/reviews/` holds unchanged.
- **Security → "Secret leakage"**: the artifact reproduces the subprocess's own two streams and nothing else — no environment variables, no tokens, no credential material.
- **Non-goals**: the runner must NOT supply an authentication token; Desired Behavior 4 exists precisely to make the OAuth failure self-diagnosing instead.

Read `bench/run.py`. The parts you touch:

- `failures_root(cache_root)` → `cache_root / "failures"`. Unchanged.
- `cache_key(cfg_hash, pr_id)` → `f"{cfg_hash}__{safe_pr_key(pr_id)}"`. Unchanged.
- `failure_log_path(cache_root, cfg_hash, pr_id)` → `failures_root(cache_root) / f"{cache_key(...)}.stderr.txt"`. **Replaced by this prompt** — the `.stderr.txt` suffix is now a lie about the file's contents. Its only two call sites are in `process_pr`; its only test reference is the glob in `test_failed_review_leaves_no_row_and_no_cache_entry`.
- `atomic_write_bytes(path, data)` — writes via a same-directory temp file and `os.replace`. Requires the parent directory to exist.
- `NON_REVIEW_MARKER = "NOT A REVIEW"`, `REJECTION_EXCERPT_BYTES = 2000`, `rejection_excerpt(text, limit)`, `non_review_report(pr_id, missing, stdout_text)`, `missing_sections(report_text)` — the v0.35.2 gate. **Do not change any of them.**
- `invoke_review(*, argv, worktree, cache_root, config_dir)` — `subprocess.run(argv, cwd=…, env=review_env(config_dir), capture_output=True, text=True, timeout=REVIEW_TIMEOUT_SECONDS)`.
- `process_pr(...)` — the three failure paths this prompt changes, in source order:
  1. the `except subprocess.TimeoutExpired as err:` block around `invoke_review`, which currently writes `err.stderr` only and re-raises;
  2. the `if proc.returncode != 0:` block, which currently writes `proc.stderr` only and raises `BenchError(f"{pr_id}: review invocation failed: exit {proc.returncode}")`;
  3. the sanity gate `if missing:` block, which prints `non_review_report(...)` to stderr and raises — and currently writes **no artifact at all**.
- `run_bench(...)` — catches `subprocess.TimeoutExpired` as `("failed", "timeout")`, `OSError` and `BenchError` as `("failed", str(err))`, then prints one `f"{pr_id}: {outcome}"` line per PR and a `f"summary: {n_ok} ok, {n_cached} cache hit, {n_failed} failed"` line. Unchanged by this prompt.

Read `bench/testsupport.py`. `stub_claude(bin_dir, counter_file, report_text)` appends its args to `counter_file`, prints `report_text` to stdout and exits 0. `stub_claude_failing(bin_dir, counter_file, exit_code=3)` appends its args, prints `stub failure` to **stderr** and exits `exit_code`. `make_stub_bin(bin_dir, name, body)` writes a `#!/bin/sh` script and chmods it 0755. `with_path(bin_dir)` returns `os.environ` with `bin_dir` prepended to `PATH`.

Read `bench/test_review.py`. `run_one_pr_with_payload(td, payload)` is the established one-PR harness: seed a merge repo under `<cache_root>/repos/testowner/repo_a`, write a one-entry manifest, build a coding repo and a config dir, install the stub `claude`, then call `run.run_bench(...)` inside `with mock.patch.dict(os.environ, env):` while capturing stderr with `contextlib.redirect_stderr`. `TestFailedReviewLeavesNoRowAndNoCacheEntry.test_failed_review_leaves_no_row_and_no_cache_entry` is the existing failure-path test and the one whose glob this prompt updates. `TestNonReviewOutputIsRejected.test_non_review_output_is_rejected` is the existing v0.35.2 gate test — its assertions must keep passing untouched.

Read `bench/test_config.py` and `bench/test_resolve.py` for the established unittest style. The 55 existing tests all pass today via `python3 -m unittest discover -s bench -p 'test_*.py'`.

Read `scripts/build-index.py` for the repo's stdlib-Python precedent.

Read `docs/dod.md` — no personal paths, `## Unreleased` CHANGELOG entry (the CHANGELOG belongs to prompt 4 of this spec; do not touch it here).

**Verified stream types** (measured on the Python 3 this repo runs, against `subprocess.run(["sh","-c","printf OUT; printf ERR >&2; sleep 5"], capture_output=True, text=True, timeout=0.5)`):

```
subprocess.TimeoutExpired.stdout -> <class 'bytes'>  b'OUT'
subprocess.TimeoutExpired.stderr -> <class 'bytes'>  b'ERR'
```

`subprocess.run(..., text=True)` yields **`str`** on `CompletedProcess.stdout` / `.stderr` but **`bytes`** on `TimeoutExpired.stdout` / `.stderr`, and either can be `None`. The artifact writer therefore has to accept `bytes`, `str` and `None` **independently per stream** — this is exactly the "mixed `bytes`/`str` combination the timeout exception actually produces" that AC11 names.
</context>

<requirements>

## 1. Constants in `bench/run.py`

Add next to the existing gate constants:

```python
# Failure artifact (frozen literals — tests grep for them and the README quotes them)
FAILURE_ARTIFACT_SUFFIX = ".failure.txt"
FAILURE_STDOUT_LABEL = "--- subprocess stdout ---"
FAILURE_STDERR_LABEL = "--- subprocess stderr ---"
FAILURE_EMPTY_STREAM_MARKER = "(empty)"
```

Both labels must be literal, distinct, and present in every artifact regardless of which stream carried anything — AC10 greps for each label and requires a count of at least 1 in both of its cases.

## 2. `stream_text(value)`

```python
def stream_text(value) -> str:
    """Return a captured subprocess stream as text, whatever shape it arrived in.

    A stream is str (CompletedProcess under text=True), bytes (TimeoutExpired,
    which ignores text mode) or None (never captured).  bytes are decoded as UTF-8
    with errors="replace" so a truncated multi-byte sequence from a killed process
    still produces a readable artifact instead of raising.  None becomes "".
    """
```

## 3. `failure_artifact_path(cache_root, cfg_hash, pr_id)`

```python
def failure_artifact_path(cache_root: pathlib.Path, cfg_hash: str,
                          pr_id: str) -> pathlib.Path:
    """Path of the both-stream diagnostic for one failed (PR, configuration) pair."""
```

Returns `failures_root(cache_root) / f"{cache_key(cfg_hash, pr_id)}{FAILURE_ARTIFACT_SUFFIX}"`.

**Delete `failure_log_path` entirely.** The `.stderr.txt` name describes a file that no longer holds only stderr, and leaving both functions in place would let a later change write the wrong one. The failure-artifact location itself is a frozen invariant: it stays under `bench/.cache/failures/`, keyed by `cache_key`, one file per (PR, configuration) pair, and is not configurable.

## 4. `failure_artifact_text(...)` and `write_failure_artifact(...)`

```python
def failure_artifact_text(*, pr_id: str, reason: str, stdout, stderr) -> str:
    """Render both captured streams into one labelled diagnostic document.

    Layout, in this order: a first line naming the PR and the reason it failed,
    then FAILURE_STDOUT_LABEL followed by the stdout text, then
    FAILURE_STDERR_LABEL followed by the stderr text.  A stream that is empty or
    whitespace-only is rendered as FAILURE_EMPTY_STREAM_MARKER under its own label
    rather than omitted — an omitted section is indistinguishable from a section
    the writer forgot, which is the ambiguity that made the observed misdiagnosis
    possible.  Neither stream is truncated: the bounded excerpt belongs to the
    v0.35.2 gate's stderr report, and the artifact is the unbounded copy.
    """


def write_failure_artifact(cache_root: pathlib.Path, cfg_hash: str, pr_id: str,
                           *, reason: str, stdout, stderr) -> pathlib.Path:
    """Write the both-stream diagnostic for a failed review and return its path.

    Creates failures_root(cache_root) when absent and writes through
    atomic_write_bytes.  Writes nothing under bench/.cache/reviews/, appends no
    ledger row, and never makes a failed PR look cached on the next run — the
    artifact is a diagnostic, not a cache entry.
    """
```

`stdout` and `stderr` are passed through `stream_text` inside `failure_artifact_text`; callers hand over whatever the subprocess API gave them and never pre-decode.

## 5. Wire all three failure paths in `process_pr`

Replace each existing single-stream write. Nothing else in `process_pr` changes — not the cache check, not `resolve_pr`, not the argv construction, not the raw-output write, not the harvest, not the row assembly, not the return values.

1. **Timeout** — in the `except subprocess.TimeoutExpired as err:` block, replace the `failure_log`/`write_bytes` lines with a single `write_failure_artifact(cache_root, cfg_hash, pr_id, reason="timeout", stdout=err.stdout, stderr=err.stderr)` and keep the bare `raise`. `run_bench` still reports this PR as `failed: timeout`.

2. **Non-zero exit** — in the `if proc.returncode != 0:` block, replace the write with `write_failure_artifact(..., reason=f"exit {proc.returncode}", stdout=proc.stdout, stderr=proc.stderr)` and keep the existing `raise BenchError(f"{pr_id}: review invocation failed: exit {proc.returncode}")` **byte-identical**.

3. **Non-review rejection** — in the sanity gate's `if missing:` block, write the artifact **before** the existing `print(non_review_report(pr_id, missing, proc.stdout), file=sys.stderr)`, with `reason=f"{NON_REVIEW_MARKER}: missing sections: {', '.join(missing)}"`, `stdout=proc.stdout`, `stderr=proc.stderr`. Then keep the existing `print(...)` and the existing `raise BenchError(...)` byte-identical.

   The gate's own semantics are unchanged in every respect: what counts as a section heading, which sections are required, the 2,000-byte bounded excerpt on stderr, no ledger row, no review cache entry, remaining PRs still run, non-zero exit. This prompt adds an artifact to the rejection path and changes nothing else about it.

## 6. Test helper in `bench/testsupport.py`

Add one helper. Do not modify or delete `stub_claude` or `stub_claude_failing` — existing tests depend on both.

```python
def stub_claude_streams(bin_dir: pathlib.Path, counter_file: pathlib.Path, *,
                        stdout_text: str = "", stderr_text: str = "",
                        exit_code: int = 0, sleep_seconds: int = 0) -> pathlib.Path:
    """Install a stub `claude` with independent control of both streams.

    Appends its args to counter_file, writes stdout_text to stdout and stderr_text
    to stderr (each omitted entirely when its argument is empty, so a genuinely
    empty stream can be reproduced), sleeps sleep_seconds, then exits exit_code.
    Both payloads are written before the sleep so a caller that kills the process
    on a timeout still captures them.
    """
```

Build it with `make_stub_bin` the way `stub_claude` and `stub_claude_failing` already do. Keep the payloads out of shell interpolation hazards by emitting them through a quoted here-document (`<<'EOF'`), the way `stub_claude` already emits `report_text`; write the stderr payload with a here-document redirected to `>&2`.

## 7. Test harness helper in `bench/test_review.py`

Add a module-level helper next to `run_one_pr_with_payload`. Do **not** modify `run_one_pr_with_payload` itself.

```python
def run_one_pr_with_streams(td: pathlib.Path, *, stdout_text: str = "",
                            stderr_text: str = "", exit_code: int = 0,
                            sleep_seconds: int = 0,
                            timeout_seconds: int | None = None):
    """Run bench over a one-PR temp manifest against a two-stream stub claude.

    Same seeding as run_one_pr_with_payload (one merge repo under
    <cache_root>/repos/testowner/repo_a, a one-entry manifest, a coding repo and an
    isolated config dir, the stub on PATH), but installs stub_claude_streams and
    captures stdout as well as stderr.  When timeout_seconds is given, run.
    REVIEW_TIMEOUT_SECONDS is patched to it for the duration of the call so the
    real timeout path can be exercised in about a second.

    Returns (returncode, captured_stdout, captured_stderr, results_dir, cache_root,
    counter_path).
    """
```

Build the isolated config directory with `testsupport.build_verify_config_dir(td / "cfg", plugin_src)` — **exactly two positional arguments, no keyword arguments**. Prompt 1 of this spec rewrites that helper's internals and removes its `use_known_marketplaces` parameter; the two-argument form is correct both before and after that change.

Capture stdout with `contextlib.redirect_stdout(io.StringIO())` alongside the existing `contextlib.redirect_stderr` usage; both modules are already imported in this file. Patch the timeout with `mock.patch.object(run, "REVIEW_TIMEOUT_SECONDS", timeout_seconds)` — `invoke_review` reads that module global at call time, so the patch takes effect without any production code becoming configurable.

## 8. New tests in `bench/test_review.py`

All tests run offline: no network, no real `claude` binary, no GitHub access. Use distinct, greppable sentinels (for example `STDOUT-SENTINEL-8F1` and `STDERR-SENTINEL-C3A`) so an assertion cannot pass by accident on shared text.

1. **`test_failed_review_artifact_carries_both_streams`** (AC10 Case A) — stub writes a stdout sentinel and a distinct stderr sentinel and exits 3. Assert: `rc == 1`; exactly one file matching `*{run.FAILURE_ARTIFACT_SUFFIX}` exists under `run.failures_root(cache_root)`; its text contains **both** sentinels, `run.FAILURE_STDOUT_LABEL` and `run.FAILURE_STDERR_LABEL`; the ledger gained 0 rows; `run.reviews_root(cache_root)` holds no `*.json` and no `*.stdout.txt`.

   **Each sentinel must be asserted under its own label, positionally** — same `text.split(...)` technique Case B uses. Assert the stdout sentinel appears in the segment following `FAILURE_STDOUT_LABEL` and before `FAILURE_STDERR_LABEL`, and the stderr sentinel in the segment following `FAILURE_STDERR_LABEL`. Presence-only assertions pass an implementation that writes each stream under the *wrong* label — which produces an artifact that looks complete and misdirects the next diagnosis, exactly the failure D3 exists to end.

2. **`test_failed_review_artifact_marks_an_empty_stream_empty`** (AC10 Case B) — stub writes the stdout sentinel only, stderr empty, exits 3. Assert: the artifact exists; it contains the stdout sentinel; it contains **both** labels; `run.FAILURE_EMPTY_STREAM_MARKER` appears in the artifact, and the text between `FAILURE_STDERR_LABEL` and end of file contains it. AC10 states this case exists "because appending stdout after stderr with no labels, or omitting an empty stream, passes Case A" — assert the stderr section is present and explicitly marked empty, not merely that the file is non-empty.

3. **`test_timeout_failure_artifact_carries_both_streams`** (AC11, unit level) — drive the writer directly with the shape the timeout exception really produces:
   ```python
   err = subprocess.TimeoutExpired(
       cmd=["claude"], timeout=1,
       output=b"STDOUT-SENTINEL-8F1", stderr="STDERR-SENTINEL-C3A",
   )
   path = run.write_failure_artifact(cache_root, "cfg", "test#1",
                                     reason="timeout",
                                     stdout=err.stdout, stderr=err.stderr)
   ```
   The mixed `bytes` stdout / `str` stderr combination is the point of the test. Assert the artifact's **full text** against both sentinels and both labels, and that the test name contains `timeout` (it does).

4. **`test_review_timeout_writes_a_both_stream_artifact`** (AC11, real path) — the same behaviour through the production path: `run_one_pr_with_streams(td, stdout_text=<stdout sentinel>, stderr_text=<stderr sentinel>, sleep_seconds=5, timeout_seconds=1)`. Assert: `rc == 1`; the captured stdout summary line reports `1 failed` and the PR line contains `timeout`; the artifact exists and carries both sentinels and both labels; the ledger gained 0 rows; no review cache entry was created. This is the boundary test — it proves the wiring in `process_pr`, not just the writer.

5. **`test_non_review_rejection_writes_a_both_stream_artifact`** (AC12) — stub prints exactly `Unknown command: /coding:pr-review` to stdout plus a benign warning sentinel to stderr and exits 0. Assert: `rc == 1`; the artifact contains **both** the `Unknown command: /coding:pr-review` text and the stderr warning sentinel, plus both labels; the results ledger gained 0 lines; `run.reviews_root(cache_root)` holds no file for that (PR, configuration) pair; the captured stdout summary reports `1 failed`; the captured stderr still carries `run.NON_REVIEW_MARKER` and the missing-section names. The last assertion is the one that proves the v0.35.2 gate's own semantics were not disturbed.

6. **`test_failure_artifact_is_not_a_cache_entry`** — after a failing run, invoke `run.run_bench` a second time over the same manifest, cache root and stub. Assert the review is invoked **again** (the counter file gains a second line) and the ledger still holds 0 rows: the artifact must never make a failed PR look cached. This is the spec constraint "the failure artifact is a diagnostic, not a cache entry" stated as a test.

## 9. Update the one existing test that names the old filename

In `bench/test_review.py`, `test_failed_review_leaves_no_row_and_no_cache_entry` globs `failures.glob("*.stderr.txt")` and asserts exactly one file. Update the glob to `f"*{run.FAILURE_ARTIFACT_SUFFIX}"` and keep the `assertEqual(len(failure_files), 1, …)` assertion and every other assertion in that test exactly as they are. This is the only permitted edit to an existing test in this prompt: it is an update to the new filename, not a relaxation. Do not delete it, do not rename it, do not drop any of its assertions.

## 10. Do not modify

`bench/prs.json`, `bench/testdata/`, `bench/README.md`, `CHANGELOG.md`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`.

Do not change `missing_sections`, `heading_section_name`, `iter_report_lines`, `harvest`, `rejection_excerpt`, `non_review_report`, `REQUIRED_SECTION_NAMES`, `NON_REVIEW_MARKER`, `REJECTION_EXCERPT_BYTES`, `build_row`, `append_row`, `atomic_write_bytes`, `invoke_review`, `review_env`, `build_review_argv`, `run_bench`, `resolve_pr`, `prepare_worktree`, `ensure_refs`, the plugin preflight, or the CLI parser.

`bench/README.md` and the CHANGELOG entry are prompt 4 of this spec. The plugin load-path preflight is prompt 1. Ref pruning is prompt 2. Do not implement any of them here.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no third-party imports, no new top-level files outside `bench/`
- Changes land only in `bench/run.py`, `bench/testsupport.py` and `bench/test_review.py`
- The existing tests keep passing and their assertions are not weakened. The only permitted edit to an existing test is the filename glob in requirement 9. Deleting a test, removing an assertion, or relaxing an assertion is not permitted. The suite's test count after this prompt is strictly greater than 55
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access — a stub executable on `PATH` that writes chosen payloads to stdout and stderr and exits with a chosen code is sufficient to reproduce every failure-artifact defect
- **Do NOT change the harvest contract or the non-review sanity gate shipped in v0.35.2.** This work adds a failure artifact to the gate's rejection path and changes nothing about what the gate accepts, what a section boundary is, or what opens a finding. The bounded 2,000-byte stderr excerpt stays bounded and unchanged
- **The failure artifact is a diagnostic, not a cache entry.** Writing it does not create a review cache entry, does not append a ledger row, and does not make a failed PR look cached on the next run. A failed PR is still retried naturally on the next invocation. The v0.35.2 invariant that a rejected non-review leaves nothing under `bench/.cache/reviews/` holds unchanged
- No credential material is read, logged, or written. The artifact reproduces the subprocess's own two streams and nothing else — no environment variables, no tokens, no argv copy carrying secrets
- Do NOT make `review_env()` supply an authentication token. Any value of `ANTHROPIC_AUTH_TOKEN` switches Claude Code into API-key mode and bypasses the OAuth path entirely, for every operator. Making the OAuth failure self-diagnosing is this prompt's job; supplying the token is a spec Non-goal
- Do NOT add environment scrubbing or an inherited-variable allowlist — the review subprocess inherits exactly what it inherits today
- Do NOT make any of this configurable: no flag, no environment variable, no config field for the failure-artifact location, the labels, the suffix, or a truncation bound. Frozen invariants: the isolated config directory `$HOME/.claude-verify`; the 45-minute review timeout; the cache, results and failure-artifact locations; the three required section names; the `--golden` exit-2 rejection. Patching `REVIEW_TIMEOUT_SECONDS` inside one test is not the same as making it configurable — no production code may read a timeout from anywhere else
- Do NOT add a field to the result row
- Subprocesses are invoked with argument lists, never shell strings; no review-output value is interpolated into a shell command
- Every git invocation still targets a path under `bench/.cache/repos/` via the existing `assert_under` chokepoint — unchanged by this prompt
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file including test data (`docs/dod.md`)
- Do NOT re-harvest, migrate or re-validate anything already under `bench/.cache/` or `bench/results/`
- Do NOT add a scenario file — the spec's **Scenario coverage** section is explicit that both failure-artifact paths are reachable with a stub executable
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# The new artifact surface exists and the misleading one is gone
grep -n 'def stream_text\|def failure_artifact_path\|def failure_artifact_text\|def write_failure_artifact' bench/run.py
grep -n 'FAILURE_ARTIFACT_SUFFIX\|FAILURE_STDOUT_LABEL\|FAILURE_STDERR_LABEL\|FAILURE_EMPTY_STREAM_MARKER' bench/run.py
grep -rn 'failure_log_path\|stderr\.txt' bench/ ; echo "old-name grep exit=$?  (expect 1)"

# All three failure paths write the artifact, and the gate is otherwise untouched
sed -n '/^def process_pr/,/^def main/p' bench/run.py | grep -n 'write_failure_artifact\|TimeoutExpired\|returncode != 0\|missing_sections\|non_review_report\|NON_REVIEW_MARKER'

# The v0.35.2 gate constants and functions are unchanged
grep -n 'NON_REVIEW_MARKER = \|REJECTION_EXCERPT_BYTES = \|def rejection_excerpt\|def non_review_report\|def missing_sections' bench/run.py

# No configurability crept in — no new flag, env var or override for the artifact
grep -niE 'add_argument.*failure|FAILURE_DIR|failure_path_override|artifact_limit|os.environ.get\(.BENCH' bench/run.py ; echo "config grep exit=$?  (expect 1)"

# New tests and helpers present by name
grep -n 'def test_failed_review_artifact_carries_both_streams\|def test_failed_review_artifact_marks_an_empty_stream_empty\|def test_timeout_failure_artifact_carries_both_streams\|def test_review_timeout_writes_a_both_stream_artifact\|def test_non_review_rejection_writes_a_both_stream_artifact\|def test_failure_artifact_is_not_a_cache_entry\|def run_one_pr_with_streams' bench/test_review.py
grep -n 'def stub_claude_streams' bench/testsupport.py
grep -n 'def stub_claude\b\|def stub_claude_failing' bench/testsupport.py

# The new harness helper does not pass the parameter prompt 1 removes
sed -n '/^def run_one_pr_with_streams/,/^class /p' bench/test_review.py | grep -n 'build_verify_config_dir\|use_known_marketplaces'

# Full suite
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
python3 -m unittest discover -s bench -p 'test_*.py' 2>&1 | grep -E '^Ran |^OK|^FAILED'

# Nothing disappeared from the existing review suite
for t in test_second_run_is_cache_hit_and_invokes_zero_reviews test_mode_change_is_cache_miss \
         test_row_carries_every_required_field test_raw_output_is_cached_verbatim \
         test_failed_review_leaves_no_row_and_no_cache_entry test_failed_pr_does_not_prevent_later_prs \
         test_corrupt_cache_row_is_treated_as_miss test_non_review_output_is_rejected \
         test_gate_does_not_apply_to_a_cache_hit test_rejection_excerpt_is_bounded \
         test_missing_section_names_are_reported_exactly test_ledger_is_append_only_and_atomic; do
  grep -q "def $t" bench/test_review.py || echo "MISSING TEST: $t"
done

# The artifact contract, exercised directly — including the mixed bytes/str timeout shape
python3 -c "
import subprocess, sys, pathlib, tempfile; sys.path.insert(0, 'bench')
import run
with tempfile.TemporaryDirectory() as td:
    cache_root = pathlib.Path(td) / 'cache'
    err = subprocess.TimeoutExpired(cmd=['claude'], timeout=1,
                                    output=b'STDOUT-SENTINEL-8F1', stderr='STDERR-SENTINEL-C3A')
    p = run.write_failure_artifact(cache_root, 'cfg', 'test#1', reason='timeout',
                                   stdout=err.stdout, stderr=err.stderr)
    text = p.read_text(encoding='utf-8')
    print(text)
    assert run.FAILURE_STDOUT_LABEL in text
    assert run.FAILURE_STDERR_LABEL in text
    assert 'STDOUT-SENTINEL-8F1' in text and 'STDERR-SENTINEL-C3A' in text
    assert p.name.endswith(run.FAILURE_ARTIFACT_SUFFIX)
    assert not run.reviews_root(cache_root).exists(), 'artifact must not create a review cache entry'
    # empty stream is marked, not omitted
    p2 = run.write_failure_artifact(cache_root, 'cfg', 'test#2', reason='exit 3',
                                    stdout='only-stdout', stderr=None)
    t2 = p2.read_text(encoding='utf-8')
    print(t2)
    assert run.FAILURE_STDERR_LABEL in t2 and run.FAILURE_EMPTY_STREAM_MARKER in t2
    assert t2.split(run.FAILURE_STDERR_LABEL)[1].strip().startswith(run.FAILURE_EMPTY_STREAM_MARKER)
    print('OK')
"

# The gate still rejects a non-review exactly as before
python3 -c "
import sys; sys.path.insert(0, 'bench')
import run
assert run.missing_sections('Unknown command: /coding:pr-review') == list(run.REQUIRED_SECTION_NAMES)
assert run.REJECTION_EXCERPT_BYTES == 2000
assert run.NON_REVIEW_MARKER == 'NOT A REVIEW'
print('OK')
"

# No personal paths, stdlib-only imports
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_review.py

# CLI contract unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; the unittest run reports `OK` with `Ran N tests`, `N > 55`; the `MISSING TEST:` loop prints nothing; the old-name grep exits 1 with no output; the first inline Python prints two artifacts, each showing both labels, and then `OK`; the second inline Python prints `OK`; the personal-path grep exits 1 with no output; both `run.py` invocations exit 2.

Operator-executed after merge, in the spec-verification phase (real tokens, live review command, not runnable here): **AC20** — the operator induces a genuine subprocess failure (for example by pointing the run at an isolated config directory with no valid credentials) and confirms the artifact under `bench/.cache/failures/` contains both stream labels with the underlying error text under the **stdout** label, not the stderr one.
</verification>
