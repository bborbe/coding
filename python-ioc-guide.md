# Python Dependency Injection Patterns

This guide defines dependency injection (DI) patterns for Python services to ensure testability, loose coupling, and maintainability.

## Overview

**Inversion of Control (IoC)** is a design principle where control of object creation is transferred from application code to external components.

**Dependency Injection (DI)** is the primary technique for implementing IoC by providing dependencies from outside instead of creating them internally.

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

## Core Pattern: Constructor Injection

Constructor injection is the **preferred** DI pattern in Python.

### Interface → Constructor → Implementation

```python
from abc import ABC, abstractmethod
from typing import Protocol

# 1. Define interface (Protocol for structural typing)
class UserRepository(Protocol):
    def save(self, user: User) -> None:
        ...

    def find_by_id(self, user_id: int) -> User | None:
        ...

# 2. Constructor with dependency injection
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
        # Use injected dependencies
        self._validator.validate(user)
        self._repo.save(user)
        self._logger.info(f"Created user {user.id}")

# 3. Concrete implementation (private/internal)
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
        self._notifications.send_confirmation(order.customer)
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

**Exception**: Setter injection is acceptable for optional dependencies only.

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

    user = User(id=1, name="Alice")

    # Act
    service.create_user(user)

    # Assert
    mock_validator.validate.assert_called_once_with(user)
    mock_repo.save.assert_called_once_with(user)
    mock_logger.info.assert_called_once()
```

### Integration Testing with Fakes

```python
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

    user = User(id=1, name="Alice")
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

### Constructor Injection vs Method Injection

Use **constructor injection** when:
- Dependency is required for all methods
- Dependency is consistent across operations
- Object cannot function without dependency

Use **method injection** when:
- Dependency varies per operation
- Dependency is short-lived
- Only specific methods need the dependency

### DI Container vs Manual Wiring

Use **manual wiring** when:
- <10 services
- Simple dependency graph
- Clarity over automation

Use **DI container** when:
- >10 services
- Complex dependency trees
- Need lifecycle management

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

**Fix**: Split into smaller services or create facade/aggregate dependencies

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

**Fix**: Introduce third service or event-based communication

## Related Concepts

- **SOLID Principles** (especially Dependency Inversion Principle)
- **Clean Architecture** (dependency rule)
- **Hexagonal Architecture** (ports & adapters)
- **Protocol/ABC** (Python's interface mechanisms)
- **Pydantic** - For validating dependencies at system boundaries, see [python-pydantic-guide.md](python-pydantic-guide.md)

## Mental Model

> **IoC:** "I don't control object creation"
> **DI:** "You give me what I need"

Dependencies flow **inward** from framework/infrastructure to business logic.

## Summary

- **Prefer constructor injection** for all required dependencies
- **Use type hints** (Protocol, ABC) for interfaces
- **Avoid service locator** and setter injection
- **Keep dependencies explicit** in constructor signatures
- **Test with mocks** or fakes injected via constructor
- **Manual wiring** for simple apps, containers for complex ones
