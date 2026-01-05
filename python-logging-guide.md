# Python Logging Guide

Logging patterns for Python applications to ensure consistent, debuggable, and production-ready logging.

## Quick Reference

| Question | Answer |
|----------|--------|
| When to configure logging | Application entry point only (`main.py`) |
| Library logging configuration | Never - libraries ONLY get logger with `__name__` |
| Exception logging | Use `logger.exception()` in except blocks |
| Message formatting | F-strings for INFO+, `%s` for expensive DEBUG |
| Where to log exceptions | Once at system boundaries (handlers, runners) |
| Secret handling | Log length/presence, never actual values |

**Canonical pattern:**
```python
# main.py - Configure once at startup
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

# any_module.py - Get logger at import time
logger = logging.getLogger(__name__)
```

## Log Level Reference

| Level | Use When | Example |
|-------|----------|---------|
| DEBUG | Development diagnostics, verbose details | `logger.debug(f"SQL query: {query}")` |
| INFO | Production status, milestones, state changes | `logger.info("Server started on port 8080")` |
| WARNING | Unexpected but recoverable, deprecated usage | `logger.warning("Cache miss, falling back to DB")` |
| ERROR | Failure that needs attention, request failed | `logger.error("Payment gateway timeout")` |
| CRITICAL | System failure, data loss, requires immediate action | `logger.critical("Out of memory")` |

## Configuration Rules

### Configure Logging Once at Application Entry Point

**Constraint:** Application code MUST call `logging.basicConfig()` exactly once at startup in `main.py`. Library code MUST NOT call `basicConfig()` or configure handlers.

**Rationale:** Multiple configurations cause conflicts, overwrites, and duplicate log entries across modules.

**Examples:**
```python
# [GOOD] Application entry point
# main.py
import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
logger.info("Application started")

# [GOOD] Library module
# mylib/service.py
import logging

logger = logging.getLogger(__name__)  # Get logger only

class UserService:
    def process(self):
        logger.info("Processing user")

# [BAD] Library configuring logging
# mylib/service.py
logging.basicConfig(level=logging.INFO)  # Never do this in libraries

# [BAD] Multiple configurations
# orders/handler.py
logging.basicConfig(level=logging.DEBUG)  # Conflicts with main config
```

### Never Combine basicConfig with Manual Handlers

**Constraint:** Code MUST use either `basicConfig()` OR manual handler setup, never both.

**Rationale:** Combining both creates duplicate handlers that log every message twice.

**Examples:**
```python
# [BAD] Mixing configuration methods
logging.basicConfig(level=logging.INFO)  # Creates default handler
logging.root.addHandler(my_handler)  # Adds second handler - duplicates!

# [GOOD] basicConfig only (simple apps)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# [GOOD] Manual handlers only (advanced apps)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

### Use Module-Level Loggers at Import Time

**Constraint:** Code MUST define loggers at module level using `logger = logging.getLogger(__name__)`, not inside functions.

**Rationale:** Module-level loggers enable hierarchical naming, per-module configuration, and easier log filtering.

**Examples:**
```python
# [GOOD] Module-level logger
# users/service.py
import logging

logger = logging.getLogger(__name__)  # Creates 'users.service' logger

class UserService:
    def create_user(self, username: str):
        logger.info(f"Creating user: username={username}")

# [BAD] Logger inside function
class UserService:
    def create_user(self, username: str):
        logger = logging.getLogger(__name__)  # Recreated every call
        logger.info(f"Creating user: username={username}")

# [GOOD] Per-module level configuration
# main.py
logging.basicConfig(level=logging.INFO)
logging.getLogger('users.service').setLevel(logging.DEBUG)
logging.getLogger('database').setLevel(logging.WARNING)
```

### Include Structured Format with Context

**Constraint:** `basicConfig()` format MUST include timestamp, level, logger name, and line number in pattern `%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s`.

**Rationale:** Structured format enables debugging by showing when, where, and what severity for every log entry.

**Examples:**
```python
# [GOOD] Complete structured format
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)
logger.info(f"Processing order: order_id={order_id}, total={total}")
# Output: 2026-01-05 14:23:15 INFO     [orders.service:45] Processing order: order_id=12345, total=99.99

# [BAD] Missing context
logging.basicConfig(format='%(message)s')  # No timestamp, level, location

# [BAD] Non-ISO date format
logging.basicConfig(datefmt='%m/%d/%y')  # Use %Y-%m-%d %H:%M:%S
```

## Exception Logging Rules

### Use logger.exception() for Exception Logging

**Constraint:** Code MUST use `logger.exception()` inside except blocks to automatically include stack traces.

**Rationale:** `logger.exception()` automatically captures and formats the full stack trace without manual `exc_info=True`.

**Examples:**
```python
# [GOOD] logger.exception() in except block
try:
    result = risky_operation()
except ValueError:
    logger.exception("Validation failed")  # Auto-includes stack trace
    raise

# [GOOD] Alternative with exc_info=True
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise

# [BAD] Missing stack trace
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Failed: {e}")  # No stack trace for debugging

# [GOOD] Stack trace outside exception context
logger.warning("Deprecated code path", stack_info=True)
```

### Log Exceptions Once at System Boundaries

**Constraint:** Code MUST log exceptions at system boundaries (API handlers, job runners, main loops) and MUST NOT log the same exception at multiple layers.

**Rationale:** Logging at every layer creates duplicate log entries for the same error, making debugging harder.

**Examples:**
```python
# [BAD] Logging at every layer
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

# [GOOD] Log once at boundary
def service_method():
    db.execute(query)  # Let exception propagate

def handler():
    try:
        service_method()
    except Exception:
        logger.exception("Failed to process request")  # Log once
        return error_response()
```

## Message Formatting Rules

### Use F-Strings for INFO and Above

**Constraint:** Code MUST use f-strings for INFO/WARNING/ERROR/CRITICAL level messages.

**Rationale:** F-strings provide clarity and have no performance impact at these levels since they're always evaluated.

**Examples:**
```python
# [GOOD] F-strings for INFO and above
logger.info(f"User {username} logged in")
logger.warning(f"Rate limit: {current}/{max}")
logger.error(f"Failed to connect: {connection_error}")

# [BAD] Comma syntax without placeholders
logger.warning("Failed to connect", connection_error)  # Only logs first arg

# [GOOD] Comma syntax with % placeholders (works but less clear)
logger.warning("Failed to connect: %s", connection_error)
```

### Use Lazy Evaluation for Expensive DEBUG Operations

**Constraint:** Code MUST use `%s` formatting (not f-strings) for DEBUG messages with expensive operations.

**Rationale:** `%s` formatting only evaluates arguments if DEBUG level is enabled, avoiding unnecessary computation.

**Examples:**
```python
# [BAD] F-string with expensive DEBUG operation
logger.debug(f"Details: {expensive_serialization(large_object)}")
# Always evaluates, even when DEBUG disabled

# [GOOD] Lazy evaluation with %s
logger.debug("Details: %s", expensive_serialization(large_object))
# Only evaluates if DEBUG enabled

# [GOOD] Explicit guard for expensive operations
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Details: {expensive_serialization(large_object)}")
```

### Include Semantic Context in Messages

**Constraint:** Log messages MUST include business identifiers using key=value format (e.g., `order_id={order_id}`).

**Rationale:** Structured key=value format enables log parsing, filtering, and correlation across requests.

**Examples:**
```python
# [GOOD] Structured context with identifiers
logger.info(f"Processing order: order_id={order_id}, user_id={user_id}")
logger.info(f"Order completed: order_id={order_id}, total={total}, items={len(items)}")

# [BAD] Unstructured message
logger.info(f"Processing order {order_id} for user {user_id}")  # Harder to parse

# [GOOD] Using extra={} for structured context
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

## Security Rules

### Never Log Secret Values

**Constraint:** Code MUST NOT log passwords, tokens, API keys, or other secrets. Code MUST log length or presence instead.

**Rationale:** Logs may be stored insecurely or sent to third-party aggregation systems, exposing credentials.

**Examples:**
```python
# [BAD] Logging secrets
logger.info(f"User login: username={username}, password={password}")
logger.debug(f"API request: Authorization: Bearer {api_token}")

# [GOOD] Log safe information only
logger.info(f"User login: username={username}")
logger.debug(f"API request authenticated: token_length={len(api_token)}")
logger.info(f"Password configured: {password is not None}")

# [GOOD] Mask sensitive data
logger.info(f"Credit card: {card_number[:4]}****{card_number[-4:]}")
```

### Handle None Values Safely

**Constraint:** Code MUST check for None before operations like `len()` on potentially missing values.

**Rationale:** Logging crashes on None values defeat the purpose of diagnostic logging.

**Examples:**
```python
password = os.getenv("PASSWORD")  # May return None

# [BAD] Unsafe None handling
logger.info(f"Password length: {len(password)}")  # Crashes if None

# [GOOD] Safe None handling
logger.info(f"Password length: {len(password) if password else 0}")
logger.info(f"Password configured: {password is not None}")
```

## Log Level Usage Rules

### Use Appropriate Log Levels

**Constraint:** Code MUST use DEBUG for diagnostics, INFO for status, WARNING for unexpected-but-recoverable, ERROR for failures, CRITICAL for system failures.

**Rationale:** Consistent levels enable proper filtering and alerting in production.

**Examples:**
```python
# [GOOD] Appropriate level usage
logger.debug(f"Processing user_id={user_id}, batch_size={len(items)}")
logger.info("Database migration completed successfully")
logger.warning(f"API rate limit approaching: {current_rate}/{max_rate}")
logger.error(f"Failed to send email to {email}: {error}")
logger.critical("Database connection pool exhausted, shutting down")

# [BAD] Wrong levels
logger.info("SQL query: SELECT * FROM users WHERE id=?")  # Use DEBUG
logger.error("Cache miss, falling back to DB")  # Use WARNING
```

## Performance Rules

### Avoid Logging in Tight Loops

**Constraint:** Code MUST NOT log on every iteration of large loops. Code MUST log summary or use sampling instead.

**Rationale:** High-frequency logging creates storage/performance issues and makes logs unsearchable.

**Examples:**
```python
# [BAD] Logging every iteration
for item in large_list:  # 10,000 items
    logger.info(f"Processing {item}")  # 10,000 log entries
    process(item)

# [GOOD] Log summary
logger.info(f"Processing {len(large_list)} items")
for item in large_list:
    process(item)
logger.info(f"Completed processing {len(large_list)} items")

# [GOOD] Sample high-frequency events
sample_rate = 0.01  # 1%
for item in large_list:
    if random.random() < sample_rate:
        logger.debug(f"Processing {item}")
    process(item)
```

### Disable Propagation When Adding Child Handlers

**Constraint:** Code that adds handlers to child loggers MUST set `propagate = False` to prevent duplicate logs.

**Rationale:** Child loggers propagate to root by default, causing messages to be logged twice when both have handlers.

**Examples:**
```python
# [BAD] Child handler without disabling propagation
child_logger = logging.getLogger('myapp.service')
child_logger.addHandler(my_handler)  # Logs go here AND to root

# [GOOD] Disable propagation
child_logger = logging.getLogger('myapp.service')
child_logger.addHandler(my_handler)
child_logger.propagate = False  # Prevent duplicate logs

# [BETTER] Only add handlers to root logger
logging.root.addHandler(my_handler)
```

## Production Patterns

### Structured Logging with JSON Format

**Constraint:** Production systems with log aggregation SHOULD use JSON formatters to output machine-parseable logs.

**Rationale:** JSON format enables automated parsing, filtering, and analysis in log aggregation systems.

**Examples:**
```python
# [GOOD] JSON formatter for production
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

# Configure with manual handlers (not basicConfig)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

### Use Correlation IDs for Distributed Systems

**Constraint:** Distributed systems MUST include request/correlation IDs in all log messages using ContextVars.

**Rationale:** Correlation IDs enable tracing requests across service boundaries and async operations.

**Examples:**
```python
# [GOOD] Correlation ID with ContextVars
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

### Use LoggerAdapter for Repeated Context

**Constraint:** Code that logs multiple messages with the same context (user_id, order_id, request_id) SHOULD use LoggerAdapter.

**Rationale:** LoggerAdapter automatically injects context into every message, reducing repetition and errors.

**Examples:**
```python
# [GOOD] LoggerAdapter for repeated context
class OrderAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[order_id={self.extra['order_id']}] {msg}", kwargs

def process_order(order_id: str):
    order_logger = OrderAdapter(logger, {"order_id": order_id})

    order_logger.info("Processing order")
    # Logs: [order_id=12345] Processing order

    order_logger.info("Order validated")
    # Logs: [order_id=12345] Order validated

# [BAD] Repeating context manually
def process_order(order_id: str):
    logger.info(f"[order_id={order_id}] Processing order")
    logger.info(f"[order_id={order_id}] Order validated")  # Repetitive
```

### Multi-Handler Configuration for Different Outputs

**Constraint:** Applications requiring multiple outputs (console, file, error tracking) MUST use manual handler configuration, not `basicConfig()`.

**Rationale:** `basicConfig()` only supports single handler/format, while manual setup enables per-destination configuration.

**Examples:**
```python
# [GOOD] Multiple handlers with different configs
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

# [BAD] Trying to use basicConfig for multiple handlers
logging.basicConfig(level=logging.INFO)  # Only creates one handler
```

## Common Antipatterns

### Never Use print() for Logging

**Constraint:** Code MUST use logging module, never `print()` for debugging or status output.

**Rationale:** `print()` lacks levels, timestamps, context, and cannot be configured or redirected.

**Examples:**
```python
# [BAD] Using print()
print(f"User {user_id} logged in")

# [GOOD] Using logging
logger.info(f"User login: user_id={user_id}")
```

### Avoid Logging During Interpreter Shutdown

**Constraint:** Code that logs in cleanup/shutdown handlers MUST wrap logging in try/except to handle handler unavailability.

**Rationale:** Logging handlers may be destroyed before cleanup code runs, causing exceptions during shutdown.

**Examples:**
```python
# [GOOD] Safe shutdown logging
import atexit

def cleanup():
    try:
        logger.info("Cleanup started")
        # ... cleanup code
        logger.info("Cleanup completed")
    except Exception:
        pass  # Logging may fail during shutdown

atexit.register(cleanup)
```

### Ensure UTF-8 Encoding for File Handlers

**Constraint:** File handlers MUST specify `encoding='utf-8'` when logging non-ASCII characters.

**Rationale:** Default encoding may vary by platform, causing Unicode errors with international characters.

**Examples:**
```python
# [GOOD] UTF-8 file handler
file_handler = logging.FileHandler('app.log', encoding='utf-8')

user_name = "José García"
logger.info(f"User registered: {user_name}")  # Works correctly
```

## Decision Framework

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

## Related Documentation

- CLI arguments for runtime log level control: [python-cli-arguments-guide.md](python-cli-arguments-guide.md)
