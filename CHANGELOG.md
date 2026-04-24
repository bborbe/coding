# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

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
