---
status: completed
spec: [005-bug-bench-harvest-finding-extraction]
summary: 'Documented harvest contract in bench/README.md § Reading review output (4 sub-sections), extended fixtures table to 6 rows, rewrote CHANGELOG.md ## Unreleased with 5 bullets covering the whole of spec 005'
execution_id: coding-exec-026-spec-005-harvest-contract-docs-and-changelog
dark-factory-version: v0.192.9
created: "2026-08-08T11:44:00Z"
queued: "2026-08-08T12:14:20Z"
started: "2026-08-08T12:41:45Z"
completed: "2026-08-08T12:45:00Z"
---

<summary>
- The benchmark's own documentation now states the rules the code actually follows for turning review text into findings
- It says what ends a findings section, including the bold-label block that previously defeated the boundary and produced invented findings
- It says both list styles open a finding, so the next reader does not re-derive the rule that lost the reviewer's most severe tier
- It says where a finding's file, line and rule attribution comes from, and that it comes from the reviewer's own markers rather than the runner's bookkeeping
- It names the loud refusal by its literal marker, so an operator hitting it can act without reading the runner's source
- The fixtures table lists all four new captures with their origin, fingerprint and expected result, so the next fixture author copies real output instead of transcribing a template
- The changelog entry describes the whole change — invented findings, dropped findings, missing attribution, loud refusal — rather than the last slice of it
- That matters because the release classifier reads the entry to decide how big the change was, and an under-described entry once drew the wrong version bump
- Final sweeps confirm no personal filesystem paths and no third-party dependencies anywhere in the benchmark
- Last of five prompts, deliberately last so the documentation describes what actually shipped
</summary>

<objective>
Write the corrected harvest contract into `bench/README.md` § "Reading review output" — what ends a findings section, both list styles that open one, where attribution is read from, and what happens to an item that cannot be attributed — extend its fixtures table with the four new captures, and consolidate `CHANGELOG.md`'s `## Unreleased` section so one reader sees the whole of spec 005 rather than this prompt's slice. Then run the repository-wide sweeps that close the spec's container-verifiable criteria.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 standard library only, no personal paths, generic examples only, never commit — dark-factory handles git).

Read `specs/in-progress/005-bug-bench-harvest-finding-extraction.md`. This prompt satisfies the contract half of **Desired Behavior 6** and **Acceptance Criteria AC1, AC15, AC16, AC17 and AC18**. Load-bearing sections: `## Acceptance Criteria` AC15/AC16/AC17/AC18 **including all three anti-keyword-stuffing clauses**, `## Why this is a bug`, `## Constraints`, and `## Suggested Decomposition`'s rationale for putting this prompt last.

**This prompt depends on prompts 1-4 of this spec having landed.** Verify before you start:

```bash
grep -n 'BOLD_RUN_START_RE\|ORDERED_ITEM_RE\|def extract_attribution\|UNATTRIBUTABLE_MARKER\|def unattributable_report' bench/run.py
```

If any of the five is absent, stop and report `status: failed` with the message `"prompts 1-4 of spec 005 not yet landed"`. Do not implement them here.

Read `bench/run.py` — **take every documented fact from the code, not from this prompt and not from memory.** In particular read: `BOLD_RUN_START_RE`, `BULLET_RE`, `ORDERED_ITEM_RE`, `THEMATIC_BREAK_RE`, `FENCE_RE`, `RULE_TAG_RE`, `HEAD_RULE_TAG_RE`, `LEADING_BOLD_RE`, `PATH_LINE_RE`, `LINE_MENTION_RE`, `UNATTRIBUTABLE_MARKER`, `list_item_body`, `_normalize_body`, `extract_attribution`, `harvest`, `HarvestResult`, `unattributable_report`, and step 6a of `process_pr`. Quote the real marker literals and the real behaviour; do not describe anything the code does not do.

Read `bench/README.md`. You extend `## Reading review output`, which currently has the sub-sections "The three required sections", "What ends a findings section", "What opens a finding" and "Fixtures", and you update `## Fixed invariants`, whose "List-item markers" bullet still says only `-` and `*` open a finding. Match the file's voice: short declarative sections, a `###` heading per topic, tables where the shape fits, and a `> **Why …**` paragraph wherever a reader would otherwise restore the wrong behaviour.

Read `CHANGELOG.md`. The frozen preamble runs from `# Changelog` down to the last `* PATCH …` bullet; the newest section is `## v0.35.3`. `## Unreleased` goes immediately after that preamble and directly above `## v0.35.3`. Note that v0.35.1's three `- bench: …` bullets are the file's only non-conforming entries and are exactly the release that under-described a large change.

Read `docs/changelog-guide.md` — `RULE changelog/preamble-frozen` and `RULE changelog/conventional-prefix-required`, plus the prefix→bump table.

Read `docs/dod.md` — no personal paths anywhere, a `## Unreleased` CHANGELOG entry required.
</context>

<requirements>

## 1. Rewrite `bench/README.md` § "Reading review output"

Four topics, **each its own `###` sub-section with its own prose block of at least two non-empty lines**. One keyword-dense line satisfies every grep while documenting nothing; the four topics must also match on at least four distinct line numbers.

**Topic 1 — what ends a findings section.** Update the existing "What ends a findings section". A section's content ends at the next markdown heading of any level, at a thematic break, at a line outside a fenced block whose first non-whitespace content opens a **bold run**, or at end of input — whichever comes first. Use the words "bold run" and "bold label". Name the two shapes that were observed defeating the old boundary: `**Notes:**` and `**Summary**:`. State that termination never depends on the terminating heading's level relative to the section's own, because level varies run to run inside a single mode. Add:

> **Why a bold label ends a section.** A review whose three severity sections all read `None.` — the correct answer, zero — was harvested as three findings, verbatim the three bullets of a trailing `**Notes:**` block. A bold label introduces a new block, and everything under it belongs to that block.

**Topic 2 — what opens a finding.** Update the existing "What opens a finding". Both list styles open one: an unordered item (`-` or `*` followed by whitespace) and an **ordered/numbered** item (a run of digits followed by `.` and whitespace). Use both the words "numbered" and "ordered list". State that ordered numbering need not start at 1 and is not limited to one digit; that non-list lines following an open item extend it; that a line inside a fenced code block is ordinary text and opens nothing; and that prose appearing before the first item — most importantly the mandated `None.` sentinel — contributes no finding. State that only the list marker is stripped from the body and the item's leading bold run is preserved verbatim. Add:

> **Why numbered items matter most.** The reviewer writes its more severe tiers as numbered lists. A capture carrying five numbered Should Fix items harvested to two — the two Nice to Have bullets — so the parser lost precisely the findings that matter most, and left no trace of the loss.

**Topic 3 — where attribution comes from.** A new `###` sub-section. `rule_id` has **two sources, in strict priority order**, and the README must document both — a doc that names only the first would be false about the shipped parser, which is the docs-disagree-with-code mechanism behind D1, D2, D4 and D7:

1. The item's own inline `*(rule: \`<id>\`)*` marker. When present it always wins and is recorded as the literal string the reviewer wrote, **whether or not that id appears in `rules/index.json`**.
2. **Only when no marker is present**, a backticked token at the very head of the item that **is a member of `rules/index.json`**. This legacy shape is what three findings in the frozen `bench/testdata/sample-report.md` depend on, and it stays index-gated on purpose: at the head of an item an unknown backticked token is far more likely to be a file path or a symbol than a rule name. State this asymmetry explicitly rather than glossing it.

Under either source, an id named in the item's prose, in the item's tail, in a traceability table, or anywhere outside the item is never attributed to it. `path` and `line` are read from the bold run at the head of the item, in the shapes the reviewer writes; a path or line appearing only in the trailing prose is not used when the leading bold run supplies one; no path is ever inferred by searching the repository and no line is ever guessed from surrounding text. Use the literal text `rule: ` and the phrase "inline rule tag" or "inline rule marker". Include the four observed bold-reference shapes as a small table with their resulting `path` and `line`. Add:

> **Why the inline marker is not validated against the rule index.** A tag naming a renamed rule, a rule added since the index was written, or a review run against a different rules revision would otherwise yield `null` — attribution would become a property of the runner's bookkeeping rather than of the reviewer's output. The instrument records what the reviewer claimed; reconciling that against the shipped rule set is the scorer's job, and coupling the two hides rule drift instead of surfacing it. The head-anchored legacy source keeps its index gate because it has no explicit marker to trust: there, membership is the only signal that a backticked token is a rule name at all.

**Topic 4 — when a finding cannot be attributed.** A new `###` sub-section containing the literal string `UNATTRIBUTABLE FINDING`. An item inside a severity section that yields neither a `path` nor a `rule_id` cannot be keyed, cannot be matched against a golden set, and is never written down as a body-only finding. Such a PR fails in the same class as the existing `NOT A REVIEW` gate: no ledger row, no `<key>.json` row marker, the PR listed as failed, the remaining PRs still processed, the process exits non-zero. State the deliberate difference between the two gates — `NOT A REVIEW` fires before the raw-output write and leaves nothing behind, while this gate fires after it, so the `<key>.stdout.txt` stays on disk and the review is re-harvestable after a parser fix without spending tokens again — and that a both-stream failure artifact is written under `bench/.cache/failures/`. State that there is no opt-out. Add:

> **Why a body-only finding is refused.** A finding with no path and no rule id is an unmatchable measurement dressed as a data point. A false rejection costs one operator decision and a re-run; a false acceptance writes an unscoreable row into an append-only ledger.

## 2. Extend the fixtures table

Replace the existing two-row table under `### Fixtures` with a six-row table carrying **Fixture / Origin / `sha256` / Harvests to** for all six files. The two pre-existing rows keep their content. The four new rows:

| Fixture | Origin | `sha256` | Harvests to |
|---|---|---|---|
| `bench/testdata/capture-notes-block-h2.md` | verbatim capture, `node-skeleton#2` short mode, `##` headings, all three sections `None.` with a trailing `**Notes:**` block | `6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9` | 0 findings, 0 unattributable |
| `bench/testdata/capture-numbered-findings-h3.md` | verbatim capture, `python-skeleton#3` full mode, `###` headings, five numbered Should Fix items with inline rule tags plus a positive-notes list | `5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93` | 5 findings, 2 unattributable |
| `bench/testdata/capture-traceability-h4.md` | verbatim capture, `node-skeleton#2` full mode, `####` headings, one bold-headed finding plus a 22-row traceability table | `2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c` | 1 finding, 0 unattributable |
| `bench/testdata/capture-summary-trailer-h4.md` | verbatim capture, `github-pr-review-agent#11` short mode, `####` headings, all three sections `None.` with a `**Summary**:` trailer | `36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79` | 0 findings, 0 unattributable |

Confirm every digest against the file before writing it (`shasum -a 256 <file> | cut -d' ' -f1`) and confirm every "Harvests to" figure by replaying the harvester over the fixture. Do not copy a number from this prompt without checking it.

Keep and strengthen the existing closing sentence: a fixture for a new defect must be a **capture of real output**, not a transcription of the template. Add that every capture checked in before this change carried zero findings, so no fixture in the repository had ever exercised the parser against a real finding — which is how this defect family reached five occurrences.

## 3. Update `## Fixed invariants`

- Replace the "List-item markers" bullet: both `-`/`*` unordered items and digit-run ordered items open a finding; prose before the first item cannot form one; a list item inside a fenced code block opens nothing.
- Add a "Section terminators" bullet: next heading of any level, thematic break, bold-run line outside a fence, end of input.
- Add an "Inline rule tag" bullet: `*(rule: \`<id>\`)*`, read positionally from the item and recorded literally, **not validated against `rules/index.json`** — and, in the same bullet or an adjacent one, the head-anchored fallback used only when no marker is present, which **is** index-gated. Do not write "never validated against `rules/index.json`" unqualified; that claim is false for the fallback path.
- Add an "Unattributable-item rejection" bullet naming `UNATTRIBUTABLE FINDING` and stating that it is not configurable and has no opt-out.
- Leave every other bullet, and the `## Safety invariant` and `## Result row` sections, untouched. The `findings` row-schema entry is still `Normalised list of {path, line, rule_id, body}` — the schema did not change.

## 4. Write the `CHANGELOG.md` `## Unreleased` entry

Insert `## Unreleased` immediately after the frozen preamble and directly above `## v0.35.3`. Do not touch the preamble and do not touch any released section.

Every bullet must match `^- (fix|feat|docs): `. The non-conforming `- bench: ` style must not appear. The section needs **at least three bullets**, and the three topic patterns must land on **three distinct bullet lines** — one bullet naming all three defects passes the loose greps while under-describing the change, which is the failure that drew a patch bump on v0.35.1.

Write one bullet per shipped behaviour, describing the whole of spec 005 and not this prompt's slice:

1. `fix:` — a trailing bold-label block (`**Notes:**`, `**Summary**:`) now ends a findings section, so housekeeping bullets after a clean review are no longer invented as findings. Must match `notes|trailing|invent|phantom`.
2. `fix:` — numbered/ordered items open a finding exactly as bullets do, so the reviewer's most severe tier is no longer dropped; a list item inside a fenced block opens nothing; the item's leading bold run survives marker stripping. Must match `numbered|dropped`.
3. `fix:` — `path`, `line` and `rule_id` are read from the reviewer's own markers — the item's leading bold reference and its inline `*(rule: …)*` tag — the inline tag's id recorded literally and independent of the runner's copy of `rules/index.json`, with the head-anchored legacy shape retained as an index-gated fallback. Must match `rule id|path|attribut`.
4. `fix:` — an item inside a severity section that yields no attribution now fails the PR loudly with `UNATTRIBUTABLE FINDING`, leaving no ledger row and no row marker while preserving the raw capture, in the same class as the existing `NOT A REVIEW` gate.
5. `docs:` — the harvest contract in `bench/README.md` and four verbatim capture fixtures that lock it down.

## 5. Run the closing sweeps

- **AC18 — no personal paths, no third-party dependencies.** `grep -rn '/Users/\|~/Documents/' bench/` must return nothing (exit 1). Every `import` / `from` line in `bench/run.py` must name a Python 3 standard-library module only — list them and check each.
- **AC15 — no test deleted, no test file gutted.** Use the **immutable tag `v0.35.3`** as the diff baseline, not `origin/master`. `origin/master` is a moving ref: if the daemon pushed between prompts 1 and 5 it has advanced past prompts 1-4, so a diff against it covers only prompt 5 — which touches no test file — and AC15 goes vacuously green on exactly the work it polices. It also fails green when it does not resolve at all, because git writes to stderr and `grep -c` then prints `0`.

  Resolve the baseline in this order: `v0.35.3^{commit}` if it verifies; else `origin/master^{commit}` with an explicit warning in your report that the result may be vacuous; else neither, in which case print `BASELINE UNAVAILABLE`, say so in your report, and **do not report AC15's diff checks as passing**.

  With a baseline, `git diff "$BASE" -- bench/test_config.py bench/test_resolve.py bench/test_review.py | grep -c '^-.*def test_'` must return `0` — list the three files explicitly rather than using the `bench/test_*.py` glob, which expands against the working tree and would silently miss a file that was deleted. `git diff "$BASE" -- bench/testdata/sample-report.md bench/testdata/real-capture-report.md` must be empty. The per-file assertion floors must hold regardless of baseline availability: `bench/test_config.py` ≥ 63, `bench/test_resolve.py` ≥ 46, `bench/test_review.py` ≥ 165.
- **AC1 — the suite grew and the gate is green.** `python3 -m unittest discover -s bench -p 'test_*.py'` reports `OK` with `Ran N tests`, `N > 72`; `make precommit` exits 0.
- **Fixture provenance.** All four capture digests still match the published values, and the two pre-existing fixtures still match `de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae` (`sample-report.md`) and `be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db` (`real-capture-report.md`).

If any sweep fails, fix the cause in the file that caused it. Never edit a fixture, never delete a test, never relax an assertion to make a sweep pass.

## 6. Failure handling

This prompt writes documentation and a changelog entry; it changes no runtime behaviour. If a documented fact and the code disagree, the **code** is authoritative for what the documentation says — re-read `bench/run.py` and document what it does. Do not change `bench/run.py` here to match a sentence you wrote; if the code is genuinely wrong, stop and report the discrepancy.

</requirements>

<constraints>
- **Changes land only in `bench/README.md` and `CHANGELOG.md`.** Do NOT change `bench/run.py`, `bench/test_*.py` or `bench/testsupport.py` in this prompt.
- **Never create, regenerate, overwrite or edit any file under `bench/testdata/`.** On a digest mismatch, stop and report failed.
- **The CHANGELOG preamble is frozen** (`RULE changelog/preamble-frozen`): `# Changelog` down to the last `* PATCH …` bullet is untouched, and no released section is edited.
- **CHANGELOG entries use conventional prefixes** `fix:` / `feat:` / `docs:` per `docs/changelog-guide.md`. The `- bench: ` style used in v0.35.1 is not repeated — dark-factory's version-bump detector reads the prefix.
- **The entry describes the whole change, not this prompt's slice.**
- **No test function may be deleted and no assertion relaxed.** Per-file assertion floors: `bench/test_config.py` ≥ 63, `bench/test_resolve.py` ≥ 46, `bench/test_review.py` ≥ 165. Suite count strictly greater than 72.
- **Do NOT document a behaviour the code does not have**, and do NOT document a knob, flag or opt-out — there are none, and describing one would invite an implementer to add it.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file, including the README.
- Python 3 standard library only; no third-party dependencies anywhere under `bench/`.
- Do NOT change `bench/prs.json`, `commands/pr-review.md`, or any rule, agent, command or doc that participates in a review.
- Do NOT commit — dark-factory handles git.
</constraints>

<verification>
```
# Prompts 1-4 landed (precondition, not a new check)
grep -n 'BOLD_RUN_START_RE\|ORDERED_ITEM_RE\|def extract_attribution\|UNATTRIBUTABLE_MARKER\|def unattributable_report' bench/run.py

# AC16 — the four README patterns, each present
grep -ciE 'bold label|bold run' bench/README.md            # expect >= 1
grep -ciE 'numbered|ordered list' bench/README.md          # expect >= 1
grep -ciE 'rule: |inline (rule )?(tag|marker)' bench/README.md  # expect >= 1
grep -cF 'UNATTRIBUTABLE FINDING' bench/README.md          # expect >= 1
grep -ciE 'rules/index\.json' bench/README.md              # expect >= 2
grep -niE 'rules/index\.json' bench/README.md | cut -d: -f1 | sort -u | wc -l   # expect >= 2 distinct lines
grep -ciE 'head-anchored|head of the item' bench/README.md # expect >= 1

# AC16 anti-keyword-stuffing — the four patterns match on >= 4 distinct lines
{ grep -niE 'bold label|bold run' bench/README.md; \
  grep -niE 'numbered|ordered list' bench/README.md; \
  grep -niE 'rule: |inline (rule )?(tag|marker)' bench/README.md; \
  grep -nF 'UNATTRIBUTABLE FINDING' bench/README.md; } | cut -d: -f1 | sort -u | wc -l   # expect >= 4

# AC16 — each topic is its own sub-section
grep -n '^### ' bench/README.md

# AC16 — the fixtures table lists all four new captures with their digests
grep -c 'capture-notes-block-h2.md\|capture-numbered-findings-h3.md\|capture-traceability-h4.md\|capture-summary-trailer-h4.md' bench/README.md  # expect >= 4
grep -c '6427028bef301ff8\|5530049fa4d116dc\|2922746bb95bdb3a\|36e15eca61133033' bench/README.md  # expect >= 4

# AC17 — the Unreleased section, its prefixes and its bullet count
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md | tee /tmp/unreleased.txt
test -s /tmp/unreleased.txt && echo "unreleased section non-empty"
grep -c '^- ' /tmp/unreleased.txt                           # expect >= 3
grep -c '^- bench: ' /tmp/unreleased.txt                    # expect 0
grep -E '^- ' /tmp/unreleased.txt | grep -cvE '^- (fix|feat|docs): ' ; echo "non-conforming bullets above (expect 0)"
grep -ciE 'notes|trailing|invent|phantom' /tmp/unreleased.txt   # expect >= 1
grep -ciE 'numbered|dropped' /tmp/unreleased.txt                # expect >= 1
grep -ciE 'rule id|path|attribut' /tmp/unreleased.txt           # expect >= 1

# AC17 anti-keyword-stuffing — three distinct bullet lines carry the three topics
{ grep -niE 'notes|trailing|invent|phantom' /tmp/unreleased.txt; \
  grep -niE 'numbered|dropped' /tmp/unreleased.txt; \
  grep -niE 'rule id|path|attribut' /tmp/unreleased.txt; } | cut -d: -f1 | sort -u | wc -l   # expect >= 3

# The frozen CHANGELOG preamble was not disturbed
head -12 CHANGELOG.md
grep -n '^## ' CHANGELOG.md | head -3   # expect '## Unreleased' first, then '## v0.35.3'

# AC18 — no personal paths, stdlib only
grep -rn '/Users/\|~/Documents/' bench/ ; echo "exit=$? (expect 1)"
grep -nE '^(import|from) ' bench/run.py

# AC15 — no test deleted, fixtures frozen, assertion floors held
# AC15 baseline: use the IMMUTABLE tag, not the moving branch ref.
# `origin/master` fails green two ways: if it does not resolve, git writes to stderr,
# `grep -c` prints 0 and the anti-gutting gate passes; and if the daemon pushed between
# prompts 1 and 5 it has advanced past prompts 1-4, so the diff covers only prompt 5 —
# which touches no test file — making AC15 vacuously green on exactly the work it polices.
if git rev-parse --verify -q 'v0.35.3^{commit}' >/dev/null; then
  BASE=v0.35.3
elif git rev-parse --verify -q 'origin/master^{commit}' >/dev/null; then
  BASE=origin/master
  echo "WARNING: tag v0.35.3 unavailable; falling back to the moving ref origin/master."
  echo "         If it has advanced past prompts 1-4 these diffs are vacuous — say so in your report."
else
  BASE=
  echo "BASELINE UNAVAILABLE: neither v0.35.3 nor origin/master resolves in this environment."
  echo "Report this explicitly; do NOT report AC15's diff checks as passing."
fi
if [ -n "$BASE" ]; then
  git diff "$BASE" -- bench/test_config.py bench/test_resolve.py bench/test_review.py | grep -c '^-.*def test_'   # expect 0
  git diff "$BASE" -- bench/testdata/sample-report.md bench/testdata/real-capture-report.md                       # expect empty
fi
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 165

# Fixture provenance, all six — CHECKED, not printed. A print loop compares against
# nothing: a mismatched fixture would emit output an agent reports as a pass, reducing
# the provenance gate to decoration.
shasum -a 256 -c - <<'SHA'
6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9  bench/testdata/capture-notes-block-h2.md
5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93  bench/testdata/capture-numbered-findings-h3.md
2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c  bench/testdata/capture-traceability-h4.md
36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79  bench/testdata/capture-summary-trailer-h4.md
de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae  bench/testdata/sample-report.md
be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db  bench/testdata/real-capture-report.md
SHA
echo "shasum -c exit=$? (expect 0; any FAILED line means stop and report failed)"

# AC1 — suite grew, gate green
python3 -m unittest discover -s bench -p 'test_*.py' 2>&1 | tail -5
make precommit
```

Expected: the four README greps each return ≥1 on ≥4 distinct lines; the four new fixture names and their digest prefixes appear in the README; the extracted Unreleased section carries ≥3 bullets, all `fix:`/`feat:`/`docs:`, zero `- bench: `, with the three topics on ≥3 distinct bullet lines; `## Unreleased` is the first `## ` section and `## v0.35.3` the second; the personal-path grep exits 1; every `bench/run.py` import names a standard-library module; the deleted-test grep prints `0` and the frozen-fixture diff is empty; all six digests match their published values; the unittest run reports `OK` with `Ran N tests`, `N > 72`; `make precommit` exits 0.
</verification>
