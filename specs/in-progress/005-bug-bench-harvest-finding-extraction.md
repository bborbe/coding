---
status: prompted
tags:
    - dark-factory
    - spec
approved: "2026-08-08T11:24:09Z"
generating: "2026-08-08T12:14:23Z"
prompted: "2026-08-08T12:14:23Z"
branch: dark-factory/bug-bench-harvest-finding-extraction
---

## Summary

- The bench runner's HARVEST layer turns review output into a list of findings. It does not parse the shapes the reviewer actually emits, and it fails in both directions at once: it invents findings that were never written, and it drops findings that were.
- **Trailing housekeeping bullets become findings.** A review whose three severity sections all read `None.` — the correct answer, zero — was harvested as three findings, verbatim the three bullets of a trailing `**Notes:**` block. v0.35.2 gave sections an end boundary; a non-heading bold label is not one, so the section stays open and swallows whatever bullets follow.
- **Numbered findings are invisible.** The reviewer writes its more severe tiers as `1.` / `2.` / `3.` lists. Only `-` and `*` open a finding, so a capture carrying five numbered Should Fix items harvested to two — the two Nice to Have bullets. The parser loses precisely the findings that matter most.
- **Attribution is absent from every finding.** Across all runs to date the harvester has produced 30 findings with 9 paths, 9 lines, and zero rule ids — while the raw output carries inline `*(rule: …)*` tags and a bold `path:line` reference at the head of nearly every item. The data is in the output and nothing reads it.
- The governing repair: the harvester extracts what the review contract defines or refuses loudly. A finding it cannot attribute is a parse failure, not a body-only finding. This is the fifth defect in one family — a layer emitting a plausible wrong number instead of refusing — and the first four (D1, D2, D4, D7) all recurred because the fixtures were written from the same template the parser was written from. The fixtures this spec mandates are four verbatim captures of real review output, two of which carry real findings; every capture checked in before now carried zero, which is why no fixture in the repository has ever exercised the parser against a real finding.

## Problem

The benchmark exists to produce a number that can be compared across configurations. The HARVEST layer decides what that number is, and it is currently wrong in both directions on real input — simultaneously, on the same run. On a review that correctly found nothing, it recorded three findings scraped from a trailing notes block. On a review that found seven things, it recorded two, discarding all five of the numbered items and every path, line and rule id the reviewer had attached to them. Neither failure is visible in the result file: a fabricated finding is byte-shaped exactly like a real one, and a dropped finding leaves no trace at all. For a measurement instrument this is worse than a crash — a crash gets investigated, `3 findings` gets recorded, averaged into a score, and cited. It already has been: three AC18 runs from spec 004 were written up as evidence of model non-determinism, with spreads of 0–5 and 1–6 findings, before the raw captures showed the counts were partly tracking how many housekeeping bullets the reviewer happened to append. The noise floor is therefore unmeasured, and the downstream task "Bootstrap and Score the Golden Finding Set" is blocked outright, because precision and recall need a stable per-finding key — a path, a line, a rule id — and the harvester currently produces findings with none of the three.

## Goal

Every finding the runner writes down corresponds to an item the reviewer actually wrote inside a severity section, carries the attribution the reviewer attached to it, and is keyed stably enough to be matched against a golden set. Content the reviewer placed outside a severity section — a trailing notes block, a positive-notes list, a traceability table, a closing summary — is never a finding, at any heading level and whatever label introduces it. Items the reviewer wrote as numbered lists are findings exactly as bullets are. `path`, `line` and `rule_id` come from the reviewer's own markers in its own output, not from the runner's copy of the rule index. And an item inside a severity section that the runner cannot attribute fails that PR loudly, in the same class as the existing `NOT A REVIEW` gate — the runner never silently falls back to a body-only finding, because a body-only finding is an unmatchable measurement dressed as a data point. The fixtures that lock all of this down are verbatim captures of live review output carrying real findings, and the harvest contract is written down beside them.

## Non-goals

- Do NOT change any rule, agent, command, or doc that participates in a review, including `commands/pr-review.md`. The measured configuration stays fixed while the instrument is repaired — this is inherited unchanged from specs 003 and 004. If the loud-failure rule proves that the review command must mandate an attribution on every finding, that is a separate spec against the reviewed configuration, filed with its own baseline impact.
- Do NOT build scoring, a golden set, or any precision/recall semantics. `--golden` stays reserved-and-rejected with exit 2, exactly as it is today. This spec makes the key that scoring needs exist; it does not consume it.
- Do NOT change the `NOT A REVIEW` gate's own semantics — which sections are required, what counts as a heading, the bounded excerpt, or what it accepts. This spec adds a second rejection class downstream of it and leaves the first one untouched.
- Do NOT change the plugin preflight, the ref pruning, or the failure-artifact writer shipped in v0.35.3. This spec touches the harvest layer and the per-PR control flow immediately around it.
- Do NOT re-harvest, migrate, or re-validate rows and raw outputs already written. Rows recorded before this change carry fabricated and missing findings; the recovery is to delete `bench/.cache/reviews/` and `bench/results/` and re-run, which the README already states.
- Do NOT infer a path by searching the repository for a filename mentioned in a finding's prose, and do NOT guess a line number from surrounding text. Attribution comes from the reviewer's markers or it does not come at all — inference is how an instrument starts agreeing with what you hoped.
- Do NOT make the section terminators, the list-item markers, the rule-tag marker, or the unattributable-item rejection configurable. All four are invariants; if a future consumer demands variation, that is a separate spec.
- Do NOT add an opt-out that lets a run accept body-only findings. An escape hatch on this Goal is the regression this spec exists to close.
- Do NOT change `bench/prs.json` — schema, entries, and `dev-1` version are frozen inputs.

## Reproduction

Runner version: `CHANGELOG.md` head is `v0.35.3`; bench suite is 72 tests, all green (`python3 -m unittest discover -s bench -p 'test_*.py'` → `Ran 72 tests` / `OK`).

Raw captures live under `bench/.cache/reviews/*.stdout.txt`, which is gitignored (`.gitignore:9` — `/bench/.cache/`) and therefore local to the operator's host. Five captures are present from two runs, both `sonnet` / `medium`, one `short` and one `full`. Replaying the shipped harvester over them:

```bash
python3 - <<'EOF'
import sys, json, pathlib
sys.path.insert(0, 'bench')
import run as R
ids = R.load_rule_ids(pathlib.Path('.'))
for f in sorted(pathlib.Path('bench/.cache/reviews').glob('*.stdout.txt')):
    out = R.harvest(f.read_text(), ids)
    print(f.name.split('__')[1], len(out))
    for o in out:
        print('   ', json.dumps(o)[:160])
EOF
```

### Observed, capture by capture

| Capture | Mode | Heading level | Findings the reviewer wrote | Findings harvested | Correct |
|---|---|---|---|---|---|
| `dc7efd9d…__node-skeleton_2` | short | `##` | 0 | **3** | no — all three invented |
| `dc7efd9d…__github-pr-review-agent_11` | short | `####` | 0 | 0 | yes |
| `dc7efd9d…__tts-mcp_20` | short | `####` | 0 | 0 | yes |
| `ce1703bc…__node-skeleton_2` | full | `####` | 1 | 1 | body corrupted, unattributed |
| `ce1703bc…__python-skeleton_3` | full | `###` | 7 | **2** | no — five dropped |

Aggregate over these five captures: 8 findings written, 6 harvested, of which 3 are genuine. Precision 3/6, recall 3/8. Zero of the 6 carry a non-null `path`, `line` or `rule_id`, while the raw output supplies a derivable path for 6 of the 8 true findings and an explicit rule tag for 2 of them. The operator's aggregate across all runs to date is the same picture at larger n: short mode 27 findings with 9 paths, 9 lines and 0 rule ids; full mode 3 findings with 0 of each.

### RC1 — a trailing `**Notes:**` block is parsed as findings (D4, reopened)

`dc7efd9d…__node-skeleton_2.stdout.txt`, verbatim:

```text
## Must Fix (Critical)
None.

## Should Fix (Important)
None.

## Nice to Have (Optional)
None.

**Notes:**
- precommit skipped (selector mode/short mode) — CI covers lint+test+typecheck
- `npm ci` was not run in this environment, so `tsc --noEmit` / `node --test` were not executed live; static review of all touched `.ts` files found no type errors, no `any`/`as`/`!`/`@ts-ignore`, and correct `.ts`-extension `require()` usage matching the documented `moduleResolution: "bundler"` invariant. Recommend confirming CI's `make check` is green before merge.
- LICENSE file present; README gained a License section pointing to it — harmless, unrelated to the TS conversion but fine.
```

Every severity section reads `None.`. The harvester returned three findings whose bodies are those three bullets. v0.35.2 gave a section an end boundary — the next heading, a thematic break, or end of input. `**Notes:**` is none of the three, so the Nice to Have section is still open when the bullets arrive and each one opens a finding inside it.

### RC2 — numbered items are invisible

`ce1703bc…__python-skeleton_3.stdout.txt`, under `### Should Fix (Important)`, verbatim:

```text
1. **`CHANGELOG.md:18`** — `- ci: install trivy in CI` uses prefix `ci:`, not in the recognized set (`feat/fix/refactor/test/docs/chore/perf`). Breaks automated version-bump detection. Fix: use `chore:`. *(rule: `changelog/conventional-prefix-required`)*
2. **`README.md` "Security gates" section (~lines 76-94)** — rationale/ADR-style content (why no severity threshold, why `osv-scanner` excluded, cross-skeleton comparison table) belongs in `CLAUDE.md`/ADR, not user-facing README. Fix: trim to a short factual statement; move rationale elsewhere. *(rule: `readme/user-facing-not-agent-context`)*
3. **`.github/workflows/ci.yml:32`** — `sudo apt-key add -` is deprecated; can silently break on a future `ubuntu-latest` bump. Fix: use a keyring-based install or switch to `aquasecurity/setup-trivy` action.
4. **CI + `Makefile.precommit`** — Trivy has no version pin (unlike `PIP_AUDIT_VERSION ?= 2.9.0` set for pip-audit in the same PR), so CI and local runs can diverge over time. Fix: pin a Trivy version.
5. **`Makefile.precommit` `trivy` target** — no `--severity` filter and no documented rationale for failing on any severity, unlike the `audit` target which explicitly explains its "any severity" choice. Fix: either add a severity threshold or document the deliberate all-severity choice.
```

The harvester returned two findings for this PR — the two `- ` bullets under `### Nice to Have (Optional)`. All five numbered items were dropped. Spec 003 named this outcome in advance and chose it: its Non-goals say *"Do NOT broaden what opens a finding (numbered lists, bold-lead paragraphs, tables). No observed review output uses them."* Observed review output now does, in the reviewer's most severe tier.

### RC3 — attribution is coupled to the runner's copy of the rule index

The rule tag `*(rule: `changelog/conventional-prefix-required`)*` is present inline in the capture above. Feeding that item's text directly to the shipped extractor does return the id, so RC3 is not "nothing parses it" — the item is never parsed at all (RC2), and RC3 is what remains after RC2 is fixed:

- `rule_id` is recovered only when the token happens to be a member of the id set loaded from `rules/index.json`. A tag naming a renamed rule, a rule added since the index was written, or a review run against a different rules revision yields `null` rather than the tag's literal value — attribution becomes a property of the runner's bookkeeping rather than of the reviewer's output.
- The extractor returns the **first** token anywhere in the item's text that is a member of that set. `ce1703bc…__node-skeleton_2` ends with a 22-row traceability table naming rule ids, and review prose routinely discusses rules by name, so a membership scan can attribute a finding to a rule the reviewer never tagged it with.
- `path` and `line` are likewise scanned from the whole item text rather than read from the leading bold reference, so the first `something.ext:NN` anywhere in a long body wins.

### RC4 — heading level varies run to run, not by mode

The captures show `##`, `###` and `####` all in use, and the level is **not** determined by mode: short mode emitted `##` on one PR and `####` on two others in the same run; full mode emitted `###` on one PR and `####` on another in the same run. The harvester already matches heading levels 1–6, so this is not an active defect — it is an untested invariant that any fix to item recognition can silently break, and the reason section termination must never key off a heading's level. It matters concretely: in `ce1703bc…__python-skeleton_3` the `### Positive notes` heading is what currently keeps four positive-note bullets out of the findings list, and that heading sits at the same level as the severity headings, while in `ce1703bc…__node-skeleton_2` a `### Traceability` heading terminates a `####` section from a shallower level.

### Bonus defect, same layer

`ce1703bc…__node-skeleton_2`'s single genuine finding is `- **No test coverage for `src/config.ts`'s new validation logic.** …`. The harvested body begins `*No test coverage for …` — one asterisk of the leading bold run is stripped as if it were a second list marker. The body is corrupted at exactly the position where the path reference lives, which is why it must be fixed as part of reading the leading bold reference rather than separately.

## Expected vs Actual

| | Expected | Actual |
|---|---|---|
| Review with all three sections `None.` and a trailing `**Notes:**` block | 0 findings — `bench/README.md` § "What opens a finding": prose before any list item "contributes no finding", and the notes block is not inside a findings section | 3 findings, bodies verbatim the notes bullets |
| Review with five numbered Should Fix items and two Nice to Have bullets | 7 findings | 2 findings |
| Finding tagged `*(rule: `changelog/conventional-prefix-required`)*` | `rule_id` = that string | `null` on every finding in every run to date |
| Finding headed `**`CHANGELOG.md:18`**` | `path` = `CHANGELOG.md`, `line` = 18 | `null`, `null` |
| Finding body `- **No test coverage …` | body begins `**No test coverage` | body begins `*No test coverage` |
| An item the runner cannot attribute | the PR fails loudly, no row written | a body-only finding is written and scored |

## Why this is a bug

`bench/README.md` § "Reading review output" states the harvest contract the runner is supposed to implement, and the runner does not implement it against real input: the section-boundary rule is documented as complete when a bold label defeats it, and the finding-opening rule is documented as `-` or `*` when the reviewer's severe tiers use `1.`. The same section states the fixture rule — *"A fixture for a new defect must be a capture of real output, not a transcription of the template"* — and that rule was followed only for captures that contained zero findings, so no fixture in the repository has ever exercised the parser against a real finding. That is precisely how this defect family reaches five occurrences: the parser, the fixtures and the documentation all agree with one another and all disagree with the model's actual output. The result is an instrument that reports a confident wrong number in both directions on the same run, which has already produced one published wrong conclusion about model determinism.

## Acceptance Criteria

Each AC is tagged **[container]** (verifiable at prompt time with no network, no tokens, and no real `claude` binary) or **[operator]** (only observable on the host, because it spends real tokens against the live review command). The convention is inherited from specs 002, 003 and 004 — whose operator criteria found every defect in this family while the container suite found none.

**Why the fixtures must be captures.** Four earlier defects in this family (D1, D2, D4, D7) recurred because each fix shipped with fixtures written alongside the parser from the same mental template, so the tests and the code agreed with each other and both disagreed with the model's real output. Every unit AC below that names a fixture requires a **verbatim capture of live review output**, and each is gated by a content-fidelity check on literals the review command's template cannot produce.

- [ ] **AC1 [container]** `make precommit` exits 0 and the bench suite grew — evidence: exit code 0; `python3 -m unittest discover -s bench -p 'test_*.py'` stderr contains `OK` and a `Ran N tests` line with `N > 72`.
- [ ] **AC2 [operator pre-step, then container]** Four captures are installed verbatim as fixtures under `bench/testdata/` and each matches its **published `sha256`** — evidence, for every row: `shasum -a 256 <fixture> | cut -d' ' -f1` equals the stated digest exactly; `grep -c '' <fixture>` returns the stated line count; `grep -cE '^<stated level> (Must Fix|Should Fix|Nice to Have)' <fixture>` returns 3 and the same grep at each other level returns 0.

  | Fixture file | Capture | Level | Lines | `sha256` |
  |---|---|---|---|---|
  | `bench/testdata/capture-notes-block-h2.md` | `node-skeleton#2`, short mode — trailing `**Notes:**` block | `##` | 17 | `6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9` |
  | `bench/testdata/capture-numbered-findings-h3.md` | `python-skeleton#3`, full mode — five numbered findings | `###` | 28 | `5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93` |
  | `bench/testdata/capture-traceability-h4.md` | `node-skeleton#2`, full mode — traceability table | `####` | 57 | `2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c` |
  | `bench/testdata/capture-summary-trailer-h4.md` | `github-pr-review-agent#11`, short mode — `**Summary**:` trailer | `####` | 21 | `36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79` |

  The four filenames are the contract: two fixtures sit at `####`, so a heading level does not identify a fixture and every reference below names a file.

  Plus `grep -rn '/Users/\|~/Documents/' bench/testdata/` returns 0 lines (exit 1).

  **The digest is the provenance gate; the line counts and heading greps are readability anchors only.** Published literals cannot serve as the gate: this spec quotes 13 of the `##` capture's 17 lines verbatim in RC1, and for the `###` capture RC2 quotes all five numbered items while AC5, AC10 Case A and AC13 publish their exact attribution, the positive-note count and the Nice-to-Have count — the entire asserted shape is already on the page, leaving only unasserted prose padding free. A `sha256` is the one anchor that can be published without enabling reconstruction.

  **Installation is an operator pre-step, not container work.** `.dark-factory.yaml` sets `worktree: false` and `.gitignore:9` excludes `/bench/.cache/`, so a container clone never contains the captures and has no way to obtain them. The operator copies the four files into `bench/testdata/` and commits them **before** `dark-factory spec approve`, so every prompt finds them already present and writes only tests against them. No prompt may create, regenerate, or reconstruct a fixture; a prompt that finds a digest mismatch stops and reports it rather than rewriting the file.

- [ ] **AC3 [container]** The trailing-notes capture yields **nothing at all** — evidence: a unit test feeds `bench/testdata/capture-notes-block-h2.md` to the harvester and compares **both** components of the AC13 two-part result against empty: the findings list equals `[]` **and** the unattributable-item report equals `[]`; the assertion's failure message prints both. Asserting only the findings list lets an implementation reclassify the three `**Notes:**` bullets as unattributable items — findings is still empty, and the PR then fails loudly on a review that correctly found nothing, which is RC1 with the sign flipped. (This capture is the exact input that produced the three phantom findings.)
- [ ] **AC4 [container]** The bold-label terminator is general, not a hardcoded label, across **three** cases — evidence, all three: the assertion compares **both** components of the two-part result — findings list and unattributable report — against their expected values. Terminated content must land in neither component.
  - Case A: a section reading `None.` followed by `**Notes:**` and three bullets → findings `[]` **and** unattributable report `[]`.
  - Case B: the same shape with the label `**Summary**:` followed by prose and then a bullet → findings `[]` **and** unattributable report `[]`. (`**Summary**:` is the shape the `github-pr-review-agent#11` capture actually uses.)
  - Case C: a section carrying **one real attributed bullet**, then `**Notes:**`, then two more bullets → exactly the one real finding, body unchanged.

  Cases B and C exist because matching the literal string `**Notes:**`, or dropping every finding that follows a `None.` sentinel, passes Case A alone.
- [ ] **AC5 [container]** The five previously-dropped numbered findings are extracted with the attribution the capture supplies — evidence: a unit test feeds `bench/testdata/capture-numbered-findings-h3.md` to the harvester and compares the Should Fix findings against this exact list, in order:

  | # | path | line | rule_id |
  |---|---|---|---|
  | 1 | `CHANGELOG.md` | 18 | `changelog/conventional-prefix-required` |
  | 2 | `README.md` | 76 | `readme/user-facing-not-agent-context` |
  | 3 | `.github/workflows/ci.yml` | 32 | null |
  | 4 | `Makefile.precommit` | null | null |
  | 5 | `Makefile.precommit` | null | null |

  The assertion compares paths, lines, rule ids and the count together and prints the full observed list on failure.
- [ ] **AC6 [container]** Ordered-item recognition is general, not fitted to the capture — evidence: a unit test over a synthetic section mixing `- `, `* ` and ordered items whose numbering starts at `3.` and includes `10.`, asserting one finding per item in document order; plus a negative case where an ordered item inside a fenced code block within a severity section yields no finding. (Without the non-1 start and the two-digit marker, a parser keyed to `1.`–`5.` passes AC5.)
- [ ] **AC7 [container]** `rule_id` comes from the reviewer's inline marker, with the head-anchored legacy shape as an index-gated fallback, across **four** cases — evidence, all four: the assertion compares the returned `rule_id` against the expected value.
  - Case A: an item tagged `*(rule: `made-up/not-in-the-index`)*`, an id absent from `rules/index.json`, yields that literal string, not null.
  - Case B: an item whose prose names a **different**, real rule id before its own `*(rule: …)*` marker yields the marker's id, not the prose one.
  - Case C: an item carrying **no** marker whose body opens with a backticked token that **is** present in `rules/index.json` yields that id — the head-anchored legacy shape, which the byte-frozen `sample-report.md` depends on for three findings.
  - Case D: the same item shape whose head token is **absent** from `rules/index.json` yields `None` — the legacy source stays index-gated, so an unknown backticked token at the head of an item is not recorded as a rule.

  Case B exists because a first-membership-match scan passes Case A. Cases C and D exist because the legacy source is otherwise held in place only by `TestHarvestNormalizesSampleReport`, an indirect guard that would not survive a refactor of that fixture's test, and because C without D would let the fallback drift into recording arbitrary head tokens. Together with AC10's traceability-table check, these close attribution-by-proximity in both directions.
- [ ] **AC8 [container]** `path` and `line` come from the leading bold reference, across **four** shapes — evidence: unit assertions on `(path, line)` pairs for each: `**`CHANGELOG.md:18`**` → (`CHANGELOG.md`, 18); `**`README.md` "Security gates" section (~lines 76-94)**` → (`README.md`, 76); `**`.github/workflows/ci.yml:32`**` → (`.github/workflows/ci.yml`, 32); `**CI + `Makefile.precommit`**` → (`Makefile.precommit`, null). Plus a negative case: an item whose leading bold reference names `a/b.py:10` and whose trailing prose mentions `c/d.py:99` resolves to (`a/b.py`, 10).
- [ ] **AC9 [container]** The body preserves the leading bold run verbatim — evidence: a unit test feeds `bench/testdata/capture-traceability-h4.md` to the harvester and asserts exactly one finding whose `body` starts with the literal `**No test coverage for` (two asterisks) and whose `path` is `src/config.ts`. (The shipped parser produces `*No test coverage for` and `path` null.)
- [ ] **AC10 [container]** Content outside a severity section is never a finding and never attributes one, across **three** cases — evidence, all three: assertions on the full returned list.
  - Case A: `bench/testdata/capture-numbered-findings-h3.md`'s four `### Positive notes` bullets contribute zero findings **and** appear in no unattributable report — content outside a severity section is not a finding and is not a parse failure either. (None of those four bullets carries a path or a rule tag, so classifying them as unattributable would fail the PR on a correctly-reviewed capture.)
  - Case B: no finding harvested from `bench/testdata/capture-traceability-h4.md` carries a `rule_id` drawn from its 22-row `### Traceability` table.
  - Case C: the two zero-finding captures each harvest to the empty list — the pre-existing `bench/testdata/real-capture-report.md`, and `bench/testdata/capture-summary-trailer-h4.md`.
- [ ] **AC11 [container]** An item the runner cannot attribute fails the PR loudly — evidence: with a stub `claude` on `PATH` printing a review whose Should Fix section carries one item with neither a path reference nor a rule tag, run the runner over a one-PR temp manifest → process exit code non-zero; stderr contains the literal `UNATTRIBUTABLE FINDING`, the PR id, the severity section name, and the item's text verbatim; the results file gains 0 lines; and under the **temp cache root the test passed to the runner** (`reviews_root(cache_root)`, `bench/run.py:305` — never `bench/.cache/`, which is gitignored at `.gitignore:9`, absent in a fresh clone, and therefore a vacuous probe) exactly **one** file exists, the `<key>.stdout.txt` raw capture, and **zero** `*.json` row markers; a both-stream failure artifact exists under `failures_root(cache_root)` carrying the rejected output; the stdout summary reports `1 failed`.

  The `.json` count is the discriminator, not the total entry count: the runner writes the raw stdout at step 5 *before* harvesting at step 6 (`bench/run.py:1404-1410`, comment "Write raw stdout verbatim before any parsing"), so a harvest-derived gate necessarily fires with the raw file already on disk. Requiring zero total entries would force either reordering harvest ahead of that write or deleting the raw output — both regressions, the second one destroying the text the Failure Modes table promises is re-harvestable after a fix.
- [ ] **AC12 [container]** The loud failure is not a blanket rejection, and AC11's probe is live — evidence: the same runner invocation with the same review shape, the single item now headed `**`src/x.py:4`**`, exits 0; the results file gains exactly 1 line; `jq -r '.findings[0].path'` on that row prints `src/x.py`; and the **same probe AC11 uses**, run here, finds **two** files under `reviews_root(cache_root)` — one `<key>.stdout.txt` and exactly **one** `<key>.json` row marker — against AC11's one-and-zero.

  The success path writes two files, the raw capture at step 5 and the row marker at step 8 (`bench/run.py:1437`); stating "1" would be off by one and an implementer observing 2 would "fix" the assertion, silently dissolving the AC11/AC12 pairing. The `*.json` count (1 here, 0 in AC11) is what proves the PR is cache-served next run in one case and retried in the other — the cache check keys on the row marker alone (`bench/run.py:1349-1350`).
- [ ] **AC13 [container]** The unattributable items in the real capture are reported as such, not silently dropped and not silently kept — evidence: a unit test over `bench/testdata/capture-numbered-findings-h3.md` asserts that harvesting reports both `### Nice to Have (Optional)` bullets as unattributable, quoting each verbatim, **and** that the five Should Fix findings from AC5 are present in the parse result. This is the honest consequence of the governing rule on a genuine review: that PR fails loudly rather than contributing two body-only findings.
- [ ] **AC14 [container]** Heading level is irrelevant to both termination and harvesting — evidence: a unit test renders identical section content at `##`, `###` and `####` and asserts all three harvest to the same list; a second case asserts a `###` heading terminates an open `##` section and a `##` heading terminates an open `####` section; the test name contains `heading_level`; the assertion prints all lists on failure.
- [ ] **AC15 [container]** No test was deleted **and no test file was gutted** — evidence, all four, each a binary mechanical check:
  - `git diff origin/master -- bench/test_*.py | grep -c '^-.*def test_'` returns 0 (no test function removed).
  - **Per-file assertion floors**, each its own check: `grep -cE '^\s*(self\.assert|assert )' bench/test_config.py` ≥ 63; the same on `bench/test_resolve.py` ≥ 46; the same on `bench/test_review.py` ≥ 165. These are the `origin/master` counts.
  - `git diff origin/master -- bench/testdata/sample-report.md bench/testdata/real-capture-report.md` is empty.
  - Combined with AC1's `N > 72`.

  Per-file floors, not a repo-wide total: the glob `bench/test_*.py` admits new files, so a repo-wide floor of 274 is satisfied by adding `bench/test_harvest.py` with 200 assertions while cutting `test_review.py` from 165 to 20 — and `test_review.py` is exactly the file this work touches. A floor per existing file cannot be paid for with a new one.

- [ ] **AC16 [container]** `bench/README.md` § "Reading review output" states the corrected contract — evidence: `grep -ciE 'bold label|bold run' bench/README.md` ≥1; `grep -ciE 'numbered|ordered list' bench/README.md` ≥1; `grep -ciE 'rule: |inline (rule )?(tag|marker)' bench/README.md` ≥1; `grep -ciE 'rules/index\.json' bench/README.md` ≥2 **on at least two distinct line numbers** — one for the inline marker's exemption from the index, one for the head-anchored fallback's index gate; `grep -ciE 'head-anchored|head of the item' bench/README.md` ≥1; `grep -cF 'UNATTRIBUTABLE FINDING' bench/README.md` ≥1; the fixtures table lists all **four** new capture fixtures with their origin, `sha256` and expected harvest — `bench/testdata/` previously held only `sample-report.md` and `real-capture-report.md`, so every AC2 fixture is new.

  **Anti-keyword-stuffing:** the four patterns must match on **at least four distinct line numbers** (union of `grep -n` line numbers has ≥4 unique values), and each of the four topics must be its own prose block of ≥2 non-empty lines. One keyword-dense line satisfies every grep while documenting nothing.
- [ ] **AC17 [container]** The CHANGELOG entry describes the whole change so a release classifier can weigh it — evidence: the section from `## Unreleased` to the next `## ` line is non-empty; every bullet in it matches `^- (fix|feat|docs): `; `grep -c '^- bench: '` over it returns 0; within it `grep -ciE 'notes|trailing|invent|phantom'` ≥1, `grep -ciE 'numbered|dropped'` ≥1, `grep -ciE 'rule id|path|attribut'` ≥1.

  **Anti-keyword-stuffing:** the three topic patterns must match on **three distinct bullet lines** and the section must contain ≥3 bullets. One bullet naming all three defects passes the loose form while under-describing the change — the failure that drew a patch bump on v0.35.1.
- [ ] **AC18 [container]** The runner still carries no personal paths and no third-party dependencies — evidence: `grep -rn '/Users/\|~/Documents/' bench/` returns 0 lines (exit 1); every `import` / `from` line in `bench/run.py` names a Python 3 standard-library module only.
- [ ] **AC19 [operator]** A clean review scores zero on the live five-PR `dev-1` fixture — evidence: after `rm -rf bench/.cache/reviews bench/results`, `make bench BENCH_ARGS="--model <m> --effort <e> --mode short"` completes; for every results row whose `raw_output_ref` file satisfies `grep -cE '^#{1,6} +(Must Fix|Should Fix|Nice to Have)' == 3` **and** `grep -cE '^None\.$' == 3`, `jq '.findings | length'` prints `0`. At least one row must satisfy the two greps, otherwise the criterion is untested and the run is repeated.
- [ ] **AC20 [operator]** Every finding recorded in a live run carries an attribution — evidence: `jq -r 'select(.findings[]? | (.path == null and .rule_id == null)) | .pr_id' bench/results/results.jsonl` prints nothing (0 lines). Any PR whose review contained an unattributable item appears instead as a loud failure in the run summary, never as a row.
- [ ] **AC21 [operator]** Numbered findings and inline rule tags survive to the ledger — evidence: for every results row, the count from `jq '.findings | length'` is ≥ the count from `grep -c '\*(rule: ' <that row's raw_output_ref>`; and across the run, `jq -r '.findings[].rule_id' bench/results/results.jsonl | grep -vc '^null$'` is ≥1 whenever any raw output contains `*(rule: `. Under the shipped runner this second count is 0 in every run to date.

**Scenario coverage — NO new scenario.** The harvester is a pure function over text and every capture is a file on disk, so all four root causes are reachable by unit tests at the exact boundary that produced them. The loud-failure control flow is reachable with the existing stub-executable harness in `bench/testsupport.py`. The remaining evidence needs real tokens against a live review, which the scenario harness cannot supply either — AC19–AC21 are operator-executed after merge, exactly as specs 002, 003 and 004 did.

## Verification

### Container-executable (runs inside the YOLO container at prompt time)

```
make precommit
python3 -m unittest discover -s bench -p 'test_*.py' -v
git diff origin/master -- bench/test_config.py bench/test_resolve.py bench/test_review.py | grep -c '^-.*def test_'
git diff origin/master -- bench/testdata/sample-report.md bench/testdata/real-capture-report.md
grep -rn '/Users/\|~/Documents/' bench/
for f in bench/testdata/capture-notes-block-h2.md \
         bench/testdata/capture-numbered-findings-h3.md \
         bench/testdata/capture-traceability-h4.md \
         bench/testdata/capture-summary-trailer-h4.md; do
  shasum -a 256 "$f" | cut -d' ' -f1; grep -c '' "$f"
done
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py
grep -niE 'bold label|numbered|unattributable|inline rule' bench/README.md
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md
```

Expected: `make precommit` exits 0; the verbose unittest run reports `OK` with `Ran N tests`, `N > 72`, and shows the trailing-notes, bold-label, numbered-item, rule-tag, leading-bold-reference, body-fidelity, outside-section, unattributable and `heading_level` tests by name; the deleted-test grep prints `0`; the four digests equal AC2's published `sha256` values and the four line counts print `17`, `28`, `57` and `21`; the three per-file assertion counts are at least `63`, `46` and `165`; the two pre-existing fixture diffs are empty; the personal-path grep returns nothing (exit 1); the README greps return ≥4 distinct lines; the extracted Unreleased section carries ≥3 `fix:`/`feat:`/`docs:` bullets naming the phantom findings, the dropped numbered findings, and attribution.

### Operator-executable (runs on the host, spends real tokens)

```
rm -rf bench/.cache/reviews bench/results
make bench BENCH_ARGS="--model <model> --effort <effort> --mode short"
jq -s 'length' bench/results/results.jsonl
jq -r 'select(.findings[]? | (.path == null and .rule_id == null)) | .pr_id' bench/results/results.jsonl
jq -r '.findings[].rule_id' bench/results/results.jsonl | grep -vc '^null$'
jq -r '.raw_output_ref' bench/results/results.jsonl | while read f; do
  printf '%s none=%s tags=%s\n' "$f" "$(grep -cE '^None\.$' "$f")" "$(grep -c '\*(rule: ' "$f")"
done
```

Expected: the run completes; the both-null selector prints nothing; every raw output whose three sections read `None.` corresponds to a row with zero findings; every row's findings count is at least its raw output's inline-rule-tag count. Any PR whose review carried an unattributable item is reported in the summary as failed with `UNATTRIBUTABLE FINDING` and has no row — that outcome satisfies the criteria and is recorded, not worked around.

## Desired Behavior

1. **A severity section ends at the first block that is not part of it.** Its content ends at the next markdown heading of any level, at a thematic break, at end of input, or at a line outside a fenced block whose first non-whitespace content begins a bold run — whichever comes first. The bold-run terminator is what closes the observed defect: `**Notes:**` and `**Summary**:` introduce a new block, and everything under them belongs to that block, not to the severity section above. Termination never depends on the terminating heading's level relative to the section's own, because level varies run to run within a single mode.

2. **A finding opens on any list item the reviewer writes, in either list style.** Unordered items (`-`, `*`) and ordered items (a run of digits followed by `.` and a space) both open a finding; ordered numbering need not start at 1 and is not restricted to one digit. Non-list lines following an open item extend it. A line inside a fenced code block is ordinary text and opens nothing. Prose appearing in a section before any item — most importantly the mandated `None.` sentinel — contributes no finding, unchanged from v0.35.2.

3. **The item's leading bold reference supplies `path` and `line`, and the body keeps it intact.** Attribution is read from the bold run at the head of the item, in the shapes the reviewer actually writes: a backticked `path:line`, a backticked path followed by a line-range mention (the range's first number is the line), and a bold run containing a backticked path-shaped token among other words. A path or line appearing only in the item's trailing prose is not used when the leading bold run supplies one, and no path is ever inferred by searching the repository. The bold run itself is preserved verbatim in the body — the list marker is stripped, the emphasis is not.

4. **`rule_id` is read positionally, from the reviewer's inline tag first and a head-anchored legacy shape second.** Two sources are consulted, in strict priority order, and never any other position:

   1. **The item's own `*(rule: `<id>`)*` marker.** When present it always wins, and the id is recorded as the literal string the reviewer wrote, **whether or not it appears in `rules/index.json`** — this is the coupling RC3 names as the defect, and this path is free of it.
   2. **Only when no marker is present**, a backticked token at the very head of the item that is a member of `rules/index.json`. This is the shape the review template emits when it tags a finding by leading the body with the rule id, and three findings in the byte-frozen `bench/testdata/sample-report.md` depend on it. This second source **remains index-gated**: a head token absent from the index yields `None` rather than being recorded blind, because at the head of an item an unknown backticked token is far more likely to be a file path or a symbol than a rule name.

   An id named **outside a marker** — in the item's prose, in a traceability table, or anywhere outside the item — is never attributed to it, under either source. The marker itself is read wherever it appears within the item, **including at its tail**, which is where the reviewer actually writes it (every `*(rule: …)*` tag in `capture-numbered-findings-h3.md` sits at the end of its item, and AC5 requires exactly those ids). The instrument records what the reviewer claimed; reconciling that against the shipped rule set is the scorer's job, not the harvester's.

   **Why the legacy source survives on purpose.** Deleting it would null the three rule ids in `sample-report.md`, which the Constraints freeze byte-for-byte *and* freeze the asserted harvest result of. Retiring it is a change to a frozen fixture's asserted result and belongs in its own spec, not here. Its index gate is a deliberate asymmetry with source 1, not an oversight, and `bench/README.md` must document both sources and the asymmetry (AC16) — a doc claiming rule ids are "never validated against `rules/index.json`" would be false about the shipped parser, which is the exact docs-disagree-with-code mechanism behind D1, D2, D4 and D7.

5. **An unattributable item fails the PR loudly.** An item inside a severity section that yields neither a `path` nor a `rule_id` cannot be keyed, therefore cannot be matched against a golden set, and is never written down as a body-only finding. Harvesting reports every such item; when the report is non-empty the PR fails in the same class as the existing `NOT A REVIEW` gate — no ledger row, no review cache entry, the PR listed as failed, remaining PRs still processed, the process exits non-zero — with a diagnosis headed by the frozen literal `UNATTRIBUTABLE FINDING` (the sibling of `NON_REVIEW_MARKER = "NOT A REVIEW"` at `bench/run.py:64`) and naming the PR, the severity section, and each offending item verbatim within the same bounded excerpt envelope the existing gate uses. Nothing else about that gate changes.

6. **The fixtures are captures with findings in them, and the contract is written beside them.** `bench/testdata/` carries four verbatim captures of live review output spanning all three observed heading levels: one whose sections all read `None.` with a trailing notes block, one carrying five numbered findings with inline rule tags plus a positive-notes list, one carrying a single bold-headed finding plus a traceability table, and one zero-finding short-mode report whose trailer is a `**Summary**:` bold label. The two pre-existing fixtures stay byte-identical. `bench/README.md` states the corrected boundary rules, the two list styles, the positional rule-tag source, and the unattributable-item rejection, so the next fixture author reads the contract rather than re-deriving it from the parser.

## Constraints

- **Language and dependencies:** Python 3 standard library only. Changes land in `bench/run.py`, `bench/test_*.py`, `bench/testsupport.py`, `bench/testdata/`, `bench/README.md`, and `CHANGELOG.md`. No packaging, no third-party imports, no new top-level files outside `bench/`.
- **The 72 existing tests keep passing and their assertions are not weakened.** No test function may be deleted and no assertion relaxed to accommodate the new parser; the suite's test count after this work is strictly greater than 72. Existing stub payloads may gain an attribution on their finding items — that is a payload change, not an assertion change — but a test that asserted a specific harvest result keeps asserting a result at least as specific. The evidence for this Constraint is AC15's per-file assertion floors (`test_config.py` ≥ 63, `test_resolve.py` ≥ 46, `test_review.py` ≥ 165), because a surviving `def test_` signature with an emptied body satisfies a deleted-test check and a test-count check simultaneously, and a repo-wide total is payable with a new file.
- **The two pre-existing fixtures are frozen.** `bench/testdata/sample-report.md` and `bench/testdata/real-capture-report.md` are byte-identical after this work; both still harvest to their previously asserted results.
- **The raw-stdout-before-parsing invariant is preserved, and the two rejection classes differ in what they leave behind.** The raw capture is written verbatim before any parsing (`bench/run.py` step 5, ahead of harvest at step 6) and that ordering does not change. Consequently the `NOT A REVIEW` gate, which fires before step 5, still leaves nothing under `reviews_root`; the new unattributable-item gate fires after it and leaves the `<key>.stdout.txt` in place while writing **no** `<key>.json` row marker and **no** ledger row. Since the cache check keys on the row marker alone (`bench/run.py:1349-1350`), the PR is still retried on the next run, and the raw text stays on disk so the review is re-harvestable once the parser is fixed. A rejected PR also writes a both-stream failure artifact under `failures_root`, the same diagnostic shipped in v0.35.3.
- **The `NOT A REVIEW` gate is unchanged** — same required sections, same heading matching, same bounded excerpt, same position ahead of the raw-output cache write. The unattributable-item rejection is a second, later gate that reuses the same no-row / no-cache-entry / retry-next-run semantics.
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access.
- **Frozen invariants** (not configurable, not flagged): the three required section names; the section terminators; the list-item markers; the inline rule-tag marker shape; the `UNATTRIBUTABLE FINDING` marker literal; the rejection excerpt bound; the 45-minute review timeout; the cache, results and failure-artifact locations; the isolated config directory; the `--golden` exit-2 rejection.
- **Harvested values are data, never paths.** A `path` or `rule_id` read out of review output is written to the ledger and to nothing else. No harvested value is opened, stat-ed, joined onto a filesystem root, or passed to a subprocess.
- No rule, agent, command, or doc that participates in a review is edited, including `commands/pr-review.md`. `bench/prs.json` stays frozen.
- **Repo conventions that must not regress** (`docs/dod.md`): no personal paths (`/Users/`, `~/Documents/`) in any shipped file including the new capture fixtures, and a `## Unreleased` CHANGELOG entry.
- **CHANGELOG entries use conventional prefixes** (`fix:` / `feat:` / `docs:`) per `docs/changelog-guide.md`, and the entry describes the whole change rather than the last prompt's slice.

## Assumptions

- **The four fixtures are installed by the operator before approval, not by any prompt.** The captures live only under `bench/.cache/reviews/`, which `.gitignore:9` excludes, and `.dark-factory.yaml` sets `worktree: false`, so a container clone can never reach them. The operator copies the four files into `bench/testdata/` and commits them before `dark-factory spec approve`; every prompt therefore finds them present and only writes tests. They were checked for personal paths (`grep -rl '/Users/' bench/.cache/reviews/` → no matches) and contain none.
- **No prompt creates, regenerates or reconstructs a fixture.** A transcribed fixture is the defect this spec exists to close, and a regenerated one is a different document that would not match AC2's published digest. A prompt that finds a fixture missing or digest-mismatched stops and reports it; it does not write the file. Handing an agent a fully-published acceptance shape and an unreachable source is what makes synthesis the default path, so the source is made reachable instead.
- `*(rule: `<id>`)*` is the reviewer's inline tagging convention. It was observed in full mode only; short mode produced no attributed findings in any capture. The harvester reads it wherever it appears within an item and does not require it.
- The reviewer places its file reference in a bold run at the head of a finding item. Every attributed item in every capture follows this; the four shapes in AC8 are the observed variants.
- Reviews will sometimes contain items with no file reference and no rule tag — two of the eight true findings in the captures are of this kind. Under Desired Behavior 5 those reviews fail loudly. That is the intended, visible cost of refusing to record unmatchable findings; the resolution path, if the rate proves high, is a separate spec against `commands/pr-review.md` requiring an attribution on every finding, not a relaxation here.
- A stub executable on `PATH` printing a chosen payload to stdout and exiting with a chosen code is sufficient to reach the runner's control flow for the loud-failure criteria; `bench/testsupport.py` already provides it.
- The five fixture PRs stay merged, their recorded SHAs stay reachable, and `dev-1` stays the manifest version.

## Failure Modes

| Trigger | Expected behavior | Recovery | Detection | Reversibility | Concurrency |
|---|---|---|---|---|---|
| Severity section reads `None.` and is followed by a bold-label block with bullets (observed) | The bold-label line ends the section; the bullets are not findings; the PR records 0 findings | None needed | `bench/testdata/capture-notes-block-h2.md` harvests to the empty list | n/a | n/a |
| Severity section carries numbered items (observed) | One finding per item, in document order, with the attribution each carries | None needed | `bench/testdata/capture-numbered-findings-h3.md` harvests its five Should Fix items | n/a | n/a |
| An item inside a severity section carries neither a path reference nor a rule tag (observed twice in one capture) | The PR fails loudly: no ledger row, no `<key>.json` row marker, item quoted verbatim on stderr; the `<key>.stdout.txt` raw capture stays on disk and a both-stream failure artifact is written; other PRs still processed; process exits non-zero | Operator reads the quoted item and decides — either the review command must mandate attribution (separate spec) or the item was genuinely not a finding; the preserved raw capture is re-harvestable without spending tokens again | Non-zero exit; the literal `UNATTRIBUTABLE FINDING` plus PR id, section name and item text on stderr; the failure artifact under `failures_root`; summary lists the PR as failed | Fully reversible — no row and no row marker written; the PR is retried because the cache check keys on the row marker alone | Rows and cache entries for other PRs untouched |
| **Every** PR in a run fails with `UNATTRIBUTABLE FINDING` | Whole run produces zero rows and fails loudly with a uniform signature — the review command routinely emits unattributed findings and the two contracts have diverged | Operator files a follow-up spec against `commands/pr-review.md`; this spec's Non-goals forbid changing it here | All five PRs failed with `UNATTRIBUTABLE FINDING` — unmistakably contract drift rather than a per-PR fault | Fully reversible — no rows written | Whole run fails uniformly; no partial ledger to reconcile |
| Rule tag names an id absent from `rules/index.json` (renamed rule, drifted index, review run against a different rules revision) | The literal string from the tag is recorded; no null, no abort | None needed | The row carries a `rule_id` the index does not contain — visible to the scorer, which is where reconciliation belongs | n/a | n/a |
| Review prose or a traceability table names rule ids other than the item's own tag (observed: a 22-row table) | Neither is attributed to any finding | None needed | `bench/testdata/capture-traceability-h4.md` yields one finding with `rule_id` null | n/a | n/a |
| A finding's continuation paragraph begins with a bold run | The finding body is truncated at that line and the section closes early | Operator adds the capture as a fixture and files a follow-up | Observable as a short body, never as an invented finding — the failure direction is loss, not fabrication. No captured output exhibits this shape | Fully reversible — the raw output is cached and re-harvestable after a fix | n/a |
| Heading level changes between runs or within a run (observed: `##`, `###`, `####` across five captures in two runs) | No effect — termination and section matching are level-agnostic | None needed | Fixtures at all three levels stay green | n/a | n/a |
| Review output is megabytes | Harvesting is linear in input size; the unattributable diagnosis reuses the existing bounded excerpt so stderr stays bounded | Operator deletes `bench/.cache/` | Excerpt visibly truncated; artifact file size | Fully reversible | Disk growth confined to the cache the README names as deletable |
| Review output contains a pathological construct (deeply nested emphasis, an unclosed fence, thousands of list markers) | Matching stays line-oriented and bounded; no unbounded backtracking; worst case is a wrong section boundary, never a hang | Operator adds the capture as a fixture | Run completes; findings visibly wrong for that PR | Fully reversible | n/a |
| Crash between harvesting and the ledger append | Nothing written — the row append is atomic and happens after both gates | Re-run; the PR is uncached and retried | Ledger has fewer rows than the manifest | Fully reversible | Atomic write-then-rename; no truncated row is ever observed |
| Cached rows and raw outputs written by the shipped parser are present | They are not re-harvested and not migrated; cache hits are served as-is | Operator deletes `bench/.cache/reviews/` and `bench/results/` and re-runs, as the README states | Rows predating the fix carry body-only findings | Fully reversible by deletion | Append-only ledger unaffected |
| Two runners started against the same output directory | Unchanged: the second exits immediately without touching the ledger or cache | Operator waits and re-runs | Non-zero exit; stderr states a run is in progress | Fully reversible | Single-instance lock, unchanged from spec 002 |

## Security / Abuse Cases

- **Attacker-controlled surface:** the review subprocess's stdout. It is third-party-influenced text — the reviewed repository's content flows into the model's output — and this change parses more of it, and extracts more values out of it, than before.
- **Extracted values are data, not paths.** `path` and `rule_id` are recorded into the ledger and used for nothing else: never opened, never stat-ed, never joined onto a filesystem root, never passed to a subprocess. A review that emits `**`../../etc/passwd:1`**` produces a ledger row with that string in it and no filesystem access.
- **No evaluation, no execution:** the harvester only matches text and slices it. No value from review output reaches a shell, and subprocesses continue to be invoked with argument lists rather than shell strings.
- **Denial by volume:** review output can be arbitrarily large. Harvesting is linear in input size, and the unattributable-item diagnosis reuses the existing bounded excerpt, so a runaway subprocess cannot flood the operator's terminal.
- **Denial by pathological input:** section, heading, emphasis and list matching stay line-oriented with bounded patterns; no construct in a report can cause unbounded backtracking or a scan that is not linear.
- **Secret leakage:** the new diagnosis reproduces the subprocess's own output and nothing else — no environment variables, no tokens, no credential material. The new fixtures are captures that were checked for personal paths before being checked in.
- **Fail-closed, not fail-open:** every ambiguity about whether an item is a keyed finding resolves to rejection. A false rejection costs one operator decision and a re-run; a false acceptance writes an unmatchable measurement into an append-only ledger, which is the failure this spec exists to prevent.

## Suggested Decomposition

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Verify the four operator-installed fixtures against AC2's published digests (stop and report on any mismatch — never write or regenerate one); add the bold-run section terminator; lock outside-section content and heading-level independence. Pure parser + tests, no runner wiring. | 1, 6 (fixtures half) | AC2, AC3, AC4, AC10, AC14 | operator pre-step: fixtures committed before approval |
| 2 | Ordered-list item recognition alongside unordered, in-fence suppression, and body fidelity (the leading bold run survives marker stripping). | 2 | AC6, AC9 | prompt 1 (fixtures) |
| 3 | Attribution extraction: `path` / `line` from the leading bold reference in its four observed shapes; `rule_id` from the item's own inline tag, positionally and independent of `rules/index.json`. | 3, 4 | AC5, AC7, AC8 | prompt 2 |
| 4 | The unattributable-item rejection and its runner wiring: harvesting reports unattributable items, the PR fails in the `NOT A REVIEW` class, no row and no cache entry, other PRs still processed. | 5 | AC11, AC12, AC13 | prompt 3 |
| 5 | `bench/README.md` harvest-contract rewrite (terminators, both list styles, positional rule tag, unattributable rejection, fixtures table); CHANGELOG `## Unreleased` entry; personal-path and stdlib-only sweep; deleted-test and frozen-fixture checks; full precommit. | 6 (contract half) | AC1, AC15, AC16, AC17, AC18 | prompts 1-4 |

Rationale: the chain 1 → 2 → 3 → 4 is genuinely sequential because each step's tests are written against behaviour the previous step made reachable — attribution (prompt 3) cannot be asserted against the five numbered items until ordered items are recognised (prompt 2), which cannot be asserted at all until the section boundaries stop swallowing them (prompt 1). All four fixtures are present from the operator pre-step before prompt 1 starts, so no prompt is ever blocked on an artifact it cannot obtain. Prompt 4 is the only one that touches the runner's control flow, isolated deliberately so the parser changes land and prove themselves as pure functions first, and so the one prompt that can fail a whole run is reviewable on its own. Prompt 5 is docs and packaging, last so the CHANGELOG bullets describe what all four actually shipped — the specific failure from spec 002, where the final prompt described only its own slice and the release classifier cut a patch instead of a minor. AC19–AC21 are operator-executed after merge in the spec-verification phase.

## Do-Nothing Option

Doing nothing leaves the instrument reporting a confident wrong number in both directions on every run, with no external signal that anything is wrong. The measured state is already known: on five real captures the harvester achieves precision 3/6 and recall 3/8, with zero attribution on every finding it emits. The consequences are not hypothetical — three runs were already published as evidence of model non-determinism when the spread was partly an artifact of how many housekeeping bullets the reviewer appended, and the golden-set task downstream is blocked because precision and recall need a per-finding key the harvester does not produce. Every further run spends real tokens generating rows that will have to be discarded. The alternatives considered: (a) hand-inspect every raw capture before trusting a run — restores correctness for one careful operator on five PRs and discards the entire point of a mechanical instrument; (b) fix only the phantom findings (RC1), the visible half — the recall hole is the more dangerous half precisely because a missing finding leaves no trace at all, and it is the one that would silently absorb a rules regression that stopped the reviewer finding things; (c) fix extraction but keep the body-only fallback instead of failing loudly — the ledger keeps filling with rows that look like data and cannot be scored, which is the exact defect family this is the fifth instance of; (d) rewrite the review command to emit machine-readable findings instead of parsing markdown — the right long-term answer and explicitly out of scope, because changing the measured configuration and the instrument in the same change destroys the baseline that specs 002–004 established. All four root causes live in one layer, are reachable by unit tests against captures that already exist on disk, and none of the downstream measurement work can start until they are closed.
