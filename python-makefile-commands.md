# Python Makefile Commands

This document defines the standard Makefile targets used across Python services in Benjamin Borbe's development ecosystem. These commands ensure consistent build processes, code quality, and testing workflows using modern Python tooling (uv, ruff, mypy, pytest).

## 1. Primary Build and Testing Commands

### `make` (Default Target)
**Purpose**: Run full precommit checks - the comprehensive quality gate before committing code.
**What it does**: Executes format, test, and check in sequence.
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

**Standard implementation**:
```makefile
precommit: format test check
	@echo "All precommit checks passed"
```

**Alternative with dependency sync** (recommended for CI/CD):
```makefile
precommit: sync format test check
	@echo "All precommit checks passed"

sync:
	uv sync --all-extras
```

### `make test`
**Purpose**: Execute comprehensive test suite with pytest.
**What it does**:
- Runs all tests using pytest
- Executes tests with proper Python path configuration
- Generates test coverage reports (optional)
- Supports async test execution with pytest-asyncio

```bash
make test
```

**Standard implementation**:
```makefile
test:
	uv run pytest
```

**With coverage**:
```makefile
test:
	uv run pytest --cov=src --cov-report=term-missing
```

**Key features**:
- Fast test execution with pytest
- Async test support via pytest-asyncio
- Comprehensive assertion framework
- Coverage reporting and threshold enforcement

### `make install`
**Purpose**: Install project dependencies using uv.
**What it does**:
- Synchronizes dependencies from pyproject.toml
- Installs all optional dependencies (dev, test)
- Creates or updates virtual environment
- Ensures consistent dependency versions via uv.lock

```bash
make install
```

**Standard implementation**:
```makefile
install:
	uv sync --all-extras
```

## 2. Code Quality and Formatting

### `make format`
**Purpose**: Apply consistent code formatting and auto-fix linting issues.
**What it does**:
- Runs `ruff format` to format Python source code
- Runs `ruff check --fix` to auto-fix linting issues
- Applies consistent indentation and spacing
- Organizes imports
- Removes unused imports

```bash
make format
```

**Standard implementation**:
```makefile
format:
	uv run ruff format .
	uv run ruff check --fix . || true
```

**Benefits**:
- Maintains consistent code style across team
- Reduces code review friction
- Automatically fixes common formatting issues
- Fast execution (Rust-based ruff)

### `make check`
**Purpose**: Run comprehensive static analysis and type checks.
**What it does**: Executes lint and typecheck in sequence.
**When to use**: Part of precommit workflow or standalone quality verification.

```bash
make check
```

**Standard implementation**:
```makefile
check: lint typecheck
	@echo "All checks passed"
```

### `make lint`
**Purpose**: Run linting checks without auto-fixing.
**What it does**:
- Runs `ruff check` in check-only mode
- Identifies code quality issues
- Reports potential bugs and anti-patterns
- Validates import organization
- Checks for common Python mistakes

```bash
make lint
```

**Standard implementation**:
```makefile
lint:
	uv run ruff check .
```

**Critical for**:
- Identifying code smells before commit
- Enforcing coding standards
- Catching potential bugs early
- Maintaining code quality consistency

### `make typecheck`
**Purpose**: Run static type checking with mypy.
**What it does**:
- Analyzes Python code for type correctness
- Validates type hints against actual usage
- Catches type-related bugs before runtime
- Enforces type safety standards

```bash
make typecheck
```

**Standard implementation**:
```makefile
typecheck:
	uv run mypy src
```

**Advanced configurations**:
```makefile
# Strict type checking
typecheck:
	uv run mypy src --strict

# With specific flags
typecheck:
	uv run mypy src --no-error-summary --show-error-codes
```

## 3. Additional Common Targets

### `make run`
**Purpose**: Run the application in development mode.
**What it does**: Executes the main application entry point.

```bash
make run
```

**Example implementations**:
```makefile
# For services with entry point
run:
	uv run skeleton serve

# For FastAPI development
run:
	uv run uvicorn main:app --reload --port 8000

# For CLI tools
run:
	uv run python main.py
```

### `make clean`
**Purpose**: Remove build artifacts and caches.
**What it does**:
- Removes virtual environment
- Cleans Python cache directories (__pycache__)
- Removes test artifacts (.pytest_cache)
- Cleans type checker cache (.mypy_cache)
- Removes ruff cache (.ruff_cache)
- Cleans build directories (dist, *.egg-info)

```bash
make clean
```

**Standard implementation**:
```makefile
clean:
	rm -rf .venv dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
```

## 4. Modular Makefile Organization

For larger projects, split Makefile into logical modules:

```
Makefile              # Main file with includes
Makefile.variables    # Environment and build variables
Makefile.precommit    # Quality check targets
Makefile.docker       # Docker build targets
Makefile.k8s          # Kubernetes deployment targets
```

**Main Makefile structure**:
```makefile
include Makefile.variables
include Makefile.precommit
include Makefile.docker
include example.env

SERVICE = bborbe/my-service

.PHONY: all run install clean

all: precommit

install:
	uv sync --all-extras

run:
	uv run my-service serve

clean:
	rm -rf .venv dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
```

**Makefile.precommit**:
```makefile
.PHONY: precommit format lint typecheck check test

precommit: format test check
	@echo "All precommit checks passed"

format:
	uv run ruff format .
	uv run ruff check --fix . || true

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

check: lint typecheck

test:
	uv run pytest
```

**Makefile.variables**:
```makefile
BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)
HOSTNAME ?= $(shell hostname -s)
ROOTDIR ?= $(shell git rev-parse --show-toplevel)
```

## 5. Workflow Integration

### Development Workflow
```bash
# Daily development cycle
make install         # Install dependencies
make format          # Format code changes
make test            # Run tests
make check           # Static analysis
make                 # Full precommit check
```

### Pre-Commit Workflow
```bash
# Before every commit (MANDATORY)
make precommit       # Comprehensive quality gate
git add .
git commit -m "implement feature X"
```

### CI/CD Integration
```bash
# Typical CI pipeline
make install         # Install dependencies
make                 # Full quality check
make test            # Test with coverage
```

## 6. Tool Configuration

### pyproject.toml Integration

All tool configurations should be in `pyproject.toml`:

```toml
[project]
name = "my-service"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "pydantic>=2.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

## 7. Error Handling and Troubleshooting

### Common Issues

**Build Failures**:
- Run `make install` to fix dependency issues
- Check Python version compatibility (>=3.12)
- Verify uv is installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

**Test Failures**:
- Review test output for specific failures
- Check test dependencies in pyproject.toml
- Ensure virtual environment is active

**Format Issues**:
- Run `make format` before committing
- Configure IDE to use ruff on save
- Check for syntax errors

**Type Check Failures**:
- Add missing type hints to functions
- Review mypy configuration strictness
- Check for incompatible type assignments

**Lint Failures**:
- Review ruff output for specific violations
- Use `make format` to auto-fix when possible
- Update code to follow Python best practices

## 8. Integration with Git Workflow

These Makefile commands integrate with the mandatory git workflow:

1. **Feature Development**: Use `make test` and `make format` during development
2. **Pre-Commit**: ALWAYS run `make precommit` before committing
3. **Code Review**: Reviewers expect all quality checks to pass
4. **Release**: CI/CD relies on these commands for automated quality gates

**Critical Requirements**:
- Never commit without running `make precommit`
- All quality checks must pass before code review
- Dependencies must be locked in uv.lock
- Type hints must be present on all public functions

## 9. Comparison with Go Projects

| Aspect | Python (uv/ruff/mypy) | Go (ginkgo/golangci-lint) |
|--------|----------------------|---------------------------|
| Formatting | `ruff format` | `gofmt` + `goimports` |
| Linting | `ruff check` | `golangci-lint` |
| Type checking | `mypy` | Built into compiler |
| Testing | `pytest` | `ginkgo` + `gomega` |
| Mocks | `unittest.mock` | `counterfeiter` |
| Package manager | `uv` | Go modules |

## 10. Best Practices

**DO**:
- Keep Makefile targets consistent across projects
- Use `.PHONY` for all non-file targets
- Add descriptive echo messages for long-running targets
- Document non-standard targets with comments
- Use `uv run` prefix for all tool executions
- Fail fast with `set -e` in shell commands

**DON'T**:
- Don't hardcode paths - use variables
- Don't skip `make precommit` before committing
- Don't mix pip/poetry/uv in same project
- Don't commit without passing tests
- Don't disable type checking or linting globally

This standardized approach ensures consistent code quality, security, and maintainability across all Python services in the development ecosystem.