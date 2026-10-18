---
status: prompted
approved: "2026-10-18T13:32:33Z"
generating: "2026-10-18T13:37:16Z"
prompted: "2026-10-18T13:55:57Z"
branch: dark-factory/pr-review-coverage-block
---

## Summary

- Every report from the PR-review command ends with a fixed coverage section: one row per review tier (deterministic, judgment, security) stating whether it ran, failed or was skipped, how many findings it produced and why, plus the full commit SHA that was reviewed and a single clean / not-clean verdict line.
- A tier that was needed and could not complete — the mechanical toolchain absent, the selector guide absent, the adjudicator dispatch failed or empty, a security step failed — reads failed and forces the not-clean verdict, naming the tier. A tier the invocation did not need (short mode, no rule-relevant files, security not requested) reads skipped with its reason and does not force not-clean.
- The section is machine-checkable: a fixed heading, exactly three tier rows, an anchored verdict line and an anchored commit line, so one grep distinguishes clean from not clean and extracts the SHA.
- Report-only: no rule, no finding set, no severity and no verdict changes. The bot wrapper is unchanged — it parses the JSON verdict block and its blocking fields, never the markdown headings or the verdict line.
- The acceptance suite locks the contract so a later edit that drops the section fails the precommit gate.

## Problem

`/coding:pr-review` emits a markdown report whose only coverage statement is the single `Judgment tier: selector ran | skipped — <reason> | n/a — short mode` line. There is no statement for the deterministic or security tiers and no reviewed SHA in the report. A tier that failed, crashed, or was never invoked is therefore indistinguishable in the report from a tier that ran and found nothing: silence reads as a pass.

That is the exact failure the [[Five-Lens Review Gate]] names — a lens that fails, returns nothing, or cannot be dispatched is an open finding, never clean — and it is the gap this task's parent goal records as SC4. It also has a concrete operational cost: the operator's PR rules allow a local `/coding:pr-review` recorded on the PR to clear an oversized PR, but a report with no per-tier coverage and no pinned SHA cannot serve as that record, because a reader cannot tell what was actually checked or at which commit. The one place a commit-ish appears today is the Security Model section under `--security`, which records `derived_from.head` — a commit-ish, not a guaranteed full-length SHA, and absent in every other mode. The block makes the reviewed SHA uniform, full-length and present in every mode.

The Five-Lens gate's own `| Lens | Ran | Findings | Fixed |` table plus `Result:` line is the shape worth taking. Its weakness #7 — no SHA in the block, so targeted re-runs cover different commits invisibly — is the thing not to copy: this block pins the full 40-character SHA.

## Goal

Every `/coding:pr-review` report — in short, selector and full mode, with and without `--security` — ends with a `#### Review Coverage` block that states, per tier, whether it ran, failed or was skipped, how many findings it produced, and the full 40-character SHA of the reviewed commit, followed by a `Result:` line that reads `clean` only when no tier failed.

A run on a fixture where the deterministic tier cannot start prints `Result: not clean — deterministic failed: …` and the deterministic row reads `failed`; the same fixture with the toolchain present prints `Result: clean`. The finding set, the severities and every bot verdict for existing inputs are unchanged.

## Non-goals

- Do NOT add the block to `/coding:local-review` or `/coding:code-review` — their calling contexts differ and the task scopes the change to `/coding:pr-review`.
- Do NOT change any rule, `rules/index.json`, `scripts/rule-checks.sh`, `scripts/ast-grep-runner.sh` or `scripts/validate-citations.sh`.
- Do NOT change the finding set, the severity mapping, the `Judgment tier:` line, the traceability section, or the bot's verdict contract.
- Do NOT change the security pipeline, the `--security` flag or the security model/verifier procedure.
- Do NOT add a config knob, an opt-out flag, a mode token, or a new subagent dispatch.
- Do NOT add a new scenario file.
- Do NOT re-run or re-derive any tier to produce the block — the block reports what already happened in this invocation.

## Assumptions

- **The reviewed repository uses SHA-1.** `git rev-parse HEAD` emits 40 lowercase hex characters. A SHA-256 repository would emit 64 and is out of scope; the acceptance assertion and the operator grep are written against the 40-character form.
- **The bench's report parser treats any heading as the end of the open findings section** (`bench/run.py` `iter_report_lines`). A coverage heading placed last therefore changes no harvest; placed mid-report it would truncate the findings section above it.
- **The reviewer bot derives its verdict from the JSON verdict block's `blocking` fields**, not from markdown headings or the `Result:` line. The block is inert to it.
- **The artifact under test is the released plugin**, not the worktree. AC9 carries the Post-Deploy marker and the freshness check; AC10–AC15 run against AC9's deployed artifact. The plugin install is the single deployed environment, so Rung-2 is the correct rung for a tool release with no separate dev/prod stage.
- **The `.in_use` load path is the most recently loaded session's.** When concurrent sessions run different plugin versions, the verifying session confirms its own pid's load path rather than the newest one.
- **The SC3 post-change bench run is the baseline.** It is recorded on the vault page [[PR Review Bench]] and in the SC3 task's `# Progress` after the in-flight re-run completes; the pre-v0.60.0 `98ff1caa` row is not the baseline for this change.

## Acceptance Criteria

**Scenario coverage: NO new scenario file.** The contract is text-assertable in `scripts/acceptance.sh` (the block's literals) and behaviorally exercisable by the operator fixture runs in AC9–AC11. The existing scenarios 005 and 006 assert the selector short-circuit and the findings path, neither of which this change alters, so a new scenario would add a walk without adding signal.

All container-executable greps below are scoped to the Step 5 region, never the whole file — `sed -n '/^### Step 5:/,/^### Step 6:/p' commands/pr-review.md` is the region, and a match outside it does not count. A whole-file grep is satisfied by a sentence appended after Step 7, so it cannot test placement.

- [ ] **AC1 — The command defines the block contract inside Step 5:** within the Step 5 region, `grep -cF '#### Review Coverage'` returns ≥1; `grep -cF '| Tier | Status | Findings | Reason |'` returns ≥1; each tier template row matches — `grep -cE '^\| deterministic \| (ran|failed|skipped) \|'`, `grep -cE '^\| judgment \| (ran|failed|skipped) \|'` and `grep -cE '^\| security \| (ran|failed|skipped) \|'` each return ≥1; `grep -cF 'Reviewed commit:'` returns ≥1; `grep -cF 'Result: clean'` returns ≥1; `grep -cF 'Result: not clean'` returns ≥1. Evidence: the seven counts, each produced from the Step 5 region pipeline.
The exact-sentence greps below are `grep -cF` literals, matched verbatim with no markdown escapes: the sentences are plain ASCII in the command file, so the implementation must include each one exactly as written here.

- [ ] **AC2 — The block is the final report section and mode-independent:** within the Step 5 region, `grep -cF 'Emit this section as the last section of the report.'` returns ≥1 and `grep -cF 'in every mode (short, selector and full) and with or without --security.'` returns ≥1. Evidence: the two counts plus the quoted sentences.
- [ ] **AC3 — The three tier statuses are defined, not inferred:** within the Step 5 region, `grep -cF "ran means the tier's procedure completed."` returns ≥1; `grep -cF "failed means the tier was required and could not complete."` returns ≥1; `grep -cF 'skipped means the invocation did not require the tier.'` returns ≥1; `grep -cF 'The selector short-circuit is ran with 0, not failed.'` returns ≥1. Evidence: the four counts plus the quoted sentences.
- [ ] **AC4 — The `Result:` rule is pinned:** within the Step 5 region, `grep -cF 'Result: clean if and only if no tier is failed.'` returns ≥1 and `grep -cF 'Result: not clean when any tier is failed, naming each failed tier and its reason on the same line.'` returns ≥1. Evidence: the two counts plus the quoted sentences.
- [ ] **AC5 — The SHA is the reviewed commit, full length, fail-closed:** within the Step 5 region, `grep -cF 'cd <REVIEW_DIR> && git rev-parse HEAD'` returns ≥1; `grep -cF 'full 40-character lowercase hex'` returns ≥1; `grep -cF 'an unreadable SHA produces Result: not clean.'` returns ≥1. Evidence: the three counts plus the quoted sentences. A bare `rev-parse HEAD` count cannot carry this — the file already contains one at the `ALREADY_AT_HEAD` check.
- [ ] **AC6 — The acceptance lock exists and can fail:** `scripts/acceptance.sh` gains a coverage-block assertion that hardcodes the literals `#### Review Coverage`, `| Tier | Status | Findings | Reason |`, `Reviewed commit:`, `Result: clean` and `Result: not clean` (never derived from the run's own output); `make check-acceptance` exits 0 on the change; in a scratch copy of the repo with the `#### Review Coverage` line removed from `commands/pr-review.md`, `make check-acceptance` exits non-zero. Evidence: both exit codes, the second run made in a scratch copy.
- [ ] **AC7 — Scope lock (negative):** `git diff --stat origin/master...HEAD -- commands/local-review.md commands/code-review.md rules scripts/rule-checks.sh scripts/ast-grep-runner.sh scripts/validate-citations.sh .maintainer.yaml docs/security` prints nothing; `grep -c '#### Review Coverage' commands/local-review.md` and `grep -c '#### Review Coverage' commands/code-review.md` each return 0. Evidence: the empty diff and the two zero counts.
- [ ] **AC8 — Precommit green, CHANGELOG entry present, no marker literals added outside the exempt paths (negative):** `make precommit` exits 0; `awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'` returns ≥1; the self-containment marker sweep over added lines outside `specs/` and `prompts/` returns 0 — `git diff origin/master...HEAD --unified=0 -- . ':(exclude)specs' ':(exclude)prompts' | grep -cE '^\+.*((^|[^A-Za-z0-9])~/[A-Za-z0-9._-]|/(Users|home)/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change)'`. Evidence: the exit code, the CHANGELOG count and the zero marker count.
- [ ] **Post-Deploy (Rung-2):** **AC9 — A clean fixture emits the block with a pinned SHA (operator-executable — needs the released plugin):** from a session loaded after the deploy, run `/coding:pr-review` over a clean fixture branch. The report ends with `#### Review Coverage`, carries exactly three tier rows, prints `Result: clean`, and prints `Reviewed commit: <40 hex>` whose value equals `git rev-parse HEAD` of the reviewed commit. Evidence: the pasted block plus `grep -E '^Reviewed commit: [0-9a-f]{40}$'` and a comparison against the fixture's `git rev-parse HEAD`.
  - `deploy_check:` `v=$(ls -dt ~/.claude/plugins/cache/coding/coding/*/.in_use/* 2>/dev/null | head -1 | sed -E 's#.*/coding/coding/([^/]+)/\.in_use/.*#\1#'); test -n "$v" && printf '%s\n' "$v"`
  - `deploy_target:` `$(git tag --contains $(git rev-parse HEAD) --sort=-v:refname | head -1 | sed 's/^v//')`
- [ ] **AC10 — A failed tier forces not-clean and names the tier (operator-executable — runs against AC9's deployed artifact):** run the same clean fixture with one tier unable to start — the deterministic tier with both `ast-grep` and `sg` removed from `PATH`, then the judgment tier with the selector guide renamed aside at **both** paths the command resolves (`$CLAUDE_PLUGIN_ROOT/docs/selector-mode-guide.md` and `$CLAUDE_CONFIG_DIR/plugins/marketplaces/coding/docs/selector-mode-guide.md`), so neither `GUIDE_OK` path exists. Each run prints `Result: not clean` naming the failed tier, and that tier's row reads `failed`. With the toolchain and guide restored, the same fixture prints `Result: clean`. Evidence: the three report bodies, grepped.
- [ ] **AC11 — One grep distinguishes clean from not clean and extracts the SHA (operator-executable — runs against AC9's deployed artifact):** over each pasted block, `grep -qE '^Result: clean$'` exits 0 only for the clean block, `grep -qE '^Result: not clean\b'` exits 0 only for the not-clean block, and `grep -oE '^Reviewed commit: [0-9a-f]{40}'` extracts the SHA from both. Evidence: the exit codes and the extracted values.
- [ ] **AC12 — The bot wrapper is unchanged and confirmed not to read the block (operator-executable — runs against AC9's deployed artifact):** read `pkg/prompts/execution.go` (`verdictTranslationFooter` and `funnelFailedSteerTemplate`) and `pkg/verdict.go` (`ParseVerdict`, `HasBlockingFinding`) in `bborbe/github-pr-review-agent` (local checkout `~/Documents/workspaces/github-pr-review-agent`); confirm the verdict is derived from the JSON verdict block's `blocking` fields and the fail-closed funnel steer, never from the markdown headings or the `Result:` line; `grep -rn 'Review Coverage\|Result: clean\|Result: not clean' pkg/` in that repo returns nothing. Record the read and both greps in `# Progress`. Evidence: the quoted mapping and the empty grep.
- [ ] **AC13 — No recall loss against the SC3 baseline (operator-executable — runs against AC9's deployed artifact):** before running the post-change bench, quote SC3's post-change baseline into this task's `# Progress` — the recall figure, config hash, `prs_version` and complete (non-partial) coverage from the run recorded on [[PR Review Bench]] and in the SC3 task's `# Progress`. The pre-v0.60.0 `98ff1caa` row is **not** the baseline. Then re-run the bench at the same pin/model/effort/mode and `prs_version`. The post-change bench report's `coding version:` line equals the version AC9's `deploy_target` resolved — a stale plugin would otherwise reproduce the baseline's recall and false-pass. Post-change recall is at least the baseline; a drop of one or more golden hits is treated as a defect — repeat the run once to distinguish nondeterminism from a real regression, and a repeated drop blocks the merge until explained in `# Progress`. Both figures are recorded in `# Progress`. Evidence: the post-change report page under `bench/reports/<config_hash>.md`, the quoted baseline entry, and both figures in `# Progress`.
- [ ] **AC14 — The per-tier counts are real, not hardcoded zeros (operator-executable — runs against AC9's deployed artifact):** run `/coding:pr-review` over a fixture that produces at least one deterministic and one judgment finding — scenario 006's perpetual fixture PR (`bborbe/maintainer#2`), or a bench PR with known findings. The `deterministic` and `judgment` cells carry the counts of the report's findings attributed to those tiers, and the three cells sum to the report's total finding count. A block whose counts are all `0` on a findings-bearing report fails. Evidence: the pasted block plus the report's finding bullets counted per tier.
- [ ] **AC15 — A skipped tier carries its reason, never a bare dash (operator-executable — runs against AC9's deployed artifact):** on a selector-mode run without `--security`, the security row reads `skipped` and its `Reason` cell is exactly `--security not requested`. On a short-mode run, the deterministic and judgment rows read `skipped` with the exact reason `short mode`. Evidence: the pasted blocks from both runs.

## Verification

### Container-executable (runs inside the dark-factory prompt container)

- `make check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test` — exits 0. `make precommit` additionally runs `check-changelog-fold`, which needs `.git` and therefore runs on the operator rung only (`hideGit=true` in the prompt container).
- `bash scripts/acceptance.sh` — exits 0, and its coverage-block assertion prints PASS.
- The AC6 negative: in a scratch copy of the repo with the `#### Review Coverage` line removed from `commands/pr-review.md`, `bash scripts/acceptance.sh` exits non-zero — run this, do not assume it.
- The `grep` checks named in AC1 through AC5, AC7 and AC8.

### Operator-executable (runs on the host after PR merge, spec verification ladder)

- `claude plugin update coding@coding` then reload, and confirm the installed version from the load path — the fixture runs below must execute the released plugin, not the worktree.
- **Coverage DoD (AC9–AC11):** from a session loaded after the deploy, over a scratch repo, run `/coding:pr-review` on a clean fixture and paste the block; then repeat with `ast-grep`/`sg` removed from `PATH` and with the selector guide moved aside at both resolved paths, and grep each block per AC11.
- **Counts and skip reasons (AC14, AC15):** run a findings-bearing fixture and check that the deterministic and judgment counts match the report's findings and sum to its total; run a selector-mode review without `--security` and a short-mode review, and check the skipped rows' `Reason` cells.
- **Bot DoD (AC12):** read the reviewer repo's verdict mapping and run the two greps; record the outcome in `# Progress`.
- **Bench DoD (AC13):** re-run the bench against SC3's post-change baseline and record both figures in `# Progress`.
- **Release tail (out of band, not gated here):** after merge, `.maintainer.yaml` (`autoRelease: true`) cuts the tag via the maintainer-agent-releaser; confirm the released version via `claude plugin list`.

## Desired Behavior

1. **A fixed block is the last section of the Step 5 report.** `commands/pr-review.md` Step 5 gains a mandatory `#### Review Coverage` section, emitted after the findings sections, the traceability section and the security sections, in every mode (short, selector, full) and with or without `--security`. The block has exactly this shape, with one row per tier:

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

   The `Reason` cell is `—` when the tier ran, and a short reason when it failed or was skipped. The **emitted** block is unfenced: the fenced template above exists only in the command file, because the bench's line reader ignores fenced lines and a fenced emitted heading would be invisible to harvest.

2. **The three statuses have one meaning each.** `ran` means the tier's own procedure completed; a legitimate zero-findings result (including the selector short-circuit `selector clean — no adjudication needed`) is `ran` with `0`, never `failed`. `failed` means the tier was required by this invocation and could not complete: the deterministic tier when `ast-grep`/`sg` is missing, the runner exits non-zero, or `make precommit` cannot be executed in full mode; the judgment tier when the selector guide is missing, an adjudicator dispatch fails or returns empty, or a full-mode owner dispatch errors; the security tier when model derivation, the verifier gate or the toolchain scan fails. `skipped` means the invocation did not require the tier: short mode (deterministic and judgment), the Step 4 early exit when no rule-relevant file changed (deterministic and judgment), and `--security` absent (security). A skip is never a failure, and a failure is never written as a skip.

3. **Findings are counted per tier, from what the report already emitted.** Each emitted finding is attributed to exactly one tier, by this precedence: (1) a finding emitted by the security pipeline — a security rule, an invariant or a toolchain finding — counts in `security`; (2) otherwise a finding whose `rule_id` resolves in `rules/index.json` to `enforcement_type: mechanical` or `script` counts in `deterministic`; (3) otherwise a `judgment` rule counts in `judgment`; (4) a finding with no `rule_id` counts in `judgment`, so nothing falls through the attribution. The three cells sum to the report's total finding count, so a finding is never counted twice and none is silently dropped. A tier that did not run and has no attributed finding carries `0`; its `Status` says why. A finding attributed to a skipped tier — for example a Step 3 `make precommit` failure with no `rule_id`, which attributes to `judgment` in short mode — is still counted in that tier's `Findings` cell while the row keeps `skipped`; the sum rule wins over the `0` default. The count is a tally of this invocation's report, never a re-run and never an estimate.

4. **The `Result:` line is the machine verdict.** `Result: clean` if and only if no tier is `failed`. `Result: not clean` when any tier is `failed`, with each failed tier and its reason named on the same line (`Result: not clean — deterministic failed: ast-grep not in PATH`). A `skipped` tier never makes a result not-clean; that is the difference between "not applicable" and "did not work".

5. **The SHA is the reviewed commit, full length, fail-closed.** The value comes from `cd <REVIEW_DIR> && git rev-parse HEAD` (the same `REVIEW_DIR` the review used, so the `ALREADY_AT_HEAD` short-circuit needs no special case), is emitted as the full 40-character lowercase hex string, and is never abbreviated or reconstructed. If the command fails, the block states `Reviewed commit: unavailable — <short reason>` and marks the deterministic row `failed` with the same reason, so the verdict rule yields `Result: not clean` instead of a fabricated SHA — an unreadable commit is a toolchain failure, not a clean review.

6. **The block changes nothing it reports on.** It adds no finding, drops no finding, changes no severity, changes no `Judgment tier:` line and changes no traceability content. The finding set of a review is byte-for-byte the same before and after this change; only the report gains the block.

7. **The contract is regression-locked and the bot is untouched.** `scripts/acceptance.sh` gains a block that asserts the literals above and fails when the heading or the `Result:` forms leave the command. The reviewer bot needs no change: it derives its verdict from the JSON verdict block's `blocking` fields and its fail-closed funnel steer, and parses no markdown heading and no `Result:` line, so the added block is inert to it. CHANGELOG gains an `## Unreleased` `feat:` bullet and `make precommit` exits 0.

## Constraints

- **Report-only.** The change edits `commands/pr-review.md` and `scripts/acceptance.sh`, plus `CHANGELOG.md`. No rule file, no index, no runner, no verifier, no bot code.
- **One block, one shape (frozen).** The heading is `#### Review Coverage`; the table header is `| Tier | Status | Findings | Reason |`; the tier tokens are exactly `deterministic`, `judgment`, `security`; the status tokens are exactly `ran`, `failed`, `skipped`; the SHA line begins `Reviewed commit: `; the verdict line begins `Result: ` and continues `clean` or `not clean`. These literals are what `scripts/acceptance.sh` asserts, so a reworded heading is a test failure rather than a silent drift.
- **Emitted last.** The block is the final section of the consolidated report. The bench's report parser treats any heading as the end of the preceding findings section, so a block placed mid-report would truncate a findings section it followed; placing it last is what keeps the bench's harvest unchanged.
- **No fabricated values.** A tier result is written from what happened in the invocation. A tier whose result is unknown is `failed` with the reason, never `ran` with a guessed count.
- **Reason strings are bounded.** A reason quotes at most a short tool message (one line, truncated), never a full stderr dump — the block is pasted into PR bodies.
- **Full 40-character SHA.** `git rev-parse HEAD` on a SHA-1 repository emits 40 hex characters; the command states the value is emitted verbatim. (A SHA-256 repository is out of scope and would emit 64; the acceptance assertion and the operator grep are written against the 40-character form because that is what this repo and its consumers use.)
- **Marker hygiene on added lines.** The `self-containment/*` rules scan changed files whole and exempt exactly six paths — `specs/`, `prompts/`, `docs/self-containment-guide.md`, `agents/self-containment-assistant.md`, `scripts/rule-checks.sh` and `scripts/testdata/`. This change adds lines to `commands/`, `scripts/acceptance.sh` and `CHANGELOG.md`, **none of them exempt**, so every added line carries no home-directory path, no requirement id, no planning-directory reference and no revision or sign-off meta. AC8 enforces it.
- **Generic content only.** Any example in the command uses User, Order, Product, Customer — never a trading or project-specific domain.
- **Release tail.** `.dark-factory.yaml` sets `autoRelease: false`; the release is cut by the maintainer-agent-releaser per `.maintainer.yaml` (`autoRelease: true`). This spec requires only the CHANGELOG `## Unreleased` entry.
- **Approval discipline.** Never edit frontmatter status manually — approval goes through `dark-factory spec approve`.

## Failure Modes

| Trigger | Expected behavior | Recovery |
|---|---|---|
| A tier silently reports `ran` when its tool never executed | The block certifies coverage that did not happen, which is the defect this change exists to remove | AC10's removed-toolchain run must read `failed`; re-run it |
| `Result: clean` is emitted while a tier row reads `failed` | The report contradicts itself and the clean verdict is untrustworthy | Derive the verdict from the rows alone (clean iff no `failed` row); re-run AC11's grep pair |
| The SHA is abbreviated, stale, or reconstructed | The block pins the wrong commit, which is the Five-Lens weakness #7 this change avoids | Emit `git rev-parse HEAD` verbatim from `REVIEW_DIR`; re-run AC9's equality check |
| The selector short-circuit is written as `failed` | Every clean selector review reads not-clean, and the verdict becomes noise | Treat the short-circuit as `ran` with `0`; re-run AC9 |
| A skipped tier (short mode, no rule-relevant files, no `--security`) is written as `failed` | Clean runs read not-clean for a tier that was never applicable | Apply the skip semantics; re-run AC9 and AC15 |
| The `Findings` cells are hardcoded `0` | The block certifies zero findings on a report that has findings | Count from the emitted report per DB3's attribution; re-run AC14 |
| The block is placed before a findings section | The bench's parser ends that findings section at the block heading and drops its findings from harvest | Move the block last; re-run `make bench-test` and AC13 |
| The block is copied into `commands/local-review.md` or `commands/code-review.md` | Out-of-scope commands change behaviour and their scenarios are re-scored against a shape they were not written for | Revert the copy; AC7's diff and greps catch it |
| A later edit drops the block from the command | The coverage statement silently disappears while the rest of the report still looks complete | `scripts/acceptance.sh` fails on the literal assertion; restore the block |
| A reason string carries a multi-line stderr dump | The pasted block becomes unreadable and may carry paths the self-containment rules flag | Truncate to one line; re-run AC8's marker sweep |
| The block is produced by re-running a tier rather than reporting the invocation | Cost doubles and the second run may disagree with the reported findings | Read the invocation's own results; never re-run |
| The bot's verdict changes for an existing input | A PR that previously approved now requests changes (or the reverse) with no code change | The bot is not edited; confirm its parser reads the JSON verdict block, not the report headings (AC12) |

## Security / Abuse Cases

- **No new untrusted input.** The block reads only the invocation's own tier outcomes and `git rev-parse HEAD` in the reviewed worktree. It opens no network path, reads no PR body, and adds no dispatch.
- **No new trust boundary.** The SHA is a value git already computed; the tier statuses are the command's own control flow. Nothing in the block is attacker-controlled beyond a repo's ability to make a tier fail, which is the behaviour being reported.
- **Bounded reason text.** A reason is a short, single-line tool message, truncated. It is not a channel for a repository to inject arbitrary content into a pasted PR body.
- **Fail-closed on silence.** The highest-risk outcome for a review gate is a clean-looking report produced by a tier that did not run. That is why an unknown tier result is `failed` and why an unreadable SHA forces `not clean`; there is no path from "could not determine" to `Result: clean`.
- **No privilege change.** The block is report text. It grants no tool, no write and no merge authority; the bot's merge verdict remains the JSON `blocking` contract.

## Suggested Decomposition

Prompts generated in this order — each row is one prompt with an auditable scope. Ordering keeps `make precommit` green after every prompt.

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Add the `#### Review Coverage` contract to `commands/pr-review.md` Step 5 — the table shape, the three status definitions, the per-tier finding tally, the `Result:` derivation, the `Reviewed commit:` SHA source and the fail-closed cases | 1, 2, 3, 4, 5, 6 | 1, 2, 3, 4, 5 | — |
| 2 | Add the coverage-block assertion block to `scripts/acceptance.sh` with the literals hardcoded, and verify the scratch-copy negative | 7 | 6 | prompt 1 (the literals prompt 1 writes) |
| 3 | CHANGELOG `## Unreleased` feat entry plus the final cross-cutting gates (`make precommit`, the scope-lock and marker ACs) | 7 | 7, 8 | prompts 1, 2 |

Rationale: prompt 1 is the only prompt that edits the command, keeping it single-writer. Prompt 2 depends on prompt 1's literals. Prompt 3 is the release tail. AC9–AC15 are operator-executable — they need the released plugin, a findings-bearing fixture and the bench — and are covered by the Verification operator rung, not by a prompt.

**Why one spec, not two.** The size budget flags a 7×15 surface, but every row is one report-only contract on one command plus one acceptance assertion. Splitting the operator rung into a second spec would double the release cycles for a change that ships no rule and no runtime behavior, and the parent goal ships strictly one change per bench re-run — a split would buy no attribution and cost a second release and a second bench run. The three-prompt decomposition keeps the implementation small.

## Do-Nothing Option

If this does not ship, every `/coding:pr-review` report keeps a single judgment-tier line as its only coverage statement. A deterministic or security tier that crashed, was never invoked, or could not dispatch stays invisible, so the report reads as a clean pass over coverage that did not happen. The operator cannot use a local review as the PR record that clears an oversized PR, because the report pins no commit and states no per-tier coverage. The parent goal [[PR Reviewer Adopts What the Five-Lens Gate Got Right]] closes SC4 on nothing, and the one technique the gate analysis flagged as both cheap and load-bearing — a per-tier coverage block — stays unported while the gate itself demonstrates the shape on every PR it runs.
