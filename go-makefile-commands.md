# Go Makefile Commands

This document defines the standard Makefile targets used across Go services in Benjamin Borbe's development ecosystem. These commands ensure consistent build processes, code quality, and testing workflows.

## 1. Primary Build and Testing Commands

### `make` (Default Target)
**Purpose**: Run full precommit checks - the comprehensive quality gate before committing code.
**What it does**: Executes format, generate, test, check, and addlicense in sequence.
**When to use**: Before every commit to ensure code meets all quality standards.

```bash
make
```

### `make precommit`
**Purpose**: Explicit precommit workflow execution.
**What it does**: Same as default `make` target - runs all quality checks.
**When to use**: Explicitly when preparing code for commit or CI/CD.

```bash
make precommit
```

### `make test`
**Purpose**: Execute comprehensive test suite with coverage and race detection.
**What it does**: 
- Runs all tests using Ginkgo v2 framework
- Enables race condition detection (`-race` flag)
- Generates test coverage reports
- Enforces minimum coverage thresholds

```bash
make test
```

**Key features**:
- BDD-style testing with Ginkgo v2 and Gomega
- UTC timezone enforcement for consistent time handling
- Counterfeiter mock integration
- Coverage reporting and threshold enforcement

### `make ensure`
**Purpose**: Clean and verify Go modules for dependency integrity.
**What it does**:
- Cleans module cache
- Downloads and verifies all dependencies  
- Ensures go.mod and go.sum are synchronized
- Validates module requirements

```bash
make ensure
```

## 2. Code Quality and Formatting

### `make format`
**Purpose**: Apply consistent code formatting and import organization.
**What it does**:
- Runs `gofmt` to format Go source code
- Organizes imports with `goimports`
- Applies consistent indentation and spacing
- Removes unused imports

```bash
make format
```

**Benefits**:
- Maintains consistent code style across team
- Reduces code review friction
- Automatically fixes common formatting issues

### `make generate`
**Purpose**: Generate code artifacts including mocks and other derived code.
**What it does**:
- Executes `go generate ./...` command
- Generates Counterfeiter mocks from `//counterfeiter:generate` comments
- Updates generated code based on interface changes
- Ensures generated artifacts are current

```bash
make generate
```

**Integration**:
- Works with `//go:generate` directives in source files
- Automatically creates mocks in `mocks/` directories
- Updates test fixtures and generated documentation

### `make check`
**Purpose**: Run comprehensive static analysis and security checks.
**What it does**: Executes vet, errcheck, and vulncheck in sequence.
**When to use**: Part of precommit workflow or standalone quality verification.

```bash
make check
```

### `make vet`
**Purpose**: Run Go's built-in static analysis tool.
**What it does**:
- Identifies suspicious constructs and potential bugs
- Checks for common programming errors
- Validates proper use of Go idioms
- Reports unreachable code and type mismatches

```bash
make vet
```

### `make errcheck`
**Purpose**: Ensure all error returns are properly handled.
**What it does**:
- Scans codebase for unchecked error returns
- Identifies potential error handling issues
- Enforces error handling best practices
- Reports functions that ignore error returns

```bash
make errcheck
```

**Critical for**:
- Robust error handling in production code
- Preventing silent failures
- Maintaining code reliability standards

### `make vulncheck`
**Purpose**: Scan for known security vulnerabilities in dependencies.
**What it does**:
- Analyzes Go modules for security issues
- Checks dependencies against vulnerability databases
- Reports known CVEs in dependencies
- Suggests remediation strategies

```bash
make vulncheck
```

### `make addlicense`
**Purpose**: Add consistent license headers to all Go source files.
**What it does**:
- Adds BSD license headers to `.go` files
- Maintains consistent copyright notices
- Updates existing headers if needed
- Ensures legal compliance

```bash
make addlicense
```

## 3. Workflow Integration

### Development Workflow
```bash
# Daily development cycle
make format          # Format code changes
make generate        # Update generated code
make test           # Run tests
make check          # Static analysis
make               # Full precommit check
```

### Pre-Commit Workflow
```bash
# Before every commit (MANDATORY)
make precommit      # Comprehensive quality gate
git add .
git commit -m "implement feature X"
```

### CI/CD Integration
```bash
# Typical CI pipeline
make ensure         # Verify dependencies
make               # Full quality check
make test          # Test with coverage
```

## 4. Error Handling and Troubleshooting

### Common Issues

**Build Failures**:
- Run `make ensure` to fix dependency issues
- Check Go version compatibility
- Verify environment setup

**Test Failures**:
- Review test output for specific failures
- Check mock generation with `make generate`
- Ensure UTC timezone for time-sensitive tests

**Format Issues**:
- Run `make format` before committing
- Configure IDE to use `gofmt` on save
- Check for syntax errors

**Security Vulnerabilities**:
- Review `make vulncheck` output
- Update dependencies to patched versions
- Check for alternative packages if needed

## 5. Integration with Git Workflow

These Makefile commands integrate with the mandatory git workflow:

1. **Feature Development**: Use `make test` and `make format` during development
2. **Pre-Commit**: ALWAYS run `make precommit` before committing
3. **Code Review**: Reviewers expect all quality checks to pass
4. **Release**: CI/CD relies on these commands for automated quality gates

**Critical Requirements**:
- Never commit without running `make precommit`
- All quality checks must pass before code review
- Generated code (mocks) must be current and committed
- License headers must be present on all Go files

This standardized approach ensures consistent code quality, security, and maintainability across all Go services in the development ecosystem.