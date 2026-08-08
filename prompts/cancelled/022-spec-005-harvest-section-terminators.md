---
status: cancelled
spec: [005-bug-bench-harvest-finding-extraction]
execution_id: coding-exec-022-spec-005-harvest-section-terminators
dark-factory-version: v0.192.9
created: "2026-08-08T11:40:00Z"
queued: "2026-08-08T12:14:19Z"
started: "2026-08-08T12:24:41Z"
completed: "2026-08-08T12:23:22Z"
lastFailReason: 'validate completion report: completion report status: partial'
cancelled: "2026-08-08T12:24:55Z"
---

<summary>
- The benchmark stops counting a reviewer's trailing housekeeping notes as review findings
- A review that correctly found nothing now records nothing, instead of recording the three bullets of its closing notes block
- The rule that ends a findings section is generalised: any bold-label block starts something new, whatever that label says
- Two more shapes the reviewer really emits — a `**Notes:**` block and a `**Summary**:` block — stop leaking into the counts
- Content the reviewer placed outside a findings section is neither counted as a finding nor treated as an error
- Harvesting now returns two things instead of one: the findings, and a report of items that could not be attributed (empty for now, filled in by a later prompt)
- Four verbatim captures of real review output are checked against their published fingerprints before any test is written against them
- If a capture does not match its fingerprint the work stops and says so, rather than rewriting the capture to fit
- Heading depth is confirmed irrelevant: the same review content at three different heading depths produces the same result
- First of five prompts; it fixes only where a section ends, and deliberately touches nothing else
</summary>

<objective>
Give a findings section a terminator that matches what the reviewer actually writes — a line whose first non-whitespace content opens a bold run ends the section, exactly as a heading or a thematic break already does — so a trailing `**Notes:**` or `**Summary**:` block can no longer be harvested as findings. Change `harvest` to return a two-part result (findings plus a reserved unattributable-item report) so the later prompts of this spec have somewhere to put a parse failure, and lock all of it against four operator-installed verbatim captures of live review output.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 standard library only, no personal paths, generic examples only, never commit — dark-factory handles git).

Read `specs/in-progress/005-bug-bench-harvest-finding-extraction.md`. This prompt satisfies **Desired Behavior 1** and the fixtures half of **Desired Behavior 6**, and **Acceptance Criteria AC2, AC3, AC4, AC10 and AC14**. Load-bearing sections to read in full: `## Reproduction` → `### RC1`, `### RC4`, `## Acceptance Criteria` AC2/AC3/AC4/AC10/AC14, `## Constraints`, `## Assumptions`.

Read `bench/run.py`. The code you change lives between the `# Harvesting` banner and the `# Result row assembly` banner. Specifically read, and take every signature from the file rather than from this prompt: the module constants block (`HEADING_RE`, `THEMATIC_BREAK_RE`, `FENCE_RE`, `BULLET_RE`, `REQUIRED_SECTION_NAMES`), `heading_section_name`, `iter_report_lines`, `missing_sections`, `_normalize_body`, `harvest`, and the single call site `findings = harvest(proc.stdout, known_rule_ids)` in `process_pr` (step 6, immediately after the step-5 raw-stdout write).

Read `bench/test_review.py`. Every existing call site of `run.harvest(...)` must keep working after the return type changes. They are in these classes: `TestHarvestNormalizesSampleReport`, `TestHarvestKeepsFindingWithoutAnyRuleId`, `TestHarvestIgnoresEmptySection`, `TestRealCaptureHarvestsToZeroFindings`, `TestTrailingProseDoesNotSwallowARealFinding`, `TestHeadingLevelDoesNotChangeHarvest`, `TestSectionNameInProseOrFenceIsNotAHeading`, `TestThematicBreakEndsASection`, `TestProseBeforeAListItemOpensNothing`.

Read the four fixtures before writing any assertion against them — they are verbatim captures, not templates, and the exact text matters:
`bench/testdata/capture-notes-block-h2.md`, `bench/testdata/capture-numbered-findings-h3.md`, `bench/testdata/capture-traceability-h4.md`, `bench/testdata/capture-summary-trailer-h4.md`.

Read `bench/testdata/sample-report.md` and `bench/testdata/real-capture-report.md` — both are byte-frozen and must still harvest to their previously asserted results.

Read `docs/dod.md` for the repository's Definition of Done.
</context>

<requirements>

## 1. Verify the four fixtures before touching any code

The four capture fixtures were installed by the operator before this spec was approved. **You never create, regenerate, overwrite, reconstruct or edit a file under `bench/testdata/`.** Verify them first:

```bash
for f in bench/testdata/capture-notes-block-h2.md \
         bench/testdata/capture-numbered-findings-h3.md \
         bench/testdata/capture-traceability-h4.md \
         bench/testdata/capture-summary-trailer-h4.md; do
  printf '%s %s %s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(grep -c '' "$f")"
done
```

Expected exactly:

| File | `sha256` | Lines | Heading level |
|---|---|---|---|
| `bench/testdata/capture-notes-block-h2.md` | `6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9` | 17 | `##` |
| `bench/testdata/capture-numbered-findings-h3.md` | `5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93` | 28 | `###` |
| `bench/testdata/capture-traceability-h4.md` | `2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c` | 57 | `####` |
| `bench/testdata/capture-summary-trailer-h4.md` | `36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79` | 21 | `####` |

Also verify, per file, that `grep -cE '^<level> (Must Fix|Should Fix|Nice to Have)' <file>` returns `3` at the stated level and `0` at each of the other two levels, and that `grep -rn '/Users/\|~/Documents/' bench/testdata/` returns no lines.

If any file is missing, or any digest, line count or heading count differs, **stop immediately and report `status: failed`** with the message `"fixture <name>: expected sha256 <published>, got <observed>"`. Do not write the file, do not adjust the expectation, do not continue with the rest of this prompt.

## 2. Add a machine-checkable fixture-digest test

In `bench/test_review.py`, add `class TestCaptureFixturesMatchPublishedDigests(unittest.TestCase)` with one test method that, for each of the four files, computes `hashlib.sha256(path.read_bytes()).hexdigest()` and asserts it equals the published digest above, and asserts the line count. Import `hashlib` at the top of the file if it is not already imported. The failure message must print the fixture name, the expected digest and the observed digest.

This test is the AC2 gate: it makes a silently-rewritten fixture a red test rather than a green one.

## 3. Introduce the two-part harvest result

In `bench/run.py`, immediately above `def harvest(...)`, add:

```python
@dataclasses.dataclass
class HarvestResult:
    """The two-part outcome of harvesting one review report.

    findings       — items inside a severity section that carry an attribution.
    unattributable — items inside a severity section that carry none.  Reserved
                     here and always empty; populated by the unattributable-item
                     gate, which classifies items once attribution extraction
                     exists.  It is a separate component precisely so a caller
                     can distinguish "nothing was found" from "something was
                     found and could not be keyed" (spec 005 AC3).
    """
    findings: list
    unattributable: list
```

Use `@dataclasses.dataclass`, matching `PrCheckout` and `PluginResolution` in the same file. `dataclasses` is already imported; add no new import.

Change `harvest`'s signature to `def harvest(report_text: str, known_rule_ids: set) -> HarvestResult:` and its final statement to `return HarvestResult(findings=findings, unattributable=[])`. Keep the parameter list unchanged. Update the docstring to describe both components.

Update the call site in `process_pr` (step 6) to:

```python
    # 6. Harvest findings
    harvested = harvest(proc.stdout, known_rule_ids)
    findings = harvested.findings
```

Nothing else in `process_pr` changes in this prompt.

Update every existing `run.harvest(...)` call site in `bench/test_review.py` to read `.findings` — for example `findings = run.harvest(text, ids).findings`. Do not delete or weaken any existing assertion; this is a call-shape change only.

## 4. Add the bold-run section terminator

Add a module constant next to `BULLET_RE` in the constants block:

```python
BOLD_RUN_START_RE = re.compile(r"^\s*\*\*")
```

In `harvest`, inside the existing `if not in_fence:` block, add a branch **after** the `THEMATIC_BREAK_RE` branch and before the `if current_section is None:` guard:

```python
            if BOLD_RUN_START_RE.match(line):
                flush_finding()
                current_section = None
                current_finding_lines = []
                continue
```

Ordering is load-bearing and must not be changed: `HEADING_RE` first, `THEMATIC_BREAK_RE` second, `BOLD_RUN_START_RE` third. A thematic break written as `***` also matches `BOLD_RUN_START_RE`, and it must be consumed as a thematic break. The branch sits inside the `if not in_fence:` block so a `**bold**` line inside a fenced code block terminates nothing.

`BOLD_RUN_START_RE` must not match a list item. `BULLET_RE` requires `[-*]` followed by whitespace, so `* **emphasised**` is a bullet (single `*` then a space) while `**Notes:**` is a bold run (two adjacent asterisks). Do not widen the pattern. Do not narrow it either. A finding's continuation paragraph that begins with a bold run will truncate that finding's body and close the section early — the spec's Failure Modes table names this shape, accepts it (the failure direction is loss, never fabrication), and records that no captured output exhibits it. Do not add a lookahead, a continuation exemption, or any heuristic to avoid it.

## 5. Tests for the bold-run terminator and the captures

Add these to `bench/test_review.py`. Every assertion below compares **both** components of the `HarvestResult`, and every failure message prints both lists.

**AC3** — `class TestNotesBlockCaptureHarvestsToNothing`: read `bench/testdata/capture-notes-block-h2.md`, harvest it, assert `result.findings == []` **and** `result.unattributable == []`. The failure message must print both. Asserting only the findings list would let an implementation reclassify the three `**Notes:**` bullets as unattributable items, which fails the PR loudly on a review that correctly found nothing — RC1 with the sign flipped.

**AC4** — `class TestBoldLabelTerminatorIsGeneral`, three separate test methods over synthetic reports:

- Case A — a section reading `None.`, then `**Notes:**`, then three bullets → `findings == []` and `unattributable == []`.
- Case B — a section reading `None.`, then `**Summary**:` followed by prose on the same line, then a bullet on a later line → `findings == []` and `unattributable == []`. This is the shape `bench/testdata/capture-summary-trailer-h4.md` actually uses; matching the literal string `**Notes:**` passes Case A alone.
- Case C — a section carrying one real attributed bullet, then `**Notes:**`, then two more bullets → exactly one finding. Use this bullet verbatim so it stays attributable under the later prompts of this spec:

  ```
  - **`src/foo.py:7`** the one real finding, which must survive.
  ```

  Assert `len(result.findings) == 1`, `result.unattributable == []`, `result.findings[0]["path"] == "src/foo.py"`, `result.findings[0]["line"] == 7`, `"the one real finding" in result.findings[0]["body"]`, and that the body contains none of the text of the two trailing bullets. Do **not** assert on the leading `**` of the body in this prompt — body fidelity is prompt 2's requirement.

**AC10** — `class TestContentOutsideASeveritySectionIsNeverAFinding`, three test methods:

- Case A — harvest `bench/testdata/capture-numbered-findings-h3.md` and assert that none of the four `### Positive notes` bullets appears in `result.findings` or in `result.unattributable`. Assert it by text: for each of the four distinctive substrings `"build-backend switch is clean"`, `"mktemp"`, `"S104"` and `"TestClient"`, assert it appears in no `body` of either list. **First assert the corpus is non-degenerate** — `self.assertTrue(result.findings or result.unattributable)` — because an absence-only probe over two empty lists passes even if harvesting broke completely. Do not assert an exact count: this fixture's harvested count changes at prompts 2 and 4. Content outside a severity section is not a finding and is not a parse failure either.

  **Do not substitute these four substrings.** Each was chosen because it occurs **exactly once** in the fixture and that one occurrence is inside a `### Positive notes` bullet (fixture lines 23, 24, 25, 26 respectively) — so the probe can only ever fail for the reason it is testing. Record that constraint as a comment directly above the substring tuple in the test source, naming the fixture line numbers, so a later prompt does not swap in a colliding token. Two obvious-looking alternatives are already disqualified and must not be reintroduced:
  - `"hatchling"` occurs twice — fixture line 20 is a **Nice to Have bullet that is a legitimate finding today**, so the probe is red on arrival.
  - `"pip-audit"` occurs three times, on two lines (line 15 once, line 24 twice) — fixture line 15 is inside **Should Fix item 4**, invisible to the parser now but harvested as a finding once prompt 2 lands ordered items, so the probe would go red one prompt later with nobody remembering why.
  - `"ruff "` occurs twice (lines 5 and 25); the line 5 hit is pre-section prose that is never harvested, so it is *safe* but not *exactly once* — `"S104"` is used instead to keep one uniform rule for all four.
- Case B — harvest `bench/testdata/capture-traceability-h4.md` and assert no finding carries a `rule_id` drawn from the file's `### Traceability` table. Assert it by reading the fixture and collecting every value in the table's first column — match line by line, or use `re.findall(r"^\| ([a-z][a-z0-9/-]+) \|", text, re.MULTILINE)`; **without `re.MULTILINE` the pattern anchors to the start of the whole string and returns nothing** (verified: 0 matches without the flag, 22 with it). **First assert `len(table_ids) == 22`** (the table has 22 rows, fixture lines 33-54), then assert no harvested `rule_id` is a member of that set. Without the cardinality assertion a mis-anchored regex yields an empty set and the membership check becomes a test that can never fail — a new variant of this project's recurring family: not an assertion whose *expected value* the implementation chooses, but one whose *input corpus* silently empties.
- Case C — both zero-finding captures harvest to an empty findings list and an empty unattributable list: `bench/testdata/real-capture-report.md` (pre-existing, frozen) and `bench/testdata/capture-summary-trailer-h4.md`.

**AC14** — `class TestHeadingLevelIsIrrelevantToTermination` with a method whose name contains `heading_level`:

- Render identical section content at `##`, `###` and `####` and assert all three harvest to equal `HarvestResult`s. **Equality alone is vacuous — three empty results compare equal**, so an implementation that harvests nothing at any level would pass a bare equality assertion. The rendered content must therefore carry a real finding, and each level must be asserted on its own as well as against the others.

  Use this exact Must Fix body at every level, followed by a `**Notes:**` block and two further bullets:

  ```
  - **`src/foo.py:7`** a finding that must appear at every level.
  ```

  Assert the three-way equality **and**, separately for each of the three levels: `len(result.findings) == 1`, `result.findings[0]["path"] == "src/foo.py"`, `result.findings[0]["line"] == 7`, and `result.unattributable == []`. The per-level assertions are what make the equality meaningful; do not drop them in favour of the equality check alone.

  The existing `test_heading_level_does_not_change_harvest` stays; this is an additional test that also covers termination.
- Assert a `###` heading terminates an open `##` section: a `## Must Fix (Critical)` section carrying one attributed bullet, followed by `### Some other heading` and two more bullets, yields exactly one finding.
- Assert a `##` heading terminates an open `####` section: the same shape with the levels swapped, yields exactly one finding.
- The failure messages print all lists.

## 6. Keep the frozen fixtures green

After the change, `bench/testdata/sample-report.md` must still harvest to its three previously asserted findings and `bench/testdata/real-capture-report.md` to zero. Neither file may be edited. If either test goes red, the terminator is wrong — fix the terminator, never the fixture and never the assertion.

## 7. Failure handling

`harvest` remains a pure function over text: it never raises for malformed input, never opens a file, never invokes a subprocess, and stays linear in input size with line-oriented matching only. A pathological report yields a wrong section boundary at worst, never a hang. `process_pr`'s existing error paths are unchanged in this prompt.

</requirements>

<constraints>
- **Python 3 standard library only.** No third-party imports, no new top-level files outside `bench/`. Changes land only in `bench/run.py` and `bench/test_review.py` in this prompt.
- **Never create, regenerate, overwrite or edit any file under `bench/testdata/`.** A transcribed or regenerated fixture is the exact defect this spec exists to close. On a digest mismatch, stop and report failed.
- **`bench/testdata/sample-report.md` and `bench/testdata/real-capture-report.md` are byte-frozen** and must still harvest to their previously asserted results.
- **No test function may be deleted and no assertion relaxed.** Per-file assertion floors that must hold after this prompt: `grep -cE '^\s*(self\.assert|assert )' bench/test_config.py` ≥ 63, `bench/test_resolve.py` ≥ 46, `bench/test_review.py` ≥ 165. The suite's test count must stay strictly greater than 72.
- **Do NOT change the `NOT A REVIEW` gate** — same required sections, same heading matching, same bounded excerpt, same position ahead of the raw-output cache write.
- **Do NOT change `bench/prs.json`, `commands/pr-review.md`, or any rule, agent, command or doc that participates in a review.**
- **Do NOT make the terminators configurable** and do NOT add any flag, env var or opt-out that relaxes them. They are frozen invariants.
- **Do NOT touch the raw-stdout-before-parsing ordering** in `process_pr` (step 5 stays ahead of step 6).
- **Harvested values are data, never paths.** No value read out of review output is opened, stat-ed, joined onto a filesystem root, or passed to a subprocess.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file.
- Bench tests must not require network access, a real `claude` binary, or GitHub access.
- Do not read from or write to `bench/.cache/` or `bench/results/`.
- Do NOT edit `bench/README.md` or `CHANGELOG.md` in this prompt — prompt 5 of this spec owns both (spec 005 AC16/AC17). `docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" criterion is deliberately deferred to prompt 5 and its absence here is **expected — do NOT report it as a blocker** and do NOT add an entry to satisfy it.
- Do NOT commit — dark-factory handles git.
</constraints>

<verification>
```
# Fixture provenance — the four digests and line counts (AC2)
for f in bench/testdata/capture-notes-block-h2.md \
         bench/testdata/capture-numbered-findings-h3.md \
         bench/testdata/capture-traceability-h4.md \
         bench/testdata/capture-summary-trailer-h4.md; do
  printf '%s %s %s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)" "$(grep -c '' "$f")"
done
grep -rn '/Users/\|~/Documents/' bench/testdata/ ; echo "exit=$? (expect 1)"

# Section-heading anchors, per fixture
grep -cE '^## (Must Fix|Should Fix|Nice to Have)' bench/testdata/capture-notes-block-h2.md          # expect 3
grep -cE '^### (Must Fix|Should Fix|Nice to Have)' bench/testdata/capture-numbered-findings-h3.md   # expect 3
grep -cE '^#### (Must Fix|Should Fix|Nice to Have)' bench/testdata/capture-traceability-h4.md       # expect 3
grep -cE '^#### (Must Fix|Should Fix|Nice to Have)' bench/testdata/capture-summary-trailer-h4.md    # expect 3

# The new constant and the two-part result exist
grep -n 'BOLD_RUN_START_RE\|class HarvestResult\|def harvest' bench/run.py

# Assertion floors (AC15) and suite size (AC1)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 165

# Full suite, named tests visible
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40

# Repository gate
make precommit
```

Expected: the four digests equal the published values and the line counts print `17`, `28`, `57`, `21`; the personal-path grep exits 1 with no output; each heading grep prints `3`; the unittest run reports `OK` with `Ran N tests` where `N > 72` and lists the new notes-block, bold-label, outside-section and `heading_level` tests by name; `make precommit` exits 0.
</verification>

