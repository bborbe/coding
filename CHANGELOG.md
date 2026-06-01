# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## Unreleased

- feat(rules): add four `### RULE` blocks to `docs/go-security-linting.md` — `go-security/file-perms-too-permissive`, `go-security/dir-perms-too-permissive`, `go-security/nosec-requires-reason`, `go-security/chmod-return-checked`; matching ast-grep YAMLs + `rules/index.json` entries

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
