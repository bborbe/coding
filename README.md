# AI Coding Guidelines

This repository contains standardized coding guidelines, patterns, and workflows specifically designed for AI agents working with Benjamin Borbe's Go ecosystem and development environment.

## Purpose

This repository serves as a comprehensive reference for AI agents (like Claude Code) to ensure consistent, high-quality code generation and development practices. It provides structured guidelines that help AI agents understand established patterns, avoid common mistakes, and integrate seamlessly with existing codebases.

## Repository Contents

### Core Go Development Guidelines

- **[go-architecture-patterns.md](go-architecture-patterns.md)** - Comprehensive Go service architecture patterns using the Interface → Constructor → Struct → Method pattern, dependency injection, and ecosystem integration
- **[go-testing-guide.md](go-testing-guide.md)** - Complete testing patterns with Ginkgo v2, Gomega, Counterfeiter mocks, and BDD-style testing approaches
- **[go-makefile-commands.md](go-makefile-commands.md)** - Standardized Makefile targets for builds, testing, code quality, and license management
- **[go-doc-best-practices.md](go-doc-best-practices.md)** - Documentation standards and best practices for Go code
- **[go-glog.md](go-glog.md)** - Logging patterns and glog usage guidelines

### Development Workflows

- **[git-commit-workflow.md](git-commit-workflow.md)** - Mandatory commit process including pre-commit steps, changelog updates, and version tagging with semantic versioning
- **[tdd-guide.md](tdd-guide.md)** - Test-driven development practices and patterns

### Frontend Development

- **[vue3-typescript-frontend-guide.md](vue3-typescript-frontend-guide.md)** - Vue 3 + TypeScript patterns with Composition API, Vite setup, and testing with Vitest
- **[astro-development-guide.md](astro-development-guide.md)** - Astro framework development guidelines

### Documentation Standards

- **[markdown-todo-guide.md](markdown-todo-guide.md)** - Markdown formatting and todo management patterns

## Key Ecosystem Libraries

These guidelines emphasize integration with ecosystem:

- **`github.com/bborbe/time`** - Time handling with dependency injection instead of standard time package
- **`github.com/bborbe/collection`** - Pointer utilities and collection helpers
- **`github.com/bborbe/errors`** - Context-aware error wrapping and handling
- **Ginkgo v2 + Gomega** - Preferred testing framework with BDD patterns
- **Counterfeiter** - Mock generation for interfaces

## For AI Agents

This repository is specifically structured to help AI agents:

1. **Understand established patterns** - Clear examples of preferred architectures and implementations
2. **Avoid common antipatterns** - Explicit guidance on what NOT to do
3. **Integrate with existing code** - Patterns that work seamlessly with the established ecosystem
4. **Maintain consistency** - Standardized approaches across all development tasks
5. **Follow mandatory workflows** - Critical processes like pre-commit checks and changelog management

## Usage

AI agents should reference these guidelines when:
- Generating new Go services or components
- Writing tests and documentation
- Setting up build and development workflows
- Implementing frontend components
- Following git commit processes
- Creating or updating documentation

Each guideline document includes complete code examples, key requirements, and common mistakes to avoid, ensuring AI agents can produce high-quality, consistent code that integrates seamlessly with existing development practices.
