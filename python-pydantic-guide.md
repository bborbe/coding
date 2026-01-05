# Python Pydantic Data Validation Patterns

This guide defines patterns for using Pydantic to validate and parse external data in Python services.

## Overview

**Pydantic** is a Python library for **data parsing, validation, and settings management** based on type hints.

It validates data at **runtime** and provides clear error messages for invalid input.

## When to Use Pydantic

### ✅ Use Pydantic When:

- **Validating untrusted or external input**
  - API request/response bodies
  - Configuration files (JSON, YAML, TOML)
  - Environment variables
  - User input from forms or CLI
  - External API responses

- **Creating boundaries** between systems
  - Input validation layer for services
  - Data contracts between microservices
  - ETL/data pipeline input validation

- **Need runtime safety** beyond static typing
  - Type coercion with validation
  - Complex validation rules
  - Clear error messages for users

- **Generating schemas** automatically
  - OpenAPI/JSON Schema generation
  - API documentation (FastAPI integration)

### ❌ Skip Pydantic When:

- **Internal data structures** already validated
- **Performance-critical paths** where validation overhead matters
- **Simple data** where dataclasses or TypedDict suffice
- **Static typing** + mypy provides enough guarantees

## Core Pattern: BaseModel Definition

### Basic Validation

```python
from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    age: int = Field(ge=0, le=150)  # 0 <= age <= 150
    is_active: bool = True  # Default value

# Usage: Automatic validation on creation
user = User(
    id=1,
    name="Alice",
    email="alice@example.com",
    age=30,
)

# Type coercion
user = User(id="123", name="Bob", email="bob@example.com", age="25")
# Converts "123" → int, "25" → int automatically
```

**Key Points:**
- Use type hints for all fields
- Pydantic validates + coerces on instantiation
- Use `Field()` for constraints (min/max, regex, etc.)
- Provide defaults for optional fields

### Validation Errors

```python
from pydantic import ValidationError

try:
    user = User(
        id="not_a_number",
        name=123,  # Should be string
        email="invalid-email",
        age=-5,
    )
except ValidationError as e:
    print(e.json())
    # Returns structured error with:
    # - Field locations
    # - Error types
    # - Human-readable messages
```

## Good vs Bad Patterns

### ✅ Good: API Request Validation

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

app = FastAPI()

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=18, le=150)

    @validator("name")
    def name_must_not_be_blank(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()

@app.post("/users")
def create_user(request: CreateUserRequest):
    # Request is already validated by Pydantic
    # No need for manual checks
    user_service.create(request)
    return {"id": 1, "name": request.name}
```

**Why it's good:**
- Validates at system boundary (API endpoint)
- Clear error messages for API consumers
- Automatic OpenAPI schema generation
- Type-safe within application after validation

### ✅ Good: Configuration Loading

```python
from pydantic import BaseSettings, Field

class AppConfig(BaseSettings):
    database_url: str = Field(..., env="DATABASE_URL")
    api_key: str = Field(..., env="API_KEY")
    debug: bool = Field(default=False, env="DEBUG")
    max_connections: int = Field(default=10, ge=1, le=100)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Automatically loads from environment variables or .env file
config = AppConfig()
```

**Why it's good:**
- Validates configuration at startup
- Fails fast if config is invalid
- Clear errors for misconfiguration
- Type-safe config throughout app

### ❌ Bad: Over-Validation of Internal Data

```python
# DON'T: Validate data already validated at boundary
class UserService:
    def create_user(self, user: User) -> None:
        # User already validated at API boundary
        # No need to re-validate here
        validated_user = User(**user.dict())  # ❌ Redundant
        self._repo.save(validated_user)
```

**Why it's bad:**
- Performance overhead (unnecessary validation)
- Already validated at system boundary
- Trust internal data types

**Fix:** Use plain dataclasses or simple types internally

```python
from dataclasses import dataclass

@dataclass
class UserEntity:
    id: int
    name: str
    email: str

class UserService:
    def create_user(self, user: UserEntity) -> None:
        # No validation needed - already validated at API boundary
        self._repo.save(user)
```

### ❌ Bad: Pydantic in Performance-Critical Paths

```python
# DON'T: Use Pydantic for high-frequency internal operations
class EventProcessor:
    def process_events(self, events: list[dict]) -> None:
        for event in events:
            # Validating 10,000 events/second = performance hit
            validated_event = Event(**event)  # ❌ Expensive
            self._handle(validated_event)
```

**Why it's bad:**
- Validation overhead on every iteration
- Events already validated on ingestion
- Slows down processing pipeline

**Fix:** Validate once at ingestion, use plain types in processing

```python
class EventIngestion:
    def ingest(self, raw_events: list[dict]) -> list[Event]:
        # Validate ONCE at boundary
        return [Event(**e) for e in raw_events]

class EventProcessor:
    def process_events(self, events: list[Event]) -> None:
        # Already validated - use directly
        for event in events:
            self._handle(event)
```

## Validation Features

### Field Constraints

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=10000)  # 0 < price <= 10000
    sku: str = Field(regex=r"^[A-Z]{3}-\d{4}$")  # Pattern: ABC-1234
    quantity: int = Field(ge=0, multiple_of=1)
```

### Custom Validators

```python
from pydantic import BaseModel, validator

class Order(BaseModel):
    items: list[str]
    total: float

    @validator("items")
    def items_must_not_be_empty(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v

    @validator("total")
    def total_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Total must be positive")
        return v
```

### Root Validators

```python
from pydantic import BaseModel, root_validator

class DateRange(BaseModel):
    start_date: date
    end_date: date

    @root_validator
    def check_dates(cls, values):
        start = values.get("start_date")
        end = values.get("end_date")
        if start and end and start > end:
            raise ValueError("start_date must be before end_date")
        return values
```

### Strict Mode

```python
from pydantic import BaseModel, StrictInt, StrictStr

class StrictUser(BaseModel):
    id: StrictInt  # No type coercion - only accepts int
    name: StrictStr  # No type coercion - only accepts str

# Raises ValidationError - no coercion
user = StrictUser(id="123", name="Alice")
```

### Nested Models

```python
class Address(BaseModel):
    street: str
    city: str
    country: str

class User(BaseModel):
    name: str
    email: EmailStr
    address: Address  # Nested validation

user = User(
    name="Alice",
    email="alice@example.com",
    address={
        "street": "123 Main St",
        "city": "NYC",
        "country": "USA",
    },
)
```

## Decision Framework

### Pydantic vs Plain Dataclasses

**Use Pydantic:**
- Validating external input
- Need runtime validation
- Complex validation rules
- Auto schema generation

**Use dataclasses:**
- Internal data structures
- Already validated data
- Simple data containers
- Performance-critical paths

### Pydantic vs TypedDict

**Use Pydantic:**
- Runtime validation needed
- Clear error messages required
- Type coercion helpful

**Use TypedDict:**
- Static type checking sufficient
- No runtime validation needed
- Working with plain dicts (e.g., JSON)

## Common Patterns

### API Request/Response Models

```python
from pydantic import BaseModel

# Request
class CreateOrderRequest(BaseModel):
    items: list[str]
    customer_id: int

# Response
class OrderResponse(BaseModel):
    id: int
    items: list[str]
    total: float
    status: str

    class Config:
        # Allow creation from ORM models
        orm_mode = True
```

### Settings Management

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "MyApp"
    admin_email: EmailStr
    database_url: str
    items_per_page: int = 50

    class Config:
        env_file = ".env"

settings = Settings()
```

### Data Transformation

```python
class InputData(BaseModel):
    raw_value: str

    @validator("raw_value", pre=True)
    def clean_value(cls, v):
        # Transform before validation
        return v.strip().lower()

class OutputData(BaseModel):
    processed_value: str

    class Config:
        @staticmethod
        def schema_extra(schema, model):
            # Customize generated schema
            schema["example"] = {"processed_value": "example"}
```

## Integration with FastAPI

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.post("/items", response_model=Item)
def create_item(item: Item):
    # FastAPI automatically:
    # 1. Validates request body against Item
    # 2. Returns 422 error if validation fails
    # 3. Generates OpenAPI schema
    # 4. Validates response against response_model
    return item
```

## Common Mistakes

### ❌ Using Pydantic Everywhere

```python
# DON'T: Use Pydantic for internal domain models
class UserService:
    def __init__(self, repo: UserRepository):
        self._repo = repo

    def get_user(self, user_id: int) -> User:  # ❌ Pydantic model
        return self._repo.find_by_id(user_id)
```

**Fix:** Use domain models internally, Pydantic at boundaries

```python
@dataclass
class UserEntity:  # Domain model
    id: int
    name: str

class UserDTO(BaseModel):  # API boundary
    id: int
    name: str

class UserService:
    def get_user(self, user_id: int) -> UserEntity:
        return self._repo.find_by_id(user_id)

@app.get("/users/{user_id}", response_model=UserDTO)
def get_user_api(user_id: int):
    entity = user_service.get_user(user_id)
    return UserDTO(**entity.__dict__)  # Convert at boundary
```

**Note:** For dependency injection patterns with these services, see [python-ioc-guide.md](python-ioc-guide.md)

### ❌ Ignoring Validation Errors

```python
# DON'T: Catch and ignore validation errors
try:
    user = User(**data)
except ValidationError:
    user = None  # ❌ Silent failure
```

**Fix:** Handle errors explicitly

```python
from pydantic import ValidationError

try:
    user = User(**data)
except ValidationError as e:
    logger.error(f"Validation failed: {e.json()}")
    raise HTTPException(status_code=400, detail=e.errors())
```

### ❌ Over-Constraining Internal Models

```python
# DON'T: Add business logic constraints to data models
class User(BaseModel):
    age: int = Field(ge=18)  # ❌ Business rule in data model

    @validator("email")
    def email_must_be_company_domain(cls, v):
        # ❌ Business logic in validator
        if not v.endswith("@company.com"):
            raise ValueError("Must use company email")
        return v
```

**Fix:** Separate data validation from business logic

```python
# Data validation only
class UserInput(BaseModel):
    age: int = Field(ge=0, le=150)  # Data constraint
    email: EmailStr  # Format validation only

# Business logic in service
class UserService:
    def create_user(self, input: UserInput) -> None:
        # Business logic validation
        if input.age < 18:
            raise BusinessRuleError("User must be 18+")
        if not input.email.endswith("@company.com"):
            raise BusinessRuleError("Must use company email")
        self._repo.save(input)
```

## Performance Considerations

### Validation Cost

```python
# Pydantic validation has overhead - use wisely
import timeit

# Fast: No validation
data = {"id": 1, "name": "Alice"}

# Slower: Pydantic validation
user = User(**data)

# Use Pydantic at boundaries, not in loops
for item in large_list:
    # ❌ Slow: Validate 10,000 times
    validated = Item(**item)

# ✅ Fast: Validate once at boundary
validated_items = [Item(**item) for item in large_list]
for item in validated_items:
    # Use validated data directly
    process(item)
```

## Related Concepts

- **Dependency Injection** - For injecting validated dependencies, see [python-ioc-guide.md](python-ioc-guide.md)
- **FastAPI** (automatic Pydantic integration)
- **SQLModel** (Pydantic + SQLAlchemy)
- **Dataclasses** (simpler alternative for internal data)
- **TypedDict** (static typing without runtime validation)
- **JSON Schema** (Pydantic can generate/consume schemas)

## Summary

- **Use Pydantic at system boundaries** (APIs, configs, external data)
- **Validate once** at data ingestion points
- **Use plain types internally** after validation
- **Leverage type hints** for schema generation
- **Provide clear error messages** for API consumers
- **Avoid over-validation** in performance-critical paths
- **Separate data validation from business logic**
