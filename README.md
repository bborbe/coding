# Coding

[![CI](https://github.com/bborbe/coding/actions/workflows/ci.yml/badge.svg)](https://github.com/bborbe/coding/actions/workflows/ci.yml)
[![License: BSD-2-Clause](https://img.shields.io/badge/License-BSD--2--Clause-blue.svg)](LICENSE)

Opinionated coding guidelines, quality review agents, and slash commands for Go and Python — packaged as a [Claude Code](https://docs.claude.com/claude-code) plugin.

## Overview

Writing consistent, idiomatic code across a large codebase is hard. This plugin bundles 50+ opinionated guides (Go architecture, error handling, testing, HTTP handlers, Python structure, Git workflow, documentation) together with specialized Claude Code agents that enforce them on your code. Install once, then run `/coding:code-review` or `/coding:pr-review` to review your work against the full ruleset.

## Requirements

- [Claude Code](https://docs.claude.com/claude-code) CLI installed

## Install

```bash
claude plugin marketplace add bborbe/coding
claude plugin install coding
```

Update:

```bash
claude plugin marketplace update coding
claude plugin update coding@coding
```

## Quick Start

Review your current branch against all guidelines:

```
/coding:pr-review
```

Review code in standard mode (7 agents) or full mode (14 agents):

```
/coding:code-review standard
/coding:code-review full
```

Find relevant guides before starting work:

```
/coding:check-guides "add Prometheus metrics to HTTP handler"
```

Commit with changelog and version bump:

```
/coding:commit
```

## Commands

| Command | Description |
|---------|-------------|
| `/coding:pr-review` | Review pull request diff against standards |
| `/coding:code-review [short\|standard\|full]` | Review code against guidelines (standard: 7 agents, full: 14) |
| `/coding:check-guides "task"` | Find relevant guides before implementation |
| `/coding:commit` | Git commit with changelog and versioning |
| `/coding:go-write-test [basic\|standard\|integration]` | Generate Go tests for changed files |
| `/coding:go-version [check\|update]` | Check/update Go version across project files |
| `/coding:improve-guide [file]` | Refactor guide into structured rule sets |
| `/coding:audit-guide [file]` | Audit guide against style, structure, and indexing |
| `/coding:vscode [dir]` | Open VS Code in directory |
| `/coding:intellij [dir]` | Open IntelliJ IDEA in directory |

## Guides

All guides live in [`docs/`](docs/) and can be read standalone without the plugin.

### Go — Architecture & Patterns

| Guide | Description |
|-------|-------------|
| [Architecture Patterns](docs/go-architecture-patterns.md) | Interface → Constructor → Struct → Method |
| [Service Implementation](docs/go-service-implementation-patterns.md) | Decision frameworks, type design |
| [Factory Pattern](docs/go-factory-pattern.md) | Dependency composition |
| [Functional Options](docs/go-functional-options-pattern.md) | Flexible constructors |
| [Functional Composition](docs/go-functional-composition-pattern.md) | Composable function types |
| [Enum Pattern](docs/go-enum-type-pattern.md) | String-based enums |
| [Filter Pattern](docs/go-filter-pattern.md) | Composable predicates |
| [Parse Pattern](docs/go-parse-pattern.md) | Custom type conversion |
| [CQRS](docs/go-cqrs.md) | Command Query Separation |
| [Composition](docs/go-composition.md) | Struct embedding |
| [Concurrency](docs/go-concurrency-patterns.md) | Goroutines, channels |
| [State Machine](docs/go-state-machine-pattern.md) | Phase-dispatched workflows, resumable multi-step processes |

### Go — Code Quality

| Guide | Description |
|-------|-------------|
| [Error Wrapping](docs/go-error-wrapping-guide.md) | bborbe/errors patterns |
| [Context Cancellation](docs/go-context-cancellation-in-loops.md) | ctx.Done() in loops |
| [Time Injection](docs/go-time-injection.md) | bborbe/time, CurrentDateTimeGetter |
| [GoDoc](docs/go-doc-best-practices.md) | Documentation standards |
| [Logging](docs/go-logging-guide.md) | Structured logging |
| [Design Patterns](docs/go-patterns.md) | Common Go patterns |

### Go — Testing

| Guide | Description |
|-------|-------------|
| [Testing Guide](docs/go-testing-guide.md) | Ginkgo v2 + Gomega |
| [Test Types](docs/go-test-types-guide.md) | Unit vs integration vs e2e |
| [Mocking Guide](docs/go-mocking-guide.md) | Counterfeiter patterns |
| [TDD Guide](docs/tdd-guide.md) | Red-green-refactor |

### Go — Infrastructure

| Guide | Description |
|-------|-------------|
| [Makefile Commands](docs/go-makefile-commands.md) | Build targets |
| [Build Args](docs/go-build-args-guide.md) | BUILD_GIT_VERSION / BUILD_GIT_COMMIT / BUILD_DATE injection + Prometheus `build_info` |
| [Library Guide](docs/go-library-guide.md) | Library structure |
| [CLI Guide](docs/go-cli-guide.md) | CLI patterns |
| [Validation](docs/go-validation-framework-guide.md) | Input validation |
| [Prometheus Metrics](docs/go-prometheus-metrics-guide.md) | Metrics implementation |
| [Licensing](docs/go-licensing-guide.md) | License management |
| [Precommit](docs/go-precommit.md) | Pre-commit workflow |
| [Replace Directive](docs/go-mod-replace-guide.md) | When to use `replace` in go.mod |
| [Linting](docs/go-linting-guide.md) | Static analysis |
| [Security Linting](docs/go-security-linting.md) | Security analysis |
| [Kubernetes CRD Controller](docs/go-kubernetes-crd-controller-guide.md) | CRD types, informer, self-install |
| [Kubernetes Manifest Layout](docs/k8s-manifest-guide.md) | `k8s/` folder, filename suffixes, templating |

### Go — HTTP & APIs

| Guide | Description |
|-------|-------------|
| [HTTP Handlers](docs/go-http-handler-refactoring-guide.md) | Handler organization |
| [JSON Error Handler](docs/go-json-error-handler-guide.md) | Structured error responses |

### Python

| Guide | Description |
|-------|-------------|
| [Project Structure](docs/python-project-structure.md) | src/ layout, pyproject.toml |
| [Architecture](docs/python-architecture-patterns.md) | Constructor injection |
| [Factory Pattern](docs/python-factory-pattern.md) | Dependency composition |
| [IoC / DI](docs/python-ioc-guide.md) | Protocol vs ABC |
| [Pydantic](docs/python-pydantic-guide.md) | Data validation |
| [Logging](docs/python-logging-guide.md) | Structured logging |
| [CLI Arguments](docs/python-cli-arguments-guide.md) | argparse, BaseSettings |
| [Makefile Commands](docs/python-makefile-commands.md) | Build targets |

### Workflows & Documentation

| Guide | Description |
|-------|-------------|
| [Git Commit](docs/git-commit-guide.md) | Commit workflow |
| [Git Workflow](docs/git-workflow.md) | Branching strategy |
| [Changelog](docs/changelog-guide.md) | CHANGELOG.md format |
| [Definition of Done](docs/definition-of-done.md) | Completion checklist |
| [Documentation Guide](docs/documentation-guide.md) | README, docs/, PRDs |
| [README Guide](docs/readme-guide.md) | README.md standards |
| [PRD Guide](docs/prd-guide.md) | Product Requirements |
| [ADR Guide](docs/adr-guide.md) | Architecture Decisions |
| [Markdown & Todos](docs/markdown-todo-guide.md) | Formatting standards |

### Frontend

| Guide | Description |
|-------|-------------|
| [Vue 3 + TypeScript](docs/vue3-typescript-frontend-guide.md) | Composition API, Vite |
| [Astro](docs/astro-development-guide.md) | Astro framework |

## Agents

Agents are invoked by commands — you rarely call them directly. Each reads its matching guide as source of truth.

<details>
<summary><b>Go Quality (standard mode, 7 agents)</b></summary>

| Agent | Doc | Checks |
|-------|-----|--------|
| `go-quality-assistant` | `go-architecture-patterns.md` | Naming, file layout, logging, concurrency, transactions |
| `go-context-assistant` | `go-context-cancellation-in-loops.md` | context.Background(), missing ctx.Done() in loops |
| `go-error-assistant` | `go-error-wrapping-guide.md` | fmt.Errorf, bare return err, missing wrapping |
| `go-time-assistant` | `go-time-injection.md` | time.Time in structs, time.Now() in production |
| `go-factory-pattern-assistant` | `go-factory-pattern.md` | Factory compliance, zero-business-logic |
| `go-http-handler-assistant` | `go-http-handler-refactoring-guide.md` | Handler organization, inline detection |
| `go-test-coverage-assistant` | `go-testing-guide.md` | Test coverage gaps |

</details>

<details>
<summary><b>Go Quality (full mode adds 8 more)</b></summary>

| Agent | Doc | Checks |
|-------|-----|--------|
| `go-metrics-assistant` | `go-prometheus-metrics-guide.md` | Metric types, naming, labels, pre-init |
| `godoc-assistant` | `go-doc-best-practices.md` | GoDoc completeness and format |
| `go-test-quality-assistant` | `go-testing-guide.md` | Ginkgo/Gomega patterns, mock usage |
| `go-security-specialist` | `go-security-linting.md` | Vulnerabilities, OWASP |
| `srp-checker` | — | Single Responsibility Principle (unit-level) |
| `go-architecture-assistant` | — | Cross-unit architecture, naive extractions, layering, boundaries |
| `go-version-manager` | — | Go version currency |
| `go-tooling-assistant` | `go-makefile-commands.md` | Makefile, tools.go |

</details>

<details>
<summary><b>Other agents</b></summary>

| Agent | Description |
|-------|-------------|
| `license-assistant` | LICENSE file, headers, README section |
| `readme-quality-assistant` | README.md completeness |
| `shellcheck-assistant` | Shell script quality |
| `python-quality-assistant` | Python code quality |
| `python-architecture-assistant` | Cross-module architecture, naive extractions, layering, boundaries |
| `context7-library-checker` | Library API currency |
| `go-test-writer-assistant` | Generate Go tests |
| `guide-improvement-assistant` | Refactor guides |
| `guide-auditor` | Audit guides against style/structure/indexing |
| `simple-bash-runner` | Run build commands |
| `pre-implementation-assistant` | Find relevant guides |
| `coding-guidelines-finder` | Search docs/ |
| `project-docs-finder` | Search project docs/ |

</details>

## Contributing

Issues and pull requests welcome at [github.com/bborbe/coding](https://github.com/bborbe/coding).

Guides are the source of truth — agents enforce them. To propose a rule change, edit the relevant file in `docs/` and open a PR.

## License

BSD-2-Clause. See [LICENSE](LICENSE).
