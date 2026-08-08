---
status: completed
spec: [003-bench-review-sanity-and-harvest-boundary]
summary: Give harvest() explicit section end boundaries and add verbatim-capture fixture with 6 new tests
execution_id: coding-bench-harvest-exec-015-spec-003-harvest-section-boundaries
dark-factory-version: v0.192.9
created: "2026-08-08T02:35:00Z"
queued: "2026-08-08T00:49:09Z"
started: "2026-08-08T00:49:11Z"
completed: "2026-08-08T00:52:55Z"
---

<summary>
- The benchmark's findings harvester stops inventing findings out of a review's closing prose
- A findings section now ends where a reader would say it ends: at the next heading, at a horizontal rule, or at the end of the report
- Only a bullet point can start a finding; plain sentences sitting in a section start nothing and can no longer absorb everything written after them
- The mandated "None." that a review writes for an empty section therefore yields nothing at all, which is what it always meant
- A real finding keeps exactly its own text — trailing summary paragraphs no longer get glued onto the end of it
- Section names written inside a fenced code block are treated as code, not as section headings
- The heading level a review happens to use stops mattering anywhere in the harvest
- Test data gains a verbatim capture of output a live review really emitted — the exact input that produced the phantom finding — instead of another transcription of the command's own template
- The existing template-derived fixture and every assertion about it stay untouched, so both renderings are locked against regression
</summary>

<objective>
Give `harvest()` in `bench/run.py` explicit section end boundaries and an explicit rule for what opens a finding, so the trailing prose that every real review wraps around its findings can never become a finding. Add a checked-in fixture that is a verbatim capture of live review output — the exact input that produced the phantom finding on `tts-mcp#20` — plus the tests that lock the new contract. This prompt changes a pure function and its test data only; it does not touch the runner's control flow.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, generic examples only, never commit).

Read `specs/in-progress/003-bench-review-sanity-and-harvest-boundary.md` — this prompt implements **Desired Behaviors 3, 4 and 5** and **Acceptance Criteria AC7, AC8, AC9, AC10, AC11**. Two sections are load-bearing:
- **`## Reference: captured real output`** — the 1,380-byte stdout captured from the 2026-08-08 run against `tts-mcp#20`. The fixture you add is derived from that block, verbatim. Read it before writing the fixture.
- **The paragraph after that block ("Verified root cause, which differs from the first diagnosis")** — heading level is *not* the defect. The harvester already matches all six heading levels. The defect is that nothing ends a section except another heading, so a thematic break and the trailing summary get appended as continuation lines to the still-open `None.` buffer, which defeats the sentinel check.

Read `bench/run.py` — the file you are changing. The pieces that matter:

```python
def harvest(report_text: str, known_rule_ids: set) -> list:
    findings: list = []
    current_section: str | None = None
    current_finding_lines: list[str] = []
    section_names = {"must fix", "should fix", "nice to have"}

    def flush_finding():
        ...
        text = " ".join(current_finding_lines)
        body = _normalize_body(current_finding_lines)
        # Skip the "None." empty-section sentinel
        if body.strip() in ("None.", "None"):
            current_finding_lines = []
            return
        rule_id = _extract_rule_id(text, known_rule_ids)
        path, line_num = _extract_path_line(text, known_rule_ids)
        findings.append({"path": path, "line": line_num, "rule_id": rule_id, "body": body})
        current_finding_lines = []
```

and its main loop, which today does three things and nothing else: a heading of any level (`^#{1,6}\s+(.+)$`) flushes and either opens a section or closes one; inside a section a bullet (`^\s{0,3}([-*])\s+(.+)$`, matched against the *stripped* line) flushes and starts a finding; any other non-empty line inside a section is appended as a continuation line **whether or not a finding is open** — that last clause is the bug.

Also read, and reuse unchanged: `_extract_rule_id(text, known_rule_ids)`, `_extract_path_line(text, known_rule_ids)`, `_normalize_body(lines)`, `load_rule_ids(coding_repo)`, `BENCH_DIR`, `REPO_ROOT`.

Read `bench/testdata/sample-report.md` — the pre-existing template-derived fixture. It harvests to exactly 3 findings today and must still harvest to exactly the same 3 after your change. Its SHA-256 is `de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae`; that value must be unchanged when you are done.

Read `bench/test_review.py` — the test file you extend. 13 tests today, plain `unittest.TestCase` classes with a docstring naming the AC, `import run` / `import testsupport` (discovery puts `bench/` on `sys.path`). Match that style; do not introduce a test framework. The three tests that already cover harvesting are `test_harvest_normalizes_sample_report`, `test_harvest_keeps_finding_without_any_rule_id`, `test_harvest_ignores_empty_section` — none of them may be deleted, renamed, or have an assertion removed or loosened.

Read `commands/pr-review.md` Step 5 (search for `**MANDATORY**: Always include all three headers`) for the three section names and the mandated `None.` sentinel. **Do not edit that file.**

Read `docs/dod.md` — no personal paths anywhere in a shipped file, `## Unreleased` CHANGELOG entry required.
</context>

<requirements>

## 1. Module-level pattern constants in `bench/run.py`

Add these next to the existing module constants (`NAME_RE`, `PR_ID_RE`). They are compiled once and used by both `harvest()` here and, in a later prompt, the sanity gate — a single definition per pattern is what keeps the two from drifting.

```python
REQUIRED_SECTION_NAMES = ("Must Fix", "Should Fix", "Nice to Have")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
SEVERITY_SUFFIX_RE = re.compile(r"\s*\([^)]+\)\s*$")
THEMATIC_BREAK_RE = re.compile(r"^ {0,3}(?:-{3,}|\*{3,}|_{3,}) *$")
FENCE_RE = re.compile(r"^ {0,3}(?:```|~~~)")
BULLET_RE = re.compile(r"^\s{0,3}([-*])\s+(.+)$")
_SECTION_BY_LOWER = {name.lower(): name for name in REQUIRED_SECTION_NAMES}
```

Every one of these is line-anchored with a bounded quantifier and no nested repetition, so matching is linear in input size — the spec's "denial by pathological input" case. Do not introduce a pattern with a nested quantifier.

`REQUIRED_SECTION_NAMES` is a frozen invariant. Do not add a flag, an environment variable, a parameter or a config field for it.

## 2. `heading_section_name(line)` — the single heading rule

```python
def heading_section_name(line: str) -> str | None:
    """Return the canonical findings-section name a markdown heading line names, or None.

    Matches a heading at any level 1-6, strips a trailing parenthesised severity
    annotation such as "(Critical)", and compares case-insensitively against
    REQUIRED_SECTION_NAMES.  Returns the canonical spelling ("Must Fix",
    "Should Fix", "Nice to Have") or None when the line is not a heading or names
    something else.
    """
```

Implementation: `HEADING_RE.match(line)`; on no match return `None`. Otherwise take group 1, `.strip()`, apply `SEVERITY_SUFFIX_RE.sub("", ...)`, `.strip()` again, and look the lowercased result up in `_SECTION_BY_LOWER`.

Heading level carries no information — `## Must Fix (Critical)` and `#### Must Fix (Critical)` are the same section. Do not branch on the number of `#` characters anywhere.

A line that merely mentions the words is not a heading: prose sentences and bold runs such as `**Must Fix**` have no leading `#` and therefore return `None`.

## 3. `iter_report_lines(report_text)` — fence-aware line iteration

```python
def iter_report_lines(report_text: str):
    """Yield (line, in_fence) for every line of report_text.

    in_fence is True for the fence delimiter lines themselves and for every line
    between an opening and a closing fence.  A line inside a fence is never a
    heading, never a thematic break and never a bullet; it is ordinary text.
    """
```

Implementation: iterate `report_text.splitlines()` with a boolean. When `FENCE_RE.match(line)`, toggle the boolean and yield `(line, True)`. Otherwise yield `(line, in_fence)` with the current value.

Fence delimiters themselves yield `True` so an opening ```` ``` ```` can never be read as a heading. An unterminated fence leaves the remainder of the report inside the fence — that is the fail-closed reading and is correct: nothing after an unterminated fence can open a section.

## 4. Rewrite the body of `harvest()`

Keep the signature exactly as it is: `def harvest(report_text: str, known_rule_ids: set) -> list:`. Keep the returned dict shape exactly as it is: `{"path": ..., "line": ..., "rule_id": ..., "body": ...}` in document order. Keep `flush_finding`'s internals exactly as they are, including the `None.` / `None` exact-equality sentinel skip — **exact equality only, never a substring or `in` test**; a genuine finding whose body contains the word "None" must survive.

Replace the loop with this contract, driven by `iter_report_lines`:

1. **When the line is not inside a fence:**
   - `name = heading_section_name(line)`. If the line matches `HEADING_RE` at all (heading of any level), `flush_finding()` first, then set `current_section = name` (which is `None` for any heading that is not one of the three), clear `current_finding_lines`, and continue to the next line. A heading always ends whatever section was open — a non-findings heading such as `### Step 4: Automated Checks` closes the section rather than extending it.
   - Else if `THEMATIC_BREAK_RE.match(line)`: `flush_finding()`, set `current_section = None`, clear `current_finding_lines`, continue. **This is the fix.** A `---` line is how real review output separates its report body from the diff summary and the closing panel; without it nothing ends the last section and every trailing paragraph is swallowed.
2. **When `current_section is None`, ignore the line entirely** — no finding is opened, nothing is buffered. Preamble prose, the diff summary, the `Step 3a` / `Step 4` trace and the closing panel all land here.
3. **Inside a section**, with `stripped = line.strip()`:
   - If the line is *not* in a fence and `BULLET_RE.match(stripped)` matches: `flush_finding()`, then `current_finding_lines = [match.group(2)]`. **A list item is the only thing that opens a finding.**
   - Else if `stripped` is non-empty **and `current_finding_lines` is non-empty**: append `stripped` as a continuation line of the finding already open.
   - Else: ignore. Non-empty prose in a section where no list item has opened a finding contributes nothing and buffers nothing — this is the mandated `None.` sentinel of an empty section, and it is why a `None.` section followed by a thematic break and a paragraph of summary now yields zero findings instead of one phantom.
   - A blank line inside an open finding is ignored and does **not** close the finding — that is existing behaviour and must not change.
4. After the loop, `flush_finding()` once — end of input is the third and last thing that ends a section.

Do not broaden what opens a finding. Numbered lists, bold-lead paragraphs and table rows are explicitly out of scope (spec Non-goals); adding speculative parsing is how the current fixture drifted from reality.

Do not add any parameter, flag or keyword argument to `harvest()`.

## 5. Add `bench/testdata/real-capture-report.md`

A verbatim capture, not a transcription. Copy the fenced `text` block under `## Reference: captured real output` in `specs/in-progress/003-bench-review-sanity-and-harvest-boundary.md` character for character from its first line (`The diff is only ...`) through its `**Summary:** ...` line. Then append a thematic break line (`---`) and at least three non-empty prose lines standing in for the closing status panel the operator's global memory appends — write generic wording, no personal paths, no `/Users/`, no `~/Documents/`, no machine names.

The file must satisfy all of these, and you must run them:

```
grep -cE '^## (Must Fix|Should Fix|Nice to Have)' bench/testdata/real-capture-report.md   # 3
grep -cE '^#### (Must Fix|Should Fix|Nice to Have)' bench/testdata/real-capture-report.md # 0
grep -c '^\*\*Summary:\*\*' bench/testdata/real-capture-report.md                         # >= 1
grep -c 'fast-uri' bench/testdata/real-capture-report.md                                  # >= 1
grep -c 'mcp/package-lock.json' bench/testdata/real-capture-report.md                     # >= 1
grep -c 'Step 3a: LICENSE Check' bench/testdata/real-capture-report.md                    # >= 1
grep -rn '/Users/\|~/Documents/' bench/testdata/                                          # no output, exit 1
```

The last three content greps are the point of the whole fixture: those literals appear nowhere in `commands/pr-review.md`'s template and cannot be produced by transcribing it. A file hand-written to satisfy only the structural greps reintroduces, at the fixture layer, exactly the template-agrees-with-itself failure this spec exists to close.

Use the filename `bench/testdata/real-capture-report.md` exactly — a later prompt in this spec references it by name.

## 6. Add tests to `bench/test_review.py`

Append new `unittest.TestCase` classes in the existing style. Every test runs offline: no network, no `claude` binary, no GitHub access. Use `run.load_rule_ids(run.REPO_ROOT)` for the id set, as the existing harvest tests do.

1. **`test_real_capture_harvests_to_zero_findings`** (AC8) — read `run.BENCH_DIR / "testdata" / "real-capture-report.md"`, call `run.harvest(text, ids)`, and assert the **full returned list** equals `[]` with `assertEqual(findings, [], f"real capture must harvest to zero findings, got: {findings}")`. Assert on the whole list, not on `len()` — the failure message must print the unexpected findings. This is the exact input that produced the phantom finding.

2. **`test_trailing_prose_does_not_swallow_a_real_finding`** (AC9) — build an inline report with exactly one list-item finding under `## Must Fix (Critical)` citing a rule id that really exists in `rules/index.json` and a `path.ext:NN` reference, `None.` under `## Should Fix (Important)` and `## Nice to Have (Optional)`, then a `---` thematic break and two paragraphs of summary prose (at least one of them beginning `**Summary:**`). Assert the full returned list equals a one-element list whose `body` is exactly the list item's own text with no trailing prose appended, and whose `path` and `line` are the values cited in that item. Compare the whole list with one `assertEqual`, not field by field.

   **The finding's own body MUST contain the literal word `None` as a substring** — write it about a `None` default argument, e.g. a body along the lines of "passing `None` as the default here hides the missing-value case". This is the single case that distinguishes the required implementation from the lazy one: requirement 4 pins the empty-section sentinel to exact equality (`body.strip() in ("None.", "None")`), and a regression to substring membership (`"None" in body`) passes every other test in this prompt while silently discarding any legitimate finding that mentions `None` — a common word in Python review comments. Without this, the D4 fix can regress into a body-substring filter undetected.

3. **`test_heading_level_does_not_change_harvest`** (AC10) — the test method name must contain `heading_level`. Render one identical body of section content at `##`, `###` and `####` (use a loop or an f-string over `("##", "###", "####")`), harvest all three, and assert with a single `assertEqual` that all three lists are equal to each other, with a failure message printing all three lists.

4. **`test_section_name_in_prose_or_fence_is_not_a_heading`** — assert `run.heading_section_name("**Must Fix**")` is `None`, `run.heading_section_name("We looked at Must Fix items.")` is `None`, `run.heading_section_name("## Must Fix (Critical)")` is `"Must Fix"`, `run.heading_section_name("###### nice to have")` is `"Nice to Have"`, and that harvesting a report whose only `## Must Fix (Critical)` line sits inside a ```` ``` ```` fenced block yields `[]`.

5. **`test_thematic_break_ends_a_section`** — a report with `## Nice to Have (Optional)` holding one real list-item finding, followed by `---` and two paragraphs of prose. Assert exactly one finding is returned and its `body` does not contain any word from the trailing prose. Without the thematic-break rule the trailing prose is appended to that finding, so this test fails on the old code for a different reason than test 1 does.

6. **`test_prose_before_a_list_item_opens_nothing`** — a section whose content is `None.` followed by a blank line and then a real list-item finding. Assert exactly one finding is returned, and its body is the list item's text alone with no `None.` prefix. This pins requirement 4.3: prose that opened nothing cannot be extended, and cannot merge into the finding that follows it.

Do not delete, rename, or weaken any of the 13 existing tests in `bench/test_review.py`, and do not touch `bench/test_config.py` or `bench/test_resolve.py`.

## 7. CHANGELOG

`CHANGELOG.md` currently has no `## Unreleased` section — its first version heading is `## v0.35.1`. Insert a `## Unreleased` section immediately above `## v0.35.1` and add a bullet using a conventional prefix (`fix:` — every other CHANGELOG entry uses `feat:`/`fix:`/`docs:` per `docs/changelog-guide.md`; the two non-conforming `bench:` bullets are on v0.35.1, the misclassified release this spec exists because of) describing the harvest section-boundary fix and the new captured fixture. Do not create a version section, do not touch any released section, and do not touch the four version strings in `.claude-plugin/`.

## 8. Do not modify

`bench/testdata/sample-report.md` (its SHA-256 must stay `de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae`), `bench/prs.json`, `bench/README.md`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`.

`bench/testsupport.py`, `process_pr`, `run_bench` and the raw-output cache write are untouched by this prompt — the non-review sanity gate is prompt 2 of this spec. Do not add a gate, a section-presence check, or any new behaviour to `process_pr` here.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no third-party imports, no `requirements.txt`, no `pyproject.toml`, no new top-level files outside `bench/`
- Changes land only in `bench/run.py`, `bench/test_review.py`, `bench/testdata/real-capture-report.md` and `CHANGELOG.md`
- The 42 existing tests keep passing and their assertions are not weakened. Deleting a test, removing an assertion, or relaxing an assertion is not acceptable. The suite's test count after this prompt is strictly greater than 42
- `bench/testdata/sample-report.md` still harvests to its previously asserted 3 findings, unchanged, and the file itself is byte-identical
- Frozen invariants — not configurable, not flagged: the three required section names, the list-item markers that open a finding, the 45-minute review timeout, the cache and results locations, the `--golden` exit-2 rejection
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`. This spec adapts the instrument to the review's real output, never the reverse
- Do NOT broaden what opens a finding: no numbered lists, no bold-lead paragraphs, no tables
- Review output is third-party-influenced text. The harvester only matches and slices text — no value from it is evaluated, passed to a shell, used to build a filesystem path, or used to construct a subprocess argument
- Section, heading, fence and thematic-break matching is line-oriented with bounded patterns; no construct in a report may cause unbounded backtracking or a scan that is not linear in input size
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file, including the new fixture (`docs/dod.md`)
- `CHANGELOG.md` gains an entry under `## Unreleased` (`docs/dod.md`)
- All new tests run offline: no network, no real `claude` binary, no GitHub access
- Do NOT re-harvest or migrate anything already sitting in `bench/.cache/reviews/`
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# Full suite: must be OK with strictly more than 42 tests
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -20

# The new tests exist by name
grep -n 'def test_real_capture_harvests_to_zero_findings\|def test_trailing_prose_does_not_swallow_a_real_finding\|heading_level\|def test_thematic_break_ends_a_section\|def test_prose_before_a_list_item_opens_nothing' bench/test_review.py

# No pre-existing test was deleted or renamed (all 13 originals still present)
for t in test_second_run_is_cache_hit_and_invokes_zero_reviews test_mode_change_is_cache_miss \
         test_cache_path_differs_when_only_mode_differs test_harvest_normalizes_sample_report \
         test_harvest_keeps_finding_without_any_rule_id test_harvest_ignores_empty_section \
         test_ledger_is_append_only_and_atomic test_second_runner_exits_without_touching_ledger \
         test_row_carries_every_required_field test_raw_output_is_cached_verbatim \
         test_failed_review_leaves_no_row_and_no_cache_entry test_failed_pr_does_not_prevent_later_prs \
         test_corrupt_cache_row_is_treated_as_miss; do
  grep -q "def $t" bench/test_review.py || echo "MISSING TEST: $t"
done

# The template-derived fixture is byte-identical (expect the hash below)
sha256sum bench/testdata/sample-report.md
echo "expected: de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae"

# The new fixture is a capture, not a transcription
grep -cE '^## (Must Fix|Should Fix|Nice to Have)' bench/testdata/real-capture-report.md    # expect 3
grep -cE '^#### (Must Fix|Should Fix|Nice to Have)' bench/testdata/real-capture-report.md  # expect 0
grep -c '^\*\*Summary:\*\*' bench/testdata/real-capture-report.md                          # expect >= 1
grep -c 'fast-uri' bench/testdata/real-capture-report.md                                   # expect >= 1
grep -c 'mcp/package-lock.json' bench/testdata/real-capture-report.md                      # expect >= 1
grep -c 'Step 3a: LICENSE Check' bench/testdata/real-capture-report.md                     # expect >= 1

# End-to-end proof the phantom finding is gone and the old fixture is unchanged
python3 -c "
import sys; sys.path.insert(0, 'bench')
import run
ids = run.load_rule_ids(run.REPO_ROOT)
cap = (run.BENCH_DIR / 'testdata' / 'real-capture-report.md').read_text()
old = (run.BENCH_DIR / 'testdata' / 'sample-report.md').read_text()
print('real capture ->', run.harvest(cap, ids))
assert run.harvest(cap, ids) == [], 'real capture must harvest to zero findings'
print('sample-report ->', len(run.harvest(old, ids)), 'findings')
assert len(run.harvest(old, ids)) == 3, 'sample-report must still harvest to 3 findings'
print('OK')
"

# No personal paths, stdlib-only imports
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py

# Unreleased section exists
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; the verbose unittest run prints `OK` and `Ran N tests` with `N > 42`; the `MISSING TEST:` loop prints nothing; the `sha256sum` matches the expected value; the fixture greps print `3`, `0`, and `>= 1` for the four content checks; the inline Python prints `real capture -> []`, `sample-report -> 3 findings` and `OK`; the personal-path grep exits 1 with no output.
</verification>
