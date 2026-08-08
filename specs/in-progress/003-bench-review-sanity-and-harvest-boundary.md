---
status: prompted
tags:
    - dark-factory
    - spec
approved: "2026-08-08T00:23:04Z"
generating: "2026-08-08T00:23:31Z"
prompted: "2026-08-08T00:39:42Z"
branch: dark-factory/bench-review-sanity-and-harvest-boundary
---

## Summary

- The benchmark runner shipped in v0.35.1 and its first real end-to-end run on 2026-08-08 produced two wrong numbers. This spec fixes exactly those two, and nothing else.
- **A non-review was scored as a perfect clean review.** The review subprocess printed `Unknown command: /coding:pr-review` (35 bytes) and exited 0. No guard fired, so the ledger recorded `ok: 0 findings` — the single worst outcome a benchmark can have, because it inflates precision, destroys recall, and does it silently.
- **The findings harvester invented a finding that was not there.** The known-clean fixture PR, whose entire purpose is to score zero, recorded one finding with no path, no line, and no rule id.
- Both defects survived 42 green unit tests because the tests were built from the same template the parser was built from, never from captured output. The fix therefore includes a fixture that is a real capture, not a transcription.
- Two other known defects from the same run (plugin path resolution, stderr-only failure logs) are deliberately excluded and named in Non-goals.

## Problem

The bench runner is the instrument that decides whether a rule change made reviews better or worse. Its first real run against the five pinned fixture PRs produced a result file that looks clean and is wrong in both directions at once. A broken command invocation — the subprocess exiting 0 after printing an error to stdout — passed every guard the runner has and was written down as a review that found nothing, which a scorer would read as flawless precision. At the same time the harvester, on genuinely good output, swept the report's closing prose into a phantom finding, so the one fixture PR curated specifically because the correct answer is zero recorded a one. An instrument that reports a fabricated zero for a broken run and a fabricated one for a clean run is not measuring anything; every downstream number — precision, recall, noise floor, model comparison — is built on it, so the error does not stay contained. Neither defect is detectable from the outside: the ledger row for a non-review is byte-shaped exactly like the row for a real clean review.

## Goal

The runner refuses to write down a number it cannot justify. Review output that is not structurally a review — missing any of the three mandatory finding sections that the review command declares mandatory — fails that PR loudly and leaves no ledger row and no cache entry behind, exactly as an empty diff already does. Review output that *is* a review is harvested with explicit section boundaries, so the narrative prose a real review wraps around its findings never becomes a finding, at any markdown heading level. The test fixtures that guard both behaviours are captures of real output rather than transcriptions of the command's template, so a future divergence between template and reality fails a test instead of shipping.

## Non-goals

- Do NOT fix the plugin path resolution defect (D1) — the preflight resolves the marketplace / `installLocation` path while Claude Code actually loads from `plugins/cache/<name>/<name>/<version>/`. Real and critical, but it changes *what the preflight resolves*, which is a different contract with its own failure modes. Separate spec.
- Do NOT change the failure-log mechanism (D3) — failure logs preserve stderr only, while Claude Code writes real errors to stdout. This spec's sanity gate writes its own bounded stderr excerpt; it does not touch how timeout and non-zero-exit failure logs are written. Separate spec.
- Do NOT make `review_env()` supply an authentication token — the runner cannot authenticate on its own; that is an operator-environment concern.
- Do NOT build scoring, a golden set, or any precision/recall semantics. `--golden` stays reserved-and-rejected with exit 2, exactly as it is today.
- Do NOT change any rule, agent, command, or doc that participates in a review, including `commands/pr-review.md`. The measured configuration must stay fixed while the instrument is repaired — changing both at once destroys the baseline the first run established.
- Do NOT re-harvest or migrate raw outputs already sitting in `bench/.cache/reviews/`. The new boundary rules apply to output harvested from this change forward; an operator who wants the old rows re-normalized deletes the cache and re-runs.
- Do NOT make the sanity gate's stderr excerpt length, the set of required section names, or the list-item markers configurable — all three are invariants. If a future consumer demands variation, that is a separate spec.
- Do NOT broaden what opens a finding (numbered lists, bold-lead paragraphs, tables). No observed review output uses them; adding speculative parsing is how the current fixture drifted from reality in the first place.

## Desired Behavior

1. **Output that is not structurally a review fails the PR, loudly.** `commands/pr-review.md` Step 5 states, in bold, that all three finding sections are mandatory and that an empty section is written as `None.` — so a report is a review only if all three of Must Fix, Should Fix, and Nice to Have are present as section headings. Output that lacks any of them is not a review, whatever the subprocess exit code was. The runner rejects it before the raw output is cached and before harvesting: no ledger row, no cache entry, the PR listed as failed in the run summary, remaining PRs still processed, and the process exits non-zero — the same treatment an empty diff gets today, for the same reason (it is otherwise indistinguishable from a genuinely clean review).

2. **The gate recognises headings, names what is missing, and shows what it got.** The three section names are matched as markdown headings at any level, with the severity annotation (`(Critical)`, `(Important)`, `(Optional)`) optional — the review command's template writes them at one level and real output was observed at another, so level is not evidence of anything. A bare mention of the words in prose or inside a fenced block is not a heading and does not satisfy the gate. The rejection message names the PR id, names each missing section, and carries a bounded verbatim excerpt of the rejected output, so the operator can tell `Unknown command: /coding:pr-review` apart from a truncated report without opening a cache file.

3. **Findings sections have explicit end boundaries.** A section's content ends at the next markdown heading, at a thematic break, or at end of input — whichever comes first. Real review output carries arbitrary trailing prose after the last section: a diff summary, and the operator's global memory appends a closing status panel. None of that is inside a findings section, so none of it can become a finding, and none of it can attach itself to the finding above it.

4. **Only a list item opens a finding, and `None.` opens nothing.** Inside a findings section, a finding starts when a list item starts; subsequent non-list lines extend the finding already open. Prose appearing in a section before any list item — most importantly the mandated `None.` sentinel of an empty section — contributes no finding and cannot be extended by anything that follows it. The observable consequence is that a report whose three sections all read `None.`, followed by a thematic break and a paragraph of summary prose, harvests to zero findings; and a report with one real finding plus the same trailing prose harvests to exactly that one finding, unaltered.

5. **Fixtures are captured, not transcribed.** The checked-in test data includes at least one file that is a verbatim capture of output a live review actually emitted, carrying its real heading levels, its `None.` sentinels, and its trailing prose. The existing template-derived fixture stays, so both renderings are locked against regression. The harvest contract — what ends a section, what opens a finding, what the sanity gate requires — is written down alongside the fixtures, because the root cause of the phantom finding was a contract that existed only as a parser and a fixture that agreed with each other and with nothing else.

## Constraints

- **Language and dependencies:** Python 3 standard library only. Changes land in `bench/run.py`, `bench/test_*.py`, `bench/testsupport.py`, `bench/testdata/`, `bench/README.md`, and `CHANGELOG.md`. No packaging, no third-party imports, no new top-level files outside `bench/`.
- **The 42 existing tests keep passing, and their assertions are not weakened.** Six of them drive the runner with a stub `claude` whose stdout is `findings: []` — which is not review-shaped and will be rejected by Desired Behavior 1. Updating those stub payloads to review-shaped output is expected and correct; deleting a test, removing an assertion, or relaxing an assertion to accommodate the gate is not. The suite's test count after this work is strictly greater than 42.
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access.
- **The gate runs on fresh subprocess output only**, ahead of the raw-output cache write, so a rejected review leaves nothing under `bench/.cache/reviews/` and is retried naturally on the next invocation. It is not applied to cache hits and does not re-validate previously cached output.
- **Frozen invariants** (not configurable, not flagged): the three required section names; the fact that all three are required; the list-item markers that open a finding; the stderr excerpt bound; the 45-minute review timeout; the cache and results locations; the `--golden` exit-2 rejection.
- `bench/prs.json` remains a frozen input — schema, entries, and `dev-1` version unchanged.
- No rule, agent, command, or doc that participates in a review is edited, including `commands/pr-review.md`. This spec adapts the instrument to the review's real output, never the reverse.
- **Repo conventions that must not regress** (`docs/dod.md`): no personal paths (`/Users/`, `~/Documents/`) in any shipped file including the new fixture, and a `## Unreleased` CHANGELOG entry.
- **The CHANGELOG bullet describes the whole change, not the last prompt's slice.** Spec 002 shipped a 1,075-line runner whose Unreleased section never described it, and the release classifier consequently cut a patch instead of a minor. The entry for this work names both the sanity gate and the harvest boundary fix in terms a release classifier can weigh.

## Assumptions

- The review command's three mandatory section headings are a stable contract. `commands/pr-review.md` Step 5 marks them **MANDATORY** with a mandated `None.` for empty sections, which is what makes their absence a reliable non-review signal rather than a stylistic difference.
- Heading *level* is not part of that contract and is not stable: the command's template renders the sections at one level and captured live output rendered them at another. The gate and the harvester therefore treat every heading level as equivalent.
- Real review output carries arbitrary prose before the first section and after the last one — a preamble narrating the diff, a `Step 3a` / `Step 4` trace, a diff-size summary, and a trailing closing panel contributed by the operator's global memory. None of it is under the runner's control and none of it may be interpreted.
- A stub executable on `PATH` that prints a chosen payload to stdout and exits 0 is sufficient to reproduce the non-review defect in a unit test; `bench/testsupport.py` already provides that harness. No live `claude` binary is needed for any container-verifiable criterion.
- The fixture PR set is unchanged and `tts-mcp#20` remains the known-clean entry whose correct answer is zero findings.

## Failure Modes

| Trigger | Expected behavior | Recovery | Detection | Reversibility | Concurrency |
|---|---|---|---|---|---|
| Review subprocess exits 0 but prints an error instead of a report (`Unknown command: …`, usage text, an empty string) | That PR is rejected as a non-review: no ledger row, no cache entry; remaining PRs still run; process exits non-zero | Operator fixes the invocation or the plugin installation and re-runs — the uncached PR is retried, cached PRs are skipped | Non-zero exit; stderr carries the non-review marker, the PR id, the missing section names, and a bounded excerpt of the rejected output; summary lists the PR as failed | Fully reversible — nothing was written | Rows and cache entries for other PRs are untouched |
| Review output is truncated mid-report (subprocess killed, pipe closed) so only the first one or two sections are present | Rejected as a non-review; stderr names the sections that were missing | Re-run the same invocation | Same marker, with the missing section names distinguishing truncation from a wholesale non-review | Fully reversible | Append-only ledger unaffected |
| The review command's template changes the heading level of the three sections | No effect — the gate and the harvester match any heading level | None needed | Fixtures at both observed levels stay green | n/a | n/a |
| The review command renames or drops one of the three sections (contract drift) | Every PR is rejected as a non-review; the whole run fails loudly with zero rows | Operator reconciles the runner's required section names with the command in a follow-up change | All five PRs listed as failed with the same missing-section name — an unmistakable signature of contract drift rather than a per-PR fault | Fully reversible — no rows written | Whole run fails uniformly; no partial ledger to reconcile |
| Real output carries trailing prose (summary, closing panel) after the last section, or preamble prose before the first | Prose outside a findings section is never a finding; prose inside a section that never opened a list item is never a finding | None needed | The clean fixture PR reports zero findings | n/a | n/a |
| A genuine finding's continuation lines wrap across several lines, or a finding body contains the word `None` | The finding is preserved intact with its path, line, and rule id; only a section whose content never opened a list item yields nothing | None needed | Fixture with one real finding plus trailing prose harvests to exactly one finding with the body unchanged | n/a | n/a |
| Rejected output is large (a runaway subprocess printing megabytes) | Only a bounded prefix reaches stderr; the full output is not written to the cache | None needed | Excerpt is visibly truncated | Fully reversible | No disk growth in the cache from a rejected review |
| Crash or interrupt between the gate and the ledger append | Nothing is written: the raw-output cache write and the row append both happen after the gate passes, and the row append is atomic | Re-run; the PR is uncached and retried | Ledger has fewer rows than the manifest | Fully reversible | Atomic write-then-rename means no truncated row is ever observed |

## Security / Abuse Cases

- **Attacker-controlled surface:** the stdout of the review subprocess. It is third-party-influenced text (the reviewed repository's content flows into the model's output) that this change parses more carefully than before.
- **No evaluation, no execution:** the gate and the harvester only match text and slice it. No value from review output is passed to a shell, used to build a filesystem path, or used to construct a subprocess argument.
- **Denial by volume:** review output can be arbitrarily large. The rejection excerpt is bounded so a runaway subprocess cannot flood the operator's terminal or a log file, and rejected output is never persisted to the cache.
- **Denial by pathological input:** section and heading matching is line-oriented with bounded patterns; no construct in the report can cause unbounded backtracking or a scan that is not linear in the input size.
- **Secret leakage:** the rejection excerpt is written to stderr only and reproduces the subprocess's own output; the runner still copies no environment variables, tokens, or credential material into any artifact.
- **Fail-closed, not fail-open:** on any ambiguity about whether output is a review, the outcome is rejection. A false rejection costs one re-run; a false acceptance writes a fabricated measurement into an append-only ledger, which is the failure this spec exists to prevent.

## Acceptance Criteria

Each AC is tagged **[container]** (verifiable at prompt time with no network, no tokens, and no real `claude` binary) or **[operator]** (only observable on the host, because it spends real tokens against the live review command over the fixture PRs) — the same convention as spec 002, whose operator criteria are what caught both of these defects.

- [ ] **AC1 [container]** `make precommit` exits 0 and the bench suite grew — evidence: exit code 0; `python3 -m unittest discover -s bench -p 'test_*.py'` stderr contains `OK` and a `Ran N tests` line with `N > 42`.
- [ ] **AC2 [container]** The exact observed non-review is rejected: with a stub `claude` on `PATH` that prints exactly `Unknown command: /coding:pr-review` to stdout and exits 0, run the runner over a one-PR temp manifest — evidence: process exit code non-zero; stderr contains the non-review marker literal and the PR id; the results file line count is unchanged (`wc -l` before == after); `ls bench/.cache/reviews/` shows no new file for that (PR, configuration) pair; stdout summary line reports `1 failed`.
- [ ] **AC3 [container]** The gate matches headings, not substrings: a stub payload in which the literals `Must Fix`, `Should Fix`, and `Nice to Have` all appear — one in a prose sentence, one inside a fenced code block, one in a bold run — but none as a markdown heading, is rejected exactly as in AC2 — evidence: exit code non-zero; stderr contains the non-review marker; results file gains 0 lines. (Without this criterion a substring check satisfies AC2.)
- [ ] **AC4 [container]** A partially-present report is rejected and the diagnosis names exactly what was missing, across **two** different combinations — evidence, both cases: exit code non-zero, results file gains 0 lines, and the missing-sections list in stderr matches exactly.
  - Case A: payload carries Must Fix and Should Fix, omits Nice to Have → list contains `Nice to Have` and does **not** contain `Must Fix` or `Should Fix`.
  - Case B: payload carries Must Fix only → list contains **both** `Should Fix` and `Nice to Have`, in that order, and does not contain `Must Fix`.

  Case B exists because a single-combination criterion is satisfiable by hardcoding "report the last section as missing" — that implementation passes Case A, AC2 and AC3 without ever computing per-heading presence, and fails Case B.
- [ ] **AC5 [container]** The rejection is diagnosable without opening a cache file: the stderr produced in AC2 contains the literal string `Unknown command:` from the rejected output — evidence: `grep -c 'Unknown command:' <captured stderr>` returns ≥1, and the captured excerpt is bounded (a stub payload of 100 kB produces stderr smaller than 8 kB). The exact excerpt size within that envelope, and the fixture's filename in AC7, are agent decides at impl time.
- [ ] **AC6 [container]** Review-shaped output at either observed heading level still produces a row: two runs over one-PR temp manifests, one stub payload rendering the three sections as `##` headings and one rendering them as `####` headings — evidence: both runs exit 0; each results file contains exactly 1 row; `jq -r .pr_id` on each prints the manifest's single id.
- [ ] **AC7 [container]** `bench/testdata/` contains a capture, not a transcription: a fixture file exists whose three section headings are `##`-level, whose three sections all read `None.`, and which carries a thematic break plus at least three non-empty prose lines after the last section — evidence: `grep -cE '^## (Must Fix|Should Fix|Nice to Have)' <fixture>` prints 3; `grep -cE '^#### (Must Fix|Should Fix|Nice to Have)' <fixture>` prints 0; `grep -c '^\*\*Summary:\*\*' <fixture>` prints ≥1; `grep -rn '/Users/\|~/Documents/' bench/testdata/` returns 0 lines (exit 1).

  **Content fidelity — the fixture must derive from the capture in `## Reference: captured real output`, not be written to satisfy the greps above.** Evidence: `grep -c 'fast-uri' <fixture>` returns ≥1 **and** `grep -c 'mcp/package-lock.json' <fixture>` returns ≥1 **and** `grep -c 'Step 3a: LICENSE Check' <fixture>` returns ≥1. These three literals appear nowhere in `commands/pr-review.md`'s template and cannot be produced by transcribing it.

  Without this, a hand-crafted file satisfying only the four structural greps passes AC7 and AC8 in full — which is precisely the template-agrees-with-itself failure this spec exists to close, reintroduced at the fixture layer.
- [ ] **AC8 [container]** That capture harvests to zero findings: a unit test feeds the AC7 fixture to the harvester — evidence: test exits 0; the assertion compares the full returned list against the empty list and its failure message prints the unexpected findings. (This is the exact input that produced the phantom finding on `tts-mcp#20`.)
- [ ] **AC9 [container]** Trailing prose does not swallow or corrupt a real finding: a unit test feeds a report with exactly one list-item finding under Must Fix, `None.` under the other two sections, then a thematic break and two paragraphs of summary prose — evidence: test exits 0; the assertion compares the full returned list against exactly one finding whose `body` equals the list item's text with no trailing prose appended, and whose `path` and `line` are the values cited in that item. (Without this criterion, dropping every finding whose body contains `None` satisfies AC8.)
- [ ] **AC10 [container]** Heading level is irrelevant to harvesting: a unit test renders identical section content at `##`, `###`, and `####` and asserts all three harvest to the same list — evidence: test exits 0; test name contains `heading_level`; the assertion compares all three lists for equality and prints them on failure.
- [ ] **AC11 [container]** The pre-existing template-derived fixture still harvests to its previously asserted findings, unchanged — evidence: `git diff origin/master -- bench/testdata/sample-report.md` is empty, and the existing sample-report harvest test's expected list is unmodified (`git diff origin/master -- bench/test_review.py | grep -c '^-.*def test_'` prints 0, proving no test was deleted).
- [ ] **AC12 [container]** The harvest contract is written down where the next fixture author will read it: `bench/README.md` documents what ends a findings section, what opens a finding, and the three-section requirement the sanity gate enforces — evidence: `grep -nE 'thematic break|ends at the next' bench/README.md` returns ≥1 line; `grep -cE 'Must Fix|Should Fix|Nice to Have' bench/README.md` returns ≥3.
- [ ] **AC13 [container]** The runner still carries no personal paths and no third-party dependencies — evidence: `grep -rn '/Users/\|~/Documents/' bench/` returns 0 lines (exit 1); every `import` / `from` line in `bench/run.py` names a Python 3 standard-library module only.
- [ ] **AC14 [container]** The CHANGELOG entry describes the whole change so a release classifier can weigh it — evidence: the `## Unreleased` section (extracted from `## Unreleased` up to the next `## ` line) contains a bullet mentioning the bench runner, the rejection of non-review output, and the harvest section-boundary fix; `grep -ciE 'bench' <extracted section>` ≥1, `grep -ciE 'harvest|finding' <extracted section>` ≥1, `grep -ciE 'not a review|non-review|sanity' <extracted section>` ≥1; the extracted section is non-empty.
- [ ] **AC15 [operator]** A fresh full run over the five-PR fixture completes and records five rows — evidence: `make bench BENCH_ARGS="--model <m> --effort <e> --mode <mode>"` exits 0 after deleting `bench/.cache/reviews/` and `bench/results/`; `jq -s 'length' bench/results/results.jsonl` prints 5.
- [ ] **AC16 [operator]** The known-clean fixture PR scores zero, which is the number this spec exists to restore — evidence: `jq -r 'select(.pr_id=="tts-mcp#20") | .findings | length' bench/results/results.jsonl` prints `0`.
- [ ] **AC17 [operator]** No phantom findings anywhere in the run — evidence: `jq -r '.findings[].body' bench/results/results.jsonl | grep -cE '^None\.?( |$)|^\*\*Summary'` prints 0.
- [ ] **AC18 [operator]** Every recorded row came from output that really was a review — evidence: for each row's `raw_output_ref`, `grep -ciE '^#{1,6} +(must fix|should fix|nice to have)' <that file>` prints 3; the count of raw-output files equals the row count.

**Scenario coverage — NO new scenario.** Both defects are reachable in unit tests: the non-review is a stub executable printing 35 bytes and exiting 0, and the phantom finding is a fixture file fed to a pure function. The remaining evidence needs real tokens against a live review, which the scenario harness cannot supply either — AC15-AC18 are operator-executed after merge, exactly as spec 002's operator criteria were, and they are what surfaced these two defects in the first place.

## Verification

### Container-executable (runs inside the YOLO container at prompt time)

```
make precommit
python3 -m unittest discover -s bench -p 'test_*.py' -v
grep -rn '/Users/\|~/Documents/' bench/
grep -cE '^## (Must Fix|Should Fix|Nice to Have)' bench/testdata/<real-capture fixture>
grep -cE '^#### (Must Fix|Should Fix|Nice to Have)' bench/testdata/<real-capture fixture>
git diff origin/master -- bench/testdata/sample-report.md
git diff origin/master -- bench/test_review.py | grep -c '^-.*def test_'
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md
```

Expected: `make precommit` exits 0; the verbose unittest run reports `OK` with `Ran N tests`, `N > 42`, and shows the non-review-gate, missing-section, heading-level, real-capture, and trailing-prose tests by name; the personal-path grep returns nothing (exit 1); the real-capture fixture greps print `3` and `0` respectively; the `sample-report.md` diff is empty; the deleted-test grep prints `0`; the extracted Unreleased section names the runner, the rejection of non-review output, and the harvest fix.

### Operator-executable (runs on the host, spends real tokens)

```
rm -rf bench/.cache/reviews bench/results
make bench BENCH_ARGS="--model <model> --effort <effort> --mode <mode>"
jq -s 'length' bench/results/results.jsonl
jq -r 'select(.pr_id=="tts-mcp#20") | .findings | length' bench/results/results.jsonl
jq -r '.findings[].body' bench/results/results.jsonl | grep -cE '^None\.?( |$)|^\*\*Summary'
jq -r .raw_output_ref bench/results/results.jsonl | while read f; do grep -ciE '^#{1,6} +(must fix|should fix|nice to have)' "$f"; done
```

Expected: the run exits 0 and writes five rows; `tts-mcp#20` reports `0` findings; the phantom-finding grep prints `0`; every raw-output file reports `3`.

## Reference: captured real output

The 1,380-byte stdout captured from the 2026-08-08 run against `tts-mcp#20` — the input that produced the phantom finding. The fixture required by AC7/AC8 reproduces this through the `**Summary:**` line and then carries a trailing thematic break plus the closing-panel lines the real session emitted (their exact wording is operator-specific; what the fixture must preserve is that non-empty prose follows the last section).

```text
The diff is only `mcp/package-lock.json` updating `fast-uri` from `3.1.4` -> `3.1.5`. This is a vendored lockfile change - the `node_modules/fast-uri/` path segment means it doesn't count toward rule-relevant files.

---

## PR Review - bench-pr-20 -> bench-base-20

**Diff size:** 1 file, 3 insertions, 3 deletions

**Changed file:**
- `mcp/package-lock.json` - `fast-uri` 3.1.4 -> 3.1.5 (node_modules vendored dependency)

---

### Step 3a: LICENSE Check
LICENSE file present in repo root.

### Step 4: Automated Checks
**Skipped.** The diff is `mcp/package-lock.json`, which contains only vendored node_modules paths.

---

## Must Fix (Critical)
None.

## Should Fix (Important)
None.

## Nice to Have (Optional)
None.

---

**Summary:** This PR bumps `fast-uri` in the MCP's vendored lockfile. No source code changed. No review findings.
```

**Verified root cause, which differs from the first diagnosis.** The harvester already matches the three section names at heading levels 1 through 6, so heading level alone is not the defect — feeding the block above to the shipped harvester and feeding the same block with `####` headings both produce the same single phantom finding, body `None. --- **Summary:** This PR bumps ...`. The mechanism is that nothing ends a section except another heading: the thematic break and the trailing summary are appended as continuation lines to the still-open `None.` buffer, which defeats the sentinel check and emits the accumulated text as one finding with no path, line, or rule id. Desired Behaviors 3 and 4 target that mechanism. The heading-level requirement is retained as a regression lock (AC6, AC10) because the current behaviour is correct and untested, not because it is broken.

## Suggested Decomposition

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Harvest section boundaries: sections end at the next heading, a thematic break, or end of input; only a list item opens a finding; the `None.` sentinel yields nothing. Add the real-capture fixture and the heading-level, trailing-prose, and clean-capture tests. | 3, 4, 5 | AC7, AC8, AC9, AC10, AC11 | — |
| 2 | The non-review sanity gate ahead of the raw-output cache write; missing-section diagnosis with a bounded stderr excerpt; update the six existing stub payloads to review-shaped output without weakening their assertions. | 1, 2 | AC2, AC3, AC4, AC5, AC6 | prompt 1 |
| 3 | `bench/README.md` harvest-contract section, CHANGELOG `## Unreleased` entry covering the whole change, personal-path and stdlib-only sweep, full precommit. | 5 | AC1, AC12, AC13, AC14 | prompts 1-2 |

Rationale: prompt 1 is a pure-function change with fixture-only evidence and no runner wiring, so it lands and proves itself independently. Prompt 2 changes the runner's control flow and is the prompt that must update the six existing stub payloads — sequencing it after prompt 1 means the review-shaped payloads it writes are already validated by the corrected harvester, rather than both changes moving at once and neither being provable. Prompt 3 is docs and packaging, deliberately last so the CHANGELOG bullet can describe what actually shipped in both prompts — the specific failure mode from spec 002, where the final prompt described only its own slice and the release classifier cut a patch. AC15-AC18 are operator-executed after merge in the spec-verification phase.

## Do-Nothing Option

Doing nothing leaves the instrument reporting confident wrong numbers in both directions. The first real run has already produced them: a broken invocation scored as flawless, and the one PR curated because its correct answer is zero scored a one. Neither is visible in the result file — a fabricated clean row is byte-shaped exactly like a real one — so the failure mode is not "the benchmark is down", it is "the benchmark quietly agrees with whatever you hoped". Every downstream deliverable (golden set, scoring, noise floor, model comparison) reads these rows, so shipping scoring on top of them would launder the errors into numbers nobody can trace back. The alternatives considered: (a) hand-inspect every raw output before trusting a run — restores correctness but discards the entire point of a mechanical instrument, and does not scale past five PRs; (b) fix only the phantom finding and leave the sanity gate for later — cheaper, but the non-review defect is the more dangerous of the two precisely because it looks like success, and it is the one that would silently survive a rules refactor that broke the command; (c) fix only the gate and leave the harvester — leaves the known-clean fixture permanently unable to score zero, which makes the clean PR useless as a control. Both defects were found by the same single run, both live in the same file, and neither is measurable until the other is fixed.
