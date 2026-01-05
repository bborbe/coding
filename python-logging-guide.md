# Python Logging Guide

This guide defines logging patterns for Python applications to ensure consistent, debuggable, and production-ready logging.

## Overview

Python's `logging` module provides structured logging with configurable levels, formats, and output destinations. Proper logging is essential for debugging, monitoring, and auditing production systems.

## Quick Reference

**Canonical configuration (applications only):**
```python
import logging

# Configure once at startup (main.py)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Get module-level logger (at import time)
logger = logging.getLogger(__name__)
```

**Do:**
- ✅ Use `logger.exception()` for exception logging
- ✅ Use f-strings for INFO/WARNING/ERROR
- ✅ Use `%s` formatting for expensive DEBUG operations
- ✅ Log once at system boundaries (API handlers, job runners)
- ✅ Use `extra={}` for structured context

**Don't:**
- ❌ Never call `basicConfig()` in libraries
- ❌ Never log secrets (log length/presence instead)
- ❌ Never use `print()` for debugging
- ❌ Never log the same exception at multiple layers
- ❌ Never combine `basicConfig()` + manual handlers

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
    format='%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Module-level logger (define at import time, not in functions)
logger = logging.getLogger(__name__)

def main():
    logger.info("Application started")
    # ... rest of application
```

**Key points:**
- Call `basicConfig()` **once** at application startup (in `main()`)
- **Never** call `basicConfig()` in libraries or reusable modules
- Include **format structure**: timestamp, level, logger name, line number
- Include **semantic context**: user_id, order_id, request_id (in message)
- Use ISO-like date format (`%Y-%m-%d %H:%M:%S`)
- Get module-specific logger with `__name__` at module import time

### Library vs Application Logging

**Applications** (executables, services, scripts):
```python
# main.py
import logging

# ✅ Applications configure logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)
```

**Libraries** (reusable packages, modules):
```python
# mylib/service.py
import logging

# ✅ Libraries get logger but NEVER configure
logger = logging.getLogger(__name__)

# ❌ Libraries NEVER call basicConfig() or add handlers
# ❌ Libraries NEVER set global log levels

class UserService:
    def process(self):
        logger.info("Processing user")  # Good - just log
```

**Why libraries must not configure:**
- Application controls all logging configuration
- Libraries would overwrite application settings
- Causes conflicts in multi-library applications

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

## Common Mistakes (Read This First!)

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

### ❌ Configuring in Libraries or Multiple Places

```python
# ❌ DON'T: Configure logging in libraries
# mylib/service.py
logging.basicConfig(level=logging.INFO)  # Bad - library must not configure

# ❌ DON'T: Configure in every module
# orders/handler.py
logging.basicConfig(level=logging.DEBUG)  # Bad - conflicts with main config

# ✅ DO: Configure once in main.py only
# main.py
logging.basicConfig(level=logging.INFO)

# mylib/service.py
logger = logging.getLogger(__name__)  # Good - just get logger
```

### ❌ Logging the Same Exception at Multiple Layers

```python
# ❌ DON'T: Log exception at every layer (log spam)
def service_method():
    try:
        db.execute(query)
    except Exception as e:
        logger.error(f"DB error: {e}", exc_info=True)  # Logged here
        raise

def handler():
    try:
        service_method()
    except Exception as e:
        logger.error(f"Handler error: {e}", exc_info=True)  # AND here - duplicate!
        raise

# ✅ DO: Log once at the boundary
def service_method():
    # Just let exception propagate
    db.execute(query)

def handler():
    try:
        service_method()
    except Exception:
        # Log once at system boundary
        logger.exception("Failed to process request")
        return error_response()
```

**Rule:** Log exceptions once at system boundaries (API handlers, job runners, main loops), not at every layer.

### ❌ Logging Secrets

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

### ❌ Wrong Logging Syntax

```python
# ❌ DON'T: Comma without % placeholder (silently ignored!)
logger.warning("Failed to connect", connection_error)  # Only logs "Failed to connect"

# ✅ DO: Use f-strings for INFO/WARNING/ERROR
logger.warning(f"Failed to connect: {connection_error}")

# ✅ DO: Use % formatting with lazy evaluation for DEBUG
logger.debug("Connection details: %s", expensive_function())  # Only evaluates if DEBUG enabled
```

**Clarification on comma syntax:**
- `logger.warning("msg", var)` **only works** with `%s` placeholders: `logger.warning("msg %s", var)`
- Without `%s`, the second argument is silently ignored
- For INFO and above, use f-strings (clearer, no performance impact)
- For DEBUG with expensive operations, use `%s` for lazy evaluation

### ❌ Combining basicConfig() and Manual Handlers

```python
# ❌ DON'T: Mix basicConfig with manual handler setup
logging.basicConfig(level=logging.INFO)  # Sets up default handler
logging.root.addHandler(my_handler)  # Adds another - now you have TWO handlers!

# ✅ DO: Choose one approach
# Option 1: basicConfig only (simple apps)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# Option 2: Manual handlers only (advanced apps)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

**Note:** Examples in this guide are mutually exclusive, not cumulative. Don't combine different configuration patterns.

### ❌ None Handling

```python
password = os.getenv("PASSWORD")  # May return None

# ❌ DON'T: Assume value exists
logger.info(f"Password length: {len(password)}")  # Crashes if password is None

# ✅ DO: Handle None safely
logger.info(f"Password length: {len(password) if password else 0}")
logger.info(f"Password configured: {password is not None}")
```

### ❌ Logging in Tight Loops

```python
# ❌ DON'T: Log every iteration (production hazard)
for item in large_list:  # 10,000 items
    logger.info(f"Processing {item}")  # 10,000 log entries!
    process(item)

# ✅ DO: Log summary or sample
logger.info(f"Processing {len(large_list)} items")
for item in large_list:
    process(item)
logger.info(f"Completed processing {len(large_list)} items")

# ✅ DO: Sample high-frequency events (see Performance section)
```

### ❌ Duplicate Logs Due to Propagation

```python
# ❌ DON'T: Add handlers to child loggers without managing propagation
child_logger = logging.getLogger('myapp.service')
child_logger.addHandler(my_handler)  # Logs go here AND propagate to root!

# ✅ DO: Disable propagation if adding child handlers
child_logger = logging.getLogger('myapp.service')
child_logger.addHandler(my_handler)
child_logger.propagate = False  # Prevent duplicate logs

# ✅ BETTER: Only add handlers to root logger
logging.root.addHandler(my_handler)
```

## Good Patterns

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
- **Format structure**: Timestamp, level, logger name, line number
- **Semantic context**: order_id, total (business data)
- Uses f-strings for clarity
- Structured key=value format for parsing

### ✅ Good: Exception Logging with logger.exception()

```python
import logging

logger = logging.getLogger(__name__)

# ✅ BEST: Use logger.exception() in except blocks
try:
    result = risky_operation()
except ValueError:
    logger.exception("Validation failed")  # Automatically includes stack trace
    raise

# ✅ ALTERNATIVE: Use exc_info=True with other levels
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise
```

**Key points:**
- `logger.exception()` is shorthand for `logger.error(..., exc_info=True)`
- Use `exception()` inside `except` blocks for automatic stack traces
- Log before re-raising to preserve context
- For non-exception stack traces, use `stack_info=True`:

```python
logger.warning("Deprecated code path", stack_info=True)
```

### ✅ Good: Structured Context with extra={}

```python
import logging

logger = logging.getLogger(__name__)

# Add structured context to log records
logger.info(
    "Order processed",
    extra={
        "order_id": order_id,
        "user_id": user_id,
        "total": total,
        "items": len(items)
    }
)
```

**Use with custom formatter:**
```python
class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Access extra fields
        order_id = getattr(record, 'order_id', None)
        return f"{record.levelname}: {record.getMessage()} [order={order_id}]"
```

**Especially useful for JSON logging** where extra fields become top-level JSON keys.

### ✅ Good: LoggerAdapter for Contextual Data

```python
import logging

logger = logging.getLogger(__name__)

class OrderAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # Inject context into every log message
        return f"[order_id={self.extra['order_id']}] {msg}", kwargs

def process_order(order_id: str):
    # Create adapter with context
    order_logger = OrderAdapter(logger, {"order_id": order_id})

    order_logger.info("Processing order")
    # Logs: [order_id=12345] Processing order

    order_logger.info("Order validated")
    # Logs: [order_id=12345] Order validated
```

**Use when:** Multiple log calls need the same context (user_id, request_id, order_id).

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

## Module-Level Loggers

### Recommended Pattern

```python
# users/service.py
import logging

# Get logger at module import time (not inside functions)
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
- Convention for library code

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

        # Include extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info']:
                log_data[key] = value

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)

# Configure with manual handlers (don't use basicConfig)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

**Use when:**
- Logs consumed by aggregation systems
- Need machine-parseable output
- Running in containers/cloud environments

### Correlation IDs for Distributed Systems

Track requests across services using ContextVars:

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

**Note on async/concurrency:**
- Logging module is thread-safe
- Use `ContextVar` for async frameworks (FastAPI, aiohttp)
- `threading.local()` for synchronous multi-threading
- ContextVars automatically isolate context per async task

## Integration Patterns

### Error Tracking Service Integration

```python
import logging
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

# Send ERROR and above to error tracking service
sentry_logging = LoggingIntegration(
    level=logging.INFO,       # Capture info and above as breadcrumbs
    event_level=logging.ERROR # Send errors and above as events
)

sentry_sdk.init(
    dsn="https://...",
    integrations=[sentry_logging],
)

logger = logging.getLogger(__name__)

# Automatically captured by error tracking
logger.exception("Payment processing failed")
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

# Configure root logger (don't use basicConfig when using custom handlers)
logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(console_handler)
logging.root.addHandler(file_handler)
```

## Performance Considerations

### F-Strings vs Lazy Evaluation

**Rule:**
- Use **f-strings** for INFO/WARNING/ERROR/CRITICAL (always evaluated, clarity matters)
- Use **`%s` formatting** for DEBUG with expensive operations (lazy evaluation)

```python
import logging

logger = logging.getLogger(__name__)

# ✅ F-strings for INFO and above (no performance impact)
logger.info(f"User {username} logged in")
logger.warning(f"Rate limit: {current}/{max}")

# ❌ DON'T: F-string with expensive DEBUG operation
logger.debug(f"Details: {expensive_serialization(large_object)}")
# Always evaluates, even when DEBUG disabled!

# ✅ DO: Use %s formatting for expensive DEBUG operations
logger.debug("Details: %s", expensive_serialization(large_object))
# Only evaluates if DEBUG level is enabled

# ✅ DO: Guard expensive operations explicitly
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

**Use when:** Processing thousands of items/second and full logging would overwhelm storage.

## Edge Cases and Gotchas

### Logging During Interpreter Shutdown

```python
import logging
import atexit

logger = logging.getLogger(__name__)

# ⚠️ Logging may fail during shutdown (handlers may be None)
def cleanup():
    try:
        logger.info("Cleanup started")
        # ... cleanup code
        logger.info("Cleanup completed")
    except Exception:
        # Logging may not work here if interpreter is shutting down
        pass

atexit.register(cleanup)
```

**Mitigation:** Use try/except around shutdown logging, or flush logs before cleanup.

### Unicode and Non-ASCII Characters

```python
import logging

logger = logging.getLogger(__name__)

# ✅ Python 3 handles Unicode natively
user_name = "José García"
logger.info(f"User registered: {user_name}")

# ✅ Ensure file handlers use UTF-8
file_handler = logging.FileHandler('app.log', encoding='utf-8')
```

**Note:** Python 3 handles Unicode strings natively. Only specify encoding for file handlers.

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
- Multiple outputs (console + file + error tracking)
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

- **Configure once** at application startup with `basicConfig()` (never in libraries)
- **Use `logger.exception()`** for exception logging in except blocks
- **Use structured format** with timestamp, level, location
- **Use `extra={}`** for structured context in log records
- **Never log secrets** - log length/presence instead
- **Use f-strings for INFO+**, `%s` for expensive DEBUG operations
- **Handle None safely** when logging variable-length data
- **Use module loggers** (`__name__`) at import time for better organization
- **Log once at boundaries** (API handlers, job runners), not every layer
- **Include context** in messages (IDs, values, error details)
- **Never combine** `basicConfig()` and manual handler setup
- **Watch for log duplication** due to propagation with child handlers
- **Integrate with monitoring** - Error tracking for exceptions, JSON for aggregation
