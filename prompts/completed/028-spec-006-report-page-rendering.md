---
status: completed
spec: [006-bench-golden-scoring-and-report]
summary: 'Implemented bench report rendering: validate_config_hash, report_path, coding_plugin_version, render_report, write_report in bench/run.py, plus 10 test classes in bench/test_score.py covering AC12/13/14/15/21/31'
execution_id: coding-exec-028-spec-006-report-page-rendering
dark-factory-version: v0.192.9
created: "2026-08-09T11:32:00Z"
queued: "2026-08-09T10:16:50Z"
started: "2026-08-09T10:50:01Z"
completed: "2026-08-09T10:59:14Z"
---

<summary>
- Every scored configuration now gets a durable page in the repository recording what it was, what it found, what it missed and how long it took
- The page states the configuration's full identity, so a number can never be read without knowing which model, effort, mode and rule set produced it
- Two honest caveats about what the ratios actually mean are printed on every page, because a headline ratio read without them is worse than no ratio
- Findings the curated set does not describe get their own section, quoted in full, under a sentence saying plainly that they are not counted against the configuration
- The page carries no generation timestamp, so re-scoring unchanged data produces a byte-identical file and any diff means the data changed
- Pages are written whole and atomically, never appended to, so a crash mid-write cannot leave a half-page behind
- The only value from the recorded data that ever becomes a filename is checked against a strict shape first, so no recorded row can direct a write outside the reports folder
- The tables are read back out of the rendered page and compared against the computed numbers, so a hardcoded template cannot pass
</summary>

<objective>
Render a scored configuration into `bench/reports/<config_hash>.md` with the four frozen sections, the pinned Configuration block, both mandated ratio caveats, tables rendered from the result object, the gap-triage section, `config_hash` validation, atomic per-file writes and no generation timestamp — so re-scoring an unchanged ledger produces a byte-identical page.
</objective>

<context>
Read `CLAUDE.md` for project conventions — Python 3 standard library only, no personal paths, never commit (dark-factory handles git).

Read `specs/in-progress/006-bench-golden-scoring-and-report.md`. This prompt is **prompt 3 of 5** and satisfies **Desired Behavior 6** and **AC14, AC15, AC21, AC31**, plus the rendering half of **AC12**. Load-bearing sections: `## Desired Behavior` items 4 (the two mandated caveats) and 6 (the page's exact contents), `## Acceptance Criteria` AC12/AC14/AC15/AC21/AC31, `## Security / Abuse Cases` in full, and the `## Failure Modes` rows for a crash mid-write, an unreadable `.claude-plugin/plugin.json` and a megabyte-sized finding body.

**This prompt depends on prompts 1 and 2 of this spec having landed.** Verify before you start:

```bash
grep -n 'def score_findings\|def score_config\|def chunk_runs\|class ConfigScore\|class RunScore\|class PrBreakdown\|INVALID_CONFIG_HASH_MARKER' bench/run.py
```

If any of the seven is absent, stop and report `status: failed` with the message `"prompts 1-2 of spec 006 not yet landed"`. Do not implement them here.

Read `bench/run.py` — `ConfigScore`, `RunScore`, `PrBreakdown`, `ScoreResult`, `score_config`, `atomic_write_bytes` (line ~453: writes via a same-directory `NamedTemporaryFile` then `os.replace`, which is exactly the write-then-rename the spec's Failure Modes table requires — reuse it, do not write a second one), `BenchError`, `assert_under`, `REPO_ROOT`, `BENCH_DIR`, and the marker constants prompt 1 added.

Read `.claude-plugin/plugin.json`. Its `version` is a bare semver **without** a leading `v` and **moves with every release** — read it at test time, never hardcode it. `bench/golden.json`'s `baseline.coding_version` is frozen at `v0.35.6` — **with** a `v`. When the two happen to agree on the numeric part, the bare form is a substring of the `v`-prefixed one, which is a trap: a lazy renderer that prints only the golden value would satisfy a naive `in` check on the coding-version line. Requirement 7 below pins both lines by exact line prefix for that reason.

Read `bench/golden.json`'s top-level `version` (`golden-dev-1`), `prs_version` (`dev-1`) and `baseline` block.

Read `bench/test_score.py` (prompts 1-2) for the `load_golden` / `load_slice` helpers and the established style. Extend that file.

Read `docs/dod.md` for the repository's Definition of Done.

**Finding bodies are single-line by construction.** `_normalize_body` in `bench/run.py` collapses every item's lines with `re.sub(r"\s+", " ", body).strip()`, so no `body` in any ledger row contains a newline — verified across all 95 findings in the four committed slices. Rendering a body verbatim on its own line therefore cannot inject a `^## ` heading into the page, which is what keeps AC15's section-order grep meaningful. Rely on that guarantee and document it inline; do not re-wrap, truncate or escape a body.
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
f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02  bench/testdata/ledger-sonnet-medium-short-4runs.jsonl
165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7  bench/testdata/ledger-sonnet-medium-short-partial.jsonl
SHA
echo "digest check exit=$? (expect 0)"
```

A `FAILED` line or a non-zero exit → stop and report `status: failed`. **Never regenerate a fixture.**

## 2. Create the tracked reports directory

Create `bench/reports/` with a `.keep` file (empty, or a one-line comment). **Do not add a `.gitignore` entry for it and do not modify `.gitignore` at all** — `bench/results/` and `bench/.cache/` stay ignored, `bench/reports/` is one of the spec's two named committed-output exceptions. Verify with `git check-ignore -q bench/reports; echo $?` → must print `1`.

## 3. Validate the one ledger value that becomes a filename

```python
CONFIG_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_config_hash(value) -> str:
    """Return value when it is 64 lowercase hex characters; raise BenchError otherwise."""
```

Raise `BenchError(f"{INVALID_CONFIG_HASH_MARKER}: {value!r}")` when `value` is not a `str` or does not fully match `CONFIG_HASH_RE`. Use `.fullmatch`, or keep the `^...$` anchors and use `.match` — but note `$` also matches before a trailing newline in Python, so `re.fullmatch` is the safer form; whichever you pick, a value containing a newline must be rejected.

```python
def report_path(reports_dir: pathlib.Path, config_hash: str) -> pathlib.Path:
    """<reports_dir>/<64-hex config_hash>.md, with the hash validated first."""
```

Call `validate_config_hash` first, then join. Use the **full 64 characters** — a truncated filename reintroduces the identity ambiguity the hash exists to remove. Additionally pass the result through the existing `assert_under(path, reports_dir.resolve())` as a second, independent gate.

Uses `path`, `rule_id` and `body` from a finding for **nothing but rendering**: never opened, stat-ed, globbed, joined onto a filesystem root, or passed to a subprocess. A finding citing `../../etc/passwd:1` produces a table cell or a quoted block containing that string and no filesystem access.

## 4. Read the plugin version

```python
def coding_plugin_version(coding_repo: pathlib.Path) -> str:
    """The `version` from <coding_repo>/.claude-plugin/plugin.json, or 'unavailable'."""
```

Return the literal string `"unavailable"` when the file is missing, unreadable, not valid JSON, or has no `version` key — the page renders and scoring does **not** abort (spec Failure Modes, last row). Catch `OSError`, `json.JSONDecodeError` / `ValueError` and `KeyError` only; do not swallow every exception. Return the value verbatim, with no `v` prefix added and none stripped.

## 5. Render the page

```python
def render_report(*, config_score: ConfigScore, golden: dict, coding_version: str) -> str:
    """Render one configuration's scored result as the full page text."""
```

The page is a **total function** of `config_score`, `golden` and `coding_version`. It is rewritten wholesale on every scoring, never appended to, and contains **no generation timestamp**, no `Generated at`, no `Generated on`, no `Generated:`, no `Report date`, no `datetime.now()`, no `time.time()`, no host name, no user name, no absolute path. Re-scoring an unchanged ledger must produce a byte-identical file, so a noisy diff always means the data changed.

Structure, in exactly this order. The four `## ` headings are **frozen invariants** — the literal text, the level and the order:

```markdown
# <config_hash>

## Configuration

- model: <model>
- effort: <effort>
- mode: <mode>
- config_hash: <config_hash>
- rules_commands_hash: <rules_commands_hash>
- prs_version: <prs_version>
- coding version: <coding_version>
- golden baseline coding version: <golden["baseline"]["coding_version"]>
- golden version: <golden["version"]>
- runner_version: <", ".join(config_score.runner_versions)>
- rows skipped: <rows_skipped>
- cost: not recorded — the ledger carries no cost field.

<precision caveat paragraph>

<recall caveat paragraph>

## Runs

| run | span | PRs | complete | golden in scope | findings | hits | misses | matched rejected | gap candidates | recall | precision | wall time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | <span_start> … <span_end> | 5 | complete | 42 | 42 | 42 | 0 | 0 | 0 | 1.000 | 1.000 | 2534 |

## Per-PR

| run | pr_id | golden in scope | hits | misses | findings | gap candidates | duration (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | tts-mcp#20 | 1 | 1 | 0 | 1 | 0 | 420 |

## Gap-triage candidates

<the literal sentence — see below>

### run <k> — <pr_id> — <path>:<line>

<body, verbatim, on its own line>
```

Rules that are not negotiable:

- The `## Configuration` block carries **each of these twelve on its own line**: `model`, `effort`, `mode`, `config_hash`, `rules_commands_hash`, `prs_version`, `coding version`, `golden baseline coding version`, `golden version`, `runner_version`, `rows skipped`, and the cost line stating cost is **not recorded**. Do not add token counting or cost estimation — the ledger carries no cost field and the page states so rather than estimating.
- The `runner_version` line lists the **set** of distinct values present among the scored rows, comma-separated in sorted order — never the first row's value. Its whole purpose is to make a ledger mixing pre- and post-005 harvest output visible rather than silently averaged.
- The **precision caveat** paragraph must contain the literal substring `not yet a result`. Write it in the page's own words, for example: *"`golden-dev-1` currently carries zero `rejected` entries, so precision cannot be lost by any configuration. A precision of `1.000` is a property of the golden set's adjudication state and is not yet a result."*
- The **recall caveat** paragraph must contain the literal substring `36 of the 42 signatures` and the phrase `embed a line reference`. For example: *"36 of the 42 signatures embed a line reference, so a re-report of the same issue at a different line does not match and is surfaced as a gap-triage candidate rather than a hit. On this golden set, `recall` measures whether a configuration cited the same line, not whether it found the issue."*
- Both caveats are printed on **every** page, for every configuration, unconditionally. There is no flag that suppresses them.
- The `## Gap-triage candidates` section opens with a sentence containing the literal substring `not a precision failure`, e.g. *"These findings matched no golden entry. They are **not a precision failure** — the golden set is a bootstrap from one strong-model run, and a finding it does not describe is evidence the set is incomplete."* The sentence is present even when the list is empty; in that case follow it with `None.`
- Each gap candidate is rendered as an `### ` sub-heading naming its run, `pr_id`, `path` and `line`, followed by a blank line and the finding's `body` **verbatim on its own line**. Use `###`, never `##`, so the section-order grep of AC15 stays meaningful. A `line` of `None` renders as the path with no `:` suffix.
- The `golden in scope` column renders `ScoreResult.entries_in_scope`, **never** `accepted_in_scope`. The two diverge exactly in the all-`unreviewed` case, where `entries_in_scope` is 42 and `accepted_in_scope` is 0.
- Table cells: render integers as plain integers, ratios as the already-formatted strings from `ScoreResult` (`1.000`, `0.048`, `n/a` — never re-format, never re-round), and `complete` as the literal word `complete` or `partial`. Escape a literal `|` as `\|` in any **string** cell (`pr_id`, span) so a pathological value cannot add a column. Bodies never appear in a table. No fixture contains a pipe in a table cell, so this branch is unreachable from real data — the test-side `parse_table` helper must therefore split on a **negative lookbehind** (`re.split(r'(?<!\\)\|', row)`) and unescape `\|` back to `|`, or a future escaped cell would be mis-split by a naive `row.split('|')`.
- Rendering is **linear in output size**. Build the page with a list of lines and one `"\n".join(...)`; no quadratic string concatenation, no regex over a `body`, no unbounded backtracking construct anywhere in the render path.
- Run rows appear in run order, per-PR rows in run order then the run's `pr_ids` order, gap candidates in run order then the run's `gap_candidates` order. Every ordering is fully determined by the result object — no `set` iteration, no `dict` ordering assumption beyond insertion order, no sorting by a value that can tie.

## 6. Write the page atomically

```python
def write_report(*, reports_dir: pathlib.Path, config_score: ConfigScore,
                 golden: dict, coding_version: str) -> pathlib.Path:
    """Render and atomically write one configuration's page.  Returns the path."""
```

`reports_dir.mkdir(parents=True, exist_ok=True)`, then `report_path(...)`, then `atomic_write_bytes(path, text.encode("utf-8"))`. Reuse the existing `atomic_write_bytes` — it already does write-to-temp-in-same-directory, `flush`, `fsync`, `os.replace`, and unlinks the temp on failure. Do not add a second atomic-write helper and do not write with `path.write_text`.

The function writes **only** the one page file. It runs no `git` command, opens no ledger, re-harvests nothing, reopens no raw capture, and mutates no golden entry.

## 7. Extend `bench/test_score.py`

Do not touch `bench/test_config.py`, `bench/test_resolve.py` or `bench/test_review.py` (floors 63 / 46 / 265, AC24).

Add a test-local table read-back helper — the whole point of AC31 is that the tables are parsed **back out of the rendered text** and compared against the result object, so a hardcoded template fails:

```python
def parse_table(page_text, heading):
    """Return the rows of the markdown table under `heading` as lists of cell strings."""
```

Locate the heading line, take following lines beginning with `|` until a non-`|` line, split each row with `re.split(r'(?<!\\\\)\\|', row)` (a negative lookbehind, so an escaped `\|` inside a cell does not add a column), unescape `\|` back to `|` in each cell, strip each cell, and drop the header and `---` separator rows.

Test cases:

1. **`TestReportPageLocationAndSections`** (AC15, structure). Score the baseline slice, `write_report` into a `tempfile.TemporaryDirectory()`. Assert the written path is `<tmp>/cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md` — the full 64-character hash. Assert the `## ` headings in the page are exactly `["## Configuration", "## Runs", "## Per-PR", "## Gap-triage candidates"]`, in that order, by collecting every line matching `^## `.

2. **`TestConfigurationBlockPinsBothVersions`** (AC15, the trap). Assert every one of the twelve Configuration fields appears on its own line. Locate a field's line by `line.startswith("- coding version: ")` and `line.startswith("- golden baseline coding version: ")` — **exact prefix at start of line**, because `coding version:` is a substring of `golden baseline coding version:` and an `in` test on the page would match the wrong line. Then assert:
   - the `coding version` line's value equals the `version` the test itself reads out of `.claude-plugin/plugin.json`, and is **not** the literal `unavailable` (an unconditional `unavailable` is the laziest implementation and must fail);
   - the `golden baseline coding version` line's value equals `golden["baseline"]["coding_version"]` — read from the file, and additionally asserted to start with `v`, so the two lines cannot be the same value;
   - the `golden version` line's value equals `golden["version"]` (`golden-dev-1`);
   - the `rows skipped` line reads `0` for this fixture;
   - the cost line states cost is not recorded.

   Three fallback cases, because a blanket `except Exception` passes on only the first: `coding_plugin_version` returns `"unavailable"` for (a) a temp directory with **no** `.claude-plugin/plugin.json`, (b) one whose `plugin.json` contains **invalid JSON** (`{not json`), and (c) one whose `plugin.json` is valid JSON with **no `version` key**. In case (a) additionally assert `render_report` still produces a full page with all four sections.

3. **`TestRunnerVersionLineListsTheWholeSet`** (AC15). Deepcopy the baseline slice, rewrite **one** row's `runner_version` to `"2"`, score and render. Assert the `runner_version` line names **both** `1` and `2`. Inline comment: all 66 rows on disk carry `"1"`, so no real fixture reaches this branch and `rows[0]["runner_version"]` would satisfy every other check forever, in the one field whose purpose is to expose a mixed-harvest ledger.

4. **`TestPerPrTableIsRenderedFromTheResult`** (AC15). Read the `## Per-PR` table back out of the baseline page with `parse_table`. Assert it contains all five `pr_id` values, and that each row's `golden in scope`, `hits`, `misses`, `findings`, `gap candidates` and `duration (s)` cells equal AC4's numbers **and** equal the corresponding `PrBreakdown` fields on the scorer's result object. Compare against the result object, not only against literals — that is what makes a hardcoded template fail.

5. **`TestRunsTableIsRenderedFromTheResult`** (AC31), two cases:
   - Score `ledger-sonnet-medium-short-4runs.jsonl`, render, `parse_table` the `## Runs` table, and compare **every cell of all four rows** against AC5's table — findings, hits, misses, matched rejected, gap candidates, recall, precision — plus the PR-coverage and span columns against `RunScore.pr_ids` and `span_start` / `span_end`. Assert run 4's precision cell is the literal `n/a`.
   - Same read-back over `ledger-sonnet-medium-short-partial.jsonl` against AC30's table, including the `golden in scope`, PR-coverage and `complete`/`partial` columns; assert rows 1-5 read `complete` and rows 6-8 read `partial`.

6. **`TestGapTriageSectionCarriesItsSentenceAndBodies`** (AC13/AC15 rendering half). Over the four-run fixture, assert the page contains the literal `not a precision failure`. Assert `len(runs[2].score.gap_candidates) == 3` **before** the body loop — otherwise an empty candidate list makes the loop vacuous and the test green. Then assert each of run 3's three gap-candidate bodies appears in the page as a **contiguous verbatim substring**. Assert each candidate's `pr_id`, `path` and `line` appear in its `### ` heading. Also assert the baseline page — which has zero gap candidates — still contains the section heading and the sentence.

7. **`TestBothCaveatsAppearOnEveryPage`** (AC15). Over both the baseline and the four-run pages, assert **three separate literals**, never an `or`: `not yet a result` appears; case-insensitively `36 of the 42 signatures` appears; case-insensitively `embed a line reference` appears. An `or` lets a page drop `36 of the 42 signatures` — the load-bearing measured number — and still pass. Additionally assert each caveat is a real sentence rather than a keyword drop: the paragraph containing `not yet a result` also contains `rejected`, and the paragraph containing `embed a line reference` also contains `gap-triage`.

8. **`TestScoringIsDeterministicAndCarriesNoWallClock`** (AC14), three writes:
   - write the same fixture into **two different** temporary directories and assert the two files' bytes are equal (`filecmp.cmp(a, b, shallow=False)` is True);
   - write a **third** time into the **same** directory as the first, over the existing file, and assert its bytes are still equal to the first. Two different directories cannot distinguish a rewrite from an append — an appending implementation writes identical bytes to each fresh path — so the same-directory rewrite is what pins "rewritten wholesale, never appended to".

   Assert a case-insensitive regex search for `generated (at|on)|generated:|report date` over the page finds nothing.

   Pin the three-decimal rendering **out of the rendered page**: score the four-run fixture, `parse_table` its `## Runs` table, take run 1's `recall` cell and assert it equals both `"0.048"` and `format(2 / 42, ".3f")`. A bare `self.assertEqual(format(2/42, ".3f"), "0.048")` must **not** appear — it asserts a property of CPython, not of `render_report`, and passes with no implementation at all.

9. **`TestAllUnreviewedGoldenSetStillRenders`** (AC12, rendering half). Set all 42 entries to `unreviewed` in a deepcopy, score the baseline slice, render, and assert the page has all four sections and the `## Runs` table's recall **and** precision cells both read the literal `n/a`. No `ZeroDivisionError`.

10. **`TestConfigHashIsGatedBeforeBecomingAFilename`** (AC21). Three cases — `"../../etc/passwd"`, `""`, and a 64-character string containing a `/` (e.g. `"a" * 32 + "/" + "b" * 31`) — each asserting `validate_config_hash` raises `BenchError` whose message contains the literal `INVALID CONFIG HASH`, and that `report_path` raises before touching the filesystem. Then: build the bad-hash variants with `dataclasses.replace(config_score, config_hash=bad)` — `ConfigScore` is `frozen=True`, so `copy.deepcopy(cfg)` followed by `cfg.config_hash = bad` raises `FrozenInstanceError` and the test fails against a correct implementation. Lay the temp tree out as `<tmproot>/marker.txt` and `<tmproot>/a/b/reports`, with the reports directory **two levels below** the temp root: with `reports_dir` directly under `<tmproot>`, a `../../etc/passwd` traversal lands outside the swept tree entirely and the check passes for an implementation with no validation at all. Attempt `write_report` with each bad hash, then walk `<tmproot>` with `os.walk` and assert no path outside `<tmproot>/a/b/reports` has an `st_mtime` newer than the marker. Add a fourth case asserting an **uppercase** 64-hex string is rejected (the rule is 64 *lowercase* hex).

## 8. Error paths

- A `config_hash` failing validation raises `BenchError` carrying `INVALID CONFIG HASH` and the offending value. `write_report` does **not** create the file, does not create a partial file, and does not `mkdir` a directory derived from the bad value. Whether other configurations continue to be scored is prompt 4's decision; here the function simply raises.
- `.claude-plugin/plugin.json` unreadable → `coding_plugin_version` returns `"unavailable"` and rendering proceeds. Scoring never aborts on it.
- A crash between write and rename cannot be observed because `atomic_write_bytes` renames into place; per the spec this carries no acceptance criterion deliberately and needs no fault-injection seam.
- A body of a megabyte or a run with thousands of gap candidates renders linearly. Do not truncate a body — `REJECTION_EXCERPT_BYTES` is the harvest layer's stderr bound and has nothing to do with the page.

## 9. Out of scope for this prompt — do not implement

`--golden` / `--score` / `--reports-dir` argument parsing, score-only mode, `load_golden`, ledger loading and its `EMPTY LEDGER` / `CORRUPT LEDGER` aborts, the per-row `prs_version` skip and its `PRS VERSION SKIP` lines, the decision to continue scoring other configurations after an `INVALID CONFIG HASH`, and the README/CHANGELOG updates all belong to prompts 4 and 5.
</requirements>

<constraints>
- Python 3 **standard library only**. No third-party imports, no new top-level files outside `bench/`.
- **`bench/golden.json` and everything under `bench/testdata/` are frozen inputs.** `git diff --exit-code bench/golden.json bench/testdata/` must exit 0.
- **Do NOT modify `.gitignore`.** `bench/reports/` must stay un-ignored; `bench/results/` and `bench/.cache/` stay ignored.
- **Do NOT change `commands/pr-review.md` or anything under `rules/`.**
- **Do NOT touch the harvest layer** or its tests. **Do NOT fix D8.**
- **The report location, filename form, section names, three-decimal ratio rendering, the `n/a` literal and the absence of a generation timestamp are frozen invariants** — not configurable, not flagged.
- **Do NOT add token counting or cost capture.** The page states cost is not recorded.
- **No generation timestamp, no wall clock, no host or user name, no absolute path** in the rendered page.
- **Values read from the ledger are data, never paths.** Only `config_hash` reaches a filename, gated by the 64-lowercase-hex check.
- **No test function may be deleted and no assertion relaxed** in `bench/test_config.py`, `bench/test_resolve.py`, `bench/test_review.py`. Floors: 63 / 46 / 265.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file, including the rendered page.
- **`docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" is satisfied by prompt 5 of this spec (AC23), not here.** Do not add a CHANGELOG entry in this prompt. Spec 002's precedent: a mid-chain prompt that described only its own slice left the release classifier cutting a patch where a minor was due, which is why the CHANGELOG lands once, last, describing what all five prompts shipped.
- Do NOT commit — dark-factory handles git.
- Existing tests must still pass.
</constraints>

<verification>
```bash
# Frozen inputs untouched, reports dir tracked
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
git check-ignore -q bench/reports ; echo "check-ignore exit=$? (expect 1 — NOT ignored)"
git diff -- .gitignore ; echo "gitignore diff must be empty"

# New surface
grep -n 'def validate_config_hash\|def report_path\|def coding_plugin_version\|def render_report\|def write_report\|CONFIG_HASH_RE' bench/run.py
grep -n 'def atomic_write_bytes' bench/run.py   # exactly one — no second helper

# No wall clock in the render path
sed -n '/^def render_report/,/^def write_report/p' bench/run.py | grep -inE 'datetime|time\.time|now\(|getpass|socket|gethostname' ; echo "wall-clock grep exit=$? (expect 1)"

# Render the baseline page and inspect it
python3 - <<'EOF'
import sys, json, pathlib, tempfile
sys.path.insert(0, 'bench')
import run as R
golden = json.loads(pathlib.Path('bench/golden.json').read_text())
rows = [json.loads(l) for l in pathlib.Path('bench/testdata/ledger-baseline-opus-xhigh-full.jsonl').read_text().splitlines() if l.strip()]
cfg = R.score_config(rows=rows, golden=golden)
ver = R.coding_plugin_version(pathlib.Path('.'))
with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
    pa = R.write_report(reports_dir=pathlib.Path(a), config_score=cfg, golden=golden, coding_version=ver)
    pb = R.write_report(reports_dir=pathlib.Path(b), config_score=cfg, golden=golden, coding_version=ver)
    print('filename', pa.name)
    print('identical', pa.read_bytes() == pb.read_bytes())
    text = pa.read_text()
print([l for l in text.splitlines() if l.startswith('## ')])
plugin_version = json.loads(pathlib.Path('.claude-plugin/plugin.json').read_text())['version']
cv = [l for l in text.splitlines() if l.startswith('- coding version: ')]
gb = [l for l in text.splitlines() if l.startswith('- golden baseline coding version: ')]
print('coding version line:', cv, '(plugin.json says', plugin_version + ')')
print('golden baseline line:', gb)
assert cv and cv[0] == f'- coding version: {plugin_version}', cv
assert 'unavailable' not in cv[0], cv
assert gb and gb[0].endswith(golden['baseline']['coding_version']), gb
print('runner_version line:', [l for l in text.splitlines() if l.startswith('- runner_version: ')])
print('rows skipped line:', [l for l in text.splitlines() if l.startswith('- rows skipped: ')])
print('not a precision failure:', text.count('not a precision failure'))
print('not yet a result:', text.count('not yet a result'))
print('line-reference caveat:', text.count('36 of the 42 signatures') + text.lower().count('embed a line reference'))
import re
print('wall-clock hits:', len(re.findall(r'(?i)generated (at|on)|generated:|report date', text)))
EOF

# Config-hash gate
python3 - <<'EOF'
import sys, pathlib
sys.path.insert(0, 'bench')
import run as R
for bad in ['../../etc/passwd', '', 'a'*32 + '/' + 'b'*31, 'A'*64]:
    try:
        R.report_path(pathlib.Path('/tmp/does-not-exist'), bad)
        print('NOT REJECTED:', repr(bad))
    except R.BenchError as err:
        print('rejected:', repr(bad), '->', 'INVALID CONFIG HASH' in str(err))
EOF

# Assertion floors untouched (AC24)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 265

grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$? (expect 1)"
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
make precommit
```

Expected: the digest check exits 0 with no `FAILED` line and the frozen-input diff is empty; `git check-ignore` exits 1 and the `.gitignore` diff is empty; the six new symbols exist and `atomic_write_bytes` is defined exactly once; the wall-clock grep in the render path exits 1; the render replay prints filename `cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md`, `identical True`, the four headings in order `['## Configuration', '## Runs', '## Per-PR', '## Gap-triage candidates']`, a `coding version` line whose value equals the `version` currently in `.claude-plugin/plugin.json` (read at run time — it moves with every release) and is not `unavailable`, a distinct `golden baseline coding version` line reading the golden set's frozen `v0.35.6`, a `runner_version` line reading `1`, `rows skipped: 0`, at least one occurrence each of `not a precision failure`, `not yet a result` and the line-reference caveat, and zero wall-clock hits; all four bad config hashes are rejected with `INVALID CONFIG HASH`; the three assertion counts are at least 63, 46 and 265; the personal-path grep exits 1; the unittest run reports `OK` with `Ran N tests`, `N > 103`, listing the report-location, configuration-block, runner-version-set, per-PR-table, runs-table, gap-triage, caveat, determinism, all-unreviewed-render and config-hash-validation tests by name; `make precommit` exits 0.
</verification>
