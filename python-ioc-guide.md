# Python Dependency Injection Patterns

Dependency injection (DI) patterns for Python services ensuring testability, loose coupling, and maintainability.

## Quick Reference

| Scenario | Use DI? | Pattern |
|----------|---------|---------|
| Service with database/API calls | Yes | Constructor injection |
| Testability required | Yes | Constructor or function injection |
| Simple script, no tests | No | Direct instantiation |
| Async service | Yes | Async constructor injection |
| Short-lived dependency | Maybe | Function/method injection |

## When to Apply DI

| Need | Use DI? |
|------|---------|
| Multiple implementations | Yes |
| Mock/fake dependencies for tests | Yes |
| External effects (database, API, file I/O) | Yes |
| Clean/hexagonal architecture | Yes |
| Reusable components | Yes |
| Small scripts, one-off utilities | No |
| Trivial dependencies with no config | No |

## Shared Example Types

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class User:
    id: int
    name: str
    email: str

@dataclass
class Order:
    id: int
    customer_id: int
    total: float
    items: list[str]

class Logger(Protocol):
    def info(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...

class UserValidator(Protocol):
    def validate(self, user: User) -> None: ...
```

## Rules

### Use Protocol for Dependency Interfaces

**Constraint:** MUST use `Protocol` for defining dependency interfaces unless shared implementation is required.

**Rationale:** Protocol enables structural typing and works seamlessly with mocks without inheritance overhead.

**Examples:**
```python
# [GOOD]
from typing import Protocol

class UserRepository(Protocol):
    def save(self, user: User) -> None: ...
    def find_by_id(self, user_id: int) -> User | None: ...

# [BAD] - Using ABC when no shared implementation needed
from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None:
        pass
```

**Protocol vs ABC Decision:**

| Need | Use |
|------|-----|
| Type hints for dependencies | Protocol |
| Shared behavior across implementations | ABC |
| Duck typing / structural compatibility | Protocol |
| Runtime enforcement of interface | ABC |
| Testing with mocks | Protocol (or ABC) |

### Use Constructor Injection as Default Pattern

**Constraint:** MUST inject dependencies through `__init__` constructor for class-based services.

**Rationale:** Constructor injection makes dependencies explicit, ensures immutability after construction, and simplifies testing.

**Examples:**
```python
# [GOOD]
class UserService:
    def __init__(
        self,
        repo: UserRepository,
        logger: Logger,
        validator: UserValidator,
    ):
        self._repo = repo
        self._logger = logger
        self._validator = validator

    def create_user(self, user: User) -> None:
        self._validator.validate(user)
        self._repo.save(user)
        self._logger.info(f"Created user {user.id}")

# [BAD] - Creating dependencies internally
class UserService:
    def __init__(self):
        self._repo = SqlUserRepository()  # Tight coupling
        self._logger = ConsoleLogger()
        self._validator = UserValidator()
```

### Store Dependencies as Private Fields

**Constraint:** MUST store injected dependencies as private fields with underscore prefix (`self._repo`).

**Rationale:** Prevents external mutation and clearly indicates internal implementation details.

**Examples:**
```python
# [GOOD]
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo  # Private field

# [BAD]
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo  # Public field allows external mutation
```

### Never Return Values from Constructors

**Constraint:** MUST NOT return values from `__init__` methods.

**Rationale:** Python constructors implicitly return `None`; explicit returns indicate misunderstanding.

**Examples:**
```python
# [GOOD]
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

# [BAD]
class UserService:
    def __init__(self, repo: UserRepository) -> UserService:
        self._repo = repo
        return self  # Invalid in Python
```

### Use Function Injection for Scripts and Pipelines

**Constraint:** MUST use function parameter injection for stateless operations, scripts, CLI tools, and data pipelines.

**Rationale:** Function injection avoids unnecessary class overhead for stateless operations while maintaining testability.

**Examples:**
```python
# [GOOD]
def process_order(
    order: Order,
    repo: OrderRepository,
    notifications: NotificationService,
) -> None:
    """Process order with injected dependencies"""
    repo.save(order)
    notifications.send(order.customer_id, f"Order {order.id} confirmed")

# [BAD] - Using class for stateless operation
class OrderProcessor:
    def __init__(self, repo: OrderRepository, notifications: NotificationService):
        self._repo = repo
        self._notifications = notifications

    def process(self, order: Order) -> None:
        self._repo.save(order)
        self._notifications.send(order.customer_id, f"Order {order.id} confirmed")
```

### Define Async Protocols for Async Dependencies

**Constraint:** MUST use `async def` in Protocol definitions when dependency methods are async.

**Rationale:** Type checker enforces await usage and prevents sync/async mismatches.

**Examples:**
```python
# [GOOD]
class AsyncUserRepository(Protocol):
    async def save(self, user: User) -> None: ...
    async def find_by_id(self, user_id: int) -> User | None: ...

class AsyncUserService:
    def __init__(self, repo: AsyncUserRepository):
        self._repo = repo

    async def create_user(self, user: User) -> None:
        await self._repo.save(user)

# [BAD] - Sync protocol for async methods
class AsyncUserRepository(Protocol):
    def save(self, user: User) -> None: ...  # Missing async

class AsyncUserService:
    async def create_user(self, user: User) -> None:
        await self._repo.save(user)  # Type checker won't catch error
```

### Use AsyncMock for Testing Async Dependencies

**Constraint:** MUST use `AsyncMock` for async dependency methods, not `Mock`.

**Rationale:** `Mock` does not support `await` syntax; `AsyncMock` properly handles async method verification.

**Examples:**
```python
# [GOOD]
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_user_async():
    mock_repo = AsyncMock(spec=AsyncUserRepository)
    service = AsyncUserService(mock_repo)
    user = User(id=1, name="Alice", email="alice@example.com")

    await service.create_user(user)

    mock_repo.save.assert_awaited_once_with(user)

# [BAD] - Using Mock for async methods
from unittest.mock import Mock

async def test_create_user_async():
    mock_repo = Mock(spec=AsyncUserRepository)  # Won't support await
    service = AsyncUserService(mock_repo)
    await service.create_user(user)  # Runtime error
```

### Manage Resource Lifecycle with Context Managers

**Constraint:** MUST use context managers (`with` statements) for resources requiring lifecycle management (connections, sessions, files).

**Rationale:** Context managers ensure cleanup happens even when exceptions occur, preventing resource leaks.

**Examples:**
```python
# [GOOD]
from contextlib import contextmanager
from typing import Generator

@contextmanager
def database_session(connection: DatabaseConnection) -> Generator[DatabaseConnection, None, None]:
    """Manage database connection lifecycle"""
    connection.connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.disconnect()

def process_users(users: list[User], db: DatabaseConnection) -> None:
    with database_session(db) as session:
        for user in users:
            session.execute(f"INSERT INTO users ...")

# [BAD] - Manual cleanup without try/finally
def process_users(users: list[User], db: DatabaseConnection) -> None:
    db.connect()
    for user in users:
        db.execute(f"INSERT INTO users ...")
    db.disconnect()  # Skipped if exception occurs
```

### Use ExitStack for Context Manager Delegation

**Constraint:** MUST use `ExitStack` when wrapping external context managers, NOT direct `__enter__`/`__exit__` calls.

**Rationale:** Direct `__enter__`/`__exit__` calls bypass proper exception handling and resource cleanup. ExitStack properly manages the context protocol.

**Examples:**
```python
# [GOOD] - Use ExitStack for delegation
from contextlib import ExitStack
from external_lib import Client

class APIClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._stack: ExitStack | None = None
        self._client: Client | None = None

    def __enter__(self) -> "APIClient":
        self._stack = ExitStack()
        self._client = self._stack.enter_context(
            Client(self._api_key)
        )
        return self

    def __exit__(self, *args) -> None:
        if self._stack:
            self._stack.__exit__(*args)

# [BAD] - Direct __enter__/__exit__ calls (anti-pattern)
class APIClient:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client: Client | None = None

    def __enter__(self) -> "APIClient":
        self._client = Client(self._api_key)
        self._client.__enter__()  # Anti-pattern: bypasses exception handling
        return self

    def __exit__(self, *args) -> None:
        if self._client:
            self._client.__exit__(*args)  # May not handle exceptions correctly
```

**Reference:** netcup-dns project (`src/netcup_dns/client.py`) demonstrates proper ExitStack usage.

### Use Async Context Managers for Async Resources

**Constraint:** MUST use `@asynccontextmanager` and `async with` for async resources.

**Rationale:** Async context managers properly handle async cleanup without blocking the event loop.

**Examples:**
```python
# [GOOD]
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def async_database_session(
    connection: AsyncDatabaseConnection,
) -> AsyncGenerator[AsyncDatabaseConnection, None]:
    await connection.connect()
    try:
        yield connection
        await connection.commit()
    except Exception:
        await connection.rollback()
        raise
    finally:
        await connection.disconnect()

async def process_users_async(users: list[User], db: AsyncDatabaseConnection) -> None:
    async with async_database_session(db) as session:
        for user in users:
            await session.execute(f"INSERT INTO users ...")

# [BAD] - Using sync context manager for async resource
@contextmanager
def async_database_session(connection: AsyncDatabaseConnection):
    connection.connect()  # Should be await connection.connect()
    try:
        yield connection
    finally:
        connection.disconnect()  # Should be await connection.disconnect()
```

### Inject Configuration Objects, Not Primitives

**Constraint:** MUST inject configuration as single dataclass/Pydantic object when more than 3 configuration parameters exist.

**Rationale:** Configuration objects prevent constructor signature changes and provide validation/defaults centrally.

**Examples:**
```python
# [GOOD]
from dataclasses import dataclass

@dataclass(frozen=True)
class EmailConfig:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    timeout: float = 30.0
    max_retries: int = 3

class EmailService:
    def __init__(self, config: EmailConfig):
        self._config = config

# [BAD] - Too many primitive parameters
class EmailService:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        timeout: float,
        max_retries: int,
    ):
        pass  # Adding new config param breaks all call sites
```

### Bundle Related Dependencies with Dataclass

**Constraint:** MUST group dependencies into frozen dataclass when constructor has 5+ parameters.

**Rationale:** Dependency bundles reduce constructor complexity and group logically related dependencies.

**Examples:**
```python
# [GOOD]
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderDependencies:
    order_repo: OrderRepository
    user_repo: UserRepository
    inventory: InventoryService
    payments: PaymentGateway
    notifications: NotificationService
    analytics: AnalyticsService

class OrderProcessor:
    def __init__(self, deps: OrderDependencies):
        self._deps = deps

    def process_order(self, order: Order) -> None:
        self._deps.payments.charge(order.total)
        self._deps.inventory.reserve(order.items)

# [BAD] - Too many constructor parameters
class OrderProcessor:
    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        inventory: InventoryService,
        payments: PaymentGateway,
        notifications: NotificationService,
        analytics: AnalyticsService,
    ):
        pass  # 6+ parameters = code smell
```

### Never Use Service Locator Pattern

**Constraint:** MUST NOT pull dependencies from container inside constructor.

**Rationale:** Service locator hides dependencies from type signature and causes runtime errors if dependency missing.

**Examples:**
```python
# [GOOD]
class OrderProcessor:
    def __init__(
        self,
        payment_gateway: PaymentGateway,
        inventory: InventoryService,
    ):
        self._payment_gateway = payment_gateway
        self._inventory = inventory

# [BAD] - Service locator anti-pattern
class OrderProcessor:
    def __init__(self, container: Container):
        # Dependencies hidden from signature
        self._payment_gateway = container.get(PaymentGateway)
        self._inventory = container.get(InventoryService)
        # Runtime error if dependency not registered
```

### Avoid Setter Injection Except for Optional Dependencies

**Constraint:** MUST NOT use setter injection for required dependencies; ONLY use for truly optional dependencies.

**Rationale:** Setter injection allows object to exist in incomplete state with missing required dependencies.

**Examples:**
```python
# [GOOD] - Required dependency via constructor
class OrderProcessor:
    def __init__(self, payment_gateway: PaymentGateway):
        self._payment_gateway = payment_gateway
        self._analytics: AnalyticsService | None = None  # Optional

    def set_analytics(self, analytics: AnalyticsService) -> None:
        """Optional: Add analytics tracking"""
        self._analytics = analytics

    def process_order(self, order: Order) -> None:
        self._payment_gateway.charge(order.total)
        if self._analytics:
            self._analytics.track("order_processed", order.id)

# [BAD] - Required dependency via setter
class OrderProcessor:
    def set_payment_gateway(self, gateway: PaymentGateway) -> None:
        self._payment_gateway = gateway

    def process_order(self, order: Order) -> None:
        self._payment_gateway.charge(order.total)  # May not exist
```

### Inject Protocol Types, Not Concrete Implementations

**Constraint:** MUST accept Protocol/ABC types in constructors, NOT concrete implementation classes.

**Rationale:** Injecting concrete types couples service to specific implementation and violates Dependency Inversion Principle.

**Examples:**
```python
# [GOOD]
class OrderProcessor:
    def __init__(self, repo: OrderRepository):  # Protocol
        self._repo = repo

# [BAD]
class OrderProcessor:
    def __init__(self, repo: SqlOrderRepository):  # Concrete class
        self._repo = repo  # Coupled to SQL implementation
```

### Never Use Default Argument Instantiation

**Constraint:** MUST NOT instantiate dependencies in default argument values.

**Rationale:** Default arguments are evaluated once at import time, causing all instances to share the same dependency object.

**Examples:**
```python
# [GOOD] - Use None and factory function
class UserService:
    def __init__(self, repo: UserRepository | None = None):
        self._repo = repo or SqlUserRepository()

# BETTER - Factory function
def create_user_service(repo: UserRepository | None = None) -> UserService:
    return UserService(repo or SqlUserRepository())

# [BAD] - Default creates shared instance
class UserService:
    def __init__(self, repo: UserRepository = SqlUserRepository()):
        self._repo = repo  # Same instance for all UserService objects
```

### Avoid Global Singleton Dependencies

**Constraint:** MUST NOT use module-level singleton instances as dependencies.

**Rationale:** Global singletons create hidden dependencies, prevent testing with mocks, and cause state leaks between tests.

**Examples:**
```python
# [GOOD] - Inject dependency
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

def create_user_service() -> UserService:
    repo = SqlUserRepository(create_database())
    return UserService(repo)

# [BAD] - Module-level singleton
_repo = SqlUserRepository(create_database())

class UserService:
    def __init__(self):
        self._repo = _repo  # Hidden dependency on global
```

### Use Mock(spec=Protocol) for Testing

**Constraint:** MUST use `Mock(spec=ProtocolName)` when creating mocks for dependency protocols.

**Rationale:** `spec` parameter ensures mock only allows methods defined in Protocol, catching errors at test time.

**Examples:**
```python
# [GOOD]
from unittest.mock import Mock

def test_create_user_saves_to_repository():
    mock_repo = Mock(spec=UserRepository)  # Only UserRepository methods allowed
    mock_logger = Mock(spec=Logger)
    service = UserService(repo=mock_repo, logger=mock_logger)

    user = User(id=1, name="Alice", email="alice@example.com")
    service.create_user(user)

    mock_repo.save.assert_called_once_with(user)

# [BAD]
def test_create_user_saves_to_repository():
    mock_repo = Mock()  # No spec = any method call allowed
    service = UserService(repo=mock_repo, logger=Mock())

    service.create_user(user)
    mock_repo.saev.assert_called_once()  # Typo not caught
```

### Use In-Memory Fakes for Integration Testing

**Constraint:** ONLY use in-memory/in-process fakes for integration tests, NOT mocks.

**Rationale:** Fakes provide real behavior without external dependencies, testing integration between components.

**Examples:**
```python
# [GOOD]
class InMemoryUserRepository:
    def __init__(self):
        self._users: dict[int, User] = {}

    def save(self, user: User) -> None:
        self._users[user.id] = user

    def find_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

def test_create_user_integration():
    fake_repo = InMemoryUserRepository()  # Real implementation
    service = UserService(repo=fake_repo, logger=ConsoleLogger())

    user = User(id=1, name="Alice", email="alice@example.com")
    service.create_user(user)

    saved_user = fake_repo.find_by_id(1)
    assert saved_user.name == "Alice"

# [BAD] - Using mocks in integration test
def test_create_user_integration():
    mock_repo = Mock(spec=UserRepository)  # Mock = unit test, not integration
    service = UserService(repo=mock_repo, logger=ConsoleLogger())
```

### Avoid Circular Dependencies

**Constraint:** MUST NOT create circular constructor dependencies between services.

**Rationale:** Circular dependencies prevent either service from being constructed.

**Examples:**
```python
# [BAD] - Circular dependency
class UserService:
    def __init__(self, order_service: OrderService):
        self._order_service = order_service

class OrderService:
    def __init__(self, user_service: UserService):
        self._user_service = user_service  # Can't construct either

# [GOOD] - Introduce third service
class UserOrderCoordinator:
    def __init__(self, user_service: UserService, order_service: OrderService):
        self._user_service = user_service
        self._order_service = order_service

# [GOOD] - Event-based communication
class UserService:
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    def create_user(self, user: User) -> None:
        # Save user
        self._event_bus.publish("user_created", user)

class OrderService:
    def __init__(self, event_bus: EventBus):
        event_bus.subscribe("user_created", self._on_user_created)
```

### Never Inject Framework Objects into Services

**Constraint:** MUST NOT inject web framework request/session objects into service constructors.

**Rationale:** Framework coupling prevents service reuse outside request context and complicates testing.

**Examples:**
```python
# [GOOD] - Extract data, inject repository
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

def create_user_endpoint(request: Request, session: Session):
    service = UserService(SqlUserRepository(session))
    user_data = request.json()
    user = User(**user_data)
    service.create_user(user)

# [BAD] - Framework-coupled service
class UserService:
    def __init__(self, request: Request, session: Session):
        self._request = request  # Coupled to web framework
        self._session = session

    def create_user(self) -> None:
        user_data = self._request.json()  # Can't use outside request context
```

## DI Pattern Decision Framework

### Constructor vs Method vs Function Injection

| Pattern | Use When |
|---------|----------|
| Constructor injection | Class needs dependency for all methods |
| Method injection | Dependency varies per call |
| Function injection | Stateless operations, scripts, pipelines |

### DI Container vs Manual Wiring

| Approach | Use When |
|----------|----------|
| Manual wiring | <10 services, simple graph, clarity preferred |
| DI container | >10 services, complex trees, lifecycle management |

### Sync vs Async

| Pattern | Use When |
|---------|----------|
| Sync DI | Traditional web apps, CLI tools, scripts |
| Async DI | FastAPI, aiohttp, data streaming, high-concurrency |

## Manual Wiring (Recommended for Most Cases)

```python
# factory.py
def create_user_service() -> UserService:
    db = create_database()
    repo = SqlUserRepository(db)
    logger = ConsoleLogger()
    validator = UserValidator()
    return UserService(repo, logger, validator)
```

## IoC Container Example (Optional)

```python
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    database = providers.Singleton(Database, config.db.url)

    user_repository = providers.Factory(
        SqlUserRepository,
        db=database,
    )

    user_service = providers.Factory(
        UserService,
        repo=user_repository,
        logger=providers.Factory(ConsoleLogger),
        validator=providers.Factory(UserValidator),
    )

# Usage
container = Container()
container.config.db.url.from_env("DATABASE_URL")
service = container.user_service()
```

**Use containers when:**
- Many dependencies (>10 services)
- Complex dependency graphs
- Need lifecycle management (singleton, transient, scoped)

## Related Documentation

- [python-architecture-patterns.md](python-architecture-patterns.md) - Service architecture overview, main.py composition root, factory pattern
- [python-pydantic-guide.md](python-pydantic-guide.md) - Validating dependencies at system boundaries
- [python-cli-arguments-guide.md](python-cli-arguments-guide.md) - Injecting config from CLI/env
- [go-architecture-patterns.md](go-architecture-patterns.md) - Equivalent patterns in Go
