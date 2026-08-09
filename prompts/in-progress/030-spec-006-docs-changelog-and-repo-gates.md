---
status: approved
spec: [006-bench-golden-scoring-and-report]
created: "2026-08-09T11:34:00Z"
queued: "2026-08-09T10:16:50Z"
---

<summary>
- The benchmark's own documentation now explains the scoring contract instead of stating that scoring does not exist
- It spells out what each of the three curation states means, so a number on a report page can be read without opening the source
- It states plainly that a finding nobody curated is triage evidence, never a black mark against the configuration
- It records both honest caveats about what the two ratios currently measure, so the caveats outlive the spec that introduced them
- It explains how repeated attempts are separated — by counting occurrences, never by the clock — and why the obvious clock-based approach is wrong on the real data
- It documents which rows get skipped and why, using the exact console message an operator will see
- The long-standing claim that nothing from a benchmark run is ever committed is corrected to name the two deliberate exceptions
- The release notes describe the whole feature rather than the last slice of it, and the repository's own quality gates are re-run end to end
</summary>

<objective>
Document the scoring contract in `bench/README.md`, amend its committed-output invariant to name the two exceptions, add a `## Unreleased` CHANGELOG entry describing what all four preceding prompts shipped, and re-run the repository's mechanical gates — tracked reports directory, no deleted tests, assertion floors, frozen fixtures, no personal paths, standard library only, full precommit.
</objective>

<context>
Read `CLAUDE.md` for project conventions — Python 3 standard library only, no personal paths, generic examples only, never commit (dark-factory handles git).

Read `specs/in-progress/006-bench-golden-scoring-and-report.md`. This prompt is **prompt 5 of 5** and satisfies **AC1, AC16, AC22, AC23, AC24, AC25**. Load-bearing sections: `## Acceptance Criteria` AC1/AC16/AC22/AC23/AC24/AC25 (AC22 including its **Anti-keyword-stuffing** paragraph), `## Constraints` (especially "Committed-output exceptions are exactly two" and "A scorer change requires no cache clear"), `## Desired Behavior` items 3, 4, 5 and 7, and the `## Assumptions` note on the 36 line-shaped signatures.

**This prompt depends on prompts 1-4 of this spec having landed.** Verify before you start:

```bash
grep -n 'def score_findings\|def score_config\|def write_report\|def load_golden\|def load_ledger\|def score_ledger\|def partition_by_prs_version' bench/run.py
grep -n '"--score"\|"--reports-dir"' bench/run.py
```

If any is absent, stop and report `status: failed` with the message `"prompts 1-4 of spec 006 not yet landed"`. This prompt writes documentation about behaviour that must already exist; describing unshipped behaviour is the doc-disagrees-with-repo failure that produced D1, D2, D4, D7 and the whole of spec 005.

Read `bench/README.md` in full — in particular `## Current state` (which currently states that `--golden` is recognised and rejected with exit code 2, and that "the golden set and scoring semantics belong to a later spec"), `## Running it` (exit codes), `### Fixtures`, `## Fixed invariants` (whose `**Cache:**` bullet carries the parenthetical "gitignored — no benchmark output is ever committed") and `## Result row`.

Read `CHANGELOG.md`'s head and `docs/changelog-guide.md` for the conventional-prefix rules. **Never hardcode the topmost released version** — it moves with every release (it was `## v0.35.6` when this prompt was written and `## v0.35.7` hours later). Resolve it at execution time:

```bash
grep -n -m1 '^## v' CHANGELOG.md        # the first released section, whatever it is
grep -n -m1 '^## Unreleased' CHANGELOG.md ; echo "unreleased-exit=$?"
```

If `## Unreleased` already exists, **append your bullets to it**; never create a second one. If it does not, insert it immediately above the line the first `grep` reported.

Read `docs/dod.md` for the repository's Definition of Done.

**Report what actually shipped, not what you would have shipped.** Before writing a word of the README or the CHANGELOG, read the four preceding prompts' actual output: `bench/run.py`'s scoring functions and the report a real scoring pass renders. If prose and code disagree, the code wins and you fix the prose.
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
f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209  bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl
6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9  bench/testdata/capture-notes-block-h2.md
5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93  bench/testdata/capture-numbered-findings-h3.md
2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c  bench/testdata/capture-traceability-h4.md
36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79  bench/testdata/capture-summary-trailer-h4.md
de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae  bench/testdata/sample-report.md
be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db  bench/testdata/real-capture-report.md
SHA
echo "digest check exit=$? (expect 0)"
```

A `FAILED` line or a non-zero exit → stop and report `status: failed` with the observed digest. The six pre-existing capture fixtures are frozen by the spec's `## Constraints` exactly as the four new ledger slices are. **Never regenerate one.**

## 2. Rewrite `bench/README.md` § `## Current state`

Replace the sentence claiming scoring belongs to a later spec and that `--golden` is rejected. State what now exists: the runner drives the real review over the pinned manifest and writes one row per PR, and a scoring layer turns a ledger plus `bench/golden.json` into per-run precision and recall and a committed report page per configuration. Name both entry points — `--golden` on a live (or fully cache-served) run, and `--score` over an existing ledger — and state that scoring invokes no review, spends no tokens and needs no network.

## 3. Add a `## Scoring` section to `bench/README.md`

Place it after `## Reading review output` and before `## Verifying an entry without cloning`. Each of the six topics below must be **its own prose block of at least two non-empty lines** — AC22's anti-keyword-stuffing rule rejects a one-line bullet list that merely contains the keywords, and requires the nine greps to match on **at least nine distinct line numbers**.

1. **The match rule and the three states** (`### Matching and the three golden states`). State the rule exactly as `bench/golden.json`'s `match_rule` field does: `rule_id` exact when both sides carry one, otherwise `path` equality plus **every** signature keyword present case-insensitively in the finding's `body`; `line` is never used for identity; path comparison is whole-string with no extension requirement. Then the three states: an unmatched **`accepted`** entry is a recall miss, a matched **`rejected`** entry is a precision penalty, an **`unreviewed`** entry is excluded from both numerator and denominator of both ratios and a finding matching one is neither a penalty nor a candidate.

2. **Gap-triage** (`### Gap-triage candidates`). A finding matching no golden entry is a **gap-triage candidate**: quoted verbatim on the report page under its own heading and counted against nothing. It is **not a precision failure** — use that exact phrase. Explain why in the README's own words: the golden set is bootstrapped from a single strong-model run, not hand-curated ground truth, so a configuration finding something the baseline missed is evidence the set is **incomplete**. Cite the recorded case: `bench/golden.json`'s `known_corrections` records `tts-mcp#20` annotated "clean — correct answer is zero findings" on the strength of six zero-finding runs from a weaker model, and the strong model then found a real, hand-verified defect in it.

3. **The precision caveat** (`### What precision currently measures`). Must contain the literal `not yet a result`. `golden-dev-1` carries zero `rejected` entries, so precision cannot be lost by any configuration; a precision of `1.000` is a property of the golden set's adjudication state and is not yet a result.

4. **The recall caveat** (`### What recall currently measures`). Must contain `36 of the 42 signatures` and `embed a line reference`. A re-report of the same issue at a different line does not match and surfaces as a gap-triage candidate rather than a hit, so on this golden set `recall` measures whether a configuration cited the same line, not whether it found the issue. Give the measured evidence: across the four runs of config `9ce66e05…` only 5 of 16 findings hit an entry, and the `apt-key` issue in `.github/workflows/ci.yml` is reported in all four runs at lines 13, 29, 9 and 27 and is a gap candidate every time.

   Both caveats must be greppable in the README **exactly as they are on the report page** — they live in both places because a caveat that dies with the spec is precisely the doc-disagrees-with-repo failure this repository has hit five times.

5. **Run chunking** (`### Runs are an occurrence index, never a timestamp cluster`). Must contain `occurrence index` or `k-th row`. Within one `config_hash`, the k-th ledger row for a given `pr_id`, in ledger file order, belongs to run k. State the measured reason no clock works: the boundary between run 2 and run 3 of config `9ce66e05…` is **48 seconds** while gaps *inside* runs 1, 2 and 4 reach **140, 128 and 110 seconds**. Then partial runs: a run not covering every PR the golden set describes is labelled **partial** and is scored only over the PRs it covers — the missing PRs' entries are **out of scope, not misses**, so a 3-PR run scores against 24 entries and a 1-PR run against 1.

6. **The per-row `prs_version` skip** (`### Rows recorded against another PR manifest`). Must contain the literal `PRS VERSION SKIP`. Every ledger row whose own `prs_version` differs from the golden set's is skipped **before scoring**, named on stderr with that literal together with its `config_hash` and both version strings. A configuration with no surviving rows gets **no page at all**; one with some survivors gets a page whose Configuration block records `rows skipped`. State the observed scale: 4 of the 66 rows on disk, across 3 of the 7 configurations, carry `empty-diff-probe`, `mode-full-probe` or `ruleid-probe`.

Additionally, in the same section: describe the report page — its location `bench/reports/<config_hash>.md` (full 64-character hash, tracked in git), its four sections in order, that it carries no generation timestamp so re-scoring unchanged data yields a byte-identical file, and that **cost is not recorded** because the ledger carries no cost field. State that a scorer change requires **no cache clear** — the config hash covers `rules/` + `commands/` but not `bench/run.py`, and scoring consumes already-normalised findings, so the existing cache-clearing instruction continues to apply to **harvest** changes alone. Do not document, add or imply automatic cache invalidation.

## 4. Amend the committed-output invariant

`## Fixed invariants` currently reads, on the `**Cache:**` bullet, "gitignored — no benchmark output is ever committed". Amend that statement so it **names the two exceptions on the same line or on lines immediately following it**: the report pages under `bench/reports/` and the four frozen ledger slices under `bench/testdata/`. AC22 checks `grep -n 'never committed\|is ever committed' bench/README.md` and requires the matched line either to reference the exceptions itself or to be immediately followed by them. Nothing else from a run is committed — `bench/results/` and `bench/.cache/` stay gitignored.

Add matching `## Fixed invariants` bullets for the scoring layer, mirroring the existing style: the match rule and its priority order; the exclusion of `line` from identity; the three state names; the gap-triage classification; the run-chunking rule; the report location and filename form; three-decimal ratio rendering and the `n/a` literal; the absence of a generation timestamp; and the precondition marker literals `GOLDEN SET NOT FOUND`, `INVALID GOLDEN SET`, `GOLDEN VERSION MISMATCH`, `PRS VERSION SKIP`, `EMPTY LEDGER`, `CORRUPT LEDGER`, `INVALID CONFIG HASH`.

## 5. Document the four ledger slices

Extend `### Fixtures` (or add `### Ledger slices` beside it) with a table naming all four committed slices, what each contains and its `sha256`, using the values from requirement 1. AC22 requires `grep -ciE 'ledger-baseline-opus|bench/testdata/ledger'` ≥ 1, and the anti-keyword-stuffing check requires that match to land in **prose, not in a table row** — so name `bench/testdata/ledger-baseline-opus-xhigh-full.jsonl` in the surrounding paragraph as well as in the table. State in prose that they are **verbatim extracts of real ledger rows**, installed by the operator before approval, and that no test may author a ledger row in their place — five defects reached production because fixtures were written from the same template as the parser consuming them.

## 6. Update `## Running it`

Document the two scoring invocations and the exit codes. **The fenced block below is README *content* to write into the file — it is not a command for you to run.** `make bench` invokes the real review command against real tokens and is operator-only:

```bash
make bench BENCH_ARGS="--model <model> --effort <effort> --mode <short|full|selector> --golden bench/golden.json"
python3 bench/run.py --score --golden bench/golden.json
```

State that `--reports-dir` defaults to `bench/reports`, that score mode **requires** `--golden` and **rejects** `--model` / `--effort` / `--mode` (a scored ledger's identity comes from its rows), and extend the existing exit-code sentence: 2 also covers a missing or invalid golden set, an empty or absent ledger, a corrupt ledger line and a live-run `prs_version` disagreement; a rejected `config_hash` yields a non-zero exit while the other configurations are still scored.

## 7. Write the `## Unreleased` CHANGELOG entry

Insert a `## Unreleased` section immediately above the **topmost `^## v` line resolved at execution time**, or append to an existing `## Unreleased` if one is already present. Never hardcode a version number as the anchor. Describe **the whole change all five prompts shipped** — this one's documentation included — not the last slice — the specific failure from spec 002, where the final prompt described only its own work and the release classifier cut a patch instead of a minor.

Requirements (AC23): at least **2** bullets; **every** bullet matches `^- (feat|fix|docs): `; within the section a case-insensitive search for `scor|precision|recall` matches at least once and for `report` at least once, **on two distinct bullet lines**. Follow `docs/changelog-guide.md`. Suggested shape — **four** bullets: one `feat:` for the scoring layer and the two ratios with their degenerate cases; one `feat:` for the report page and the gap-triage section; one `feat:` for the **user-facing CLI surface** — `--golden` now scoring instead of refusing, the new `--score` mode over an existing ledger, `--reports-dir`, the per-row `PRS VERSION SKIP`, and the precondition literals `GOLDEN SET NOT FOUND` / `INVALID GOLDEN SET` / `GOLDEN VERSION MISMATCH` / `EMPTY LEDGER` / `CORRUPT LEDGER` / `INVALID CONFIG HASH`; and one `docs:` for the README contract and the amended committed-output invariant. The CLI bullet is called out explicitly because AC23's mechanical check cannot detect its omission — `scor|precision|recall` and `report` both match without it, and a release classifier reading a CHANGELOG that never mentions a new flag cuts the wrong size. Name the load-bearing decision explicitly in the text: a finding matching no golden entry is reported as a gap-triage candidate, never as a precision failure.

## 8. Re-run the repository's mechanical gates

These are audits, not edits. Fix what they surface; do **not** relax a check to make it pass.

- **AC16 — `bench/reports/` is tracked.** `git check-ignore -q bench/reports` exits **1**; `git diff "$BASE" -- .gitignore` (same tag-first baseline as AC24) contains no added line matching `reports`; after scoring `bench/testdata/ledger-baseline-opus-xhigh-full.jsonl` into `bench/reports/`, `bench/reports/cc64cc99…6838b.md` appears in `git status --porcelain -uall` (the default `-unormal` collapses a brand-new untracked directory to a single `?? bench/reports/` entry, so the filename would never show). Use the **fixture** as input, never the gitignored live ledger — a container clone contains the former and never the latter. Leave the produced page in the working tree; dark-factory handles git.
- **AC24 — nothing was deleted or gutted.** Resolve the baseline **tag-first**, never bare `origin/master` — this repository documented and rejected the moving-baseline defect in `prompts/completed/026-spec-005-…` and it must not regress: prefer the topmost release tag (`git rev-parse --verify -q '<tag>^{commit}'`, with `<tag>` read from the first `^## v` line of `CHANGELOG.md`), else fall back to `origin/master` **while printing an explicit vacuity warning**, else print `BASELINE UNAVAILABLE` and do **not** report the diff checks as passing. Against that baseline, `git diff "$BASE" -- bench/test_config.py bench/test_resolve.py bench/test_review.py | grep -c '^-.*def test_'` returns **0** — name the three files **explicitly**, never `bench/test_*.py`, because the glob expands against the working tree and cannot see a file deleted outright. Add a `test -f` existence check per file for the same reason. Per-file assertion floors `grep -cE '^\s*(self\.assert|assert )'` return ≥ **63** on `bench/test_config.py`, ≥ **46** on `bench/test_resolve.py`, ≥ **265** on `bench/test_review.py`; `git diff "$BASE" -- bench/testdata/sample-report.md bench/testdata/real-capture-report.md bench/testdata/capture-notes-block-h2.md bench/testdata/capture-numbered-findings-h3.md bench/testdata/capture-summary-trailer-h4.md bench/testdata/capture-traceability-h4.md` is empty — the four capture files named explicitly, for the same glob reason. Per-file floors, not a repo-wide total: a new `bench/test_score.py` with 200 assertions must not pay for a gutted `test_review.py`.
- **AC25 — no personal paths, no third-party imports.** `grep -rn '/Users/\|~/Documents/' bench/` returns 0 lines (exit 1), including inside the four ledger slices and any rendered report page; every `import` / `from` line in `bench/run.py` names a Python 3 standard-library module only.
- **AC1 — the suite grew and the gate is green.** `make precommit` exits 0; `python3 -m unittest discover -s bench -p 'test_*.py'` reports `OK` and `Ran N tests` with **N > 103**.

If neither the release tag nor `origin/master` resolves, say so explicitly in your report and do **not** report the diff-based checks as passing. The verification block below carries the guarded form.

## 9. Out of scope for this prompt — do not implement

Do not change `bench/run.py`'s behaviour, add a flag, add a metric, add token counting or cost capture, add automatic cache invalidation, edit `commands/pr-review.md` or anything under `rules/`, edit `bench/golden.json` or any file under `bench/testdata/`, or modify `.gitignore`. If a gate in requirement 8 fails because of a defect in prompts 1-4, fix the defect in `bench/run.py` or `bench/test_score.py` — never by weakening the gate, and never by editing a frozen input.

AC26, AC27 and AC28 are **operator-executed on the host after merge** — they spend real tokens against the live review command. Do not attempt them, do not add them to any verification block, and do not write a test that simulates them.
</requirements>

<constraints>
- Python 3 **standard library only**. Changes land in `bench/README.md`, `CHANGELOG.md`, `bench/reports/` and — only to fix a defect the gates surface — `bench/run.py` / `bench/test_score.py`.
- **`bench/golden.json` and all ten files under `bench/testdata/` are frozen.** `git diff --exit-code bench/golden.json bench/testdata/` must exit 0.
- **Do NOT modify `.gitignore`.** `bench/reports/` stays un-ignored; `bench/results/` and `bench/.cache/` stay ignored.
- **Do NOT change `commands/pr-review.md` or anything under `rules/`.** Either moves `rules_commands_hash` and orphans every existing ledger row and every published number.
- **Do NOT touch the harvest layer** or its tests. **Do NOT fix D8** — but do not document the scorer as having its dot requirement either; the scorer compares whole paths.
- **The committed-output exceptions are exactly two**: report pages under `bench/reports/` and the frozen ledger slices under `bench/testdata/`. Do not name a third and do not commit `bench/results/` or `bench/.cache/`.
- **Do NOT document or add automatic cache invalidation** on a `bench/run.py` change. Cache invalidation stays manual and stays the operator's call.
- **Do NOT document the match rule, the state names, the gap-triage classification, the run-chunking rule, the report location or the ratio rounding as configurable.** All six are frozen invariants.
- **No test function may be deleted or renamed and no assertion relaxed.** Floors: 63 / 46 / 265.
- Generic examples only; no personal paths (`/Users/`, `~/Documents/`) in any shipped file.
- Do NOT commit — dark-factory handles git.
- Existing tests must still pass.
</constraints>

<verification>
```bash
# All eleven frozen inputs, CHECKED not printed
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
f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209  bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl
6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9  bench/testdata/capture-notes-block-h2.md
5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93  bench/testdata/capture-numbered-findings-h3.md
2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c  bench/testdata/capture-traceability-h4.md
36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79  bench/testdata/capture-summary-trailer-h4.md
de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae  bench/testdata/sample-report.md
be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db  bench/testdata/real-capture-report.md
SHA
echo "digest check exit=$? (expect 0; any FAILED line means stop and report failed)"

# AC22 — nine patterns, and the distinct-line count
grep -niE 'gap-triage|gap triage' bench/README.md
grep -nF 'not a precision failure' bench/README.md
grep -niE 'unreviewed' bench/README.md
grep -niE 'occurrence index|k-th row' bench/README.md
grep -niE 'bench/reports' bench/README.md
grep -niE 'ledger-baseline-opus|bench/testdata/ledger' bench/README.md
grep -niE '36 of the 42 signatures|embed a line reference' bench/README.md
grep -nF 'not yet a result' bench/README.md
grep -nF 'PRS VERSION SKIP' bench/README.md
python3 - <<'EOF'
import re, pathlib
text = pathlib.Path('bench/README.md').read_text().splitlines()
pats = [r'(?i)gap-triage|gap triage', r'not a precision failure', r'(?i)unreviewed',
        r'(?i)occurrence index|k-th row', r'(?i)bench/reports',
        r'(?i)ledger-baseline-opus|bench/testdata/ledger',
        r'(?i)36 of the 42 signatures|embed a line reference',
        r'not yet a result', r'PRS VERSION SKIP']
lines = set()
for p in pats:
    hits = [i + 1 for i, l in enumerate(text) if re.search(p, l)]
    print(f'{p[:40]:42} hits={len(hits)}')
    lines.update(hits)
print('distinct matched lines:', len(lines), '(expect >= 9)')
assert len(lines) >= 9, f'AC22 distinct-line floor not met: {len(lines)}'

# AC22 anti-keyword-stuffing, prose-block half.  A neighbouring BULLET or TABLE ROW
# is not prose.  Nine consecutive one-line bullets otherwise vouch for each other and
# satisfy the very rule they violate — each one's "non-empty non-heading neighbour" is
# the next stuffed bullet.  (Reproduced: a nine-bullet README passed the naive form.)
LIST_OR_TABLE = re.compile(r'^\s*([-*+]\s|\d+[.)]\s|\|)')
def is_prose(i):
    if not (0 <= i < len(text)):
        return False
    s = text[i].strip()
    return bool(s) and not s.startswith('#') and not LIST_OR_TABLE.match(text[i])
def in_prose_block(idx):
    i = idx - 1
    return is_prose(i) and (is_prose(i - 1) or is_prose(i + 1))
lonely = sorted(n for n in lines if not in_prose_block(n))
print('matched lines that are bullets/table rows or stand alone:', lonely)
assert not lonely, f'AC22 prose-block rule violated on lines {lonely} — each pattern must match inside a paragraph of >=2 prose lines, not a bullet or a table row'
EOF

# The committed-output invariant names the two exceptions (asserted, not merely printed)
python3 - <<'EOF'
import pathlib, sys
text = pathlib.Path('bench/README.md').read_text().splitlines()
hits = [i for i, l in enumerate(text) if 'never committed' in l or 'is ever committed' in l]
print('invariant lines:', [i + 1 for i in hits])
assert hits, 'the committed-output invariant sentence is gone'
ok = False
for i in hits:
    window = '\n'.join(text[i:i + 4])
    print('---'); print(window)
    if 'bench/reports' in window and 'bench/testdata' in window:
        ok = True
assert ok, 'the invariant sentence does not name both exceptions within 3 following lines'
print('committed-output invariant OK')
EOF

# AC16 — reports dir tracked, gitignore untouched
git check-ignore -q bench/reports ; echo "check-ignore exit=$? (expect 1)"
git diff -- .gitignore ; echo "gitignore working-tree diff must be empty"
python3 - <<'EOF'
import shutil, tempfile, pathlib, subprocess, sys
tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copy('bench/testdata/ledger-baseline-opus-xhigh-full.jsonl', tmp / 'results.jsonl')
r = subprocess.run([sys.executable, 'bench/run.py', '--score', '--golden', 'bench/golden.json',
                    '--out-dir', str(tmp), '--reports-dir', 'bench/reports'],
                   capture_output=True, text=True)
print('exit', r.returncode, r.stdout.strip(), r.stderr.strip())
shutil.rmtree(tmp)
assert r.returncode == 0, f'AC16: the fixture scoring pass failed: {r.stderr}'
EOF
# `git status --porcelain` COLLAPSES a brand-new untracked directory to a single
# `?? bench/reports/` entry — the filename never appears, so a per-file grep can
# never match.  `-uall` lists every untracked file individually.
git status --porcelain -uall bench/reports/
python3 - <<'EOF'
import pathlib, subprocess
page = 'bench/reports/cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md'
assert pathlib.Path(page).is_file(), f'AC16: the fixture scoring pass wrote no {page}'
out = subprocess.run(['git', 'status', '--porcelain', '-uall', 'bench/reports/'],
                     capture_output=True, text=True).stdout
print(out)
assert page in out, f'AC16: {page} is invisible to git status — is bench/reports ignored?'
print('AC16 page present and visible to git: OK')
EOF

# AC24 — nothing deleted or gutted (guarded baseline)
# Tag-first baseline resolver.  A bare `origin/master` is a MOVING baseline: if it has
# already advanced past prompts 1-4, every diff below is vacuous and reads as a pass.
# This repository documented and rejected that defect in prompts/completed/026-spec-005.
TAG=$(grep -m1 '^## v' CHANGELOG.md | sed 's/^## //')
if [ -n "$TAG" ] && git rev-parse --verify -q "${TAG}^{commit}" >/dev/null; then
  BASE="$TAG"
  echo "baseline: release tag $BASE"
elif git rev-parse --verify -q 'origin/master^{commit}' >/dev/null; then
  BASE=origin/master
  echo "WARNING: release tag unavailable; falling back to the MOVING ref origin/master."
  echo "         If it has advanced past prompts 1-4 these diffs are vacuous — say so in your report."
else
  BASE=
  echo "BASELINE UNAVAILABLE: neither the release tag nor origin/master resolves."
  echo "Report this explicitly; do NOT report AC24's diff checks as passing."
fi
if [ -n "$BASE" ]; then
  # Name the three test files explicitly: a bench/test_*.py glob expands against the
  # WORKING TREE and cannot see a file deleted outright.
  for f in bench/test_config.py bench/test_resolve.py bench/test_review.py; do
    test -f "$f" || echo "MISSING TEST FILE: $f (AC24 violated — a whole file was deleted)"
  done
  # Asserted, not merely printed: `grep -c` prints a count and exits, so a non-zero
  # count reads as ordinary output and the daemon does not check exit codes.
  BASE="$BASE" python3 - <<'EOF'
import os, subprocess, sys
base = os.environ['BASE']
def diff(*paths):
    return subprocess.run(['git', 'diff', base, '--', *paths],
                          capture_output=True, text=True).stdout

tests = ['bench/test_config.py', 'bench/test_resolve.py', 'bench/test_review.py']
deleted = [l for l in diff(*tests).splitlines() if l.startswith('-') and 'def test_' in l]
print('deleted test defs:', len(deleted))
assert not deleted, f'AC24: test functions deleted or renamed: {deleted}'

gi = [l for l in diff('.gitignore').splitlines() if l.startswith('+') and 'reports' in l]
print('added gitignore reports lines:', gi)
assert not gi, f'AC16: .gitignore gained a reports rule: {gi}'

frozen = ['bench/testdata/sample-report.md', 'bench/testdata/real-capture-report.md',
          'bench/testdata/capture-notes-block-h2.md', 'bench/testdata/capture-numbered-findings-h3.md',
          'bench/testdata/capture-summary-trailer-h4.md', 'bench/testdata/capture-traceability-h4.md']
fd = diff(*frozen)
print('frozen-fixture diff bytes:', len(fd))
assert not fd.strip(), f'AC24: a frozen capture fixture changed:\n{fd[:400]}'

floors = {'bench/test_config.py': 63, 'bench/test_resolve.py': 46, 'bench/test_review.py': 265}
import re, pathlib
for name, floor in floors.items():
    path = pathlib.Path(name)
    assert path.is_file(), f'AC24: {name} is missing entirely'
    n = sum(1 for l in path.read_text().splitlines() if re.match(r'^\s*(self\.assert|assert )', l))
    print(f'{name}: {n} assertions (floor {floor})')
    assert n >= floor, f'AC24: {name} fell below its assertion floor: {n} < {floor}'
print('AC24 mechanical checks OK')
EOF
fi
# AC23 — the Unreleased section
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md
python3 - <<'EOF'
import re, pathlib
text = pathlib.Path('CHANGELOG.md').read_text().splitlines()
starts = [i for i, l in enumerate(text) if l.startswith('## Unreleased')]
assert starts, 'AC23: no "## Unreleased" section in CHANGELOG.md'
assert len(starts) == 1, f'AC23: {len(starts)} "## Unreleased" sections — there must be exactly one'
start = starts[0]
end = next((i for i, l in enumerate(text[start + 1:], start + 1) if l.startswith('## ')), len(text))
section = text[start + 1:end]
bullets = [l for l in section if l.startswith('- ')]
bad = [l[:30] for l in bullets if not re.match(r'^- (feat|fix|docs): ', l)]
scor = [i for i, l in enumerate(bullets) if re.search(r'(?i)scor|precision|recall', l)]
rep_ = [i for i, l in enumerate(bullets) if re.search(r'(?i)report', l)]
print('bullets', len(bullets), 'bad prefixes', bad, 'scoring', scor, 'report', rep_)
assert len(bullets) >= 2, f'AC23: only {len(bullets)} bullets'
assert not bad, f'AC23: non-conventional bullet prefixes: {bad}'
assert scor, 'AC23: no bullet mentions scoring/precision/recall'
assert rep_, 'AC23: no bullet mentions the report'
assert len(set(scor) | set(rep_)) >= 2, 'AC23: the two topics must land on two DISTINCT bullet lines'
print('CHANGELOG Unreleased OK')
EOF

# AC25 — repo conventions
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$? (expect 1)"
python3 - <<'EOF'
import ast, pathlib, sys
tree = ast.parse(pathlib.Path('bench/run.py').read_text())
mods = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        mods.update(a.name.split('.')[0] for a in node.names)
    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        mods.add(node.module.split('.')[0])
external = sorted(m for m in mods if m not in sys.stdlib_module_names)
print('imports:', sorted(mods))
print('non-stdlib:', external)
assert not external, f'AC25: non-stdlib imports in bench/run.py: {external}'
EOF

# AC1 — suite grew, gate green
python3 -m unittest discover -s bench -p 'test_*.py' 2>&1 | tee /tmp/bench-suite.out | tail -5
python3 - <<'EOF'
import re, pathlib
out = pathlib.Path('/tmp/bench-suite.out').read_text()
m = re.search(r'^Ran (\d+) tests', out, re.M)
assert m, 'no "Ran N tests" line in the unittest output'
n = int(m.group(1))
print('Ran', n, 'tests (AC1 requires > 103)')
assert n > 103, f'AC1: suite did not grow: {n}'
assert re.search(r'^OK', out, re.M), 'suite is not green'
EOF
make precommit
```

Expected: the digest check exits 0 with no `FAILED` line; each of the nine README patterns matches at least once and the distinct matched-line count is ≥ 9; the `is ever committed` line references the report pages and the frozen ledger slices, or is immediately followed by them; `git check-ignore` exits 1 and the `.gitignore` diff is empty; the fixture-driven scoring pass writes `bench/reports/cc64cc99063178c49ed7bf9118c0cb92cd84d085877c8498c99e66a97de6838b.md` and `git status --porcelain -uall` shows it as untracked or added by name; the baseline resolves to the release tag, the deleted-test grep prints `0`, the `.gitignore` diff grep prints `0`, no `MISSING TEST FILE` line appears and the frozen-fixture diff is empty (or the moving-baseline warning / baseline-unavailable notice is reported explicitly); the AC24 block prints `AC24 mechanical checks OK` with the three assertion counts at or above 63, 46 and 265; the CHANGELOG check prints ≥ 2 bullets, an empty bad-prefix list and ≥ 2 distinct bullet lines covering scoring and the report; the personal-path grep exits 1; the AST import check prints an empty non-stdlib list; the AC16 assertion block prints `AC16 page present and visible to git: OK`; the unittest run reports `OK` with `Ran N tests`, `N > 103`; `make precommit` exits 0.
</verification>
