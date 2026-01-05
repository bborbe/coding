# Python Logging Guide

This guide defines logging patterns for Python applications to ensure consistent, debuggable, and production-ready logging.

## Overview

Python's `logging` module provides structured logging with configurable levels, formats, and output destinations. Proper logging is essential for debugging, monitoring, and auditing production systems.

## When to Use Logging

### ✅ Use Logging For:

- **Application state changes** - Startup, shutdown, configuration
- **Error conditions** - Exceptions, validation failures, external service errors
- **Important business events** - Order created, user registered, payment processed
- **Debug information** - Request/response details, intermediate values
- **Performance metrics** - Slow queries, API latency, processing time
- **Audit trails** - User actions, data modifications, access control

### ❌ Don't Use Logging For:

- **Sensitive data** - Passwords, tokens, credit cards, API keys (log length/presence only)
- **High-frequency events** - Every loop iteration, every message processed (use sampling)
- **Binary data** - Images, files (log metadata instead)
- **Debugging with print()** - Use `logging.debug()` instead

## Core Pattern: Basic Configuration

### Application Startup Configuration

```python
import logging

# Configure logging at application entry point (main.py)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Application started")
    # ... rest of application
```

**Key points:**
- Call `basicConfig()` once at application startup (in `main()`)
- Include timestamp, level, filename, and line number in format
- Use ISO-like date format (`%Y-%m-%d %H:%M:%S`)
- Get module-specific logger with `__name__`

### Log Levels

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG - Detailed diagnostic information
logger.debug(f"Processing user_id={user_id}, batch_size={len(items)}")

# INFO - General informational messages
logger.info("Database migration completed successfully")

# WARNING - Something unexpected but recoverable
logger.warning(f"API rate limit approaching: {current_rate}/{max_rate}")

# ERROR - Error condition that doesn't stop the application
logger.error(f"Failed to send email to {email}: {error}")

# CRITICAL - Serious error, application may not continue
logger.critical("Database connection pool exhausted, shutting down")
```

**Level Guidelines:**
- **DEBUG**: Development-only details, verbose output
- **INFO**: Production-ready status updates, milestones
- **WARNING**: Unexpected but handled conditions
- **ERROR**: Failures that need attention but allow continuation
- **CRITICAL**: Failures requiring immediate action or shutdown

## Good vs Bad Patterns

### ✅ Good: Structured Format with Context

```python
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def process_order(order_id: str):
    logger.info(f"Processing order: order_id={order_id}")
    # ...
    logger.info(f"Order processed successfully: order_id={order_id}, total={total}")
```

**Why it's good:**
- Timestamp for when events occurred
- Log level for filtering/alerting
- File and line number for debugging
- Structured key=value format for parsing
- Uses f-strings for formatting

### ✅ Good: Safe Logging of Secrets

```python
password = "secret123"
api_key = os.getenv("API_KEY")

# ✅ Log length/presence, not actual values
logger.info(f"User authenticated: username={username}, password_length={len(password)}")
logger.info(f"API key configured: key_present={api_key is not None}")

# ✅ Mask sensitive data
logger.info(f"Credit card: {card_number[:4]}****{card_number[-4:]}")
```

**Why it's good:**
- Never logs actual secrets
- Provides debugging info (length, presence)
- Masks sensitive data when necessary

### ❌ Bad: Wrong Logging Syntax

```python
# ❌ DON'T: String concatenation with comma
logger.warning("Failed to connect", connection_error)  # Only logs first argument!

# ❌ DON'T: Old-style % formatting
logger.info("User %s logged in" % username)  # Harder to read

# ✅ DO: Use f-strings
logger.warning(f"Failed to connect: {connection_error}")
logger.info(f"User {username} logged in")
```

**Why comma syntax is wrong:**
- `logging.warning("msg", var)` only logs `"msg"` (var is ignored unless it's an exception)
- Use f-strings or `logger.warning("msg %s", var)` with % formatting

### ❌ Bad: Logging Secrets

```python
# ❌ DON'T: Log passwords, tokens, keys
logger.info(f"User login: username={username}, password={password}")
logger.debug(f"API request: Authorization: Bearer {api_token}")

# ✅ DO: Log safe information only
logger.info(f"User login: username={username}")
logger.debug(f"API request authenticated: token_length={len(api_token)}")
```

**Why it's bad:**
- Logs may be stored insecurely, sent to third parties
- Credentials leak in log aggregation systems
- Compliance/security violations

### ❌ Bad: None Handling

```python
password = os.getenv("PASSWORD")  # May return None

# ❌ DON'T: Assume value exists
logger.info(f"Password length: {len(password)}")  # Crashes if password is None

# ✅ DO: Handle None safely
logger.info(f"Password length: {len(password) if password else 0}")
logger.info(f"Password configured: {password is not None}")
```

## Module-Level Loggers

### Recommended Pattern

```python
# users/service.py
import logging

logger = logging.getLogger(__name__)  # Creates 'users.service' logger

class UserService:
    def create_user(self, username: str):
        logger.info(f"Creating user: username={username}")
        # ...
        logger.info(f"User created: user_id={user.id}")
```

**Why use `__name__`:**
- Creates hierarchical logger names (`users.service`, `orders.handler`)
- Allows per-module log level configuration
- Easier to filter logs by component

### Configuring Module-Specific Levels

```python
# main.py
import logging

# Root logger at INFO
logging.basicConfig(level=logging.INFO)

# Set specific modules to DEBUG
logging.getLogger('users.service').setLevel(logging.DEBUG)
logging.getLogger('database').setLevel(logging.WARNING)
```

## Production Patterns

### Structured Logging (JSON)

For production systems with log aggregation (CloudWatch, Datadog, etc.):

```python
import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

**Use when:**
- Logs consumed by aggregation systems
- Need machine-parseable output
- Running in containers/cloud environments

### Exception Logging

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"Validation failed: {e}", exc_info=True)
    raise
except Exception as e:
    logger.critical(f"Unexpected error in risky_operation: {e}", exc_info=True)
    raise
```

**Key points:**
- Use `exc_info=True` to include stack trace
- Log before re-raising to preserve context
- Use ERROR for expected exceptions, CRITICAL for unexpected

### Correlation IDs

For distributed systems, track requests across services:

```python
import logging
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar('request_id', default='')

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True

logging.basicConfig(
    format='%(asctime)s [%(request_id)s] %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)
logger.addFilter(RequestIdFilter())

def handle_request(request):
    request_id_var.set(str(uuid.uuid4()))
    logger.info(f"Processing request: path={request.path}")
    # All logs in this context include request_id
```

## Integration Patterns

### Sentry Integration

```python
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Send ERROR and above to Sentry
sentry_logging = LoggingIntegration(
    level=logging.INFO,       # Capture info and above as breadcrumbs
    event_level=logging.ERROR # Send errors and above as events
)

sentry_sdk.init(
    dsn="https://...",
    integrations=[sentry_logging],
)

logger = logging.getLogger(__name__)

# Automatically captured by Sentry
logger.error("Payment processing failed", exc_info=True)
```

### Multi-Handler Configuration

```python
import logging
from logging.handlers import RotatingFileHandler

# Console handler (INFO and above)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

# File handler (DEBUG and above)
file_handler = RotatingFileHandler(
    'app.log',
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s'
))

# Configure root logger
logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(console_handler)
logging.root.addHandler(file_handler)
```

## Performance Considerations

### Lazy Evaluation

```python
import logging

logger = logging.getLogger(__name__)

# ❌ DON'T: Expensive operation always runs
logger.debug(f"Details: {expensive_serialization(large_object)}")

# ✅ DO: Use lazy evaluation
logger.debug("Details: %s", expensive_serialization(large_object))
# Only evaluates if DEBUG level is enabled

# ✅ DO: Guard expensive operations
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Details: {expensive_serialization(large_object)}")
```

### Sampling High-Frequency Events

```python
import logging
import random

logger = logging.getLogger(__name__)
sample_rate = 0.01  # Log 1% of events

def process_message(message):
    if random.random() < sample_rate:
        logger.debug(f"Processing message: {message}")
    # ... process all messages
```

## Common Mistakes

### ❌ Using print() Instead of Logging

```python
# ❌ DON'T: Use print for debugging
print(f"User {user_id} logged in")

# ✅ DO: Use logging
logger.info(f"User login: user_id={user_id}")
```

**Why logging is better:**
- Configurable levels (turn off debug in production)
- Timestamps and context automatically included
- Can route to files, services, aggregation systems
- Searchable, filterable, parseable

### ❌ Configuring in Multiple Places

```python
# ❌ DON'T: Configure logging in every module
# users/service.py
logging.basicConfig(level=logging.INFO)  # Bad

# orders/handler.py
logging.basicConfig(level=logging.DEBUG)  # Bad - conflicts

# ✅ DO: Configure once in main.py
# main.py
logging.basicConfig(level=logging.INFO)

# users/service.py
logger = logging.getLogger(__name__)  # Good
```

### ❌ Catching and Silencing Errors

```python
# ❌ DON'T: Silent failures
try:
    send_email(user.email)
except Exception:
    pass  # Error disappears

# ✅ DO: Log errors even if handled
try:
    send_email(user.email)
except Exception as e:
    logger.warning(f"Failed to send email to {user.email}: {e}")
    # Continue execution
```

## Decision Framework

### When to Use Each Level

| Level | Use When | Example |
|-------|----------|---------|
| DEBUG | Development diagnostics, verbose details | `logger.debug(f"SQL query: {query}")` |
| INFO | Production status, milestones, state changes | `logger.info("Server started on port 8080")` |
| WARNING | Unexpected but recoverable, deprecated usage | `logger.warning("Cache miss, falling back to DB")` |
| ERROR | Failure that needs attention, request failed | `logger.error("Payment gateway timeout")` |
| CRITICAL | System failure, data loss, requires immediate action | `logger.critical("Out of memory")` |

### basicConfig vs Custom Configuration

**Use `basicConfig()`:**
- Simple applications
- Single output destination
- Quick setup

**Use custom handlers:**
- Multiple outputs (console + file + Sentry)
- Different formats per destination
- Rotating log files
- Production systems

### Module Logger vs Root Logger

**Use module logger (`__name__`):**
- Libraries and reusable components
- Want per-module control
- Multi-module applications

**Use root logger (`logging.info()`):**
- Simple scripts
- Single-file applications
- Quick prototypes

## Related Concepts

- **Structured logging** - JSON format for machine parsing
- **Log aggregation** - CloudWatch, Datadog, Splunk
- **Observability** - Metrics, traces, logs (three pillars)
- **CLI arguments** - For runtime log level control, see [python-cli-arguments-guide.md](python-cli-arguments-guide.md)

## Summary

- **Configure once** at application startup with `basicConfig()`
- **Use structured format** with timestamp, level, location
- **Never log secrets** - log length/presence instead
- **Use f-strings** for formatting, not comma syntax
- **Handle None safely** when logging variable-length data
- **Use module loggers** (`__name__`) for better organization
- **Include context** in messages (IDs, values, error details)
- **Use appropriate levels** - DEBUG for dev, INFO for production status
- **Integrate with monitoring** - Sentry for errors, JSON for aggregation
