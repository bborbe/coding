# Coding

Coding guidelines, quality agents, and slash commands for Go and Python development. Install as Claude Code plugin for automated code review.

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

## Commands

| Command | Description |
|---------|-------------|
| `/coding:code-review [short\|standard\|full]` | Review code against guidelines (standard: 7 agents, full: 14) |
| `/coding:pr-review` | Review pull request diff against standards |
| `/coding:check-guides "task"` | Find relevant guides before implementation |
| `/coding:commit` | Git commit with changelog and versioning |
| `/coding:go-write-test [basic\|standard\|integration]` | Generate Go tests for changed files |
| `/coding:go-version [check\|update]` | Check/update Go version across project files |
| `/coding:improve-guide [file]` | Refactor guide into structured rule sets |
| `/coding:vscode [dir]` | Open VS Code in directory |
| `/coding:intellij [dir]` | Open IntelliJ IDEA in directory |

## Agents

Agents are invoked by commands. Each reads its matching doc as source of truth.

### Go Quality (standard mode)

| Agent | Doc | Checks |
|-------|-----|--------|
| `go-quality-assistant` | `go-architecture-patterns.md` | Naming, file layout, logging, concurrency, transactions |
| `go-context-assistant` | `go-context-cancellation-in-loops.md` | context.Background(), missing ctx.Done() in loops |
| `go-error-assistant` | `go-error-wrapping-guide.md` | fmt.Errorf, bare return err, missing wrapping |
| `go-time-assistant` | `go-time-injection.md` | time.Time in structs, time.Now() in production |
| `go-factory-pattern-assistant` | `go-factory-pattern.md` | Factory compliance, zero-business-logic |
| `go-http-handler-assistant` | `go-http-handler-refactoring-guide.md` | Handler organization, inline detection |
| `go-test-coverage-assistant` | `go-testing-guide.md` | Test coverage gaps |

### Go Quality (full mode adds)

| Agent | Doc | Checks |
|-------|-----|--------|
| `go-metrics-assistant` | `go-prometheus-metrics-guide.md` | Metric types, naming, labels, pre-init |
| `godoc-assistant` | `go-doc-best-practices.md` | GoDoc completeness and format |
| `go-test-quality-assistant` | `go-testing-guide.md` | Ginkgo/Gomega patterns, mock usage |
| `go-security-specialist` | `go-security-linting.md` | Vulnerabilities, OWASP |
| `srp-checker` | — | Single Responsibility Principle |
| `go-version-manager` | — | Go version currency |
| `go-tooling-assistant` | `go-makefile-commands.md` | Makefile, tools.go |

### Other

| Agent | Description |
|-------|-------------|
| `license-assistant` | LICENSE file, headers, README section |
| `readme-quality-assistant` | README.md completeness |
| `shellcheck-assistant` | Shell script quality |
| `python-quality-assistant` | Python code quality |
| `context7-library-checker` | Library API currency |
| `go-test-writer-assistant` | Generate Go tests |
| `guide-improvement-assistant` | Refactor guides |
| `simple-bash-runner` | Run build commands |
| `pre-implementation-assistant` | Find relevant guides |
| `coding-guidelines-finder` | Search docs/ |
| `project-docs-finder` | Search project docs/ |

## Guides

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
| [Library Guide](docs/go-library-guide.md) | Library structure |
| [CLI Guide](docs/go-cli-guide.md) | CLI patterns |
| [Validation](docs/go-validation-framework-guide.md) | Input validation |
| [Prometheus Metrics](docs/go-prometheus-metrics-guide.md) | Metrics implementation |
| [Licensing](docs/go-licensing-guide.md) | License management |
| [Precommit](docs/go-precommit.md) | Pre-commit workflow |
| [Linting](docs/go-linting-guide.md) | Static analysis |
| [Security Linting](docs/go-security-linting.md) | Security analysis |

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
| [PRD Guide](docs/prd-guide.md) | Product Requirements |
| [ADR Guide](docs/adr-guide.md) | Architecture Decisions |
| [Markdown & Todos](docs/markdown-todo-guide.md) | Formatting standards |

### Frontend

| Guide | Description |
|-------|-------------|
| [Vue 3 + TypeScript](docs/vue3-typescript-frontend-guide.md) | Composition API, Vite |
| [Astro](docs/astro-development-guide.md) | Astro framework |

## License

BSD-style license. See [LICENSE](LICENSE) file.
