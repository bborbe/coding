# Coding Guidelines

Standardized coding guidelines, patterns, and workflows for Go and Python development.

## Go

### Architecture & Design Patterns

| Guide | Description |
|-------|-------------|
| [Architecture Patterns](docs/go-architecture-patterns.md) | Interface → Constructor → Struct → Method pattern, dependency injection |
| [Service Implementation](docs/go-service-implementation-patterns.md) | Decision frameworks, type design, package organization |
| [Factory Pattern](docs/go-factory-pattern.md) | Dependency composition with zero business logic |
| [Functional Options](docs/go-functional-options-pattern.md) | Flexible constructor configuration |
| [Functional Composition](docs/go-functional-composition-pattern.md) | Composable function and list types |
| [Enum Pattern](docs/go-enum-type-pattern.md) | String-based enums with validation |
| [Filter Pattern](docs/go-filter-pattern.md) | Composable collection predicates |
| [Parse Pattern](docs/go-parse-pattern.md) | Custom type conversion and unmarshaling |
| [CQRS](docs/go-cqrs.md) | Command Query Responsibility Segregation |
| [Composition](docs/go-composition.md) | Struct embedding and interface composition |
| [Concurrency](docs/go-concurrency-patterns.md) | Goroutines, channels, sync primitives |

### Testing & Quality

| Guide | Description |
|-------|-------------|
| [Testing Guide](docs/go-testing-guide.md) | Ginkgo v2 + Gomega syntax, BDD patterns |
| [Test Types](docs/go-test-types-guide.md) | Unit vs integration vs e2e decision framework |
| [Mocking Guide](docs/go-mocking-guide.md) | Counterfeiter patterns, what to mock |
| [TDD Guide](docs/tdd-guide.md) | Red-green-refactor cycle |
| [Linting](docs/go-linting-guide.md) | Static analysis configuration |
| [Security Linting](docs/go-security-linting.md) | Security-focused static analysis |

### Infrastructure & Tools

| Guide | Description |
|-------|-------------|
| [Makefile Commands](docs/go-makefile-commands.md) | Standardized build targets |
| [Library Guide](docs/go-library-guide.md) | Library structure, versioning, API design |
| [CLI Guide](docs/go-cli-guide.md) | Command-line application patterns |
| [Validation](docs/go-validation-framework-guide.md) | Input validation framework |
| [Prometheus Metrics](docs/go-prometheus-metrics-guide.md) | Metrics implementation and naming |
| [Licensing](docs/go-licensing-guide.md) | License files, headers, addlicense tool |
| [Precommit](docs/go-precommit.md) | Pre-commit checks and workflow |
| [Time Injection](docs/go-time-injection.md) | Testable time handling via DI |

### HTTP & APIs

| Guide | Description |
|-------|-------------|
| [HTTP Handlers](docs/go-http-handler-refactoring-guide.md) | Handler organization and refactoring |
| [JSON Error Handler](docs/go-json-error-handler-guide.md) | Structured error responses for APIs |

### Code Style & Documentation

| Guide | Description |
|-------|-------------|
| [GoDoc](docs/go-doc-best-practices.md) | Documentation comment standards |
| [Error Wrapping](docs/go-error-wrapping-guide.md) | Context-aware error handling |
| [Context Cancellation](docs/go-context-cancellation-in-loops.md) | Non-blocking select in loops |
| [Logging](docs/go-logging-guide.md) | Structured logging patterns |
| [Design Patterns](docs/go-patterns.md) | Common Go design patterns |

## Python

| Guide | Description |
|-------|-------------|
| [Project Structure](docs/python-project-structure.md) | src/ layout, pyproject.toml, uv |
| [Architecture Patterns](docs/python-architecture-patterns.md) | Constructor injection, composition root |
| [Factory Pattern](docs/python-factory-pattern.md) | Dependency composition |
| [IoC / Dependency Injection](docs/python-ioc-guide.md) | Protocol vs ABC, async patterns |
| [Pydantic](docs/python-pydantic-guide.md) | Data validation, BaseSettings |
| [Logging](docs/python-logging-guide.md) | Structured logging, safe secrets |
| [CLI Arguments](docs/python-cli-arguments-guide.md) | argparse, BaseSettings, typer |
| [Makefile Commands](docs/python-makefile-commands.md) | Build targets (uv, ruff, mypy, pytest) |

## Development Workflows

| Guide | Description |
|-------|-------------|
| [Git Commit](docs/git-commit-guide.md) | Commit workflow, CHANGELOG, message format |
| [Git Workflow](docs/git-workflow.md) | Branching strategy, PR process |
| [Changelog](docs/changelog-guide.md) | CHANGELOG.md format and maintenance |
| [Definition of Done](docs/definition-of-done.md) | Checklist for completed work |

## Frontend

| Guide | Description |
|-------|-------------|
| [Vue 3 + TypeScript](docs/vue3-typescript-frontend-guide.md) | Composition API, Vite, Vitest |
| [Astro](docs/astro-development-guide.md) | Astro framework patterns |

## Documentation

| Guide | Description |
|-------|-------------|
| [Documentation Guide](docs/documentation-guide.md) | README, docs/, PRDs, ADRs |
| [PRD Guide](docs/prd-guide.md) | Product Requirements Documents |
| [ADR Guide](docs/adr-guide.md) | Architecture Decision Records |
| [Markdown & Todos](docs/markdown-todo-guide.md) | Formatting standards |

## Claude Code Plugin

This repo is also a [Claude Code plugin](https://docs.anthropic.com/en/docs/claude-code/plugins). Install it to get coding guidelines, code review commands, and quality agents directly in Claude Code.

```bash
# Add as marketplace
/plugin marketplace add bborbe/coding

# Install plugin
/plugin install coding@coding
```

**Included commands:** `/coding:code-review`, `/coding:pr-review`, `/coding:check-guides`, `/coding:godoc`, `/coding:go-write-test`, `/coding:go-version`, `/coding:doc-review`, `/coding:improve-guide`

**Included agents:** go-quality-assistant, go-test-quality-assistant, go-security-specialist, srp-checker, python-quality-assistant, and more.

## License

BSD-style license. See [LICENSE](LICENSE) file for details.
