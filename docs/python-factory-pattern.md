# Python Factory Pattern Guide

Factory functions compose objects by wiring dependencies together. They contain **zero business logic** - only constructor calls.

## 1. Core Principles

**Factories should only:**
- Pass dependencies to constructors
- Build nested object trees
- Return typed objects (Protocol implementations)

**Factories must NOT:**
- Contain loops, conditionals, or business logic
- Have inline function implementations with logic
- Mix object creation with execution

## 2. When to Extract Factory Pattern

**Signals to extract factory function or module:**

### Module-Level Global State

```python
# [BAD] - Global state scattered in application code
# server.py
_client: AlertmanagerClient | None = None

def handle_request():
    global _client
    if _client is None:
        _client = AlertmanagerClient(get_config())
    return _client.get_alerts()

# [GOOD] - Extracted to factory.py
# factory.py
_client: AlertmanagerClient | None = None

def get_client() -> AlertmanagerClient:
    """Get or create the Alertmanager client singleton."""
    global _client
    if _client is None:
        logger.debug("Initializing Alertmanager client")
        _client = AlertmanagerClient(get_config())
    return _client

# server.py
from .factory import get_client

def handle_request():
    return get_client().get_alerts()
```

### Repeated Initialization Checks

```python
# [BAD] - Repeated initialization logic
# Multiple modules checking if initialized
if not database:
    database = Database(config)

if not api_client:
    api_client = ApiClient(config)

# [GOOD] - Centralized in factory
def get_database() -> Database:
    global _database
    if _database is None:
        _database = Database(get_config())
    return _database
```

### Complex Dependency Wiring

```python
# [BAD] - Complex wiring in main.py (>10 lines of composition)
# main.py
def main():
    # ... 20+ lines of dependency wiring ...

# [GOOD] - Extract to factory functions
# factory.py
def create_user_service(database: Database) -> UserService:
    return UserService(
        repo=SqlUserRepository(database),
        logger=ConsoleLogger(),
        validator=UserValidator(),
    )

# main.py
def main():
    service = create_user_service(database)
```

### When NOT to Extract

**Don't extract for:**
- Simple 1-2 line object creation
- Objects with no dependencies
- Code that only creates object once in main.py

```python
# [GOOD] - No factory needed for simple cases
# main.py
def main():
    logger = ConsoleLogger()  # Simple, no extraction needed
    config = Config.from_env()
```

**Reference:** alertmanager-mcp migrated global `_client` state from server.py to factory.py, demonstrating when extraction improves code organization.

## 3. File Organization

**Services/Applications:**
```
pkg/factory.py    # All factory functions in ONE file
```

**Or inline in main.py** for simpler applications.

**Naming:**
- Factories: `create_*` prefix (e.g., `create_user_service`)
- Constructors: Class `__init__` (e.g., `UserService(...)`)

## 4. Good Factory Examples

### Simple Composition

```python
def create_user_service(database: Database) -> UserService:
    return UserService(
        repo=SqlUserRepository(database),
        logger=ConsoleLogger(),
        validator=UserValidator(),
    )
```

### Nested Composition (Middleware/Decorators)

```python
def create_message_handler(database: Database, producer: Producer) -> MessageHandler:
    return RetryMessageHandler(
        MetricsMessageHandler(
            LoggingMessageHandler(
                UserMessageHandler(
                    repo=SqlUserRepository(database),
                    sender=KafkaSender(producer),
                ),
                logger=ConsoleLogger(),
            ),
            metrics=PrometheusMetrics(),
        ),
        max_retries=3,
    )
```

### Fetcher/Sender Composition

```python
def create_order_fetcher(api_client: ApiClient, queue: QueueClient, branch: str) -> OrderFetcher:
    return OrderFetcher(
        api_client=api_client,
        sender=OrderSender(
            queue_client=queue,
            topic=f"{branch}-orders",
        ),
    )
```

### List Composition

```python
def create_validators() -> list[Validator]:
    return [
        EmailValidator(),
        PhoneValidator(),
        AddressValidator(CountryLookup()),
    ]
```

### Handler Composition

```python
def create_command_handler(
    database: Database,
    producer: Producer,
    branch: str,
) -> CommandHandler:
    return CommandHandler(
        user_fetcher=create_user_fetcher(database, producer, branch),
        order_fetcher=create_order_fetcher(database, producer, branch),
        account_fetcher=create_account_fetcher(database, producer, branch),
    )
```

## 5. Bad Factory Patterns

### DON'T: Inline Business Logic

```python
# BAD: Loop, error handling, conditionals in factory
def create_batch_handler(database: Database, index: Index) -> MessageHandler:
    def handle_batch(messages: list[Message]) -> None:
        batch = index.new_batch()

        for message in messages:  # Loop = business logic!
            try:
                user = parse_user(message)
                batch.add(user)
            except Exception as e:
                logging.error(f"Failed: {e}")  # Error handling!

        if batch.size() > 0:  # Conditional!
            index.commit(batch)

    return MessageHandler(handle_batch)
```

**Why bad:**
- For loop iterating messages
- Try/except error handling
- Conditional logic
- Inline function with behavior

### DO: Move Implementation to Separate Class

```python
# In factory.py:
def create_batch_handler(database: Database, index: Index) -> MessageHandler:
    return BatchIndexHandler(index, SqlUserRepository(database))


# In batch_index_handler.py:
class BatchIndexHandler:
    def __init__(self, index: Index, repo: UserRepository):
        self._index = index
        self._repo = repo

    def handle(self, messages: list[Message]) -> None:
        batch = self._index.new_batch()

        for message in messages:
            try:
                user = self._repo.parse(message)
                batch.add(user)
            except Exception as e:
                logging.error(f"Failed: {e}")

        if batch.size() > 0:
            self._index.commit(batch)
```

### DON'T: Execute Logic in Factory

```python
# BAD
def create_service(database: Database) -> UserService:
    service = UserService(database)
    service.initialize()  # Execution!
    service.warm_cache()  # More execution!
    return service
```

### DON'T: Create Singletons

```python
# BAD
_instance: UserService | None = None

def create_user_service(database: Database) -> UserService:
    global _instance
    if _instance is None:  # Conditional!
        _instance = UserService(database)
    return _instance
```

### DON'T: Conditionals Based on Config

```python
# BAD
def create_repository(config: Config) -> UserRepository:
    if config.use_cache:  # Conditional!
        return CachedUserRepository(SqlUserRepository())
    else:
        return SqlUserRepository()
```

### DO: Separate Factory Functions

```python
# GOOD
def create_repository(database: Database) -> UserRepository:
    return SqlUserRepository(database)

def create_cached_repository(database: Database, cache: Cache) -> UserRepository:
    return CachedUserRepository(
        repo=SqlUserRepository(database),
        cache=cache,
    )
```

## 6. Usage in main.py

Factories wire the application together:

```python
def main():
    # 1. Infrastructure
    database = Database(os.getenv('DATABASE_URL'))
    producer = KafkaProducer(os.getenv('KAFKA_BROKERS'))
    branch = os.getenv('BRANCH')

    # 2. Use factories to build services
    user_service = create_user_service(database)
    command_handler = create_command_handler(database, producer, branch)

    # 3. Build server
    server = HttpServer(
        port=int(os.getenv('PORT', '8080')),
        handler=create_http_handler(user_service),
    )

    # 4. Run
    server.run()
```

## 7. Factory vs Inline Wiring

**Use factory functions when:**
- Same composition used in multiple places
- Complex nested composition (3+ levels)
- Testing needs different wiring
- Composition is getting long in main.py

**Use inline wiring when:**
- Simple 1-2 level composition
- Used only once
- Easy to read inline

```python
# Inline is fine for simple cases
def main():
    user_service = UserService(
        repo=SqlUserRepository(database),
        logger=ConsoleLogger(),
    )
```

## 8. Common Antipatterns

### DON'T: Split Factories Across Files

```python
# BAD
pkg/user_factory.py
pkg/order_factory.py
pkg/handler_factory.py

# GOOD
pkg/factory.py  # All factories in one file
```

### DON'T: Factory With Side Effects

```python
# BAD
def create_service(database: Database) -> UserService:
    logging.info("Creating service...")  # Side effect!
    return UserService(database)
```

### DON'T: Async Factory (Usually)

```python
# BAD - usually unnecessary
async def create_service(database: Database) -> UserService:
    await database.ping()  # Execution in factory!
    return UserService(database)

# GOOD - async in the service, not factory
def create_service(database: Database) -> UserService:
    return UserService(database)  # Service handles async internally
```

## Summary

**Factory Checklist:**
- [ ] All factories in single file: `pkg/factory.py` or inline in `main.py`
- [ ] Use `create_*` prefix
- [ ] Only constructor calls - zero business logic
- [ ] No loops, conditionals, or error handling
- [ ] Move complex logic to separate implementation classes
- [ ] Return typed objects (Protocol implementations preferred)

## Related Documentation

- [python-architecture-patterns.md](python-architecture-patterns.md) - Service architecture overview
- [python-ioc-guide.md](python-ioc-guide.md) - Dependency injection patterns
- [go-factory-pattern.md](go-factory-pattern.md) - Equivalent patterns in Go
