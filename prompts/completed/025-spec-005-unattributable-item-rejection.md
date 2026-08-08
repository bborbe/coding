---
status: completed
spec: [005-bug-bench-harvest-finding-extraction]
execution_id: coding-exec-025-spec-005-unattributable-item-rejection
dark-factory-version: v0.192.9
created: "2026-08-08T11:43:00Z"
queued: "2026-08-08T12:14:19Z"
started: "2026-08-08T12:33:56Z"
completed: "2026-08-08T12:41:44Z"
---

<summary>
- A review item the benchmark cannot attribute now fails that pull request loudly instead of being written down as a finding with nothing in it
- An unkeyable finding is an unmatchable measurement dressed as a data point; recording it is worse than refusing it
- The refusal is visible: the run exits non-zero, names the pull request, names the section, and quotes the offending item word for word
- It behaves exactly like the existing "not a review" refusal — no ledger row, no cache entry, and the pull request is retried on the next run
- The reviewer's raw output is deliberately kept on disk, so the operator can re-examine it later without spending tokens again
- Every other pull request in the same run still gets processed and recorded
- The refusal is not a blanket one: the same review with a file reference on the item is accepted and recorded normally
- The honest consequence on one real capture is that a genuine review fails rather than contributing two findings that could never be scored
- There is deliberately no opt-out — an escape hatch on this behavior is the regression the whole change exists to close
- Fourth of five prompts, and the only one that touches the runner's control flow
</summary>

<objective>
Make harvesting report every item inside a severity section that yields neither a `path` nor a `rule_id`, and make a non-empty report fail the PR in the same class as the existing `NOT A REVIEW` gate — no ledger row, no `<key>.json` row marker, a both-stream failure artifact, the raw `<key>.stdout.txt` left in place, the PR listed as failed, the remaining PRs still processed, the process exiting non-zero, with a diagnosis headed by the frozen literal `UNATTRIBUTABLE FINDING`.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 standard library only, no personal paths, generic examples only, never commit — dark-factory handles git).

Read `specs/in-progress/005-bug-bench-harvest-finding-extraction.md`. This prompt satisfies **Desired Behavior 5** and **Acceptance Criteria AC11, AC12 and AC13**. Load-bearing sections: `## Desired Behavior` item 5, `## Acceptance Criteria` AC11/AC12/AC13 **including both of their explanatory paragraphs about the `.json` discriminator**, the `## Constraints` bullet "The raw-stdout-before-parsing invariant is preserved, and the two rejection classes differ in what they leave behind", the `## Non-goals` bullet forbidding an opt-out, and the first three `## Failure Modes` rows.

**This prompt depends on prompts 1, 2 and 3 of this spec having landed.** Verify before you start:

```bash
grep -n 'class HarvestResult\|def list_item_body\|def extract_attribution' bench/run.py
```

If any of the three is absent, stop and report `status: failed` with the message `"prompts 1-3 of spec 005 not yet landed"`. Do not implement them here.

Read `bench/run.py`. Take every signature from the file:

- `NON_REVIEW_MARKER = "NOT A REVIEW"` and `REJECTION_EXCERPT_BYTES = 2000` in the constants block — the new marker is their sibling.
- `rejection_excerpt` and `non_review_report` — the diagnosis you mirror.
- `failures_root`, `failure_artifact_path`, `failure_artifact_text`, `write_failure_artifact` — the failure artifact shipped in v0.35.3, reused unchanged.
- `reviews_root`, `cache_row_path`, `cache_raw_path`, `atomic_write_bytes`, `append_row`.
- `harvest`, `HarvestResult`, `flush_finding`, `extract_attribution`.
- `process_pr` end to end. Note the numbered steps: **1** cache check keyed on the row marker alone, **2** resolve, **3** invoke, **4** the `NOT A REVIEW` gate (which fires *before* anything is written), **5** the raw-stdout write with its comment "Write raw stdout verbatim before any parsing", **6** harvest, **7** ledger append, **8** row-marker write.
- `run_bench`'s per-PR `try` block: a `BenchError` becomes `("failed", str(err))`, the loop continues to the next PR, and the summary line counts `failed:` prefixes.

Read `bench/test_review.py`, in particular the module-level helper `run_one_pr_with_payload(td, payload) -> (returncode, captured_stderr, results_dir, cache_root)` and its **five call sites across four classes** (`bench/test_review.py` ~1062, ~1101, ~1128, ~1152, ~1191 — `TestNonReviewOutputIsRejected`, `TestSectionNamesOutsideHeadingsDoNotSatisfyTheGate`, `TestMissingSectionNamesAreReportedExactly` twice, and `TestReviewShapedOutputAtEitherHeadingLevelProducesARow`). They are the shape your AC11 and AC12 tests follow. Also read `TestHarvestKeepsFindingWithoutAnyRuleId`, whose stub payload requirement 5 below changes.

Read `bench/testsupport.py` — `review_report(...)`, `CLEAN_REVIEW_REPORT`, `stub_claude`, `with_path`.

Read `bench/testdata/capture-numbered-findings-h3.md` in full; its two `### Nice to Have (Optional)` bullets are the AC13 subject.

Read `docs/dod.md` for the repository's Definition of Done.
</context>

<requirements>

## 1. Re-verify the fixture you assert against

```bash
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/capture-numbered-findings-h3.md   # expect 5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93
```

On mismatch, stop and report `status: failed` with the observed digest. **Never write, regenerate or edit a file under `bench/testdata/`.**

## 2. Add the frozen marker literal

In the constants block of `bench/run.py`, directly beneath `NON_REVIEW_MARKER = "NOT A REVIEW"`:

```python
UNATTRIBUTABLE_MARKER = "UNATTRIBUTABLE FINDING"
```

That exact string, with a single space, uppercase, no punctuation. It is a frozen invariant: do not derive it, do not make it configurable, do not choose a different one.

## 3. Classify unattributable items during harvesting

In `harvest`'s `flush_finding`, after the `None.` sentinel check and after the call to `extract_attribution`, split the item:

```python
        if path is None and rule_id is None:
            unattributable.append({
                "section": current_section,
                "body": body,
            })
        else:
            findings.append({
                "path": path,
                "line": line_num,
                "rule_id": rule_id,
                "body": body,
            })
```

`line` alone never makes an item attributable — only a `path` or a `rule_id` can key a finding against a golden set. The finding dict keeps exactly its four existing keys `path`, `line`, `rule_id`, `body`; the ledger row schema does not change.

Declare `unattributable: list = []` alongside `findings` at the top of `harvest`, add it to the `nonlocal` declaration in `flush_finding`, and return `HarvestResult(findings=findings, unattributable=unattributable)`. Update `HarvestResult`'s docstring: the field is no longer reserved.

Only items **inside** a severity section are ever classified. Content outside one — a positive-notes list, a traceability table, a notes block — opens no item at all and therefore appears in neither component. This is what keeps a correctly-clean review from failing loudly.

## 4. Build the diagnosis and wire the gate

Add, immediately after `non_review_report`:

```python
def unattributable_report(pr_id: str, items: list, stdout_text: str) -> str:
    """Build the multi-line stderr diagnosis for a review carrying unkeyable items.

    Names the PR, then each offending item's severity section and its text
    verbatim.  The item block is passed through the same bounded excerpt the
    NOT A REVIEW gate uses, so a runaway subprocess cannot flood the terminal.
    """
```

Its output must contain, in order: a first line `f"{UNATTRIBUTABLE_MARKER}: {pr_id}"`; a line stating how many items could not be attributed; then one block per item of the form `f"[{item['section']}] {item['body']}"`; then the line `no ledger row and no row marker were written; this PR is retried on the next run`. Pass the joined item block through `rejection_excerpt(...)` so stderr stays bounded exactly as the existing gate's is. Do not re-print the whole subprocess stdout — the raw capture is already on disk and the failure artifact already carries both streams.

In `process_pr`, insert a new step between the harvest and the ledger append — after step 6, before step 7:

```python
    # 6a. Unattributable-item gate — a finding that cannot be keyed is a parse
    #     failure, not a body-only finding.  Fires *after* the step-5 raw write,
    #     so the raw capture stays on disk and is re-harvestable after a fix,
    #     and *before* the ledger append and the row-marker write, so the PR is
    #     retried next run (the cache check keys on the row marker alone).
    if harvested.unattributable:
        n = len(harvested.unattributable)
        write_failure_artifact(
            cache_root, cfg_hash, pr_id,
            reason=f"{UNATTRIBUTABLE_MARKER}: {n} unattributable item(s)",
            stdout=proc.stdout, stderr=proc.stderr,
        )
        print(unattributable_report(pr_id, harvested.unattributable, proc.stdout),
              file=sys.stderr)
        raise BenchError(
            f"{UNATTRIBUTABLE_MARKER}: {pr_id}: {n} unattributable item(s)"
        )
```

Nothing else in `process_pr` moves. Step 5 stays ahead of step 6; the `NOT A REVIEW` gate stays at step 4, ahead of step 5, and is not touched. `run_bench` needs no change — it already turns a `BenchError` into a `failed` outcome, continues with the remaining PRs, and returns 1.

## 5. Repair the stub payloads that now carry unattributable items

Running the suite after requirement 4 will turn some existing tests red because their stub payloads contain a finding item with no attribution. Fix the **payload**, never the assertion — the spec calls this out explicitly as a payload change, not an assertion change.

The known one is `TestHarvestKeepsFindingWithoutAnyRuleId`. Change its report from

```
#### Must Fix (Critical)
- This finding has no rule ID at all but should still be kept.
```

to

```
#### Must Fix (Critical)
- **`src/x.py:4`** This finding has no rule ID at all but should still be kept.
```

Its three assertions stay exactly as they are: one finding, `rule_id is None`, `"no rule ID"` in the body. The test still asserts what it always asserted — an item citing no rule id is kept with `rule_id` null — and it now does so on an item that is attributable by path, which is the contract.

**The second known-red test is `TestRawOutputIsCachedVerbatim` (`bench/test_review.py:613`).** Its payload's finding item has no leading bold run and no rule marker, so after prompt 3 both `path` and `rule_id` are `None`, the new gate fires, `rc` becomes 1 and its `assertEqual(rc, 0)` fails. Repair the **payload** — change its Must Fix item to:

```
- **`agents/x.md:12`** sample finding.
```

All of its assertions stay exactly as they are. **Under no circumstances relax `assertEqual(rc, 0)`**: that assertion is the whole point of the test — the raw output is cached verbatim on a *successful* run — and turning it into `assertIn(rc, (0, 1))` or deleting it would hide the very regression this prompt introduces.

Run the full suite and repair any other **in-test literal payload** the same way: add a leading bold path reference of the form ``**`some/file.ext:NN`**`` to the item. Do not delete a test, do not relax an assertion, and do not add an opt-out to make a payload pass.

**This repair instruction is fenced to in-test literal payloads only.** If a test that reads a file from `bench/testdata/` goes red — in particular prompt 1's `result.unattributable == []` assertions over `capture-notes-block-h2.md`, `real-capture-report.md` or `capture-summary-trailer-h4.md` — that is **not** a payload to repair. It means the "only items inside a severity section are classified" rule is implemented wrong: content outside a severity section is being swept into `unattributable`, which would fail a PR on a review that correctly found nothing. Fix `harvest`. **Editing a fixture under `bench/testdata/` is forbidden** — all six are digest-pinned by spec AC2 and prompt 5 verifies them with `shasum -c`.

## 6. Update the AC5 count

Prompt 3 of this spec left `TestNumberedCaptureFindingsCarryAttribution` asserting `len(result.findings) == 7`. With classification in place the two `### Nice to Have (Optional)` bullets move out of `findings`, so change that assertion to `len(result.findings) == 5`. The five-tuple comparison for `result.findings[:5]` is unchanged. This tightens the assertion; do not replace it with an inequality.

## 7. Tests

**AC13 — the unattributable items in the real capture are reported as such.** `class TestNiceToHaveBulletsAreReportedUnattributable`, one test method that harvests `bench/testdata/capture-numbered-findings-h3.md` and asserts:

- `len(result.unattributable) == 2`;
- both entries have `section == "Nice to Have"`;
- the two bodies equal, verbatim, the fixture's two `### Nice to Have (Optional)` bullets with their `- ` marker removed and internal whitespace collapsed. Take the two strings from the fixture and confirm them against it before writing the test; they are:

  ```
  Manual Trivy apt-install (update/install/repo-key) duplicates the maintained `aquasecurity/setup-trivy` action — adds ~30-60s/run and maintenance surface with no caching/pinning.
  ```
  ```
  Commit subject `switch build backend to hatchling and add conventional changelog prefixes` is 73 chars (soft cap 50) — FYI only, not in the active rule set.
  ```

- **and** that the five Should Fix findings from AC5 are still present in `result.findings`, asserted by the same five `(path, line, rule_id)` tuples. This is the honest consequence of the governing rule on a genuine review: that PR fails loudly rather than contributing two body-only findings.

**AC11 — an unattributable item fails the PR loudly.** `class TestUnattributableItemFailsThePrLoudly`, one test method using `run_one_pr_with_payload` with the payload

```python
testsupport.review_report(
    should_fix="- an item with neither a file reference nor a rule tag, so it cannot be keyed."
)
```

Assert all of:

- the return code is non-zero;
- stderr contains the **spelled-out literal** `"UNATTRIBUTABLE FINDING"` — write that string in the test source; do **not** assert `run.UNATTRIBUTABLE_MARKER`, whose value the implementer chooses, which would make the assertion compare the implementation against itself and pass for any spelling;
- as its own assertion with its own message, `self.assertEqual(run.UNATTRIBUTABLE_MARKER, "UNATTRIBUTABLE FINDING")` — the marker is a frozen spec invariant (spec 005 AC11, AC16 and Constraints), not an implementation choice. An underscore variant such as `"UNATTRIBUTABLE_FINDING"` would otherwise satisfy every check in this prompt while silently violating spec AC11, prompt 5's `grep -cF` and operator AC20;
- the PR id `test#1`, the section name `Should Fix`, and the item's text verbatim;
- the results ledger gains **0** lines (handle the file not existing at all, as the existing gate tests do);
- under `run.reviews_root(cache_root)` — the temp cache root the test passed to the runner, never `bench/.cache/` — exactly **one** file exists, and it is the `<key>.stdout.txt` raw capture; `list(reviews.glob("*.json"))` has length **0**. Assert the `.json` count as its own assertion with its own message: it is the discriminator, and it is what proves the PR is retried rather than served from cache next run;
- a failure artifact exists under `run.failures_root(cache_root)` and its text contains the item's text;
- the captured stdout summary line reports `1 failed`. Capture stdout with `contextlib.redirect_stdout` alongside the existing stderr capture, or extend `run_one_pr_with_payload` to return it — if you extend the helper, update **all five existing call sites** (~1062, ~1101, ~1128, ~1152, ~1191) rather than duplicating it. Verify the count with `grep -n 'run_one_pr_with_payload' bench/test_review.py` before you start; missing one leaves the suite red for a reason unrelated to this prompt.

**AC12 — the loud failure is not a blanket rejection, and AC11's probe is live.** `class TestAttributedItemStillProducesARow`, one test method, the same runner invocation and the same review shape with the single item now headed by a bold reference:

```python
testsupport.review_report(
    should_fix="- **`src/x.py:4`** an item with a file reference and no rule tag."
)
```

Assert all of:

- the return code is `0`;
- the results ledger gains exactly **1** line, and that row's `findings[0]["path"] == "src/x.py"` and `findings[0]["line"] == 4`;
- the **same probe AC11 uses**, run here, finds **two** files under `run.reviews_root(cache_root)` — one `<key>.stdout.txt` and exactly **one** `<key>.json` row marker. State the expected counts as `2` and `1` in the assertion messages. The success path writes two files (the raw capture at step 5 and the row marker at step 8); an implementer who observes 2 where the test says 1 would "fix" the assertion and silently dissolve the AC11/AC12 pairing.

## 8. Failure handling

- The gate is fail-closed: every ambiguity about whether an item is a keyed finding resolves to rejection. A false rejection costs one operator decision and a re-run; a false acceptance writes an unmatchable measurement into an append-only ledger.
- The diagnosis reproduces the subprocess's own output and nothing else — no environment variables, no tokens, no credential material.
- Review output can be arbitrarily large: the item block passes through `rejection_excerpt`, so stderr stays bounded at `REJECTION_EXCERPT_BYTES` with the truncation marked.
- When **every** PR in a run trips the gate, the run produces zero rows and fails uniformly. That is the correct, visible outcome; do not add a threshold, a tolerance or a downgrade-to-warning path.
- `write_failure_artifact` already tolerates `None` and non-string streams via `stream_text`; do not add error handling around it.

</requirements>

<constraints>
- **Python 3 standard library only.** No third-party imports, no new top-level files outside `bench/`. Changes land only in `bench/run.py`, `bench/test_review.py` and — only if you extend a helper — `bench/testsupport.py`.
- **Do NOT add an opt-out.** No flag, no environment variable, no manifest field, no config knob that lets a run accept body-only findings or downgrade the rejection to a warning. An escape hatch on this Goal is the regression this spec exists to close.
- **Do NOT make the rejection, the marker literal or the excerpt bound configurable.** All are frozen invariants.
- **Do NOT change the `NOT A REVIEW` gate** — same required sections, same heading matching, same bounded excerpt, same position at step 4 ahead of the step-5 raw write. The new gate is a second, later gate that reuses the same no-row / no-row-marker / retry-next-run semantics.
- **Do NOT move the step-5 raw-stdout write.** It stays ahead of harvesting. The two rejection classes differ deliberately in what they leave behind: `NOT A REVIEW` leaves nothing under `reviews_root`, the new gate leaves the `<key>.stdout.txt` and writes no `<key>.json`.
- **Do NOT delete the raw capture on rejection.** The Failure Modes table promises it is re-harvestable after a fix without spending tokens again.
- **Never create, regenerate, overwrite or edit any file under `bench/testdata/`.** On a digest mismatch, stop and report failed.
- **`bench/testdata/sample-report.md` and `bench/testdata/real-capture-report.md` are byte-frozen** and must still harvest to their previously asserted results.
- **No test function may be deleted and no assertion relaxed.** Per-file assertion floors that must hold after this prompt: `grep -cE '^\s*(self\.assert|assert )' bench/test_config.py` ≥ 63, `bench/test_resolve.py` ≥ 46, `bench/test_review.py` ≥ 165. The suite's test count must stay strictly greater than 72.
- **Do NOT change `bench/prs.json`, `commands/pr-review.md`, or any rule, agent, command or doc that participates in a review.** If the loud-failure rule proves the review command must mandate an attribution on every finding, that is a separate spec.
- **Do NOT re-harvest or migrate rows and raw outputs already written.**
- **Harvested values are data, never paths.** No `path` or `rule_id` read out of review output is opened, stat-ed, joined onto a filesystem root, or passed to a subprocess.
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file. Every test must use its own `tempfile.TemporaryDirectory()` cache root — never `bench/.cache/`, which is gitignored and absent in a fresh clone, making a probe against it vacuous.
- Bench tests must not require network access, a real `claude` binary, or GitHub access.
- Do NOT edit `bench/README.md` or `CHANGELOG.md` in this prompt — prompt 5 of this spec owns both (spec 005 AC16/AC17). `docs/dod.md`'s "CHANGELOG.md has an entry under `## Unreleased`" criterion is deliberately deferred to prompt 5 and its absence here is **expected — do NOT report it as a blocker** and do NOT add an entry to satisfy it.
- Do NOT commit — dark-factory handles git.
</constraints>

<verification>
```
# Prompts 1-3 landed (precondition, not a new check)
grep -n 'class HarvestResult\|def list_item_body\|def extract_attribution' bench/run.py

# The frozen marker and the gate exist, in the right places
grep -nF 'UNATTRIBUTABLE_MARKER = "UNATTRIBUTABLE FINDING"' bench/run.py
grep -n 'def unattributable_report' bench/run.py
grep -n '# 4. Sanity gate\|# 5. Write raw stdout\|# 6. Harvest\|# 6a. Unattributable\|# 7. Build row\|# 8. Write cache marker' bench/run.py

# No opt-out was introduced
grep -niE 'allow.unattributable|skip.unattributable|--allow|accept_body_only|ignore_unattributable' bench/run.py ; echo "exit=$? (expect 1)"

# Fixtures untouched
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/capture-numbered-findings-h3.md
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/sample-report.md        # expect de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae
python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' bench/testdata/real-capture-report.md  # expect be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db

# AC13 — the real capture now splits five findings from two unattributable items
python3 - <<'EOF'
import sys, json, pathlib
sys.path.insert(0, 'bench')
import run as R
ids = R.load_rule_ids(pathlib.Path('.'))
r = R.harvest(pathlib.Path('bench/testdata/capture-numbered-findings-h3.md').read_text(), ids)
print('findings', len(r.findings), 'unattributable', len(r.unattributable))
for u in r.unattributable:
    print('   ', json.dumps(u))
EOF

# Assertion floors (AC15)
grep -cE '^\s*(self\.assert|assert )' bench/test_config.py   # expect >= 63
grep -cE '^\s*(self\.assert|assert )' bench/test_resolve.py  # expect >= 46
grep -cE '^\s*(self\.assert|assert )' bench/test_review.py   # expect >= 165

# Full suite and repository gate
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -50
make precommit
```

Expected: the marker is declared with the exact literal `UNATTRIBUTABLE_MARKER = "UNATTRIBUTABLE FINDING"` (a name-only match is not sufficient — the spelling is the invariant), `unattributable_report` is present, and the step comments appear in the order 4, 5, 6, 6a, 7, 8; the opt-out grep exits 1; the three digests are unchanged; the replay prints `findings 5 unattributable 2` with both entries carrying `"section": "Nice to Have"`; the unittest run reports `OK` with `Ran N tests`, `N > 72`, and lists the unattributable-capture, loud-failure and attributed-row tests by name; `make precommit` exits 0.
</verification>
