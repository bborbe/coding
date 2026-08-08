---
status: completed
spec: [005-bug-bench-harvest-finding-extraction]
summary: 'Implemented positional attribution extraction: rule_id from inline marker (verbatim, no index check) and head-anchored fallback (index-gated), path/line from leading bold reference in four observed shapes, replacing the whole-item membership scan'
execution_id: coding-exec-024-spec-005-attribution-from-reviewer-markers
dark-factory-version: v0.192.9
created: "2026-08-08T11:42:00Z"
queued: "2026-08-08T12:14:19Z"
started: "2026-08-08T12:29:43Z"
completed: "2026-08-08T12:33:54Z"
---

<summary>
- Every finding the benchmark records now carries the file, line and rule the reviewer itself attached to it
- Until now the ledger held thirty findings with zero rule ids, while the raw output carried the tags all along
- The rule id is read from the reviewer's own inline tag and recorded exactly as written, even when that rule is not in the runner's own index
- That matters because a renamed or newly added rule previously vanished into a null, turning attribution into a fact about the runner's bookkeeping rather than the review
- A rule name mentioned in passing — in prose, or in a closing traceability table — is never attributed to a finding it does not belong to
- One legacy shape survives on purpose: when an item carries no inline tag and opens with a rule name the runner already knows, that name is still used, because three findings in a frozen fixture depend on it
- The file reference is read from the front of the item, where the reviewer puts it, in the four shapes it actually writes
- A file path mentioned later in a long finding no longer overrides the one at the front
- No path is ever guessed by searching the repository, and no line number is inferred from surrounding text
- The five previously invisible numbered findings are now locked down with their exact expected attribution
- Third of five prompts; it changes only where attribution comes from, and still writes every item to the ledger
</summary>

<objective>
Read `path`, `line` and `rule_id` from the reviewer's own markers rather than by scanning the whole item against the runner's copy of the rule index: `rule_id` from the item's inline `*(rule: \`<id>\`)*` tag, recorded as the literal string whether or not that id is in `rules/index.json`; `path` and `line` from the bold run at the head of the item, in the four shapes the reviewer actually writes. After this prompt the five numbered Should Fix items in the real capture carry exactly the attribution the capture supplies.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 standard library only, no personal paths, generic examples only, never commit — dark-factory handles git).

Read `specs/in-progress/005-bug-bench-harvest-finding-extraction.md`. This prompt satisfies **Desired Behaviors 3 and 4** and **Acceptance Criteria AC5, AC7 and AC8**. Load-bearing sections: `### RC3 — attribution is coupled to the runner's copy of the rule index`, `## Desired Behavior` items 3 and 4, `## Acceptance Criteria` AC5/AC7/AC8, the `## Non-goals` clause forbidding path inference, `## Constraints`, and the `## Failure Modes` rows for a drifted rule index and for a traceability table.

**This prompt depends on prompts 1 and 2 of this spec having landed.** Verify before you start:

```bash
grep -n 'BOLD_RUN_START_RE\|class HarvestResult\|ORDERED_ITEM_RE\|def list_item_body' bench/run.py
```

If any of the four is absent, stop and report `status: failed` with the message `"prompts 1-2 of spec 005 not yet landed"`. Do not implement them here.

Read `bench/run.py` — specifically `load_rule_ids`, `_extract_rule_id`, `_extract_path_line`, `_normalize_body`, `list_item_body`, `HarvestResult` and `harvest`'s `flush_finding`. Take every signature from the file.

Read `bench/testdata/capture-numbered-findings-h3.md` in full. Its five numbered Should Fix items are the input for AC5 and the source of the four bold-reference shapes in AC8. Read them character by character — the backticks, the quotation marks and the `(~lines 76-94)` parenthetical all matter.

Read `bench/testdata/sample-report.md`. It is **byte-frozen** and its three findings must keep the `rule_id`, `path` and `line` values `TestHarvestNormalizesSampleReport` already asserts. Its items carry no leading bold run and no inline `*(rule: …)*` tag; each begins with a backticked rule id at the head of the item. Requirement 3 below defines the fallback that keeps them green.

Read `bench/test_review.py` — in particular `TestHarvestNormalizesSampleReport`, `TestTrailingProseDoesNotSwallowARealFinding`, `TestHeadingLevelDoesNotChangeHarvest` and `TestProseBeforeAListItemOpensNothing`, all of which assert `path`, `line` or `rule_id` on items whose attribution sits at the head of the item rather than in a bold run.

Read `docs/dod.md` for the repository's Definition of Done.

**Two rule-id sources, in priority order — both are part of the shipped contract.**

Spec Desired Behavior 4 (as amended) names two sources and one asymmetry between them:

1. The item's own inline `*(rule: `<id>`)*` marker always wins, and its value is recorded **verbatim, without checking `rules/index.json`** — that index coupling is the defect RC3 names, and this path is free of it.
2. **Only when no marker is present**, a backticked token at the very head of the item that **is a member of `rules/index.json`** is used. This legacy shape is what the three findings in the byte-frozen `bench/testdata/sample-report.md` depend on; deleting it would null all three and break a frozen fixture's asserted result. It stays index-gated on purpose: at the head of an item, an unknown backticked token is far more likely to be a file path or a symbol than a rule name.

Nothing is ever taken from the middle or the tail of an item, and nothing from outside it, under either source. Spec AC7 Cases C and D lock both halves of the second source — C that a known head token is used, D that an unknown one yields `None`.

This asymmetry is deliberate and **must be documented as such**. Prompt 5 rewrites `bench/README.md`; its text must describe **both** sources and must not claim rule ids are "never validated against `rules/index.json`" without qualifying that to the inline-marker path only. A doc that disagrees with the parser is the exact mechanism behind D1, D2, D4 and D7.
</context>

<requirements>

## 1. Re-verify the fixtures you assert against

```bash
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/capture-numbered-findings-h3.md   # expect 5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/capture-traceability-h4.md        # expect 2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/sample-report.md                  # expect de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae
```

On any mismatch, stop and report `status: failed` with the observed digest. **Never write, regenerate or edit a file under `bench/testdata/`.**

## 2. Add the marker constants

Add to the module constants block in `bench/run.py`, next to `BULLET_RE` / `ORDERED_ITEM_RE`:

```python
RULE_TAG_RE = re.compile(r"\*\(rule:\s*`([^`]+)`\)\*")
HEAD_RULE_TAG_RE = re.compile(r"^`([^`]+)`")
LEADING_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*")
PATH_LINE_RE = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9_./-]+):(\d+)")
BACKTICK_TOKEN_RE = re.compile(r"`([^`\s]+)`")
LINE_MENTION_RE = re.compile(r"(?i)\blines?\s*~?\s*(\d+)")
```

`LEADING_BOLD_RE` is non-greedy so it stops at the first closing `**`, which is where the reviewer's reference ends. `PATH_LINE_RE` is the pattern already inlined in `_extract_path_line`, hoisted to a constant so both call sites share it.

## 3. Replace attribution extraction with positional, priority-ordered rules

Add one function immediately above `_normalize_body`, and route `flush_finding` through it. It operates on the **normalised body** (list marker already removed by `list_item_body`, leading bold run intact), never on raw lines.

```python
def extract_attribution(body: str, known_rule_ids: set) -> tuple[str | None, int | None, str | None]:
    """Return (path, line, rule_id) for one finding item, read from the item's own markers.

    rule_id, in priority order:
      1. the item's own inline `*(rule: `<id>`)*` marker — recorded as the literal
         string the reviewer wrote, whether or not it appears in rules/index.json;
      2. otherwise a backticked token at the very head of the item that is a member
         of known_rule_ids (the shape the review template emits when it tags a
         finding by leading its body with the rule id);
      3. otherwise None.
    An id named anywhere else in the item, or anywhere outside it, is never used.

    path/line, in priority order:
      1. the bold run at the head of the item, when it names a path;
      2. otherwise the first path:line reference anywhere in the item that is not
         a known rule id;
      3. otherwise (None, None).
    When the leading bold run supplies a path, line is taken from that bold run and
    from nowhere else — a line number appearing only in the item's trailing prose is
    not used.  No path is ever inferred by searching the repository and no line is
    ever guessed from surrounding text.
    """
```

Implementation rules, exactly:

**rule_id**
1. `RULE_TAG_RE.search(body)` → return `group(1)` verbatim. Do **not** check membership in `known_rule_ids`. A tag naming a renamed rule, a rule added since the index was written, or a rule from a different rules revision is recorded as written; reconciling it against the shipped rule set is the scorer's job.
2. Else `HEAD_RULE_TAG_RE.match(body)` → if `group(1) in known_rule_ids`, return it.
3. Else `None`.

**path / line**
1. `LEADING_BOLD_RE.match(body)`. If it matches, let `ref = group(1)` and read only from `ref`:
   - `PATH_LINE_RE.search(ref)` → `(group(1), int(group(2)))`. Return.
   - else the first `BACKTICK_TOKEN_RE` match in `ref` whose token contains a `.` → that token is the path; the line is `int(LINE_MENTION_RE.search(ref).group(1))` when that pattern matches `ref`, else `None`. Return.
   - else fall through to step 2 (a bold run that names no path supplies no attribution).
2. `_extract_path_line(body, known_rule_ids)` — the existing whole-item scan, unchanged, which skips tokens that are known rule ids.
3. Else `(None, None)`.

Delete `_extract_rule_id` entirely; it implements exactly the membership scan RC3 identifies as the defect and has no remaining caller. Keep `_extract_path_line` as the step-2 fallback and change nothing inside it except using the hoisted `PATH_LINE_RE`.

In `flush_finding`, drop the `text = " ".join(current_finding_lines)` variable and its two uses, and call `extract_attribution(body, known_rule_ids)` once after the `None.` sentinel check. Both extractors must read the same normalised `body`, so that `^` anchoring means "the head of the item".

`known_rule_ids` stays in `harvest`'s signature and stays wired from `load_rule_ids` in `run_bench` — it is still consulted, for the head-anchored fallback and for the `_extract_path_line` skip list only.

## 4. The four bold-reference shapes, verified against the capture

These are the four shapes the capture actually contains. Your implementation must produce exactly these results:

| Leading bold run | `path` | `line` |
|---|---|---|
| ``**`CHANGELOG.md:18`**`` | `CHANGELOG.md` | 18 |
| ``**`README.md` "Security gates" section (~lines 76-94)**`` | `README.md` | 76 |
| ``**`.github/workflows/ci.yml:32`**`` | `.github/workflows/ci.yml` | 32 |
| ``**CI + `Makefile.precommit`**`` | `Makefile.precommit` | `None` |

Note the third: `PATH_LINE_RE` must match a path that begins with a dot. Note the fourth: a bold run may carry ordinary words around the backticked path, and a backticked token with no dot (for example `` `trivy` `` in the fifth capture item) is not a path.

## 5. Tests

Add to `bench/test_review.py`. Every failure message prints the full observed list.

**AC5 — the five previously-dropped numbered findings carry the capture's attribution.** `class TestNumberedCaptureFindingsCarryAttribution`, one test method that harvests `bench/testdata/capture-numbered-findings-h3.md` and compares paths, lines, rule ids and the count together:

```python
expected = [
    ("CHANGELOG.md", 18, "changelog/conventional-prefix-required"),
    ("README.md", 76, "readme/user-facing-not-agent-context"),
    (".github/workflows/ci.yml", 32, None),
    ("Makefile.precommit", None, None),
    ("Makefile.precommit", None, None),
]
```

Assert `[(f["path"], f["line"], f["rule_id"]) for f in result.findings[:5]] == expected` and assert `len(result.findings) == 7`. The trailing two are the `### Nice to Have (Optional)` bullets; prompt 4 of this spec reclassifies them as unattributable and updates this count to `5` — do not anticipate that here, and do not weaken the assertion to an inequality.

**AC7 — `rule_id` comes from the reviewer's marker first, and from an index-gated head-anchored token second.** `class TestRuleIdComesFromTheItemsOwnMarkers`, four test methods, one per spec AC7 case:

- Case A — an item tagged with an id absent from `rules/index.json` yields that literal string, not `None`:

  ```
  ## Must Fix (Critical)
  - **`src/x.py:1`** something is wrong here. *(rule: `made-up/not-in-the-index`)*
  ```

  Assert `rule_id == "made-up/not-in-the-index"`, and assert in the same test that `"made-up/not-in-the-index" not in run.load_rule_ids(run.REPO_ROOT)` so the case cannot silently become vacuous if someone adds that id.

- Case B — an item whose prose names a different, real rule id **before** its own marker yields the marker's id. Pick two distinct real ids from `run.load_rule_ids(run.REPO_ROOT)` at test time rather than hardcoding them, assert they differ, put one in the prose and the other in the marker, and assert the marker's id is returned. A first-membership-match scan passes Case A alone; this is what closes it.

- **Case C** — an item carrying **no** marker whose body opens with a backticked token that **is** a member of `rules/index.json` yields that id:

  ```
  ## Must Fix (Critical)
  - `<real-id>`: a finding in src/x.py:1
  ```

  Pick `<real-id>` from `run.load_rule_ids(run.REPO_ROOT)` at test time rather than hardcoding it, and shape the item so the token sits at position 0 of the normalised body — the head anchor cannot see past a leading bold run. Assert `rule_id == <real-id>`. This is the head-anchored legacy shape the byte-frozen `sample-report.md` depends on for three findings; `TestHarvestNormalizesSampleReport` is only an indirect guard and, as spec AC7 states, would not survive a refactor of that fixture's test.

- **Case D** — the same shape whose head token is **absent** from `rules/index.json` yields `None`:

  ```
  ## Must Fix (Critical)
  - `not-a-real-rule-id`: a finding in src/x.py:7
  ```

  Assert `rule_id is None`, assert `path == "src/x.py"` and `line == 7`, and assert in the same test that `"not-a-real-rule-id" not in run.load_rule_ids(run.REPO_ROOT)` so the case cannot become vacuous. **The item must carry a path** — without one it yields neither `path` nor `rule_id`, and prompt 4 would reclassify it as unattributable, moving it out of `result.findings` and breaking this assertion.

  **Case D is the only test in the whole suite that fails if the index gate on the head-anchored source is dropped.** Against an implementation that records any head-anchored backticked token as a rule id, every other test stays green: `sample-report.md`'s head tokens are all real ids; the five capture items and every AC8 synthetic open with `**`; Cases A and B carry markers; the traceability item opens with `**`; and `TestHarvestKeepsFindingWithoutAnyRuleId` has no head backtick. Do not omit or merge this case.

**AC8 — `path` and `line` come from the leading bold reference.** `class TestPathAndLineComeFromTheLeadingBoldReference`, with:

- one assertion per row of the table in requirement 4, over synthetic single-item sections carrying that exact bold run;
- a negative case: an item whose leading bold reference names `a/b.py:10` and whose trailing prose mentions `c/d.py:99` resolves to `("a/b.py", 10)`. **This is a shape check, not a regression guard — it also passes against the unchanged parser**, because `_extract_path_line` (`bench/run.py:1028`) scans the whole item and returns the *first* `path:line` match, which for this input is already the leading one. Keep it, but do not treat its green as evidence the change works;
- a second negative case: an item whose leading bold run names a path with no line (``**`a/b.py`**``) and whose trailing prose mentions `line 42` resolves to `("a/b.py", None)` — a line appearing only in the prose is not used when the bold run supplies the path;
- **a third negative case, the discriminating one — do not omit it and do not merge it into the case above**: an item whose leading bold run names a path with **no** line (``**`a/b.py`**``) and whose trailing prose carries a **full** `c/d.py:99` reference resolves to `("a/b.py", None)`. The shipped parser returns `("c/d.py", 99)` for this input (verified), so this is the one AC8 case that is **red before the change and green after**. Without it, every AC8 negative case is satisfiable with zero code change.

**AC9 completion.** Add one assertion to the existing `TestBodyPreservesLeadingBoldRun` test created by prompt 2: `result.findings[0]["path"] == "src/config.ts"`. Do not remove any assertion already in that method.

**AC10 Case B regression.** The existing outside-section test that asserts no harvested `rule_id` from `bench/testdata/capture-traceability-h4.md` is drawn from its `### Traceability` table must stay green. It is now non-vacuous: the table sits outside the item and outside the section, and `RULE_TAG_RE` never reaches it.

**Frozen-fixture regression.** `TestHarvestNormalizesSampleReport` must still pass unchanged, including its final loop asserting every non-null `rule_id` is a member of the real index. If it goes red, the head-anchored fallback in requirement 3 is wrong — fix the fallback, never the fixture and never the assertion.

## 6. Failure handling and safety

- Every new pattern is anchored or bounded, contains no nested quantifier, and cannot backtrack unboundedly. `LEADING_BOLD_RE` is non-greedy and anchored at `^`; an item with no closing `**` simply does not match and falls through to the whole-item scan.
- `extract_attribution` never raises: every `search`/`match` result is checked for `None` before `group` is called, and `int(...)` is only reached on a `(\d+)` capture.
- **Extracted values are data, never paths.** A `path` or `rule_id` read out of review output is written to the ledger row and used for nothing else — never opened, never stat-ed, never joined onto a filesystem root, never passed to a subprocess, never compared against the filesystem. A review emitting ``**`../../etc/passwd:1`**`` produces a ledger row containing that string and no filesystem access. Add a test asserting exactly that: harvest a section carrying that item and assert `path == "../../etc/passwd"` and `line == 1`, with no file access anywhere in the code path.
- `harvest` remains a pure function over text, linear in input size, and still never raises for malformed input.

</requirements>

<constraints>
- **Python 3 standard library only.** No third-party imports, no new top-level files outside `bench/`. Changes land only in `bench/run.py` and `bench/test_review.py` in this prompt.
- **Never create, regenerate, overwrite or edit any file under `bench/testdata/`.** On a digest mismatch, stop and report failed.
- **`bench/testdata/sample-report.md` and `bench/testdata/real-capture-report.md` are byte-frozen** and must still harvest to their previously asserted results, including every `rule_id`, `path` and `line` value already asserted.
- **Do NOT infer a path by searching the repository** for a filename mentioned in a finding's prose, and do NOT guess a line number from surrounding text. Attribution comes from the reviewer's markers or it does not come at all.
- **Do NOT add the unattributable-item classification or any runner-side rejection in this prompt.** `HarvestResult.unattributable` stays empty; every item still becomes a finding. Prompt 4 of this spec owns that.
- **No test function may be deleted and no assertion relaxed.** Per-file assertion floors that must hold after this prompt: `grep -cE '^\s*(self\.assert|assert )' bench/test_config.py` ≥ 63, `bench/test_resolve.py` ≥ 46, `bench/test_review.py` ≥ 165. The suite's test count must stay strictly greater than 72.
- **Do NOT change the `NOT A REVIEW` gate.**
- **Do NOT change `bench/prs.json`, `commands/pr-review.md`, or any rule, agent, command or doc that participates in a review.**
- **Do NOT make the inline rule-tag marker shape configurable** and do NOT add any flag, env var or opt-out. It is a frozen invariant.
- **Do NOT touch the raw-stdout-before-parsing ordering** in `process_pr`.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file.
- Bench tests must not require network access, a real `claude` binary, or GitHub access.
- Do not read from or write to `bench/.cache/` or `bench/results/`.
- Do NOT edit `bench/README.md` or `CHANGELOG.md` in this prompt — prompt 5 of this spec owns both (spec 005 AC16/AC17). `docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" criterion is deliberately deferred to prompt 5 and its absence here is **expected — do NOT report it as a blocker** and do NOT add an entry to satisfy it.
- Do NOT commit — dark-factory handles git.
</constraints>

<verification>
```
# Prompts 1-2 landed (precondition, not a new check)
grep -n 'BOLD_RUN_START_RE\|class HarvestResult\|ORDERED_ITEM_RE\|def list_item_body' bench/run.py

# Fixtures untouched
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/capture-numbered-findings-h3.md
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/capture-traceability-h4.md
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/sample-report.md
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/real-capture-report.md

# The membership scan is gone and the positional extractors exist
grep -n 'def _extract_rule_id' bench/run.py ; echo "exit=$? (expect 1 — deleted)"
grep -n 'RULE_TAG_RE\|HEAD_RULE_TAG_RE\|LEADING_BOLD_RE\|BACKTICK_TOKEN_RE\|LINE_MENTION_RE\|def extract_attribution' bench/run.py

# AC5 — the five numbered items now carry their attribution
python3 - <<'EOF'
import sys, json, pathlib
sys.path.insert(0, 'bench')
import run as R
ids = R.load_rule_ids(pathlib.Path('.'))
r = R.harvest(pathlib.Path('bench/testdata/capture-numbered-findings-h3.md').read_text(), ids)
for f in r.findings:
    print(json.dumps({k: f[k] for k in ('path', 'line', 'rule_id')}))
EOF

# Frozen fixture still attributes as before
python3 - <<'EOF'
import sys, json, pathlib
sys.path.insert(0, 'bench')
import run as R
ids = R.load_rule_ids(pathlib.Path('.'))
r = R.harvest(pathlib.Path('bench/testdata/sample-report.md').read_text(), ids)
for f in r.findings:
    print(json.dumps({k: f[k] for k in ('path', 'line', 'rule_id')}))
EOF

# Assertion floors (AC15)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 165

# Full suite and repository gate
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
make precommit
```

Expected: the four digests are unchanged; the `_extract_rule_id` grep exits 1; the numbered-capture replay prints the five AC5 rows in order followed by two rows of all-nulls; the sample-report replay prints `agents/my-agent.md` / `3` / `agent-cmd/agent-frontmatter`, then `null` / `null` / `agent-cmd/command-thin`, then `null` / `null` / `changelog/unreleased-entry-required`; the unittest run reports `OK` with `Ran N tests`, `N > 72`, and lists the rule-tag, leading-bold-reference and numbered-capture tests by name; `make precommit` exits 0.
</verification>
