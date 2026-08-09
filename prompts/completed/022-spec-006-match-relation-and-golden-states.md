---
status: completed
spec: [006-bench-golden-scoring-and-report]
execution_id: coding-exec-022-spec-006-match-relation-and-golden-states
dark-factory-version: v0.192.9
created: "2026-08-09T11:30:00Z"
queued: "2026-08-09T10:16:50Z"
started: "2026-08-09T10:17:54Z"
completed: "2026-08-09T10:46:48Z"
---

<summary>
- The benchmark gains the ability to compare what a review actually found against the curated list of what it should have found
- A finding and a curated entry are declared the same issue by one settled rule: the rule name when both sides carry one, otherwise the file plus every keyword of the entry appearing in the finding's text
- Line numbers are deliberately ignored when deciding whether two reports describe the same issue
- The three curation states get their meaning: something expected but not found costs recall, a known false alarm that reappears costs precision, and something not yet adjudicated counts on neither side
- A finding that matches nothing curated is recorded as a gap-triage candidate — evidence that the curated list is incomplete, never as a false alarm
- One finding can satisfy two curated entries at once; nothing is paired off one-to-one
- This prompt adds a pure calculation with no files written, no command-line surface and no report page — those are the next three prompts
- Every number it produces is checked against real recorded benchmark data, not against data written for the test
</summary>

<objective>
Implement the golden-set match relation and the accepted / rejected / unreviewed / gap-triage scoring semantics in `bench/run.py` as a **pure function** over a list of golden entries and a list of findings. No file I/O, no CLI surface, no rendering. After this prompt, scoring the real baseline ledger slice against the real `bench/golden.json` reproduces the published 42/42/0/0 self-match exactly.
</objective>

<context>
Read `CLAUDE.md` for project conventions — Python 3 standard library only, no personal paths, generic examples only, never commit (dark-factory handles git).

Read `specs/in-progress/006-bench-golden-scoring-and-report.md`. This prompt is **prompt 1 of 5** in that spec's `## Suggested Decomposition` and satisfies **Desired Behaviors 2 and 3** and **AC2, AC3, AC7, AC8, AC9, AC10, AC11, AC13, AC20**. Load-bearing sections: `## Desired Behavior` items 2 and 3, `## Acceptance Criteria` AC2/AC3/AC7/AC8/AC9/AC10/AC11/AC13/AC20, the whole `## Non-goals` list, `## Constraints`, and the `## Assumptions` note that every published number was measured against the real files.

Read `bench/golden.json`. Its top-level keys are `version`, `created`, `prs_version`, `baseline`, `match_rule`, `states`, `scoring_note`, `known_corrections`, `entries`. Each of the 42 entries carries `pr_id`, `path`, `signature` (a list of strings), `rule_id` (string or `null`), `state`, `line_when_seen`, `excerpt`. All 42 entries are `state: "accepted"` on disk; exactly 4 carry a non-null `rule_id`; 38 carry `null`.

Read `bench/testdata/ledger-baseline-opus-xhigh-full.jsonl`. Each line is one ledger row with keys `base_sha`, `changed_files`, `config_hash`, `diff_range`, `duration_seconds`, `effort`, `findings`, `head_sha`, `mode`, `model`, `notes`, `parent_count`, `pr_id`, `prs_version`, `raw_output_ref`, `review_command`, `rules_commands_hash`, `runner_version`, `started_at`. Each element of `findings` carries exactly `body`, `line`, `path`, `rule_id`.

Read `bench/run.py` — in particular the module constants block (lines ~37-95), `class BenchError`, `HarvestResult`, and `build_row`. Take every signature you touch from the file, never from memory. Note that `bench/run.py` imports standard-library modules only and must continue to.

Read `bench/test_review.py` for the existing test style (`unittest.TestCase` subclasses, descriptive class names, `self.assertEqual` with a message on failure).

Read `docs/dod.md` for the repository's Definition of Done.

**The five input files are already installed and committed by the operator.** You verify them and never write them. `bench/golden.json` is a frozen input: `git diff --exit-code bench/golden.json` must exit 0 after your work.
</context>

<requirements>

## 1. Verify the five operator-installed inputs before writing any code

Run exactly this, and check the result — do not merely print digests:

```bash
# `shasum` is Perl-core and absent from many slim images; the daemon does not check
# verification exit codes, so a missing binary would read as a pass.  Verify in Python.
python3 - <<'EOF'
import hashlib, pathlib, sys
EXPECTED = {
    'bench/golden.json': '90f5b0a61ac763b6abb3991fff699a4818318f22a171f6fc4375d314da43459d',
    'bench/testdata/ledger-baseline-opus-xhigh-full.jsonl': 'af8f684b95e82577af4ac6b4a04392559ef04865ee95e7f8afdcc8f1756e86fb',
    'bench/testdata/ledger-sonnet-medium-short-4runs.jsonl': 'f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02',
    'bench/testdata/ledger-sonnet-medium-short-partial.jsonl': '165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7',
    'bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl': 'f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209',
}
bad = []
for name, want in EXPECTED.items():
    path = pathlib.Path(name)
    if not path.exists():
        bad.append(f'{name}: MISSING')
        continue
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != want:
        bad.append(f'{name}: {got} != {want}')
print('FIXTURE DIGESTS FAILED:' if bad else 'fixture digests OK')
for line in bad:
    print(' ', line)
sys.exit(1 if bad else 0)
EOF
echo "digest check exit=$?"
grep -c '' bench/golden.json bench/testdata/ledger-*.jsonl   # expect 490, 5, 20, 32, 4
```

If the digest check prints `FIXTURE DIGESTS FAILED`, exits non-zero, or a line count differs: **stop immediately and report `status: failed`** with the observed digest and count. **Never create, regenerate, synthesise, repair or edit any of these five files.** Five defects reached production in this codebase because a fixture was authored from the same mental template as the parser that consumes it; the whole value of these five files is that they predate your code.

## 2. Add the frozen literal constants

Add to the module constants block in `bench/run.py`, after the existing `UNATTRIBUTABLE_MARKER` / `REJECTION_EXCERPT_BYTES` group. These seven strings are **frozen invariants** per the spec's `## Constraints` — the literal is the contract, and every assertion in this spec and its four sibling prompts greps for the literal string, never for the symbol:

```python
# ----------------------------------------------------------------------
# Scoring — frozen marker literals (spec 006 Constraints; not configurable)
# ----------------------------------------------------------------------
GOLDEN_NOT_FOUND_MARKER = "GOLDEN SET NOT FOUND"
INVALID_GOLDEN_MARKER = "INVALID GOLDEN SET"
GOLDEN_VERSION_MISMATCH_MARKER = "GOLDEN VERSION MISMATCH"
PRS_VERSION_SKIP_MARKER = "PRS VERSION SKIP"
EMPTY_LEDGER_MARKER = "EMPTY LEDGER"
CORRUPT_LEDGER_MARKER = "CORRUPT LEDGER"
INVALID_CONFIG_HASH_MARKER = "INVALID CONFIG HASH"

STATE_ACCEPTED = "accepted"
STATE_REJECTED = "rejected"
STATE_UNREVIEWED = "unreviewed"
GOLDEN_STATES = (STATE_ACCEPTED, STATE_REJECTED, STATE_UNREVIEWED)
REQUIRED_GOLDEN_KEYS = ("entries", "match_rule", "states")
RATIO_NA = "n/a"
```

Declare all seven markers here even though only the last group is used in this prompt — prompts 3 and 4 of this spec consume `INVALID_CONFIG_HASH_MARKER`, `PRS_VERSION_SKIP_MARKER`, `EMPTY_LEDGER_MARKER`, `CORRUPT_LEDGER_MARKER`, `GOLDEN_NOT_FOUND_MARKER`, `INVALID_GOLDEN_MARKER` and `GOLDEN_VERSION_MISMATCH_MARKER`, and the spec freezes them as one set.

## 3. Implement `format_ratio`

```python
def format_ratio(numerator: int, denominator: int) -> str:
    """Render a ratio as three fixed decimals, or the literal 'n/a' on a zero denominator."""
```

Return `RATIO_NA` when `denominator == 0`. Otherwise return `format(numerator / denominator, ".3f")`. Never `round()`-then-`str()`, never an f-string with a computed precision: the spec freezes the rendering at `format(value, '.3f')` so that `2/42` renders `0.048` on every platform. A zero denominator never renders `0.000` and never raises `ZeroDivisionError`.

## 4. Implement the match relation

```python
def finding_matches_entry(entry: dict, finding: dict) -> bool:
    """True when this finding and this golden entry describe the same issue.

    rule_id exact when BOTH sides carry a non-null one; otherwise path string
    equality plus EVERY signature keyword present case-insensitively in body.
    `line` is read from neither side.
    """
```

Exact semantics, in this order:

1. `entry_rule = entry.get("rule_id")`, `finding_rule = finding.get("rule_id")`. If **both** are non-null and non-empty: return `entry_rule == finding_rule`. A rule-id disagreement is **decisive** — return `False` immediately, do **not** fall through to path + signature. This is AC8 Case A: the `github-pr-review-agent#11` / `CHANGELOG.md` finding with its `rule_id` rewritten to `made-up/other-rule` becomes a miss even though `path` still matches and the signature keyword is still in the body.
2. Otherwise (either side null): return `True` only when `entry["path"] == finding["path"]` **and** every keyword in `entry["signature"]` is a case-insensitive substring of `finding["body"]`. Use `all(k.lower() in body_lower for k in entry["signature"])` with `body_lower = (finding.get("body") or "").lower()`. Requiring **every** keyword, not any, is AC9.
3. Path comparison is whole-string equality on the full path, with **no extension gate and no dot requirement**. Do not import, reuse or imitate `PATH_LINE_RE`. That regex's dot requirement is defect D8 in the harvest layer; the spec's `## Non-goals` says D8 stays open there and AC20 requires the scorer not to inherit it — a golden entry with `path` `Dockerfile` matches a finding with `path` `Dockerfile`.
4. `line` is read from **neither** side, on **any** branch. It is display data on the report and identity nowhere (AC7).
5. No fuzzy comparison, no token overlap, no similarity threshold, no normalisation beyond `.lower()`, no model, no network.

An entry whose `signature` is an empty list and whose path matches would match every finding on that path. Do not special-case it; no entry in `bench/golden.json` has an empty signature and inventing a branch for it is scope the spec did not ask for.

## 5. Implement the scoring result and `score_findings`

Use `dataclasses` (already available; add the import to the stdlib import block if `bench/run.py` does not already import it — check first, `HarvestResult` may already use it).

```python
@dataclasses.dataclass(frozen=True)
class ScoreResult:
    entries_in_scope: int
    accepted_in_scope: int
    accepted_hits: int
    misses: int
    matched_rejected: int
    excluded_unreviewed: int
    findings: int
    gap_candidates: tuple
    recall: str
    precision: str
```

```python
def score_findings(*, entries: list, findings: list) -> ScoreResult:
    """Score an already-scoped list of golden entries against a list of findings.

    `entries` are golden entries already restricted to the PRs under consideration.
    Each element of `findings` is a dict carrying 'pr_id', 'path', 'line', 'body'
    and 'rule_id'.  Pure: no I/O, no mutation of either argument.
    """
```

Algorithm:

- **Matching is a relation, not an assignment.** Compute two index sets: `matched_entries` = every entry index for which at least one finding with the same `pr_id` matches it, and `matched_findings` = every finding index that matches at least one entry with the same `pr_id`. Do not pop, consume, mark-used or otherwise remove a finding once it has matched an entry, and do not `break` out of the inner loop in a way that stops a second entry from also being satisfied by the same finding. This is AC8 Case D, and it is the only assertion in the spec that separates the relation from a greedy pairing — on the 66 real ledger rows the mapping is a perfect bijection, so a greedy implementation is byte-identical on every other criterion in this spec.
- A pair is only considered when `entry["pr_id"] == finding["pr_id"]`. Never match across PRs.
- `entries_in_scope` = `len(entries)`.
- `accepted_in_scope` = count of entries with `state == STATE_ACCEPTED`.
- `accepted_hits` = count of `accepted` entries in `matched_entries`.
- `misses` = `accepted_in_scope - accepted_hits`.
- `matched_rejected` = count of `rejected` entries in `matched_entries`.
- `excluded_unreviewed` = count of entries with `state == STATE_UNREVIEWED` (whether or not they matched). Per AC11 an `unreviewed` entry is excluded from both numerator and denominator of both ratios.
- `findings` = `len(findings)`.
- `gap_candidates` = a tuple, in input order, of one plain `dict` per finding index **not** in `matched_findings`, each `{"pr_id": ..., "path": ..., "line": ..., "body": ...}` copied verbatim from the finding — same string objects' values, no truncation, no re-wrapping, no escaping. A finding that matched an `unreviewed` entry is **not** a gap candidate (AC11: it matched an entry, it is simply not adjudicated). A finding that matched a `rejected` entry is **not** a gap candidate either (AC10) — it is already counted as the precision penalty.
- `recall` = `format_ratio(accepted_hits, accepted_in_scope)`.
- `precision` = `format_ratio(accepted_hits, accepted_hits + matched_rejected)`.

An unmatched finding is **never** a precision failure. There is no flag, no keyword argument and no environment variable that makes it one, and no flag that suppresses the gap list — the spec's `## Non-goals` names both as the regression this spec exists to prevent.

## 6. Add the two small helpers the later prompts reuse

```python
def iter_findings(rows: list) -> list:
    """Flatten ledger rows into findings, each carrying its row's pr_id.

    Returns dicts with 'pr_id', 'path', 'line', 'body', 'rule_id' in row order,
    then finding order within a row.  The input rows are not mutated.
    """
```

```python
def entries_in_scope(golden: dict, pr_ids) -> list:
    """The golden entries whose pr_id is in pr_ids, in golden-file order."""
```

`entries_in_scope` is what makes a partial run score against its own PRs rather than all 42 (prompt 2, AC30). Accept any iterable and compare against a `set(pr_ids)` built inside.

## 7. Write `bench/test_score.py`

New file. Do not touch `bench/test_config.py`, `bench/test_resolve.py` or `bench/test_review.py` — the spec's `## Constraints` sets per-file assertion floors on all three (AC24) and a new file paying for a gutted old one is the exact failure that check exists to catch.

Add a module-level helper that loads the real files by path relative to `bench/`, e.g.

```python
BENCH_DIR = pathlib.Path(__file__).resolve().parent

def load_golden():
    return json.loads((BENCH_DIR / "golden.json").read_text(encoding="utf-8"))

def load_slice(name):
    path = BENCH_DIR / "testdata" / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
```

Every test below **must** bind to these real files. No test in this file may score a golden entry or a finding that this file authored, except where an AC explicitly requires a synthetic mutation — and those mutations are always `copy.deepcopy` of the real data with one field changed, never a hand-built row.

Write these test cases, each its own `unittest.TestCase` with a descriptive name.

**Where a case names a specific entry or a specific pair, assert it by calling `finding_matches_entry(entry, finding)` directly**, in addition to the aggregate counts. `ScoreResult` carries counts only, so an entry-level claim cannot be read off it. **Do not add a matched-entry or missed-entry field to `ScoreResult` to make such an assertion expressible, and never drop the assertion because the result object cannot express it** — the direct call is the mechanism.

1. **`TestBaselineSelfMatchIsPerfect`** (AC3). Load the real golden set and the real baseline slice. Score `iter_findings(rows)` against `entries_in_scope(golden, {r["pr_id"] for r in rows})`. Assert the **whole `ScoreResult` in one `assertEqual`** against the expected object: `entries_in_scope=42, accepted_in_scope=42, accepted_hits=42, misses=0, matched_rejected=0, excluded_unreviewed=0, findings=42, gap_candidates=(), recall="1.000", precision="1.000"`. This is the anti-laziness anchor: a matcher that matches nothing scores 0/42 here and a matcher that matches everything fails the four-run assertions in prompt 2.

   **Vary the filter argument in the same test.** Every fixture in this prompt covers all five PRs, so an `entries_in_scope` implementation that ignores `pr_ids` entirely and returns all 42 entries passes every other assertion here. Pin it directly (both numbers measured against the real golden set):

   ```python
   self.assertEqual(len(R.entries_in_scope(golden, {"tts-mcp#20"})), 1)
   self.assertEqual(len(R.entries_in_scope(golden, {"quant#109", "tts-mcp#20"})), 7)
   ```

2. **`TestLineIsNeverUsedForIdentity`** (AC7). Two cases over `copy.deepcopy` of the baseline slice: every finding's `line` set to `None`; every finding's `line` set to its value plus 1000 **where that value is not already `None`**. The baseline slice contains exactly one finding with `line: null` — `node-skeleton#2` / `test/health.test.ts` — so an unguarded `f["line"] + 1000` raises `TypeError` and the test fails against a correct implementation. Assert the full `ScoreResult` equals AC3's in both. Do the same to the golden side in a third case by setting every entry's `line_when_seen` to `None`, and assert the result is unchanged — `line_when_seen` is provenance, not identity.

3. **`TestRuleIdTakesPriority`** (AC8), four cases:
   - **A**: deepcopy the baseline slice; on the `github-pr-review-agent#11` row, set the `CHANGELOG.md` finding's `rule_id` to `"made-up/other-rule"`. Assert `accepted_hits == 41` and `misses == 1`. Pin *which* entry broke by calling the match relation directly — `self.assertFalse(R.finding_matches_entry(changelog_entry, mutated_finding))` — and prove it is not an accidental path break with `self.assertEqual(mutated_finding["path"], "CHANGELOG.md")` and `self.assertIn("changelog.md:11", mutated_finding["body"].lower())`.
   - **B**: same finding's `rule_id` set to `None`. Assert `accepted_hits == 42` and `misses == 0`, and pin the named pair directly with `self.assertTrue(R.finding_matches_entry(changelog_entry, finding_with_null_rule_id))` — the pair falls through to path + signature.
   - **C**: pick one of the 38 golden entries whose `rule_id` is `None` (for example `quant#109`'s first entry) and inject a non-null `rule_id` on the finding that matches it. Assert `accepted_hits == 42`, and pin the specific pair with `self.assertTrue(R.finding_matches_entry(null_rule_entry, finding_with_injected_rule_id))` — resolved by path + signature, not skipped.
   - **D**: deepcopy the golden entries and **append** one entry `{"pr_id": "python-skeleton#3", "path": ".github/workflows/ci.yml", "signature": ["apt-key"], "rule_id": None, "state": "accepted"}`. The real finding at `.github/workflows/ci.yml` line 32 already matches the existing entry whose signature is `[".github/workflows/ci.yml:32"]`, and its body also contains `apt-key`. Assert `accepted_in_scope == 43`, `accepted_hits == 43`, `misses == 0` and `gap_candidates == ()` — **two entries hit from one finding, and that finding is not a gap candidate**. Add an inline comment naming this as the only assertion separating the relation from a greedy 1:1 assignment.

4. **`TestSignatureRequiresEveryKeywordCaseInsensitively`** (AC9). **Mutate an entry whose `rule_id` is `None`** — use `node-skeleton#2` / `README.md`, whose `signature` is `["readme.md:107"]` and whose `rule_id` is `null`. Do **not** use the `github-pr-review-agent#11` / `CHANGELOG.md` entry: it carries `rule_id` `changelog/conventional-prefix-required` and its finding carries the same one, so match-rule step 1 short-circuits and **its signature is never read** — an absent-keyword mutation there still yields 42 hits against a correct implementation, and an upper-cased-keyword mutation yields 42 against every implementation, so both halves would be broken in opposite directions.

   Two mutations on a `copy.deepcopy` of the golden set, both on that `node-skeleton#2` / `README.md` entry:
   - append a keyword that does **not** appear in that body (e.g. `"zzz-absent-keyword"`) → assert `accepted_hits == 41` and `misses == 1`;
   - append `"README.MD"`, which appears in the body only in a different case → assert it stays a hit, `accepted_hits == 42`.

   State the real base case in an inline comment: case-insensitivity is load-bearing on this golden set because **6 of the 38 null-`rule_id` entries match case-insensitively only** — `node-skeleton#2` / `README.md` (`readme.md:107`), `python-skeleton#3` / `Makefile.precommit` (`makefile.precommit:42`, `makefile.precommit:24`, `makefile.precommit:60-61`) and `python-skeleton#3` / `README.md` (`readme.md:80`, `readme.md:84`). A case-**sensitive** matcher therefore scores 36/42 on AC3, not 42/42.

5. **`TestRejectedEntryIsAPrecisionPenalty`** (AC10). Deepcopy the golden set; flip the single `tts-mcp#20` entry's `state` to `rejected`. Assert `accepted_in_scope == 41`, `accepted_hits == 41`, `matched_rejected == 1`, `gap_candidates == ()`, `recall == "1.000"`, `precision == "0.976"`. Pin the mechanism rather than restating the empty tuple: `all(...)` over `gap_candidates` is vacuously true given the `gap_candidates == ()` assertion above it, so assert instead that the pair still matches — `self.assertTrue(R.finding_matches_entry(tts_entry_now_rejected, tts_finding))` — which is what makes the finding a precision penalty rather than a candidate.

6. **`TestUnreviewedEntryIsExcludedFromBothRatios`** (AC11). Same entry flipped to `unreviewed`. Assert `accepted_in_scope == 41`, `accepted_hits == 41`, `matched_rejected == 0`, `excluded_unreviewed == 1`, `gap_candidates == ()`, `recall == "1.000"`, `precision == "1.000"`.

7. **`TestGapCandidatesAreNotPrecisionFailures`** (AC13). Load `bench/testdata/ledger-sonnet-medium-short-4runs.jsonl`. Chunking belongs to prompt 2, so select run 3's rows here by per-PR occurrence index inline in the test (for each `pr_id`, the 3rd row in file order) — a five-line `collections.Counter` loop, not a helper in `run.py`. Assert that run's `gap_candidates` has exactly 3 entries, that each carries `pr_id`, `path`, `line` and `body` and that each `body` is byte-identical to the corresponding finding's body in the fixture, and that the run's `precision` is `"1.000"` — unchanged by the presence of those 3 candidates. Second assertion in the same test: the `apt-key` finding in `.github/workflows/ci.yml` on `python-skeleton#3` appears as a gap candidate in **all four** runs, at `line` 13, 29, 9 and 27 respectively. Assert those four line values explicitly. Four independent reports of one issue that the settled match rule does not match is exactly the evidence a curator needs, and precisely the thing that must not be recorded as four false positives.

8. **`TestScorerDoesNotRequireAPathExtension`** (AC20). Build the golden side as a deepcopy of the real set plus one in-test entry `{"pr_id": "tts-mcp#20", "path": "Dockerfile", "signature": ["healthcheck"], "rule_id": None, "state": "accepted"}`, and the finding side as the real baseline findings plus one synthetic finding `{"pr_id": "tts-mcp#20", "path": "Dockerfile", "line": 4, "body": "HEALTHCHECK instruction missing", "rule_id": None}`. Pin the whole result in one `assertEqual`: `entries_in_scope=43, accepted_in_scope=43, accepted_hits=43, misses=0, matched_rejected=0, excluded_unreviewed=0, findings=43, gap_candidates=(), recall="1.000", precision="1.000"`. Additionally assert `R.finding_matches_entry(dockerfile_entry, dockerfile_finding) is True`. Add an inline comment: the harvester's inability to *produce* an extensionless path is D8 and stays out of scope here.

9. **`TestFixtureProvenance`** (AC2). Assert the `sha256` of all five installed files equals the published digests and that the line counts are 490 / 5 / 20 / 32 / 4. Compute the digest inside the test with `hashlib.sha256(path.read_bytes()).hexdigest()`. This test is what turns a silently swapped fixture into a red suite rather than a plausible wrong number.

10. **`TestRatioRenderingIsFrozen`**. `format_ratio` ships in this prompt; test 7 reaches a zero denominator only incidentally through run 4 of the four-run slice and never asserts the rendering, so pin all four shapes directly against the **literals**: `format_ratio(2, 42) == "0.048"`, `format_ratio(0, 42) == "0.000"`, `format_ratio(41, 42) == "0.976"`, and `format_ratio(0, 0) == "n/a"` — the last asserted against the literal `"n/a"` as well as against `R.RATIO_NA`, and reached by a plain call outside any `try`, so a `ZeroDivisionError` fails the test rather than being caught.

11. **`TestGoldenSetIsNotMutatedByScoring`** (spec `## Constraints`, "frozen input"). Snapshot `hashlib.sha256` of `bench/golden.json` and of each of the four slices before and after running the full AC3 scoring, and assert both are unchanged. Additionally deep-compare the `entries` list object passed into `score_findings` against a pre-call `copy.deepcopy` to prove the function mutates neither argument.

12. **`TestDefensiveBranches`**. Requirement 8 below specifies two guards that **no fixture reaches** — 0 of the 95 findings across the four slices has a missing or `None` `body`, and all 42 golden entries are `accepted` — so an implementation writing `finding["body"].lower()` unguarded, or raising on an unknown state, passes every other test in this file. Two cases on `copy.deepcopy` of the real data:
    - set one finding's `body` to `None` (and a second case: `del` the key entirely) → scoring raises nothing, that finding is a gap candidate, and the entry it used to match becomes a miss;
    - set one golden entry's `state` to `"bogus"` → it is counted in `entries_in_scope` but in **none** of `accepted_in_scope`, `matched_rejected` or `excluded_unreviewed`, and scoring raises nothing.

## 8. Error paths

`score_findings` operates on already-validated data and does no I/O, so it raises nothing of its own. Two defensive rules, both without new configuration:

- A finding whose `body` is missing or `None` is treated as an empty body (`(finding.get("body") or "")`), so it matches no signature-based entry and becomes a gap candidate. It must not raise `AttributeError`.
- A golden entry whose `state` is not one of `GOLDEN_STATES` is counted in `entries_in_scope` but in none of the accepted / rejected / unreviewed tallies. Do not raise here — the loud rejection of a malformed golden set belongs to `load_golden` in prompt 4, with the `INVALID GOLDEN SET` literal, and duplicating it here would produce two different failure modes for one input.

Matching is linear in `entries × findings` within a PR. Do not build a regex from any ledger value, and do not use `re` anywhere in the match path — a `body` is attacker-influenced text and the spec's `## Security / Abuse Cases` requires no construct in a ledger row to cause unbounded backtracking.

## 9. Out of scope for this prompt — do not implement

Run chunking, per-run and per-PR aggregation, the report page, `--golden` / `--score` CLI wiring, the `prs_version` skip, `load_golden`, ledger loading, `config_hash` validation and the README/CHANGELOG updates all belong to prompts 2-5 of this spec. Adding them here makes prompt 2's diff unreviewable.
</requirements>

<constraints>
- Python 3 **standard library only**. No third-party imports, no packaging, no new top-level files outside `bench/`. Every `import` / `from` line you add to `bench/run.py` must name a stdlib module.
- **`bench/golden.json` and everything under `bench/testdata/` are frozen inputs.** `git diff --exit-code bench/golden.json bench/testdata/` must exit 0 after your work. Never write, regenerate or repair one; on a digest mismatch, stop and report `status: failed`.
- **Do NOT change `commands/pr-review.md` or anything under `rules/`.** Either moves `rules_commands_hash` and orphans every existing ledger row and every published number in the spec.
- **Do NOT touch the harvest layer** — `harvest`, `HarvestResult`, `extract_attribution`, the `UNATTRIBUTABLE FINDING` gate, the `NOT A REVIEW` gate — or their tests. Finding extraction is spec 005's territory.
- **Do NOT fix D8.** Extensionless paths being unattributable in the harvester stays a known open defect. The scorer simply must not replicate the dot requirement.
- **Do NOT introduce an LLM judge, a fuzzy body matcher, an embedding comparison or any non-deterministic matching.** Text equality and case-insensitive substring containment only.
- **Do NOT re-derive, refine or edit the match rule or the 42 signatures.**
- **Do NOT make the match rule, the three state names, the gap-triage classification or the ratio rounding configurable.** No flag, no keyword argument, no environment variable.
- **Do NOT add an opt-out that counts unmatched findings as precision failures, or a flag that suppresses gap-triage.** An escape hatch on this behavior is the regression the spec exists to prevent.
- **No test function may be deleted and no assertion relaxed** in `bench/test_config.py`, `bench/test_resolve.py` or `bench/test_review.py`. Their assertion floors are 63 / 46 / 265.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file.
- **`docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" is satisfied by prompt 5 of this spec (AC23), not here.** Do not add a CHANGELOG entry in this prompt. Spec 002's precedent: a mid-chain prompt that described only its own slice left the release classifier cutting a patch where a minor was due, which is why the CHANGELOG lands once, last, describing what all five prompts shipped.
- Do NOT commit — dark-factory handles git.
- Existing tests must still pass: the suite is at 103 tests and green before you start.
</constraints>

<verification>
```bash
# Inputs untouched and still authentic
python3 - <<'EOF'
import hashlib, pathlib, sys
EXPECTED = {
    'bench/golden.json': '90f5b0a61ac763b6abb3991fff699a4818318f22a171f6fc4375d314da43459d',
    'bench/testdata/ledger-baseline-opus-xhigh-full.jsonl': 'af8f684b95e82577af4ac6b4a04392559ef04865ee95e7f8afdcc8f1756e86fb',
    'bench/testdata/ledger-sonnet-medium-short-4runs.jsonl': 'f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02',
    'bench/testdata/ledger-sonnet-medium-short-partial.jsonl': '165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7',
    'bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl': 'f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209',
}
bad = [f'{n}: {hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest() if pathlib.Path(n).exists() else "MISSING"}'
       for n, w in EXPECTED.items()
       if not pathlib.Path(n).exists() or hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest() != w]
assert not bad, 'FIXTURE DIGESTS FAILED: ' + '; '.join(bad)
print('fixture digests OK')
EOF
echo "digest check exit=$? (expect 0; a non-zero exit or an AssertionError means stop and report failed)"
git diff --exit-code bench/golden.json bench/testdata/ ; echo "frozen-input diff exit=$? (expect 0)"

# The new surface exists with the frozen literals
grep -n 'GOLDEN SET NOT FOUND\|INVALID GOLDEN SET\|GOLDEN VERSION MISMATCH\|PRS VERSION SKIP\|EMPTY LEDGER\|CORRUPT LEDGER\|INVALID CONFIG HASH' bench/run.py
grep -n 'def format_ratio\|def finding_matches_entry\|def score_findings\|def iter_findings\|def entries_in_scope\|class ScoreResult' bench/run.py

# The scorer must not have inherited the harvest dot gate
grep -n 'PATH_LINE_RE' bench/run.py   # must appear only inside the harvest helpers, never in the match path

# Replay AC3 against the real files
python3 - <<'EOF'
import sys, json, pathlib, dataclasses
sys.path.insert(0, 'bench')
import run as R
golden = json.loads(pathlib.Path('bench/golden.json').read_text())
rows = [json.loads(l) for l in pathlib.Path('bench/testdata/ledger-baseline-opus-xhigh-full.jsonl').read_text().splitlines() if l.strip()]
entries = R.entries_in_scope(golden, {r['pr_id'] for r in rows})
print(dataclasses.asdict(R.score_findings(entries=entries, findings=R.iter_findings(rows))))
EOF

# Ratio rendering, both degenerate denominators
python3 -c "import sys; sys.path.insert(0,'bench'); import run as R; print(R.format_ratio(2,42), R.format_ratio(0,42), R.format_ratio(0,0), R.format_ratio(41,42))"

# Assertion floors untouched (AC24)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 265

# Repo gates
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$? (expect 1)"
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
make precommit
```

Expected: the digest check prints `fixture digests OK` and exits 0; the frozen-input diff is empty; all seven marker literals and the six new symbols appear in `bench/run.py`; the AC3 replay prints `entries_in_scope 42, accepted_in_scope 42, accepted_hits 42, misses 0, matched_rejected 0, excluded_unreviewed 0, findings 42, gap_candidates (), recall '1.000', precision '1.000'`; `format_ratio` prints `0.048 0.000 n/a 0.976`; the three assertion counts are at least 63, 46 and 265; the personal-path grep exits 1; the unittest run reports `OK` with `Ran N tests`, `N > 103`, and lists the baseline-self-match, line-independence, rule-id-priority, signature-keyword, rejected-penalty, unreviewed-exclusion, gap-triage, extensionless-path, ratio-rendering, fixture-provenance and defensive-branch tests by name; `make precommit` exits 0.
</verification>
