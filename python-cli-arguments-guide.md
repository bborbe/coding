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
    kafka_brokers: list[str] = Field(..., env="KAFKA_BROKERS")

    @validator("kafka_brokers", pre=True)
    def parse_brokers(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def main():
    config = AppConfig()  # Validates and loads from env/.env

    print(f"Starting server on port {config.port}")
    print(f"Connecting to Kafka: {config.kafka_brokers}")
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
        description='Process orders from Kafka queue',
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
        '--kafka-brokers',
        default=os.getenv('KAFKA_BROKERS', 'localhost:9092'),
        help='Comma-separated Kafka broker list'
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
    if isinstance(args.kafka_brokers, str):
        args.kafka_brokers = args.kafka_brokers.split(',')

    return args

def main():
    args = parse_args()

    print(f"Port: {args.port}")
    print(f"Brokers: {args.kafka_brokers}")
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
    kafka_brokers: str = typer.Option(
        os.getenv('KAFKA_BROKERS', 'localhost:9092'),
        help="Comma-separated Kafka brokers"
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
    brokers = kafka_brokers.split(',')

    typer.echo(f"Starting server on port {port}")
    typer.echo(f"Kafka brokers: {brokers}")

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
        'kafka-brokers=',
        'debug',
    ])

    port = 8080
    brokers = None
    debug = False

    for opt, arg in opts:
        if opt == '-h':
            print('Usage: ...')
            sys.exit()
        elif opt in ('-p', '--port'):
            port = int(arg)
        elif opt in ('--kafka-brokers'):
            brokers = arg.split(',')
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
brokers: list[str] = os.getenv('KAFKA_BROKERS')
# Returns str | None, not list[str]!

# ✅ DO: Correct type handling
brokers: list[str] | None = None
kafka_brokers_env = os.getenv('KAFKA_BROKERS')
if kafka_brokers_env:
    brokers = kafka_brokers_env.split(',')
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
trading_allowed = env_bool('TRADING_ALLOWED', default=False)
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
brokers = env_list('KAFKA_BROKERS', default=['localhost:9092'])
# KAFKA_BROKERS="broker1:9092,broker2:9092" → ['broker1:9092', 'broker2:9092']
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

## Configuration Validation

### Startup Validation

```python
from pydantic import BaseSettings, Field, validator
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
    except Exception as e:
        print(f"Configuration error: {e}")
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
    kafka_brokers: list[str]
    api_key: str

def main():
    config = Config()

    # Configure logging based on config
    if config.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Log configuration (safely)
    logging.info(f"Port: {config.port}")
    logging.info(f"Kafka brokers: {config.kafka_brokers}")
    logging.info(f"API key configured: {config.api_key is not None}")
    logging.info(f"Debug mode: {config.debug}")
```

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

## Related Concepts

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
