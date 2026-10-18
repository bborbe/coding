98ff1caaf435fd644d51c3d544f983f57a382e4faed0cbf5cedf3bb1e7fa6ed9

## Configuration
- model: MiniMax-M3.1-Flash-Preview[1m]
- effort: high
- mode: full
- config_hash: 98ff1caaf435fd644d51c3d544f983f57a382e4faed0cbf5cedf3bb1e7fa6ed9
- rules_commands_hash: d5da1b0377a19672f1286914db661c7c44e0121ddcfdc94ff887d16f52196856
- prs_version: curated-1
- coding version: 0.59.0
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
| 1 | 2026-10-18T08:37:22.649729+00:00 … 2026-10-18T11:56:17.392869+00:00 | 29/20 | partial | 148 | 185 | 14 | 113 | 0 | 171 | 0.110 | 1.000 | 12572 |

## Per-PR
| run | pr_id | golden in scope | hits | misses | findings | gap candidates | dropped items | missing sections | duration (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | tts-mcp#20 | 1 | 0 | 1 | 0 | 0 | 0 | — | 118 |
| 1 | github-pr-review-agent#11 | 16 | 1 | 13 | 4 | 3 | 0 | — | 321 |
| 1 | node-skeleton#2 | 12 | 1 | 11 | 2 | 1 | 0 | — | 595 |
| 1 | python-skeleton#3 | 17 | 3 | 13 | 12 | 9 | 0 | — | 387 |
| 1 | vault-cli#68 | 1 | 0 | 1 | 1 | 1 | 0 | — | 395 |
| 1 | backup#15 | 4 | 0 | 2 | 1 | 1 | 0 | — | 786 |
| 1 | bw#41 | 3 | 0 | 2 | 4 | 4 | 0 | — | 243 |
| 1 | dark-factory#71 | 2 | 0 | 2 | 4 | 4 | 0 | — | 465 |
| 1 | tts-mcp#16 | 6 | 0 | 5 | 7 | 7 | 0 | — | 240 |
| 1 | tts-mcp#3 | 6 | 1 | 4 | 8 | 7 | 0 | — | 147 |
| 1 | distill#6 | 10 | 1 | 6 | 12 | 11 | 0 | — | 243 |
| 1 | vault-ui#39 | 6 | 0 | 6 | 3 | 3 | 0 | — | 410 |
| 1 | recurring-task-creator#30 | 6 | 0 | 4 | 4 | 4 | 0 | — | 279 |
| 1 | tts-mcp#10 | 9 | 1 | 6 | 11 | 10 | 0 | — | 371 |
| 1 | discord-assistant#5 | 13 | 2 | 11 | 12 | 10 | 0 | — | 404 |
| 1 | tts-mcp#13 | 10 | 2 | 7 | 14 | 12 | 0 | — | 284 |
| 1 | github-releaser-agent#8 | 13 | 0 | 9 | 7 | 7 | 0 | — | 358 |
| 1 | discord-assistant#1 | 9 | 1 | 8 | 15 | 14 | 2 | — | 398 |
| 1 | helm#3 | 4 | 1 | 2 | 3 | 2 | 0 | — | 171 |
| 1 | agent-task-executor#67 | 0 | 0 | 0 | 7 | 7 | 2 | — | 227 |
| 1 | vault-ui#94 | 0 | 0 | 0 | 5 | 5 | 0 | — | 110 |
| 1 | ai-assistant#111 | 0 | 0 | 0 | 6 | 6 | 0 | — | 227 |
| 1 | claude-supervisor#91 | 0 | 0 | 0 | 10 | 10 | 0 | — | 188 |
| 1 | claude-supervisor#100 | 0 | 0 | 0 | 9 | 9 | 0 | — | 1275 |
| 1 | claude-supervisor#85 | 0 | 0 | 0 | 5 | 5 | 0 | — | 1041 |
| 1 | ai-assistant#107 | 0 | 0 | 0 | 6 | 6 | 0 | — | 1136 |
| 1 | agent-claude#20 | 0 | 0 | 0 | 4 | 4 | 4 | — | 726 |
| 1 | bw#49 | 0 | 0 | 0 | 0 | 0 | 2 | — | 297 |
| 1 | git-ai-sync#16 | 0 | 0 | 0 | 9 | 9 | 0 | — | 732 |

*Effective fixture: **29 of 20** PRs produced a scored row.* **10** findings carried no matching key and never reached scoring.

## Gap-triage candidates
These findings matched no golden entry. They are **not a precision failure** — the golden set is a bootstrap from one strong-model run, and a finding it does not describe is evidence the set is incomplete.

### run 1 — github-pr-review-agent#11 — cmd/run-task/main.go:125

**`cmd/run-task/main.go:125-138`** — `--skip-post` does not actually remove the GitHub dependency. Before `factory.RunAgent` is ever called, `Run` hard-fails without `APP_ID`/`INSTALLATION_ID`/PEM (`errors.Errorf(..., "GitHub App credentials not configured")`) and unconditionally calls `githubapp.MintIAT(ctx, appCfg)`, minting a **live installation token** against GitHub. A caller wanting a no-write local run still needs working GitHub App credentials and makes a real network call. Since the stated purpose is safe local runs against third-party PRs, consider short-circuiting auth resolution when `a.SkipPost` is set. *(not rule-derived)*

### run 1 — github-pr-review-agent#11 — pkg/factory/factory.go:188

**`pkg/factory/factory.go:188`** — the `ghTokenCheckStep` preflight (`GET https://api.github.com/rate_limit`, and `needs_input` on an empty token) is constructed inside `CreateAgent`, which `RunAgent` calls regardless of `SkipPost`. The three consumer guards (poster, verifier, dismiss) are all correctly gated, but this fourth GitHub-touching path is not. It is a *read*, so the documented "suppresses GitHub **writes**" claim still holds — the gap is that `pkg/skip_post_boundary_test.go:11-14` asserts no "live API read" under skip-post, which this path contradicts. Either gate the preflight on `SkipPost` or narrow that test comment. *(not rule-derived)*

### run 1 — github-pr-review-agent#11 — pkg/factory/runner.go:66

**`pkg/factory/runner.go:66`** — `ResolvePosters` is a non-`Create*` function with a config branch in `pkg/factory/`, nominally against `go-factory/no-impl-in-factory-pkg` (MUST). I rate this a rule-fit rather than a defect: `ResolveBotLogin` (same package, also a `Resolve*` helper with a conditional), `RunAgent`, and `deliverStartupFailure` all predate it, so the package already establishes this shape. Reported for rule-awareness only; no change recommended. *(rule: `go-factory/no-impl-in-factory-pkg`)*

### run 1 — node-skeleton#2 — package.json:26

**`package.json:26`** — the new `typescript-eslint@^8.66.0` devDependency pulls `@typescript-eslint/typescript-estree/node_modules/brace-expansion@5.0.9` (high). Adds one new vulnerable path to a tree that every cloned service inherits. Dev-only (`Dockerfile:8` runs `npm ci --omit=dev`, so it is absent from the runtime image). `npm audit fix` resolves it.

### run 1 — python-skeleton#3 — .github/workflows/ci.yml:33

**`.github/workflows/ci.yml:33`** — the apt source is built with `$(lsb_release -sc)`, i.e. the runner codename (`noble`). Since trivy v0.72.0 the official APT repo publishes only to the `generic` distribution; per-codename dists are frozen, so CI installs a scanner stuck at v0.71.2 and the step breaks outright once the codename dist is dropped. Fix: pin `deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main` and pin the package version. *(rule: `node/make/security-gates-in-check`)*

### run 1 — python-skeleton#3 — CHANGELOG.md:18

**`CHANGELOG.md:18`** — the bullet `- ci: install trivy in CI` uses prefix `ci:`, which is not in the recognised set (`feat:`/`fix:`/`refactor:`/`test:`/`docs:`/`chore:`/`perf:`). The version-bump parser matches the `^- ([a-z]+:)` shape but cannot classify the prefix, so the automated bump decision for this release breaks. Fix: `chore: install trivy in CI`. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — python-skeleton#3 — README.md:76

**`README.md:76-94`** — the new `## Security gates` section is contributor-operational meta, not user-facing content: severity-threshold policy, the `osv-scanner` exclusion rationale, the ruff suppression list, and the ignore-file convention are the class the README guide bans ("architecture internals, workflow rules"). The genuinely user-facing fact — that `make check` runs these gates — is already conveyed by the `make audit` / `make trivy` lines added at `README.md:70` and `README.md:73`. Fix: keep a one- or two-sentence statement, move the rationale to `CLAUDE.md`. *(rule: `readme/user-facing-not-agent-context`)*

### run 1 — python-skeleton#3 — README.md:86

**`README.md:86`** — garbled sentence: "to add a third advisory database **over ground** pip-audit and trivy already cover" does not parse; the preposition is missing its complement. Fix: "on top of the ground pip-audit and trivy already cover."

### run 1 — python-skeleton#3 — Makefile.precommit:55

**`Makefile.precommit:55-56`** — the comment claims that without `sync` "trivy finds no Python manifest and silently reports zero dependency vulnerabilities". `pyproject.toml` is tracked and always present, so trivy does find a manifest; the real failure is auditing the *unlocked* tree, not finding none. The `sync` dependency is still correct — only the stated reason is wrong. Same overstatement at `README.md:82`.

### run 1 — python-skeleton#3 — README.md:90

**`README.md:90-94`** — the cross-skeleton comparison table names two sibling internal repos (`go-skeleton`, `node-skeleton`) that are neither linked nor meaningful to a reader of `python-skeleton`, and its `python-skeleton` row duplicates the prose directly above it. The table's claims were verified accurate against the sibling repos — the issue is relevance, not correctness. Folds into the section-level fix above. *(rule: `readme/user-facing-not-agent-context`)*

### run 1 — python-skeleton#3 — README.md:69

**`README.md:69-73`** — `make audit` / `make trivy` are now documented twice (command block and the new section), the duplication the README guide warns about. *(rule: `readme/user-facing-not-agent-context`)*

### run 1 — python-skeleton#3 — README.md:76

**`README.md:76`** — the new section sits between `## Development` and `## Docker`, separating the dev commands from Docker usage; its heading case is also inconsistent with the repo's Title Case headings (`Quick Start`, `Development`, `Project Structure`).

### run 1 — python-skeleton#3 — README.md:90

**`README.md:90-94`** — the new table omits the leading/trailing pipes used by the two existing tables in this README (Endpoints at line 36, Configuration at line 46); renders fine, breaks visual consistency.

### run 1 — vault-cli#68 — CHANGELOG.md:13

**`CHANGELOG.md:13`** — the bullet's closing clause is a sentence fragment: "…and the repo no longer violates its own `docs/dod.md`" has no predicate. Add one (e.g. "…its own `docs/dod.md` rule against `exclude`/`replace` directives").

### run 1 — backup#15 — Makefile:127

**`Makefile:127`** — the rewritten `docker build` line passes only `--build-arg NPM_REGISTRY`; the three canonical provenance args (`BUILD_GIT_VERSION`, `BUILD_GIT_COMMIT`, `BUILD_DATE`) are absent from the whole service — no matching `ARG`/OCI `LABEL` in `Dockerfile`, no `-ldflags "-X"` wiring (the Go stage builds with `-ldflags "-s"` only). Images cannot answer which commit/when they were built. Pre-existing gap, flagged only because the diff rewrote this exact line. *(rule: `go-build-args/three-args-required`)*

### run 1 — bw#41 — groups/meta/k3s.py:7

**`groups/meta/k3s.py:7-10`** — the rationale comment states a mechanism that is not true on Linux: "`arp_tbl` is a single GLOBAL kernel table counting entries across every network namespace". `arp_tbl` is the FreeBSD sysctl name; Linux has no such global entry-counting table. Linux neighbour tables are **per network namespace** — each netns gets its own `neigh_table` whose `gc_thresh{1,2,3}` are copied from `net.ipv4.neigh.default.*` at creation. What is globally capped is the *number of tables* (`ip_neigh_table_max`), not entries across namespaces. The supporting inference is also internally inconsistent: under the "single global table" claim, the host's 404 entries against a 1024 default would mean the table was far from full, so the cited observation argues *against* the claim it is offered to support. Since this comment is the record a future maintainer will consult to decide whether to keep or revert these values, the wrong mechanism is worth correcting to what the evidence actually supports. No rule covers comment factual accuracy, so this is uncited.

### run 1 — bw#41 — groups/meta/k3s.py:22

**`groups/meta/k3s.py:22-24`** — `net.ipv4.neigh.default.gc_thresh{1,2,3}` is a **creation-time template**: Linux copies these into a namespace's `neigh_table` when the namespace is created and does not retroactively resize tables already running. Applying this changes only **newly created** pod namespaces; existing pods keep 128/512/1024 until they are recreated. The chosen lever is still the right one — `net.ipv4.neigh.<iface>.gc_thresh*` is not practical across hundreds of ephemeral veths — but the rollout caveat (pair with pod churn or a node reboot) and the per-netns semantics are the two facts a reader needs, and neither is stated. Reasoning is from kernel behaviour (`neigh_table_init` reads the `default/` values per netns), not live-verified — this macOS host has no Linux `/proc/sys` to check against.

### run 1 — bw#41 — groups/meta/k3s.py:22

**`groups/meta/k3s.py:22`** — `gc_thresh1` 128 → 4096 lets each table grow ~32× before aggressive GC begins, *per namespace*. On a node with hundreds of pod netns that raises the aggregate neighbour-entry memory ceiling. Not a defect, but an unremarked tradeoff; one line would do.

### run 1 — bw#41 — bundles/intellij/metadata.py:28

**`bundles/intellij/metadata.py:28-29`** — removes a blank line inside the `sysctl.options` dict; purely cosmetic, and it rides in a separate `fmt` commit alongside a functional k3s change in an unrelated bundle.

### run 1 — dark-factory#71 — CHANGELOG.md:15

**`CHANGELOG.md:15`** — the bullet says "each Blocker/Critical issue", but `Blocker` is not a severity level anywhere in this repo. `agents/prompt-auditor.md` defines exactly two tiers — `## Critical Issues` and `## Recommendations` — and `grep -rn "Blocker" agents/prompt-auditor.md` returns nothing. Prose-only drift; the mechanism the bullet describes is implemented correctly.

### run 1 — dark-factory#71 — agents/prompt-auditor.md:494

**`agents/prompt-auditor.md:494-496`** — the find/replace requirement is stated twice, here in `<output_format>` and again at `agents/prompt-auditor.md:514-518` in `<final_step>`. They agree today and drift is a maintenance risk only. This is not a `agent-cmd/single-source-of-truth` violation; that rule targets external data sources.

### run 1 — dark-factory#71 — CHANGELOG.md:15

**`CHANGELOG.md:15`** — the bullet says "each Blocker/Critical issue", but `Blocker` is not a severity level in this repo. `agents/prompt-auditor.md` defines exactly two tiers (`## Critical Issues`, `## Recommendations`), and `grep -rn "Blocker" agents/prompt-auditor.md` returns nothing. Prose-only drift.

### run 1 — dark-factory#71 — agents/prompt-auditor.md:494

**`agents/prompt-auditor.md:494-496`** — the find/replace requirement is stated twice, here and again at `agents/prompt-auditor.md:514-518`. The two agree today; this is drift risk, not a `agent-cmd/single-source-of-truth` violation (that rule targets external data sources).

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:14

**`skills/voice/SKILL.md:14`** — the Args line for `on` says it speaks "completion/failure events, decisions, and **`AskUserQuestion` prompts**", but the new capability table (`:71`) gives `on` → Every question "❌ decisions only" and the new attention-signals list (`:79`) says `say("Needs your input.")` — a generic signal, not the prompt text. The two descriptions of the same mode disagree about whether the question itself is read aloud. This is the exact two-sources-of-truth failure the diff set out to eliminate, relocated inside the file. Fix: narrow `:14` to the generic decision signal, or widen the table row. *(rule: `agent-cmd/single-source-of-truth`)*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:78

**`skills/voice/SKILL.md:78`** — new example `say("Build failed in capitalcom-gateway.")` names a project-specific internal service. Sole occurrence in the repo, introduced by this diff; the plugin ships to anyone. Use a generic name (`say("Build failed in the gateway service.")`).

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:8

**`skills/voice/SKILL.md:8`** — "there is no competing always-on rule in `~/.claude/CLAUDE.md`" trips the mechanical MUST rule `self-containment/no-home-dir-paths` (the guide's exemption list is closed and does not cover it). Low-impact — `~/.claude/CLAUDE.md` is Claude Code's documented user-memory path that exists on every install — but reword to "user-level CLAUDE.md memory rule" to clear the mechanical tier. *(rule: `self-containment/no-home-dir-paths`)*

### run 1 — tts-mcp#16 — CHANGELOG.md:16

**`CHANGELOG.md:16`** — same `~/.claude/CLAUDE.md` literal, same mechanical hit, same remedy.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:94

**`skills/voice/SKILL.md:94`** — same literal again, same remedy.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:14

**`skills/voice/SKILL.md:14`** — "`on` (**default**)" reads ambiguously against `:8`'s new "Voice is off until someone invokes `/voice`": the default *argument* is not the default *state*. Clarify to "(default when invoked with no arg)".

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — frontmatter Args list omits the `fix` alias documented at `:19`; minor summary drift after the description rewrite.

### run 1 — tts-mcp#3 — CHANGELOG.md:12

**`CHANGELOG.md:12`** — new `## Unreleased` bullet leads with a backticked path (`commands/voice-test.md`), not a conventional prefix, so the auto-release bump detector cannot classify it; this is a new capability and risks a patch bump. Use `- feat: Add /tts-mcp:voice-test …`. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — tts-mcp#3 — CHANGELOG.md:16

**`CHANGELOG.md:16`** — second bullet leads with `` `/tts-mcp:voice on` ``, same failure. Use `- refactor: Drop the startup selftest from /tts-mcp:voice on and interview`. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — tts-mcp#3 — commands/voice-test.md:18

**`commands/voice-test.md:18-23`** — the failure-triage tree (reachability → queue state → retry → restart → report) is inlined rather than delegated. At 23 lines with no agents shipped this is a defensible deliberate deviation, but it is a deviation from "command = interface, agent has the knowledge". *(rule: `agent-cmd/command-thin`)*

### run 1 — tts-mcp#3 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — the rewritten `description` now carries a behavioral directive ("Activation does not run a selftest — use /tts-mcp:voice-test") rather than pure discovery triggers, diluting the trigger-phrase density the field exists for. Not a `skill-md-frontmatter-required` violation (that rule is presence-only, and `name:`/`description:` are both correct). *(rule: `skill-writing/skill-md-frontmatter-required`)*

### run 1 — tts-mcp#3 — skills/voice/SKILL.md:22

**`skills/voice/SKILL.md:22`** — "the handshake cost a round-trip on every activation" is change rationale, not description of what the skill does; it goes stale on the next reworks. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — tts-mcp#3 — CHANGELOG.md:12

**`CHANGELOG.md:12`** — trailing clause "This is the extracted startup handshake, now invoked deliberately instead of on every activation" narrates the diff's history and duplicates the `### Changed` bullet at line 16. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — tts-mcp#3 — CHANGELOG.md:10

**`CHANGELOG.md:10,14`** — `### Added` / `### Changed` subheadings under `## Unreleased`; the changelog guide requires a flat list. No rule id covers this one — guide § File Structure "Flat list" only. Note the released `## v0.1.0` section uses the same category style, so the new block matches local convention.

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:36

**`hooks/deny-generated-file-edits.sh:36`** — `grep -oE 'Source:[[:space:]]*\S+'` truncates the source directory at the first whitespace, so the denial message points the agent at a path that does not exist. Reproduced end-to-end against the banner shape emitted at `pkg/distill/driver.go:313-315`, using the real-world path from `docs/spec.md:279`: ``` source_dir = /Users/bborbe/Documents/Obsidian/Personal/50 ← does not exist regen = distill --source /Users/bborbe/Documents/Obsidian/Personal/50 Knowledge Base/CLAUDE Rules --output … ``` The same message therefore contradicts itself — `Regenerate:` (line 37, uses `.+`) is intact while `Source:` is chopped. The hook actively misdirects the agent it is meant to redirect. Fix: `'Source:[[:space:]]*[^[:space:]]+[^>]*'` or take the remainder of the line via `sed -E 's/^.*Source:[[:space:]]*//'` and strip the trailing `-->`.

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:12

**`hooks/deny-generated-file-edits.sh:12`** — `set -e` aborts on malformed stdin: `printf 'not json' | …sh` exits 5 at the `jq` on line 12, before any branch runs. A PreToolUse non-2 exit is non-blocking in Claude Code, so this is fail-open. Fix: `tool=$(jq -r '.tool_name' <<<"$input" 2>/dev/null || true)`.

### run 1 — distill#6 — README.md:127

**`README.md:127-130`** — the install command is unreachable for the documented install path. `README.md:11-13` tells users to `go install github.com/bborbe/distill@latest`, which leaves no checkout on disk, so `cp hooks/deny-generated-file-edits.sh ~/.claude/hooks/` is a dangling relative path for the primary audience. `cp` also fails outright when `~/.claude/hooks/` does not exist. Fix: `mkdir -p ~/.claude/hooks` plus a `curl -fsSL …/main/hooks/deny-generated-file-edits.sh` alternative, or state "from a checkout of this repo".

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:33

**`hooks/deny-generated-file-edits.sh:33`** — `head -c 2048 "$path"` has no `--`, so a leading-dash path is parsed as an option (`head: invalid option -- w`), the `|| true` swallows it, and protection silently lapses. Fix: `head -c 2048 -- "$path"`.

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:36

**`hooks/deny-generated-file-edits.sh:36`** — `\S` is not POSIX ERE; on a strict POSIX grep it matches a literal `S` and source extraction silently falls back to the generic message. `[^[:space:]]+` is portable and equivalent.

### run 1 — distill#6 — README.md:134

**`README.md:134-147`** — no caveat that pasting the snippet over an existing `hooks.PreToolUse` array **replaces** it rather than merging. One line closes it.

### run 1 — distill#6 — docs/adopting-distill.md:110

**`docs/adopting-distill.md:110`** — the duplicated install snippet omits the `chmod +x` that `README.md:129` carries; either drop it or make it identical.

### run 1 — distill#6 — docs/adopting-distill.md:5

**`docs/adopting-distill.md:5,97,107`** — link labels promise sections (`README.md § Source rule format`) but the targets are bare `../README.md`. Add anchors (`#source-rule-format`, `#make-integration`, `#edit-protection-hook`).

### run 1 — distill#6 — README.md:149

**`README.md:149`** — `Requires jq` sits after the install block and the settings snippet; the reader wires it up before learning the prerequisite.

### run 1 — distill#6 — CHANGELOG.md:7

**`CHANGELOG.md:7`** — `feat(hooks):` does not match the rule's literal prefix regex `^- ([a-z]+:)`, though it matches the established project convention (`CHANGELOG.md:13` uses `chore(dev):`). Harmless; drop the scope only if strict-regex compliance is wanted. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh

**`hooks/deny-generated-file-edits.sh`** — the only executable code in the diff has no automated coverage, and `make precommit` runs no shellcheck (its `addlicense` target globs `*.go` only, so the license-header convention does not reach `.sh` either).

### run 1 — vault-ui#39 — src/vault_ui/static/app.js:1105

**`src/vault_ui/static/app.js:1105-1111`** — the new `formatActivityAge` block was inserted *between* `cardShellHtml`'s existing 3-line doc comment and `cardShellHtml` itself. Two unrelated comment runs are now jammed together with no blank line, so `cardShellHtml` (line 1138) is left undocumented while `formatActivityAge` appears to carry a comment describing a card body. Confirmed by reading the file; two independent owners found it. Fix: move the new comment+function above line 1105, or below `cardShellHtml`.

### run 1 — vault-ui#39 — src/vault_ui/activity.py:50

**`src/vault_ui/activity.py:50-61`** — `session_id` is interpolated straight into a glob pattern (`f"*/{filename}"`) with no validation. A `claude_session_id` containing a glob metacharacter matches arbitrary files — verified: id `*` matched `a.jsonl` and `b.jsonl` in my test, returning a wrong timestamp. The repo already guards this: `cleanup.py:51-60` rejects `/`, `\`, and non-UUIDs, and `session_resolver.is_uuid` is **already imported** in `tasks.py:36`. Adding the guard costs no new import.

### run 1 — vault-ui#39 — src/vault_ui/api/tasks.py:1795

**`src/vault_ui/api/tasks.py:1795` and `:706`** — `_task_to_response`/`_goal_to_response` were pure transforms; they now perform filesystem I/O. Verified against the base branch. Both run inside `async def` via `asyncio.gather`, so `stat`/`glob` block the event loop. Measured cost: 0.31 ms per lookup, ~62 ms for a 200-card all-miss board, against a 60 s poll (~0.1% duty cycle) — real but not severe. `derive_claude_project_dir` is also recomputed per task though invariant per vault. *(rule: `python-architecture/constructor-injection-only`)*

### run 1 — recurring-task-creator#30 — pkg/publisher/period_token_test.go:25

**`pkg/publisher/period_token_test.go:25`** — Coverage gap: only `offset=-1` single-period is tested, while the fix also changes positive and multi-period offsets. Verified empirically with Go's `AddDate`: monthly `2026-01-31` off `+1` → old `2026-03` vs new `2026-02`; monthly `2026-05-31` off `+1` → old `2026-07` vs new `2026-06`; quarterly `2026-12-31` off `-2` → old `2026Q3` vs new `2026Q2`; quarterly off `+2` → old `2027Q3` vs new `2027Q2`; monthly `2026-01-29` off `+1` → old `2026-03` vs new `2026-02`. All five diverge and all are untested. This matters beyond tidiness because `k8s/apis/task.benjamin-borbe.de/v1/types.go:77` documents positive offsets as first-class ("positive values name a future period"), so the untested half is a documented, supported input. Add one positive-offset monthly entry on a 31st and one multi-quarter entry.

### run 1 — recurring-task-creator#30 — CHANGELOG.md:14

**`CHANGELOG.md:14`** — `- fix(deps): bump ...` fails `changelog/conventional-prefix-required`. The rule's enforcement is regex `^- ([a-z]+:)`, which requires `:` immediately after the letters, so the `(deps)` scope does not match. The guide's table further assigns dependency updates to `chore:` (line 112) and its checklist repeats it (line 205); the repo's own released sections use `chore:` for dep bumps (`CHANGELOG.md:80`). Rewrite as `- chore: bump \`google.golang.org/grpc\` to v1.82.1 (...)`. *(rule: `changelog/conventional-prefix-required`)* Note the irony: `3f42ce6` is titled "use conventional prefix for grpc changelog bullet" — the corrective commit fixed the missing prefix but landed on a scoped form the regex still rejects.

### run 1 — recurring-task-creator#30 — pkg/publisher/period_token_test.go:68

**`pkg/publisher/period_token_test.go:68-71`** — The `2026-08-31` entry sits under the line-52 header "Discriminating entries — old code produces wrong token on these", but it does not discriminate. Verified: old code computes Aug 31 −1mo = Jul 31 (a valid date), so both old and new yield `2026-07`. Its trailing comment ("July has 31 days but August target does too") explains the opposite of discrimination. The assertion is correct; only the classification is wrong — move it to the control block or reword. *(rule: `tdd/failing-test-before-implementation`)*

### run 1 — recurring-task-creator#30 — pkg/publisher/period_token_test.go:123

**`pkg/publisher/period_token_test.go:123-125`** — The leap-day rationale is inaccurate on two counts: Feb 29 −1y normalizes to Mar 1 2027 (a month boundary, not a year boundary), and no December overflow is involved. The assertion `2027` is correct. Reword or drop. *(rule: `tdd/failing-test-before-implementation`)*

### run 1 — tts-mcp#10 — CHANGELOG.md:17

**`CHANGELOG.md:17`** — "The two remaining advisories are `@hono/node-server <2.0.5` … Left unfixed deliberately" is **false**. `@hono/node-server` is not flagged on this lockfile at all — the audit lists exactly `sdk`, `fast-uri`, `hono`, `ip-address`, `proxy-addr`, `qs`. It *was* flagged on base (moderate) and this PR fixed it (`1.19.12 → 1.19.15`; the vulnerable 1.x range is `<1.19.15`). The advisory the author documented as deliberately left open is the one that was actually resolved. No remaining set exists as described.

### run 1 — tts-mcp#10 — CHANGELOG.md:17

**`CHANGELOG.md:17`** — "`npm audit fix --force` resolves it only by downgrading the SDK to 1.24.3 (breaking)" is **false**. Verified dry-run: `--force` **upgrades** `@modelcontextprotocol/sdk` `1.29.0 → 1.32.1`. There is no downgrade and no blocking condition.

### run 1 — tts-mcp#10 — mcp/package-lock.json

**`mcp/package-lock.json`** — `proxy-addr` 2.0.7 is a **critical** (CVSS 9.1, IP spoofing via IPv4-mapped IPv6 trust subnet), present on base *and* head, and never mentioned in the entry. `npm audit` reports `fixAvailable=true` for an in-range `2.0.7 → 2.0.8` bump. It is unreachable here (the relay uses `StdioServerTransport` and never instantiates `express`), but a critical omitted from a security-summary bullet is the omission that matters.

### run 1 — tts-mcp#10 — CHANGELOG.md:16

**`CHANGELOG.md:16`**, **`CHANGELOG.md:17`**, **`CHANGELOG.md:21`** — none of the three new bullets starts with a conventional prefix, so dark-factory's bump parser cannot classify them. *(rule: `changelog/conventional-prefix-required`)* — all three are dependency/tooling work, so `chore:` fits each.

### run 1 — tts-mcp#10 — CHANGELOG.md:14

**`CHANGELOG.md:14`** — the new `### Fixed` category heading contradicts the flat-list rule. *(rule: `changelog/preamble-frozen`)* — note the file already uses `### Added`/`### Changed` on unchanged lines, so this is a pre-existing repo-wide style, not a regression introduced here.

### run 1 — tts-mcp#10 — .github/workflows/ci.yml:34

**`.github/workflows/ci.yml:34-35`** — the comment's trailing clause ("without this the `test` check was blind to every change under `mcp/`") narrates the motivating change rather than describing the code, and will go stale once the blind spot is closed. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — tts-mcp#10 — Makefile.precommit:26

**`Makefile.precommit:26`** — `npx tsc` resolves the local binary only because `typescript` is a devDependency and `npm ci` installs dev deps by default. Under `NODE_ENV=production` or `--omit=dev`, `npx` falls back to fetching the latest compiler from the registry — an unpinned typecheck. `./node_modules/.bin/tsc --noEmit` removes the fallback.

### run 1 — tts-mcp#10 — Makefile.precommit:25

**`Makefile.precommit:25`** — a target named `mcp-typecheck` performs a full `npm ci`, so every `make check` deletes and re-downloads `mcp/node_modules`. Splitting install from check (or `--prefer-offline --no-audit --no-fund`) keeps local iteration cheap.

### run 1 — tts-mcp#10 — Makefile.precommit:30

**`Makefile.precommit:30`** — `check` still has no dependency-vulnerability or secret scan, so the lockfile this PR churns is the one thing `check` cannot see. *(rule: `node/make/security-gates-in-check`)*

### run 1 — tts-mcp#10 — .github/workflows/ci.yml:37

**`.github/workflows/ci.yml:37-39`** — Node is pinned to 22 in CI but `mcp/package.json` declares no `engines`, so local majors drift silently; `setup-node` also runs without `cache: npm`.

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:823

**`shim/claude_openai_shim.py:823`** — the `\W*` in `_WAKE_RE` makes address-checking quadratic in transcript length. Measured on the exact compiled pattern: doubling the input quadruples the time (250→8000 sentence starts = 5.9 ms → 5.84 s;16000 starts = 23.3 s). Root cause is the unbounded `\W*` re-scanning the remainder at every one of N sentence-start positions. This runs on the request hot path for every voice turn. Bounding it fixes it with identical semantics — `\W*` → `[^\w]{0,8}` takes 16000 starts from **23.3 s to 13.5 ms** (1700×), and I verified both patterns agree on every realistic utterance. `src/config.js:182` carries the same unbounded `\W*` on the bot side. Exploitability is limited: `SHIM_HOST` is set nowhere in the repo, so the shim binds `127.0.0.1` and the input is the operator's own speech — **but this becomes a Must Fix the moment the shim is exposed beyond loopback**, which is the normal k8s shape.

### run 1 — discord-assistant#5 — config.example.yaml:65

**`config.example.yaml:65`** — `voice.wake_phrases` is documented as the place to tune wake phrases ("add what your transcripts show"), but it only ever reaches the shim. The bot never reads `config.yaml` — `grep` for yaml in `src/` returns nothing; `src/config.js:142` reads `process.env.SHIM_WAKE_PHRASES` only. So an operator who follows this file gets a split brain: the endpoint gates on their list while the bot's typing indicator and busy gate stay on the built-in default. That reintroduces the exact wedge this same PR fixed in commit 7 — `answering` set for an utterance the endpoint answers with silence, dots hanging to the 5-minute cap and `speak()` refusing typed turns as `busy` meanwhile. The `src/config.js` comment calls drift "cosmetic"; this is the one instance an operator will actually hit, because it is the default path. Either have the bot read the same channel, or state on the config.yaml comment that it configures the endpoint only and the bot additionally needs the env var.

### run 1 — discord-assistant#5 — src/config.js:17

**`src/config.js:17`** — the quote-strip order diverges from the shim's, contradicting the comment the diff adds at `shim/claude_openai_shim.py:107` claiming agreement "on every spelling". JS strips quotes **then** trims (`.replace(/^["']|["']$/g,'').trim()`); Python trims **then** strips quotes (`.strip().strip("\"'")`). Verified across 14 inputs: they disagree on ` "1" `, ` "true" `, and `" 0 "`. The direction matters for consent — `TRANSCRIBE=" 0 "` reads **false** in the shim but falls back to **true** in the bot. Narrow trigger (whitespace inside the quotes), but silent, and it is precisely the class the comment claims to have closed. Align by trimming whitespace on both sides of the quote strip on both processors.

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:864

**`shim/claude_openai_shim.py:864`** — the `lstrip(" ,.:;-—")` set omits `?` and `!`. `"Hey bot?"` strips to `"?"`, which passes the `stripped.strip()` fallback and is handed to the model as the entire prompt; `"Hey bot."` falls back to `"Hey bot."`, the vocative this function's own docstring says it exists to remove. *(rule: none)*

### run 1 — discord-assistant#5 — src/config.js:23

**`src/config.js:23`** — `flag()` returns the fallback for any unrecognised value with nothing logged, and `config.check()` never sees the new settings, so `TRANSCRIBE=fales` silently keeps recording. The docstring's goal ("a switch that looks set and isn't") holds only for spellings already in the list. *(rule: `node/config/validate-before-serving`)*

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:821

**`shim/claude_openai_shim.py:821`** — `_FILLER_WORDS` is interpolated into the regex without `re.escape`, while the phrase alternation on lines 825–826 escapes correctly. Safe today (all members are bare alphanumerics); a filler containing a metacharacter would silently change the pattern.

### run 1 — discord-assistant#5 — shim/claude_openai_shim.py:1829

**`shim/claude_openai_shim.py:1829`** — the endpoint is the authority on what gets answered, yet `is_addressed`/`strip_wake_phrase` have no tests: `make test` is `node --test` only, and no Python harness exists. The JS/Python mirror is "kept in sync by hand" with nothing enforcing it.

### run 1 — discord-assistant#5 — src/voice.js:331

**`src/voice.js:331`** — `ws.send` inside the `'open'` handler is unguarded; a socket that errors between open and send throws inside the event handler. The deep-merge justification cites `handlers/session.py:28`, outside this repo and unverifiable here — if that server *replaces* rather than merges `turn_detection`, every connect resets the launcher's VAD tuning, which is the opposite of the comment's intent.

### run 1 — discord-assistant#5 — src/config.js:181

**`src/config.js:181`** — the `RegExp` is rebuilt per call per phrase on every transcription event, while the Python counterpart precompiles `_WAKE_RE` once at module load.

### run 1 — discord-assistant#5 — config.example.yaml:65

**`config.example.yaml:65`** — no normalisation of intra-phrase whitespace or punctuation, so `"Hey, bot"` and `"Hey bot"` miss, despite the variant list existing precisely to absorb STT artefacts. Both fall back to silence, which is the fail-quiet side, so the cost is a missed trigger.

### run 1 — tts-mcp#13 — src/server.py:353

**`src/server.py:353`** — `instruct` is queued with no engine-capability check, so a voxtral server returns `202 Accepted` and only fails later as an asynchronous per-message `error`. `voice` *is* validated synchronously (`:333`, 400 on unknown voice), so this is an inconsistency in the same handler. This directly contradicts the shipped docs: `README.md:273` and `CHANGELOG.md:13` both say the voxtral engine "fails the request", while `README.md:275` documents "Returns `202 Accepted`". `VoxtralEngine.generate` only raises at `src/tts/engine.py:131`, inside the worker's `try` at `src/server.py:494`. Fix: expose the capability on the seam (`supports_instruct`) and reject at `say()` with a 4xx — that also makes the documentation true.

### run 1 — tts-mcp#13 — CHANGELOG.md:12

**`CHANGELOG.md:12-16`** — all 9 bullets under `## Unreleased` lack a conventional prefix, so `/coding:commit` cannot detect a version bump and this feature commit would patch-bump instead of minor-bump. *(rule: `changelog/conventional-prefix-required`)* Note this is a **pre-existing repo-wide gap**, not introduced here — `## v0.2.0` and `## v0.1.0` are also prefix-free. Flagged because the rule is MUST-tier and now blocks this release's bump detection.

### run 1 — tts-mcp#13 — CHANGELOG.md:12

**`CHANGELOG.md:12`** — "The worker, normalization, and playback layers are untouched" is false, and self-contradictory: `normalize.py`/`player.py` are indeed untouched, but `worker.py` has 35 changed lines, and the same block's Changed bullet at `CHANGELOG.md:14` lists `streaming_chunk_iter()`, `audio_worker()`, and `audio_worker_from_model_id()` as changed.

### run 1 — tts-mcp#13 — src/server.py:118

**`src/server.py:118-140`** — commit `59f9fe8` converted 15 config fields to `self._x` + one-line read-only properties, which silences the mechanical private-fields detector without addressing the underlying clump. The ten audio fields (`sample_rate`, `lead_silence_ms`, `normalize_audio`, `target_lufs`, `true_peak_ceiling_db`, `min_duration_seconds`, `meter`, `stream`, `streaming_interval`, `streaming_warmup_seconds`) already have a value object — `AudioSettings` — yet `ServerState` re-declares all ten and `audio_settings()` (`:227-240`) reassembles them from its own copies. Fix: compose `ServerState(engine, settings: AudioSettings, …)` and delete the ten properties.

### run 1 — tts-mcp#13 — scripts/download-model.sh:104

**`scripts/download-model.sh:104`** — the new `speech_tokenizer` loop writes straight to the final path (`curl -o "$dest"`), so a `set -e` abort leaves a truncated `speech_tokenizer/model.safetensors` that a later run accepts and `-C -` resumes onto. Use `-o "$dest.part" && mv`.

### run 1 — tts-mcp#13 — src/tts/engine.py:34

**`src/tts/engine.py:34-37`** — `TTSEngine.kind` has no production caller; `grep '\.kind'` hits only `tests/test_engine.py:36,41`. Speculative generality forcing both impls to carry a dead member.

### run 1 — tts-mcp#13 — src/tts/worker.py:57

**`src/tts/worker.py:57`** — `_generate_worker_chunks` hardcodes `None` and takes no `instruct` parameter at all, while `_run_streaming_worker` passes a hardcoded `None` at `:171`. The CLI can never reach a qwen3-only feature; the parameter exists purely to match the shared signature.

### run 1 — tts-mcp#13 — src/server.py:287

**`src/server.py:287-288`** — `StatusResponse.audio_file`/`.error` gained `= None` defaults, relaxing them from required to optional. Unrelated to this change, unexplained, and the sole construction site (`src/server.py:376`) passes both explicitly — no functional effect, but it silently alters the published OpenAPI schema.

### run 1 — tts-mcp#13 — README.md:91

**`README.md:91-100`** — the expanded `src/tts/` tree adds per-module internals (`normalize.py # BS.1770-4 loudness normalization`), which the guide lists under README "never contains". *(rule: `readme/user-facing-not-agent-context`)*

### run 1 — tts-mcp#13 — CHANGELOG.md:13

**`CHANGELOG.md:13`** — the clause "per the project's no-silent-fallback rule" cites the authoring rule rather than the behavior; a reader can't resolve it from the repo. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — tts-mcp#13 — src/tts/engine.py:249

**`src/tts/engine.py:249`** — `cast(CustomVoiceModel, model)` is a no-op at runtime; correctness depends on `validate_model()` having run at load. Document the precondition on `TTSEngine.generate`.

### run 1 — tts-mcp#13 — scripts/download-model.sh:113

**`scripts/download-model.sh:113-114`** — hardcodes `language: English` and `default_voice: ryan` without validating `ryan` against the selected model's speaker set.

### run 1 — github-releaser-agent#8 — pkg/steps_planning.go:753

**`pkg/steps_planning.go:753`** — `PreconditionP1UnreleasedNotFirst` covers **two** changelog shapes, not one. `changelog.ValidateUnreleased` emits the identical `"is not the first ## section"` reason both when `## Unreleased` is **absent entirely** (the incident shape this feature targets) *and* when `## Unreleased` **exists but sits below a version heading**. `handleValidationFailure` gates only on the precondition, so both take the `nothing_to_release` branch. I reproduced the second shape end-to-end against the real step: a changelog at the tagged commit whose misordered `## Unreleased` holds `feat:` bullets returns `STATUS=done NEXT=done`, writes `status: completed`, sets **no** `previous_assignee`, and emits `outcome=nothing_to_release`. A genuinely malformed changelog — the exact case the spec says must reach a human — is silently closed as released work. This contradicts the change's own stated contract on three counts: `specs/completed/002-planning-close-nothing-to-release.md:29` (*"a genuinely malformed changelog still reaches a human"*), the constraint *"Fail-open is mandatory: every error path … falls through to today's escalation"*, and `docs/dod.md:19`, which now documents the widening as if it were the intended narrow exception. The fix is a discrimination the reason string already supports: gate on *both* `P1_unreleased_not_first` **and** the absence of any `## Unreleased` heading, so only shape (a) closes and shape (b) still escalates.

### run 1 — github-releaser-agent#8 — pkg/steps_planning_test.go:2271

**`pkg/steps_planning_test.go:2271`** — the seam-argument assertion cannot detect the contract it documents. Frontmatter `current_version` and the mocked remote tag are both `v0.3.1`, so `Expect(tag).To(Equal("v0.3.1"))` at `:2316` passes identically whether the code consults `effectiveVersion` (remote-resolved) or `snapshotVersion` (frontmatter). The doc block at `pkg/steps_planning.go:746-748` makes that distinction load-bearing. One spec with `current_version: v0.3.0` against remote `v0.3.1` would pin it. *(rule: `test-pyramid/push-down-when-unsure`)*

### run 1 — github-releaser-agent#8 — pkg/githubtags/tags.go:34

**`pkg/githubtags/tags.go:34`** — `LatestSemverTag` renders bare on pkg.go.dev. This diff stripped its contract paragraph and the `// Implementations MUST be safe for concurrent use.` line off the type comment, then documented only the *new* method inline — the asymmetry is the tell, and the concurrency contract is a real caller constraint. The type comment at `:32` also now describes only one of two methods. *(rule: `go-doc/exported-item-must-have-comment`)*

### run 1 — github-releaser-agent#8 — pkg/steps_planning_test.go:2409

**`pkg/steps_planning_test.go:2409` / `:2439`** — `tag absent escalates` and `lookup failure escalates (fail-open)` assert an identical observable set; the branches differ only in `glog.V(2).Infof` vs `glog.Warningf`, so the second never proves it took the second branch. The safety property (escalate, never silently complete) *is* covered.

### run 1 — github-releaser-agent#8 — pkg/steps_planning_test.go:2603

**`pkg/steps_planning_test.go:2603`** — `sameCommit`'s swap (`if len(a) > len(b)`) is never executed; no table entry passes a `ref` longer than `tagCommit`. Requires a >40-char hex ref, which GitHub's API never emits — effectively dead defensive code.

### run 1 — github-releaser-agent#8 — pkg/steps_planning_test.go:2634

**`pkg/steps_planning_test.go:2634`** — `releaseTagVerdict` tokens asserted as raw `"nothing_to_release"` / `"escalate"` rather than the exported constants, so a constant change wouldn't fail the test.

### run 1 — github-releaser-agent#8 — CHANGELOG.md:8

**`CHANGELOG.md:8`** — commit `04f55d7` subject is past-tense (*"spec 002 **transitioned**"*); `2312772` / `75cde50` are verbless prompt slugs. *(rule: `git-commit/imperative-mood`)*

### run 1 — discord-assistant#1 — src/index.js:272

**`src/index.js:272`** — the new `RECOVERABLE_NET` arm swallows uncaught exceptions matching an *unanchored* `/i` regex on `err.message`. Verified false positives: `TypeError: x is not a function (ENOTFOUND in path)` and `Cannot read properties of undefined (reading socket hang up)` both match — a genuinely fatal bug is silently absorbed and the process continues in undefined state. This inverts the file's own stated invariant three lines above (`src/index.js:243-245`: "Exiting on an unknown exception is right — the process state is unknowable"). Match errno-style tokens on `err.code`, anchor the free-text ones.

### run 1 — discord-assistant#1 — src/index.js:276

**`src/index.js:276`** — the branch sets `gatewayReady = false` on *any* match, including one from the voice/LLM/REST path, while the gateway is healthy. `gatewayReady` returns true only via `clientReady`/`shardReady`/`shardResume`, so on a healthy connection the next shard event may never come and readiness stays false forever. Nothing recovers it: liveness is deliberately gateway-free (`k8s/discord-assistant-deploy.yaml:42-45`), `replicas: 1` so draining goes nowhere, and the supervisor is **local-only** — `Dockerfile:39` is `ENTRYPOINT ["node","src/index.js"]`. Result in production: pod alive, liveness-green, readiness-red, never restarted — the exact "strictly worse than exiting" state the new comment rejects.

### run 1 — discord-assistant#1 — scripts/supervise.sh:47

**`scripts/supervise.sh:47`** — `sleep "$delay"` is not interruptible; bash defers the trap until the sleep returns. Verified: SIGTERM to the supervisor PID during a 30s backoff hangs **29.0s**; SIGTERM to the process group exits in 0.1s. Any stop path that signals the supervisor alone (Docker `SIGTERM` to PID 1, `kill -TERM <pid>`) hangs up to `DELAY_MAX`. Background the sleep and `wait` on it.

### run 1 — discord-assistant#1 — scripts/supervise.sh:19

**`scripts/supervise.sh:19-23`** — `stop()` kills the child then `exit 0` **without waiting**. Verified: supervisor dead at t+0.3s while the child kept draining to t+3s. It reports success while graceful shutdown is in flight and orphans the child.

### run 1 — discord-assistant#1 — scripts/supervise.sh:12

**`scripts/supervise.sh:12-14`** — delay bounds are never validated. `SUPERVISE_DELAY_MIN=0` → **996 restarts in 5s**; `SUPERVISE_DELAY_MAX=0` → **1089 in 8s**. Non-numeric → `supervise.sh:50: abc: unbound variable`, the supervisor **dies and the child is never restarted** — the exact failure the script exists to prevent. Validate and clamp before the loop.

### run 1 — discord-assistant#1 — src/index.js:272

**`src/index.js:272`** — the same network fault surfacing as a *rejected promise* still hits `src/index.js:232-235` (`unhandledRejection` → `process.exit(1)`). The fix covers only the synchronous throw path, so the incident class in the CHANGELOG is only partly closed.

### run 1 — discord-assistant#1 — CHANGELOG.md:5

**`CHANGELOG.md:5`** — new `## Unreleased` bullet has no conventional prefix; the bump detector reads the first token and finds none. `fix:` (or `feat:` for supervise.sh) — not both. *(rule: `changelog/conventional-prefix-required`)*

### run 1 — discord-assistant#1 — Makefile:33

**`Makefile:33`** — `make run` now returns the *supervisor's* status, and a persistent crash restarts forever, so a non-zero exit never surfaces to a caller. The recipe also gained a dependency on `scripts/supervise.sh` with no guard analogous to `require-config`.

### run 1 — discord-assistant#1 — src/index.js:259

**`src/index.js:259-265`** — no test covers `connectedOnce`, `RECOVERABLE_NET`, or `supervise.sh`; `test/` holds only config/health/llm. The `connectedOnce` gate is the whole design and is untested.

### run 1 — discord-assistant#1 — scripts/supervise.sh:20

**`scripts/supervise.sh:20`** — `trap - INT TERM` restores *default* disposition, so a second Ctrl-C can kill the supervisor before `kill "$child"` runs. Use `trap '' INT TERM`.

### run 1 — discord-assistant#1 — scripts/supervise.sh:40

**`scripts/supervise.sh:40-42`** — exit 2 is a magic code hard-coupled to `src/index.js:23`. A revoked/invalid token fails `client.login` → `unhandledRejection` → exit1 → restart forever at max backoff; the most likely permanent failure never reaches a give-up.

### run 1 — discord-assistant#1 — src/index.js:262

**`src/index.js:262-265`** — `connectedOnce` is one-way and re-registers `clientReady`, already handled at `src/index.js:75`; two sources of truth for "gateway has been up".

### run 1 — discord-assistant#1 — src/index.js:275

**`src/index.js:275-277`** — a swallow emits a log line only, no counter or duration; a crash is visible as a restart count, a swallow is not — the visibility argument in the CHANGELOG is inverted.

### run 1 — discord-assistant#1 — scripts/supervise.sh:10

**`scripts/supervise.sh:10`** — `pipefail` is inert; the script has no pipelines.

### run 1 — helm#3 — charts/github-pr-reviewer/values.yaml:61

**`charts/github-pr-reviewer/values.yaml:61`** — the diff changes `TRUSTED_AUTHORS` from a single value (`bborbe`) to a comma-separated list, but the contract is unverifiable from this repo. The consumer is the external image `bborbe/github-pr-watcher` (`values.yaml:41`); no template, schema, or README in this repo defines the separator or whether matching is split-then-trimmed. If the watcher still does a single exact-string compare, the effective value becomes the literal `bborbe,ben-s-go-updater[bot]` — matching *no* login, so **both** authors silently lose trust and every PR routes to `human_review`. That's a safe-fail direction, not an unsafe one, but it defeats the change's purpose with no error. The `<slug>[bot]` form and the case-sensitive exact match are likewise asserted only in the comment. Please confirm against the watcher that comma-splitting is supported; if it is, this is doc-only.

### run 1 — helm#3 — charts/github-pr-reviewer/README.md:33

**`charts/github-pr-reviewer/README.md:33`** — the values contract lists `watcher.env.TRUSTED_AUTHORS` as an invariant default but doesn't state the comma-separated format. Since an operator overriding it via `--set` needs to know the separator, one clause here would match the rigor of the rest of that section.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:340

**`pkg/spawner/service_reconciler_test.go:340-343`** — the 50-iteration loop in the two-Config spec collects no `orderings` set and asserts only the *final* state (345-351), so iterations 1-49 buy zero signal; a single reconcile fails identically on a buggy build. Its siblings at 223 and 249 do collect. Either collect the set or drop to one iteration.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:241

**`pkg/spawner/service_reconciler_test.go:241-257`** — the 20-key spec asserts only `HaveLen(1)`, never *which* order, so it passes on a deterministic-but-wrong sequence. Its 4-key sibling at 232-238 catches that; this one leans on it. The exact sorted slice is cheap here.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:214

**`pkg/spawner/service_reconciler_test.go:214-220, 260-266, 281-287, 303-309`** — the6-line `multiEnv.Env` literal is copy-pasted four times and the ordering-loop block three times. A `func() map[string]string` fixture and one `orderingsAcross(n, conf, cfg)` helper collapse both.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler.go:296

**`pkg/spawner/service_reconciler.go:296`** — the doc comment says "the reconciler re-renders this StatefulSet on every pass and **the result is compared**". The reconciler does not compare; `StatefulSetDeployer.Deploy` `Update`s unconditionally and the API server does the diff that bumps generation. The consequence described is accurate, the mechanism attribution is loose. The same paragraph says "both walks are over the Config's own env map" — the second (313) walks the `keys` slice.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler.go:276

**`pkg/spawner/service_reconciler.go:276-277`, `:297-298`** — redundant assertions in the test file: `second.Spec.Containers[0].Env` Equal `first...Env` is strictly subsumed by `second` Equal `first`; `after.Image` NotTo Equal `before.Image` is tautological against a literal. Keep one of each.

### run 1 — agent-task-executor#67 — pkg/spawner/service_reconciler_test.go:280

**`pkg/spawner/service_reconciler_test.go:280-300`** — the image-change spec near-duplicates the pre-existing spec at `:191`; the only new assertion is `after.Env == before.Env`. Folding that one line in removes a redundant reconcile cycle.

### run 1 — agent-task-executor#67 — CHANGELOG.md:6

**`CHANGELOG.md:6`** — compliant (`fix:` prefix, correct placement under `## Unreleased`, verified via the `awk` section assertion). Nit only: the bullet names `StatefulSet`/`Config` but not the function that changed.

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:120

**`src/vault_ui/pane_resolver.py:120`** — `env["PATH"]` raises `KeyError` when `PATH` is absent from `os.environ`. The expression is evaluated as an argument *inside* the `try` at `:175-181`, whose only handler is `except OSError`, so the `KeyError` escapes `resolve_pane_id` — contradicting the docstring's "Returns ``None`` for every failure" (`:166`). launchd always sets `PATH`, so this is latent, but the sibling `_who_needs_me_path` at `:70` uses the safe `os.environ.get`. Fix: `env.get("PATH", "")`.

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:120

**`src/vault_ui/pane_resolver.py:120`** — prepending gives `/Applications/WezTerm.app/Contents/MacOS` precedence over every system directory for the helper *and* every process it forks. Appending is equally functional here and removes the shadowing surface entirely. Note the tradeoff: prepend pins resolution to the bundle (the deterministic-binary behaviour the CHANGELOG claims), append would prefer a Homebrew `wezterm` already on the plist `PATH`. Prepend is a defensible pick — flagging only so the choice is deliberate.

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:115

**`src/vault_ui/pane_resolver.py:115-118`** — the one diagnostic explaining this diff's silent failure mode ("wezterm not found; pane resolution may fail") is `logger.debug`, invisible at the level a launchd service actually runs. This whole change exists because that failure was silent; the regression signal stays silent too.

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:49

**`src/vault_ui/pane_resolver.py:49`** — the bundle path is hardcoded with no override, while `config.yaml.example:5` already ships `vault_cli_path` for the analogous `vault-cli` binary. A WezTerm installed outside `/Applications` still fails under a minimal `PATH` — same as before the change, so not a regression, but it is the one case the new code does not cover.

### run 1 — vault-ui#94 — src/vault_ui/pane_resolver.py:94

**`src/vault_ui/pane_resolver.py:94`** — `.exists()` accepts a *directory* named `wezterm`; `is_file()` (or an executable check) would match the docstring's claim. Trivial — a bundle named correctly never produces this.

### run 1 — ai-assistant#111 — src/llm.js:96

**`src/llm.js:96`** — 403 is lumped in with 401 as `permanent`. The shim only emits 401 (unauthorized) and 403 (`identities.strict` refusal), so for the Claude-Code-shim path this is right. But `CLAUDE.md` records the LLM endpoint as swappable by design, and a 403 from an OpenAI-compatible backend or a WAF in front of one (Cloudflare bot check, org/project permission, plan gating) is recoverable. Classifying it permanent means the transport acks, the user's message is dropped with no retry, and the notice says "misconfigured" when the cause was a quota or a WAF challenge. Suggest 401 permanent, 403 retryable — or branch on the shim's own refusal body (`{"error":{"message":"unauthorized"}}` vs `"identity refused: …"`), which is unambiguous. *(no rule id — correctness)*

### run 1 — ai-assistant#111 — src/llm.js:96

**`src/llm.js:96`** — the CHANGELOG bullet records the observed refusal as "(401/400)", but 400 is not in the permanent set. The shim's `/chat/completions` returns 400 for `bad json` and `no user message` (`shim/claude_openai_shim.py:3690,3694`) — both deterministic caller-side conditions that reproduce identically on every redelivery, i.e. the exact loop this PR exists to stop. Either mark 400 permanent too or correct the CHANGELOG's parenthetical; right now the doc claims coverage the code does not have. *(no rule id — internal inconsistency)*

### run 1 — ai-assistant#111 — src/llm.js:68

**`src/llm.js:68`** — the guard is per-request only. `src/config.js:344`'s `config.check()` has no credential clause and `src/index.js:15-19` exits on whatever it returns, so a deployment with neither credential still boots, passes `/healthz` and `/ready`, and only then silently discards every turn with an in-thread notice. That is the rule's named failure mode — *"boots with bad configuration… passes its probes and silently serves errors"* — reached one layer later. Adding `if (!config.chatBridgeToken && config.apiKey === 'not-needed') problems.push('no credential — set CHAT_BRIDGE_TOKEN or OPENAI_API_KEY')` gives the honest CrashLoopBackOff; the runtime guard stays as defence in depth. Note the rule's literal `applies_when` is not met (`check()` exists and is called and exits non-zero) — this is a coverage gap on the changed guard's own design, not a violation in unchanged files. Downgrade to Optional if read strictly. *(rule: `node/config/validate-before-serving`)*

### run 1 — ai-assistant#111 — test/gchat.test.js

**`test/gchat.test.js`** — the new `e.permanent` → post-notice → ack branch in the Pub/Sub handler has no test. The file already establishes the pattern for exactly this kind of guarantee (`readThreadHistory`, lines 254-284, exists because the surrounding comment says a dropped catch "reaches its outer catch, the message is nacked, and Pub/Sub redelivers it: a loop, not a degraded answer"). The permanent branch is the same guarantee one level up, and it is the half that actually stops the loop — the `llm.js` half is fully covered. Extract the handler body behind a small seam (or a `permanent` classification helper) and assert ack-not-nack plus the notice text. *(no rule id — test coverage gap)*

### run 1 — ai-assistant#111 — src/llm.js:603

**`src/llm.js:603`** — `hasCredential` is exported but has no caller outside its own definition; the tests reach the guard through `chat()`. Dead export, or the seam a boot-time `config.check()` cannot use (it would be circular) — either drop it or note what it is for.

### run 1 — ai-assistant#111 — src/llm.js:25

**`src/llm.js:25`** — the doc block still says the `not-needed` sentinel "exists so a local run against a shim that does not check can proceed." That remains true for the six other `controlAuth()` call sites (`/voice/bind`, `/mode`, `/sessions/reset`, …), which this diff does not guard — but for `chat()` the sentinel is now explicitly refused, which is what the next sentence says. Reads as a contradiction on the same lines; worth one clause narrowing it to the unguarded routes.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:143

**`scripts/session-liveness.py:143-148`** — `subprocess.run(["ps", …])` has no `timeout=`. A hung or locale-stalling `ps` blocks `read_registry()` synchronously on the `--check`, `--list`, and import paths. Add `timeout=` and catch `subprocess.TimeoutExpired` beside the existing `OSError`.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:90

**`scripts/session-liveness.py:90`** — `_CTIME_FMT` is `LC_TIME`-dependent, and `ps -o lstart=` emits locale-formatted output, so the docstring's "the SAME format" holds only under a C/en locale. Verified: with `LC_ALL=de_DE.UTF-8` the same live record reads `alive=None` (UNKNOWN) instead of `True`; under the default locale it reads `True`. It fails *safe* (never a false death), but it silently turns the entire registry UNKNOWN on a non-English host — exactly the mass-blind direction the change exists to avoid. Fix: pass `env={**os.environ, "LC_ALL": "C"}` to the `ps` call. *(rule: `python-logging/configure-once-in-main` — n/a, quality finding not rule-derived; no rule id)*

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:199

**`scripts/session-liveness.py:199-205`** — `_pid_identity` returns `None` for two distinct causes (no usable `procStart` at :200, **and** `ps` reported no `lstart` for an occupied pid at :202-204), but the docstring at :224 and the UNKNOWN message at :409 attribute it solely to the missing `procStart`. A `ps` read-miss therefore surfaces a misleading reason. Widen the message to "no start time could be established for the holder".

### run 1 — claude-supervisor#91 — scripts/tests/test_session_liveness.py:272

**`scripts/tests/test_session_liveness.py:272`** — the comment says *"an unproven identity must not appear"*, but the test plants a **mismatched** `procStart` (a proven negative, `False`) and `main()` at :518 explicitly **keeps** unproven identities. The comment states the inverse of the implemented rule. Rewrite: *"a proven mismatch is a negative, so it is dropped; an unprovable identity stays listed."*

### run 1 — claude-supervisor#91 — scripts/transport-read-check.py:47

**`scripts/transport-read-check.py:47-49`** — `# added 2026-10-01` plus a before/after history comparison sit inside the `SITE_LIST` data block. Keep the durable part (first transport call `session-liveness.py` holds), drop the date marker. *(rule: `self-containment/no-revision-meta`)*

### run 1 — claude-supervisor#91 — scripts/manager-predispatch.py:552

**`scripts/manager-predispatch.py:552`** — `` `alive` is a three-state since 2026-10-01 `` records *when* the field changed rather than what it is. Drop the date. *(rule: `self-containment/no-revision-meta`)*

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:66

**`scripts/session-liveness.py:66`**, **`scripts/tests/test_session_liveness.py:219`** — the `[[A Substring-Matched Liveness Probe…]]` wikilink resolves only in the operator's Obsidian vault, never in a checkout. Name the residual in words. *(rule: `self-containment/no-planning-doc-refs`)*

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:127

**`scripts/session-liveness.py:127`** — *"which is this fix inverted"* points at the change under review rather than the function's contract. *(rule: `self-containment/no-steering-echoes`)*

### run 1 — claude-supervisor#91 — scripts/tests/test_session_liveness.py:54

**`scripts/tests/test_session_liveness.py:54-72`** and **`scripts/tests/test_manager_predispatch.py:38-53`** — `live_proc_start()` is byte-identical in both files; factor into the shared test helper.

### run 1 — claude-supervisor#91 — scripts/session-liveness.py:283

**`scripts/session-liveness.py:283` vs `restart-precheck.py:100`** — `read_registry` accepts `bool` (`isinstance(True, int)` is `True`) and negatives as pids; `restart-precheck.pid_is_alive` guards `pid <= 0`. Pre-existing, not introduced here — but the identity pass now feeds those pids to `ps` unchanged.

### run 1 — claude-supervisor#100 — CHANGELOG.md:120

**`CHANGELOG.md:120`** — `## Unreleased` was inserted **mid-history**, between `## v0.87.5` (line 116) and `## v0.87.4` (line 124). It is not the top of the file; `## v0.94.0` is (line 11). This silently corrupts the next release. I reproduced it end-to-end on a scratch copy: renaming `## Unreleased` → `## v0.95.0` in place (which is exactly what `coding/agents/release-changelog-assistant.md` step 2's extract-and-rename does — it finds the heading anywhere) lands `## v0.95.0` at line 120, buried under eight headings that look newer, while `scripts/check-versions.py:21` reads the **first** `## ` heading and gets `v0.94.0` → **`VERSION MISMATCH`, exit 1**. Both `check-changelog.py` (position-agnostic regex) and `check-versions.py` pass green on the defect today. Fix: move the section to line 11, directly above `## v0.94.0`. *(rule: `changelog/preamble-frozen` — note this rule's detector only fires on content inside/above the preamble block, so it does not catch the ordering violation; a rule-base gap, not a misapplication.)*

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:86

**`scripts/voice-ask-pairing.py:86`** — the detector counts a card as paired **only** when an `attention-ask.py post` Bash call appears in the transcript. But this repo's own dominant card path is the `Stop` hook: `commands/worker-drive.md:467` states the `👤 You:` closer panel is published by `~/.claude/hooks/attention-log.py` → `~/.claude/scripts/attention-watcher.py`, **not** by a CLI post in the session's transcript. I reproduced the consequence: a worker that voices a question and ends on a `👤 You: pick —` panel — exactly the flow `worker-drive` and this PR's banner target — reports **unpaired**, though the card exists on the board. The detector therefore flags the very panels the rule most wants carded, and its `unpaired` count is not "cards that never existed." Either widen the pairing signal to hook-published cards, or state the exclusion in `docs/voice-asks.md` so the number is not read as a defect count.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:54

**`scripts/voice-ask-pairing.py:54`** — `_is_post` matches unanchored substrings (`"attention-ask.py" in command and " post" in command`). Verified false positives: `attention-ask.py poll abc --note 'do not post yet'` and `echo attention-ask.py post is documented in docs/voice-asks.md` both score as a card posted. I grepped real transcripts for such commands — zero instances today, so impact is latent. Anchor it: `re.search(r'attention-ask\.py["\']?\s+post(-batch)?\b', command)`.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:97

**`scripts/voice-ask-pairing.py:97`** — `os.path.getmtime` is unguarded, so a transcript rotated away between `glob` and `stat` raises `FileNotFoundError` out of `main()`, contradicting the docstring's "Exit 0 always." `scan()` already models the right tolerance at line 60.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:62

**`scripts/voice-ask-pairing.py:62`** — `open(path, errors="ignore")` leaves encoding to the platform locale; transcripts are always UTF-8. Add `encoding="utf-8"`.

### run 1 — claude-supervisor#100 — scripts/voice-ask-pairing.py:96

**`scripts/voice-ask-pairing.py:96`** — no env override for the transcript root, while the two peers that glob the same tree (`scripts/who-needs-me.py:43`, `scripts/reap-closer.py:101`) both read `PROJECTS_DIR` first. *(rule: `self-containment/no-home-dir-paths` — the mechanical hit here is **not actionable**: 26 sibling scripts and the repo's own CLAUDE.md use the same literal, so this follows the established convention. Recorded for the override gap only.)*

### run 1 — claude-supervisor#100 — commands/worker-drive.md:511

**`commands/worker-drive.md:511`** — banner placed mid-document with a doubled blank line (512–513); the other three commands put theirs directly after the frontmatter. The mid-document slot is arguably better (it sits with the TTS guidance) — make all four consistent and drop the extra blank line.

### run 1 — claude-supervisor#100 — README.md:243

**`README.md:243`** — `docs/voice-asks.md` is the only file in `docs/` not listed in README's Documentation section (`fleet-surface`, `session-tiers`, `subject-resolution`, `pane-reads`, `restart-worker` all are). Verified by looping the directory against README.

### run 1 — claude-supervisor#100 — CLAUDE.md:130

**`CLAUDE.md:130`** — the layout map is otherwise grouped by directory; `scripts/voice-ask-pairing.py` is wedged between two `docs/` rows.

### run 1 — claude-supervisor#85 — server/supervisor.mjs:760

**`server/supervisor.mjs:760`** — the cap-reached error still advises `remove the key for unlimited`. That was true before this change and is now exactly backwards: an absent key resolves to `DEFAULT_MAX_CONCURRENT` (20), so an operator hitting a full fleet follows the instruction, changes nothing, and gets the identical error again. The only route to unlimited is an explicit `0`. The parallel text in `server/spawn-mode.mjs:169-170` *was* updated to `"(0 for unlimited), or omit the key for the default of N"` — this second copy was missed. **Outside the diff** (`supervisor.mjs` is unchanged) but rendered wrong by this change; flagged as Must Fix rather than buried in Notes because it is a broken remediation instruction on the exact error path a saturated fleet hits.

### run 1 — claude-supervisor#85 — scripts/check-worker-target.py:112

**`scripts/check-worker-target.py:112-123`** — check (b) cannot detect the defect it is named for. The inline comment reads *"a referencing file points at the home; it does not carry its own copy"*, and the docstring claims it prevents a third copy — but the code only tests `HOME_ANCHOR not in text`. **Presence of the pointer is checked; absence of a restated copy never is.** A file carrying both passes. The test suite has the same blind spot: `SITE_RESTATES` (line 43) restates the number but omits the anchor, so `test_referencing_site_without_the_pointer_fails` exercises only the no-pointer path — there is no case for anchor-present *and* number-restated. This is the one gap that matters, because the whole change exists to make a restated copy detectable.

### run 1 — claude-supervisor#85 — commands/fleet-loop.md:262

**`commands/fleet-loop.md:262`** — restates the number: `` (`spawn.maxConcurrent`, default 20) ``. Thirty-nine lines below, line 223 states the rule this diff establishes: *"read the number there and **never restate it here**."* The file does both. Verified empirically: `make precommit` runs `check-worker-target` and exits 0 with this line present — the live demonstration that the gap above is real, not theoretical.

### run 1 — claude-supervisor#85 — docs/fleet-surface.md:176

**`docs/fleet-surface.md:176`** — *"The count is live **WORKERS**, from the heartbeat store"* contradicts the store's own contract. `server/supervisor.mjs:74` is the sole writer: `stampRecord(heartbeatDir, { sessionId, pid, pid, mode: 'headless' })`, and `scripts/live-workers.py` documents itself as reading *"the headless-worker heartbeat store."* Interactive/tab workers are never counted. The line carefully excludes `~/.claude/sessions/*.json` and states the auto-resume exclusion, but not this one. Severity rose with this change: the number stopped being only a guard and became the **decision input for whether a manager proposes work** — so a fleet with 15 tabs and 2 headless workers reads `2/20` and proposes against a fleet the operator is already saturated with.

### run 1 — claude-supervisor#85 — scripts/check-worker-target.py:43

**`scripts/check-worker-target.py:43`** and **`CHANGELOG.md:14`** — both hard-code the same evidence as *"lines 35 and 70"*. Accurate today (verified: `grep -c` = 2, at exactly those lines), but any insertion above them silently falsifies a comment whose entire purpose is to justify a load-bearing key choice. Two copies of the same brittle citation, in a change about not having two copies of things. Naming the two occurrences by their surrounding prose would survive reflow.

### run 1 — ai-assistant#107 — src/gchat.js:197

**`src/gchat.js:197-205`** — the refusal branch inherits the reply-then-ack contract that exists to guarantee delivery of a real answer, but a refusal is not worth guaranteeing. If `postChatReply` throws (403 where the app cannot post, 404 from a malformed `spaceName`, a persistent 429), the shared `catch` at `:219-222` runs `message.nack()` and Pub/Sub redelivers — re-posting the refusal each time the API intermittently succeeds, and because `flowControl.maxMessages = 1` (`:174`) it repeatedly occupies the single in-flight slot. One wedged refused message degrades the whole Chat surface. Fix: catch inside the refusal branch, log at `warn`, and `message.ack()` unconditionally — a lost refusal costs nothing, a redelivery loop costs the surface.

### run 1 — ai-assistant#107 — src/config.js:356

**`src/config.js:356-359`** — the new `check()` branch makes `GCHAT_ALLOWED_EMAILS` mandatory, and `src/index.js:14-18` calls `process.exit(2)` on any problem. An existing Chat-enabled deployment that never set the variable will crash-loop on rollout. The posture is right (loud at boot, fails closed, matches the unconditional `ALLOWED_USER_IDS` check at `:347`); the gap is operational — `CHANGELOG.md:13` documents the variable but does not say it must be set *before* upgrade.

### run 1 — ai-assistant#107 — test/gchat.test.js:117

**`test/gchat.test.js:117`** — `delete process.env.GCHAT_ALLOWED_EMAILS;` at file scope executes at module load, i.e. **before** any registered test body runs (verified on Node v22.22.3), so it cleans nothing. The preceding test leaves `GCHAT_ALLOWED_EMAILS=alice@seibert.group` set for the rest of the file. Harmless today only because it happens to be last. Move the cleanup into the last test body and delete this line.

### run 1 — ai-assistant#107 — src/gchat.js:102

**`src/gchat.js:102-103`** — `REFUSAL_TEXT` names a specific human to any sender who messages the app, disclosing that the bot exists, that it is allowlist-gated, and who owns it — a durable, screenshottable org-structure leak and a ready-made phishing target. Naming a role ("ask the Data Platform team or your workspace admin") keeps the useful next step without naming a person. *(also raised independently by the self-containment agent)*

### run 1 — ai-assistant#107 — src/gchat.js:117

**`src/gchat.js:117-123`** — `isAllowedSender` reads the module-level `config` import rather than taking the list as a parameter. Not a violation — the rule targets handler/app factories, and this is the same pattern the rest of the file already uses (`config.identity` at `:76`, `config.gchatSaCredentials` at `:133`). The real cost is that it forces the `require.cache` surgery in the new tests. Taking `allowedEmails` as a parameter would delete the `loadGchat` helper outright. *(rule: `node/architecture/inject-dependencies`)*

### run 1 — ai-assistant#107 — src/gchat.js:114

**`src/gchat.js:114`** — the rule id `node/config/data-not-behaviour` is cited without an in-repo resolution path, and the reason is already stated in words on the line above it. A dangling pointer adds no traceability. *(rule: `self-containment/no-requirement-ids`)*

### run 1 — agent-claude#20 — main.go:246

**`main.go:246`** — `NewServiceWithPermissions` mounts `GET`/`POST /permission` with **no authentication and no session scoping**. Verified in the v0.93.0 source: `permissionHandler` (`interactive/permission-handler.go:30`) switches on method with no auth check, and upstream's own comment states *"The endpoint is unauthenticated and reachable by anything in the namespace."* The registry is one shared instance across **all** sessions, and `sessionFactory.Create(_ string)` discards the session id entirely, so a pending permission raised by session A is listed and answerable by any other caller — including one that never posted the prompt. This diff is what makes the route reachable; previously the nil decider meant no turn could ever pause. *(rule: `go-security/resource-ownership`)*

### run 1 — agent-claude#20 — pkg/factory/factory_test.go:137

**`pkg/factory/factory_test.go:137`** — the only test touched is a signature fix that still passes `nil` for the new parameter, so the shared-registry wiring that is the entire point of this diff has **zero coverage**. Nothing asserts the factory receives the same registry instance the service serves. *(rule: `tdd/failing-test-before-implementation`)*

### run 1 — agent-claude#20 — main.go:99

**`main.go:99-100`** — the `Listen` doc comment still reads "readiness, metrics and prompt intake"; this diff adds the permission endpoint to that surface (its own new log line at 230-232 already says so). Line unchanged by the diff, but the diff makes it stale.

### run 1 — agent-claude#20 — README.md:20

**`README.md:20`** — service-mode description likewise omits the permission endpoint.

### run 1 — git-ai-sync#16 — entrypoint.sh:43

**`entrypoint.sh:43-44`** — `git config --global user.name/user.email` are the writes the startup guard exists to protect, but their exit status is discarded (`set -u` at line 8, no `set -e`). With an unwritable `HOME` (`ENV HOME=/tmp`, line 74 of the Dockerfile) both writes return 255, the script logs nothing wrong, and the first commit succeeds with git's hostname-derived fallback identity (`user@host`) — precisely the failure the comment at lines 35-38 says it prevents. *(rule: `shellcheck/set-e-guard` — advisory, no rule id in index.json)*

### run 1 — git-ai-sync#16 — entrypoint.sh:50

**`entrypoint.sh:50-53`** — line 22 gates on `[ ! -e "$VAULT/.git" ]`, which is true for a **worktree/submodule pointer file** as well as a directory. Then `grep -qxF` exits 2 (stderr suppressed), `echo >> "$EXCLUDE"` fails with "not a directory" (status discarded), and line 53 logs **`excluded .git-ai-sync.lock via …` — a false success**. The real gitdir's exclude is never touched, so `stage_all`'s `git add .` (verified: `git_operations.py:73`) commits the lock file into the vault. Gate on `[ -d ]` or resolve via `git -C "$VAULT" rev-parse --git-path info/exclude`.

### run 1 — git-ai-sync#16 — entrypoint.sh:70

**`entrypoint.sh:70-74`** — the retry loop has no backoff ceiling and treats every non-zero `watch` exit as a conflict. Verified against `__main__.py`: `cmd_watch` exits 1 on a conflict (line 238) **and** on `MarkerRefusalError` (line 275) and on lock error (line 153); `cmd_resolve` exits 1 on "Not in conflict state" (line 410) and on `resolved_count == 0` (line 432). So a permanent non-conflict failure — a missing `git-ai-sync` binary, a stale lock, a marker refusal — produces `resolve failed rc=1` every 5 seconds forever, with no crash-loop signal and no liveness probe in this diff. *(rule: none)*

### run 1 — git-ai-sync#16 — Dockerfile:52

**`Dockerfile:52` + `Dockerfile:61`** — `uv.lock` is copied into the build stage but `uv tool install --no-cache .` does not consume it (`uv tool install` resolves from package metadata; only `uv sync` honors the lock). The COPY signals a reproducibility intent the install does not honor. Use `uv sync --frozen` into a venv, or drop the lock COPY. *(rule: none)*

### run 1 — git-ai-sync#16 — Dockerfile:64

**`Dockerfile:64`** — `npm install -g @anthropic-ai/claude-code` is unpinned, so two builds of the same commit can ship different CLI versions. *(rule: `go-tools-versioning` sibling practice — no matching id)*

### run 1 — git-ai-sync#16 — Dockerfile:47

**`Dockerfile:47-49`** — the fallback version is `fallback-version = "0.9.0"` (`pyproject.toml:44`) while `CHANGELOG.md` is at `v0.11.2`. Because `.git` is excluded, `__init__.py`'s `version("git-ai-sync")` resolves to **0.9.0** in the image. The comment at lines 53-59 says this is acceptable because "the real version travels on the OCI labels" — true for `org.opencontainers.image.version`, but `git-ai-sync --version` inside the pod reports the stale number, and the entrypoint's own version line (line 18) reads `BUILD_GIT_VERSION`, not the installed metadata. *(rule: none)*

### run 1 — git-ai-sync#16 — entrypoint.sh:74

**`entrypoint.sh:74`** — `sleep "$RETRY_DELAY"` runs unconditionally, including after an `rc=0`; a non-numeric `GIT_AI_SYNC_RETRY_DELAY` turns the loop into a tight spin. *(rule: none)*

### run 1 — git-ai-sync#16 — entrypoint.sh:65

**`entrypoint.sh:65-66`** — if `TERM` arrives between `&` and `WATCH_PID=$!`, `stop()` sees `WATCH_PID=""`, skips the `kill`, and the child is orphaned un-signalled. *(rule: none)*

### run 1 — git-ai-sync#16 — .dockerignore:21

**`.dockerignore:21-22`** — `Dockerfile` and `.dockerignore` exclude themselves; neither is ever `COPY`'d, so both lines are no-ops. *(rule: none)*
