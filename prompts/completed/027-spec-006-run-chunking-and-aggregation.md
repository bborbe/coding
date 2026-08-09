---
status: completed
spec: [006-bench-golden-scoring-and-report]
summary: Implemented run chunking by per-PR occurrence index, per-run/per-PR aggregation dataclasses, score_run, score_config, and all 13 new unit tests covering AC4/AC5/AC6/AC12/AC30
execution_id: coding-exec-027-spec-006-run-chunking-and-aggregation
dark-factory-version: v0.192.9
created: "2026-08-09T11:31:00Z"
queued: "2026-08-09T10:16:50Z"
started: "2026-08-09T10:47:37Z"
completed: "2026-08-09T10:50:00Z"
---

<summary>
- The benchmark can now tell apart repeated attempts at the same configuration, so "run 2 of 4" stops being something an operator reconstructs by eye
- Runs are separated by counting how many times each PR has already appeared, never by looking at the clock
- That matters concretely: on the real recorded data the gap between two runs is 48 seconds while gaps inside a run reach 140 seconds, so no time-based rule can separate them and the one applied by hand got it wrong
- A run in which some PR never produced a row is labelled incomplete and is scored only against the PRs it actually covers
- A PR that failed and left no row therefore no longer looks like a collapse in review quality
- Each run reports its own hit, miss, gap and timing numbers, broken down per PR
- Both ratios are defined even when their denominator is zero, rendering as "n/a" rather than zero or a crash
- Still no files written and no command-line surface — this prompt only turns matched findings into per-run numbers
</summary>

<objective>
Chunk a configuration's ledger rows into runs by per-PR occurrence index, label each run complete or partial, score each run over only the PRs it covers, and aggregate per-run and per-PR numbers into a result object. After this prompt the four-run and eight-run real ledger slices reproduce the spec's published tables exactly, with both zero-denominator cases rendering `n/a`.
</objective>

<context>
Read `CLAUDE.md` for project conventions — Python 3 standard library only, no personal paths, never commit (dark-factory handles git).

Read `specs/in-progress/006-bench-golden-scoring-and-report.md`. This prompt is **prompt 2 of 5** and satisfies **Desired Behaviors 4 and 5** and **AC4, AC5, AC6, AC12, AC30**. Load-bearing sections: `## Desired Behavior` items 4 and 5, `## Acceptance Criteria` AC4/AC5/AC6/AC12/AC30, the `## Failure Modes` rows for a partial run, a zero-`accepted`-in-scope golden set and a run matching zero entries, and the `## Non-goals` clause forbidding a configurable run-chunking rule.

**This prompt depends on prompt 1 of this spec having landed.** Verify before you start:

```bash
grep -n 'def score_findings\|def entries_in_scope\|def iter_findings\|def format_ratio\|class ScoreResult\|RATIO_NA' bench/run.py
```

If any of the six is absent, stop and report `status: failed` with the message `"prompt 1 of spec 006 not yet landed"`. Do not implement prompt 1's surface here.

Read `bench/run.py` — `score_findings`, `ScoreResult`, `entries_in_scope`, `iter_findings`, `format_ratio`, and the existing `build_row` for the exact ledger row field names.

Read `bench/test_score.py` (created by prompt 1) for the `load_golden` / `load_slice` helpers and the established test style. Extend that file; do not create a second scoring test module.

Read `bench/testdata/ledger-sonnet-medium-short-4runs.jsonl` and `bench/testdata/ledger-sonnet-medium-short-partial.jsonl`. Both are frozen operator-installed inputs. Never write, regenerate or repair one.

Read `docs/dod.md` for the repository's Definition of Done.

**The expected PR set is the golden set's own PR coverage.** Score-only mode has no manifest — each ledger row carries only its own `pr_id` — so "does this run cover every PR" is decided against the distinct `pr_id` values present in `golden["entries"]`. On `bench/golden.json` that is exactly the five fixture PRs (`tts-mcp#20`, `github-pr-review-agent#11`, `quant#109`, `node-skeleton#2`, `python-skeleton#3`), which is why AC30's five-PR runs are complete and its 3-PR and 1-PR runs are partial. Do not read `bench/prs.json` for this; it is unavailable to the scorer's contract and would make score-only mode depend on a file the ledger rows do not reference.
</context>

<requirements>

## 1. Re-verify the frozen inputs you assert against

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
f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02  bench/testdata/ledger-sonnet-medium-short-4runs.jsonl
165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7  bench/testdata/ledger-sonnet-medium-short-partial.jsonl
SHA
echo "digest check exit=$? (expect 0)"
```

A `FAILED` line or a non-zero exit → stop and report `status: failed` with the observed digest. **Never regenerate a fixture.**

## 2. Implement run chunking

```python
def chunk_runs(rows: list) -> list:
    """Split one configuration's ledger rows into runs by per-PR occurrence index.

    Within a config, the k-th row for a given pr_id — in ledger file order —
    belongs to run k.  Returns a list of lists, run 1 first.  Input not mutated.
    """
```

Implementation: a `collections.Counter` keyed by `pr_id`; for each row in input order, its run index is the current count for its `pr_id`, then increment. Collect into a `collections.defaultdict(list)` and return `[runs[k] for k in sorted(runs)]`. Rows inside a run stay in file order.

**Timestamps are read nowhere in this function.** Do not read `started_at`, do not sort by it, do not compute a gap, do not apply a threshold. **The literal string `started_at` must not appear anywhere inside `chunk_runs`, comments and docstring included** — the verification below greps the function body and expects `0`, so even a "we deliberately ignore started_at" comment makes a correct implementation look non-compliant. Put that rationale in the test instead. In the real ledger the boundary between run 2 and run 3 of config `9ce66e05…` is **48 seconds** while gaps *inside* runs 1, 2 and 4 reach **140, 128 and 110 seconds** — no time threshold separates them in either direction, and the threshold applied by hand is the one that produced the wrong answer this spec exists to prevent. There is no flag, no keyword argument and no environment variable that switches chunking to a clock.

## 3. Implement the aggregation dataclasses

```python
@dataclasses.dataclass(frozen=True)
class PrBreakdown:
    pr_id: str
    entries_in_scope: int
    hits: int
    misses: int
    findings: int
    gap_candidates: int          # a COUNT — len(ScoreResult.gap_candidates)
    duration_seconds: int


@dataclasses.dataclass(frozen=True)
class RunScore:
    index: int                 # 1-based
    pr_ids: tuple              # PRs covered, in first-appearance order within the run
    complete: bool
    span_start: str            # earliest started_at among the run's rows; display only
    span_end: str              # latest started_at among the run's rows; display only
    wall_time_seconds: int
    score: ScoreResult
    per_pr: tuple              # tuple[PrBreakdown, ...]


@dataclasses.dataclass(frozen=True)
class ConfigScore:
    config_hash: str
    model: str
    effort: str
    mode: str
    rules_commands_hash: str
    prs_version: str
    runner_versions: tuple     # every DISTINCT runner_version among the scored rows, sorted
    rows_skipped: int
    runs: tuple                # tuple[RunScore, ...]
```

`PrBreakdown.gap_candidates` and every `gap candidates` cell in a table tuple below are **integers** (`len(...)`). The tuple of verbatim candidate dicts stays where prompt 1 put it, on `ScoreResult.gap_candidates`, and is never flattened into a count there.

`rows_skipped` counts this configuration's rows dropped for a `prs_version` disagreement. It is **0** in everything this prompt does; prompt 4 owns the skip and passes the real count. Give it a default of `0` so this prompt's tests construct nothing artificial.

`runner_versions` is the **set** of distinct values present, sorted, never the first row's — it is the field whose whole purpose is to make a ledger mixing pre- and post-005 harvest output visible rather than silently averaged. All 66 rows on disk carry `"1"`, so no real fixture reaches a mixed value. Test 6 below pins the mixed case on the **result object**, and prompt 3 pins it again on the **rendered page** — both are required, and neither substitutes for the other.

## 4. Implement `score_run`

```python
def score_run(*, rows: list, golden: dict, expected_pr_ids: frozenset, index: int) -> RunScore:
```

- `pr_ids` = the distinct `pr_id` values in `rows`, in first-appearance order, as a tuple.
- `complete` = `set(pr_ids) == set(expected_pr_ids)`.
- Scope: `entries_in_scope(golden, pr_ids)`. **A run is scored only against the golden entries of the PRs it actually covers.** The entries of a PR the run did not cover are **out of scope, not misses** — charging a partial run the full 42 reports a recall collapse where the only event was a PR that never ran. AC30's `golden in scope` column is the discriminator: 42 for the five-PR runs, 24 for the two 3-PR runs, 1 for the single-PR run.
- `score` = `score_findings(entries=<scoped entries>, findings=iter_findings(rows))`.
- `span_start` / `span_end` = `min` / `max` of the rows' `started_at` strings (ISO-8601, lexicographically ordered). These are **display data only**: no scoring decision reads them, and AC6 requires every number to survive overwriting all of them with one identical literal.
- `wall_time_seconds` = `round(sum(row["duration_seconds"] for row in rows))` — **`round` of the unrounded sum**, not the sum of rounded values. On the baseline slice this is `round(2533.923)` = **2534**, matching `bench/golden.json`'s frozen `baseline.wall_time_seconds`; summing the rounded column instead gives 2533. That one-second gap is a rounding-order difference, not a data error.
- `per_pr` = one `PrBreakdown` per covered `pr_id`, in `pr_ids` order. Each is produced by calling `score_findings` again with that PR's entries and that PR's findings only, so a per-PR row is a real re-score rather than a hand-summed slice of the run total. `duration_seconds` on a `PrBreakdown` is `round(raw)` for that PR's row — the whole-seconds rounding of each row's own value. If one `pr_id` somehow has two rows inside one run (it cannot, by construction of the occurrence index), sum their raw durations and round once.

## 5. Implement `score_config`

```python
def score_config(*, rows: list, golden: dict, rows_skipped: int = 0) -> ConfigScore:
    """Score every run of one configuration's ledger rows."""
```

- Require all `rows` to share one `config_hash`; the caller (prompt 4) groups by it. Take `config_hash`, `model`, `effort`, `mode`, `rules_commands_hash` and `prs_version` from the first row — these are components of the config identity, so every row of a configuration agrees on them by construction.
- `expected_pr_ids` = `frozenset(e["pr_id"] for e in golden["entries"])`.
- `runs` = `tuple(score_run(rows=chunk, golden=golden, expected_pr_ids=expected_pr_ids, index=i) for i, chunk in enumerate(chunk_runs(rows), 1))`.
- `runner_versions` = `tuple(sorted({str(r.get("runner_version")) for r in rows}))`.
- Pure: no I/O, no mutation of `rows` or `golden`, no `git`, no subprocess, no network.

## 6. Extend `bench/test_score.py`

Do not touch `bench/test_config.py`, `bench/test_resolve.py` or `bench/test_review.py` — their per-file assertion floors (63 / 46 / 265) are AC24 and a new-file surplus does not pay for a gutted old one.

1. **`TestBaselinePerPrBreakdown`** (AC4). Score the baseline slice as one config. Assert run count 1, then assert the **whole per-PR table in one comparison** — build the observed table as a list of tuples `(pr_id, entries_in_scope, hits, misses, findings, gap_candidates, duration_seconds)` and `assertEqual` it against:

   ```python
   [
       ("tts-mcp#20",                1,  1, 0,  1, 0, 420),
       ("github-pr-review-agent#11", 13, 13, 0, 13, 0, 690),
       ("quant#109",                 6,  6, 0,  6, 0, 268),
       ("node-skeleton#2",           10, 10, 0, 10, 0, 686),
       ("python-skeleton#3",         12, 12, 0, 12, 0, 469),
   ]
   ```

   Pass `msg=` to the assertion carrying the observed table pretty-printed, so a failure prints what was actually computed. Separately assert `run.wall_time_seconds == 2534` **and** `run.wall_time_seconds == golden["baseline"]["wall_time_seconds"]`, with an inline comment that summing the rounded per-PR column would give 2533.

   **Pin the configuration identity by value in the same test.** Nothing else in this spec asserts `ConfigScore.model`, `.effort`, `.mode`, `.rules_commands_hash`, `.prs_version` or the run span by value — prompt 3 only checks the corresponding page lines are *present*, and compares span cells against the very object that produced them, so an implementation assigning `model=rows[0]["effort"]` would pass the entire suite. Add:

   ```python
   self.assertEqual(
       (cfg.config_hash, cfg.model, cfg.effort, cfg.mode,
        cfg.rules_commands_hash, cfg.prs_version, cfg.runner_versions, cfg.rows_skipped),
       ("cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b",
        "opus", "xhigh", "full",
        "ecc803331f860b845a6a1b8a103e889bce02520e8cc04ea88102de74c8d5600d",
        "dev-1", ("1",), 0),
   )
   self.assertEqual(run.span_start, min(r["started_at"] for r in rows))
   self.assertEqual(run.span_end, max(r["started_at"] for r in rows))
   self.assertNotEqual(run.span_start, run.span_end)
   ```

2. **`TestFourRunSliceChunksIntoFourRuns`** (AC5). Load `ledger-sonnet-medium-short-4runs.jsonl`, score as one config, assert `len(runs) == 4`, and assert the **whole table in one comparison** as a list of tuples `(findings, accepted_hits, misses, matched_rejected, gap_candidates, recall, precision)`:

   ```python
   [
       (3, 2, 40, 0, 1, "0.048", "1.000"),
       (2, 1, 41, 0, 1, "0.024", "1.000"),
       (5, 2, 40, 0, 3, "0.048", "1.000"),
       (6, 0, 42, 0, 6, "0.000", "n/a"),
   ]
   ```

   Also assert every run covers all 5 PRs and `complete is True` for all four. Run 4 is the real-data degenerate case: zero matched entries means the precision denominator is zero and the required rendering is the literal `n/a` — never `0.000`, never an exception. Assert `runs[3].score.precision == R.RATIO_NA` **and** `== "n/a"`, so the assertion pins the literal and not just the symbol.

3. **`TestRunChunkingIgnoresTimestamps`** (AC6), two cases:
   - Deepcopy the four-run slice and overwrite **every** row's `started_at` with one identical literal (e.g. `"2026-01-01T00:00:00+00:00"`). Re-score and assert the run count and the **complete AC5 table** are unchanged. Reuse the same expected table constant as test 2 rather than re-typing it.
   - Reverse the physical order of the 20 lines, re-score, and assert that for each `pr_id` the k-th row of the reversed order lands in run k of the reversed result — i.e. chunking is a function of file order alone. Assert the run count is still 4.

   Add an inline comment recording the measured evidence: the boundary between run 2 and run 3 is 48 seconds while gaps inside runs 1, 2 and 4 reach 140, 128 and 110 seconds, so no time threshold separates them and this test is what stops a gap-keyed chunker from passing AC5 by coincidence.

4. **`TestPartialRunsAreLabelledAndScopedDown`** (AC30). Load `ledger-sonnet-medium-short-partial.jsonl`, score as one config, and assert:
   - `len(runs) == 8`;
   - the PR-coverage vector `[len(r.pr_ids) for r in runs] == [5, 5, 5, 5, 5, 3, 3, 1]`;
   - `[r.complete for r in runs] == [True, True, True, True, True, False, False, False]`;
   - the **whole table in one comparison** as a list of tuples `(prs, entries_in_scope, findings, accepted_hits, misses, gap_candidates, recall, precision)`:

     ```python
     [
         (5, 42, 6, 2, 40, 4, "0.048", "1.000"),
         (5, 42, 9, 1, 41, 8, "0.024", "1.000"),
         (5, 42, 9, 3, 39, 6, "0.071", "1.000"),
         (5, 42, 5, 0, 42, 5, "0.000", "n/a"),
         (5, 42, 1, 0, 42, 1, "0.000", "n/a"),
         (3, 24, 1, 0, 24, 1, "0.000", "n/a"),
         (3, 24, 1, 0, 24, 1, "0.000", "n/a"),
         (1,  1, 0, 0,  1, 0, "0.000", "n/a"),
     ]
     ```

   Add an inline comment: the `entries_in_scope` column is the discriminator — an implementation that omits partial handling charges runs 6, 7 and 8 the full 42 and fails here. Run 8 covers `tts-mcp#20` alone and scopes to that PR's single entry.

5. **`TestAllUnreviewedGoldenSetScoresWithoutDividing`** (AC12, scoring half). Deepcopy the golden set, set **every** one of the 42 entries to `unreviewed`, score the baseline slice, and assert exception-free completion with `accepted_in_scope == 0`, `accepted_hits == 0`, `misses == 0`, `matched_rejected == 0`, `gap_candidates == ()`, `excluded_unreviewed == 42`, `recall == "n/a"`, `precision == "n/a"`. Make the `score_config` call **outside any `try`**, so a `ZeroDivisionError` on either denominator fails the test rather than being swallowed. Assert both ratios against the literal `"n/a"` **and** against `R.RATIO_NA`. The report-rendering half of AC12 (the `## Runs` table carrying `n/a` in both ratio columns) is prompt 3's; do not render anything here.

6. **`TestRunnerVersionSetIsCollectedNotSampled`**. Deepcopy the baseline slice, rewrite **one** row's `runner_version` to `"2"`, score, and assert `runner_versions == ("1", "2")`. All 66 real rows carry `"1"`, so this synthetic mutation is the only way to reach the branch, and `rows[0]["runner_version"]` would otherwise satisfy every real check forever.

7. **`TestDefensiveGuardsAreReachable`**. Requirement 7 below specifies three defensive branches; each gets a case, because an unasserted branch is the same family of hole as the `runner_version` set:
   - **missing `duration_seconds`**: `copy.deepcopy` the baseline slice, `del` the key from the `quant#109` row, score, and assert the run completes without raising and `wall_time_seconds == round(2533.923 - 268.299) == 2266` — that row contributes `0.0`. Assert the corresponding `PrBreakdown.duration_seconds` is `0`.
   - **missing `started_at` on every row**: `copy.deepcopy` the baseline slice, `del` `started_at` from **all five** rows, score, and assert `span_start == ""` and `span_end == ""`, **and** that the whole AC4 per-PR table and `wall_time_seconds == 2534` are **unchanged** — reuse test 1's expected-table constant rather than re-typing it. Spans are display data; no number may move.
   - **empty input**: `self.assertEqual(R.chunk_runs([]), [])`.

## 7. Error paths

- A row whose `duration_seconds` is missing or `None` contributes `0.0` to the wall-time sum rather than raising. The ledger is machine-written and every row carries the field; this is a guard, not a feature, and gets no flag.
- A row whose `started_at` is missing contributes nothing to the span; if **no** row in a run carries one, `span_start` and `span_end` are the empty string. No scoring number depends on either.
- `chunk_runs([])` returns `[]`, and `score_config` with zero rows is never called — prompt 4 filters empty configurations out before calling, and a configuration with no surviving rows gets **no page at all**. Do not invent an empty-`ConfigScore` shape here.
- A row missing `pr_id` is a corrupt ledger and must not be silently dropped: the loud abort belongs to prompt 4's ledger loader with the `CORRUPT LEDGER` literal. Do not add a second, quieter failure mode here.

## 8. Out of scope for this prompt — do not implement

Report rendering, the `## Configuration` / `## Runs` / `## Per-PR` / `## Gap-triage candidates` sections, `config_hash` validation, atomic page writes, `--golden` / `--score` / `--reports-dir` CLI wiring, the per-row `prs_version` skip, `load_golden`, ledger loading, and the README/CHANGELOG updates belong to prompts 3-5.
</requirements>

<constraints>
- Python 3 **standard library only**. No third-party imports, no new top-level files outside `bench/`.
- **`bench/golden.json` and everything under `bench/testdata/` are frozen inputs.** `git diff --exit-code bench/golden.json bench/testdata/` must exit 0. On a digest mismatch, stop and report `status: failed`; never regenerate a fixture.
- **Do NOT change `commands/pr-review.md` or anything under `rules/`.** Either moves `rules_commands_hash` and orphans every existing ledger row.
- **Do NOT touch the harvest layer** or its tests. **Do NOT fix D8.**
- **The ledger is append-only and read-only to the scorer.** No row is rewritten, deduplicated, reordered or deleted on disk; the in-test deepcopy mutations of AC6 and the `runner_version` case operate on in-memory copies only.
- **Do NOT make the run-chunking rule configurable** and do not add a timestamp-based fallback, hybrid or heuristic. No flag, no keyword argument, no environment variable.
- **Do NOT re-derive the match rule** or change anything prompt 1 shipped.
- **No test function may be deleted and no assertion relaxed** in `bench/test_config.py`, `bench/test_resolve.py` or `bench/test_review.py`. Floors: 63 / 46 / 265.
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
SHA
echo "digest check exit=$? (expect 0)"
git diff --exit-code bench/golden.json bench/testdata/ ; echo "frozen-input diff exit=$? (expect 0)"

# New surface exists
grep -n 'def chunk_runs\|def score_run\|def score_config\|class RunScore\|class PrBreakdown\|class ConfigScore' bench/run.py

# Chunking must not read the clock
sed -n '/^def chunk_runs/,/^def /p' bench/run.py | grep -c 'started_at'   # expect 0

# Replay AC5 and AC30 against the real slices
python3 - <<'EOF'
import sys, json, pathlib
sys.path.insert(0, 'bench')
import run as R
golden = json.loads(pathlib.Path('bench/golden.json').read_text())
def rows(name):
    p = pathlib.Path('bench/testdata') / name
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

cfg = R.score_config(rows=rows('ledger-sonnet-medium-short-4runs.jsonl'), golden=golden)
print('runs', len(cfg.runs), 'runner_versions', cfg.runner_versions)
for r in cfg.runs:
    s = r.score
    print(r.index, len(r.pr_ids), r.complete, s.entries_in_scope, s.findings,
          s.accepted_hits, s.misses, s.matched_rejected, len(s.gap_candidates), s.recall, s.precision)

cfg = R.score_config(rows=rows('ledger-sonnet-medium-short-partial.jsonl'), golden=golden)
print('runs', len(cfg.runs), 'coverage', [len(r.pr_ids) for r in cfg.runs],
      'complete', [r.complete for r in cfg.runs])
for r in cfg.runs:
    s = r.score
    print(r.index, len(r.pr_ids), s.entries_in_scope, s.findings, s.accepted_hits,
          s.misses, len(s.gap_candidates), s.recall, s.precision)

cfg = R.score_config(rows=rows('ledger-baseline-opus-xhigh-full.jsonl'), golden=golden)
run = cfg.runs[0]
print('wall', run.wall_time_seconds, 'golden baseline wall', golden['baseline']['wall_time_seconds'])
for p in run.per_pr:
    print(p.pr_id, p.entries_in_scope, p.hits, p.misses, p.findings, p.gap_candidates, p.duration_seconds)
EOF

# Assertion floors untouched (AC24)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 265

grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$? (expect 1)"
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
make precommit
```

Expected: the digest check exits 0 with no `FAILED` line and the frozen-input diff is empty; the six new symbols exist; the `started_at` grep inside `chunk_runs` prints `0`; the four-run replay prints 4 runs, all complete with 5 PRs and 42 in scope, and the rows `3 2 40 0 1 0.048 1.000`, `2 1 41 0 1 0.024 1.000`, `5 2 40 0 3 0.048 1.000`, `6 0 42 0 6 0.000 n/a`; the partial replay prints 8 runs with coverage `[5, 5, 5, 5, 5, 3, 3, 1]`, complete `[True × 5, False × 3]`, in-scope `42 × 5, 24, 24, 1` and AC30's numbers; the baseline replay prints wall `2534` equal to the golden baseline value and AC4's five per-PR rows; the three assertion counts are at least 63, 46 and 265; the personal-path grep exits 1; the unittest run reports `OK` with `Ran N tests`, `N > 103`, listing the per-PR-table, four-run-chunking, timestamp-independence, partial-run, all-unreviewed and runner-version-set tests by name; `make precommit` exits 0.
</verification>
