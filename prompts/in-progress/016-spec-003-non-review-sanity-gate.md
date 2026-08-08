---
status: approved
spec: [003-bench-review-sanity-and-harvest-boundary]
created: "2026-08-08T02:35:00Z"
queued: "2026-08-08T00:49:09Z"
---

<summary>
- Output that is not structurally a review can no longer be written down as a perfect clean review
- A report counts as a review only when all three mandatory finding sections are actually present as headings; anything else fails that pull request loudly
- A subprocess that exits successfully after printing an error message is now caught — that is the exact failure that scored a broken invocation as flawless
- A rejected pull request leaves nothing behind: no result row, no cached output, so the next run simply retries it
- The remaining pull requests still run, and the whole run finishes with a failing exit code and lists the rejection in its summary
- The rejection message names the pull request, names each section that was missing, and quotes what the runner actually got, so the operator diagnoses it without opening a cache file
- The quoted excerpt is size-bounded, so a runaway subprocess printing megabytes cannot flood the terminal
- Section names mentioned in prose, in bold, or inside a code block do not count as sections — only real headings do
- The heading level a review uses still does not matter: reports at either observed level are accepted and recorded
- The existing tests that drove the runner with output that was never review-shaped are updated to real review shape, with every assertion kept
</summary>

<objective>
Add a sanity gate to `bench/run.py` that rejects review output which is not structurally a review — output missing any of the three mandatory finding sections — before the raw output is cached and before it is harvested, so no ledger row and no cache entry can ever be written for a non-review. The rejection names the PR, names each missing section, and carries a bounded verbatim excerpt on stderr. This closes the defect where `Unknown command: /coding:pr-review` on stdout with exit code 0 was recorded as `ok: 0 findings`.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, never commit).

Read `specs/in-progress/003-bench-review-sanity-and-harvest-boundary.md` — this prompt implements **Desired Behaviors 1 and 2** and **Acceptance Criteria AC2, AC3, AC4, AC5, AC6**. Load-bearing sections: the **Failure Modes** table (rows for "subprocess exits 0 but prints an error", "truncated mid-report", "contract drift", "rejected output is large", "crash between the gate and the ledger"), and **Security / Abuse Cases** ("fail-closed, not fail-open"; "denial by volume").

**This prompt depends on prompt 1 of this spec having landed.** Prompt 1 added `REQUIRED_SECTION_NAMES`, `HEADING_RE`, `SEVERITY_SUFFIX_RE`, `FENCE_RE`, `heading_section_name(line)` and `iter_report_lines(report_text)` to `bench/run.py`. Verify they exist before you start:

```bash
grep -n 'REQUIRED_SECTION_NAMES\|def heading_section_name\|def iter_report_lines' bench/run.py
```

If any is absent, stop and report `status: failed` with the message `"prompt 1 of spec 003 (harvest section boundaries) not yet landed"`. Do not re-implement them here — a second copy of the heading rule is exactly the drift this spec exists to prevent.

Read `bench/run.py`. The parts you touch:

- `BenchError` — the single exception type; raised inside `process_pr` it becomes a per-PR `failed:` outcome, raised outside the loop it becomes exit code 2.
- `process_pr(*, entry, coding_repo, results_dir, cache_root, model, effort, mode, config_dir, cfg_hash, rc_hash, prs_version, known_rule_ids) -> tuple[str, str]` — its current sequence is: (1) cache check and early return, (2) `resolve_pr`, (3) `build_review_argv` + `invoke_review`, (4) `TimeoutExpired` → failure log + re-raise, (5) non-zero `returncode` → failure log + `BenchError`, (6) `atomic_write_bytes(raw_path, proc.stdout.encode("utf-8"))`, (7) `harvest`, (8) `build_row` + `append_row`, (9) cache marker. **The gate goes between step 5 and step 6.**
- `run_bench` — it catches `BenchError` per PR, records `outcome, detail = "failed", str(err)`, prints `f"{pr_id}: {outcome}: {detail}"` **to stdout**, counts outcomes by the prefixes `"ok:"` / `"cache hit:"` / `"failed:"`, prints `summary: N ok, N cache hit, N failed`, and returns `1` when any PR failed. Do not change any of that. Because it prints to stdout, the gate must write its own diagnosis to stderr itself.
- `sys` is already imported. `failures_root` / `failure_log_path` exist and are used by the timeout and non-zero-exit paths only.

Read `bench/testsupport.py`. `stub_claude(bin_dir, counter_file, report_text="")` writes a `/bin/sh` stub that appends `"$*"` to `counter_file` and then emits `report_text` via `cat <<'REPORT_EOF' ... REPORT_EOF`, so a multi-line payload works as long as no line of it equals `REPORT_EOF`, and the stub's stdout is always `report_text + "\n"`.

Read `bench/test_review.py`. Six tests currently pass a payload to `stub_claude` that is **not review-shaped** and will be rejected by the gate — all six must be updated:

| Test | Current payload |
|---|---|
| `test_second_run_is_cache_hit_and_invokes_zero_reviews` | `"findings: []"` |
| `test_mode_change_is_cache_miss` | `"findings: []"` |
| `test_row_carries_every_required_field` | `"findings: []"` |
| `test_failed_pr_does_not_prevent_later_prs` | `"findings: []"` |
| `test_corrupt_cache_row_is_treated_as_miss` | `"findings: []"` |
| `test_raw_output_is_cached_verbatim` | `"findings: [{\"rule_id\":\"foo/bar\",\"path\":\"x.go\",\"line\":1}]"` |

`test_failed_review_leaves_no_row_and_no_cache_entry` uses `stub_claude_failing` (non-zero exit) and needs no payload change.

Read `commands/pr-review.md` Step 5 (search for `**MANDATORY**: Always include all three headers`) — the contract the gate enforces. **Do not edit that file.**

Read `docs/dod.md` — no personal paths, `## Unreleased` CHANGELOG entry.
</context>

<requirements>

## 1. Gate constants in `bench/run.py`

Add next to the existing module constants:

```python
NON_REVIEW_MARKER = "NOT A REVIEW"
REJECTION_EXCERPT_BYTES = 2000
```

Both are frozen invariants. Do not add a flag, an environment variable, a parameter or a config field for either. `REJECTION_EXCERPT_BYTES` is what keeps a runaway subprocess printing megabytes from flooding the operator's terminal, and it must be small enough that a 100 kB payload still produces a total stderr diagnosis under 8 kB.

## 2. `missing_sections(report_text)`

```python
def missing_sections(report_text: str) -> list[str]:
    """Return the required findings-section names absent from report_text, in canonical order.

    A section counts as present only when it appears as a markdown heading at any
    level 1-6 outside a fenced code block.  The words appearing in prose, in a
    bold run, or inside a fence do not count.  Returns [] when all three are
    present.
    """
```

Implementation: walk `iter_report_lines(report_text)`; skip every line whose `in_fence` flag is `True`; for the rest, collect `heading_section_name(line)` when it is not `None`; return `[name for name in REQUIRED_SECTION_NAMES if name not in present]`.

**Return canonical order** — `REQUIRED_SECTION_NAMES` order, i.e. `Must Fix`, `Should Fix`, `Nice to Have`. AC4 Case B asserts `Should Fix` and `Nice to Have` appear in that order; iterating the tuple gives it for free.

**Compute per-heading presence.** Do not special-case "report the last section as missing" or any other shortcut: a payload carrying only `Must Fix` must return both `Should Fix` and `Nice to Have`, and a payload carrying `Must Fix` and `Should Fix` must return only `Nice to Have`.

## 3. `rejection_excerpt(text)`

```python
def rejection_excerpt(text: str, limit: int = REJECTION_EXCERPT_BYTES) -> str:
    """Return at most limit bytes of text's UTF-8 prefix, marked when truncated."""
```

Encode `text` as UTF-8. If the encoding is at most `limit` bytes, decode and return it unchanged. Otherwise slice the first `limit` bytes, decode with `errors="ignore"` so a multi-byte character split at the boundary is dropped rather than raising, and append a visible truncation marker naming the total byte count, e.g. `f"\n[... truncated, {total} bytes total]"`. The excerpt reproduces the subprocess's own output and nothing else — never append an environment variable, a token, or any credential material.

## 4. `non_review_report(pr_id, missing, stdout_text)`

```python
def non_review_report(pr_id: str, missing: list[str], stdout_text: str) -> str:
    """Build the multi-line stderr diagnosis for output rejected as a non-review."""
```

Return exactly this shape:

```
NOT A REVIEW: <pr_id>
missing sections: <comma-joined missing names in canonical order>
no ledger row and no cache entry were written; this PR is retried on the next run
--- rejected output excerpt (<total> bytes total) ---
<rejection_excerpt(stdout_text)>
--- end excerpt ---
```

where `NOT A REVIEW` is `NON_REVIEW_MARKER` and `<total>` is `len(stdout_text.encode("utf-8"))`.

**The line beginning `missing sections: ` must be the only place any required section name appears in the diagnosis, apart from the verbatim excerpt.** Do not enumerate the full set of required sections, do not print "expected Must Fix, Should Fix, Nice to Have", and do not add a legend. AC4 asserts on the content of that one line; a message that also lists what *was* found makes the criterion unverifiable.

## 5. Wire the gate into `process_pr`

Insert immediately after the existing non-zero-`returncode` block and **before** `atomic_write_bytes(raw_path, ...)`:

```python
missing = missing_sections(proc.stdout)
if missing:
    print(non_review_report(pr_id, missing, proc.stdout), file=sys.stderr)
    raise BenchError(
        f"{NON_REVIEW_MARKER}: {pr_id}: missing sections: {', '.join(missing)}"
    )
```

Consequences that must hold and that you must not work around:

- The gate runs on **fresh subprocess output only**. It sits after the cache-hit early return, so a cache hit is never re-validated, and it is not applied to previously cached output.
- Nothing is written for a rejected review: the raw-output cache write, the harvest, the ledger append and the cache marker all come after it. Do **not** write a failure log for a gate rejection — failure logs stay exclusively on the timeout and non-zero-exit paths (the spec's Non-goals put the failure-log mechanism out of scope).
- The `BenchError` propagates to `run_bench`'s per-PR handler, which records `failed: NOT A REVIEW: ...`, prints it, continues with the remaining PRs, and returns `1`. Do not add a retry, do not add a fallback, do not downgrade the rejection to a warning.
- The `BenchError` message carries the marker, the PR id and the missing list, but **not** the excerpt — the excerpt is stderr-only, so the stdout summary line stays one readable line.

Fail-closed: on any ambiguity about whether output is a review, the outcome is rejection. A false rejection costs one re-run; a false acceptance writes a fabricated measurement into an append-only ledger.

## 6. Add `review_report(...)` to `bench/testsupport.py`

```python
def review_report(*, must_fix: str | None = "None.", should_fix: str | None = "None.",
                  nice_to_have: str | None = "None.", heading_level: int = 2,
                  preamble: str = "", trailing: str = "") -> str:
    """Build a review-shaped stub payload.

    Renders the three mandatory sections at heading_level, in the order Must Fix,
    Should Fix, Nice to Have, each carrying the given body.  Passing None for a
    section omits that section entirely, which is how a non-review payload is
    built.  preamble is emitted before the first section and trailing after the
    last one, both verbatim and both empty by default.
    """
```

Render each present section as `"#" * heading_level + " " + name + " " + annotation`, using the annotations the review command's template writes: `(Critical)`, `(Important)`, `(Optional)`. No line of the result may equal `REPORT_EOF` (the stub's heredoc delimiter).

Also add a module-level `CLEAN_REVIEW_REPORT = review_report()` for the common case, so the six updated tests read as one word rather than six copies of the same literal.

## 7. Update the six existing stub payloads — without weakening any assertion

Replace each `"findings: []"` payload listed in `<context>` with `testsupport.CLEAN_REVIEW_REPORT`. For `test_raw_output_is_cached_verbatim`, set `report_text = testsupport.review_report(must_fix="- `agent-cmd/command-thin`: sample finding at `agents/x.md:12`.")` and leave the assertion `self.assertEqual(raw_path.read_text(), report_text + "\n", ...)` exactly as it is — the stub's heredoc still yields `report_text + "\n"` for a multi-line payload.

Rule for this whole requirement: **update payloads only.** Do not delete a test, do not remove an assertion, do not relax an assertion, do not change an expected count, and do not add a skip. Every rule id you write into a payload must be an `id` that really exists in `rules/index.json`; do not invent ids and do not edit `rules/index.json`.

## 8. Add tests to `bench/test_review.py`

Existing style: plain `unittest.TestCase`, `tempfile.TemporaryDirectory()`, seed a repo with `testsupport.make_merge_repo` under `<cache_root>/repos/<owner>/<repo>`, build a one-PR manifest with `testsupport.make_manifest`, build a plugin with `testsupport.build_coding_repo` and a matching config dir with `testsupport.build_verify_config_dir(..., use_known_marketplaces=True)`, install the stub with `testsupport.stub_claude`, then call `run.run_bench(...)` inside `with mock.patch.dict(os.environ, env):`. Copy that harness; do not invent a new one.

The gate writes to `sys.stderr` via `print(..., file=sys.stderr)`, so capture it with `contextlib.redirect_stderr(io.StringIO())` around the `run_bench` call. Add `import contextlib` and `import io` to the test file's imports.

Because this harness repeats six times, factor it into one module-level helper in `bench/test_review.py` — e.g. `run_one_pr_with_payload(td, payload) -> tuple[int, str, pathlib.Path, pathlib.Path]` returning `(returncode, captured_stderr, results_dir, cache_root)` — and have the new tests call it. Do not move the helper into `testsupport.py`; it is specific to these tests.

1. **`test_non_review_output_is_rejected`** (AC2, AC5) — payload is exactly `Unknown command: /coding:pr-review`. Assert: `run_bench` returns `1`; captured stderr contains `run.NON_REVIEW_MARKER`; captured stderr contains the PR id; captured stderr contains the literal `Unknown command:` (the operator must diagnose it without opening a cache file); the ledger file either does not exist or has 0 lines; `run.reviews_root(cache_root)` contains no `.json` and no `.stdout.txt` file.

2. **`test_section_names_outside_headings_do_not_satisfy_the_gate`** (AC3) — payload in which all three literals appear but none as a heading: `Must Fix` in a prose sentence, `## Should Fix (Important)` inside a ```` ``` ```` fenced block, and `**Nice to Have**` as a bold run. Assert the same outcomes as test 1 (return `1`, marker on stderr, zero ledger rows, no review cache files). Without this test a substring check would satisfy AC2.

3. **`test_missing_section_names_are_reported_exactly`** (AC4) — two cases in one test, each asserting on the single stderr line that starts with `missing sections: `. Extract it with something like `next(l for l in stderr.splitlines() if l.startswith("missing sections: "))` and assert on the remainder of that line, **not** on the whole stderr (the verbatim excerpt reproduces the payload, which legitimately contains the section names that were present).
   - Case A: `testsupport.review_report(nice_to_have=None)` → the list is exactly `Nice to Have`; assert it does not contain `Must Fix` and does not contain `Should Fix`; ledger gains 0 rows; exit code `1`.
   - Case B: `testsupport.review_report(should_fix=None, nice_to_have=None)` → the list is exactly `Should Fix, Nice to Have`, in that order; assert it does not contain `Must Fix`; ledger gains 0 rows; exit code `1`.

   Case B is what makes a hardcoded "report the last section as missing" implementation fail.

4. **`test_rejection_excerpt_is_bounded`** (AC5) — a pure unit test on `run.non_review_report("test#1", ["Must Fix"], "x" * 100_000)`: assert `len(result.encode("utf-8")) < 8192`, and assert the result contains the truncation marker. No subprocess, no temp dirs.

5. **`test_review_shaped_output_at_either_heading_level_produces_a_row`** (AC6) — two independent runs over one-PR manifests, one with `testsupport.review_report(heading_level=2)` and one with `testsupport.review_report(heading_level=4)`. Assert for both: `run_bench` returns `0`; the ledger contains exactly 1 row; the row's `pr_id` equals the manifest's single id. Use separate results directories and separate cache roots so the second run is not a cache hit.

6. **`test_gate_does_not_apply_to_a_cache_hit`** — run once with a review-shaped payload so a row and a cache entry are written; then run again against the same cache root with the stub payload replaced by `Unknown command: /coding:pr-review`. Assert the second run returns `0` and reports a cache hit, proving the gate is not applied to previously cached output. This pins the spec constraint "the gate runs on fresh subprocess output only ... it is not applied to cache hits".

Every test runs offline: no network, no real `claude` binary, no GitHub access.

## 9. CHANGELOG

Add a bullet under the existing `## Unreleased` heading in `CHANGELOG.md` (prompt 1 of this spec created that section) using a conventional prefix (`fix:`, per `docs/changelog-guide.md` — not the non-conforming `bench:` style on v0.35.1), describing the rejection of output that is not structurally a review. Do not create a version section, do not touch any released section, and do not touch the four version strings in `.claude-plugin/`.

## 10. Do not modify

`bench/testdata/sample-report.md`, `bench/testdata/real-capture-report.md`, `bench/prs.json`, `bench/README.md`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`.

Do not change `harvest()`, `heading_section_name()`, `iter_report_lines()` or any pattern constant that prompt 1 added — reuse them. Do not change `run_bench`'s banner, per-PR exception handling, outcome counting, summary printing or return-code logic. Do not touch the timeout or non-zero-exit failure-log paths. `bench/README.md` and the whole-change CHANGELOG bullet are prompt 3 of this spec.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no third-party imports, no new top-level files outside `bench/`
- Changes land only in `bench/run.py`, `bench/testsupport.py`, `bench/test_review.py` and `CHANGELOG.md`
- The existing tests keep passing and their assertions are not weakened. Updating the six stub payloads to review-shaped output is expected and correct; deleting a test, removing an assertion, or relaxing an assertion to accommodate the gate is not. The suite's test count after this prompt is strictly greater than after prompt 1
- The gate runs on fresh subprocess output only, ahead of the raw-output cache write, so a rejected review leaves nothing under `bench/.cache/reviews/` and is retried naturally on the next invocation. It is not applied to cache hits and does not re-validate previously cached output
- A rejected PR produces no ledger row and no cache entry; the remaining PRs still run; the process exits non-zero — the same treatment an empty diff gets today
- Do NOT add a retry loop, a fallback, or a warning-only mode around a rejection. Fail-closed, not fail-open
- Do NOT write a failure log for a gate rejection — the failure-log mechanism is out of scope for this spec (Non-goals D3)
- Frozen invariants — not configurable, not flagged: the three required section names, the fact that all three are required, the list-item markers, the stderr excerpt bound, the 45-minute review timeout, the cache and results locations, the `--golden` exit-2 rejection
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`
- Review output is third-party-influenced text: the gate only matches text and slices it. No value from it is evaluated, passed to a shell, used to build a filesystem path, or used to construct a subprocess argument
- The rejection excerpt is bounded and written to stderr only; it reproduces the subprocess's own output and never copies an environment variable, token or credential into any artifact
- Heading, fence and section matching is line-oriented with bounded patterns; no construct in a report may cause unbounded backtracking or a scan that is not linear in input size
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file (`docs/dod.md`)
- `CHANGELOG.md` gains an entry under `## Unreleased` (`docs/dod.md`)
- All new tests run offline: no network, no real `claude` binary, no GitHub access
- Do NOT re-harvest or migrate anything already sitting in `bench/.cache/reviews/`
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# Prompt 1 primitives are present and reused, not duplicated
grep -n 'REQUIRED_SECTION_NAMES\|def heading_section_name\|def iter_report_lines\|def missing_sections\|def rejection_excerpt\|def non_review_report\|NON_REVIEW_MARKER\|REJECTION_EXCERPT_BYTES' bench/run.py

# The gate sits before the raw-output cache write in process_pr
grep -n 'missing_sections\|atomic_write_bytes(raw_path\|findings = harvest\|append_row' bench/run.py

# Full suite
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -25

# New tests exist by name
grep -n 'def test_non_review_output_is_rejected\|def test_section_names_outside_headings_do_not_satisfy_the_gate\|def test_missing_section_names_are_reported_exactly\|def test_rejection_excerpt_is_bounded\|def test_review_shaped_output_at_either_heading_level_produces_a_row\|def test_gate_does_not_apply_to_a_cache_hit' bench/test_review.py

# No pre-existing test was deleted or renamed
for t in test_second_run_is_cache_hit_and_invokes_zero_reviews test_mode_change_is_cache_miss \
         test_cache_path_differs_when_only_mode_differs test_harvest_normalizes_sample_report \
         test_harvest_keeps_finding_without_any_rule_id test_harvest_ignores_empty_section \
         test_ledger_is_append_only_and_atomic test_second_runner_exits_without_touching_ledger \
         test_row_carries_every_required_field test_raw_output_is_cached_verbatim \
         test_failed_review_leaves_no_row_and_no_cache_entry test_failed_pr_does_not_prevent_later_prs \
         test_corrupt_cache_row_is_treated_as_miss; do
  grep -q "def $t" bench/test_review.py || echo "MISSING TEST: $t"
done

# The gate's own contract, exercised directly
python3 -c "
import sys; sys.path.insert(0, 'bench')
import run, testsupport
print('non-review        ->', run.missing_sections('Unknown command: /coding:pr-review'))
print('all three present ->', run.missing_sections(testsupport.review_report()))
print('level 4 present   ->', run.missing_sections(testsupport.review_report(heading_level=4)))
print('case A            ->', run.missing_sections(testsupport.review_report(nice_to_have=None)))
print('case B            ->', run.missing_sections(testsupport.review_report(should_fix=None, nice_to_have=None)))
print('prose/fence/bold  ->', run.missing_sections('We looked at Must Fix items.\n\n\`\`\`\n## Should Fix (Important)\n\`\`\`\n\n**Nice to Have**\n'))
assert run.missing_sections(testsupport.review_report()) == []
assert run.missing_sections(testsupport.review_report(heading_level=4)) == []
assert run.missing_sections(testsupport.review_report(nice_to_have=None)) == ['Nice to Have']
assert run.missing_sections(testsupport.review_report(should_fix=None, nice_to_have=None)) == ['Should Fix', 'Nice to Have']
big = run.non_review_report('test#1', ['Must Fix'], 'x' * 100000)
print('100kB payload -> stderr bytes:', len(big.encode('utf-8')))
assert len(big.encode('utf-8')) < 8192
print('OK')
"

# The real capture from prompt 1 still passes the gate (it IS a review)
python3 -c "
import sys; sys.path.insert(0, 'bench')
import run
t = (run.BENCH_DIR / 'testdata' / 'real-capture-report.md').read_text()
print('real capture missing sections ->', run.missing_sections(t))
assert run.missing_sections(t) == []
print('OK')
"

# No personal paths, stdlib-only imports
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_review.py

# Reserved and mandatory flags unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Unreleased section
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; the verbose unittest run prints `OK` with a test count strictly greater than after prompt 1 and shows the non-review-gate, missing-section, excerpt-bound, heading-level and cache-hit tests by name; the `MISSING TEST:` loop prints nothing; the first inline Python prints `['Must Fix', 'Should Fix', 'Nice to Have']` for the non-review and the prose/fence/bold payload, `[]` for both review-shaped payloads, `['Nice to Have']` for case A, `['Should Fix', 'Nice to Have']` for case B, a stderr byte count under 8192, and `OK`; the second inline Python prints `[]` and `OK`; the personal-path grep exits 1 with no output; both `run.py` invocations exit 2.
</verification>
