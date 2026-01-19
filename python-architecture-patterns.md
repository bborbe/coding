# Python Service Architecture Patterns

Standard patterns for building Python services with dependency injection, clean architecture, and testability.

## Overview

The standard pattern for Python services follows this structure:
1. **Protocol** - Define the contract (interface)
2. **Constructor** - Inject dependencies via `__init__`
3. **Private fields** - Store dependencies with underscore prefix
4. **Methods** - Business logic with runtime parameters only

## 1. Core Pattern: Constructor Injection

### Protocol Definition

```python
from typing import Protocol

class UserRepository(Protocol):
    def save(self, user: User) -> None: ...
    def find_by_id(self, user_id: int) -> User | None: ...
```

### Service Implementation

```python
class UserService:
    def __init__(
        self,
        repo: UserRepository,
        logger: Logger,
        validator: UserValidator,
    ):
        self._repo = repo           # Static dependency
        self._logger = logger       # Static dependency
        self._validator = validator # Static dependency

    def create_user(self, user: User) -> None:  # Runtime param only
        self._validator.validate(user)
        self._repo.save(user)
        self._logger.info(f"Created user {user.id}")
```

**Key points:**
- Constructor receives ALL dependencies (static, mockable)
- Methods receive ONLY runtime data (request params, user input)
- Dependencies stored as private fields (`self._dep`)
- Clean separation: deps bound once, methods reusable

## 2. main.py Pattern (Composition Root)

The `main.py` is the **composition root** where all dependencies are wired together.

### Structure

```python
#!/usr/bin/env python3
import os
import sys
import logging
import signal

def main(argv):
    # 1. Configure logging
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        level=logging.INFO,
    )

    # 2. Parse configuration (env vars, CLI args)
    db_url: str = os.getenv('DATABASE_URL')
    api_key: str = os.getenv('API_KEY')
    port: int = int(os.getenv('PORT', '8080'))

    # 3. Create infrastructure (external connections)
    database = Database(db_url)
    api_client = ApiClient(api_key)

    # 4. Wire services (composition / factory pattern)
    user_repo = SqlUserRepository(database)
    validator = UserValidator()
    logger = ConsoleLogger()

    user_service = UserService(
        repo=user_repo,
        logger=logger,
        validator=validator,
    )

    # 5. Create handlers/consumers
    handler = UserHandler(user_service)
    server = HttpServer(port, handler)

    # 6. Setup shutdown
    def shutdown(signum, frame):
        logging.info('Shutting down...')
        server.shutdown()
        database.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # 7. Run
    server.run()

if __name__ == '__main__':
    main(sys.argv[1:])
```

**Key points:**
- Single entry point, all wiring happens here
- Infrastructure created first (db, clients)
- Services composed with explicit dependencies
- Shutdown handling for graceful cleanup

## 3. Factory Pattern

When wiring becomes complex, extract to factory functions. See **[python-factory-pattern.md](python-factory-pattern.md)** for detailed patterns.

**Quick rules:**
- `create_*` prefix for factory functions
- Zero business logic - only constructor calls
- All factories in single file: `pkg/factory.py`

```python
# factory.py
def create_user_service(database: Database) -> UserService:
    return UserService(
        repo=SqlUserRepository(database),
        logger=ConsoleLogger(),
        validator=UserValidator(),
    )

# main.py
def main(argv):
    # ... config and infrastructure ...
    user_service = create_user_service(database)
    # ... run ...
```

## 4. Sender/Fetcher Pattern

Common pattern for services that fetch data and send it elsewhere.

### Pattern Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         Fetcher                                  │
│  - Takes: external API client + Sender                          │
│  - Does: fetch data → iterate → delegate to sender              │
│  - Returns: count or result                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Sender                                   │
│  - Takes: output client (queue, API, etc.)                      │
│  - Does: format and send single item                            │
│  - Single responsibility                                         │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
class OrderSender:
    def __init__(self, queue_client: QueueClient, topic: str):
        self._queue_client = queue_client
        self._topic = topic

    def send_order(self, order: dict) -> None:
        self._queue_client.send(
            topic=self._topic,
            key=str(order["id"]),
            value=order,
        )


class OrderFetcher:
    def __init__(self, api_client: ApiClient, sender: OrderSender):
        self._api_client = api_client
        self._sender = sender

    def fetch_orders(self, from_date: datetime, until_date: datetime) -> int:
        orders = self._api_client.get_orders(from_date, until_date)

        counter = 0
        for order in orders:
            self._sender.send_order(order)
            counter += 1

        return counter
```

### Wiring

```python
# In main.py or factory.py
order_fetcher = OrderFetcher(
    api_client=RestApiClient(api_url),
    sender=OrderSender(
        queue_client=KafkaClient(brokers),
        topic=f"{environment}-orders",
    ),
)
```

## 5. Async Patterns

### Async Service

```python
class AsyncUserRepository(Protocol):
    async def save(self, user: User) -> None: ...
    async def find_by_id(self, user_id: int) -> User | None: ...


class AsyncUserService:
    def __init__(self, repo: AsyncUserRepository, logger: Logger):
        self._repo = repo
        self._logger = logger

    async def create_user(self, user: User) -> None:
        await self._repo.save(user)
        self._logger.info(f"Created user {user.id}")
```

### Async main.py

```python
import asyncio

async def main():
    database = await AsyncDatabase.connect(db_url)

    user_service = AsyncUserService(
        repo=AsyncSqlUserRepository(database),
        logger=ConsoleLogger(),
    )

    server = AsyncHttpServer(port, UserHandler(user_service))
    await server.run()

if __name__ == '__main__':
    asyncio.run(main())
```

## 6. Python Version Consistency

**Constraint:** `requires-python`, `target-version`, and `python_version` MUST specify the same Python version in `pyproject.toml`.

**Rationale:** Mismatched versions cause type checking/linting to use different Python semantics than runtime, leading to false positives or missed errors.

**Check locations in pyproject.toml:**
```toml
[project]
requires-python = ">=3.12"           # Runtime requirement

[tool.ruff]
target-version = "py312"             # Linting/formatting target

[tool.mypy]
python_version = "3.12"              # Type checking target
```

**Example:**
```toml
# [GOOD] - All versions match
[project]
requires-python = ">=3.12"

[tool.ruff]
target-version = "py312"

[tool.mypy]
python_version = "3.12"

# [BAD] - Mismatched versions
[project]
requires-python = ">=3.10"

[tool.ruff]
target-version = "py312"             # Inconsistent!

[tool.mypy]
python_version = "3.11"              # Inconsistent!
```

**Reference:** alertmanager-mcp project demonstrates correct version consistency.

## 7. Type Casting for External API Responses

**Constraint:** External API responses MUST use `typing.cast()` when strict mypy is enabled.

**Rationale:** HTTP clients and external libraries return `Any`, breaking strict type checking. Explicit casting documents expected structure and enables type safety throughout the codebase.

**Examples:**
```python
# [GOOD] - Explicit casting for external API
from typing import cast, Any
import requests

class AlertmanagerClient:
    def get_alerts(self) -> list[dict[str, Any]]:
        response = self._request("GET", "/api/v2/alerts")
        return cast(list[dict[str, Any]], response)

    def _request(self, method: str, path: str) -> Any:
        return requests.request(method, self._base_url + path).json()

# [BAD] - Returns Any, breaks strict mypy
class AlertmanagerClient:
    def get_alerts(self):  # Implicit return type: Any
        return self._request("GET", "/api/v2/alerts")
```

**When to cast:**
- HTTP API responses (`requests.get().json()`)
- External library returns with `Any` type
- Database query results without ORM
- JSON parsing results (`json.loads()`)

**Reference:** alertmanager-mcp client.py demonstrates casting for API responses.

## 8. File Organization

```
service-name/
├── main.py              # Entry point, composition root
├── pkg/
│   ├── __init__.py
│   ├── service.py       # Business logic (UserService, etc.)
│   ├── handler.py       # HTTP/message handlers
│   ├── repository.py    # Data access implementations
│   ├── factory.py       # Factory functions (if complex wiring)
│   └── types.py         # Domain types, dataclasses
├── tests/
│   ├── conftest.py      # Shared fixtures with full type hints
│   ├── test_service.py
│   └── test_handler.py
├── requirements.txt
└── Dockerfile
```

## 9. Common Antipatterns

### DON'T: Create dependencies inside constructor

```python
# ❌ BAD - tight coupling, not testable
class UserService:
    def __init__(self):
        self._repo = SqlUserRepository()  # Hidden dependency
        self._logger = ConsoleLogger()

# ✅ GOOD - explicit injection
class UserService:
    def __init__(self, repo: UserRepository, logger: Logger):
        self._repo = repo
        self._logger = logger
```

### DON'T: Pass dependencies through methods

```python
# ❌ BAD - dependency passed at runtime
class UserService:
    def create_user(self, user: User, repo: UserRepository) -> None:
        repo.save(user)

# ✅ GOOD - dependency injected at construction
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def create_user(self, user: User) -> None:
        self._repo.save(user)
```

### DON'T: Business logic in factory/main.py

```python
# ❌ BAD - logic in composition root
def main():
    user = User(name="John")
    if not user.name:  # Business logic!
        raise ValueError("Invalid user")

# ✅ GOOD - logic in service
def main():
    service = create_user_service(database)
    service.create_user(user)  # Validation inside service
```

### DON'T: Use global singletons

```python
# ❌ BAD - hidden global state
_database = None

def get_database():
    global _database
    if _database is None:
        _database = Database(os.getenv('DB_URL'))
    return _database

class UserService:
    def __init__(self):
        self._db = get_database()  # Hidden dependency

# ✅ GOOD - explicit injection
class UserService:
    def __init__(self, database: Database):
        self._db = database
```

## 10. Testing

### Shared Test Fixtures with Type Hints

**Constraint:** Shared pytest fixtures in `tests/conftest.py` MUST have full type hints for strict mypy compliance.

**Rationale:** Fixtures without type hints break strict type checking in test files. Type hints enable IDE support and catch fixture usage errors.

**Examples:**
```python
# tests/conftest.py

# [GOOD] - Full type hints on fixtures
from typing import Any
import pytest
from pytest_mock import MockerFixture

@pytest.fixture
def mock_alertmanager_env(mocker: MockerFixture) -> Any:
    """Mock Alertmanager environment variables with defaults."""
    def mock_getenv(key: str, default: str | None = None) -> str | None:
        env_vars = {
            "ALERTMANAGER_URL": "http://fake-alertmanager",
            "ALERTMANAGER_TIMEOUT": "30",
        }
        return env_vars.get(key, default)
    return mocker.patch("os.getenv", side_effect=mock_getenv)

@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(id=1, name="Alice", email="alice@example.com")

# [BAD] - No type hints
@pytest.fixture
def mock_env(mocker):  # Missing types
    return mocker.patch("os.getenv")

@pytest.fixture
def sample_user():  # Missing return type
    return User(id=1, name="Alice")
```

**Reference:** alertmanager-mcp tests/conftest.py demonstrates properly typed fixtures.

### Unit Test with Mocks

```python
from unittest.mock import Mock

def test_create_user_saves_to_repository():
    mock_repo = Mock(spec=UserRepository)
    mock_logger = Mock(spec=Logger)

    service = UserService(repo=mock_repo, logger=mock_logger)
    user = User(id=1, name="Alice", email="alice@example.com")

    service.create_user(user)

    mock_repo.save.assert_called_once_with(user)
```

### Integration Test with Fakes

```python
class InMemoryUserRepository:
    def __init__(self):
        self._users: dict[int, User] = {}

    def save(self, user: User) -> None:
        self._users[user.id] = user

    def find_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)


def test_user_service_integration():
    fake_repo = InMemoryUserRepository()
    service = UserService(repo=fake_repo, logger=ConsoleLogger())

    user = User(id=1, name="Alice", email="alice@example.com")
    service.create_user(user)

    assert fake_repo.find_by_id(1).name == "Alice"
```

## Related Documentation

- [python-project-structure.md](python-project-structure.md) - Project layout, pyproject.toml, src/ layout, test organization
- [python-factory-pattern.md](python-factory-pattern.md) - Detailed factory patterns, antipatterns, file organization
- [python-ioc-guide.md](python-ioc-guide.md) - Detailed DI patterns, Protocol vs ABC, async patterns
- [python-logging-guide.md](python-logging-guide.md) - Logging configuration and best practices
- [python-cli-arguments-guide.md](python-cli-arguments-guide.md) - CLI argument and env var parsing
- [python-pydantic-guide.md](python-pydantic-guide.md) - Data validation with Pydantic
- [go-architecture-patterns.md](go-architecture-patterns.md) - Equivalent patterns in Go
