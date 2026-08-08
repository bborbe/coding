---
status: completed
spec: [003-bench-review-sanity-and-harvest-boundary]
summary: Documented harvest contract in bench/README.md and consolidated Unreleased changelog entry covering all of spec 003
execution_id: coding-bench-harvest-exec-017-spec-003-harvest-contract-docs-and-changelog
dark-factory-version: v0.192.9
created: "2026-08-08T02:35:00Z"
queued: "2026-08-08T00:49:10Z"
started: "2026-08-08T00:57:29Z"
completed: "2026-08-08T00:59:20Z"
---

<summary>
- The rules the benchmark uses to read a review are written down where the next fixture author will actually look
- Anyone adding test data now learns, without reading the parser, what ends a findings section and what starts a finding
- The three sections a review must contain, and what happens when one is missing, are documented alongside those rules
- The documentation names the two checked-in fixtures and says which one is a real capture and which one is derived from the command's template
- The changelog entry describes the whole change — both the rejection of non-review output and the harvest boundary fix — so the release classifier weighs it correctly instead of cutting a patch for a feature
- A final sweep confirms no personal filesystem paths and no third-party dependencies were introduced anywhere in the benchmark
- The full repository gate runs green with a larger test suite than before
</summary>

<objective>
Write the harvest contract down in `bench/README.md` — what ends a findings section, what opens a finding, and the three-section requirement the sanity gate enforces — and consolidate `CHANGELOG.md`'s `## Unreleased` section so one reader can see the whole change. The root cause of the phantom finding was a contract that existed only as a parser and a fixture that agreed with each other and with nothing else; this prompt closes that. Last prompt of spec 003, deliberately last so the changelog can describe what actually shipped.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, generic examples only, never commit).

Read `specs/in-progress/003-bench-review-sanity-and-harvest-boundary.md` — this prompt satisfies **Acceptance Criteria AC1, AC12, AC13, AC14** and **Desired Behavior 5**'s second half ("The harvest contract ... is written down alongside the fixtures"). Two constraints are load-bearing:
- *"The CHANGELOG bullet describes the whole change, not the last prompt's slice."* Spec 002 shipped a 1,075-line runner whose Unreleased section never described it, and the release classifier consequently cut a patch instead of a minor.
- *"Do NOT make the sanity gate's stderr excerpt length, the set of required section names, or the list-item markers configurable — all three are invariants."* Document them as fixed; do not document a knob that does not exist.

**This prompt depends on prompts 1 and 2 of this spec having landed.** Verify before you start:

```bash
grep -n 'def heading_section_name\|def iter_report_lines\|def missing_sections\|def non_review_report' bench/run.py
ls bench/testdata/
```

If `heading_section_name`, `iter_report_lines`, `missing_sections` or `non_review_report` is absent, or `bench/testdata/real-capture-report.md` does not exist, stop and report `status: failed` with the message `"prompts 1-2 of spec 003 not yet landed"`. Do not implement them here.

Read `bench/run.py` — the shipped behaviour you are documenting. Take the contract from the code, not from memory: `REQUIRED_SECTION_NAMES`, `THEMATIC_BREAK_RE`, `BULLET_RE`, `FENCE_RE`, `heading_section_name`, `iter_report_lines`, `harvest`, `missing_sections`, `rejection_excerpt`, `non_review_report`, and the gate call inside `process_pr`. Do not describe anything the code does not do.

Read `bench/README.md` — the file you extend. It already documents the configuration tuple, `prs.json`, how to run it, the diff-range rule, the `EMPTY DIFF` abort, the fixed invariants, the safety invariant and the result-row schema. It says nothing about how review output is read. Match its voice: short declarative sections, a `##` heading per topic, tables where the shape fits, a "why" paragraph wherever a reader would otherwise restore the wrong behaviour.

Read `bench/testdata/sample-report.md` (template-derived, `####` headings, three findings) and `bench/testdata/real-capture-report.md` (verbatim capture of live output, `##` headings, all three sections `None.`, trailing prose, zero findings) — the two fixtures you name in the new section.

Read `CHANGELOG.md` — its `## Unreleased` section, created by prompt 1 and appended to by prompt 2, sits above `## v0.35.1`. Read `docs/changelog-guide.md` for entry style.

Read `docs/dod.md` — no personal paths anywhere, `## Unreleased` entry required, 4-version alignment not touched.
</context>

<requirements>

## 1. Add a `## Reading review output` section to `bench/README.md`

Place it after the `## Diff-range rule` section and before `## Verifying an entry without cloning`. It documents three things and their rationale.

**a. The three required sections and the sanity gate.** `commands/pr-review.md` Step 5 marks `Must Fix`, `Should Fix` and `Nice to Have` **MANDATORY** and mandates the literal `None.` for an empty section. A report is a review only when all three appear as markdown headings; output missing any of them is rejected before the raw output is cached and before it is harvested, so a rejected PR leaves no ledger row and no cache entry, the remaining PRs still run, and the process exits non-zero — the same treatment an `EMPTY DIFF` gets, for the same reason. The rejection names the PR, names each missing section on its own `missing sections: ` line, and carries a bounded verbatim excerpt on stderr. Record why: a subprocess that exits 0 after printing `Unknown command: /coding:pr-review` is otherwise indistinguishable from a genuinely clean review, and a fabricated clean row is byte-shaped exactly like a real one.

**b. What ends a findings section.** A section's content ends at the next markdown heading of any level, at a thematic break (`---`, `***` or `___` on its own line), or at end of input — whichever comes first. The section names are matched as headings at any level with the severity annotation optional; a mention in prose, in a bold run, or inside a fenced code block is not a heading. Record why heading level carries no information: the command's template renders the sections at one level and captured live output rendered them at another, so level is not evidence of anything.

**c. What opens a finding.** Inside a findings section a finding starts when a list item starts (`-` or `*`); subsequent non-list lines extend the finding already open. Prose appearing in a section before any list item — most importantly the mandated `None.` sentinel — contributes no finding and cannot be extended by anything that follows it. Record why: real review output carries a diff summary and a closing status panel after the last section, and before the boundary rules existed those lines were appended as continuation lines to the still-open `None.` buffer, which defeated the sentinel check and emitted the accumulated text as one finding with no path, line or rule id. That is the phantom finding the known-clean fixture PR recorded.

Name both fixtures and say what each one locks:

| Fixture | Origin | Harvests to |
|---|---|---|
| `bench/testdata/sample-report.md` | derived from the review command's Step 5 template, `####` headings | 3 findings |
| `bench/testdata/real-capture-report.md` | verbatim capture of live review output, `##` headings, all three sections `None.`, trailing prose | 0 findings |

State the rule for anyone adding a third: a fixture is a capture of real output, not a transcription of the template. Both defects this section documents survived 42 green unit tests because the tests were built from the same template the parser was built from.

Do not restate the harvest normalization rules the code does not have. Do not document a configuration knob: the three required section names, the fact that all three are required, the list-item markers and the stderr excerpt bound are fixed invariants. Add them to the existing `## Fixed invariants` list rather than inventing a parallel list.

The section must satisfy, and you must run:

```
grep -nE 'thematic break|ends at the next' bench/README.md      # >= 1 line
grep -cE 'Must Fix|Should Fix|Nice to Have' bench/README.md     # >= 3
```

## 2. Consolidate the `## Unreleased` CHANGELOG entry

Rewrite the bullets under `## Unreleased` in `CHANGELOG.md` so they describe the whole of spec 003 — not the last prompt's slice. Use conventional prefixes (`fix:` for both defect fixes, `docs:` for the contract documentation) per `docs/changelog-guide.md`, one bullet per logical change. Do NOT reuse the `bench: ...` style: those two bullets on v0.35.1 are the only non-conforming entries in the file, and v0.35.1 is precisely the release whose bullets under-described a 1,075-line change and drew a patch bump instead of a minor. The section must cover, at minimum:

- the bench runner rejecting review output that is not structurally a review (all three mandatory finding sections present as headings), before the raw-output cache write, leaving no ledger row and no cache entry, with the PR listed as failed and a bounded stderr excerpt naming each missing section
- the harvest section-boundary fix: a findings section ends at the next heading, a thematic break, or end of input, and only a list item opens a finding, so trailing prose can no longer become a phantom finding
- the new `bench/testdata/real-capture-report.md` fixture — a verbatim capture of live review output rather than a transcription of the command's template
- the documented harvest contract in `bench/README.md`

The release classifier reads these bullets to choose the version bump. The literal checks it must pass:

```
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md > /tmp/unreleased.txt
grep -ciE 'bench' /tmp/unreleased.txt                       # >= 1
grep -ciE 'harvest|finding' /tmp/unreleased.txt             # >= 1
grep -ciE 'not a review|non-review|sanity' /tmp/unreleased.txt  # >= 1
```

Do not create a version section, do not rename `## Unreleased` to a version, do not touch any released section, and do not touch the four version strings in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` — releases are manual and handled by maintainer-agent-releaser.

## 3. Final sweep

Run and fix anything these surface. They are checks, not licence to refactor:

- `grep -rn '/Users/\|~/Documents/' bench/` must return no lines (exit 1). This includes both fixtures and the README.
- Every `import` / `from` line in `bench/run.py`, `bench/testsupport.py` and every `bench/test_*.py` names a Python 3 standard-library module only. No third-party imports, no `requirements.txt`, no `pyproject.toml`, no `setup.py`.
- `python3 -m unittest discover -s bench -p 'test_*.py'` reports `OK` with `Ran N tests`, `N > 42`.
- `make precommit` exits 0.

If any of these fails for a reason introduced by prompt 1 or prompt 2, fix it here rather than leaving the spec unshippable, and say so in the completion report.

## 4. Do not modify

`bench/run.py` behaviour (documentation-only prompt — change it only if the sweep in requirement 3 surfaces a genuine defect, and say so in the report), `bench/testdata/sample-report.md`, `bench/testdata/real-capture-report.md`, `bench/prs.json`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`.

Do not add a scenario. The spec's **Scenario coverage** section is explicit: both defects are reachable in unit tests, and the remaining evidence (AC15–AC18) needs real tokens against a live review, which no scenario harness can supply.
</requirements>

<constraints>
- Python 3 standard library only — no third-party dependencies anywhere in `bench/`
- Changes land only in `bench/README.md` and `CHANGELOG.md` (plus any fix requirement 3 genuinely forces)
- The existing tests keep passing and their assertions are not weakened. The suite's test count is strictly greater than 42
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access
- Frozen invariants — document them as fixed, never as configurable: the three required section names, the fact that all three are required, the list-item markers that open a finding, the stderr excerpt bound, the 45-minute review timeout, the cache and results locations, the `--golden` exit-2 rejection
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`. This spec adapts the instrument to the review's real output, never the reverse
- Generic examples only — no trading-domain content (`CLAUDE.md`)
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file (`docs/dod.md`)
- The `## Unreleased` CHANGELOG section describes the whole change, in terms a release classifier can weigh
- The 4-version alignment is NOT touched — releases are manual (`docs/dod.md`)
- Do NOT re-harvest or migrate anything already sitting in `bench/.cache/reviews/`
- Do NOT add a scenario file
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# AC12 — the harvest contract is written down where the next fixture author reads it
grep -nE 'thematic break|ends at the next' bench/README.md
grep -cE 'Must Fix|Should Fix|Nice to Have' bench/README.md
grep -n 'real-capture-report.md\|sample-report.md' bench/README.md

# AC14 — the Unreleased section describes the whole change
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md | tee /tmp/unreleased.txt
test -s /tmp/unreleased.txt && echo "unreleased section non-empty"
grep -ciE 'bench' /tmp/unreleased.txt                          # expect >= 1
grep -ciE 'harvest|finding' /tmp/unreleased.txt                # expect >= 1
grep -ciE 'not a review|non-review|sanity' /tmp/unreleased.txt # expect >= 1

# AC13 — no personal paths, stdlib-only imports
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_*.py

# No packaging crept in
ls bench/ ; test ! -e requirements.txt && test ! -e pyproject.toml && test ! -e setup.py && echo "no packaging files"

# AC1 — the suite grew and is green
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -25

# Both fixtures still harvest to their asserted answers
python3 -c "
import sys; sys.path.insert(0, 'bench')
import run
ids = run.load_rule_ids(run.REPO_ROOT)
cap = (run.BENCH_DIR / 'testdata' / 'real-capture-report.md').read_text()
tpl = (run.BENCH_DIR / 'testdata' / 'sample-report.md').read_text()
assert run.harvest(cap, ids) == [], run.harvest(cap, ids)
assert len(run.harvest(tpl, ids)) == 3, run.harvest(tpl, ids)
assert run.missing_sections(cap) == []
assert run.missing_sections('Unknown command: /coding:pr-review') == list(run.REQUIRED_SECTION_NAMES)
print('OK')
"

# Reserved and mandatory flags unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; `grep -nE 'thematic break|ends at the next' bench/README.md` returns at least one line; the section-name count is at least 3; the extracted Unreleased section is non-empty and all three `grep -ci` checks return at least 1; the personal-path grep exits 1 with no output; every import line names a stdlib module; the verbose unittest run prints `OK` with `Ran N tests`, `N > 42`; the inline Python prints `OK`; both `run.py` invocations exit 2.

Operator-executed after merge, in the spec-verification phase (real tokens, live review command, not runnable here): AC15–AC18 in the spec's **Operator-executable** block — a fresh five-PR run recording five rows, `tts-mcp#20` scoring `0` findings, zero phantom findings across the run, and every recorded row's raw output carrying all three section headings.
</verification>
