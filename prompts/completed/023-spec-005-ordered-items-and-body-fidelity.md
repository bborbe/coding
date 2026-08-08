---
status: completed
spec: [005-bug-bench-harvest-finding-extraction]
summary: Ordered list items now open findings, fenced code block items are suppressed, and leading bold run in body is preserved
execution_id: coding-exec-023-spec-005-ordered-items-and-body-fidelity
dark-factory-version: v0.192.9
created: "2026-08-08T11:41:00Z"
queued: "2026-08-08T12:14:19Z"
started: "2026-08-08T12:24:56Z"
completed: "2026-08-08T12:29:41Z"
---

<summary>
- The benchmark now sees the findings the reviewer writes as a numbered list, which it previously discarded entirely
- These are the reviewer's most severe tier, so the instrument was losing precisely the findings that matter most
- Numbering does not have to start at one and is not limited to single digits — a list starting at three and running to ten counts every item
- Bulleted and numbered items are treated identically; both open one finding per item, in the order the reviewer wrote them
- A list written inside a fenced code block is example text, not a finding, and is now ignored as such
- A finding's text keeps the reviewer's emphasis intact — the leading bold run is no longer half-eaten as though it were a second list marker
- That corruption mattered because it chewed exactly the position where the file reference lives
- One real capture carrying a bold-headed finding is locked down as a regression fixture
- Second of five prompts; it changes only what opens a finding and what its text looks like
- Attribution — where the path, line and rule id come from — is deliberately left to the next prompt
</summary>

<objective>
Make an ordered list item open a finding exactly as an unordered one does, suppress list items inside fenced code blocks, and stop the body normaliser from stripping an asterisk off the item's leading bold run. After this prompt the five numbered Should Fix items in the real capture are visible to the harvester as five findings, in document order, and the one bold-headed finding in the traceability capture keeps its `**` intact.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 standard library only, no personal paths, generic examples only, never commit — dark-factory handles git).

Read `specs/in-progress/005-bug-bench-harvest-finding-extraction.md`. This prompt satisfies **Desired Behavior 2** and **Acceptance Criteria AC6 and AC9**. Load-bearing sections: `### RC2 — numbered items are invisible`, `### Bonus defect, same layer`, `## Acceptance Criteria` AC6/AC9, `## Constraints`.

**This prompt depends on prompt 1 of this spec having landed.** Verify before you start:

```bash
grep -n 'BOLD_RUN_START_RE\|class HarvestResult' bench/run.py
```

If either is absent, stop and report `status: failed` with the message `"prompt 1 of spec 005 not yet landed"`. Do not implement prompt 1's changes here.

Read `bench/run.py` — specifically the constants block (`BULLET_RE`, `FENCE_RE`, `BOLD_RUN_START_RE`), `iter_report_lines`, `_normalize_body`, `HarvestResult` and `harvest`. Take every signature from the file.

Read `bench/testdata/capture-numbered-findings-h3.md` in full. Its `### Should Fix (Important)` section carries five items numbered `1.` through `5.`; its `### Nice to Have (Optional)` section carries two `- ` bullets; its `### Positive notes` heading is not a severity section.

Read `bench/testdata/capture-traceability-h4.md` in full. Its `#### Should Fix (Important)` section carries exactly one item that begins `- **No test coverage for \`src/config.ts\`'s new validation logic.**`. Under the shipped parser the harvested body begins `*No test coverage for` — one asterisk short.

Read `bench/test_review.py` for the existing test style, in particular `TestHarvestNormalizesSampleReport` and `TestSectionNameInProseOrFenceIsNotAHeading`.

Read `docs/dod.md` for the repository's Definition of Done.
</context>

<requirements>

## 1. Re-verify the fixtures you assert against

Before writing any test, confirm the two fixtures this prompt reads are still the operator-installed captures:

```bash
shasum -a 256 bench/testdata/capture-numbered-findings-h3.md | cut -d' ' -f1   # expect 5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93
shasum -a 256 bench/testdata/capture-traceability-h4.md | cut -d' ' -f1        # expect 2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c
```

On any mismatch, stop and report `status: failed` with the observed digest. **Never write, regenerate or edit a file under `bench/testdata/`.**

## 2. Recognise ordered list items

Add a module constant next to `BULLET_RE`:

```python
ORDERED_ITEM_RE = re.compile(r"^\s{0,3}\d+\.\s+(.+)$")
```

A run of one or more digits followed by `.` and at least one space opens a finding. The numbering need not start at 1 and is not limited to one digit — `3.` and `10.` both open findings.

Add a helper immediately above `_normalize_body`:

```python
def list_item_body(stripped_line: str) -> str | None:
    """Return the item text when stripped_line opens a list item, else None.

    Both list styles the reviewer uses open a finding: an unordered item
    (`-` or `*` followed by whitespace) and an ordered item (a run of digits
    followed by `.` and whitespace).  The marker is removed; nothing else about
    the text is changed, so a leading bold run survives intact.
    """
    m = BULLET_RE.match(stripped_line)
    if m:
        return m.group(2)
    m = ORDERED_ITEM_RE.match(stripped_line)
    if m:
        return m.group(1)
    return None
```

In `harvest`, replace the two-step `if stripped and BULLET_RE.match(stripped): ... current_finding_lines = [BULLET_RE.match(stripped).group(2)]` with a single call to `list_item_body(stripped)`, opening a finding when it returns a non-`None` value. Do not call the regex twice.

`ORDERED_ITEM_RE` must not be reachable for a line inside a fenced block — see requirement 3.

## 3. Suppress list items inside fenced code blocks

`iter_report_lines` already yields `in_fence` for every line, but the item-matching tail of `harvest` runs outside the `if not in_fence:` guard, so today a list item inside a fenced code block opens a finding. Fix it: when `in_fence` is true, a line is ordinary text — it opens nothing. It may still extend a finding that is already open (a fenced snippet inside a finding is part of that finding's text), so the continuation branch stays reachable.

Concretely, the item branch becomes conditional on `not in_fence`:

```python
        item = list_item_body(stripped) if (stripped and not in_fence) else None
        if item is not None:
            flush_finding()
            current_finding_lines = [item]
        elif stripped and current_finding_lines:
            current_finding_lines.append(stripped)
```

The existing `test_fence_contains_heading_not_a_section` must stay green.

## 4. Preserve the leading bold run in the body

`_normalize_body` receives item text from which the list marker has **already** been removed, then strips one more leading `*` or `-`:

```python
    body = lines[0]
    if body.startswith(("*", "-")):
        body = body[1:].lstrip()
```

That second strip is the bonus defect: on `**No test coverage for …` it eats one asterisk of the emphasis, corrupting the body at exactly the position where the path reference lives. Delete those three lines. `_normalize_body` now only joins the item's lines and collapses runs of whitespace:

```python
def _normalize_body(lines: list[str]) -> str:
    """Join an item's lines into one whitespace-collapsed string.

    The list marker was already removed by list_item_body; nothing else is
    stripped, so the item's leading bold run is preserved verbatim.
    """
    body = " ".join(lines)
    return re.sub(r"\s+", " ", body).strip()
```

The `None.` sentinel check in `flush_finding` compares `body.strip()` against `("None.", "None")` and is unaffected — leave it exactly as it is.

## 5. Tests

Add to `bench/test_review.py`. Every assertion compares against a `HarvestResult` and prints the observed lists on failure.

**AC6 — ordered-item recognition is general, not fitted to the capture.** `class TestOrderedAndUnorderedItemsBothOpenFindings`, two test methods:

- A synthetic severity section mixing both list styles, with ordered numbering that starts at `3.` and includes a two-digit marker. Use exactly this section body so every item stays attributable under the later prompts of this spec:

  ```
  ## Must Fix (Critical)
  - **`a/one.py:1`** first item, unordered dash.
  * **`a/two.py:2`** second item, unordered star.
  3. **`a/three.py:3`** third item, ordered starting at three.
  4. **`a/four.py:4`** fourth item.
  10. **`a/ten.py:10`** fifth item, two-digit marker.
  ```

  Assert exactly five findings, and assert the list of `path` values equals `["a/one.py", "a/two.py", "a/three.py", "a/four.py", "a/ten.py"]` — that is document order, and it is what proves a parser keyed to `1.`–`5.` does not pass.

- A negative case: an ordered item inside a fenced code block within a severity section yields no finding. Build a report whose `## Should Fix (Important)` section reads `None.`, then a blank line, then a fenced block (three backticks) containing the line `1. this ordered item is inside a fence and is not a finding`, then the closing fence. Assert **both** `result.findings == []` **and** `result.unattributable == []`, with a failure message printing both lists. Asserting only `findings` lets an implementation classify the fenced line as an unattributable item instead of ignoring it — findings is still empty, and the PR would then fail loudly on example text inside a code block, which is the same sign-flipped failure prompt 1's AC3/AC4 guard against.

**AC9 — the body preserves the leading bold run verbatim.** `class TestBodyPreservesLeadingBoldRun`, one test method that harvests `bench/testdata/capture-traceability-h4.md` and asserts:

- exactly one finding,
- `result.findings[0]["body"].startswith("**No test coverage for")` — two asterisks, with a failure message printing the first 60 characters of the observed body,
- `result.unattributable == []`.

Prompt 3 of this spec adds one further assertion to this same test method (`result.findings[0]["path"] == "src/config.ts"`); do not add it here, because the leading-bold-reference extraction it depends on does not exist yet.

**Sibling-test re-anchor (required).** Prompt 1 added `TestContentOutsideASeveritySectionIsNeverAFinding`, whose Case A probes this same fixture by asserting four distinctive substrings appear in no harvested body. Once ordered items open findings, the fixture's harvest grows from 2 findings to 7, and a substring that sat inside a previously-invisible Should Fix item becomes reachable. If prompt 1's four substrings are `"build-backend switch is clean"`, `"mktemp"`, `"S104"` and `"TestClient"`, none of them moves and the probe stays green — verify that and move on. If you instead find a probe substring that has gone red (`"pip-audit"` at fixture line 15 is the known case, inside Should Fix item 4), **re-anchor that probe** to a substring that occurs exactly once in the fixture and only inside a `### Positive notes` bullet.

Re-anchoring a probe substring is **not** "relaxing an assertion" under requirement 5's constraint: the assertion count is unchanged and the property under test — no positive-note content is ever harvested — is unchanged; only the token used to observe it moves off a collision. Do not delete the test, do not drop one of its cases, do not weaken it to a membership check, and do not edit the fixture. If you cannot find a non-colliding substring, stop and report rather than removing the case.

**Regression guard.** `bench/testdata/sample-report.md` must still harvest to its three previously asserted findings and `bench/testdata/real-capture-report.md` to zero. Neither file may be edited.

## 6. Failure handling

Matching stays line-oriented and bounded: `ORDERED_ITEM_RE` is anchored, has no nested quantifier and cannot backtrack unboundedly on a line of thousands of list markers. `harvest` still never raises for malformed input, never opens a file and never invokes a subprocess, and remains linear in input size. An unclosed fence yields a wrong section boundary at worst, never a hang.

</requirements>

<constraints>
- **Python 3 standard library only.** No third-party imports, no new top-level files outside `bench/`. Changes land only in `bench/run.py` and `bench/test_review.py` in this prompt.
- **Never create, regenerate, overwrite or edit any file under `bench/testdata/`.** On a digest mismatch, stop and report failed.
- **`bench/testdata/sample-report.md` and `bench/testdata/real-capture-report.md` are byte-frozen** and must still harvest to their previously asserted results.
- **No test function may be deleted and no assertion relaxed.** Per-file assertion floors that must hold after this prompt: `grep -cE '^\s*(self\.assert|assert )' bench/test_config.py` ≥ 63, `bench/test_resolve.py` ≥ 46, `bench/test_review.py` ≥ 165. The suite's test count must stay strictly greater than 72.
- **Do NOT change the `NOT A REVIEW` gate.**
- **Do NOT change `bench/prs.json`, `commands/pr-review.md`, or any rule, agent, command or doc that participates in a review.**
- **Do NOT make the list-item markers configurable** and do NOT add any flag, env var or opt-out. They are frozen invariants.
- **Do NOT change attribution extraction in this prompt.** `_extract_rule_id` and `_extract_path_line` are prompt 3's subject; leave them exactly as they are.
- **Do NOT touch the raw-stdout-before-parsing ordering** in `process_pr`.
- **Harvested values are data, never paths.** No value read out of review output is opened, stat-ed, joined onto a filesystem root, or passed to a subprocess.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file.
- Bench tests must not require network access, a real `claude` binary, or GitHub access.
- Do not read from or write to `bench/.cache/` or `bench/results/`.
- Do NOT edit `bench/README.md` or `CHANGELOG.md` in this prompt — prompt 5 of this spec owns both (spec 005 AC16/AC17). `docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" criterion is deliberately deferred to prompt 5 and its absence here is **expected — do NOT report it as a blocker** and do NOT add an entry to satisfy it.
- Do NOT commit — dark-factory handles git.
</constraints>

<verification>
```
# Prompt 1 landed (precondition, not a new check)
grep -n 'BOLD_RUN_START_RE\|class HarvestResult' bench/run.py

# Fixtures untouched
shasum -a 256 bench/testdata/capture-numbered-findings-h3.md | cut -d' ' -f1
shasum -a 256 bench/testdata/capture-traceability-h4.md | cut -d' ' -f1
shasum -a 256 bench/testdata/sample-report.md | cut -d' ' -f1        # expect de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae
shasum -a 256 bench/testdata/real-capture-report.md | cut -d' ' -f1  # expect be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db

# The new recognition surface exists and the double-strip is gone
grep -n 'ORDERED_ITEM_RE\|def list_item_body\|def _normalize_body' bench/run.py
grep -n 'startswith((\"\*\", \"-\"))' bench/run.py ; echo "exit=$? (expect 1 — the extra strip is deleted)"

# The five numbered items are now visible — ASSERTED, not printed.
# `print` always exits 0 and the daemon does not gate on verification exit codes,
# so a harvest yielding 2, or 5, or 7-with-corrupted-bodies would otherwise "pass"
# the one check that proves this prompt's headline objective.
python3 - <<'EOF'
import sys, pathlib
sys.path.insert(0, 'bench')
import run as R
ids = R.load_rule_ids(pathlib.Path('.'))
r = R.harvest(pathlib.Path('bench/testdata/capture-numbered-findings-h3.md').read_text(), ids)
bodies = [f['body'] for f in r.findings]
print('findings', len(bodies))
for b in bodies:
    print('   ', b[:70])

assert len(bodies) == 7, f"expected 7 findings, got {len(bodies)}: {bodies}"
expected_prefixes = [
    '**`CHANGELOG.md:18`**',
    '**`README.md`',
    '**`.github/workflows/ci.yml:32`**',
    '**CI + `Makefile.precommit`**',
    '**`Makefile.precommit` `trivy` target**',
]
for i, pfx in enumerate(expected_prefixes):
    assert bodies[i].startswith(pfx), f"body {i} must start with {pfx!r}, got {bodies[i][:80]!r}"

# The traceability capture proves the _normalize_body bold-run fix: both asterisks survive.
t = R.harvest(pathlib.Path('bench/testdata/capture-traceability-h4.md').read_text(), ids)
assert len(t.findings) == 1, f"expected 1 finding, got {len(t.findings)}"
assert t.findings[0]['body'].startswith('**No test coverage for'), \
    f"leading bold run was mangled: {t.findings[0]['body'][:80]!r}"

print('replay assertions OK')
EOF

# Assertion floors (AC15)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 165

# Full suite and repository gate
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
make precommit
```

Expected: the four digests are unchanged; the extra-strip grep exits 1; the replay ends with `replay assertions OK` (any `AssertionError` is a failure, not a diagnostic) and reports `findings 7` for the numbered capture (five Should Fix items plus the two Nice to Have bullets — the two become unattributable in prompt 4, not here) and the first five bodies begin `**\`CHANGELOG.md:18\`**`, `**\`README.md\` …`, `**\`.github/workflows/ci.yml:32\`**`, `**CI + \`Makefile.precommit\`**`, `**\`Makefile.precommit\` \`trivy\` target**`; the unittest run reports `OK` with `Ran N tests`, `N > 72`, and lists the ordered-item and body-fidelity tests by name; `make precommit` exits 0.
</verification>
