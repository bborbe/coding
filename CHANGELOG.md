# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## v0.28.0

- **feat: add `/coding:self-improve` command** — reviews the current session and proposes at most two durable, evidence-backed improvements to the Claude Code environment (memory/`CLAUDE.md` rules, commands, agents, skills). Two-phase: Report (read-only, ≤2 proposals ranked, routes each by scope) → Apply (only after explicit approval). Default outcome is "nothing worth keeping this session." Stays inline (analyzes the parent conversation; cannot be delegated to a sub-agent). Sibling to the audit-* commands, on the friction-removal side.

## v0.27.0

- **feat: add factory rule `go-factory/main-holds-only-boot-lifecycle-config` (SHOULD)** to `docs/go-factory-pattern.md`. New §11 "The main.go / factory boundary" states the complementary positive rule to §6.2/§8: `main.go Run` keeps only boot errors, lifecycle (`defer`), and config branching — every pure-composition value (including `run.Func` server/consumer wiring) belongs in a factory. Adds the "pass-through test", tightens §4.3 ("no additional logic" limits statement *kind*, not *count* — multi-statement router wiring is fine), fixes the §8 example which previously modeled router assembly in main, and adds a Summary bullet. Regenerates `rules/index.json` (judgment-tier, trigger `**/main.go`) and surfaces the rule in `go-factory-pattern-assistant`.

## v0.26.0

- **feat: split review commands into 3 distinct scopes.** Renames current `/coding:code-review` → `/coding:local-review` (preserving its diff-vs-`HEAD~1` semantics for pre-commit local checks), AND introduces a brand-new `/coding:code-review` that scans the WHOLE codebase via `git ls-files`. New command ships with severity filter (default-on: Must Fix + Should Fix only; `--include-optional` to opt in), rule-id dedup at consolidation (N occurrences → 1 summary with sample sites), and baseline file (`.code-review-baseline.yaml` via `--refresh-baseline`) so subsequent runs only flag NEW findings (drift since last sweep) rather than the operator's full accepted tech-debt set. Design rationale: `docs/three-command-review-split.md`. 10 reference sites updated across `llms.txt`, `README.md`, `scenarios/*`, and 4 agent definitions to point at `/coding:local-review` (preserving old semantics). **Migration**: sharp behavior cutover on the `/coding:code-review` slot — operators previously relying on its diff-vs-`HEAD~1` behavior must move to `/coding:local-review`. The contrast pair `pr-review` (remote, branch vs target) / `local-review` (local, pre-commit) reads cleanly; `code-review` takes the unmarked whole-codebase slot.

## v0.25.1

- docs: add `docs/three-command-review-split.md` — design note locking the proposed shape for splitting the review commands into three distinct scopes (`/coding:pr-review` remote diff, `/coding:local-review` local pre-commit diff (renamed from current `/coding:code-review`), new `/coding:code-review` whole-codebase audit). The doc pins defaults for baseline-file location (`.code-review-baseline.yaml` at repo root, `--baseline-path` override), monorepo handling (one baseline per repo by default; per-subproject via override), `--refresh-baseline` clean-tree requirement, and `.gitignore` semantics (respected; no separate `.claude-ignore` introduced).

## v0.25.0

- feat: extract `coding:architecture-dimensions-assistant` agent + `docs/architecture-dimensions-guide.md` — closes the v0.24.0 `/coding:architecture-review` MAJOR finding ("dimensions pass routes to generic `claude` with inline agent role"). The 8-dimension behavioral review checklist (data flow, failure, concurrency, observability, cross-cutting consistency, config/blast radius, evolvability, drift) is now a maintainable doc-paired agent. `/coding:architecture-review` Agent B now routes to the new agent with a one-line prompt instead of an inlined 200-word checklist. Indexed in README.md (Workflows & Documentation + Go agents table), llms.txt, and CLAUDE.md Doc↔Agent table.

## v0.24.0

- feat: add `/coding:architecture-review [directory]` — deep whole-codebase architectural review (different altitude from `/coding:code-review`'s diff-scope and `/coding:audit-architecture`'s single-agent scan). Spawns two parallel agents: top-down structural (`go-architecture-assistant` / `python-architecture-assistant`) + dimensions pass (data flow, failure, concurrency, observability, drift). Consolidates into Must Fix / Should Fix / Could Fix with file:line citations and Top 5 highest-leverage fixes.

## v0.23.1

- docs: add `docs/go-package-layout-guide.md` — flat `pkg/` default, five subpackage-split triggers (independent reuse, versioning, cycle break, navigation friction, build-tag isolation), conventional always-split exceptions (`pkg/factory/`, `pkg/handler/`), GOOD/BAD code pair, premature-split → flat migration steps. Indexed in README.md (Go — Architecture & Patterns), llms.txt, and CLAUDE.md Doc↔Agent table (owner: `go-architecture-assistant`).

## v0.23.0

- feat: add RULE `go-composition/no-same-package-private-helper-for-business-logic` (MUST, judgment-tier, owner go-architecture-assistant) — flags new business logic added as a same-package private helper instead of behind an interface + constructor + struct + method seam. Closes the gap left by the cross-package version (which only matches `pkg.Func` syntax). Codified after PR bborbe/recurring-task-creator#16 shipped a private `buildFrontmatter` helper that local pr-review dismissed as "pre-existing pattern" (broken-windows fallacy).

## v0.22.0

- feat!: selector mode is now the DEFAULT for `/coding:pr-review` and `/coding:code-review` (was opt-in via `--selector`/`selector` token); callers passing `standard` now get selector behavior — BREAKING CHANGE for any tooling that relied on `standard` triggering per-owner Task dispatch
- feat!: standard-mode per-owner Task dispatch removed — `owners_to_spawn` computation, per-owner Task prompt template, `funnel clean — no adjudication needed` standard-mode short-circuit, and `REVIEW_TIMING` per-owner instrumentation block deleted from both commands; full mode remains the per-owner deep sweep escape hatch
- docs: scenarios/002 and scenarios/004 retired (status: outdated) — superseded by scenarios/005 and scenarios/006 respectively; footer updated with retirement reason
- chore: acceptance.sh updated to assert the new dispatch reality: Selector mode (default) routing check added (section 1), per-owner block check tightened to full-mode-only assertions (section 2)

## v0.21.0

- fix: ast-grep-runner.sh excludes `.git/` paths from both input file list and findings output — incident 2026-06-11 surfaced 274 stale agent-auditor findings from `.git/COMMIT_EDITMSG` during selector validation
- feat: scenarios/005 (selector clean short-circuit) and scenarios/006 (selector findings path) — two new E2E scenarios (walked 2026-06-11, promoted to active) contracting the selector-mode journeys for a README-only diff and the perpetual fixture PR
- feat: acceptance.sh section 5 "Selector mode contracts" — 16 scripted checks covering --selector parse, short-circuit string, GUIDE_OK/GUIDE_MISSING fail-fast, selector-mode-guide.md content, sibling consistency, citation-validator rejection of unknown rule_ids, and runner .git/ exclusion

## v0.20.0

- feat: add opt-in `--selector` mode to `/coding:pr-review` and `/coding:code-review` — replaces per-owner Task fanout (Step 4b-ii) with two in-session steps: Step 4c-sel CLASSIFY (narrows glob candidates via recall-optimized contract) and Step 4d-sel ADJUDICATE (reads only applicable rule blocks, emits findings in existing severity buckets); zero sub-agent spawns; default mode unchanged
- refactor: extract selector-mode classify/adjudicate procedure to docs/selector-mode-guide.md — commands carry thin pointers (single source of truth; answers pr-reviewer command-thin + single-source-of-truth findings)
- fix: selector-mode guide resolution is now fail-fast — explicit `GUIDE_OK`/`GUIDE_MISSING` echo, and on missing guide the review STOPS with a Must Fix toolchain failure instead of silently continuing mechanical-only (caught by MiniMax-M2.7 benchmark: weaker model skipped classify+adjudicate entirely when the guide path failed, presenting a judgment-less review as complete)

## v0.19.0
- refactor!: BREAKING CHANGE — rename `coding:release-changelog-agent` → `coding:release-changelog-assistant` to match marketplace `<noun>-<role>.md` naming convention (`-assistant` / `-auditor`, not `-agent`). Coordinated rename: agent file `agents/release-changelog-agent.md` → `agents/release-changelog-assistant.md`, `name:` frontmatter, both callers' `subagent_type=` reference, README agents-table entry, llms.txt entry, and CHANGELOG mentions. Callers on v0.18.0 will fail to resolve until updated; v0.18.0 callers are bundled in this same commit so any installer of v0.19.0+ has the matching pair.
- refactor: restructure `coding:release-changelog-assistant` body to XML schema per agent-command-development-guide — add `<constraints>` block (NEVER commit/tag/push, ALWAYS return error field when malformed, etc.), `<process>` block summarizing the 5-step workflow up-front (was buried), `<output_format>` for the success JSON schema, `<error_handling>` for the three error codes (separates concerns from success). Markdown `#` headings retained only for high-level sections (Purpose, Inputs, classification rules, rewrite rules, caller profiles, invocation example); structural directives now use XML tags as the guide requires.
- docs: trim `coding:release-changelog-assistant` `description:` frontmatter from 229-char paragraph to one-sentence summary per agent-command-development-guide; the long-form caller list + flag semantics live in the body, not the description.
- chore: drop non-standard `effort: medium` frontmatter from `coding:release-changelog-assistant` — not a documented Claude Code field; if smaller-model cost is wanted, use `model: haiku` (documented mechanism).
- docs: add `coding:release-changelog-assistant` entry to `llms.txt` under Development Workflows so plugin installers + `/coding:check-guides` discover it alongside the changelog guide.

## v0.18.0
- fix: address third round of pr-reviewer findings — add missing `coding:` plugin namespace prefix to `subagent_type` in 3 places (`commit.md`, `github-release.md`, `agents/release-changelog-agent.md` invocation example); agent would have failed to resolve at runtime when installed via marketplace. Strip pre-release suffix in version arithmetic (`v0.69.0-rc1` → `0.69.0` before `read MAJ MIN PAT`) so the command's bash matches the agent's documented input contract. Drop unused `Bash(sed:*)` from `allowed-tools` (swapped to awk earlier). Replace remaining `~/Documents/workspaces/maintainer` example with `/path/to/local/repo` (self-containment).
- refactor: `/coding:github-release` now invokes `release-changelog-agent` for bump classification + bullet rewrite (flags: `majorBumpAllowed=true`, `rewriteChangelogEntries=true`). Step 4 replaces the inline classifier prose; Step 8 threads the optional `rewritten_unreleased` body through to the header rewrite (Edit tool for full-block replacement, awk for header-only passthrough). Operator confirm at Step 6 still has final say on the agent's bump call (downgrade dialog).
- refactor: `/coding:commit` Workflow B now invokes `release-changelog-agent` for bump classification instead of using the inline Version Increment Rules heuristic. Flags: `majorBumpAllowed=false` (preserves Workflow B's "major requires manual edit" contract), `rewriteChangelogEntries=false` (pure passthrough — Workflow B keeps the sed-rename behavior, no AI rewrite). Behavior on a happy-path release is identical to pre-refactor; the change is internal (one canonical source of bump-classification rules for all three callers).
- refactor: `release-changelog-agent` now reads `CHANGELOG.md` from cwd and extracts the `## Unreleased` block itself (instead of requiring the caller to pass `unreleased_body` inline). Centralizes parsing logic in one place; callers only pass `current_version` + the two flags. New output field `unreleased_body` returns the verbatim extracted text so the caller can do an atomic Edit-tool match-and-replace without re-parsing. Adds an error-case JSON branch (`changelog-missing` / `unreleased-section-missing` / `unreleased-section-empty`) for malformed input.
- feat: add `release-changelog-agent` sub-agent — canonical release-AI source: classifies the next semver bump from `## Unreleased` bullets and optionally rewrites them to conventional-prefix style. Two-flag contract (`majorBumpAllowed`, `rewriteChangelogEntries`) lets each caller opt into the capability tier it wants. Plan-time only (no git mutation). Ported from `agent/github-releaser/pkg/prompts/bump_classification.md` + `changelog_rewrite.md` with the flag layer added. Faithfulness audit (the agent's `ai_review` phase) deferred to Phase 2.
- feat: add `/coding:github-release` command — direct release of a git repo (cwd, local dir, or `owner/repo` clone-to-tmp), with bump classification from `## Unreleased`, commit/tag/push, and PR + auto-merge fallback for branch-protected repos
- fix: address second round of `/coding:github-release` pr-reviewer findings — define `owner_repo` helper for Step 7's tag-collision `gh api` call (previously referenced undefined `$OWNER`/`$REPO`), add `trap '... rm -rf ...' EXIT` to clean tmp clones on any exit path (including Ctrl-C and errors), spell out Step 11's PR-merge polling loop (`for _ in $(seq 1 30); do sleep 10; ...`) including the re-run path on timeout, drop personal-path references from the command body + CHANGELOG bullet (marketplace self-containment), add new command to `README.md` commands table
- fix: address `/coding:github-release` pr-reviewer findings — quote `argument-hint`, tighten allowed-tools `rm -rf` glob to mktemp-pattern (`/tmp/github-release/tmp.*`), reject owner/repo targets containing `:` or `@` (host-injection), swap sed→awk in CHANGELOG header rewrite (metachar-safe), define `die` + `default_branch` helper functions inline
- refactor: scope `/coding:github-release` tmp clones to `/tmp/github-release/` (was bare `mktemp -d` landing in `$TMPDIR` — `/var/folders/...` on macOS, `/tmp` on Linux); tightens `allowed-tools` from `rm -rf /tmp:*` + `rm -rf /var:*` (overly broad, allowed `rm -rf /var` system dir) to `rm -rf /tmp/github-release:*` only

## v0.17.0
- fix: correct Step 4b-i trigger glob-to-regex conversion in both commands — escape literal dots, anchor the match, `**/` matches zero-or-more dirs (root main.go), placeholder ordering so `**` expansion survives the `*` pass; found by self-reviewing PR #48 with its own pipeline (12 phantom owners → 1 real)
- perf: add standard-mode early exit to Step 4 in both commands — diffs touching no rule-relevant files (no .go/.py, no CHANGELOG/go.mod/LICENSE/README/Makefile/pyproject/k8s/agents/commands/skills/docs) skip the funnel entirely with a report note

- docs: update scenarios/001-004 to funnel v2 architecture (scripts/ast-grep-runner.sh, exit 2, /tmp/findings.json contract, funnel-clean short-circuit, diff-scope assertions); walk 001/003/004 with real output recorded
- feat: extend `build-index.py` to derive `enforcement_type` (`mechanical`/`script`/`judgment`) and parse optional `**Trigger**:` field into a `trigger` array for every rule entry in `rules/index.json`
- feat: backfill `**Trigger**:` field for all 62 judgment-tier rules across 30 doc files — enables diff-scoped dispatcher to skip owners whose triggers don't match changed files
- feat: rewrite Step 4 in `commands/pr-review.md` and `commands/code-review.md` — standard mode now computes active judgment-rule set via jq glob-matching and spawns only owners present in `findings_by_owner ∪ active-judgment-rule-owners`; zero LLM spawns when funnel is clean and no judgment rules are active; full mode unchanged
- docs: update `docs/rule-block-schema.md` to document `Trigger` optional field and new `enforcement_type`/`trigger` index fields
- feat: add `scripts/ast-grep-runner.sh` — deterministic replacement for the `ast-grep-runner` LLM agent; same JSON contract (`stats`/`findings_by_owner`/`errors`), diff-scoping via changed-file args, merges `rule-checks.sh` output.
- feat: add `scripts/rule-checks.sh` — script-tier (bucket 2) mechanical checks for 11 rules: `go-licensing/license-file-required`, `go-licensing/readme-license-section-required`, `changelog/preamble-frozen`, `git-commit/subject-under-50-chars`, `git-workflow/no-ai-attribution-in-commits`, `go-library/semver-vprefix-tag-required`, `go-tools-versioning/no-tools-go-for-clis`, `go-mod-replace/no-cross-repo-replace`, `python-project-structure/src-layout-required`, `python-project-structure/pyproject-toml-with-hatchling`, `skill-writing/scripts-in-scripts-subdir`.
- docs: deprecate `agents/ast-grep-runner.md` with pointer to `scripts/ast-grep-runner.sh`; update `**Enforcement**:` lines for 11 rules to cite `scripts/rule-checks.sh`.
- feat: transcribe 37 judgment-tier rule recipes into mechanical ast-grep YAMLs (`rules/go/` +31, new `rules/python/` +6) — each rule's prose "ast-grep partial/follow-up" recipe is now a real over-inclusive first-pass filter; mechanical coverage 29 → 66 of 139 rules. `go-mod-replace/no-cross-repo-replace` excluded (no go.mod grammar; doc updated to agent-only enforcement).
- feat: add ast-grep native rule tests — `testConfigs: rule-tests/` in `sgconfig.yml`, 37 test files with ≥2 valid + ≥2 invalid snippets per rule (incl. documented exemption cases); `ast-grep test -c sgconfig.yml` passes 37/37.
- docs: update 19 docs' `**Enforcement**:` lines to cite the new YAML paths, keeping adjudication guidance and dropping the now-redundant pattern prose.
- perf: gate `make precommit` to Full mode only in both `pr-review.md` and `code-review.md` — running the full test suite is CI's job; Standard/Short mode now report "precommit skipped (standard mode) — CI covers lint+test" instead.
- perf: make timing instrumentation opt-in via `REVIEW_TIMING=1` env var in both commands — the per-Owner ts_start/ts_end + jq/grep roll-up (~14 extra tool calls) now only fires when explicitly requested; otherwise skipped entirely.
- perf: add Step 0a-pre short-circuit to `pr-review.md` — if the cwd is already a clean checkout at origin/<SOURCE_BRANCH> HEAD, skip worktree creation/removal entirely (saves ~18 tool calls in the agent pod where cwd is already at PR HEAD).
- perf: tighten ast-grep Step 4.0 preflight in both commands — run exactly one compound check, once; on failure report and skip Step 4. Explicitly forbid further investigation (`which`, `ls rules/`, retry variants) to prevent the 4-probe drift observed in prod.
- perf: change `!git diff HEAD~1` context injection to `!git diff --stat HEAD~1` in `code-review.md` — review steps pull full diffs per-file on demand; the unconditional full diff injection was pure token waste.

## v0.16.0

- feat(rules): bootstrap `docs/go-functional-composition-pattern.md` with 5 `### RULE` blocks (`go-functional-composition/func-type-name`, `list-type-name`, `list-checks-ctx-done`, `list-wraps-errors-with-ctx`, `multi-method-func-explicit-delegate`). Covers the four load-bearing conventions of the pattern (Func/List naming, ctx-aware iteration, error wrapping with caller context, multi-method nil-safe delegation).
- feat(rules): bootstrap `docs/git-commit-guide.md` with 3 `### RULE` blocks (`git-commit/imperative-mood`, `git-commit/subject-under-50-chars`, `git-commit/feature-branch-no-tag`). All judgment-tier; the agent reads commit messages via `git log` rather than diff-time AST patterns. The doc also carries an explicit cross-reference to the pre-existing `git-workflow/no-ai-attribution-in-commits` rule (canonical in `docs/git-workflow.md`) instead of duplicating it.
- feat(rules): mechanical ast-grep YAML for `go-testing/suite-timeout-required`. Flags `func TestXxx(t *testing.T)` bodies that call `GinkgoConfiguration()` but don't assign to `suiteConfig.Timeout` before `RunSpecs`. The only cleanly-tractable of the 5 remaining `go-testing/*` MUST rules — the others need errcheck-equivalent type inference or file-existence checks. Mechanical YAML count: 28 → 29.
- feat(dispatcher): per-Owner timing instrumentation in Step 4b of both `commands/pr-review.md` and `commands/code-review.md` — JSONL log per Owner agent dispatch (event / owner / findings_in / wall_ms) plus roll-up summary. Makes "is this Owner worth dispatching?" answerable with data; previously the funnel ROI was anecdotal.
- Total rules in index after this batch: 131 → 139 (+8 — 5 functional-composition + 3 git-commit; the AI-attribution rule already existed in git-workflow.md). 0-rule docs remaining: 15 → 13 (still ~7 meta-docs of those out of scope). Mechanical YAML count: 28 → 29.

## v0.15.1

- feat(scripts): new `scripts/acceptance.sh` + `make check-acceptance` Makefile target — 12 fast assertions covering the dispatcher contract that doesn't need an E2E scenario walk: mode coverage (short/standard/full), per-Owner routing + index-to-agent integrity, Step 2.5 context-glob mappings, broken-YAML isolation. Wired into `make precommit` so CI catches dispatcher drift. Closes the 4 acceptance items listed on `[[Refactor coding pr-review to doc-driven rules pipeline]]` task page that were left over from the scenario-cut.
- fix(rules): `go-errors/no-fmt-errorf.yml` rewritten as a structural rule. The original `pattern: fmt.Errorf($$$ARGS)` was parsed by tree-sitter Go grammar as a `type_conversion_expression` (because `Type(arg)` is a valid Go type cast at pattern-compile time), so the rule matched no real call sites — silently emitting zero findings since the YAML shipped. Replaced with `kind: call_expression` + structural `selector_expression` match on `fmt.Errorf`. Verified against scenario 004's fixture (`pkg/scenarios-test-fixture/violations.go` on bborbe/maintainer#2): the `Boom` function's `fmt.Errorf` now fires. Scenario 004's `findings_count` floor lifted ≥4 → ≥5.

## v0.15.0

- feat(pipeline): dispatcher refactor for `/coding:pr-review` + `/coding:code-review` — Step 4 replaced with `ast-grep-runner` (mechanical funnel) → per-Owner LLM-tier adjudication → citation validation. Decouples LLM-call count from PR file count; small PR-size now equals small LLM-call count for the same rule coverage. Migrated 13 rule-enforcer agents to the dispatcher contract.
- feat(pipeline): citation validator (`scripts/validate-citations.sh`) — rejects findings whose `rule_id` is not present in `rules/index.json`. Smoke-tested against synthetic hallucination payload.
- feat(pipeline): coverage lint (`scripts/check-coverage.sh`) wired into `make precommit` — fails on dangling enforcement references, orphan YAMLs, and rule-id mismatches between docs and the index.
- feat(dispatcher): fail-fast preflight when `ast-grep` / `sg` binary is missing — both `commands/pr-review.md` Step 4.0 and `agents/ast-grep-runner.md` Step 0 emit a documented error and exit 1 instead of silently looping on `sg --version` (the failure mode observed on coding#34).
- feat(rules): mechanical ast-grep YAML count 20 → 28 across batches 5–6: `go-cli/slog-not-glog-in-new-projects`, `go-glog/use-v-for-debug-not-info`, `go-testing/no-testing-t-direct`, `go-testing/no-stdlib-table-tests`, `go-architecture/constructor-returns-interface`, `go-architecture/no-globals-or-singletons`, `go-architecture/counterfeiter-directive-on-interface`, `go-patterns/bborbe-collection-ptr-not-helpers`, `go-json-error-handler/use-error-code-constants`, `go-k8s-binary/secret-fields-need-display-length`, `go-concurrency/no-raw-go-func`, `go-concurrency/channel-closed-by-sender-only`, `go-cli/cobra-not-stdlib-flag`.
- fix(rules): `nosec-requires-reason.yml` — `pattern-regex` is not a valid ast-grep 0.43 field. Rewritten as `kind: comment` + `all: [regex: '#nosec\b', not.regex: '--']`. The original YAML had been silently parse-failing on every PR review since the rule shipped.
- feat(rules): bootstrap `docs/go-logging-guide.md` with 7 `### RULE` blocks (`no-mixing-slog-and-glog`, `no-log-and-return-error`, `external-call-logs-response`, `no-sensitive-data-in-logs`, `lowercase-log-messages`, `no-tight-loop-without-sampler`, `skip-empty-v2-heartbeats`). Total rules in index: 124 → 131.
- feat(scenarios): new `scenarios/` directory with 4 active E2E acceptance scenarios following the dark-factory scenario writing guide. Each scenario is a manually-walked checklist operators run from any terminal: `001-toolchain-preflight` (dispatcher fail-fasts when ast-grep is absent), `002-clean-pr-zero-findings` (README-only diff emits empty severity sections), `003-scaling-funnel-100-files` (mechanical funnel ≤30s, distinct Owners ≤30), `004-findings-exist-path` (`/coding:pr-review` against the perpetual test PR [bborbe/maintainer#2](https://github.com/bborbe/maintainer/pull/2) surfaces ≥4 findings with valid citations).
- docs: README + `llms.txt` index the 4 active scenarios alongside guides and agents.
- fix(commit): `/coding:commit` no longer classifies `scenarios/` changes as pipeline-only. Scenarios are shipped acceptance contracts (release-relevant, like `docs/` and `rules/`), not dark-factory runtime state — they belong in the changelog. Prompts and specs remain pipeline-only as before. Without this fix, a PR adding only scenario files would route to Workflow E and silently ship without a release-note record (the regression observed retroactively on PR #37 + #40 + #41).

## v0.14.0

- feat(rules): grow `rules/index.json` from 27 to 124 entries (+97 rules across 44 doc families). Most enforceable conventions in `docs/` now carry canonical `### RULE <id> (LEVEL)` blocks consumable by `/coding:pr-review`.
- feat(rules): new rule families bootstrapped — `go-architecture`, `go-prometheus`, `go-testing`, `go-licensing`, `go-doc`, `go-state-machine`, `go-linting`, `go-json-error-handler`, `go-service-impl`, `go-k8s-crd`, `go-functional-options`, `go-mod-replace`, `go-glog`, `go-concurrency`, `go-http-service`, `go-cqrs`, `go-cli`, `go-enum-type`, `go-composition`, `go-build-args`, `go-mod-dependency-fix`, `go-makefile`, `go-patterns`, `go-library`, `go-k8s-binary`, `go-filter`, `go-parse`, `go-validation`, `go-tools-versioning`, `go-boolean-combinator`, `go-mod-dependency-fix`, `agent-cmd`, `python-architecture`, `python-ioc`, `python-logging`, `python-pydantic`, `python-project-structure`, `python-makefile`, `python-factory`, `tdd`, `test-pyramid`, `changelog`, `git-workflow`, `markdown-todo`, `claude-md`, `readme`, `skill-writing`, `teamvault`, `k8s-manifest`, `adr`.
- feat(rules): first mechanical ast-grep YAML for a bootstrapped rule — `rules/go/counter-total-suffix.yml` (enforces `go-prometheus/counter-total-suffix` at lint time). Recipe for struct-literal-field matching codified in `docs/ast-grep-rule-writing-guide.md` (PR #11 → #12).
- feat(precommit): new `make check-index` target wired into the precommit chain — fails loudly when `rules/index.json` is stale relative to the walker output. Closes the gap that turned the PR #9 walker-regen miss into a retroactive PR #10 catch-up.
- docs(trim): trim three oversized guides to rules-only form, moving comprehensive reference content to the maintainer's Obsidian KB so `coding/docs/` stays portable for any plugin installer — `go-prometheus-metrics-guide.md` 2399 → 379 lines, `go-testing-guide.md` 1207 → 428 lines, `agent-command-development-guide.md` 1750 → 347 lines.
- docs(schema): `docs/rule-block-schema.md` now documents the recommended `**Why**:` paragraph and `#### Bad` / `#### Good` example sections — closes a gap where every existing rule block carried Why but the schema doc only described the three required fields.
- chore(rules): CLAUDE.md doc-agent alignment table grew from 13 to 44 entries to match the new rule-family coverage.

## v0.13.0

- docs(trim): trim `docs/go-prometheus-metrics-guide.md` 2399 → 379 lines (rules-only architecture; comprehensive reference moves to maintainer's Obsidian KB).
- docs(trim): trim `docs/go-testing-guide.md` 1207 → 428 lines (same architecture).
- docs(trim): trim `docs/agent-command-development-guide.md` 1750 → 347 lines with 7 pre-canonicalized `### RULE` blocks (`agent-cmd/command-thin`, `no-user-prompts`, `scripts-in-claude-dir`, `command-frontmatter`, `agent-frontmatter`, `single-source-of-truth`, `gap-driven-feedback`).
- feat(rules): add six `### RULE` blocks to `docs/go-prometheus-metrics-guide.md` — `go-prometheus/counter-pre-initialization`, `composed-metrics-interface`, `no-gauge-for-monotonic`, `counter-total-suffix`, `help-string-quality`, `label-naming-consistency`.
- feat(rules): add eight `### RULE` blocks to `docs/go-testing-guide.md` — `go-testing/no-stdlib-table-tests`, `no-testing-t-direct`, `no-bare-error-call`, `suite-test-file-required`, `main-test-with-compiles`, `suite-timeout-required`, `counterfeiter-mocks-required`, `libtime-injection-required`.
- feat(rules): first mechanical ast-grep YAML for `go-prometheus/counter-total-suffix` (`rules/go/counter-total-suffix.yml`) — uses `pattern.context + selector + inside.stopBy + constraints.not.regex` recipe; 4 TP / 0 FP across fixture cases (NewCounterVec, NewCounter, Name-position-agnostic, no false-flag on GaugeOpts/HistogramOpts).
- docs(ast-grep): propagate struct-literal-field-matching recipe to `docs/ast-grep-rule-writing-guide.md` (new section + three pitfall entries + canonical-example pointer).
- feat(precommit): add `make check-index` target; wired into `precommit` chain. Diff-based drift detection on `rules/index.json` — fails loud with actionable error when walker output and committed index diverge. Closes the gap exposed by the agent-cmd-guide trim's walker-regen miss (caught retroactively by the testing-bootstrap PR).
- `rules/index.json` grown 17 → 42 entries across eight rule families: `agent-cmd`, `go-context`, `go-errors`, `go-factory`, `go-http-handler`, `go-prometheus` (new), `go-security`, `go-testing` (new), `go-time`.

## v0.12.0

- feat(rules): add four `### RULE` blocks to `docs/go-http-handler-refactoring-guide.md` — `go-http-handler/no-inline-error-handler`, `go-http-handler/no-inline-background-handler`, `go-http-handler/new-prefix-naming`, `go-http-handler/kebab-case-handler-files`; matching ast-grep YAMLs for the two mechanical rules + `rules/index.json` entries grown from 17 to 21

## v0.11.1

- feat(rules): add four `### RULE` blocks to `docs/go-security-linting.md` — `go-security/file-perms-too-permissive`, `go-security/dir-perms-too-permissive`, `go-security/nosec-requires-reason`, `go-security/chmod-return-checked`; matching ast-grep YAMLs + `rules/index.json` entries
- chore(release): live-verify `github-releaser-agent` plugin-manifest bumping — release commit should rewrite `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` version fields alongside the CHANGELOG (feature shipped via `bborbe/maintainer` PR #33).

## v0.11.0

- refactor(check-links): extract inline shell from Makefile target to `scripts/check-links.sh` — enables `shellcheck` linting of the link-check logic
- feat(scan): add `scripts/scan.sh` — run ast-grep rules against external repos
- feat(rules): add two `### RULE` blocks — `go-time/no-time-now-direct`, `go-time/no-time-time-in-fields`; matching ast-grep YAMLs + `rules/index.json` entries
- docs: add `docs/ast-grep-rule-writing-guide.md` — authoring guide for ast-grep YAML rules paired with `### RULE` blocks
- docs: add `docs/go-time-injection.md` — guide for the two new go-time rules
- chore(ast-grep): add `sgconfig.yml` for project discovery; fix root `main.go` glob and expand ignores across all 3 rule YAMLs

## v0.10.0

- feat: add `scripts/build-index.py` — deterministic walker that extracts `### RULE` blocks from `docs/*.md` and emits `rules/index.json`
- docs: add `docs/rule-block-schema.md` — authoritative reference for `### RULE` block contract and `rules/index.json` schema.
- feat: add `make build-index` target — generates `rules/index.json` from `### RULE` blocks in `docs/`
- chore: commit initial `rules/index.json` — single entry for `go-context/cancel-check-in-loop` rule

## v0.9.13

- feat(commit): detect `.maintainer.yaml: release.autoRelease: true` and skip the tag step — `github-releaser-agent` owns the release. New routing rule short-circuits the branch check: master with bot opt-in routes to Workflow A (Unreleased append, no tag). See `[[GitHub Auto-Release Guide]]`.

## v0.9.12

- refactor(auditors): slim `audit-agent`, `audit-skill`, `audit-slash-command` commands to thin delegators — move target-path resolution out of the command body into the `agent-auditor` / `skill-auditor` / `slash-command-auditor` agents (knowledge belongs in the agent), rewrite `<success_criteria>` from invocation-mechanics checks to outcome checks, and normalize `argument-hint` to `[path/...]` style. Behavior unchanged; addresses self-audit findings.

## v0.9.11

- docs(go): add `go-k8s-binary-conventions.md` guide.
- docs(teamvault): add `teamvault-conventions.md` explaining the lookup-key vs raw-secret pattern; make `coding:code-review` aware of it.
- docs(pr-review): mirror `code-review` Step 2.5 — load context-specific conventions during PR review.
- templates: replace bare `make vulncheck` in `Makefile.library` and `Makefile.service` with the structured pattern from `go-skeleton` — adds `VULNCHECK_IGNORE ?= ...` allowlist of OSV IDs, runs govulncheck in JSON mode, and prints a deduplicated table (`OSV id`, `module@version -> fixed_version`, `summary`). Exits non-zero only on unignored findings.
- docs(go-makefile-commands): document new `make vulncheck` behavior, the `VULNCHECK_IGNORE` and `GOVULNCHECK_VERSION` variables, and how to allowlist a new OSV ID per-project.
- chore(release): version bump to `0.9.11` also forces plugin re-discovery of `coding:audit-agent`, `coding:audit-skill`, `coding:audit-slash-command` — fixed in 0.9.10 but never picked up because Claude Code caches command/agent discovery per plugin version (no bump = no re-scan).

## v0.9.10

- fix(auditors): unbreak `coding:audit-agent`, `coding:audit-slash-command`, `coding:audit-skill` commands and their corresponding agents (`agent-auditor`, `slash-command-auditor`, `skill-auditor`). Three slash commands were missing `allowed-tools: Task` in their frontmatter so the Task tool was blocked at invocation. Three agents were missing `effort: high` and used YAML-list `tools:` form (vs comma-string) which Claude Code's plugin loader silently rejected. Net: 3 previously-dead commands and 3 agents now load and function.
- note: Claude Code caches plugin agent/command discovery by plugin version. New agents/commands added at the same version are NOT picked up by `/reload-plugins` — only a version bump triggers re-discovery. Document this for future plugin releases.

## v0.9.9

- docs: clarify CQRS handler-error semantics in `go-cqrs.md` — handler errors do NOT cause kafka replay; the result-sender wrapper emits a single Failure result and commits the offset. Use `ErrCommandObjectSkipped` to suppress noisy Failure results when the caller condition is non-retryable.
- docs: Tighten CHANGELOG header rule in `docs/changelog-guide.md` — everything before the first `##` is frozen; never insert above any header line. Prevents the failure mode where a past `## Unreleased` was placed above the SemVer preamble and later release renames stranded the preamble mid-file.

## v0.9.8

- chore: extract `check-versions` to `scripts/check-versions.sh`; add `make release-check` (`precommit + check-versions`); unwire `check-versions` from `precommit` so drift during development is allowed and alignment is enforced at release time. Add `docs/releasing-coding.md`. Aligns with `dark-factory` / `vault-cli` / `semantic-search` release-gate shape.

## v0.9.7

- Re-align plugin manifests with git tag — `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (both metadata and plugins[0] entries) bumped from `0.8.0` → `0.9.7`. Manifests had drifted across v0.9.x releases.
- Add `make check-versions` precommit target — fails if `CHANGELOG.md` top version, `plugin.json`, and both `marketplace.json` version fields don't match. Prevents future drift.
- Strengthen `CLAUDE.md` "Version Alignment — MANDATORY" section: 4-place rule, precommit enforcement, release checklist update.
- `make check-json` now also validates `marketplace.json` syntax (was only `plugin.json`).

## v0.9.6

- Add `docs/go-http-service-guide.md` — canonical admin endpoint block (`/healthz`, `/readiness`, `/metrics`, `/setloglevel/{level}`, `/gc`, conditional `/resetdb`, `/resetbucket`, `/trigger`, `/sentryalert`, `/testloglevel`), port 9090 convention, K8s `admin/port` / `admin/path` Service annotations for gateway auto-registration, server lifecycle, security boundary, anti-patterns, validation checklist.
- Trim `/setloglevel` wiring snippet from `docs/go-logging-guide.md` (now a one-line reference to `go-http-service-guide.md`); logging guide retains glog level meanings and curl examples.
- Cross-link new guide from `README.md` and `llms.txt` under "Go — HTTP & APIs".

## v0.9.5

- Update `docs/go-tools-versioning-guide.md` with three lessons from the `jira-task-creator` migration:
  - New section "errcheck: Run via golangci-lint, Not Standalone" — recommends running `errcheck` via `.golangci.yml` instead of a standalone Makefile target. Avoids the `GODEBUG=gotypesalias=1` workaround required by `errcheck@v1.10.0` when the project uses Go 1.24+ generic type aliases. Includes the pattern (settings, exclusions) and migration steps.
  - "Don't downgrade during migration" note in the `tools.env` section — when a repo's existing tool version is newer than canonical (e.g. `golangci-lint@v2.12.1` vs canonical `v2.11.4`), keep the newer version. Newer linters often introduce checks that catch real issues; downgrading silently regresses already-clean code.
  - Note in the migration step about indirect-dep auto-population — after rewriting a minimal `go.mod` and bumping direct bborbe deps to `@latest`, indirect deps are typically already at latest via Go's module graph resolution.

## v0.9.4

- Add `docs/go-boolean-combinator-pattern.md` — `And` / `Or` / `Not` combinator pattern for predicate-style interfaces. Captures the convention used by `signalcheck` and the upcoming `truster` package: single-method decision interface, structured result with description, slice-typed combinators, function-typed adapter, fail-safe empty-list handling, full-evaluation audit-trail default. Includes anti-patterns (naked bool returns, nesting via callbacks, vacuous truth in security contexts) and a checklist for new implementations.
- Update `docs/go-filter-pattern.md` Related Patterns — replace the "Specification Pattern" placeholder with a real link to the new combinator guide.
- Index the new guide in `README.md` (Go — Architecture & Patterns table) and `llms.txt`.

## v0.9.3

- Add `templates/migrate-tools-go.sh` — reusable bulk migration script for multi-module repos. Operates on current repo via `git rev-parse --show-toplevel`, finds all `tools.go`, deletes them, bumps every `bborbe/*` dep (direct + indirect) to `@latest`, runs `go mod tidy`, drops obsolete replaces. Idempotent. Used to migrate 128 trading sub-modules in one run.
- Update `docs/go-tools-versioning-guide.md`: bump bborbe deps to `@latest` must include INDIRECT bborbe deps (drop the `// indirect` filter from the grep). Empirical example documented from `backup/service` (indirect `bborbe/kv v1.19.4` was dragging full pollution; bumping to v1.19.6 dropped go.mod from 486 → 93 lines).
- Update `templates/prompt-migrate-tools-go.md` to match the guide (script-driven `@latest` for direct + indirect; multi-module local-replace handling).

## v0.9.2

- Update `docs/go-tools-versioning-guide.md` with `bborbe/* @latest` recipe — script-driven dep bump replaces fragile manual version enumeration. New step in migration procedure: `grep '^	github.com/bborbe/' go.mod | grep -v '// indirect\|=>' | awk '{print $1}' | xargs -I {} go get {}@latest`
- Add post-migration verification step (zero pollution check): `grep -E '(cellbuf|go-header|go-diskfs|golangci-lint|osv-scanner|ginkgolinter|charmbracelet/x|denis-tingaikin)' go.mod` must return zero matches
- Add four new pitfalls based on agent multi-module migration experience: one unbumped bborbe dep brings cascade back; `go mod why` is the diagnostic; hardcoded version lists in prompts truncate; multi-module local-path replaces stay
- Update `templates/prompt-migrate-tools-go.md` to match: explicit `@latest` step, post-tidy pollution check, multi-module replace handling, renumbered steps to 11

## v0.9.1

- Add `templates/prompt-migrate-tools-go.md` — dark-factory prompt template for migrating Go libraries from `tools.go` to `tools.env` + Makefile `@version` pattern. Self-contained with full migration steps, references the guide, includes verification checks. Copy to each bborbe lib's `prompts/in-progress/` to drive the migration via dark-factory.

## v0.9.0

- Add `docs/go-tools-versioning-guide.md` covering the migration from `tools.go` to `tools.env` + Makefile `@version` pattern for CLI tool version pinning. Documents why `tools.go` is harmful (transitive dep pollution, cascade through library imports, permanent replace workarounds), the canonical `tools.env` source-of-truth, `go run pkg@$(VERSION)` invocation pattern, `//go:generate` directive update, the 7-step migration procedure, dependency-tree-based migration order, and pitfalls (gosec "dev" cosmetic, `go run` ignoring local replaces, `go mod tidy -e` truncation, osv-scanner v2.3.2+ broken upstream).
- Add canonical `templates/tools.env` listing the version pin for every CLI tool (addlicense, counterfeiter, errcheck, ginkgo, goimports-reviser, golangci-lint, golines, go-modtool, gosec, govulncheck, osv-scanner). Pinned `OSV_SCANNER_VERSION=v2.3.1` since v2.3.2+ is broken upstream.
- Update `templates/Makefile.library` and `templates/Makefile.service` to `include tools.env` and use `go run pkg@$(VERSION)` everywhere instead of `go run -mod=mod pkg`. Switch `golangci-lint` import path to v2 (`github.com/golangci/golangci-lint/v2/cmd/golangci-lint`).
- Remove `templates/tools.go` — superseded by the `tools.env` + Makefile pattern.

## v0.8.0

- Add `docs/go-state-machine-pattern.md` covering the phase-dispatched state machine pattern for long-running, resumable, multi-process workflows. Documents core structure (Phase enum, Status enum, Result envelope, dispatcher), Status-vs-Phase distinction with controller persistence rule, heterogeneous phases (pure-Go and external runners), external controller contract, four backward-edge patterns (Interventional Reset, Phase Unrolling, Sub-Phase loop, Circuit Breaker), parallel sub-phases via `bborbe/run`, anti-patterns with paired `[GOOD]`/`[BAD]` examples, and testing guidance. Generic Order/Customer/Product domain throughout. Indexed in README.md and llms.txt under Go Architecture & Patterns. Reference-only guide (no matching agent — fits CLAUDE.md exemption for pattern guides).

## v0.7.1

- Extend `docs/go-build-args-guide.md` with a "Vendor handling" section clarifying that `go mod vendor` is a build-time concern, not a precommit concern. `vendor/` is gitignored in the canonical layout; `Makefile.precommit`'s `ensure` target deletes any lingering `vendor/` and uses `-mod=mod`; `Makefile.docker`'s `build` target regenerates vendor just-in-time before `docker build`. Automation that edits Go code (dark-factory prompts, CI stages) should run `go mod tidy` when deps change but NEVER `go mod vendor` — the precommit step wipes it out immediately after. Prevents ~1–2 min of wasted time per prompt execution in repos that follow this pattern.

## v0.7.0

- Add `docs/go-build-args-guide.md` covering the three standard build-time injection values — `BUILD_GIT_VERSION` (from `git describe --tags --always --dirty`), `BUILD_GIT_COMMIT` (from `git rev-parse --short HEAD`), and `BUILD_DATE` — across all four participating files per service: `Makefile.docker` build-args, `Dockerfile` ARG/ENV/LABEL blocks (with OCI `org.opencontainers.image.*` labels), the Argument struct with matching `env:` tags, and the startup log. Integrates with the shared `github.com/bborbe/metrics` v0.5.0 package's `BuildInfoMetrics` helper — publishes a single `build_info{version, commit}` gauge whose value is the build timestamp in Unix seconds, with service identification via the Prometheus `job` label. Includes a rollout checklist and canonical PromQL queries for deployment-age alerting and rollout-state visibility.

## v0.6.0

- Add `docs/go-mod-replace-guide.md` covering when to use `replace` in `go.mod` (monorepo siblings yes, cross-repo no) with GOOD/BAD examples and antipatterns.
- Add `docs/k8s-manifest-guide.md` covering Kubernetes manifest layout: `k8s/` folder next to code, one-resource-per-file, type-suffix filename convention (`-deploy.yaml`, `-svc.yaml`, etc.), env-substituted placeholder pattern (`{{ "KEY" | env }}`), thin Makefile delegating to shared fragments, secret templating, and antipatterns. Aligned with `github.com/bborbe/go-skeleton/k8s` reference layout.
- Expand `docs/go-kubernetes-crd-controller-guide.md` §2a with a naming convention section (group/kind/plural/scope rules) and rewrite §3 code generation setup: `tools.go` pins `k8s.io/code-generator` via `cmd/validation-gen` import, and `hack/update-codegen.sh` sources `kube_codegen.sh` from `$GOMODCACHE` (resolved via `go list -m -f '{{.Dir}}'`) instead of `vendor/` — since shell scripts aren't vendored by `go mod vendor`. Drops the `go mod vendor` prerequisite from the workflow.
- Update `docs/go-mocking-guide.md` to require package-prefixed test suite filenames (`<package>_suite_test.go`) matching Ginkgo's `ginkgo bootstrap` default; removes bare `suite_test.go` references across the guide.

## v0.5.0

- Add `go-architecture-assistant` + `python-architecture-assistant` agents plus `/coding:audit-architecture` command. Detect naive extractions (helpers pulled out just to satisfy `funlen`/`C901` — called once, generic names, same-file same-type), package/module boundary violations, dependency direction errors, layering leaks, and missing abstraction seams. Wired into `/coding:code-review full` alongside `srp-checker` (unit-level SRP stays there; architecture agents cover cross-unit).
- Both agents include a `Concrete patterns` section with 6 (Go) / 5 (Python) high-confidence rules distilled from real-codebase audits: (1) committed `.bak`/`.orig` backup files, (2) dead abstraction (interface/Protocol + impl + zero external callers), (3) empty-chain seam (interface method whose chain is always empty — silent noop), (4) repetitive decode/apply god function (5+ `if key in data { parse; assign }` blocks → apply-map or patch DTO), (5) Go-only: god factory file vs composition root (false-positive guard: free-function factory files >500 LoC are legitimate composition roots, split by subsystem not by package), (6) typos in exported API (`Exectuor`, `Recieve`, etc.). Each rule has deterministic detection commands, generic examples (User/Order only), structural fixes, and false-positive guards.

## v0.4.2

- Enforce package-prefix convention for all counterfeiter mock filenames and `--fake-name` values across `go-mocking-guide.md`, `go-patterns.md`, `go-architecture-patterns.md`, `go-prometheus-metrics-guide.md`, and `go-kubernetes-crd-controller-guide.md`. Prevents collisions in the flat `mocks/` directory when two packages export interfaces with the same name (e.g. `formatter.Formatter` vs `status.Formatter`).
- Update k8s CRD guide snippet with example showing `controller-k8s-connector.go` / `ControllerK8sConnector` naming.

## v0.4.1

- Scrub `go-kubernetes-crd-controller-guide.md` of employer-internal references (sm-octopus, trading examples); replace with public bborbe repo references (bborbe/alert, bborbe/cqrs) and generic example domains
- Fix invalid Go syntax `XPreserveUnknownFields: &true` → `ptr.To(true)` using `k8s.io/utils/ptr`
- Rename "What to NOT do" heading to "Antipatterns" per guide style

## v0.4.0

- Add `go-kubernetes-crd-controller-guide.md` covering CRD types, generated clientset, self-install, event-handler pattern, and deliberate exclusions (no Lister, no WaitForCacheSync, no separate YAML manifest)
- Add `/coding:audit-guide` command + `guide-auditor` agent for auditing coding guides against style/structure/indexing/self-containment standards; explicit forbidden-term grep blocks work-context leakage (seibert, octopus, trading domain, personal paths)
- Improve `go-time-injection.md`

## v0.3.1

- Fix agent paths to use canonical plugin path `~/.claude/plugins/marketplaces/coding/docs/`
- Clarify definition-of-done to follow all guides, not just language-specific ones

## v0.3.0

- Rewrite README.md per readme-guide.md (add Overview, Requirements, Quick Start, Contributing; CI and license badges; collapse agents into details; reorder commands; fix license to BSD-2-Clause)
- Add GitHub Actions CI workflow running `make precommit` on push and PRs
- Fix Makefile check-links silent-fail bug (pipe subshell swallowed `EXIT=1`) and allow directory links (`-f` → `-e`); strip anchors before check
- Add `check-json` target validating `.claude-plugin/plugin.json`
- Add sentinel error naming convention (`ErrXxx`) and backwards-compat alias pattern to go-error-wrapping-guide.md

## v0.2.2

- commit: Read project CLAUDE.md as step 2 of detection — honors project-specific release checklists (extra files to bump, version-sync rules) that the generic workflow would otherwise miss

## v0.2.1

- Add go-mod dependency fix guide
- Skip license checks for private repos
- Improve factory guide
- Sync plugin version to v0.2.0 and add release checklist to CLAUDE.md
- Improve /commit to detect unreleased commits since last tag on clean working tree

## v0.2.0

- Add readme-guide.md and claude-md-guide.md for README.md vs CLAUDE.md separation
- Update documentation-guide.md with CLAUDE.md overview and links to specific guides

## v0.1.0
- Add finder agents for self-contained check-guides
- Add templates, remove personal paths from agents
- Add vscode and intellij skills, archive old commands
- Add go-write-test, improve-guide, go-version commands with agents
- Remove personal paths from shared plugin docs
- Add 6 metrics patterns to prometheus guide
- Split go-quality-assistant into focused agents aligned with docs
- Add vendor counterfeiter detection to go-test-quality-assistant
- Add file organization rules to go-quality-assistant

## v0.0.3
- Make plugin self-contained: add all agents referenced by commands
- Add coding: prefix to agent references in commands
- Add pre-implementation-assistant, license-assistant, godoc-assistant, go-version-manager, shellcheck-assistant

## v0.0.2
- Trim to 4 essential commands: code-review, pr-review, check-guides, commit
- Trim to 12 agents required by those commands
- Remove 9 non-essential commands and 10 unused agents

## v0.0.1
- Restructure as Claude Code plugin with .claude-plugin/ metadata
- Move all guides into docs/ subdirectory
- Add 12 shareable slash commands (code-review, pr-review, check-guides, etc.)
- Add 22 shareable agents (go-quality-assistant, srp-checker, etc.)
- Add llms.txt index for AI agent discovery
- Add Makefile with link validation
- Rewrite README as human-first reference with tables
