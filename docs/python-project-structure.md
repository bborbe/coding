# Python Project Structure Guide

Standard project layout and organization patterns for Python services and applications.

## Quick Reference

| Question | Answer |
|----------|--------|
| **Package location** | `src/package_name/` (NOT root) |
| **Build system** | pyproject.toml with hatchling backend |
| **Test layout** | Mirror src/ structure in tests/ |
| **Entry point** | `src/package/__main__.py` for `python -m` |
| **Dependencies** | uv with uv.lock for reproducibility |

## Standard Directory Structure

```
project-name/
├── src/
│   └── package_name/              # Package in src/ layout
│       ├── __init__.py            # Package initialization, __version__
│       ├── __main__.py            # Entry point for python -m
│       ├── config.py              # Configuration (Pydantic BaseSettings)
│       ├── factory.py             # Dependency injection factories
│       ├── logging_setup.py       # Logging configuration
│       ├── service.py             # Business logic
│       ├── repository.py          # Data access
│       └── commands/              # CLI command modules (if applicable)
│           ├── __init__.py
│           ├── backup.py
│           └── info.py
├── tests/
│   ├── conftest.py                # Shared pytest fixtures
│   ├── test_service.py            # Mirrors src/package_name/service.py
│   └── commands/                  # Mirrors src/package_name/commands/
│       ├── test_backup.py
│       └── test_info.py
├── pyproject.toml                 # Project metadata and dependencies
├── uv.lock                        # Dependency lock file (committed)
├── Makefile                       # Build and quality commands
├── README.md                      # Project documentation
├── CHANGELOG.md                   # Version history
├── LICENSE                        # License file
└── .gitignore                     # Git ignore patterns
```

## Rules

### Use src/ Package Layout

**Constraint:** Packages MUST be placed in `src/package_name/`, NOT at repository root.

**Rationale:** src/ layout prevents accidental imports of development code, ensures package installation testing, and separates source from metadata files.

**Examples:**

```bash
# [GOOD] - src/ layout
src/
  iphone_backup/
    __init__.py
    backup.py

# [BAD] - Root layout
iphone_backup/
  __init__.py
  backup.py
```

**Benefits:**
- Prevents `sys.path` pollution during development
- Forces testing against installed package, not development directory
- Clean separation between package code and project files
- Standard recognized by all Python build tools

### Use pyproject.toml with hatchling

**Constraint:** Projects MUST use `pyproject.toml` with hatchling build backend, NOT setup.py.

**Rationale:** PEP 517/518 standard build system; hatchling is simple, fast, and maintained by PyPA.

**Examples:**

```toml
# [GOOD] - Modern pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "iphone-backup"
version = "0.5.0"
description = "iPhone photo backup tool"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.11"
authors = [
    { name = "Benjamin Borbe", email = "bborbe@example.com" },
]
dependencies = [
    "pymobiledevice3>=3.0.0",
    "pydantic>=2.10.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.13.0",
    "ruff>=0.8.0",
]

[project.scripts]
iphone-backup = "iphone_backup.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["src/iphone_backup"]
```

**Key sections:**
- `[build-system]` - Declares hatchling as build backend
- `[project]` - Package metadata (name, version, dependencies)
- `[project.optional-dependencies]` - Dev/test dependencies
- `[project.scripts]` - Console script entry points
- `[tool.hatch.build.targets.wheel]` - Build configuration

### Mirror src/ Structure in tests/

**Constraint:** Test directory structure MUST mirror the src/ package structure.

**Rationale:** Makes tests easy to locate, maintains organization at scale, clear 1:1 mapping between source and test files.

**Examples:**

```bash
# [GOOD] - Mirrored structure
src/
  iphone_backup/
    commands/
      backup.py
      info.py
    scanner.py
tests/
  commands/
    test_backup.py        # Tests src/.../commands/backup.py
    test_info.py          # Tests src/.../commands/info.py
  test_scanner.py         # Tests src/.../scanner.py

# [BAD] - Flat test structure
tests/
  test_backup.py
  test_info.py
  test_scanner.py         # Where is backup/info relationship?
```

### Use __main__.py for CLI Entry Point

**Constraint:** CLI applications MUST use `src/package/__main__.py` as entry point to enable `python -m package` execution.

**Rationale:** Standard Python pattern for executable modules; supports both `python -m` and console script execution.

**Examples:**

```python
# [GOOD] - src/iphone_backup/__main__.py
"""Entry point for the iphone-backup application."""

import sys
from iphone_backup.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**
```bash
# Both methods work
python -m iphone_backup backup
iphone-backup backup  # Via console script in pyproject.toml
```

### Commit uv.lock for Reproducibility

**Constraint:** The uv.lock file MUST be committed to version control.

**Rationale:** Ensures reproducible builds across environments and CI/CD pipelines.

**Examples:**

```bash
# [GOOD] - Lock file committed
git add uv.lock
git commit -m "Update dependencies"

# [BAD] - Lock file in .gitignore
echo "uv.lock" >> .gitignore
```

### Add __version__ to Package __init__.py

**Constraint:** Package `__init__.py` MUST expose `__version__` string matching pyproject.toml version.

**Rationale:** Enables runtime version checks and debugging.

**Examples:**

```python
# [GOOD] - src/iphone_backup/__init__.py
"""iPhone backup package."""

__version__ = "0.5.0"
```

## pyproject.toml Structure

### Minimal Template

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-package"
version = "0.1.0"
description = "Package description"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.12"
authors = [
    { name = "Your Name", email = "you@example.com" },
]
dependencies = [
    "pydantic>=2.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "mypy>=1.13.0",
    "ruff>=0.8.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
```

### Tool Configuration Sections

All tool configurations should be in `[tool.*]` sections:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = "external_package.*"
ignore_missing_imports = true

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
    "SIM",    # flake8-simplify
    "RUF",    # ruff-specific rules
]
```

## Migration from setup.py

### Migration Checklist

- [ ] Create `pyproject.toml` with `[build-system]` and `[project]` sections
- [ ] Move package from root to `src/package_name/`
- [ ] Update imports in all modules to use new package path
- [ ] Convert setup.py metadata to `[project]` section
- [ ] Move install_requires → `dependencies`
- [ ] Move extras_require → `[project.optional-dependencies]`
- [ ] Move entry_points → `[project.scripts]`
- [ ] Update test imports and paths
- [ ] Update Makefile paths (if any) to use src/
- [ ] Remove setup.py, setup.cfg, MANIFEST.in
- [ ] Run `uv sync` to generate uv.lock
- [ ] Test with `python -m build` and `python -m package`

### setup.py → pyproject.toml Mapping

```python
# OLD: setup.py
from setuptools import setup, find_packages

setup(
    name="iphone-backup",
    version="0.5.0",
    author="Benjamin Borbe",
    author_email="bborbe@example.com",
    description="iPhone photo backup tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "pymobiledevice3>=3.0.0",
        "pydantic>=2.10.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.0",
            "mypy>=1.13.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "iphone-backup=iphone_backup.__main__:main",
        ],
    },
    python_requires=">=3.11",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
)
```

```toml
# NEW: pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "iphone-backup"
version = "0.5.0"
description = "iPhone photo backup tool"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.11"
authors = [
    { name = "Benjamin Borbe", email = "bborbe@example.com" },
]
dependencies = [
    "pymobiledevice3>=3.0.0",
    "pydantic>=2.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "mypy>=1.13.0",
]

[project.scripts]
iphone-backup = "iphone_backup.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["src/iphone_backup"]
```

## Test Organization

### Shared Fixtures with conftest.py

**Constraint:** Common test fixtures MUST be defined in `tests/conftest.py`.

**Rationale:** pytest automatically discovers conftest.py; fixtures are available to all tests without imports.

**Examples:**

```python
# [GOOD] - tests/conftest.py
"""Shared test fixtures for iphone_backup tests."""

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_backup_dir() -> Generator[Path, None, None]:
    """Create temporary backup directory that's automatically cleaned up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for general testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
```

### Test File Naming

```
test_*.py          # Test modules
Test*              # Test classes
test_*             # Test functions
```

**Configure in pyproject.toml:**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

## Common Antipatterns

### DON'T: Root-Level Package

```bash
# [BAD] - Package at root
mypackage/
  __init__.py
  main.py
tests/
  test_main.py
```

**Problems:**
- Import ambiguity during development
- Can import uninstalled development code
- Mixes package with project files

### DON'T: Keep setup.py with pyproject.toml

```bash
# [BAD] - Both build configs
pyproject.toml
setup.py           # Remove this
```

**Why:** Conflicting configurations, unclear source of truth.

### DON'T: Ignore uv.lock

```bash
# [BAD] - .gitignore
uv.lock
```

**Why:** Non-reproducible builds, dependency drift in CI/CD.

### DON'T: Flat Test Directory

```bash
# [BAD] - No structure
tests/
  test_backup.py
  test_info.py
  test_list.py
  test_scanner.py
  test_device.py
```

**Why:** Hard to locate tests, no clear organization, doesn't scale.

## Integration with Tools

### uv Commands

```bash
# Install dependencies
uv sync --all-extras

# Add dependency
uv add requests

# Add dev dependency
uv add --dev pytest

# Update dependencies
uv lock --upgrade

# Run command in venv
uv run pytest
uv run mypy src
```

### Build and Install

```bash
# Build wheel
python -m build

# Install editable
pip install -e .

# Install from wheel
pip install dist/package-0.1.0-py3-none-any.whl
```

## Reference Projects

**Fully compliant examples:**
- `/Users/bborbe/Documents/workspaces/netcup-dns` - Production CLI tool
- `/Users/bborbe/Documents/workspaces/alertmanager-mcp` - MCP server
- `/Users/bborbe/Documents/workspaces/iphone-image-backup` - CLI with subcommands

## Related Documentation

- [python-cli-arguments-guide.md](python-cli-arguments-guide.md) - CLI patterns and __main__.py
- [python-architecture-patterns.md](python-architecture-patterns.md) - Service organization
- [python-makefile-commands.md](python-makefile-commands.md) - Build commands
- [python-factory-pattern.md](python-factory-pattern.md) - Dependency wiring
- [python-pydantic-guide.md](python-pydantic-guide.md) - Configuration with BaseSettings
