# Python CLI Arguments and Environment Variables

This guide defines patterns for handling command-line arguments and environment variables in Python applications.

## Overview

Applications need configuration from two primary sources:
1. **Environment variables** - Container config, CI/CD, deployment-specific values
2. **Command-line arguments** - Runtime overrides, developer options, script parameters

Modern Python applications combine both sources with proper validation and type safety.

## When to Use Each Approach

### Environment Variables

**Use for:**
- Deployment-specific configuration (database URLs, API endpoints)
- Container/cloud environments (Docker, Kubernetes)
- CI/CD pipelines
- Secrets and credentials (with secret management)
- Values that rarely change per deployment

**Example:** `DATABASE_URL`, `API_KEY`, `LOG_LEVEL`

### Command-Line Arguments

**Use for:**
- Runtime behavior changes (debug mode, batch size)
- Developer/operator overrides
- Script parameters that vary per execution
- One-off operations

**Example:** `--debug`, `--batch-size 100`, `--dry-run`

### Combining Both

**Best practice:** Load defaults from environment, override with CLI arguments

```python
port = int(os.getenv('PORT', '8080'))  # Default from env
# CLI --port overrides env value
```

## Configuration Precedence

Configuration sources are applied in this order (later sources override earlier):

```
1. Code defaults     →  port: int = 8080
2. .env file         →  PORT=9000  (loaded by Pydantic/python-dotenv)
3. Environment vars  →  export PORT=3000
4. CLI arguments     →  --port 4000
```

**Example flow:**
```python
# 1. Code default: port = 8080
# 2. .env file contains: PORT=9000 → port = 9000
# 3. Shell: export PORT=3000 → port = 3000
# 4. CLI: --port 4000 → port = 4000 (final value)
```

**Key points:**
- Environment variables override `.env` file (deployment flexibility)
- CLI arguments have highest priority (developer/operator override)
- Pydantic BaseSettings follows this order automatically
- Always document which sources your app supports

## Recommended Approaches

### Option 1: Pydantic BaseSettings (Recommended for Applications)

Best for web services, daemons, and production applications.

```python
from pydantic import BaseSettings, Field, validator

class AppConfig(BaseSettings):
    # Environment variables with validation
    database_url: str = Field(..., env="DATABASE_URL")
    api_key: str = Field(..., env="API_KEY")
    port: int = Field(8080, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    workers: int = Field(4, env="WORKERS", ge=1, le=32)
    service_hosts: list[str] = Field(..., env="SERVICE_HOSTS")

    @validator("service_hosts", pre=True)
    def parse_hosts(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def main():
    config = AppConfig()  # Validates and loads from env/.env

    print(f"Starting server on port {config.port}")
    print(f"Connecting to services: {config.service_hosts}")
    # ... rest of application
```

**Advantages:**
- ✅ Type-safe with runtime validation
- ✅ Auto-loads from `.env` file
- ✅ Clear errors if config invalid
- ✅ Single source of truth
- ✅ Integrates with FastAPI automatically

**See:** [python-pydantic-guide.md](python-pydantic-guide.md) for BaseSettings details

### Option 2: argparse (Recommended for Scripts/CLI Tools)

Best for command-line tools, scripts, and utilities.

```python
import argparse
import os

def parse_args():
    parser = argparse.ArgumentParser(
        description='Process orders from message queue',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Arguments with env var defaults
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('PORT', '8080')),
        help='Server port'
    )
    parser.add_argument(
        '--service-hosts',
        default=os.getenv('SERVICE_HOSTS', 'localhost:8080'),
        help='Comma-separated service host list'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        default=os.getenv('DEBUG', '').lower() == 'true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=int(os.getenv('WORKERS', '4')),
        help='Number of worker threads'
    )

    args = parser.parse_args()

    # Post-process complex types
    if isinstance(args.service_hosts, str):
        args.service_hosts = args.service_hosts.split(',')

    return args

def main():
    args = parse_args()

    print(f"Port: {args.port}")
    print(f"Service hosts: {args.service_hosts}")
    print(f"Debug: {args.debug}")

    # ... rest of application

if __name__ == '__main__':
    main()
```

**Advantages:**
- ✅ Stdlib (no dependencies)
- ✅ Auto-generated help text
- ✅ Type conversion built-in
- ✅ Supports subcommands
- ✅ Familiar to CLI users

### Option 3: typer (Modern CLI Framework)

Best for complex CLI applications with multiple commands.

```python
import typer
import os

app = typer.Typer()

@app.command()
def serve(
    port: int = typer.Option(
        int(os.getenv('PORT', '8080')),
        help="Server port"
    ),
    service_hosts: str = typer.Option(
        os.getenv('SERVICE_HOSTS', 'localhost:8080'),
        help="Comma-separated service hosts"
    ),
    debug: bool = typer.Option(
        False,
        help="Enable debug logging"
    ),
    workers: int = typer.Option(
        4,
        min=1,
        max=32,
        help="Number of worker threads"
    ),
):
    """Start the application server"""
    hosts = service_hosts.split(',')

    typer.echo(f"Starting server on port {port}")
    typer.echo(f"Service hosts: {hosts}")

    # ... rest of application

if __name__ == '__main__':
    app()
```

**Advantages:**
- ✅ Type-hint driven (minimal boilerplate)
- ✅ Auto-generated help
- ✅ Rich terminal output
- ✅ Great for multi-command CLIs

## Anti-Patterns to Avoid

### ❌ Bad: getopt (Legacy, Verbose)

```python
import getopt
import sys

# ❌ DON'T: Use getopt (legacy, verbose, error-prone)
def main(argv):
    opts, args = getopt.getopt(argv, 'hp:', [
        'port=',
        'service-hosts=',
        'debug',
    ])

    port = 8080
    hosts = None
    debug = False

    for opt, arg in opts:
        if opt == '-h':
            print('Usage: ...')
            sys.exit()
        elif opt in ('-p', '--port'):
            port = int(arg)
        elif opt in ('--service-hosts'):
            hosts = arg.split(',')
        elif opt in ('--debug'):
            debug = True

    # ... rest
```

**Why it's bad:**
- Manual option parsing (error-prone)
- No automatic help text
- No type validation
- Verbose boilerplate
- Hard to maintain

**Fix:** Use argparse or typer instead

### ❌ Bad: Wrong Type Annotations

```python
import os

# ❌ DON'T: Type annotation doesn't match reality
hosts: list[str] = os.getenv('SERVICE_HOSTS')
# Returns str | None, not list[str]!

# ✅ DO: Correct type handling
hosts: list[str] | None = None
service_hosts_env = os.getenv('SERVICE_HOSTS')
if service_hosts_env:
    hosts = service_hosts_env.split(',')
```

### ❌ Bad: No Validation

```python
import os

# ❌ DON'T: No validation, crashes later
port = int(os.getenv('PORT'))  # Crashes if PORT not set or invalid

# ✅ DO: Validate and provide defaults
port_str = os.getenv('PORT', '8080')
try:
    port = int(port_str)
    if port < 1 or port > 65535:
        raise ValueError(f"Port must be 1-65535, got {port}")
except ValueError as e:
    print(f"Invalid PORT: {e}")
    sys.exit(1)

# ✅ BETTER: Use Pydantic for automatic validation
class Config(BaseSettings):
    port: int = Field(8080, ge=1, le=65535)
```

### ❌ Bad: Logging Secrets

```python
import os
import logging

password = os.getenv('DATABASE_PASSWORD')

# ❌ DON'T: Log actual secrets
logging.info(f"Database password: {password}")

# ✅ DO: Log presence/length only
logging.info(f"Database password configured: {password is not None}")
logging.info(f"Database password length: {len(password) if password else 0}")
```

**See:** [python-logging-guide.md](python-logging-guide.md) for safe logging patterns

### ❌ Bad: No None Handling

```python
import os

password = os.getenv('PASSWORD')  # Returns None if not set

# ❌ DON'T: Assume value exists
print(f"Password length: {len(password)}")  # Crashes if None

# ✅ DO: Handle None safely
if password is None:
    print("ERROR: PASSWORD environment variable not set")
    sys.exit(1)

print(f"Password length: {len(password)}")
```

### ❌ Bad: Reading Env at Import Time

```python
# config.py

# ❌ DON'T: Read env vars at module import time
DATABASE_URL = os.getenv('DATABASE_URL')  # Evaluated when module is imported
API_KEY = os.getenv('API_KEY')

# Problem: Tests can't override these values after import
# Problem: Values are "frozen" at import time
# Problem: Circular import issues in complex apps
```

```python
# ✅ DO: Read env vars in functions or use lazy loading

# Option 1: Function that reads on demand
def get_database_url() -> str:
    return os.getenv('DATABASE_URL', 'sqlite:///default.db')

# Option 2: Class with lazy initialization
class Config:
    _instance: 'Config | None' = None

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.api_key = os.getenv('API_KEY')

    @classmethod
    def get(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# Option 3: Pydantic BaseSettings (recommended)
class Settings(BaseSettings):
    database_url: str
    api_key: str

# Instantiate in main(), not at module level
def main():
    settings = Settings()
```

**Why import-time reading is bad:**
- Tests can't monkeypatch values after import
- Configuration is "frozen" at import time
- Hard to debug when values don't change
- Prevents configuration from different sources

## Common Patterns

### Pattern 1: Environment with CLI Override

```python
import argparse
import os

def parse_args():
    parser = argparse.ArgumentParser()

    # Load default from env, allow CLI override
    parser.add_argument(
        '--database-url',
        default=os.getenv('DATABASE_URL'),
        help='Database connection string'
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.database_url:
        parser.error("DATABASE_URL must be set via env or --database-url")

    return args
```

### Pattern 2: Boolean Environment Variables

```python
import os

def env_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable"""
    value = os.getenv(key, '').lower()
    if value in ('true', '1', 'yes', 'on'):
        return True
    if value in ('false', '0', 'no', 'off', ''):
        return default
    raise ValueError(f"Invalid boolean value for {key}: {value}")

# Usage
debug = env_bool('DEBUG', default=False)
feature_enabled = env_bool('FEATURE_ENABLED', default=False)
```

### Pattern 3: List from Environment

```python
import os

def env_list(key: str, separator: str = ',', default: list[str] | None = None) -> list[str]:
    """Parse list from environment variable"""
    value = os.getenv(key)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(separator) if item.strip()]

# Usage
hosts = env_list('SERVICE_HOSTS', default=['localhost:8080'])
# SERVICE_HOSTS="host1:8080,host2:8080" → ['host1:8080', 'host2:8080']
```

### Pattern 4: Required vs Optional

```python
import os
import sys

def require_env(key: str) -> str:
    """Get required environment variable or exit"""
    value = os.getenv(key)
    if value is None:
        print(f"ERROR: {key} environment variable must be set")
        sys.exit(1)
    return value

# Usage
api_key = require_env('API_KEY')  # Exits if not set
log_level = os.getenv('LOG_LEVEL', 'INFO')  # Optional with default
```

### Pattern 5: Pydantic with CLI Override

Combine Pydantic BaseSettings with argparse for best of both:

```python
from pydantic import BaseSettings, Field
import argparse

class Config(BaseSettings):
    port: int = Field(8080, env="PORT")
    debug: bool = Field(False, env="DEBUG")
    workers: int = Field(4, env="WORKERS")

    class Config:
        env_file = ".env"

def parse_args():
    # Load config from env first
    config = Config()

    # Allow CLI overrides
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=config.port)
    parser.add_argument('--debug', action='store_true', default=config.debug)
    parser.add_argument('--workers', type=int, default=config.workers)

    args = parser.parse_args()

    # Update config with CLI overrides
    config.port = args.port
    config.debug = args.debug
    config.workers = args.workers

    return config

def main():
    config = parse_args()
    print(f"Port: {config.port}")
```

### Pattern 6: Enum-Based Configuration

```python
from enum import Enum
from pydantic import BaseSettings, validator

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class Config(BaseSettings):
    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO

    @validator("environment", pre=True)
    def parse_environment(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

# Usage
config = Config()  # ENV=production LOG_LEVEL=DEBUG

if config.environment == Environment.PRODUCTION:
    # Production-specific behavior
    pass
```

**Advantages:**
- Type-safe, IDE autocompletion
- Prevents invalid values
- Self-documenting allowed values
- Clear comparison logic

### Pattern 7: Path Handling with pathlib

```python
from pathlib import Path
from pydantic import BaseSettings, validator

class Config(BaseSettings):
    data_dir: Path = Path("./data")
    log_file: Path = Path("./logs/app.log")
    config_file: Path | None = None

    @validator("data_dir", "log_file", pre=True)
    def parse_path(cls, v):
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    @validator("data_dir")
    def ensure_dir_exists(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v

# Usage
config = Config()
# DATA_DIR=~/mydata → /home/user/mydata (expanded and resolved)

# pathlib operations
for file in config.data_dir.glob("*.json"):
    print(file.name)
```

**Key points:**
- Use `pathlib.Path` instead of `str` for filesystem paths
- Call `.expanduser()` to handle `~` home directory
- Call `.resolve()` to get absolute paths
- Create directories with `.mkdir(parents=True, exist_ok=True)`

## Configuration Validation

### Startup Validation

```python
from pydantic import BaseSettings, Field, ValidationError, validator
import sys

class Config(BaseSettings):
    port: int = Field(..., ge=1, le=65535)
    workers: int = Field(..., ge=1, le=128)
    database_url: str

    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'mysql://')):
            raise ValueError('Database URL must start with postgresql:// or mysql://')
        return v

    class Config:
        env_file = ".env"

def main():
    try:
        config = Config()
    except ValidationError as e:
        print("Configuration error:")
        for error in e.errors():
            print(f"  {error['loc']}: {error['msg']}")
        sys.exit(1)

    print("Configuration valid")
    # ... start application
```

### Logging Configuration on Startup

```python
import logging
from pydantic import BaseSettings

class Config(BaseSettings):
    port: int = 8080
    debug: bool = False
    service_hosts: list[str]
    api_key: str

def main():
    config = Config()

    # Configure logging based on config
    if config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Log configuration (safely)
    logging.info(f"Port: {config.port}")
    logging.info(f"Service hosts: {config.service_hosts}")
    logging.info(f"API key configured: {config.api_key is not None}")
    logging.info(f"Debug mode: {config.debug}")
```

## Exception Handling in CLI Applications

### Use Specific Exception Handlers Before Broad Catch-All

**Constraint:** MUST handle specific exception types before generic `except Exception`, and include `KeyboardInterrupt` handler.

**Rationale:** Specific handlers provide better error messages and appropriate exit codes. Broad catch-all should only handle truly unexpected errors.

**Examples:**
```python
# [GOOD] - Specific exception types with appropriate error messages
import sys
import yaml
from pydantic import ValidationError

def main():
    args = parse_args()

    # Load configuration with specific error handling
    try:
        config = Config()
    except ValidationError as e:
        logger.error("Configuration error:")
        for error in e.errors():
            logger.error(f"  {error['loc']}: {error['msg']}")
        sys.exit(1)

    # Execute command with specific error handling
    try:
        if args.command == "process":
            process_files(args.file_path)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except (OSError, IOError) as e:
        logger.error(f"I/O error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)  # Standard UNIX exit code for SIGINT
    except Exception:
        logger.exception("Unexpected error occurred")
        sys.exit(1)

# [BAD] - Only broad catch-all
def main():
    try:
        config = Config()
        process_files(args.file_path)
    except Exception as e:
        print(f"Error: {e}")  # No context about what failed
        sys.exit(1)
```

### Exit Code Conventions

- `0` - Success
- `1` - General error (configuration, runtime, unexpected)
- `2` - Command-line usage error (argparse handles this)
- `130` - Interrupted by Ctrl+C (128 + SIGINT signal number)

**Reference:** netcup-dns project (`src/netcup_dns/__main__.py`) demonstrates comprehensive exception handling for CLI tools.

## CLI Command Module Organization

### Command Module Pattern for Subcommands

**Constraint:** CLI applications with subcommands MUST organize each command as a separate module with a single public function.

**Rationale:** Keeps commands isolated, testable, and maintainable; clear separation of concerns.

**Structure:**
```
src/
  package/
    __main__.py           # CLI routing and setup
    commands/
      __init__.py
      backup.py           # def backup_photos(...)
      info.py             # def show_device_info(...)
      list_devices.py     # def list_connected_devices(...)
```

**Implementation:**

```python
# src/package/__main__.py
"""Entry point for the application."""

import argparse
import logging
import sys

from pydantic import ValidationError

from package.commands.backup import backup_photos
from package.commands.info import show_device_info
from package.commands.list_devices import list_connected_devices
from package.config import Config
from package.logging_setup import configure_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Application description",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Configuration file path",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # backup subcommand
    backup_parser = subparsers.add_parser("backup", help="Backup data")
    backup_parser.add_argument("-d", "--backup-dir", help="Backup directory")

    # info subcommand
    subparsers.add_parser("info", help="Show information")

    # list-devices subcommand
    subparsers.add_parser("list-devices", help="List connected devices")

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Load configuration with error handling
    try:
        config = Config(config_file=args.config)
    except ValidationError as e:
        configure_logging("ERROR")
        logger.error("Configuration error:")
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            logger.error(f"  {field}: {error['msg']}")
        sys.exit(1)

    # Configure logging
    configure_logging(args.log_level)

    # Route to command modules
    try:
        if args.command == "backup":
            backup_photos(args.backup_dir, config.config_file)
        elif args.command == "info":
            show_device_info(config.config_file)
        elif args.command == "list-devices":
            list_connected_devices(config.config_file)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        sys.exit(1)
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception:
        logger.exception("Unexpected error occurred")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

```python
# src/package/commands/backup.py
"""Backup command implementation."""

import logging

from package.backup import BackupService

logger = logging.getLogger(__name__)


def backup_photos(backup_dir: str | None, config_file: str) -> None:
    """Backup all photos.

    Args:
        backup_dir: Backup directory path (None to use config default)
        config_file: Configuration file path
    """
    logger.info("Starting backup")

    backup = BackupService(backup_dir, config_file)
    success = backup.run()

    if not success:
        raise RuntimeError("Backup failed")
```

**Key patterns:**
- Each command = one module with one public function
- Command functions take simple arguments (not `argparse.Namespace`)
- `__main__.py` handles routing, logging setup, and exception boundaries
- Command modules focus on business logic delegation only
- Exception handling at routing layer, not in command modules

### __main__.py Module Pattern

**Constraint:** CLI applications MUST use `src/package/__main__.py` as entry point to enable `python -m package` execution.

**Rationale:** Standard Python pattern for executable modules; supports both `python -m` and console script execution; keeps main() testable.

**Examples:**

```python
# [GOOD] - __main__.py as entry point
# src/package/__main__.py
"""Entry point for package."""

import sys

def main() -> None:
    """Main entry point."""
    # ... implementation

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Method 1: python -m
python -m package backup --backup-dir /tmp

# Method 2: console script (configured in pyproject.toml)
package-cli backup --backup-dir /tmp
```

**pyproject.toml configuration:**
```toml
[project.scripts]
package-cli = "package.__main__:main"
```

**Benefits:**
- Enables `python -m package` execution
- Consistent with Python module execution conventions
- main() function is importable for testing
- Works with both installed and development mode

### Command Routing Pattern

**Constraint:** Command routing MUST use if/elif chain or dict dispatch, NOT dynamic imports.

**Rationale:** Explicit routing is easier to debug, type-check, and navigate.

**Examples:**

```python
# [GOOD] - Explicit routing with if/elif
def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    if args.command == "backup":
        backup_photos(args.backup_dir, config)
    elif args.command == "restore":
        restore_photos(args.restore_dir, config)
    elif args.command == "list":
        list_photos(config)

# [GOOD] - Dict dispatch for many commands
COMMANDS = {
    "backup": backup_photos,
    "restore": restore_photos,
    "list": list_photos,
    "verify": verify_photos,
}

def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    command_fn = COMMANDS.get(args.command)
    if command_fn is None:
        raise ValueError(f"Unknown command: {args.command}")

    command_fn(args, config)

# [BAD] - Dynamic import (hard to type-check and debug)
def main() -> None:
    args = parse_args()
    module = __import__(f"package.commands.{args.command}")
    command_fn = getattr(module, f"run_{args.command}")
    command_fn(args)
```

**Reference:** iphone-image-backup project (`src/iphone_backup/__main__.py`) demonstrates complete command module pattern with subcommands.

## Decision Framework

### Which Approach to Use?

| Use Case | Recommended Approach | Why |
|----------|---------------------|-----|
| Web service (FastAPI, Flask) | Pydantic BaseSettings | Auto-validates, integrates with FastAPI, type-safe |
| Daemon/background worker | Pydantic BaseSettings | Centralized config, validation, .env support |
| CLI tool with subcommands | typer | Rich CLI, type-hints, minimal boilerplate |
| Simple script | argparse | Stdlib, familiar, sufficient for simple cases |
| Legacy codebase | argparse | Easy migration from getopt, no new dependencies |

### Environment vs CLI Arguments?

**Environment variables when:**
- Config varies by deployment (dev/staging/prod)
- Running in containers/cloud
- Values are secrets or rarely change
- Used by CI/CD pipelines

**CLI arguments when:**
- Need runtime control (debug mode, dry-run)
- Developer/operator overrides
- Values vary per execution
- One-off operations or testing

**Both (env with CLI override) when:**
- Need deployment defaults but allow runtime override
- Developer flexibility + production stability
- Example: `PORT=8080` in prod, `--port 3000` in dev

## Testing Configuration

### Testing with Environment Variables

```python
import os
import pytest

def test_config_from_env(monkeypatch):
    monkeypatch.setenv('PORT', '9000')
    monkeypatch.setenv('DEBUG', 'true')

    config = Config()

    assert config.port == 9000
    assert config.debug is True

def test_config_validation(monkeypatch):
    monkeypatch.setenv('PORT', '99999')  # Invalid port

    with pytest.raises(ValueError):
        Config()
```

### Testing CLI Arguments

```python
import argparse
import pytest

def test_parse_args():
    parser = create_parser()
    args = parser.parse_args(['--port', '3000', '--debug'])

    assert args.port == 3000
    assert args.debug is True

def test_required_argument_missing():
    parser = create_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])  # Missing required args
```

## Edge Cases and Gotchas

### Empty String vs Unset

```python
import os

# These are DIFFERENT:
# - VAR="" → os.getenv('VAR') returns ""
# - VAR not set → os.getenv('VAR') returns None

value = os.getenv('VAR')

# ❌ DON'T: Treat empty string as unset
if not value:  # True for both "" and None
    value = 'default'

# ✅ DO: Distinguish between empty and unset
if value is None:
    value = 'default'  # Only when truly unset

# ✅ DO: Use explicit default if empty should also use default
value = os.getenv('VAR') or 'default'  # Treats "" as unset
```

### Whitespace in Environment Variables

```python
import os

# Shell: export NAME="  Alice  "
name = os.getenv('NAME')  # Returns "  Alice  " (with spaces)

# ✅ DO: Strip whitespace for string values
name = os.getenv('NAME', '').strip()

# ✅ DO: Strip items in lists
def env_list(key: str) -> list[str]:
    value = os.getenv(key, '')
    return [item.strip() for item in value.split(',') if item.strip()]
```

### Boolean Value Ambiguity

```python
# These are all used in the wild:
# DEBUG=true, DEBUG=True, DEBUG=TRUE
# DEBUG=1, DEBUG=yes, DEBUG=on
# DEBUG=false, DEBUG=0, DEBUG=no, DEBUG=off

def env_bool(key: str, default: bool = False) -> bool:
    """Parse boolean with common variations"""
    value = os.getenv(key, '').lower().strip()
    if value in ('true', '1', 'yes', 'on'):
        return True
    if value in ('false', '0', 'no', 'off', ''):
        return default
    raise ValueError(f"Invalid boolean for {key}: '{value}'")

# ✅ Pydantic handles this automatically with proper typing
class Config(BaseSettings):
    debug: bool = False  # Parses "true", "1", "yes", etc.
```

### Integer Parsing Edge Cases

```python
import os

# ❌ DON'T: Crash on invalid input
port = int(os.getenv('PORT'))  # Crashes if "abc" or None

# ✅ DO: Validate with clear errors
def env_int(key: str, default: int | None = None) -> int:
    value = os.getenv(key)
    if value is None:
        if default is None:
            raise ValueError(f"{key} must be set")
        return default
    try:
        return int(value.strip())
    except ValueError:
        raise ValueError(f"{key} must be integer, got: '{value}'")
```

### Case Sensitivity

```python
# Environment variables are case-sensitive on Unix, case-insensitive on Windows

# ❌ DON'T: Assume case behavior
os.getenv('database_url')  # May not match DATABASE_URL on Unix

# ✅ DO: Use consistent casing (UPPER_SNAKE_CASE is convention)
os.getenv('DATABASE_URL')
```

## Related Concepts

- **Project structure** - See [python-project-structure.md](python-project-structure.md) for __main__.py and command module organization
- **Pydantic BaseSettings** - See [python-pydantic-guide.md](python-pydantic-guide.md) for validation details
- **Logging configuration** - See [python-logging-guide.md](python-logging-guide.md) for runtime log control
- **Dependency injection** - See [python-ioc-guide.md](python-ioc-guide.md) for passing config to services
- **Secrets management** - Vault, AWS Secrets Manager, Kubernetes Secrets

## Summary

- **Combine env vars + CLI args** - Env for defaults, CLI for overrides
- **Use Pydantic BaseSettings** for applications (type-safe, validated)
- **Use argparse** for scripts (stdlib, familiar, sufficient)
- **Use typer** for complex CLIs (modern, type-hint driven)
- **Avoid getopt** (legacy, verbose, error-prone)
- **Validate at startup** - Fail fast with clear errors
- **Never log secrets** - Log presence/length only
- **Handle None safely** - Check before using env var values
- **Provide clear defaults** - Document expected env vars
- **Type annotations must match reality** - `os.getenv()` returns `str | None`
