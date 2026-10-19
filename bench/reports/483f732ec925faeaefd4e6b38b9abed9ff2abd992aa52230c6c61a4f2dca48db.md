483f732ec925faeaefd4e6b38b9abed9ff2abd992aa52230c6c61a4f2dca48db

## Configuration
- model: MiniMax-M3.1-Flash-Preview[1m]
- effort: high
- mode: full
- config_hash: 483f732ec925faeaefd4e6b38b9abed9ff2abd992aa52230c6c61a4f2dca48db
- rules_commands_hash: 79f3137f0d3c378fd813a76bec0554db83c68fccc5e749117374223101fb5d2e
- prs_version: curated-1
- coding version: 0.60.1
- golden baseline coding version: v0.35.6
- golden version: golden-curated-4
- runner_version: 1
- rows skipped: 0
- cost: not recorded — the ledger carries no cost field.

*golden-curated-4* carries 21 `rejected` entries, so precision is measurable: reporting one costs precision. With so few adjudicated, a single hit still moves the number a long way — read it as directional, not calibrated.

No signature embeds a line reference, so a re-report of the same issue at a different line still matches. `recall` measures issue detection.

## Runs
| run | span | PRs | complete | golden in scope | findings | hits | misses | matched rejected | gap candidates | recall | precision | wall time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-18T16:27:37.189296+00:00 … 2026-10-18T18:23:58.012463+00:00 | 31/20 | partial | 158 | 178 | 15 | 122 | 0 | 163 | 0.109 | 1.000 | 7247 |

## Per-PR
| run | pr_id | golden in scope | hits | misses | findings | gap candidates | dropped items | missing sections | duration (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | tts-mcp#20 | 1 | 0 | 1 | 0 | 0 | 0 | — | 82 |
| 1 | github-pr-review-agent#11 | 16 | 4 | 10 | 9 | 5 | 0 | — | 360 |
| 1 | quant#109 | 10 | 0 | 10 | 1 | 1 | 0 | — | 71 |
| 1 | node-skeleton#2 | 12 | 1 | 11 | 7 | 6 | 0 | — | 814 |
| 1 | python-skeleton#3 | 17 | 2 | 14 | 8 | 6 | 0 | — | 424 |
| 1 | vault-cli#68 | 1 | 0 | 1 | 0 | 0 | 0 | — | 115 |
| 1 | backup#15 | 4 | 0 | 2 | 1 | 1 | 0 | — | 127 |
| 1 | bw#41 | 3 | 0 | 2 | 1 | 1 | 0 | — | 226 |
| 1 | dark-factory#71 | 2 | 0 | 2 | 3 | 3 | 0 | — | 197 |
| 1 | tts-mcp#16 | 6 | 0 | 5 | 10 | 10 | 0 | — | 194 |
| 1 | tts-mcp#3 | 6 | 1 | 4 | 7 | 6 | 0 | — | 251 |
| 1 | distill#6 | 10 | 1 | 6 | 8 | 7 | 2 | — | 183 |
| 1 | vault-ui#39 | 6 | 1 | 5 | 15 | 14 | 0 | — | 234 |
| 1 | recurring-task-creator#30 | 6 | 0 | 4 | 3 | 3 | 0 | — | 162 |
| 1 | tts-mcp#10 | 9 | 0 | 7 | 4 | 4 | 0 | — | 87 |
| 1 | discord-assistant#5 | 13 | 1 | 12 | 10 | 9 | 0 | — | 131 |
| 1 | tts-mcp#13 | 10 | 3 | 6 | 5 | 2 | 0 | — | 201 |
| 1 | github-releaser-agent#8 | 13 | 0 | 9 | 7 | 7 | 0 | — | 531 |
| 1 | discord-assistant#1 | 9 | 0 | 9 | 8 | 8 | 0 | — | 243 |
| 1 | helm#3 | 4 | 1 | 2 | 5 | 4 | 0 | — | 135 |
| 1 | agent-task-executor#67 | 0 | 0 | 0 | 7 | 7 | 0 | — | 206 |
| 1 | vault-ui#94 | 0 | 0 | 0 | 3 | 3 | 0 | — | 169 |
| 1 | ai-assistant#111 | 0 | 0 | 0 | 1 | 1 | 0 | — | 262 |
| 1 | claude-supervisor#91 | 0 | 0 | 0 | 11 | 11 | 0 | — | 309 |
| 1 | claude-supervisor#100 | 0 | 0 | 0 | 13 | 13 | 0 | — | 186 |
| 1 | claude-supervisor#85 | 0 | 0 | 0 | 6 | 6 | 2 | — | 409 |
| 1 | ai-assistant#107 | 0 | 0 | 0 | 7 | 7 | 0 | — | 213 |
| 1 | agent-claude#20 | 0 | 0 | 0 | 4 | 4 | 0 | — | 203 |
| 1 | nuke#357 | 0 | 0 | 0 | 1 | 1 | 0 | — | 116 |
| 1 | bw#49 | 0 | 0 | 0 | 0 | 0 | 0 | — | 75 |
| 1 | git-ai-sync#16 | 0 | 0 | 0 | 13 | 13 | 0 | — | 329 |

*Effective fixture: **31 of 20** PRs produced a scored row.* **4** findings carried no matching key and never reached scoring.

## Gap-triage candidates
These findings matched no golden entry. They are **not a precision failure** — the golden set is a bootstrap from one strong-model run, and a finding it does not describe is evidence the set is incomplete.

### run 1 — github-pr-review-agent#11 — docs/pr-post-back.md:124

**`docs/pr-post-back.md:124`** — attributes nil-poster behaviour to "the LGTM path", which no longer exists: `planningStep` holds no poster and `PostLGTM` is deprecated with no callers. The real short-circuit is `postAndRoute` (`pkg/steps_checkout_execution.go:315-321`), returning `Status: done, NextPhase: ai_review`. The parenthetical this diff *added* ("`PostLGTM` itself is deprecated and has no non-test callers") is factually true — and thereby contradicts the sentence it annotates.

### run 1 — github-pr-review-agent#11 — pkg/factory/runner.go:57

**`pkg/factory/runner.go:57-59`** — "suppresses all GitHub write calls" understates: returning a nil verifier also suppresses a GitHub **read** (`pkg/steps_review.go:118`). Separately, the App installation-token mint (`cmd/run-task/main.go:138`) still POSTs under the flag. Same wording at `cmd/run-task/main.go:75-76` and `CHANGELOG.md:11`.

### run 1 — github-pr-review-agent#11 — pkg/factory/runner.go:134

**`pkg/factory/runner.go:134`** — `SkipPost` is consulted only inside `if agent == nil`. A caller supplying `cfg.Agent` with `SkipPost: true` gets a **silent no-op** — no error, no log. Unreachable today (`main.go` doesn't set it), but this is a safety flag whose failure mode is silence.

### run 1 — github-pr-review-agent#11 — pkg/skip_post_boundary_test.go:224

**`pkg/skip_post_boundary_test.go:224`** — `NotTo(ContainSubstring("ai_review verify:"))` is not the detector the comment claims. Under the regression, `VerifyReview` nil-derefs and **panics before returning**; and with a working verifier nothing is appended. Assert `BeIdenticalTo(nil)` on the verifier directly; keep the substring as belt-and-braces.

### run 1 — github-pr-review-agent#11 — CHANGELOG.md:11

**`CHANGELOG.md:11`** — the `feat:` bullet bundles three unrelated changes (flag, nil-guard fix, doc corrections); the guide asks for one bullet per change. The `fix:` prefix on the `klauspost/compress` bump at `:10` is defensible (security remediation) but the guide prefers `chore:` for dependency updates.

### run 1 — quant#109 — task/recurring-schedules/prod/feed-worms.yaml:12

**`task/recurring-schedules/prod/feed-worms.yaml:12`** — this CR fires on `weekdays: [Sunday, Wednesday]` but carries no `due_date`, so it is the one Sunday-firing Schedule left behind by a change whose commit message scopes itself to "weekend-firing Schedule CRs". It is the only weekend-firing CR outside the diff (`ibkr-swing-trading` is Mon–Fri, correctly out of scope), so the omission reads as a missed file rather than a deliberate exclusion. Add `due_date: "{{current_date}}"` under its `frontmatter` to match the other eight Sunday-due schedules.

### run 1 — node-skeleton#2 — package-lock.json

**`package-lock.json`** — the PR adds a new transitive dependency `@typescript-eslint/typescript-estree/node_modules/brace-expansion@5.0.9`, which falls inside the advisory ranges `GHSA-q2hr-2g5m-vwhr` and `GHSA-qhr7-859c-m2p7`. `make audit` (`npm audit --audit-level=high`) therefore exits 1 and `make precommit` fails at the `audit` step. Dev-only path, so no runtime exposure — but CI runs `make precommit` and will go red. Fix: `npm audit fix` (or pin the tree to a fixed `brace-expansion`). Evidence it is not this PR's regression: the other three flagged packages resolve identically on both sides — `proxy-addr@2.0.7` (critical, `GHSA-jqcg-44mw-7w3h`), `js-yaml@4.3.1`, `qs@6.15.3`, `brace-expansion@1.1.18` are byte-identical at `origin/bench-base-2`. **`make precommit` already failed on the base branch**; this PR adds one more vulnerable copy on top.

### run 1 — node-skeleton#2 — README.md:55

**`README.md:55-59`** — the Layout block now lists `.ts` files, but the README never states that sources are TypeScript executed directly by Node's native type stripping (no build step, no `dist/`) or what Node version that requires. This is load-bearing: `package.json` declares `"node": ">=22"`, while unflagged type stripping starts at Node **22.18.0** — on 22.0–22.17 `node src/index.ts` dies with `Unknown file extension ".ts"`, so the Quick Start breaks for an engineer who satisfies the stated requirement. Fix: add a short TypeScript/requirements note and tighten `engines`.

### run 1 — node-skeleton#2 — package.json:7

**`package.json:7-9`** — same root cause as above, in the manifest itself: `engines.node` stays `">=22"` while the entrypoint moved to `src/index.ts`. Node only strips types without a flag from 22.18. Fix: `">=22.18"` (or add `--experimental-strip-types` and floor at 22.6). The `node:22-slim` base image floats past 22.18, so the container is unaffected.

### run 1 — node-skeleton#2 — src/config.ts:52

**`src/config.ts:52`** — the new validator rejects `shutdownTimeoutMs < 0` but accepts `0`, which makes the forced-exit timer fire immediately on SIGTERM and drop every in-flight request — the exact failure the drain window exists to prevent. Fix: `< 1`, or add an upper bound tied to `terminationGracePeriodSeconds`.

### run 1 — node-skeleton#2 — CHANGELOG.md:13

**`CHANGELOG.md:13`** — `feat:` misclassifies a restructure-plus-tooling change; the changelog guide buckets this as `refactor:` ("code restructure") or `chore:` ("build, tooling"), and reserves `feat:` for genuine new capability. Consequence: the autoRelease agent minor-bumps a refactor instead of patch-bumping it. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — node-skeleton#2 — README.md:42

**`README.md:42`** — "`tsc --noEmit` — the only step that validates types" is inaccurate as written: `make lint` also rejects type-level code (`no-explicit-any`, `no-non-null-assertion`) that `tsc` permits. Fix: "`tsc --noEmit` — type-checks the sources; Node strips types without checking them".

### run 1 — python-skeleton#3 — CHANGELOG.md:18

**`CHANGELOG.md:18`** — `- ci: install trivy in CI` uses `ci:`, which is outside the rule's recognised prefix set (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `perf:`). `chore:` is the correct prefix for tooling. The other nine new bullets are correctly prefixed. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — python-skeleton#3 — README.md:76

**`README.md:76-94`** — the new `## Security gates` section carries maintainer/ADR content rather than user-facing usage: the no-severity-threshold design argument (`:80`), the internal reason `audit`/`trivy` depend on `sync` (`:82`), the ruff `S104`/`S101` suppression rationale (`:84`, duplicating `pyproject.toml:65-72` in a second location that will drift), the `osv-scanner` rejection rationale (`:86`), and a cross-skeleton table naming unlinked external repos (`:90-94`). Fix: keep a one-line factual statement of what `make check` runs, move the rationale to `CLAUDE.md` or `docs/security.md`, delete the table's self-referential `python-skeleton` row. *(rule: `readme/user-facing-not-agent-context`)*

### run 1 — python-skeleton#3 — Makefile.precommit:46

**`Makefile.precommit:46`** — `trap 'rm -f "$$REQ"' EXIT INT TERM` handles `INT`/`TERM` but never exits; after the handler returns, `sh` resumes, so an interrupted `uvx pip-audit` can have `$REQ` removed while still reading it. Fix: `trap 'rm -f "$$REQ"; exit 130' INT; trap 'rm -f "$$REQ"; exit 143' TERM`, keeping the `EXIT` trap.

### run 1 — python-skeleton#3 — Makefile.precommit:57

**`Makefile.precommit:57-67`** — `trivy` is an undeclared host dependency of `check`, unlike `audit` which self-provisions via `uvx`; a developer without it gets exit 127 rather than an install hint. It is also unpinned while `PIP_AUDIT_VERSION` is pinned, so a trivy update changes gate findings with no commit. Fix: presence check with an install hint, and pin the version alongside `PIP_AUDIT_VERSION`.

### run 1 — python-skeleton#3 — README.md:82

**`README.md:82`** — "Without that dependency a fresh clone would scan no Python manifest at all" holds for `trivy` (which reads `uv.lock` directly) but not for `audit`, where `uv export` resolves from `pyproject.toml` and writes the lock if absent. The `sync` dependency is still right for reproducibility, but the stated reason overstates it. The same imprecision is in the comment at `Makefile.precommit:47-49`.

### run 1 — python-skeleton#3 — Makefile.precommit:48

**`Makefile.precommit:48`** — `uvx pip-audit@$(PIP_AUDIT_VERSION)` runs outside the locked environment; the project convention elsewhere is `uv run`. Version-pinned, so acceptable, but adding `pip-audit>=2.9.0` to `[project.optional-dependencies].dev` and calling `uv run pip-audit` would keep the audit tool in `uv.lock`.

### run 1 — backup#15 — Makefile:127

**`Makefile:127`** — the changed `docker build` invocation passes only `NPM_REGISTRY`; the three canonical build args (`BUILD_GIT_VERSION` via `git describe --tags --always --dirty`, `BUILD_GIT_COMMIT` via `git rev-parse --short HEAD`, `BUILD_DATE` via `date -u +%Y-%m-%dT%H:%M:%SZ`) are still absent, so the image carries no version/commit/date metadata, and `main.go` declares no matching `buildGitVersion` / `buildGitCommit` / `buildDate` vars wired through `-ldflags "-X"`. This is pre-existing convention debt inherited from the base branch, not introduced here — the diff only had to touch that line to add the build arg. *(rule: `go-build-args/three-args-required`)*

### run 1 — bw#41 — groups/meta/k3s.py:20

**`groups/meta/k3s.py:20-26`** — the ARP thresholds are hardcoded into group metadata, so they apply to any node whose *name* matches `.*k3s.*`, regardless of whether `k3s.enabled` is true. The repo's established pattern for feature-scoped sysctl is a `@metadata_reactor.provides('sysctl/options')` in the owning bundle, gated on the feature flag — see `bundles/kvm-host/metadata.py:39`, `bundles/kvm-guest/metadata.py:29`, `bundles/netplan/metadata.py:2`, `bundles/intellij/metadata.py:23`. `bundles/k3s/metadata.py` already uses exactly this shape for `iptables`. Moving the block there would keep one feature's config in one place. Not a correctness defect — Bundlewrap merges group and node metadata, so either placement works. No rule id maps to this.

### run 1 — dark-factory#71 — pkg/specnum/specnum.go:9

**`pkg/specnum/specnum.go:9`** — `make precommit` **fails** (exit 2). `make check` runs `golangci-lint v2.11.4`, which cannot decode the installed toolchain's export data: `cannot decode "unicode", export data version 5 is greater than maximum supported version 2`. This is a Go 1.27.2 vs golangci-lint v2.11.4 incompatibility, **not a defect in this diff** — `pkg/specnum/specnum.go` is not in the changed set, and the 2 reported issues are import-resolution `typecheck` errors, not lint findings about code. It does mean the repo's standard verification gate is currently red for environmental reasons; the diff's own test suite (`go test -p=18` across ~50 packages) passed.

### run 1 — dark-factory#71 — agents/prompt-auditor.md:509

**`agents/prompt-auditor.md:509-518`** — the rewritten `<final_step>` deletes all three numbered options, which regresses a live spec's acceptance criterion. `specs/align-agents-with-coding-guide.md` (criterion 6, and its DoD evidence line) requires auditor `<final_step>` blocks to contain **≥4** numbered options matching `^[1-9]\. \*\*`, and criterion 6 is explicitly written as adding a fourth option on top of the existing three ("distinct semantics from the existing three"). That spec is `status: draft`, not in `specs/completed/`. Its own evidence command confirms the regression: `awk '/<final_step>/,/<\/final_step>/' agents/prompt-auditor.md | grep -cE '^[1-9]\. \*\*'` returns **0** at HEAD versus **3** on the base branch (sibling `agents/spec-auditor.md` is untouched at 3). Nothing parses the options programmatically — `commands/audit-prompt.md` and `commands/generate-prompts-for-spec.md` only read the report body — so this is a spec-reconciliation gap, not a runtime break. Amend the spec, or record why the criterion no longer applies.

### run 1 — dark-factory#71 — CHANGELOG.md:15

**`CHANGELOG.md:15`** — the entry says "for each Blocker/Critical issue", but `prompt-auditor`'s severity taxonomy is only **Critical Issue** / **Recommendation**; "Blocker" is not a term this agent uses anywhere (verified across all 20 severity mentions in the file). Dropping "Blocker/" would keep the entry accurate. *Independently flagged by the agent-auditor dispatch.*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:8

**`skills/voice/SKILL.md:8`** — the change's central claim is false. The file asserts *"This skill is the sole authority on spoken-output volume — there is no competing always-on rule in `~/.claude/CLAUDE.md`"*. Verified live: `~/.claude/CLAUDE.md` still carries **Voice Chat Brevity** (line 99) and **Attention Costs Operator** (lines 100–103), both always-on and both governing `mcp__tts__say` volume. Only the older "Voice Attention Only … `ryan`" rule was removed. A user-level `CLAUDE.md` outranks a plugin skill, so the memory rule still wins — the exact condition the CHANGELOG says is fixed. Independently flagged by three of five agents. Beyond this machine the claim is unshippable at all: a plugin cannot assert the absence of rules in a consumer's memory file.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:69

**`skills/voice/SKILL.md:69-74`** — the capability table's Answers column contradicts the surviving rule and presents `narrate` as novel. Rows `on` and `interview` say `❌ screen only`, but `~/.claude/CLAUDE.md:102` mandates *"answer a direct operator question by voice — 1–3 sentences, gist first — in every active mode"*, and states it gates only *unprompted* speech. Either align the column or scope the table to unprompted speech.

### run 1 — tts-mcp#16 — CHANGELOG.md:16

**`CHANGELOG.md:16-17`** — records a migration that did not fully happen. "sole authority", "no always-on default any more" and "previously carried by an always-on `~/.claude/CLAUDE.md` rule" are contradicted by the live config. Suggest recording what actually changed (the old `Voice Attention Only` rule removed; volume policy now documented per-mode).

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — description says "Activation speaks a one-line confirmation" unconditionally, while line 33 correctly exempts `off` and `status`.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — the unquoted `description` scalar contains `Args: ` (colon + space), illegal in YAML plain scalar; `yaml.safe_load` raises `ScannerError`. The base file fails identically (pre-existing), but this line was rewritten, so it is the moment to quote the value or drop the colon.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:8

**`skills/voice/SKILL.md:8`** — `~/.claude/CLAUDE.md` machine-path reference. *(rule: `self-containment/no-home-dir-paths`)* — downgraded from MUST to Optional: it is the conventional Claude Code user-config path, resolves for every consumer, and is prose rather than a runtime read. Prefer naming the rule kind over the file location.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:94

**`skills/voice/SKILL.md:94`** — same reference, same downgrade. *(rule: `self-containment/no-home-dir-paths`)*

### run 1 — tts-mcp#16 — CHANGELOG.md:16

**`CHANGELOG.md:16`** — same reference in the `### Changed` bullet. *(rule: `self-containment/no-home-dir-paths`)*

### run 1 — tts-mcp#16 — CHANGELOG.md:10

**`CHANGELOG.md:10,14`** — `### Added` / `### Changed` headings under `## Unreleased` contradict `changelog-guide.md:73` ("Flat list — no categories"). Mitigated: every released section in this repo uses categories, so a fix is repo-wide, not PR-local.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md

**`skills/voice/SKILL.md`** — no Success Criteria / Prerequisites section, which the skill-writing guide's checklist expects.

### run 1 — tts-mcp#3 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — the rewritten `description:` is not parseable YAML: the unquoted `Args: on | off | …` introduces a `: ` sequence, and `yaml.safe_load` fails with `mapping values are not allowed here` (column 410), which makes both `name` and `description` unreadable to a strict parser. Note this is **pre-existing** — the base branch fails the same way at column 323 — so the diff rewrites the line and carries the defect forward rather than introducing it. Quote the scalar or drop the `Args:` segment into the body. *(rule: `skill-writing/skill-md-frontmatter-required`)*

### run 1 — tts-mcp#3 — CHANGELOG.md:12

**`CHANGELOG.md:12`** — the new `## Unreleased` bullet starts with a code span (`` `commands/voice-test.md` ``), not a conventional prefix; version-bump detection falls through to patch for a genuinely new command. Use `feat: …`. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — tts-mcp#3 — CHANGELOG.md:16

**`CHANGELOG.md:16`** — same: no conventional prefix. Use `refactor: …`. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — tts-mcp#3 — commands/voice-test.md:15

**`commands/voice-test.md:15`** — `(lead throwaway word per the playbook — CoreAudio clips the first word)` restates a rule owned by `skills/voice/SKILL.md:42` and names the authority only as "the playbook", with no path. Point at `skills/voice/SKILL.md` instead of duplicating. *(rule: `agent-cmd/single-source-of-truth`)*

### run 1 — tts-mcp#3 — CHANGELOG.md:12

**`CHANGELOG.md:12`** — the trailing clause "This is the extracted startup handshake, now invoked deliberately instead of on every activation" narrates the refactoring operation rather than what the command does. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — tts-mcp#3 — skills/voice/SKILL.md:22

**`skills/voice/SKILL.md:22`** — "in practice it is, and the handshake cost a round-trip on every activation" justifies the change by its origin; the surrounding sentence already states the behavior. Rationale belongs in the CHANGELOG, not the user-facing skill body. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:36

**`hooks/deny-generated-file-edits.sh:36`** — `Source:` extraction uses `\S+`, which stops at the first whitespace, so any source directory containing spaces is truncated in the denial message. Verified against the path shape this repo itself emits at `docs/spec.md:279`: extracted `…/Personal/50`, expected `…/Personal/50 Knowledge Base/CLAUDE Rules`. The `Regenerate:` extraction one line below uses `.+` and is correct — the asymmetry is the tell. Fix: `grep -oE 'Source:[[:space:]]*.+'`, matching the `Regenerate:` pattern.

### run 1 — distill#6 — CHANGELOG.md:7

**`CHANGELOG.md:7`** — `feat(hooks):` does not satisfy `changelog/conventional-prefix-required`. The rule's own enforcement regex `^- ([a-z]+:)` does not match a scoped prefix; verified by running the regex against both forms. Since `feat:` is what selects a minor bump, this ships a new user-facing capability as a patch. The existing `chore(dev):` entries do not establish precedent — `chore` is a patch either way, so the scope is invisible there. Fix: `feat:` (the hook path is already named in the sentence). *(rule: `changelog/conventional-prefix-required`)*

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:33

**`hooks/deny-generated-file-edits.sh:33`** — a filename starting with `-` is parsed by `head` as an option rather than a path. Verified: `./-dash.md` denies correctly, but the bare `-dash.md` passes through. Low impact — Claude Code sends absolute paths. Fix: `head -c 2048 -- "$path"`.

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:34

**`hooks/deny-generated-file-edits.sh:34`** — the banner match is unanchored, so any file *describing* the banner within its first 2 KB would be falsely denied. The margin is thin: the phrase sits at byte 2486 in `README.md` and 3662 in `docs/adopting-distill.md` — both just outside the cap. Fix: anchor with `^[[:space:]]*AUTO-GENERATED by distill` plus a required `^[[:space:]]*Regenerate:` companion.

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:11

**`hooks/deny-generated-file-edits.sh:11`** — with `jq` absent the hook exits 127 and emits no JSON, so protection silently disappears. Fail-open is the right call for an accidental-clobbering guard, but README's `Requires jq` (line 149) does not say what happens without it. Fix: `command -v jq >/dev/null || { echo "…hook inactive" >&2; exit 0; }`.

### run 1 — distill#6 — docs/adopting-distill.md:115

**`docs/adopting-distill.md:115`** — "makes that mistake impossible" overstates the guarantee. `Bash` (`sed -i`, `cat > file`) is outside the matcher and writes the generated file unhindered. Soften to "hard".

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:25

**`hooks/deny-generated-file-edits.sh:25`** — `MultiEdit` is covered by neither the `case` arm nor the README matcher; verified passing through. Add it only if your installed Claude Code still exposes that tool.

### run 1 — vault-ui#39 — src/vault_ui/activity.py:53

**`src/vault_ui/activity.py:53`** — `session_id` is interpolated raw into both `project_dir / f"{session_id}.jsonl"` and the glob pattern `*/{session_id}.jsonl`, with no validation. `cleanup.py:51-59` performs *this exact lookup* and explicitly rejects ids containing `/` or `\` before touching the filesystem. Consequences: a `..`-bearing value escapes `project_dir`; glob metacharacters (`*`, `?`, `[…]`) make the fallback match an unrelated file and report its mtime as the card's activity. Impact is capped at an mtime disclosure (no file content is read), but a wrong age on every card for that task is a visible defect. Reuse `session_resolver.is_uuid` / the `/`-guard.

### run 1 — vault-ui#39 — src/vault_ui/activity.py:53

**`src/vault_ui/activity.py:53`** — related, and the same fix covers it: `transcript_mtime` only resolves UUID session ids, but the write path at `api/tasks.py:1728-1737` stores the raw display name whenever `resolve_session_id` fails (`stored_value = request.claude_session_id`). Such tasks silently get **no** transcript signal and fall back to file mtime even when a live transcript exists — and `cleanup.py:59-64` proves display-name ids do occur in the wild ("Clearing unresolved display-name session"). Route through `session_resolver.resolve_session_id`, which the codebase already owns for exactly this.

### run 1 — vault-ui#39 — src/vault_ui/activity.py:61

**`src/vault_ui/activity.py:61`** — the fallback `root.glob(f"*/{filename}")` scandirs `~/.claude/projects` **plus every project directory, once per task, per request**, with no negative-result memoization. On this machine that's 92 project dirs; measured cost is ~0.2 ms per scan, so a 200-card board where most sessions live outside the vault dir re-pays the full scan ~40 ms per poll, every 60 s, forever — for transcripts that will never appear locally. Memoize per `session_id`, or bound the scan to one pass per request.

### run 1 — vault-ui#39 — src/vault_ui/api/tasks.py:1794

**`src/vault_ui/api/tasks.py:1794`** — `_task_to_response` was a pure mapping function; it now performs synchronous `stat`/glob I/O inside the async request path, once per task (list comprehension at `tasks.py:606`), blocking the event loop for the duration of the list build. The existing per-vault cache caches only the subprocess call, so it does not cover this. Resolve activity behind the cache layer, or memoize by `session_id`.

### run 1 — vault-ui#39 — tests/test_activity.py:140

**`tests/test_activity.py:140`** — `test_formatter_uses_single_largest_unit` does not execute the formatter; it slices the source at `APP_JS[start:start+900]` and greps for `"'<1m'"`, `` "}m`" ``, `` "}h`" ``, `` "}d`" ``, `` "}w`" ``. Those literals are present regardless of the comparisons around them, so changing `if (minutes < 60)` to `if (minutes < 600)` leaves the test green while the UI renders `500m` instead of `8h` — the exact bug class the test is named for. The 900-char window also overruns the 537-char function by ~360 chars into `activityAgeHtml`, so tokens in the *next* function satisfy the assertions. Node 22 is available and the function is pure: extract it by brace-matching and run it under `node -e` with `pytest.mark.skipif(shutil.which("node") is None)`, parametrized on boundaries (59s→`<1m`, 60s→`1m`, 3599s→`59m`, 3600s→`1h`, 86399s→`23h`, 86400s→`1d`, 7d−1s→`6d`, 7d→`1w`). The two wiring tests (`test_task_card_renders_activity_age`, `test_goal_card_renders_activity_age`) do prove the call sites exist and are fine as-is.

### run 1 — vault-ui#39 — CHANGELOG.md:7

**`CHANGELOG.md:7`** — the new bullet starts `- feat(ui):`, but the rule's enforcement is the regex `^- ([a-z]+:)` whose first token must be in `feat: | fix: | refactor: | test: | docs: | chore: | perf:`. `feat(ui):` does not match (the char after `feat` is `(`), so a downstream tool reading that regex will not see the `feat:` token. Changing this line to `- feat:` also aligns it with the repo's own dominant convention — 97 unscoped prefixes vs 25 scoped. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — vault-ui#39 — src/vault_ui/activity.py:21

**`src/vault_ui/activity.py:21`** — `_claude_projects_root()` re-encodes the `~/.claude/projects` layout that `cleanup.derive_claude_project_dir` (`cleanup.py:17`) already owns, and `tasks.py` imports that one on the adjacent line. Two modules now encode the same storage convention independently. `session_resolver.py` is the natural single owner ("find a session's `.jsonl`").

### run 1 — vault-ui#39 — src/vault_ui/activity.py:63

**`src/vault_ui/activity.py:63`** — `except OSError` wraps the whole `for` loop, so one unreadable directory aborts the scan for all remaining ones and the function returns `None` despite a readable transcript further down. **Version-dependent:** verified on this repo's own venv (Python 3.14) that `Path.glob` swallows `PermissionError` and the bug does **not** reproduce; it applies to the declared floor of 3.12 (`requires-python = ">=3.12"`), where glob still propagates. Catch per-iteration and `continue`.

### run 1 — vault-ui#39 — src/vault_ui/static/app.js:1117

**`src/vault_ui/static/app.js:1117`** — a future `activity_date` (browser clock behind the server, a vault synced across hosts) yields negative `seconds`, falls into `if (seconds < 60)`, and renders `<1m` — reading "just now" indefinitely and hiding the clock skew. `Math.max(0, …)` plus a distinct label makes it visible.

### run 1 — vault-ui#39 — src/vault_ui/static/app.js:1135

**`src/vault_ui/static/app.js:1135`** — `escapeHtml` (`app.js:1484`) is a text-node escaper (`div.textContent` → `div.innerHTML`); it encodes `& < >` but leaves `"` and `'` intact, which is the wrong escaper for a double-quoted attribute. Not exploitable today because `activity_date` is a Pydantic-serialized `datetime` (ISO 8601, quotes impossible), but the safety rests entirely on that field staying a datetime. The same latent pattern already exists on `app.js:1203` and `1213`/`1262`, so a shared `escapeAttr` fixes all of them.

### run 1 — vault-ui#39 — src/vault_ui/static/app.js:1135

**`src/vault_ui/static/app.js:1135`** — the hover tooltip prints raw ISO UTC (`2026-08-09T08:58:32Z`). The changelog calls it "the full timestamp", which is literally true but not readable outside UTC; `new Date(activityDate).toLocaleString()` suits a tooltip whose only job is human readability.

### run 1 — vault-ui#39 — tests/test_activity.py:10

**`tests/test_activity.py:10`** — `APP_JS`/`STYLE_CSS` are read at **import** time, so moving or renaming the static assets turns all 13 tests (including the nine genuine Python unit tests) into collection errors rather than three localized failures. Read them lazily inside the static-assertion tests.

### run 1 — vault-ui#39 — tests/test_api.py:3642

**`tests/test_api.py:3642`** — no test asserts that `_task_to_response`/`_goal_to_response` actually populate `activity_date` on the response; the existing shape guard is `expected_keys.issubset(...)` (verified at `test_api.py:3642`), which by design only protects pre-existing keys and cannot catch a dropped field. One API-level assertion per endpoint would close it.

### run 1 — vault-ui#39 — CHANGELOG.md:7

**`CHANGELOG.md:7`** — the bullet is a ~700-character paragraph bundling four distinct changes and is declarative where the changelog guide's examples are imperative ("Add…", "Fix…"). The guide sets no length cap and the file's existing style is long-paragraph, so this is style, not a rule violation.

### run 1 — recurring-task-creator#30 — CHANGELOG.md:14

**`CHANGELOG.md:14`** — the dependency bullet `- fix(deps): bump google.golang.org/grpc to v1.82.1 …` does not match the enforcement regex `^- ([a-z]+:)`, so the bump parser sees no valid prefix. The HEAD commit `3f42ce6` ("use conventional prefix for grpc changelog bullet") deliberately traded a prefixless bullet for the Conventional Commits *scoped* form, which this repo's guide does not recognize. Verified: the sibling `- fix:` bullet passes, this one fails. The guide additionally specifies `chore:` for dependency updates. Suggested: `- chore: bump google.golang.org/grpc from v1.79.3 to v1.82.1 (GHSA-hrxh-6v49-42gf, HIGH — xDS RBAC and HTTP/2 vulnerabilities)`. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — recurring-task-creator#30 — pkg/publisher/period_token_test.go:68

**`pkg/publisher/period_token_test.go:68-73`** — the last entry in the block opened by the line-52 comment `// Discriminating entries — old code produces wrong token on these` does not discriminate. I verified empirically with a standalone reproduction of both code paths: `2026-08-31` minus one month is a valid `2026-07-31`, so old and new both yield `2026-07`. (The three entries that *do* discriminate — `2026-07-31`, `2026-03-31`, `2026-05-31` — yield old `2026-07`/`2026-03`/`2026-05` vs new `2026-06`/`2026-02`/`2026-04`.) The branch's own prompt record classifies `2026-08-31` as a control/regression entry, so the test file contradicts its spec. Keep the assertion; move it to the line-36 control block or relabel it. *(rule: `tdd/failing-test-before-implementation`)*

### run 1 — recurring-task-creator#30 — pkg/publisher/period_token.go:105

**`pkg/publisher/period_token.go:105,109,113`** — `time.Date(base.Year(), base.Month(), 1, 0, 0, 0, 0, base.Location())` is triplicated verbatim across the Monthly/Quarterly/Yearly cases. A small unexported `firstOfMonth(base time.Time) time.Time` beside the existing `firstOfPreviousMonth` in `render.go` is the cleaner shape and does not trip `go-composition/no-same-package-private-helper-for-business-logic` (the rule exempts pure same-file leaf helpers). If extracted, it must keep `base.Location()` — do not copy `firstOfPreviousMonth`'s hardcoded `time.UTC`.

### run 1 — tts-mcp#10 — CHANGELOG.md:16

**`CHANGELOG.md:16`** — "clearing **6 of 8** npm-audit findings" contradicts its own enumeration and the next bullet. The enumeration lists 2 high + 4 moderate + 2 low = **8** findings, across **7** distinct packages (`fast-uri`, `hono`, `qs`, `ip-address`, `express-rate-limit`, `esbuild`, `body-parser`); line 17 then says **two remain**. So the entry implies 10 total, not 8, and no reading of the text yields "6". On a repo with `autoRelease: true` this number is the release note's whole security claim — it should read "8 of 10", or the enumeration should be corrected to match the real audit count. *(no rule — data-accuracy defect)*

### run 1 — tts-mcp#10 — CHANGELOG.md:16

**`CHANGELOG.md:16-21`** — the three new bullets carry no conventional prefix, against a MUST rule. But **0 of 45** bullets in this CHANGELOG have a prefix; the file classifies via `### Fixed` / `### Changed` headings instead, and pre-existing Unreleased bullets 12 and 23 follow the same unprefixed style. Prefixing only these three would make the file internally inconsistent. Either prefix them and backfill, or record an exemption for this file. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — tts-mcp#10 — .github/workflows/ci.yml:35

**`.github/workflows/ci.yml:35`** — "without this the `test` check was blind to every change under `mcp/`" narrates the pre-change state, i.e. why the step was added, rather than what the workflow now does. It goes stale once the step lands. The rest of the comment block is present-tense and passes. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — tts-mcp#10 — Makefile.precommit:30

**`Makefile.precommit:30`** — `check` now covers the relay's *types* but still no dependency-vulnerability scanning or secret detection; no `audit`/`trivy` target exists in the repo. Consistent with the PR's own framing (the CHANGELOG documents the `mcp/` audit findings), a scanner that must be remembered gets skipped — wiring `npm audit --audit-level=high` into `check` is what makes it a gate. *(rule: `node/make/security-gates-in-check`)*

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:1980

`shim/claude_openai_shim.py:1980` — `self-containment/no-planning-doc-refs` — comment says *"Two triggers, either is enough — see `# Design`, "What still needs deciding during implementation""*. On a changed line (hunk 1884–2016), and `# Design` resolves against the authoring task file, which ships nowhere; a reader of the merged code has no way to look it up. Fix: state the rationale in the code's own terms — e.g. *"Two triggers, either is enough: length alone misses a short pure-payload answer that never hit `SPOKEN_MAX`."* (The reason is already in the same sentence; only the pointer needs cutting.)

### run 1 — discord-assistant#5 — src/voice.js:896

`src/voice.js:896` — candidate, **not reported** — the `postToChannel` docstring says *"see the task's Out of Scope"*, the same pattern. I could not confirm it falls inside a changed hunk of this diff (hunk line ranges were supplied for config.example.yaml, the shim and CHANGELOG.md only, and I have no shell here to diff it), so under the changed-lines-only contract I am not filing it. Worth a one-line confirmation by whoever runs the diff with git access.

### run 1 — discord-assistant#5 — src/config.js:28

**`src/config.js:28-37`** — `flag()` silently returns the fallback for any unrecognised non-empty value, while the shim parser it was written to agree with treats unknown-non-empty as **true**. A typo'd `INTERRUPT_RESPONSE=ture` reads `false` on the bot and `True` on the shim. The comment at `src/config.js:20-26` claims agreement "on every spelling"; verified divergence on `ture`, `INTERRUPT`, `2`, `maybe`. Same class as `TRANSCRIBE=fals` silently recording. *(rule: `node/config/validate-before-serving`)*

### run 1 — discord-assistant#5 — src/config.js:28

**`src/config.js:28-37`** — bot/shim boolean parsers still disagree on padded quoted values. `X="0" ` (space inside the quotes): bot strips quotes **before** trim, so it sees `"0"` unstripped → fallback; shim strips whitespace first → `0` → false. Verified on `' "0" '`, `' "off" '`, `" 'off' "`. This diff's stated purpose was eliminating exactly this disagreement.

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:835

**`shim/claude_openai_shim.py:835`** — a comma-only `SHIM_WAKE_PHRASES=","` passes the `not WAKE_PHRASES.strip()` guard, then the generator at `:826` yields no alternatives, producing `(?:)` — an empty group matching at any sentence boundary. Verified: `is_addressed("what is the weather")` returns `True`. Fails **open**, opposite the documented "fail quiet" contract. The bot's `.filter(Boolean)` yields `[]` and returns `True` too, so both fail open — but the bot's is intentional, the shim's is an accident.

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:832

**`shim/claude_openai_shim.py:832`** — `\b` after the phrase alternative makes a configured wake phrase ending in punctuation (`ok google?`) permanently unmatchable. Defaults are word-final so it only bites user config.

### run 1 — discord-assistant#5 — src/voice.js:555

**`src/voice.js:555`** — `config.interruptResponse` is read per-event locally but sent **once** on `open` at `:336`. The two interrupt paths the changelog says were unified can still diverge if config mutates between connect and event. Capturing once and using it for both would make the guarantee structural. *(rule: `node/architecture/inject-dependencies`)*

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:1980

**`shim/claude_openai_shim.py:1980`** — comment references `# Design` / "What still needs deciding during implementation", which resolves against the authoring task file and ships nowhere. The rationale is already in the same sentence. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — discord-assistant#5 — CHANGELOG.md:3

**`CHANGELOG.md:3`** — `changelog/preamble-frozen` fires on `## Unreleased`, but the base branch has no preamble at all and every existing `## vX.Y.Z` heading fires identically. Repo-wide pre-existing, not caused by this diff — fix separately. *(rule: `changelog/preamble-frozen`)*

### run 1 — tts-mcp#13 — src/server.py:353

**`src/server.py:353`** — `say()` queues `WorkItem(instruct=body.instruct)` without checking whether the configured engine supports `instruct`. `POST /say` returns `202 Accepted` for an input that is guaranteed to fail, and per the finding above the failure is then mis-reported as success. Request-boundary validation is the same fix as above.

### run 1 — tts-mcp#13 — src/tts/generate.py:56

**`src/tts/generate.py:56`** — `generate_chunks` takes `streaming_interval` purely to satisfy the shared engine call signature, and ignores it in buffered mode (documented in the docstring). Not wrong, but a keyword-only param with a default would remove the need to thread `state.streaming_interval` through the buffered call sites.

### run 1 — github-releaser-agent#8 — pkg/githubtags/tags.go:33

**`pkg/githubtags/tags.go:33-47`** — the diff converted the interface's single doc block into per-method comments but deleted the doc for `LatestSemverTag` and the interface-level contract `// Implementations MUST be safe for concurrent use.` The interface method is now undocumented, and the concurrency guarantee is gone from the contract entirely (the impl-level doc at line 148 does not carry it). Re-add a comment above line 35 restoring both. *(rule: `go-doc/exported-item-must-have-comment`)*

### run 1 — github-releaser-agent#8 — specs/completed/002-planning-close-nothing-to-release.md:48

**`specs/completed/002-planning-close-nothing-to-release.md:48-62`** — all 15 acceptance-criteria boxes are still `- [ ]` although the file's frontmatter reads `status: completed`. Sibling completed specs use `- [x]`. The record reads as unverified. *(rule: `markdown-todo/lowercase-x-for-complete` — casing is compliant; this is about unticked state, not casing)*

### run 1 — github-releaser-agent#8 — specs/completed/002-planning-close-nothing-to-release.md:49

**`specs/completed/002-planning-close-nothing-to-release.md:49`** — cites "bug 048 at `pkg/steps_planning.go:624`"; that comment now lives at line 682 after this diff shifted it. Stale pointer in a shipped record.

### run 1 — github-releaser-agent#8 — pkg/steps_planning.go:750

**`pkg/steps_planning.go:750-753`** — `handleValidationFailure` takes 8 parameters. A domain-named single-caller method, so not a naive split, but bundling `owner/name/ref/effectiveVersion/reason/snapshotVersion` into a small input struct would make the decision contract explicit.

### run 1 — github-releaser-agent#8 — pkg/steps_planning.go:39

**`pkg/steps_planning.go:39`** — `releaseTagVerdictEscalate` is an untyped string const doubling as log token and branch value; it can drift from `PlanOutcomeNothingToRelease`. Folding it into a typed verdict enum would close that. *(rule: `go-enum-type/typed-constants-with-collection`)* *(same rule, same fix, `pkg/plan_output.go:111` — the new outcome joins a pre-existing untyped const block; the pattern predates this PR, so a follow-up introducing `type PlanOutcome string` for all four members is the right shape)*

### run 1 — github-releaser-agent#8 — pkg/githubtags/tags.go:176

**`pkg/githubtags/tags.go:176-178`** — `fetchPage` declares named results `tags []tagResponse, nextURL string` but the refactor now returns locals `tagEntries`/`next` explicitly; the names are documentation-only residue.

### run 1 — github-releaser-agent#8 — CHANGELOG.md

**`CHANGELOG.md` (git history)** — three of four commit subjects are non-imperative or bare slugs: `04f55d7 "specs: spec 002 transitioned to verifying"` (past tense), `75cde50 "005-spec-002-planning-nothing-to-release"` and `2312772 "004-spec-002-tag-commit-seam"` (no verb). These are dark-factory daemon-generated — the fix belongs in the daemon's commit-subject template, not a history rewrite (amending is banned). *(rule: `git-commit/imperative-mood`)*

### run 1 — discord-assistant#1 — scripts/supervise.sh:35

**`scripts/supervise.sh:35-44`** — the documented "`2` = bad config, give up" contract is incomplete. `config.check()` (`src/config.js:65-71`) only tests that `DISCORD_TOKEN` is *present* and `ALLOWED_USER_IDS` is non-empty; a revoked or syntactically invalid token passes validation, then `client.login()` (`src/index.js:283`) rejects with no handler → `unhandledRejection` → `process.exit(1)` (`src/index.js:234`) → restart loop forever at the 60s cap. Reproduced: a child exiting 1 spins indefinitely; only exit 2 gives up. The exact scenario the CHANGELOG says backoff exists to stop ("token revoked") is the one case backoff cannot fix.

### run 1 — discord-assistant#1 — src/index.js:272

**`src/index.js:272-277`** — `gatewayReady = false` is applied unconditionally to any exception matching `RECOVERABLE_NET`, but that regex also matches failures from non-gateway subsystems (the shim/LLM HTTP client, the speech-to-speech `ws`). `gatewayReady` is only restored by `clientReady`/`shardResume`/`shardReady` (`src/index.js:76,110,113`) — none of which fires for an LLM or s2s fault. Readiness therefore latches at 503 permanently while the bot is healthy, and `/healthz` still returns 200 (`src/health.js:29`), so neither k8s nor the supervisor intervenes. The in-code comment "Readiness already reports the disconnect" assumes the exception implies a gateway disconnect; it does not. Gate the flag on an actual shard event rather than a message regex.

### run 1 — discord-assistant#1 — scripts/supervise.sh:14

**`scripts/supervise.sh:14,50-51`** — `delay` only doubles and clamps; nothing resets it to `DELAY_MIN`. Verified: 1→2→…→60, and the restart following an arbitrarily long healthy run still uses 60s. This is precisely the 2026-08-05 scenario — a bot that ran fine for eight hours then died — so recovery after the documented incident is delayed by up to a minute. Reset on a long-lived run.

### run 1 — discord-assistant#1 — CHANGELOG.md:5

**`CHANGELOG.md:5`** — the new `## Unreleased` bullet begins `- Survive a gateway network fault…` with no conventional prefix; the rule requires `feat:`/`fix:`/`refactor:`/`test:`/`docs:`/`chore:`/`perf:`. Missing prefix degrades release-version detection. The pre-existing entries at lines 24 and 50 share the flaw, but consistency with an existing violation does not clear the MUST. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — discord-assistant#1 — scripts/supervise.sh:27

**`scripts/supervise.sh:27-28`** — narrow race: a signal landing between `"$@" &` and `child=$!` runs `stop()` with `child=""`, so the supervisor exits 0 while the just-started child survives.

### run 1 — discord-assistant#1 — scripts/supervise.sh:21

**`scripts/supervise.sh:21-22`** — single SIGTERM with no wait or `kill -KILL` escalation; a TERM-ignoring child is orphaned. For `node` this is not practical (it handles SIGTERM), but the supervisor exits before node's ~600ms graceful shutdown finishes.

### run 1 — discord-assistant#1 — scripts/supervise.sh:27

**`scripts/supervise.sh:27`** — no `$#` guard: invoking with no command prints "exited cleanly, not restarting" and exits 0 instead of a usage error.

### run 1 — discord-assistant#1 — src/index.js:263

**`src/index.js:263`** — a second `client.once('clientReady')` listener duplicates the one at `src/index.js:75`; `connectedOnce = true` belongs in the existing handler.

### run 1 — helm#3 — charts/github-pr-reviewer/values.yaml:54

**`charts/github-pr-reviewer/values.yaml:54-60`** — the comment narrates the change rather than describing the chart. "Trusted because its PRs are mechanical…", "the repo gate runs twice in-pod plus CI", "so this risk argument does not transfer" is trust-decision rationale: it answers why this entry was added, not what the chart does. Lines 50–53 (match semantics, `<slug>[bot]` form, routing to `human_review`) are legitimately behavioural and should stay; the per-bot rationale belongs in the chart README or the PR description. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — helm#3 — None

**commit `e634f85`** — subject `trust ben-s-go-updater[bot] in github-pr-reviewer TRUSTED_AUTHORS` is 65 chars, over the 50-char cap, and wraps in `git log --oneline` and PR list views. e.g. `trust update-go bot in TRUSTED_AUTHORS`. *(rule: `git-commit/subject-under-50-chars`)*

### run 1 — helm#3 — charts/github-pr-reviewer/values.yaml:61

**`charts/github-pr-reviewer/values.yaml:61`** — trust is keyed solely on author login, but the safety property the comment relies on ("go.mod/go.sum + CHANGELOG bullet, no code") is not enforceable by the chart. If that App's workflow changes or its token is compromised, arbitrary diffs reach the auto-review path. Impact is bounded to wasted agent review and a bot-posted review, not a merge. Enforce it outside the comment — branch protection requiring human approval, or a watcher-side path filter.

### run 1 — helm#3 — charts/github-pr-reviewer/values.yaml:61

**`charts/github-pr-reviewer/values.yaml:61`** — `values.schema.json` types `env` as free-form strings, so nothing forbids whitespace in `TRUSTED_AUTHORS`. A future edit to `bborbe, ben-s-go-updater[bot]` silently narrows trust if the consumer does not trim. Failure direction is fail-safe (a miss routes to `human_review`), but it is silent. Add a `pattern` forbidding whitespace, or document the no-space contract in the chart README.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler.go:312

**`pkg/spawner/service_reconciler.go:312`** — `sort.Strings(keys)` where `go.mod` is at `go 1.27.1`, so the generic `slices.Sort` is the modern idiom and drops the new `sort` import. `docs/go-factory-pattern.md:157` still shows `sort.Strings`, so this is a style preference, not a convention violation.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler.go:303

**`pkg/spawner/service_reconciler.go:303`** — the five-line in-function comment justifying the *absence* of a `ctx.Done()` check is defensible (a `ctx` parameter on a pure render would have nothing to observe, and documenting a deliberate deviation at the site is what a SHOULD-level rule expects), but it reads as rebuttal rather than documentation. One line — "pure render over an in-memory map; no cancellation point" — carries the same information.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:214

**`pkg/spawner/service_reconciler_test.go:214`** — the identical four-entry `multiEnv.Env` literal is repeated verbatim at `:214`, `:260`, `:281`, `:303`. Hoisting one into the outer `Describe` removes ~16 duplicated lines; four copies will drift.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:223

**`pkg/spawner/service_reconciler_test.go:223`** — the "reconcile N times, collect distinct orderings" loop is duplicated at `:223`, `:249`, `:340`. A `renderOrderings(conf, cfg, n)` helper removes three copies and makes the assertion intent obvious.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:259

**`pkg/spawner/service_reconciler_test.go:259`** — "byte-identical pod template across two consecutive reconciles" is real but weak as a guard: pre-fix, two consecutive ranges over a 4-key map agree ~44% of the time (4 distinct rotations, base order 62.5%, consecutive-match 43.8%), so this spec passes on the buggy code nearly half the time. The50-reconcile loop at `:223` covers this properly.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:280

**`pkg/spawner/service_reconciler_test.go:280`** — same two-draw weakness: `Expect(after.Env).To(Equal(before.Env))` passes pre-fix ~44% of runs. The `after.Image != before.Image` half is tautological with respect to this fix (the image changed either way).

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:302

**`pkg/spawner/service_reconciler_test.go:302`** — same two-draw weakness: `envNames(after) == envNames(before)` passes pre-fix ~44%. `after != before` and the `ContainElement(MODEL=opus)` check hold regardless of the fix.

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:120

**`src/vault_ui/pane_resolver.py:120`** — `env["PATH"] = str(bin_dir) + os.pathsep + env["PATH"]` indexes `PATH` unconditionally, raising `KeyError` when the environment has none. The call site at `:180` sits inside a `try` that catches only `OSError` (`:182`), so the exception escapes `resolve_pane_id` — breaking the module's stated contract ("Returns `None` for every failure") on the HTTP request path. This is exactly the launchd-adjacent stripped-environment case the change targets. The same line also yields a trailing `:` when `PATH` is empty, putting the child's working directory on its own search path. Suggested fix: ```python current = env.get("PATH") env["PATH"] = str(bin_dir) if not current else str(bin_dir) + os.pathsep + current ```

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:94

**`src/vault_ui/pane_resolver.py:94`** — `(_WEZTERM_BUNDLE_DIR / "wezterm").exists()` is true for a *directory* named `wezterm`; the function's contract is "directory holding the `wezterm` executable". `.is_file()` states that intent and fails closed. Low impact given the fixed bundle path.

### run 1 — vault-ui#94 — CHANGELOG.md:7

**`CHANGELOG.md:7`** — the bullet names no exact artifact (`pane_resolver.py`, `_subprocess_env`) while sibling entries do (`v0.73.0` names `POST /api/tasks/{task_id}/jump`). Weaker grep-ability against the actual change.

### run 1 — ai-assistant#111 — src/llm.js:32

**`src/llm.js:32`** — `hasCredential()` accepts a whitespace-only `OPENAI_API_KEY` as a real credential. It tests `config.apiKey !== 'not-needed'`, but `src/config.js:67` builds `apiKey` as `process.env.OPENAI_API_KEY || 'not-needed'` — **untrimmed**, unlike `chatBridgeToken`, which is `.trim()`ed at `src/config.js:202`. So `OPENAI_API_KEY=' '` is truthy, is not the sentinel, passes the guard, and `chat()` fetches with `Authorization: Bearer `. This contradicts the guard's own stated invariant ("never fetch a turn without a credential"). *Impact is bounded, not a security bypass*: the shim's `compare_digest` refuses it, and the new 401→`permanent` path then acks rather than looping — the cost is one wasted request and a confusing "misconfigured" notice. Empty-string and unset both fail closed correctly (`||` maps them to the sentinel), and a literal `'not-needed'` also fails closed. Fix: normalize at read — `apiKey: (process.env.OPENAI_API_KEY || '').trim() || 'not-needed'` — plus one test asserting `' '` rejects and touches the network zero times. *(rule: `go-security/insecure-defaults`)*

### run 1 — claude-supervisor#91 — scripts/manager-predispatch.py:557

**`scripts/manager-predispatch.py:557`** — the three-state `is False` / `is not False` semantics are entirely unpinned. **Proven by reversion experiment:** reverting all three consumer sites (`:557`, `:599`, `:710`) back to plain truthiness in a scratch copy leaves **90/90 tests green**. No test anywhere constructs `alive=None` — the only `alive` values in `test_manager_predispatch.py` are `True` (lines 1063-1064). This is the safety-critical half of the fix: a reverted `liveness_of_sid` reads UNKNOWN as dead, falls through to `LIVENESS_NONE`, and the auto-resume gate then resumes onto a live conversation — with nothing red.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:180

**`scripts/session-liveness.py:180-184`** — the per-pid `ps` retry is load-bearing and untested. Verified `ps` genuinely fails all-or-nothing (`ps -p $$,999999` → exit 1, "process id too large", **no rows**; `_ps_starts([good, 999999])` → `{}`), and the retry genuinely recovers (`_live_start_epochs` → `{53587: 1792346428}`). But `grep` finds **zero** test references to `_ps_starts`, `_live_start_epochs`, or an oversized pid. Deleting the retry loop reintroduces the whole-registry UNKNOWN the docstring warns about, with all 33 tests still green.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:143

**`scripts/session-liveness.py:143-150`** — unguarded subprocess: no `timeout=`, `check=False` with the return code never inspected, and `OSError` swallowed to `{}` with no diagnostic. Separately, `text=True` decodes with the locale encoding and raises `UnicodeDecodeError` — a `ValueError`, **not** caught here — straight out of `read_registry`, which `who-needs-me.py`, `manager-predispatch.py` and `approved-not-started.py` all import on every invocation.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:409

**`scripts/session-liveness.py:409`** — the UNKNOWN message misattributes every failure to the record. `_pid_identity` (`:199-204`) collapses three distinct causes into `None` — absent `procStart`, `ps` not reporting the pid, and `ps` failing outright — and all three render as "the record carries no usable procStart". A sandboxed or missing `ps` therefore reads as registry-data corruption and sends the operator to the wrong place.

### run 1 — claude-supervisor#91 — scripts/transport-read-check.py:50

**`scripts/transport-read-check.py:50`** — `_ps_starts` was registered in `SITE_LIST` but **not** in `accessors` (`:175-181`), so the file's own assertion — *"broken must be `None`, never an empty container"* (`:190-198`) — never runs against it. By inspection this is determinate: `_ps_starts` returns `{}` on `OSError` and `{}` when healthy-empty, so adding it to `accessors` would fail the check. The site is registered for completeness but exempted from the very guarantee the checker exists to enforce.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:159

**`scripts/session-liveness.py:159-163`** — `ps -o lstart=` is `LC_TIME`-localized, but the subprocess inherits the ambient environment and the parse uses the fixed English `_CTIME_FMT`. A non-English locale silently turns **every** record UNKNOWN — a total, quiet degradation. `env={**os.environ, "LC_ALL": "C"}` removes the class. Same applies to both test helpers.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:286

**`scripts/session-liveness.py:286-289`** — the split identity pass can produce a hybrid record on a sessionId collision. **Verified** with controlled glob order: `out[sid]`'s `pid`/`name`/`status` come from the last file read, while `alive` is written from whichever `occupied` tuple came last — a *different* file. Observed `{pid: <dead>, name: "B-dead", status: "idle", alive: True}`. A caller trusting `alive` and then acting on `rec["pid"]` would target a dead pid. Pre-change code derived `alive` from the same file as `pid`, so this is newly introduced; requires a collision, which this repo guards against elsewhere (`restart-worker.py`), hence Optional.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:492

**`scripts/session-liveness.py:492`** — `--list --json` emits `state: "live"` for entries `resolve()` classifies UNKNOWN. The `alive` normalization is justified in the comment; `state` still overclaims what the probe knows.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:187

**`scripts/session-liveness.py:187-198`** — `pidDomain` (present on every live record, currently `darwin`) is ignored, so a non-local pid domain would be compared against the local `ps`.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:66

**`scripts/session-liveness.py:66`** — `[[A Substring-Matched Liveness Probe Reports a Dead Session as Live]]` resolves to nothing in-tree; `grep -rl` finds only the two citations, and no such file ships. Same link at `scripts/tests/test_session_liveness.py:219`. The sentences around it already state the rationale standalone. *(rule: `self-containment/no-planning-doc-refs`)*

### run 1 — claude-supervisor#91 — scripts/tests/test_session_liveness.py:54

**`scripts/tests/test_session_liveness.py:54-71`** — `live_proc_start` re-implements production's parse + zone conversion rather than deriving from it, so a zone bug in `_ps_starts` would be mirrored by the fixture and both suites would still pass. This is precisely the failure class the CHANGELOG warns about. Duplicated again at `scripts/tests/test_manager_predispatch.py:31-49`.

### run 1 — claude-supervisor#100 — CHANGELOG.md:120

**`CHANGELOG.md:120`** — the new `## Unreleased` section was inserted mid-file, between `## v0.87.5` and `## v0.87.4`, while the base branch already carries an `## Unreleased` at line 11 with 2 bullets. The base advanced two commits past the merge-base (`40fd833e` → `a21f1e93`), one of which added that top section, so this PR developed blind to it. On merge the file has **two** `## Unreleased` sections; `check-changelog.py:49` uses `re.search` and reads only the first, so this entry never reaches a release. `make precommit` passes anyway because the checker enforces existence, not position or uniqueness. Move the bullet into the existing top `## Unreleased` above `## v0.94.0`.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:54

**`scripts/voice-ask-pairing.py:54-55`** — `_is_post` matches substrings, not the subcommand. `grep -rn 'attention-ask.py post' docs/`, `echo 'attention-ask.py post'`, and `answer … --note "the post was posted"` all return `True`, so a command that merely *mentions* the post satisfies the pairing rule and reports a missing card as paired. Verified end-to-end. This is a silent false negative in the one direction the detector exists to catch; three separate owners flagged it independently. Fix: `re.search(r"attention-ask\.py\s+(post|post-batch)\b", command)`.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:63

**`scripts/voice-ask-pairing.py:63-64`** — `except OSError: return [], []` makes a typo'd path, a permission error, or a directory indistinguishable from a clean scan. Verified: `voice-ask-pairing.py /tmp/does-not-exist-xyz.jsonl` prints `questions=0 paired=0 unpaired=0` at exit 0. Report the failure and exit non-zero.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:73

**`scripts/voice-ask-pairing.py:73`** — `(record.get("message") or {}).get("content")` assumes dicts. A record whose `message` is a string raises `AttributeError`, aborting the whole run and discarding every other file's results — against the docstring's "Exit 0 always" contract. Verified (the owner's original repro is caught by the line prefilter; a `message` string on a line containing `mcp__tts__say` does crash). `main()` needs a per-file guard too.

### run 1 — claude-supervisor#100 — docs/voice-asks.md

**`docs/voice-asks.md`** — declared canonical in `CLAUDE.md:129` and the CHANGELOG, but absent from both indexes that enumerate every other doc: `README.md:243-245` and `llms.txt:13-18`.

### run 1 — claude-supervisor#100 — scripts/tests/test_voice_ask_pairing.py:47

**`scripts/tests/test_voice_ask_pairing.py:47-101`** — every test drives `scan()`/`is_question()` directly; `main()` is never invoked, so both behaviours documented only there ("Exit 0 always", the `--json` payload shape) are untested, as are the missing-path, malformed-JSON, missing/invalid-timestamp and non-dict paths — the four that would have caught the three findings above.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:97

**`scripts/voice-ask-pairing.py:97`** — `os.path.getmtime` unguarded; a file removed between `glob` and stat aborts the default scan.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:89

**`scripts/voice-ask-pairing.py:89-90`** — one `post` pairs every question within ±60 s (two questions5 s apart, one card → `unpaired=[]`); neither documented nor tested.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:49

**`scripts/voice-ask-pairing.py:49`** — `_ts` assumes `timestamp` is a str; a numeric one raises. Same crash class as above.

### run 1 — claude-supervisor#100 — commands/worker-drive.md:512

**`commands/worker-drive.md:512-513`** — two consecutive blank lines after the inserted rule line.

### run 1 — claude-supervisor#100 — commands/fleet-loop.md:35

**`commands/fleet-loop.md:35`** — the ⚠️ line lands before the command's opening objective; `worker-drive.md:511` places the same line correctly inside its voice section. Same at `manager-loop.md:44` and `manager-drive.md:20`.

### run 1 — claude-supervisor#100 — docs/voice-asks.md:10

**`docs/voice-asks.md:10,16`** — docs name only `attention-ask.py post`, but the detector also accepts `post-batch` (asserted at `scripts/tests/test_voice_ask_pairing.py:74-77`).

### run 1 — claude-supervisor#100 — scripts/tests/test_voice_ask_pairing.py

**`scripts/tests/test_voice_ask_pairing.py`** — wired into `make test` but not into CI: `ci.yml` runs `make precommit`, which omits `test`. Pre-existing, but this suite will never run automatically.

### run 1 — claude-supervisor#85 — server/spawn-mode.mjs:176

**`server/spawn-mode.mjs:176`** — the new `unset → DEFAULT_MAX_CONCURRENT (20)` default was not propagated to three surfaces that still assert the old contract, one of them an operator-facing instruction the spawner emits at the cap: `server/supervisor.mjs:760` tells the operator *"Raise spawn.maxConcurrent … or **remove the key for unlimited**"* — removing the key now yields 20, not unlimited, so following the message does not do what it says; `server/config.mjs:102` still reads *"Unset means unlimited, which is the shipped state — see resolveMaxConcurrent"*; `README.md:115` still reads *"It ships empty, and empty means unlimited … Nothing here invents a number on the operator's behalf — set one when load demands it, and `0` is accepted as the same answer"*. The CHANGELOG entry's stated rationale is that the reversal must not be "left with both statements standing" — these are exactly those statements, one of them in the user-facing README and one in the refusal text a blocked manager prints. This is the defect class the new `check-worker-target.py` exists to prevent, and the check's own scope (`commands/`, `agents/`) does not cover any of the three.

### run 1 — claude-supervisor#85 — commands/fleet-loop.md:223

**`commands/fleet-loop.md:223`** — the prescribed count `python3 $P/live-workers.py --list | wc -l` does not produce the count it claims, in both of its edge cases (measured):

### run 1 — claude-supervisor#85 — commands/manager-loop.md:259

**`commands/manager-loop.md:259`** — the `under-target` branch's trigger half (a) reads the live count through the same `live-workers.py --list | wc -l` pipeline, so the branch that decides whether to post a card inherits both miscounts above: an idle fleet reads as1 live, and an unreadable store reads as 0 and therefore "below target", which is the one reading `docs/fleet-surface.md:174` explicitly forbids (*"an unreadable store is `UNKNOWN`, never `0`"*).

### run 1 — claude-supervisor#85 — docs/fleet-surface.md:176

**`docs/fleet-surface.md:176`** — the bullet claims `scripts/live-workers.py` is "the read half of `server/heartbeat.mjs`", but the two readers disagree on one case (measured): a stale stamp whose `source` is `cluster` and whose cluster marker is unreachable is counted by `live-workers.py` as live with `state: unknown`, while `server/heartbeat.mjs` `listLive()` drops it entirely (node reported length 0, python listed 1 on the same store). So the number a manager prints and proposes against can exceed the number `spawnAgent` enforces — the "two counters that cannot be told apart" drift this change was built to remove, re-entering through the reader rather than the number.

### run 1 — claude-supervisor#85 — scripts/check-worker-target.py:119

**`scripts/check-worker-target.py:119`** — assertion (b) checks only that a referencing file *carries* `Spawn a worker item 5`, never that it does not also carry its own copy of the number. Verified: a file containing both `Respect \`spawn.maxConcurrent\` (default 20)` and the pointer passes clean. The docstring and the CHANGELOG entry both state the stronger contract ("carries a **pointer** to it rather than its own copy of the number"), so a future edit that adds the number next to an existing pointer is not caught. The test fixture `SITE_RESTATES` fails for the missing pointer, not for the restatement, so no test covers the both-present case either.

### run 1 — claude-supervisor#85 — server/spawn-mode.mjs:176

**`server/spawn-mode.mjs:176`** — because the default is now non-null, the `live === null` refusal in `server/supervisor.mjs:746` (refusing to spawn past a limit it cannot count) is reachable on a **default install with no config at all**, where it previously could not fire — under the old contract an unset key short-circuited the whole block. The common fresh-install path is safe (`readdirSync` ENOENT returns `[]`, not `null`), so this only bites when the heartbeat directory exists and is unreadable; the blast radius is "every spawn refuses with a `SUPERVISOR_HEARTBEAT_DIR` message" on an install that never asked for a limit. Worth a sentence in the CHANGELOG noting the new default makes a fail-closed path default-reachable.

### run 1 — ai-assistant#107 — test/test_shim.py

**`test/test_shim.py`** — `make precommit` is red: 4 of 200 Python shim tests fail (`is_barge_in_off` returns `True` where `False` is expected; `interrupt` reports `False` where `True` is expected). **Pre-existing, not introduced by this diff** — reproduced identically at base commit `ea788fd` in a clean worktree. The Node suite is green (`# fail 0`). Does not block this PR; needs its own task, since it leaves `main` red independently.

### run 1 — ai-assistant#107 — src/gchat.js:197

**`src/gchat.js:197-205`** — the refusal branch inherits the shared reply-then-ack contract, so a *permanently* failing `postChatReply` (403 — app removed from the space; revoked SA credentials) hits the catch at `:219-222` and calls `message.nack()`. There is no dead-letter or delivery-attempt bound anywhere in the repo (verified: the only `maxAttempts` is unrelated, `voiceRejoinMaxAttempts`), so Pub/Sub redelivers for the full retention window while `flowControl: { maxMessages: 1 }` (`:174`) serializes the subscription — one poisoned message starves every allowlisted user's turns. The documented rationale for nacking ("visible duplicates rather than silent drops") does not extend to a refusal: no work was executed, so there is nothing to preserve. Ack the refusal regardless of post success, or bound the attempts.

### run 1 — ai-assistant#107 — test/gchat.test.js:88

**`test/gchat.test.js:88-115`** — the additions thoroughly exercise `isAllowedSender` (unset, empty, listed/unlisted, case in both directions, missing sender) but **not the gate's placement in `startGchat`**. Nothing asserts that a refused sender never reaches `chat()`, that `REFUSAL_TEXT` is posted, or that the message is acked. Verified: no test file references `startGchat`, `postChatReply`, `message.ack`, or the handler. Moving `const allowed = isAllowedSender(...)` below `await chat(...)`, or dropping the `return` at `:204`, passes all 34 tests. This wiring is the control standing between an outsider and a vault-reading session.

### run 1 — ai-assistant#107 — src/gchat.js:117

**`src/gchat.js:117-123`** — `isAllowedSender` reads module-level `config` rather than taking the list as a parameter, which is what forced the require-cache surgery in `test/gchat.test.js:80-86` (reloading both modules because `gchat` captures `config` at load). *(rule: `node/architecture/inject-dependencies`)*

### run 1 — ai-assistant#107 — src/gchat.js:102

**`src/gchat.js:102-103`** — `REFUSAL_TEXT` hardcodes a personal name, which goes stale on reassignment and discloses the operator to anyone who can reach the space. It is also a dead export: `REFUSAL_TEXT` is never imported outside `gchat.js`. Consider a team/role reference and drop the export unless a test asserts on it.

### run 1 — ai-assistant#107 — src/config.js:123

**`src/config.js:123`** — `GCHAT_ALLOWED_EMAILS` is undocumented: it appears in neither `README.md` nor `local.env.example`. Verified, no `GCHAT_*` variable is documented in either — so an operator enabling `GCHAT_ENABLED=1` has no documented way to discover the required variable.

### run 1 — ai-assistant#107 — src/config.js:54

**`src/config.js:54-59`** — `list()` does not strip surrounding quotes, unlike `flag()` (`:16-18`) and `wakePhrases` (`:232-236`), which both document why: the Makefile's `-include local.env` parses with MAKE semantics, so `export X="a"` arrives with quotes attached. Downgraded from the agent's rating — the process is actually fed by `make run` → `set -a; . ./local.env` (shell sourcing), which strips them itself, so the primary path is clean. Fails closed, and `allowedUserIds` shares the flaw; only reachable via the make-include path.

### run 1 — agent-claude#20 — main.go:246

**`main.go:246`** — `interactive.NewServiceWithPermissions` mounts a `/permission` route that the v0.93.0 source itself documents as *"unauthenticated and reachable by anything in the namespace"* (`interactive/permission-handler.go:16`). `POST` resolves a pending request by body-field `id` with no authn and no ownership check, so any caller reaching `LISTEN` (default `:9090`, all interfaces) can post `{allow:true}` and approve a tool invocation the allowlist would have denied. This flips the previous fail-closed behavior — a non-allowlisted tool failed the turn loudly — into fail-open: the allowlist stops being an enforcement boundary. `GET` additionally discloses `tool_name`, `description` and `input_preview` per pending request. Fix: keep the nil decider + `NewService` until an auth layer exists, or wrap the handler in bearer/mTLS auth middleware and bind `LISTEN` to loopback plus a NetworkPolicy admitting only the intended caller. *(rule: `go-security/resource-ownership`)*

### run 1 — agent-claude#20 — pkg/factory/factory_test.go:137

**`pkg/factory/factory_test.go:137`** — the only test change is a sixth `nil` argument. The spec still asserts `NotTo(BeNil())`, so it passes identically whether `CreateClaudeSessionFactory` forwards the caller's decider into `claudelib.NewSessionFactory` or silently drops it — exactly the regression this PR fixes. No spec exercises a non-nil `PermissionDecider`. Fix: assert the observable seam (`--permission-prompt-tool stdio` in the spawned argv via a fake `claude` on PATH), or extract the config+decider assembly into an unexported helper and unit-test it as `main_internal_test.go` does for `buildClaudeEnv`. *(rule: `tdd/failing-test-before-implementation`)*

### run 1 — agent-claude#20 — main.go:237

**`main.go:237`** — the new comment claims one registry instance is handed to both consumers, but no test asserts either consumer receives a non-nil registry, let alone the *same* one. The existing `runService` spec only checks lifecycle, so it stays green if the wiring is reverted to nil or if two registries are constructed at the two call sites — the symptom this PR exists to fix. Fix: bind a free port, start `runService`, assert `GET /permission` returns `200 []`; pointer-identity needs a seam (inject the registry into `runService` or extract the wiring). *(rule: `tdd/failing-test-before-implementation`)*

### run 1 — agent-claude#20 — go.mod:93

**`go.mod:93`** — `govulncheck` + `trivy`: `golang.org/x/net v0.58.0` carries 5 reachable CVEs, incl. **HIGH** CVE-2026-78669 (HTTP/2 SETTINGS-frame DoS), fixed in v0.60.0; reachable via the HTTP/2 server at `main.go:48`. Pre-existing — the base commit already pinned v0.58.0; only `github.com/bborbe/agent` moved. Material because this diff widens exposure of the same server. Fix: `go get golang.org/x/net@v0.60.0 && go mod tidy`.

### run 1 — nuke#357 — agent/Makefile:137

**`agent/Makefile:137`** — the new `agent-claude:v0.4.0` mirror entry is the only current pin in `MIRROR_IMAGES` with no rationale in the comment block directly above the list. Every other live pin is narrated there (`agent-claude:v0.2.6` at line 99, the `agent-pi` v0.4.x chain at lines 103–127, plus the "these two must move together" invariant at lines 128–133 that this very change exercises). The next reader bumping this tag has no in-place record of what v0.4.0 bought. The rationale exists in `CHANGELOG.md`, which is the weaker location for it.

### run 1 — git-ai-sync#16 — entrypoint.sh:64

**`entrypoint.sh:64-75`** — the restart loop re-enters `watch` on a still-conflicted tree. `resolve` exits 1 on any failure (Claude error, unresolvable file, `__main__.py:426/432/436/446`) and leaves the repo in `MERGE_HEAD`/rebase state. The loop then sleeps 5 s and starts `watch` again, and `cmd_watch` has **no** conflict-state guard — `is_in_conflict_state` is only checked in `cmd_resolve` (`__main__.py:410`). On its next iteration `watch` does `has_changes` → `git add .` (`git_operations.py:73`) → `git commit -m` (`:97`); `git add .` resolves the unmerged index entries and the merge commit lands with `<<<<<<<` markers in the content. `commit_with_marker_recovery` (`conflict_resolver.py:289`) only saves this if the *vault* repo has a marker-refusing pre-commit hook installed — nothing in this image installs one. Gate the restart on real git state (`git rev-parse --verify MERGE_HEAD`, `rebase-merge`/`rebase-apply`) and `merge --abort`/`rebase --abort` + `exit 1` when resolution fails, instead of resuming.

### run 1 — git-ai-sync#16 — Dockerfile:75

**`Dockerfile:75`** — `ENV HOME=/tmp` contradicts the SSH deploy-key mount described at `Dockerfile:71` (`/home/node/.ssh`) and required by `:29`. OpenSSH resolves identity and `known_hosts` under `$HOME/.ssh` = `/tmp/.ssh`; no `GIT_SSH_COMMAND` or `core.sshCommand` redirects it. Either set `HOME=/home/node` and move the uv/git state to `/tmp` explicitly, or point SSH at the mount path. (Pod spec not in this diff — the contradiction between these two lines in the diff is the finding.)

### run 1 — git-ai-sync#16 — Dockerfile:16

**`Dockerfile:16-18`** + **`entrypoint.sh:19`** — the version banner can never print a real version. `BUILD_GIT_VERSION`/`BUILD_GIT_COMMIT`/`BUILD_DATE` are `ARG`s consumed only by the `LABEL`s; `ARG` values do not reach the runtime environment, so the container always logs `git-ai-sync dev (commit none, built unknown)`. Nothing in `Makefile` or `.github/workflows/` passes them either. Promote them with `ENV BUILD_GIT_VERSION=${BUILD_GIT_VERSION} …` after the tool install, or drop the line.

### run 1 — git-ai-sync#16 — entrypoint.sh:50

**`entrypoint.sh:50-53`** — `$VAULT/.git/info/exclude` assumes `.git` is a directory, but the `:22` guard is `-e`, which also passes when `.git` is a *file* (worktree/submodule pointer). The `echo >>` then fails silently and the log still claims "excluded", leaving `.git-ai-sync.lock` to be swept into the vault by the `git add .` the block exists to prevent. Use `git -C "$VAULT" rev-parse --absolute-git-dir`, `mkdir -p "$GIT_DIR/info"`, and only log success on a successful append.

### run 1 — git-ai-sync#16 — entrypoint.sh:10

**`entrypoint.sh:10,43-44`** — `export HOME="${HOME:-/tmp}"` inherits whatever the pod sets, and the two `git config --global` writes are unchecked with no `set -e`. Under `readOnlyRootFilesystem` with `HOME=/home/node` both writes fail and the script continues, deferring exactly the late "Please tell me who you are" failure that `:35-38` claims to prevent. Force `HOME=/tmp` and `|| { log "FATAL: cannot write git config"; exit 1; }` on each write.

### run 1 — git-ai-sync#16 — entrypoint.sh:57

**`entrypoint.sh:57-61`** — `stop()` kills the child and exits without waiting. `git-ai-sync` installs its own SIGTERM handler that exits 0 (`__main__.py:112-120`), but as PID 1 the shell's exit SIGKILLs whatever is left, potentially mid-commit or mid-push. Add `wait "$CHILD_PID"` after the `kill`.

### run 1 — git-ai-sync#16 — entrypoint.sh:56

**`entrypoint.sh:56,59,66-68`** — `WATCH_PID` is never cleared after `wait`, so a TERM arriving during a multi-minute `git-ai-sync resolve` signals a stale (possibly recycled) PID, and the resolve child itself is never signalled at all. Track one `CHILD_PID` set before both calls. (The `wait`/`rc=$?` pattern itself is correct — verified in dash.)

### run 1 — git-ai-sync#16 — Dockerfile:64

**`Dockerfile:64`** — `RUN npm install -g @anthropic-ai/claude-code` sits below `COPY src/` (`:53`) and `uv tool install .` (`:61`), so every code change re-runs it. It also floats unpinned, so two builds of the same commit get different CLI versions and conflict-resolution behaviour can drift. Move it above the source layers, pin a version, and `npm cache clean --force`.

### run 1 — git-ai-sync#16 — entrypoint.sh:13

**`entrypoint.sh:13-14`** — `INTERVAL`/`STRATEGY` are never validated. A typo makes `watch` exit 2 instantly (`--interval` is `type=int`, `--strategy` has `choices`) and the wrapper restarts it every 5 s forever — the opposite of the file's own fail-at-startup philosophy at `:35-38`.

### run 1 — git-ai-sync#16 — Dockerfile:80

**`Dockerfile:80`** — no `HEALTHCHECK`. The current design cannot distinguish "watch is running" from "restart-looping every 5 s" from outside the pod.

### run 1 — git-ai-sync#16 — Dockerfile:36

**`Dockerfile:36`** — `ghcr.io/astral-sh/uv:0.12.19` is a floating tag; pin by digest for reproducible builds (the base image at `:14` likewise).

### run 1 — git-ai-sync#16 — Dockerfile:66

**`Dockerfile:66-67`** — `COPY` + `RUN chmod` is two layers; use `COPY --chmod=0755`. Also `entrypoint.sh` is committed mode `100644`, so local execution is not executable.

### run 1 — git-ai-sync#16 — CHANGELOG.md:13

**`CHANGELOG.md:13`** — the bullet is a single ~800-character paragraph carrying implementation internals (`node:22-slim`, uv prefixes, `.git/info/exclude`). The prefix rule passes; the shape does not match `- <prefix>: <what> [context]`. Split into 2-3 short bullets.
