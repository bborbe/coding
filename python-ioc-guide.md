# Python Dependency Injection Patterns

This guide defines dependency injection (DI) patterns for Python services to ensure testability, loose coupling, and maintainability.

## Overview

**Inversion of Control (IoC)** is a design principle where control of object creation is transferred from application code to external components.

**Dependency Injection (DI)** is the primary technique for implementing IoC by providing dependencies from outside instead of creating them internally.

## At a Glance

| Scenario | Use DI? | Pattern |
|----------|---------|---------|
| Service with database/API calls | Yes | Constructor injection |
| Testability required | Yes | Constructor or function injection |
| Simple script, no tests | No | Direct instantiation |
| Async service | Yes | Async constructor injection |
| Short-lived dependency | Maybe | Function/method injection |

## Shared Example Types

These types are used throughout this guide:

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

## When to Use Dependency Injection

### Use DI When:
- Building services or libraries with multiple implementations
- Testability is critical (need to inject mocks/fakes)
- Dependencies have external effects (database, API calls, file I/O)
- Following clean architecture or hexagonal architecture patterns
- Building reusable components

### Skip DI When:
- Writing small scripts or one-off utilities
- Dependency is trivial (e.g., `datetime.now()` wrapper with no config)
- Over-engineering simple code

## Protocol vs ABC

Python offers two mechanisms for defining interfaces:

### Protocol (Preferred for DI)

```python
from typing import Protocol

class UserRepository(Protocol):
    def save(self, user: User) -> None: ...
    def find_by_id(self, user_id: int) -> User | None: ...
```

**Use Protocol when:**
- Consumer-side typing (define what you need)
- Structural/duck typing (any class with matching methods works)
- No shared implementation needed
- Testing with mocks (Protocol works with `Mock(spec=...)`)

### ABC (Abstract Base Class)

```python
from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None:
        pass

    @abstractmethod
    def find_by_id(self, user_id: int) -> User | None:
        pass

    def exists(self, user_id: int) -> bool:
        """Shared implementation for all subclasses"""
        return self.find_by_id(user_id) is not None
```

**Use ABC when:**
- Need shared default implementations
- Runtime enforcement (TypeError if abstract method not implemented)
- Framework/library design with explicit inheritance
- Want to prevent direct instantiation

### Decision

| Need | Use |
|------|-----|
| Type hints for dependencies | Protocol |
| Shared behavior across implementations | ABC |
| Duck typing / structural compatibility | Protocol |
| Runtime enforcement of interface | ABC |
| Testing with mocks | Protocol (or ABC) |

**Default choice:** Use `Protocol` for dependency injection interfaces.

## Core Pattern: Constructor Injection

Constructor injection is the **preferred** DI pattern in Python.

### Interface → Constructor → Implementation

```python
from typing import Protocol

class UserRepository(Protocol):
    def save(self, user: User) -> None: ...
    def find_by_id(self, user_id: int) -> User | None: ...

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

# Concrete implementation
class SqlUserRepository:
    def __init__(self, db: Database):
        self._db = db

    def save(self, user: User) -> None:
        self._db.execute("INSERT INTO users ...")

    def find_by_id(self, user_id: int) -> User | None:
        return self._db.query("SELECT * FROM users WHERE id = ?", user_id)
```

**Key Points:**
- Use `Protocol` for structural typing (duck typing with type hints)
- Accept dependencies in `__init__` only
- Store dependencies as private fields (`self._repo`)
- Return nothing from `__init__` (constructors never return values)
- Use type hints for all parameters

## Function-Level Dependency Injection

For scripts, data pipelines, and non-OOP codebases, use function parameters:

### Basic Function Injection

```python
from typing import Protocol

class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...

class NotificationService(Protocol):
    def send(self, customer_id: int, message: str) -> None: ...

def process_order(
    order: Order,
    repo: OrderRepository,
    notifications: NotificationService,
) -> None:
    """Process order with injected dependencies"""
    repo.save(order)
    notifications.send(order.customer_id, f"Order {order.id} confirmed")
```

**When to use:**
- Scripts and CLI tools
- Data pipelines
- Functional programming style
- Stateless operations

### Testing Function Injection

```python
from unittest.mock import Mock

def test_process_order_saves_and_notifies():
    mock_repo = Mock(spec=OrderRepository)
    mock_notifications = Mock(spec=NotificationService)

    order = Order(id=1, customer_id=42, total=99.99, items=["item1"])

    process_order(order, mock_repo, mock_notifications)

    mock_repo.save.assert_called_once_with(order)
    mock_notifications.send.assert_called_once_with(42, "Order 1 confirmed")
```

### Partial Application for Convenience

```python
from functools import partial

# Wire dependencies once
repo = SqlOrderRepository(db)
notifications = EmailNotificationService(smtp)

# Create partially applied function
process = partial(process_order, repo=repo, notifications=notifications)

# Use without repeating dependencies
process(order1)
process(order2)
```

## Async Dependency Injection

Modern Python (3.10+) heavily uses `async/await`. DI patterns apply equally:

### Async Protocol Definition

```python
from typing import Protocol

class AsyncUserRepository(Protocol):
    async def save(self, user: User) -> None: ...
    async def find_by_id(self, user_id: int) -> User | None: ...

class AsyncNotificationService(Protocol):
    async def send(self, user_id: int, message: str) -> None: ...
```

### Async Service with Constructor Injection

```python
class AsyncUserService:
    def __init__(
        self,
        repo: AsyncUserRepository,
        notifications: AsyncNotificationService,
        logger: Logger,
    ):
        self._repo = repo
        self._notifications = notifications
        self._logger = logger

    async def create_user(self, user: User) -> None:
        await self._repo.save(user)
        await self._notifications.send(user.id, "Welcome!")
        self._logger.info(f"Created user {user.id}")
```

### Async Function Injection

```python
async def process_order_async(
    order: Order,
    repo: AsyncOrderRepository,
    notifications: AsyncNotificationService,
) -> None:
    await repo.save(order)
    await notifications.send(order.customer_id, f"Order {order.id} confirmed")
```

### Testing Async Dependencies

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_user_async():
    mock_repo = AsyncMock(spec=AsyncUserRepository)
    mock_notifications = AsyncMock(spec=AsyncNotificationService)
    mock_logger = Mock(spec=Logger)

    service = AsyncUserService(mock_repo, mock_notifications, mock_logger)
    user = User(id=1, name="Alice", email="alice@example.com")

    await service.create_user(user)

    mock_repo.save.assert_awaited_once_with(user)
    mock_notifications.send.assert_awaited_once_with(1, "Welcome!")
```

## Lifecycle Management

Manage resource lifecycle (connections, sessions) without containers:

### Context Managers

```python
from contextlib import contextmanager
from typing import Generator

class DatabaseConnection:
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def execute(self, query: str) -> None: ...

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

# Usage
def process_users(users: list[User], db: DatabaseConnection) -> None:
    with database_session(db) as session:
        for user in users:
            session.execute(f"INSERT INTO users ...")
```

### Async Context Managers

```python
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

# Usage
async def process_users_async(users: list[User], db: AsyncDatabaseConnection) -> None:
    async with async_database_session(db) as session:
        for user in users:
            await session.execute(f"INSERT INTO users ...")
```

### Class-Based Context Manager

```python
class ManagedUserRepository:
    def __init__(self, db: DatabaseConnection):
        self._db = db

    def __enter__(self) -> "ManagedUserRepository":
        self._db.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._db.disconnect()

    def save(self, user: User) -> None:
        self._db.execute(f"INSERT INTO users ...")

# Usage with DI
def create_user_with_managed_repo(
    user: User,
    repo_factory: Callable[[], ManagedUserRepository],
) -> None:
    with repo_factory() as repo:
        repo.save(user)
```

## Configuration as a Dependency

Inject configuration objects instead of primitives:

### ❌ Bad: Injecting Primitives

```python
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
        # Too many primitives = unclear interface
        pass
```

### ✅ Good: Injecting Configuration Object

```python
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

    def send(self, to: str, subject: str, body: str) -> None:
        # Use self._config.smtp_host, etc.
        pass
```

**Benefits:**
- Single parameter instead of many
- Config changes don't break constructor signature
- Config object can have validation
- Easier to test (inject different configs)

### Integrating with Pydantic Settings

```python
from pydantic import BaseSettings

class EmailConfig(BaseSettings):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    timeout: float = 30.0
    max_retries: int = 3

    class Config:
        env_prefix = "EMAIL_"

# Auto-loads from EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, etc.
config = EmailConfig()
email_service = EmailService(config)
```

**See:** [python-pydantic-guide.md](python-pydantic-guide.md) for Pydantic configuration patterns

## Dependency Bundles with Dataclass

Group related dependencies to reduce constructor parameters:

### ❌ Problem: Too Many Parameters

```python
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
        # 6+ dependencies = code smell
        pass
```

### ✅ Solution: Dependency Bundle

```python
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
        self._deps.notifications.send_confirmation(order.customer_id)
```

**When to use:**
- 5+ dependencies in constructor
- Dependencies are logically grouped
- Same dependencies used across multiple services

**When to avoid:**
- Few dependencies (2-4)
- Dependencies are unrelated
- Creates god object

## Good vs Bad Patterns

### ✅ Good: Constructor Injection

```python
class OrderProcessor:
    def __init__(
        self,
        payment_gateway: PaymentGateway,
        inventory: InventoryService,
        notifications: NotificationService,
    ):
        self._payment_gateway = payment_gateway
        self._inventory = inventory
        self._notifications = notifications

    def process_order(self, order: Order) -> None:
        self._payment_gateway.charge(order.total)
        self._inventory.reserve(order.items)
        self._notifications.send_confirmation(order.customer_id)
```

**Why it's good:**
- All dependencies are explicit
- Immutable after construction
- Easy to test (inject mocks)
- No hidden coupling

**Note:** For API boundary validation of injected data, see [python-pydantic-guide.md](python-pydantic-guide.md)

### ❌ Bad: Tight Coupling

```python
class OrderProcessor:
    def __init__(self):
        # Creating dependencies internally = tight coupling
        self._payment_gateway = StripePaymentGateway()
        self._inventory = SqlInventoryService()
        self._notifications = EmailNotificationService()
```

**Why it's bad:**
- Hard to test (can't inject mocks)
- Hard to swap implementations
- Hidden dependencies
- Violates Single Responsibility Principle

### ❌ Bad: Service Locator Anti-Pattern

```python
class OrderProcessor:
    def __init__(self, container: Container):
        # Pulling dependencies from container = hidden coupling
        self._payment_gateway = container.get(PaymentGateway)
        self._inventory = container.get(InventoryService)
```

**Why it's bad:**
- Dependencies are hidden (not in function signature)
- Harder to test
- Implicit coupling to container
- Runtime errors if dependency missing

### ❌ Bad: Setter Injection

```python
class OrderProcessor:
    def set_payment_gateway(self, gateway: PaymentGateway) -> None:
        self._payment_gateway = gateway

    def process_order(self, order: Order) -> None:
        # What if payment_gateway was never set?
        self._payment_gateway.charge(order.total)
```

**Why it's bad:**
- Dependencies may be missing at runtime
- Mutable state
- Less explicit than constructor injection

**Exception**: Setter injection is acceptable for truly optional dependencies with sensible defaults:

```python
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
```

### ❌ Bad: Injecting Concrete Implementations

```python
# ❌ DON'T: Accept concrete class
class OrderProcessor:
    def __init__(self, repo: SqlOrderRepository):
        self._repo = repo

# ✅ DO: Accept interface (Protocol)
class OrderProcessor:
    def __init__(self, repo: OrderRepository):  # Protocol, not concrete
        self._repo = repo
```

**Why it's bad:**
- Violates Dependency Inversion Principle
- Coupled to specific implementation
- Harder to test (must use real SqlOrderRepository or subclass)

### ❌ Bad: Default Argument Instantiation

```python
# ❌ DON'T: Default creates new instance
class UserService:
    def __init__(self, repo: UserRepository = SqlUserRepository()):
        self._repo = repo

# Same instance shared across all UserService instances!
# Default arguments are evaluated once at function definition time
```

**Why it's bad:**
- Default argument evaluated once at import time
- All instances share the same repository object
- Subtle, hard-to-debug bugs
- State leaks between tests

**Fix:**

```python
# ✅ DO: Use None and create inside
class UserService:
    def __init__(self, repo: UserRepository | None = None):
        self._repo = repo or SqlUserRepository()

# ✅ BETTER: Factory function
def create_user_service(repo: UserRepository | None = None) -> UserService:
    return UserService(repo or SqlUserRepository())
```

### ❌ Bad: Global Singleton

```python
# ❌ DON'T: Module-level singleton
_repo = SqlUserRepository(create_database())

class UserService:
    def __init__(self):
        self._repo = _repo  # Uses global

# Hard to test, hidden dependency, shared mutable state
```

**Why it's bad:**
- Hidden dependency on global state
- Can't inject different implementations
- State shared across tests
- Import order matters

**Fix:**

```python
# ✅ DO: Inject dependency
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

# Factory creates the singleton if needed
def create_user_service() -> UserService:
    repo = SqlUserRepository(create_database())
    return UserService(repo)
```

## Dependency Injection Types

### 1. Constructor Injection (Preferred)

```python
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo
```

**Pros:**
- Explicit dependencies
- Immutable after creation
- Best for testing
- Clear what object needs to function

### 2. Method Injection

```python
class UserService:
    def create_user(self, user: User, repo: UserRepository) -> None:
        repo.save(user)
```

**Use case:**
- Short-lived dependencies
- Different implementations per method call
- Dependency varies per operation

**Cons:**
- Method signatures become cluttered
- Harder to enforce consistency

### 3. Property/Setter Injection (Avoid)

```python
class UserService:
    @property
    def repo(self) -> UserRepository:
        return self._repo

    @repo.setter
    def repo(self, value: UserRepository) -> None:
        self._repo = value
```

**Use case:**
- Optional dependencies only
- Framework requirements (rare)

**Cons:**
- Dependencies may be missing
- Mutable state
- Less explicit

## Testing with Dependency Injection

### Unit Testing with Mocks

```python
import pytest
from unittest.mock import Mock

def test_create_user_saves_to_repository():
    # Arrange: Create mocks
    mock_repo = Mock(spec=UserRepository)
    mock_logger = Mock(spec=Logger)
    mock_validator = Mock(spec=UserValidator)

    service = UserService(
        repo=mock_repo,
        logger=mock_logger,
        validator=mock_validator,
    )

    user = User(id=1, name="Alice", email="alice@example.com")

    # Act
    service.create_user(user)

    # Assert
    mock_validator.validate.assert_called_once_with(user)
    mock_repo.save.assert_called_once_with(user)
    mock_logger.info.assert_called_once()
```

**Note on Mock with Protocol:** `Mock(spec=UserRepository)` works because Protocol defines the expected interface. The mock will only allow calls to methods defined in the Protocol.

### Integration Testing with Fakes

```python
class InMemoryUserRepository:
    def __init__(self):
        self._users: dict[int, User] = {}

    def save(self, user: User) -> None:
        self._users[user.id] = user

    def find_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)

def test_create_user_integration():
    # Use in-memory fake instead of real database
    fake_repo = InMemoryUserRepository()
    real_logger = ConsoleLogger()
    real_validator = UserValidator()

    service = UserService(
        repo=fake_repo,
        logger=real_logger,
        validator=real_validator,
    )

    user = User(id=1, name="Alice", email="alice@example.com")
    service.create_user(user)

    # Verify user was saved
    saved_user = fake_repo.find_by_id(1)
    assert saved_user.name == "Alice"
```

## IoC Containers (Optional)

For large applications, an IoC container can manage dependency wiring.

### Simple Manual Wiring (Recommended for Most Cases)

```python
# factory.py
def create_user_service() -> UserService:
    db = create_database()
    repo = SqlUserRepository(db)
    logger = ConsoleLogger()
    validator = UserValidator()
    return UserService(repo, logger, validator)
```

### Using dependency-injector Library

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

**When to use containers:**
- Many dependencies (>10 services)
- Complex dependency graphs
- Need lifecycle management (singleton, transient, scoped)

**When to avoid:**
- Simple applications (manual wiring is clearer)
- Small dependency trees

## Decision Framework

### Constructor Injection vs Method Injection vs Function Injection

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

## Common Mistakes

### ❌ Over-Injection

```python
class UserService:
    def __init__(
        self,
        repo: UserRepository,
        logger: Logger,
        validator: UserValidator,
        email_service: EmailService,
        sms_service: SmsService,
        analytics: AnalyticsService,
        # ... 10 more dependencies
    ):
        pass
```

**Problem**: Too many dependencies = Single Responsibility Principle violation

**Fix**: Split into smaller services or use dependency bundles

### ❌ God Object Dependencies

```python
class UserService:
    def __init__(self, app_context: ApplicationContext):
        # ApplicationContext has 50+ services
        pass
```

**Problem**: Hidden dependencies, unclear requirements

**Fix**: Inject only what you need explicitly

### ❌ Circular Dependencies

```python
class UserService:
    def __init__(self, order_service: OrderService):
        self._order_service = order_service

class OrderService:
    def __init__(self, user_service: UserService):
        self._user_service = user_service
```

**Problem**: Can't construct either service

**Fix**: Introduce third service, event-based communication, or lazy injection

### ❌ Framework-Coupled Constructors

```python
# ❌ DON'T: Inject framework objects into services
class UserService:
    def __init__(self, request: Request, session: Session):
        self._request = request
        self._session = session

# ✅ DO: Extract what you need, inject as parameters
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

def create_user_endpoint(request: Request, session: Session):
    service = UserService(SqlUserRepository(session))
    user_data = request.json()
    # ...
```

**Why it's bad:**
- Service coupled to web framework
- Can't reuse service outside request context
- Harder to test

## Related Concepts

- **SOLID Principles** (especially Dependency Inversion Principle)
- **Clean Architecture** (dependency rule)
- **Hexagonal Architecture** (ports & adapters)
- **Protocol/ABC** (Python's interface mechanisms)
- **Pydantic** - For validating dependencies at system boundaries, see [python-pydantic-guide.md](python-pydantic-guide.md)
- **CLI Configuration** - For injecting config from CLI/env, see [python-cli-arguments-guide.md](python-cli-arguments-guide.md)

## Mental Model

> **IoC:** "I don't control object creation"
> **DI:** "You give me what I need"

Dependencies flow **inward** from framework/infrastructure to business logic.

## Summary

- **Prefer constructor injection** for class-based services
- **Use function injection** for scripts, pipelines, stateless operations
- **Use Protocol** for interface definitions (not ABC, unless shared behavior needed)
- **Use type hints** for all dependencies
- **Handle async properly** with async protocols and AsyncMock
- **Manage lifecycle** with context managers, not global singletons
- **Inject config objects** instead of many primitives
- **Use dependency bundles** when constructor has 5+ parameters
- **Avoid** service locator, setter injection, default argument instantiation
- **Avoid** global singletons and framework-coupled constructors
- **Test with mocks** or fakes injected via constructor/function
- **Manual wiring** for simple apps, containers for complex ones
