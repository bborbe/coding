---
status: completed
spec: [014-pr-review-coverage-block]
summary: Added the mandatory Review Coverage section to /coding:pr-review's Step 5 report and allowlisted the SHA read
execution_id: coding-coverage-block-exec-056-spec-014-review-coverage-contract
dark-factory-version: v0.198.7
created: "2026-10-18T13:41:49Z"
queued: "2026-10-18T14:11:25Z"
started: "2026-10-18T14:12:47Z"
completed: "2026-10-18T14:17:43Z"
branch: dark-factory/pr-review-coverage-block
---

# Add the review coverage contract to the PR review report

<summary>
- Every `/coding:pr-review` report now ends with a fixed review-coverage section
- Each of the three review tiers gets one row saying whether it ran, failed or was skipped, how many findings it produced and why
- The reviewed commit is printed as a full commit id, and an unreadable commit is reported as a failure instead of a made-up value
- The verdict line reads clean only when no tier failed; a skipped tier never makes a report not-clean
- A tier that was needed but could not complete is reported as failed, naming the tier and a short reason
- The finding counts are tallied from the report that was already produced, never re-run or estimated
- The section is emitted last, in short, selector and full mode, with or without the security flag
- Nothing about the findings, the severities, the existing judgment-tier line or the security pipeline changes
</summary>

<objective>
Add a mandatory `#### Review Coverage` section to the end of `/coding:pr-review`'s Step 5 report, so a reader can tell, per tier, what actually ran and at which commit. This is prompt **1 of 3** for spec 014 and the only prompt that writes `commands/pr-review.md`.
</objective>

<context>
Read fully before editing:

- `commands/pr-review.md` in full (451 lines). The region this prompt edits is the `### Step 5: Consolidated Report` section, which currently runs from the heading `### Step 5: Consolidated Report` to just before `### Step 6: Next Steps Recommendation`. Within it, the last subsection is `#### Security Model (under \`--security\` only)`. The new block goes after that subsection and before `### Step 6`.
- `rules/index.json` — confirm the three `enforcement_type` values the finding-attribution rule names: `mechanical`, `script` and `judgment`. There are 194 entries today; the values are exactly those three.
- `scripts/rule-checks.sh` — read `self_containment_exempt` (the six exempt paths) and the four self-containment marker patterns (`no-home-dir-paths`, `no-requirement-ids`, `no-planning-doc-refs`, `no-revision-meta`). The constraints below reproduce their union; do not retype it from memory.
- `scripts/acceptance.sh` — read the `=== 5/6 Selector mode contracts ===` section and the `=== Summary ===` tail. This prompt does not edit the file, but prompt 2 will add a coverage-block assertion against the literals this prompt writes, so every required literal below must be present verbatim.
- `CLAUDE.md` — repo content rules (generic examples only, doc↔agent alignment).

**Verified repo facts this prompt relies on**

- The Step 5 region is extracted exactly by `sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md`. It is 58 lines today and contains zero occurrences of `#### Review Coverage`, `Result: clean` and `Result: not clean`.
- The three severity headings are `#### Must Fix (Critical)`, `#### Should Fix (Important)` and `#### Nice to Have (Optional)`; each occurs once. The `Judgment tier:` line occurs once. This prompt adds the block without touching any of them.
- The command file already contains one bare `git rev-parse HEAD` in the Step 0a-pre `ALREADY_AT_HEAD` check. The acceptance criterion for the SHA source therefore greps the full `cd <REVIEW_DIR> && git rev-parse HEAD` form, which is new.
- `commands/local-review.md` and `commands/code-review.md` are out of scope and must not receive the block.
- This container's `.git` is masked — `.dark-factory.log` records `hideGit=true hideGitSource=arg` — so no `git` command can run in verification.
</context>

<requirements>

### 1. Snapshot before editing

Take the baseline first, so the added-lines marker sweep and the scope-lock comparison in `<verification>` have something to compare against:

```bash
cp commands/pr-review.md /tmp/pr-review-before.md
find commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security -type f -exec sha256sum {} + | sort > /tmp/scope-before.txt
```

This is the git-free equivalent of reading the file at the target branch. `/tmp` does not persist across prompts, so both comparisons must happen inside this run.

### 2. Insert the `#### Review Coverage` subsection

Insert the following subsection at the end of Step 5, after the `#### Security Model (under \`--security\` only)` subsection and immediately before `### Step 6: Next Steps Recommendation`. The prose is plain markdown; only the example block inside it is fenced.

````markdown
#### Review Coverage

Emit this section as the last section of the report. Emit it in every mode (short, selector and full) and with or without --security.

This section reports what this invocation already did. It never re-runs, re-derives or estimates a tier.

```markdown
#### Review Coverage

| Tier | Status | Findings | Reason |
|---|---|---|---|
| deterministic | ran | 3 | — |
| judgment | ran | 1 | — |
| security | skipped | 0 | --security not requested |

Reviewed commit: 0123456789abcdef0123456789abcdef01234567
Result: clean
```

The emitted block is unfenced. The fenced example above exists only in this command file; a fenced emitted heading would be invisible to the bench's report reader.

Status meanings:

- ran means the tier's procedure completed. A legitimate zero-findings result — including the selector short-circuit `selector clean — no adjudication needed` — is `ran` with `0`, never `failed`.
- failed means the tier was required and could not complete. The deterministic tier fails when `ast-grep`/`sg` is missing, the runner exits non-zero, a full-mode `make precommit` cannot be executed, or the reviewed commit cannot be read. The judgment tier fails when the selector guide is missing, an adjudicator dispatch fails or returns empty, or a full-mode owner dispatch errors. The security tier fails when model derivation, the verifier gate or the toolchain scan fails.
- skipped means the invocation did not require the tier. The cases are short mode (deterministic and judgment), the Step 4 early exit when no rule-relevant file changed (deterministic and judgment), and `--security` absent (security). A skip is never a failure, and a failure is never written as a skip.
- The selector short-circuit is ran with 0, not failed.

Tier requirements for this invocation:

- deterministic — `skipped` with reason `short mode` in short mode, and `skipped` with reason `no rule-relevant files changed` on the Step 4 early exit. Otherwise `ran`, or `failed` per the failure cases above.
- judgment — `skipped` with reason `short mode` in short mode, and `skipped` with reason `no rule-relevant files changed` on the Step 4 early exit. Otherwise `ran` (including the selector short-circuit with `0`), or `failed` per the failure cases above.
- security — `skipped` with reason exactly `--security not requested` when the flag is absent. When the flag is present, the security pipeline runs in every mode and the row is `ran` or `failed`.

Findings are counted per tier, from what the report already emitted:

1. A finding emitted by the security pipeline — a security rule, an invariant or a toolchain finding — counts in `security`.
2. Otherwise a finding whose `rule_id` resolves in `rules/index.json` to `enforcement_type: mechanical` or `script` counts in `deterministic`.
3. Otherwise a `judgment` rule counts in `judgment`.
4. A finding with no `rule_id` counts in `judgment`, so nothing falls through the attribution.

The three cells sum to the report's total finding count: a finding is never counted twice and none is silently dropped. A tier that did not run and has no attributed finding carries `0`; its `Status` says why. A finding attributed to a skipped tier — for example a Step 3 `make precommit` failure with no `rule_id`, which attributes to `judgment` in short mode — is still counted in that tier's `Findings` cell while the row keeps `skipped` and its `Reason`; the sum rule wins over the `0` default. The count is a tally of this invocation's report, never a re-run and never an estimate.

The `Reason` cell is `—` when the tier ran, and a short reason when it failed or was skipped. A reason quotes at most one line of tool output, truncated; it is never a full stderr dump.

Result: clean if and only if no tier is failed. Result: not clean when any tier is failed, naming each failed tier and its reason on the same line. For example, `Result: not clean — deterministic failed: ast-grep not in PATH`. A skipped tier never makes a result not-clean.

The reviewed commit is the value of `cd <REVIEW_DIR> && git rev-parse HEAD` for the same `REVIEW_DIR` the review used, so the `ALREADY_AT_HEAD` short-circuit needs no special case. Emit it as the full 40-character lowercase hex string; never abbreviate or reconstruct it. If the command fails, do not fabricate a SHA: the `Reviewed commit:` line states `Reviewed commit: unavailable — <short reason>`, the deterministic row is `failed` with the same short reason, and an unreadable SHA produces Result: not clean.
````

### 2b. Allowlist the SHA read

Add `Bash(git rev-parse:*)` to the `allowed-tools` line in `commands/pr-review.md`'s frontmatter, so the `cd <REVIEW_DIR> && git rev-parse HEAD` read does not prompt for permission. The line becomes:

`allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+), Bash(git fetch:+), Bash(git worktree:+), Bash(git branch:+), Bash(git rev-parse:*), Bash(rm -rf:+), Bash(gh pr view:+), Bash(cat:+)`

Do not change any other frontmatter field.

### 3. Preserve every existing Step 5 line

Do not rewrite, reorder or delete anything else in Step 5. In particular:

- the `Judgment tier:` line stays exactly as it is;
- the `Intent:` line stays exactly as it is;
- the `#### Must Fix (Critical)`, `#### Should Fix (Important)` and `#### Nice to Have (Optional)` sections stay exactly as they are;
- the `#### Selector Mode: Classify Traceability (selector mode only)` section stays exactly as it is;
- the `#### Security Findings (under \`--security\` only)` and `#### Security Model (under \`--security\` only)` sections stay exactly as they are.

The new block is additive report text. It adds no finding, drops no finding, changes no severity and changes no traceability content.

### 4. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation. Walk the exact-literal list below against the Step 5 region and confirm each one is present verbatim:

- `#### Review Coverage`
- `| Tier | Status | Findings | Reason |`
- `Reviewed commit:`
- `Result: clean`
- `Result: not clean`
- `Emit this section as the last section of the report.`
- `in every mode (short, selector and full) and with or without --security.`
- `ran means the tier's procedure completed.`
- `failed means the tier was required and could not complete.`
- `skipped means the invocation did not require the tier.`
- `The selector short-circuit is ran with 0, not failed.`
- `Result: clean if and only if no tier is failed.`
- `Result: not clean when any tier is failed, naming each failed tier and its reason on the same line.`
- `cd <REVIEW_DIR> && git rev-parse HEAD`
- `full 40-character lowercase hex`
- `an unreadable SHA produces Result: not clean.`

Do not report success if any check failed.
</requirements>

<constraints>
- **Scope:** this prompt writes exactly one file — `commands/pr-review.md`. Do NOT modify `commands/local-review.md`, `commands/code-review.md`, `scripts/*`, `rules/*`, `docs/*`, `agents/*`, `scenarios/*`, `CHANGELOG.md`, `README.md`, `llms.txt`, `CLAUDE.md`, `.claude-plugin/*`, `.maintainer.yaml` or `docs/security/**`.
- **Report-only.** The change adds no rule, no index entry, no runner change, no verifier change and no bot change. The finding set, the severity mapping, the `Judgment tier:` line, the traceability section, the security pipeline, the `--security` flag and the security model/verifier procedure are unchanged.
- **One block, one shape (frozen).** The heading is `#### Review Coverage`; the table header is `| Tier | Status | Findings | Reason |`; the tier tokens are exactly `deterministic`, `judgment`, `security`; the status tokens are exactly `ran`, `failed`, `skipped`; the SHA line begins `Reviewed commit: `; the verdict line begins `Result: ` and continues `clean` or `not clean`. Prompt 2 asserts these literals, so a reworded heading is a test failure rather than a silent drift.
- **Exact sentences are plain text.** The four status sentences and the two verdict sentences are asserted with `grep -cF` against the command file. Write each one exactly as given, with no bold, backticks or other markdown between the status token and the word `means`, and with the sentence-final period present. In particular, `ran means the tier's procedure completed.` must not become `**ran** means ...` or `` `ran` means ... ``.
- **Emitted last.** The block is the final section of the consolidated report. The bench's report parser treats any heading as the end of the preceding findings section, so a block placed mid-report would truncate a findings section it followed; placing it last is what keeps the bench's harvest unchanged.
- **Emitted unfenced.** The example in the command file is fenced; the block the command tells the reviewer to emit is not fenced.
- **No fabricated values.** A tier result is written from what happened in the invocation. A tier whose result is unknown is `failed` with the reason, never `ran` with a guessed count. Never re-run or re-derive a tier to produce the block.
- **Reason strings are bounded.** A reason quotes at most one line of tool output, truncated. It is never a full stderr dump and never a multi-line paste.
- **Full 40-character SHA.** The value comes from `cd <REVIEW_DIR> && git rev-parse HEAD` and is emitted verbatim. A SHA-256 repository is out of scope.
- **No config knob, no opt-out flag, no mode token, no new subagent dispatch, no new scenario file.**
- **Generic content only.** Any example uses User, Order, Product, Customer — never a trading or project-specific domain.
- **Marker hygiene on every added line.** `commands/pr-review.md` is not an exempt path, so no added line may carry a home-directory path, a requirement id, a planning-directory reference, or revision/sign-off meta. The literal pattern (copied from `scripts/rule-checks.sh`, not retyped from memory):

  ```
  (^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
  ```

  Copy this pattern without the fence's leading indentation — a copy that carries the two leading spaces no longer matches a home-directory path. The verification block below also carries the pattern inline.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit=true hideGitSource=arg`), so a bare `git` call fails with `fatal: not a git repository`. The daemon commits on completion. The `<REVIEW_DIR>` text in the command file is a documented placeholder, not a command this prompt runs.
- **The `CHANGELOG.md` `## Unreleased` entry is prompt 3's scope** — this prompt is forbidden from touching `CHANGELOG.md`. Do not report the changelog entry as a blocker; it is a scope boundary, not an unmet criterion.
- **Cross-prompt boundary:** prompt 2 asserts the five literals `#### Review Coverage`, `| Tier | Status | Findings | Reason |`, `Reviewed commit:`, `Result: clean` and `Result: not clean` inside the Step 5 region. All five must be present at the end of this run, or prompt 2 cannot pass. If any is missing, report `Status: failed` naming it.
</constraints>

<verification>
All commands run from the repo root and are container-executable. This container has **no git** — no check below uses it. The two snapshots in requirement 1 must have been taken **before** the edit.

```bash
# --- extract the Step 5 region once; every literal check is scoped to it ---
sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md > /tmp/step5.txt
wc -l < /tmp/step5.txt                                                          # informational: 58 before, more after

# --- AC1: the block, the table and the two verdict forms ---
grep -cF '#### Review Coverage' /tmp/step5.txt                                  # expect: >= 1
grep -cF '| Tier | Status | Findings | Reason |' /tmp/step5.txt                  # expect: >= 1
grep -cE '^\| deterministic \| (ran|failed|skipped) \|' /tmp/step5.txt           # expect: >= 1
grep -cE '^\| judgment \| (ran|failed|skipped) \|' /tmp/step5.txt                # expect: >= 1
grep -cE '^\| security \| (ran|failed|skipped) \|' /tmp/step5.txt                # expect: >= 1
grep -cF 'Reviewed commit:' /tmp/step5.txt                                      # expect: >= 1
grep -cF 'Result: clean' /tmp/step5.txt                                         # expect: >= 1
grep -cF 'Result: not clean' /tmp/step5.txt                                     # expect: >= 1

# --- AC2: last section, every mode ---
grep -cF 'Emit this section as the last section of the report.' /tmp/step5.txt   # expect: >= 1
grep -cF 'in every mode (short, selector and full) and with or without --security.' /tmp/step5.txt   # expect: >= 1

# --- AC3: the three statuses are defined, not inferred ---
grep -cF "ran means the tier's procedure completed." /tmp/step5.txt              # expect: >= 1
grep -cF "failed means the tier was required and could not complete." /tmp/step5.txt   # expect: >= 1
grep -cF 'skipped means the invocation did not require the tier.' /tmp/step5.txt      # expect: >= 1
grep -cF 'The selector short-circuit is ran with 0, not failed.' /tmp/step5.txt       # expect: >= 1

# --- AC4: the Result rule is pinned ---
grep -cF 'Result: clean if and only if no tier is failed.' /tmp/step5.txt        # expect: >= 1
grep -cF 'Result: not clean when any tier is failed, naming each failed tier and its reason on the same line.' /tmp/step5.txt   # expect: >= 1

# --- AC5: the SHA is the reviewed commit, full length, fail-closed ---
grep -cF 'cd <REVIEW_DIR> && git rev-parse HEAD' /tmp/step5.txt                  # expect: >= 1
grep -cF 'full 40-character lowercase hex' /tmp/step5.txt                        # expect: >= 1
grep -cF 'an unreadable SHA produces Result: not clean.' /tmp/step5.txt          # expect: >= 1
grep -cF 'Bash(git rev-parse:*)' commands/pr-review.md                            # expect: 1

# --- placement: after Security Model, before Step 6, and only in pr-review ---
awk '/^#### Security Model/{m=NR} /^#### Review Coverage/{c=NR} /^### Step 6:/{e=NR} END { if (m && c && e && c>m && c<e) print "OK: block follows Security Model and precedes Step 6"; else print "FAIL: block placement" }' commands/pr-review.md
if grep -q '#### Review Coverage' commands/local-review.md commands/code-review.md; then
  echo "FAIL: the block was copied into a sibling command"
else
  echo "OK: sibling commands untouched"
fi

# the emitted heading must be outside any fence (a fenced heading is invisible to the report reader)
if grep -q '^````' commands/pr-review.md; then
  echo "FAIL: the outer prompt fence was copied into the command file — the block is fenced"
else
  echo "OK: no four-backtick fence in the command file"
fi

# --- the existing Step 5 report contract is intact ---
grep -c 'Judgment tier:' commands/pr-review.md                                   # expect: 1
grep -c '^#### Must Fix (Critical)' commands/pr-review.md                        # expect: 1
grep -c '^#### Should Fix (Important)' commands/pr-review.md                     # expect: 1
grep -c '^#### Nice to Have (Optional)' commands/pr-review.md                    # expect: 1
grep -c '^#### Security Model (under `--security` only)' commands/pr-review.md   # expect: 1

# --- marker hygiene on the lines this prompt added (snapshot-based; no git) ---
diff -u /tmp/pr-review-before.md commands/pr-review.md > /tmp/pr-review.diff || true
grep '^+' /tmp/pr-review.diff | grep -v '^+++' > /tmp/pr-review-added.txt
added_count=$(wc -l < /tmp/pr-review-added.txt)
if [ "$added_count" -eq 0 ]; then
  echo "FAIL: no added lines — the baseline snapshot was taken after the edit"
else
  echo "OK: $added_count added lines"
fi
if grep -qE '(^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/pr-review-added.txt; then
  echo "FAIL: a marker literal was added to commands/pr-review.md"
else
  echo "OK: added lines are marker-free"
fi

# --- scope lock: the paths this prompt must not touch are unchanged ---
find commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security -type f -exec sha256sum {} + | sort > /tmp/scope-after.txt
if diff -q /tmp/scope-before.txt /tmp/scope-after.txt > /dev/null 2>&1; then
  echo "OK: scope-lock paths unchanged"
else
  echo "FAIL: a scope-lock path changed"
  diff /tmp/scope-before.txt /tmp/scope-after.txt
fi

# --- the real in-container gate (precommit minus the git-dependent changelog-fold target) ---
for bin in jq ast-grep python3; do
  command -v "$bin" >/dev/null || echo "FAIL: $bin is not in the container PATH — check-acceptance/check-rule-tests cannot run"
done
make check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test   # expect: exit 0
```

`make precommit` adds `check-changelog-fold` on top of the seven targets above. That target shells out to `git rev-parse --git-dir` and dies with `not a git repository` while `.git` is masked here, so it cannot pass inside this container and is deliberately excluded. The full `make precommit` is an operator-rung check on the host — do not attempt it in this container. Do not report success on the checks above if any of them exited non-zero.
</verification>

<notes>
<!-- OPEN QUESTION (reviewer): the spec does not pin the exact reason string for the Step 4 early exit. This prompt uses `no rule-relevant files changed`, mirroring the existing report sentence `Step 4 skipped: no rule-relevant files changed`. If the operator grep in AC15 should see the longer `Step 4 skipped: ...` form instead, change the literal in requirement 2 and in prompt 2's tier-requirements prose. -->
<!-- RESOLVED: requirement 2 pins the failure form `Reviewed commit: unavailable — <short reason>` and marks the deterministic row `failed`, so the unreadable-SHA case reaches not-clean through the verdict rule. -->
- **Why the status sentences are not bolded.** `scripts/acceptance.sh` and the acceptance criteria use `grep -cF` on plain sentences such as `ran means the tier's procedure completed.` Markdown emphasis between `ran` and `means` would break the fixed-string match, so the four status sentences and the two verdict sentences are written as plain text.
- **Why the block is scoped to Step 5 in the checks.** A whole-file grep is satisfied by a sentence appended after Step 7, so it cannot test placement. The verification block extracts the Step 5 region once and checks every literal inside it.
- **Why no scenario file.** The contract is text-assertable here and behaviourally exercisable by the operator fixture runs in the spec's operator rung. The existing scenarios 005 and 006 cover the selector short-circuit and the findings path, neither of which this change alters.
</notes>
