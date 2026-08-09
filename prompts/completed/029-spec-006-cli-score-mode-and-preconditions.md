---
status: completed
spec: [006-bench-golden-scoring-and-report]
summary: 'Wired scoring into runner control flow: --golden and --score CLI flags, load_golden/load_ledger/partition_by_prs_version/score_ledger functions, run_bench post-loop scoring with only_config_hash filter, and full integration test suite (16 new tests covering AC17/18/19/21/29 and DB1)'
execution_id: coding-exec-029-spec-006-cli-score-mode-and-preconditions
dark-factory-version: v0.192.9
created: "2026-08-09T11:33:00Z"
queued: "2026-08-09T10:16:50Z"
started: "2026-08-09T10:59:16Z"
completed: "2026-08-09T11:34:20Z"
---

<summary>
- The benchmark gains a command that turns everything already recorded on disk into scores and report pages, without invoking a single review or spending a token
- Supplying the curated set to a normal run now scores that run instead of refusing to start
- Rows recorded against a different set of PRs than the curated set describes are skipped one by one and named on the console, so a number is never computed over the wrong fixture
- A configuration whose rows were all skipped gets no page at all, rather than a misleading one
- Every way the inputs can be wrong — missing curated file, malformed curated file, missing ledger, empty ledger, a corrupted line, a mismatched PR-set version, a nonsense configuration identity — stops the command with a distinct, fixed message before anything is written
- A corrupted ledger line aborts rather than being skipped, because skipping one silently reassigns later rows to the wrong run
- Identity flags are rejected when scoring an existing ledger, so nobody can believe a specific configuration was scored when it was not
- The ledger and the curated set are opened read-only and are provably unchanged afterwards
</summary>

<objective>
Wire scoring into the runner's control flow: `--golden` scores a live or cache-served run and writes its page; `--score` reads the ledger and scores every distinct `config_hash` in it, invoking nothing; `--reports-dir` defaults to `bench/reports`; every row whose `prs_version` disagrees with the golden set's is skipped before scoring and named on stderr; and every precondition aborts with exit 2 and its frozen literal before any review subprocess starts.
</objective>

<context>
Read `CLAUDE.md` for project conventions — Python 3 standard library only, no personal paths, never commit (dark-factory handles git).

Read `specs/in-progress/006-bench-golden-scoring-and-report.md`. This prompt is **prompt 4 of 5** and satisfies **Desired Behaviors 1 and 7** and **AC17, AC18, AC19, AC29**. Load-bearing sections: `## Desired Behavior` items 1 (including the whole `prs_version` sub-section) and 7, `## Acceptance Criteria` AC17/AC18/AC19/AC29, the `## Failure Modes` rows for a missing/invalid golden set, the live-run join, the per-row join, a corrupt ledger line, an absent/empty ledger and an invalid `config_hash`, and the `## Non-goals` clause forbidding automatic cache invalidation.

**This prompt depends on prompts 1, 2 and 3 of this spec having landed.** Verify before you start:

```bash
grep -n 'def score_findings\|def score_config\|def write_report\|def report_path\|def validate_config_hash\|def coding_plugin_version\|PRS_VERSION_SKIP_MARKER\|EMPTY_LEDGER_MARKER\|CORRUPT_LEDGER_MARKER\|GOLDEN_NOT_FOUND_MARKER\|INVALID_GOLDEN_MARKER\|GOLDEN_VERSION_MISMATCH_MARKER\|REQUIRED_GOLDEN_KEYS' bench/run.py
```

If any is absent, stop and report `status: failed` with the message `"prompts 1-3 of spec 006 not yet landed"`. Do not implement them here.

Read `bench/run.py` — `build_parser`, `main`, `run_bench`, `process_pr`, `load_manifest`, `ledger_path`, `BenchLock`, `BenchError`, `verify_config_dir`, and the scoring surface prompts 1-3 added. Take every signature from the file.

Read `bench/testsupport.py` — `stub_claude(bin_dir, counter_file, report_text="")` installs an executable `claude` stub that appends its args to `counter_file`; `with_path(bin_dir)` builds the environment overlay. These are how AC17 and AC18 prove no review was invoked.

Read `bench/test_config.py`, in particular `class TestCliContract` and its `test_golden_flag_exits_two`. That test currently asserts the reserved-flag rejection this prompt removes. **Requirement 8 below repurposes it in place — its `def` line must stay byte-identical**, because AC24 checks `git diff origin/master -- bench/test_*.py | grep -c '^-.*def test_'` returns 0 and the file's assertion floor is 63.

Read `bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl` — four rows, `prs_version` values `empty-diff-probe` (config `2cb78fbc…`, `tts-mcp#20`), `mode-full-probe` (config `ce1703bc…`, `node-skeleton#2` and `python-skeleton#3`) and `ruleid-probe` (config `0271bf17…`, `github-pr-review-agent#11`). Three distinct configurations, none of which may get a page.

Read `docs/dod.md` for the repository's Definition of Done.
</context>

<requirements>

## 1. Re-verify the frozen inputs

```bash
# Portable digest check: `shasum` is Perl-core and absent from many slim images, and the
# daemon does not check verification exit codes, so a missing binary would read as a pass.
sha256check() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 -c -
  elif command -v sha256sum >/dev/null 2>&1; then sha256sum -c -
  else python3 -c 'import sys,hashlib,pathlib
bad=[]
for line in sys.stdin:
    if not line.strip(): continue
    want, name = line.split()
    p = pathlib.Path(name)
    got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"
    if got != want: bad.append(f"{name}: {got}")
print("FAILED: " + "; ".join(bad) if bad else "all digests OK")
sys.exit(1 if bad else 0)'
  fi
}
sha256check <<'SHA'
90f5b0a61ac763b6abb3991fff699a4818318f22a171f6fc4375d314da43459d  bench/golden.json
af8f684b95e82577af4ac6b4a04392559ef04865ee95e7f8afdcc8f1756e86fb  bench/testdata/ledger-baseline-opus-xhigh-full.jsonl
f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209  bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl
SHA
echo "digest check exit=$? (expect 0)"
```

A `FAILED` line or a non-zero exit → stop and report `status: failed`. **Never regenerate a fixture.**

## 2. Load the golden set

```python
def load_golden(path: pathlib.Path) -> dict:
    """Read and validate a golden set.  Raises BenchError with a frozen literal."""
```

- File missing or unreadable → `BenchError(f"{GOLDEN_NOT_FOUND_MARKER}: {path}")`.
- Not valid JSON, not a JSON object, or missing any of `REQUIRED_GOLDEN_KEYS` (`entries`, `match_rule`, `states`) → `BenchError(f"{INVALID_GOLDEN_MARKER}: ...")` naming what was missing or malformed.
- Also reject when `prs_version` is absent or not a string — same `INVALID GOLDEN SET` literal. `prs_version` is **not** in `REQUIRED_GOLDEN_KEYS`, which prompt 1 froze as `("entries", "match_rule", "states")`; do **not** add it to that tuple. Validate it as a separate check in `load_golden`, because it is load-bearing for the per-row skip and an absent one would otherwise escape the loader and raise a bare `KeyError` out of `score_ledger` — which `except BenchError` does not convert, giving a traceback and exit 1 where the contract requires exit 2 with a frozen literal.
- Also reject when `entries` is not a list, or when any entry lacks `pr_id`, `path`, `signature` or `state` — same `INVALID GOLDEN SET` literal. A malformed entry reaching `score_findings` would be silently mis-tallied rather than reported, which is the failure mode the loud gate exists for.
- The golden set is opened **read-only**. Never write it, never rewrite it, never normalise it back to disk. `git diff --exit-code bench/golden.json` must exit 0 after any invocation.

## 3. Load the ledger

```python
def load_ledger(path: pathlib.Path) -> list:
    """Read a JSONL ledger.  Raises BenchError with a frozen literal."""
```

- Path absent, or present but zero bytes, or every line blank/whitespace → `BenchError(f"{EMPTY_LEDGER_MARKER}: {path}")`. Writing zero pages and exiting 0 is indistinguishable from success, so this is loud.
- A non-blank line that is not valid JSON, or that is valid JSON but not an object → `BenchError(f"{CORRUPT_LEDGER_MARKER}: {path}:{lineno}: ...")` naming the **1-based** line number of the offending line, counted over the physical lines of the file including blanks.
- **Never skip an unparseable line.** The ledger is machine-written and append-only, so a bad line means corruption; dropping it shifts every later occurrence index for that PR and silently reassigns rows to the wrong run — the exact correctness the run-chunking rule rests on.
- A row missing `config_hash`, `pr_id`, `prs_version` or `findings` is also `CORRUPT LEDGER` with its line number.
- Opened read-only. The scorer never rewrites, deduplicates, reorders or deletes a row, and never takes `BenchLock` to read.

## 4. Partition rows by `prs_version`

```python
def partition_by_prs_version(rows: list, golden_prs_version: str) -> tuple:
    """Return (kept, skipped): rows whose prs_version equals the golden set's, and the rest."""
```

For each skipped row, print exactly one line to **stderr** containing the literal `PRS VERSION SKIP`, the row's `config_hash` and **both** version strings, e.g.:

```
PRS VERSION SKIP: config 2cb78fbc… row prs_version 'empty-diff-probe' != golden prs_version 'dev-1' (pr tts-mcp#20)
```

One line per skipped **row**, not per configuration — AC29 asserts exactly 4 lines over the 4 probe rows. This is a **per-row** filter, never a per-config gate: a configuration mixing versions keeps its surviving rows and gets a page recording how many were skipped. A per-config gate produces 0 pages on AC29's third case where the correct answer is 1, and that case is the only discriminator between the two designs — do not "simplify" it away.

Why per-row and not a global abort: those rows describe different diff ranges over a different PR set, so a recall computed for them against `golden-dev-1` is not a number, and committing such a page beside a valid one invites exactly the side-by-side comparison that is invalid. This is the same argument that freezes `rules_commands_hash`, applied to the other half of the configuration identity.

## 5. Score a ledger into pages

```python
def score_ledger(*, rows: list, golden: dict, reports_dir: pathlib.Path,
                 coding_repo: pathlib.Path, only_config_hash: str | None = None) -> int:
    """Score every configuration in `rows` and write one page each.  Returns an exit code."""
```

- Apply `partition_by_prs_version` first, using `golden["prs_version"]`. **The skip happens upstream of every number** — a skipped row contributes to no run, no occurrence index, no count.
- Group the kept rows by `config_hash`, preserving first-appearance order. When `only_config_hash` is given (live mode), score just that configuration.
- Count skipped rows **per `config_hash`** and pass that as `rows_skipped=` to `score_config`.
- A configuration with **no surviving rows gets no page at all** — not an empty page, not a page with zeroes. AC29 case 1 asserts `ls <reports-dir> | wc -l` prints 0 for the all-probe fixture.
- For each surviving configuration: `write_report(reports_dir=..., config_score=..., golden=golden, coding_version=coding_plugin_version(coding_repo))`. Read the plugin version **once** before the loop so every page in one pass agrees.
- If `validate_config_hash` raises for a configuration: print the `BenchError` message (carrying `INVALID CONFIG HASH` and the offending value) to stderr, **skip that configuration, continue scoring the others**, and remember to return exit code **exactly `1`** — not merely "non-zero", which an uncaught traceback also satisfies. No file is created for the rejected configuration and no file is created outside `reports_dir`.
- Print one stdout line per written page (`wrote <path>`) so an operator can see what happened. No line contains a timestamp.
- Return `0` when every surviving configuration was scored and written, `1` when one or more was rejected.

`score_ledger` invokes **no review**, re-harvests nothing, reopens no raw capture, mutates no ledger row, edits no golden entry, and runs **no `git` command**. It never deletes or invalidates `bench/.cache/` — cache invalidation stays manual and stays the operator's call, and a scorer change does not require a cache clear at all.

## 6. Extend the CLI

In `build_parser`, replace the `--golden` help text (`[RESERVED — not implemented; scoring is future work]`) with a real description, and add two arguments:

```python
    parser.add_argument(
        "--golden",
        type=pathlib.Path,
        default=None,
        help="Golden set JSON; scores the run (or the ledger, with --score) and writes report pages",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        default=False,
        help="Score an existing ledger and exit; invokes no review. Requires --golden",
    )
    parser.add_argument(
        "--reports-dir",
        type=pathlib.Path,
        default=BENCH_DIR / "reports",
        help="Directory for report pages (default: bench/reports)",
    )
```

In `main`, the order of checks is load-bearing — **every precondition must fail before any review subprocess starts**:

1. **Delete the reserved-`--golden` rejection** — the `if args.golden is not None: print(...); return 2` block currently at the top of `main` (around `bench/run.py:1610`), whose message says scoring "is not implemented in this runner". It is replaced wholesale by the scoring paths below. `--print-config-hash` keeps its current position and behaviour.
2. If `args.score`:
   - `--golden` absent → exit 2, stderr stating score mode requires `--golden`.
   - any of `--model` / `--effort` / `--mode` supplied → exit 2, stderr stating that identity flags have no meaning when scoring an existing ledger, because a scored ledger's identity comes from its rows. Silently ignoring them would let an operator believe a specific configuration was scored.
   - `golden = load_golden(args.golden)` (raises `GOLDEN SET NOT FOUND` / `INVALID GOLDEN SET` → exit 2 via the existing top-level `except BenchError`).
   - `rows = load_ledger(ledger_path(args.out_dir))` (raises `EMPTY LEDGER` / `CORRUPT LEDGER` → exit 2).
   - `return score_ledger(rows=rows, golden=golden, reports_dir=args.reports_dir, coding_repo=args.coding_repo.resolve())`.
   - Score mode never calls `verify_config_dir()`, never resolves a PR, never opens a worktree, never takes `BenchLock`.
3. Otherwise (live mode): the existing missing-`--model`/`--effort`/`--mode` check runs unchanged. Then, **if `args.golden` is given**, `golden = load_golden(args.golden)` and compare `golden["prs_version"]` against `load_manifest(args.manifest)["version"]`; on disagreement raise `BenchError` containing `GOLDEN VERSION MISMATCH` and **both** version strings → exit 2 **before the first review**. This global gate covers only the live-run join, where there is exactly one manifest; the per-row join is requirement 4.
4. Pass `golden=golden_or_None` and `reports_dir=args.reports_dir` into `run_bench`.

In `run_bench`, add keyword arguments `golden=None, reports_dir=None` **with defaults**, so the ten-plus existing direct `run.run_bench(...)` call sites in `bench/test_config.py` keep compiling and passing untouched. After the PR loop and after `BenchLock` is released, when `golden` is not `None`: `rows = load_ledger(ledger_path(results_dir))`, then `score_ledger(rows=rows, golden=golden, reports_dir=reports_dir, coding_repo=coding_repo, only_config_hash=cfg_hash)`. Because every completed `(PR, configuration)` pair is cache-served, repeating an already-run configuration with `--golden` invokes zero reviews and costs zero tokens. A non-zero score result must not mask a non-zero run result — return the run's code when it is non-zero, otherwise the score code.

**Do not add automatic cache invalidation** on a `bench/run.py` change, and do not delete `bench/.cache/` or `bench/results/` from any code path.

## 7. Extend `bench/test_score.py`

1. **`TestScoringInvokesNoReviewAndMutatesNothing`** (AC17). Copy `ledger-baseline-opus-xhigh-full.jsonl` to `<tmp>/results/results.jsonl`, install `testsupport.stub_claude(bin_dir, counter_file)`, and run `bench/run.py --score --golden bench/golden.json --out-dir <tmp>/results --reports-dir <tmp>/reports` as a subprocess with `testsupport.with_path(bin_dir)`. Assert: exit 0; the counter file has **0 lines** (or does not exist); the temp ledger's `sha256` and `grep -c ''`-equivalent line count are identical before and after; `git diff --exit-code bench/golden.json bench/testdata/` exits 0; and the reports directory contains exactly one file, `cc64cc99…6838b.md`.

2. **`TestPreconditionsFailBeforeAnyReview`** (AC18), four subprocess cases, each with the stub `claude` on `PATH` and each asserting the counter file has 0 lines:
   - `--score --golden <missing path>` → exit 2, stderr contains `GOLDEN SET NOT FOUND`.
   - `--score --golden <file whose JSON lacks entries / match_rule / states>` → exit 2, stderr contains `INVALID GOLDEN SET`. Write that malformed file into the temp directory; it is a deliberately bad **input**, not a fixture, so authoring it here is correct.
   - **live-run mode** with a manifest whose `version` differs from the golden set's `prs_version` → exit 2, stderr contains `GOLDEN VERSION MISMATCH` **and both** version strings. Build the manifest with `testsupport.make_manifest(..., version="other-version")`.
   - `--score --golden bench/golden.json --model opus` (and separately `--effort`, `--mode`) → exit 2, stderr states identity flags have no meaning when scoring an existing ledger.

   Assert on the **literal** marker strings, never on `run.GOLDEN_NOT_FOUND_MARKER` — an assertion that greps for the symbol rather than the literal cannot fail if the literal changes, and that exact defect has been caught twice in this pipeline.

3. **`TestScoreModeOverBadLedgerFailsLoudly`** (AC19), four cases, each asserting exit 2 and that the reports directory is **empty** (0 entries):
   - no `results.jsonl` in `--out-dir` → stderr contains `EMPTY LEDGER`;
   - a zero-byte `results.jsonl` → `EMPTY LEDGER`;
   - a `results.jsonl` whose every line is whitespace → `EMPTY LEDGER`;
   - a `results.jsonl` built from the baseline fixture with one line replaced by `{not json` → stderr contains `CORRUPT LEDGER` **and** the offending **1-based** line number. Place the bad line at line 3 and assert the **anchored** form `f"{ledger_path}:3:"` is in stderr, plus `assertNotIn(f"{ledger_path}:2:", stderr)` and `assertNotIn(f"{ledger_path}:4:", stderr)`. A bare `self.assertIn("3", stderr)` is satisfied by a digit in the random temporary-directory path in the same message roughly a third of the time, so it passes against a 0-based implementation.
   - a `results.jsonl` built from the baseline fixture with one line replaced by a valid JSON object missing a required field (e.g. `{"pr_id": "x#1"}`, with no `config_hash`) → exit 2, stderr contains `CORRUPT LEDGER` and that line's 1-based number, anchored the same way.

4. **`TestRowsAgainstAnotherManifestAreSkippedPerRow`** (AC29), three cases:
   - `ledger-probe-configs-mixed-prs-version.jsonl` scored against the real golden set exits **0**, writes **0** pages and emits exactly **4** stderr lines containing `PRS VERSION SKIP`, each naming its `config_hash` and both version strings. Assert all three probe versions (`empty-diff-probe`, `mode-full-probe`, `ruleid-probe`) and `dev-1` appear, and that no file named for `2cb78fbc…`, `ce1703bc…` or `0271bf17…` exists in the reports directory.
   - the baseline slice **concatenated** with the probe slice writes exactly **1** page — `cc64cc99…6838b.md` — with AC3's numbers unchanged, plus the same 4 skip lines. **Assert that page's Configuration block reads `- rows skipped: 0`.** The four skipped rows belong to three *other* configurations, so a per-configuration counter renders `0` here while a global counter renders `4` — this assertion is the only thing in the spec separating the two, because AC29 case 3 has one skip inside one configuration, where both designs agree. Inline comment: a scorer ignoring `prs_version` writes four pages here and a global abort writes zero, so this case rules out both — but it does **not** separate a per-row filter from a per-config gate, because no configuration in this fixture mixes versions.
   - the baseline slice with the single `tts-mcp#20` row's `prs_version` rewritten in-test to `mode-full-probe` writes exactly **1** page. **Assert every number by reading the rendered page back**, not off a result object the subprocess never returns: the Configuration block line `- rows skipped: 1`; `parse_table` of the `## Runs` table yielding exactly one row whose cells read `partial`, PRs `4`, golden in scope `41`, findings `41`, hits `41`, misses `0`, matched rejected `0`, gap candidates `0`, recall `1.000`, precision `1.000`; and `parse_table` of `## Per-PR` containing **no** `tts-mcp#20` row and exactly four rows. The skipped PR's single golden entry is **out of scope, not a miss**. Note that `gap candidates` here is a rendered integer cell reading `0` — do not assert `gap_candidates == ()` against it. Inline comment: **this is the discriminator**; a per-config gate yields 0 pages here rather than 1, so trimming this case as redundant would silently regress the per-row rule.

5. **`TestInvalidConfigHashRejectsOneConfigAndKeepsTheRest`** (AC21, CLI half). Build a temp ledger from the baseline slice plus one extra row that is a `copy.deepcopy` of the `quant#109` baseline row with **only** `config_hash` rewritten to `"../../etc/passwd"` — every other field, including `prs_version` `dev-1`, `pr_id`, `findings`, `runner_version` and `duration_seconds`, left intact, so the row passes `load_ledger`'s required-field check and the `prs_version` filter and actually reaches the hash gate instead of aborting earlier as `CORRUPT LEDGER`. Assert: stderr contains `INVALID CONFIG HASH` and the offending value; the exit code is exactly `1`; the baseline page is still written; and no file was created outside the reports directory (walk the temp tree and compare `st_mtime` against a marker file created first).

6. **`TestLiveRunWithGoldenScoresItsOwnConfigurationOnly`** (DB1, live-run half). The whole live-mode `--golden` branch — the new `run_bench` keyword parameters, the post-loop scoring call and the `only_config_hash` filter — is otherwise unexercised in the container, because the one live case in test 2 exits at the precondition and never enters `run_bench`. Build a run with `testsupport.stub_claude(bin_dir, counter_file, report_text=testsupport.review_report(...))`, `testsupport.seed_one_pr_manifest(...)` and `testsupport.build_verify_config_dir(...)` following the existing live-run tests in `bench/test_config.py`, and a small golden set written into the temp directory whose `prs_version` **matches** that manifest's `version`. Assert: exit 0; a page is written for that run's own `config_hash` and for **no** other; and the ledger from a prior unrelated `config_hash` seeded into the same results directory produced **no** page, proving `only_config_hash` filters rather than scoring the whole ledger.

7. **`TestRunFailureOutranksScoreResult`** (DB1, exit-code precedence). Same harness with `testsupport.stub_claude_failing(...)` so the run itself returns non-zero, plus a valid `--golden`. Assert the process exits with the **run's** non-zero code, not the score's `0` — a green scoring pass must never mask a failed run.

## 8. Repurpose the existing reserved-flag test in place

`bench/test_config.py` currently contains, inside `class TestCliContract`:

```python
    def test_golden_flag_exits_two(self):
        """--golden exits 2 and stderr mentions scoring / future work."""
```

**Keep the `def test_golden_flag_exits_two(self):` line byte-identical** — AC24's `git diff origin/master -- bench/test_*.py | grep -c '^-.*def test_'` must return 0, so renaming or deleting it fails the criterion. Rewrite only its docstring and body: `--golden bench/golden.json` with no `--model` / `--effort` / `--mode` and no `--score` is a live run missing its identity flags, so it still exits 2 — now with the missing-argument message. Assert exit 2, that stderr names `--model`, and that stderr no longer claims scoring is unimplemented (`self.assertNotIn("future work", result.stderr)`). Keep **at least three** assertions in the function so `bench/test_config.py` stays at or above its floor of 63.

Then re-run `grep -cE '^\s*(self\.assert|assert )' bench/test_config.py` and confirm it is still ≥ 63.

## 9. Error paths and exit codes

| Condition | Exit | Stderr literal |
|---|---|---|
| `--score` without `--golden` | 2 | (plain message; no frozen literal required) |
| `--score` with `--model` / `--effort` / `--mode` | 2 | plain message naming the flags |
| golden file missing/unreadable | 2 | `GOLDEN SET NOT FOUND` |
| golden JSON malformed, missing `entries`/`match_rule`/`states`, or missing `prs_version` | 2 | `INVALID GOLDEN SET` |
| live run, golden `prs_version` ≠ manifest `version` | 2 | `GOLDEN VERSION MISMATCH` + both versions |
| ledger absent / zero-byte / all-whitespace | 2 | `EMPTY LEDGER` |
| a ledger line is not valid JSON or not an object | 2 | `CORRUPT LEDGER` + 1-based line number |
| a row's `config_hash` is not 64 lowercase hex | exactly `1` | `INVALID CONFIG HASH` + value, other configs still scored |
| a row's `prs_version` ≠ golden's | not an error | `PRS VERSION SKIP` per row on stderr; scoring continues |
| every configuration scored and written | 0 | — |

All exit-2 paths write **zero** pages. Reuse the existing top-level `except BenchError` in `main` to convert a `BenchError` to exit 2; do not add a second handler.

## 10. Out of scope for this prompt — do not implement

`bench/README.md`, `CHANGELOG.md`, the `.gitignore` verification, the personal-path and stdlib sweeps, and the deleted-test / assertion-floor / frozen-fixture audit belong to prompt 5. Do not add token counting, cost capture, automatic cache invalidation, or a flag that changes the match rule, the run-chunking rule, the report location or the ratio rendering.
</requirements>

<constraints>
- Python 3 **standard library only**. No third-party imports, no new top-level files outside `bench/`.
- **`bench/golden.json` and everything under `bench/testdata/` are frozen inputs.** `git diff --exit-code bench/golden.json bench/testdata/` must exit 0 after every test run.
- **The ledger is append-only and read-only to the scorer.** No row is rewritten, deduplicated, reordered or deleted; `bench/results/` and `bench/.cache/` stay gitignored; the scorer opens the ledger for reading only.
- **Do NOT modify `.gitignore`.**
- **Do NOT change `commands/pr-review.md` or anything under `rules/`.**
- **Do NOT touch the harvest layer**, `HarvestResult`, the `UNATTRIBUTABLE FINDING` gate or the `NOT A REVIEW` gate, or their tests. **Do NOT fix D8.**
- **The precondition marker literals are frozen:** `GOLDEN SET NOT FOUND`, `INVALID GOLDEN SET`, `GOLDEN VERSION MISMATCH`, `PRS VERSION SKIP`, `EMPTY LEDGER`, `CORRUPT LEDGER`, `INVALID CONFIG HASH`. Tests assert the literal string, never the symbol.
- **Do NOT add automatic cache invalidation** on a `bench/run.py` change, and never delete `bench/.cache/` or `bench/results/` from code.
- **Do NOT add token counting or cost capture.**
- **Do NOT skip a corrupt ledger line** and do not add a `--force` / `--skip-bad-lines` escape hatch.
- **Do NOT make the report location, the `prs_version` skip rule, the run-chunking rule or the ratio rendering configurable.**
- **No test function may be deleted or renamed** in `bench/test_config.py`, `bench/test_resolve.py` or `bench/test_review.py`, and no assertion relaxed. Floors: 63 / 46 / 265. `test_golden_flag_exits_two` is repurposed in place with its `def` line unchanged.
- **Every existing `run.run_bench(...)` call site in `bench/test_config.py` must keep working untouched** — the new `golden` and `reports_dir` parameters carry defaults.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file.
- **`docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" is satisfied by prompt 5 of this spec (AC23), not here.** Do not add a CHANGELOG entry in this prompt. Spec 002's precedent: a mid-chain prompt that described only its own slice left the release classifier cutting a patch where a minor was due, which is why the CHANGELOG lands once, last, describing what all five prompts shipped.
- Do NOT commit — dark-factory handles git.
- Existing tests must still pass.
</constraints>

<verification>
```bash
# Frozen inputs untouched
# Portable digest check: `shasum` is Perl-core and absent from many slim images, and the
# daemon does not check verification exit codes, so a missing binary would read as a pass.
sha256check() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 -c -
  elif command -v sha256sum >/dev/null 2>&1; then sha256sum -c -
  else python3 -c 'import sys,hashlib,pathlib
bad=[]
for line in sys.stdin:
    if not line.strip(): continue
    want, name = line.split()
    p = pathlib.Path(name)
    got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING"
    if got != want: bad.append(f"{name}: {got}")
print("FAILED: " + "; ".join(bad) if bad else "all digests OK")
sys.exit(1 if bad else 0)'
  fi
}
sha256check <<'SHA'
90f5b0a61ac763b6abb3991fff699a4818318f22a171f6fc4375d314da43459d  bench/golden.json
af8f684b95e82577af4ac6b4a04392559ef04865ee95e7f8afdcc8f1756e86fb  bench/testdata/ledger-baseline-opus-xhigh-full.jsonl
f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02  bench/testdata/ledger-sonnet-medium-short-4runs.jsonl
165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7  bench/testdata/ledger-sonnet-medium-short-partial.jsonl
f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209  bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl
SHA
echo "digest check exit=$? (expect 0)"
git diff --exit-code bench/golden.json bench/testdata/ ; echo "frozen-input diff exit=$? (expect 0)"
git diff -- .gitignore ; echo "gitignore diff must be empty"

# New surface and CLI
grep -n 'def load_golden\|def load_ledger\|def partition_by_prs_version\|def score_ledger' bench/run.py
grep -n '"--score"\|"--reports-dir"' bench/run.py
grep -n 'RESERVED' bench/run.py ; echo "reserved-help grep exit=$? (expect 1 — removed)"
python3 bench/run.py --help 2>&1 | grep -E '\-\-golden|\-\-score|\-\-reports-dir'

# The reserved-flag test was repurposed, not deleted
grep -n 'def test_golden_flag_exits_two' bench/test_config.py   # must still exist, unchanged
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py      # expect >= 63

# Score mode end to end over the probe fixture — 0 pages, 4 skip lines
python3 - <<'EOF'
import subprocess, sys, tempfile, pathlib, shutil, os
td = pathlib.Path(tempfile.mkdtemp())
(td / 'results').mkdir(); (td / 'reports').mkdir()
shutil.copy('bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl', td / 'results' / 'results.jsonl')
r = subprocess.run([sys.executable, 'bench/run.py', '--score', '--golden', 'bench/golden.json',
                    '--out-dir', str(td/'results'), '--reports-dir', str(td/'reports')],
                   capture_output=True, text=True)
pages = list((td/'reports').iterdir())
skips = [l for l in r.stderr.splitlines() if 'PRS VERSION SKIP' in l]
print('exit', r.returncode, 'pages', len(pages), 'skip lines', len(skips))
print(r.stderr.strip())
assert r.returncode == 0, r.stderr
assert len(pages) == 0, pages
assert len(skips) == 4, skips
EOF

# Score mode over baseline + probe — exactly 1 page with AC3 numbers
python3 - <<'EOF'
import subprocess, sys, tempfile, pathlib
td = pathlib.Path(tempfile.mkdtemp())
(td/'results').mkdir(); (td/'reports').mkdir()
blob = (pathlib.Path('bench/testdata/ledger-baseline-opus-xhigh-full.jsonl').read_text()
        + pathlib.Path('bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl').read_text())
(td/'results'/'results.jsonl').write_text(blob)
r = subprocess.run([sys.executable, 'bench/run.py', '--score', '--golden', 'bench/golden.json',
                    '--out-dir', str(td/'results'), '--reports-dir', str(td/'reports')],
                   capture_output=True, text=True)
pages = sorted(p.name for p in (td/'reports').iterdir())
skips = [l for l in r.stderr.splitlines() if 'PRS VERSION SKIP' in l]
print('exit', r.returncode, 'pages', pages, 'skip lines', len(skips))
assert r.returncode == 0, r.stderr
assert pages == ['cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md'], pages
assert len(skips) == 4, skips
text = (td/'reports'/pages[0]).read_text()
skipped_line = [l for l in text.splitlines() if l.startswith('- rows skipped: ')]
print(skipped_line)
assert skipped_line == ['- rows skipped: 0'], skipped_line
print([l for l in text.splitlines() if l.startswith('| 1 |')][:1])
EOF

# Preconditions, all with exit 2 and their frozen literals
python3 bench/run.py --score --golden /nonexistent/golden.json ; echo "exit=$?"
python3 bench/run.py --score --golden bench/golden.json --model opus ; echo "exit=$?"

# Assertion floors (AC24)
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 265

grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$? (expect 1)"
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
make precommit
```

Expected: the digest check exits 0 with no `FAILED` line, the frozen-input diff is empty and the `.gitignore` diff is empty; the four new functions and the two new flags exist and `RESERVED` is gone from the help text; `test_golden_flag_exits_two` still exists and `bench/test_config.py` is at or above 63 assertions; the probe-only score prints `exit 0`, `pages 0` and `skip lines 4`; the baseline+probe score prints `exit 0`, `pages ['cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md']`, `skip lines 4`, `- rows skipped: 0` and a Runs row reading 42 / 42 / 0 / 0 / 0 / 1.000 / 1.000; the missing-golden invocation exits 2 with `GOLDEN SET NOT FOUND` on stderr; the identity-flag invocation exits 2 naming the flags; the two remaining assertion counts are at least 46 and 265; the personal-path grep exits 1; the unittest run reports `OK` with `Ran N tests`, `N > 103`, listing the no-review, precondition, corrupt-ledger, prs-version-skip, invalid-config-hash, live-run-with-golden and run-failure-precedence tests by name; `make precommit` exits 0.
</verification>
