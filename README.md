# AI Coding Guidelines

This repository contains standardized coding guidelines, patterns, and workflows specifically designed for AI agents working with Benjamin Borbe's Go ecosystem and development environment.

## Purpose

This repository serves as a comprehensive reference for AI agents (like Claude Code) to ensure consistent, high-quality code generation and development practices. It provides structured guidelines that help AI agents understand established patterns, avoid common mistakes, and integrate seamlessly with existing codebases.

---

## Table of Contents

- [Core Go Development Guidelines](#core-go-development-guidelines)
  - [Architecture & Design Patterns](#architecture--design-patterns)
  - [Testing & Quality](#testing--quality)
  - [Infrastructure & Tools](#infrastructure--tools)
  - [HTTP & APIs](#http--apis)
  - [Documentation & Code Quality](#documentation--code-quality)
- [Python Development Guidelines](#python-development-guidelines)
- [Development Workflows](#development-workflows)
- [Frontend Development](#frontend-development)
- [Documentation Standards](#documentation-standards)
- [Key Ecosystem Libraries](#key-ecosystem-libraries)
- [For AI Agents](#for-ai-agents)
- [Usage](#usage)
- [License](#license)

---

## Core Go Development Guidelines

### Architecture & Design Patterns

- **[go-architecture-patterns.md](go-architecture-patterns.md)** - Core service architecture using Interface → Constructor → Struct → Method pattern with dependency injection and ecosystem integration
- **[go-factory-pattern.md](go-factory-pattern.md)** - Factory function patterns for dependency composition with zero business logic, file organization, and naming conventions
- **[go-service-implementation-patterns.md](go-service-implementation-patterns.md)** - Decision frameworks for service architecture, type design patterns, and implementation best practices
- **[go-functional-composition-pattern.md](go-functional-composition-pattern.md)** - Functional composition patterns for implementing interfaces using composable function and list types
- **[go-functional-options-pattern.md](go-functional-options-pattern.md)** - Functional options pattern for flexible constructor configuration and optional parameters
- **[go-enum-type-pattern.md](go-enum-type-pattern.md)** - String-based enum pattern with type-safe constants, validation, and collection operations
- **[go-filter-pattern.md](go-filter-pattern.md)** - Filter pattern for collection operations and data filtering with composable predicates
- **[go-parse-pattern.md](go-parse-pattern.md)** - Parse pattern for custom type conversion, unmarshaling, and string-to-type transformation
- **[go-context-cancellation-in-loops.md](go-context-cancellation-in-loops.md)** - Context cancellation pattern for long-running loops with non-blocking select checks

### Testing & Quality

- **[go-testing-guide.md](go-testing-guide.md)** - How to write tests with Ginkgo v2 and Gomega framework syntax, test suite setup, and BDD patterns
- **[go-test-types-guide.md](go-test-types-guide.md)** - What to test and when: unit vs integration vs end-to-end test definitions and decision framework
- **[go-mocking-guide.md](go-mocking-guide.md)** - Mocking patterns with Counterfeiter, mock discovery strategies, and what to mock vs not mock
- **[tdd-guide.md](tdd-guide.md)** - Test-driven development workflow with red-green-refactor cycle

### Infrastructure & Tools

- **[go-library-guide.md](go-library-guide.md)** - Library project structure, versioning, public API design, and release management
- **[go-validation-framework-guide.md](go-validation-framework-guide.md)** - Input validation patterns, error handling, and validation framework design
- **[go-prometheus-metrics-guide.md](go-prometheus-metrics-guide.md)** - Prometheus metrics implementation, naming conventions, and best practices
- **[go-makefile-commands.md](go-makefile-commands.md)** - Standardized Makefile targets for builds, testing, code quality, and license management
- **[go-licensing-guide.md](go-licensing-guide.md)** - Licensing practices including LICENSE files, README sections, source headers, and addlicense tool
- **[go-glog.md](go-glog.md)** - Structured logging with glog, log levels, and contextual logging practices

### HTTP & APIs

- **[go-http-handler-refactoring-guide.md](go-http-handler-refactoring-guide.md)** - HTTP handler organization, refactoring patterns, and architectural guidelines
- **[go-json-error-handler-guide.md](go-json-error-handler-guide.md)** - Standardized JSON error responses for HTTP APIs with error codes, status mapping, and structured details

### Documentation & Code Quality

- **[go-doc-best-practices.md](go-doc-best-practices.md)** - GoDoc standards, documentation comments, and API documentation best practices

---

## Python Development Guidelines

- **[python-architecture-patterns.md](python-architecture-patterns.md)** - Core service architecture with constructor injection, main.py composition root, and file organization
- **[python-factory-pattern.md](python-factory-pattern.md)** - Factory function patterns for dependency composition with zero business logic, file organization, and naming conventions
- **[python-ioc-guide.md](python-ioc-guide.md)** - Detailed dependency injection patterns with Protocol vs ABC, async patterns, testing with mocks, and when to use DI
- **[python-pydantic-guide.md](python-pydantic-guide.md)** - Data validation with Pydantic for API boundaries, configuration management, and external data validation
- **[python-logging-guide.md](python-logging-guide.md)** - Logging patterns with structured formats, log levels, safe secret handling, and production integration
- **[python-cli-arguments-guide.md](python-cli-arguments-guide.md)** - CLI argument parsing and environment variable handling with Pydantic BaseSettings, argparse, and typer
- **[python-makefile-commands.md](python-makefile-commands.md)** - Standardized Makefile targets for Python projects including builds, testing, code quality, and dependency management

---

## Development Workflows

- **[git-commit-guide.md](git-commit-guide.md)** - Git commit workflow and reference covering mandatory processes (make precommit, CHANGELOG), message format, repository configuration, and troubleshooting

---

## Frontend Development

- **[vue3-typescript-frontend-guide.md](vue3-typescript-frontend-guide.md)** - Vue 3 + TypeScript patterns with Composition API, Vite setup, and Vitest testing
- **[astro-development-guide.md](astro-development-guide.md)** - Astro framework development guidelines and best practices

---

## Documentation Standards

- **[documentation-guide.md](documentation-guide.md)** - Comprehensive guide for documentation structure (README, docs/, PRDs, ADRs) with AI context principles
- **[prd-guide.md](prd-guide.md)** - Product Requirements Document templates, best practices, and when to create PRDs
- **[adr-guide.md](adr-guide.md)** - Architecture Decision Records guide with templates, organization patterns, and status management
- **[markdown-todo-guide.md](markdown-todo-guide.md)** - Markdown formatting standards and todo management patterns

---

## Key Ecosystem Libraries

These guidelines emphasize integration with Benjamin Borbe's ecosystem libraries. Each library solves specific problems and has clear usage patterns:

- **`github.com/bborbe/time`** - Time handling with dependency injection
  - **When:** Any code that needs current time (enables deterministic testing)
  - **Pattern:** Inject `libtime.CurrentDateTime` interface, use `.Now()` method
  - **Replaces:** Direct `time.Now()` calls

- **`github.com/bborbe/collection`** - Pointer utilities and collection helpers
  - **When:** Creating pointers to literals (`collection.Ptr("value")`)
  - **Replaces:** Custom `stringPtr()`, `intPtr()` helper functions
  - **Also provides:** Filter, Map, Reduce operations for slices

- **`github.com/bborbe/errors`** - Context-aware error wrapping and handling
  - **When:** All error handling that needs context propagation
  - **Pattern:** `errors.Wrap(ctx, err, "description")`
  - **Replaces:** Standard `fmt.Errorf()` for better error chains

- **`github.com/bborbe/http`** - HTTP utilities with JSON error handling
  - **When:** Building HTTP APIs that need structured error responses
  - **Pattern:** `libhttp.NewJSONErrorHandler(handler)` with `WrapWithCode/WrapWithDetails`
  - **See:** [go-json-error-handler-guide.md](go-json-error-handler-guide.md)

- **Ginkgo v2 + Gomega** - BDD-style testing framework with expressive assertions
  - **When:** All test files (replaces standard `testing` package patterns)
  - **Pattern:** `Describe/Context/It` structure with `Expect()` assertions
  - **See:** [go-testing-guide.md](go-testing-guide.md)

- **Counterfeiter** - Type-safe mock generation for interfaces
  - **When:** Unit tests requiring dependency mocks
  - **Pattern:** `//counterfeiter:generate` directive, use generated fakes
  - **See:** [go-mocking-guide.md](go-mocking-guide.md)

---

## For AI Agents

This repository is specifically structured to help AI agents:

1. **Understand established patterns** - Clear examples of preferred architectures and implementations
2. **Avoid common antipatterns** - Explicit guidance on what NOT to do
3. **Integrate with existing code** - Patterns that work seamlessly with the established ecosystem
4. **Maintain consistency** - Standardized approaches across all development tasks
5. **Follow mandatory workflows** - Critical processes like pre-commit checks and changelog management

### Quick Decision Guide for AI Agents

**When generating Go code:**
- Start with [go-architecture-patterns.md](go-architecture-patterns.md) for overall structure
- Check [go-service-implementation-patterns.md](go-service-implementation-patterns.md) for design decisions
- Use specific pattern guides as needed:
  - [go-factory-pattern.md](go-factory-pattern.md) for factory organization and dependency composition
  - [go-functional-options-pattern.md](go-functional-options-pattern.md) for flexible constructors
  - [go-enum-type-pattern.md](go-enum-type-pattern.md) for type-safe enumerations
  - [go-filter-pattern.md](go-filter-pattern.md) for collection operations
  - [go-parse-pattern.md](go-parse-pattern.md) for custom type conversions

**When writing tests:**
1. Read [go-test-types-guide.md](go-test-types-guide.md) to choose test type (unit/integration/e2e)
2. Follow [go-testing-guide.md](go-testing-guide.md) for Ginkgo v2 syntax and patterns
3. Consult [go-mocking-guide.md](go-mocking-guide.md) for mock usage and generation

**When setting up projects:**
- Reference [go-makefile-commands.md](go-makefile-commands.md) for standardized targets
- Follow [git-commit-guide.md](git-commit-guide.md) for commit process (mandatory)
- Apply [go-licensing-guide.md](go-licensing-guide.md) for licensing setup

**When working with frontend:**
- Use [vue3-typescript-frontend-guide.md](vue3-typescript-frontend-guide.md) for Vue 3 projects
- Reference [astro-development-guide.md](astro-development-guide.md) for Astro projects

---

## Usage

AI agents should reference these guidelines when:
- Generating new Go services or components
- Writing tests and documentation
- Setting up build and development workflows
- Implementing frontend components
- Following git commit processes
- Creating or updating documentation

Each guideline document includes complete code examples, key requirements, and common mistakes to avoid, ensuring AI agents can produce high-quality, consistent code that integrates seamlessly with existing development practices.

---

## License

BSD-style license. See [LICENSE](LICENSE) file for details.
