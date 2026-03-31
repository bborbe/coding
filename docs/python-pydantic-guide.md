# Python Pydantic Data Validation Patterns

Data validation library for Python enforcing type safety and constraints at system boundaries.

## Quick Reference

| Question | Answer |
|----------|--------|
| **When to use** | Validating external data at system boundaries (APIs, configs, external services) |
| **When to skip** | Internal data already validated, performance-critical paths |
| **Default choice** | Pydantic v2 `BaseModel` for DTOs, `BaseSettings` for config |
| **Key pattern** | Validate once at boundary → use plain types (`dataclass`) internally |
| **Boundary** | API endpoint, config loading, external service response, file ingestion |

## Version Reference

| Feature | Pydantic v1 | Pydantic v2 |
|---------|-------------|-------------|
| Validators | `@validator` | `@field_validator` |
| Model validators | `@root_validator` | `@model_validator` |
| Settings | `from pydantic import BaseSettings` | `from pydantic_settings import BaseSettings` |
| Serialization | `.dict()`, `.json()` | `.model_dump()`, `.model_dump_json()` |
| ORM mode | `Config.orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| Config class | `class Config:` | `model_config = ConfigDict(...)` |
| Regex | `Field(regex=...)` | `Field(pattern=...)` |

```bash
# v2 (recommended)
pip install pydantic pydantic-settings

# v1 (legacy)
pip install "pydantic<2"
```

## Boundary Validation Rules

### Pydantic Usage Scope

**Constraint:** Pydantic MUST ONLY be used at system boundaries for external data validation.

**Rationale:** Validation overhead is justified only when parsing untrusted input; internal data has already been validated.

**Examples:**

```python
# [GOOD] - Validate at API boundary
@app.post("/users")
def create_user(request: CreateUserRequest):  # Pydantic validates here
    user_service.create(request.to_entity())  # Internal uses plain types

# [BAD] - Pydantic deep in internal code
class UserService:
    def get_user(self, user_id: int) -> User:  # Pydantic model internally
        return self._repo.find_by_id(user_id)
```

### Single Validation Point

**Constraint:** Data MUST be validated exactly once at ingestion.

**Rationale:** Re-validation wastes CPU cycles and obscures the trust boundary.

**Examples:**

```python
# [GOOD] - Validate once at ingestion
class EventIngestion:
    def ingest(self, raw_events: list[dict]) -> list[Event]:
        return [Event(**e) for e in raw_events]  # Validate here

class EventProcessor:
    def process_events(self, events: list[Event]) -> None:
        for event in events:
            self._handle(event)  # Already validated

# [BAD] - Re-validate already validated data
class UserService:
    def create_user(self, user: User) -> None:
        validated_user = User(**user.dict())  # Redundant validation
        self._repo.save(validated_user)
```

### Internal Data Representation

**Constraint:** Internal domain models MUST use `dataclass` or plain types, not `BaseModel`.

**Rationale:** Avoids validation overhead on trusted data; separates concerns between DTOs and domain entities.

**Examples:**

```python
# [GOOD] - dataclass for internal domain model
from dataclasses import dataclass

@dataclass
class UserEntity:
    id: int
    name: str
    email: str

class UserDTO(BaseModel):  # Pydantic at boundary only
    id: int
    name: str

# [BAD] - Pydantic for internal domain model
class UserEntity(BaseModel):  # Unnecessary validation overhead
    id: int
    name: str
```

---

## Field Definition Rules

### Optional Field Declaration

**Constraint:** Omittable fields MUST have a default value; `Optional[T]` alone is NOT sufficient.

**Rationale:** `Optional[T]` means "T or None", not "field can be omitted". Without a default, the field is still required.

**Examples:**

```python
# [GOOD] - Truly optional with default
class User(BaseModel):
    name: Optional[str] = None  # Can be omitted

# [BAD] - Required despite Optional annotation
class User(BaseModel):
    name: Optional[str]  # Still REQUIRED - only allows None as value

User()  # ValidationError: field required
```

### Field Constraints

**Constraint:** Numeric and string constraints MUST use `Field()` parameters, not custom validators.

**Rationale:** Built-in constraints are optimized and generate accurate JSON Schema.

**Examples:**

```python
# [GOOD] - Use Field() constraints
class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=10000)
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")  # v2: pattern, v1: regex

# [BAD] - Custom validator for simple constraints
class Product(BaseModel):
    price: float

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v <= 0 or v > 10000:
            raise ValueError("...")
        return v
```

### Mutable Default Values

**Constraint:** Mutable defaults MUST use `Field(default_factory=...)`.

**Rationale:** Explicit factory prevents accidental shared state; clarity over implicit safety.

**Examples:**

```python
# [GOOD] - Explicit default factory
class User(BaseModel):
    tags: list[str] = Field(default_factory=list)

# [BAD] - Implicit mutable default (works but unclear)
class User(BaseModel):
    tags: list[str] = []
```

---

## Validator Rules

### Field Validator Signature (v2)

**Constraint:** In Pydantic v2, `@field_validator` MUST be decorated with `@classmethod` and include type hints.

**Rationale:** v2 requires explicit classmethod decorator; type hints enable proper IDE support.

**Examples:**

```python
# [GOOD] - Pydantic v2 validator
@field_validator("name")
@classmethod
def validate_name(cls, v: str) -> str:
    if not v.strip():
        raise ValueError("Name cannot be blank")
    return v.strip()

# [BAD] - Missing classmethod (v2)
@field_validator("name")
def validate_name(cls, v):  # Will fail in v2
    return v.strip()
```

### Pre-Validation Transformation

**Constraint:** Data transformation before validation MUST use `mode="before"` (v2) or `pre=True` (v1).

**Rationale:** Ensures transformation happens before type coercion and validation.

**Examples:**

```python
# [GOOD] - v2 pre-validation
@field_validator("raw_value", mode="before")
@classmethod
def clean_value(cls, v: str) -> str:
    return v.strip().lower()

# [GOOD] - v1 pre-validation
@validator("raw_value", pre=True)
def clean_value(cls, v):
    return v.strip().lower()
```

### Cross-Field Validation

**Constraint:** Validation involving multiple fields MUST use `@model_validator` (v2) or `@root_validator` (v1).

**Rationale:** Field validators only see one field; model validators access all fields.

**Examples:**

```python
# [GOOD] - v2 model validator
@model_validator(mode="after")
def check_dates(self) -> "DateRange":
    if self.start_date > self.end_date:
        raise ValueError("start_date must be before end_date")
    return self

# [GOOD] - v1 root validator
@root_validator
def check_dates(cls, values):
    if values.get("start_date") > values.get("end_date"):
        raise ValueError("start_date must be before end_date")
    return values
```

### Business Logic Separation

**Constraint:** Business rules MUST NOT be implemented in Pydantic validators.

**Rationale:** Validators are for data format; business rules belong in service layer for testability and reuse.

**Examples:**

```python
# [GOOD] - Data validation only, business logic in service
class UserInput(BaseModel):
    age: int = Field(ge=0, le=150)  # Data constraint
    email: EmailStr  # Format validation

class UserService:
    def create_user(self, input: UserInput) -> None:
        if input.age < 18:  # Business rule
            raise BusinessRuleError("User must be 18+")
        if not input.email.endswith("@company.com"):  # Business rule
            raise BusinessRuleError("Must use company email")

# [BAD] - Business logic in validator
class User(BaseModel):
    age: int = Field(ge=18)  # Business rule masquerading as data validation

    @field_validator("email")
    @classmethod
    def email_must_be_company_domain(cls, v):
        if not v.endswith("@company.com"):  # Business logic
            raise ValueError("Must use company email")
        return v
```

---

## Immutability Rules

### Frozen Models for DTOs

**Constraint:** Read-only DTOs MUST use `frozen=True` configuration.

**Rationale:** Prevents accidental mutation after validation; ensures data integrity.

**Examples:**

```python
# [GOOD] - v2 frozen model
class ReadOnlyUser(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    name: str

# [GOOD] - v1 frozen model
class ReadOnlyUser(BaseModel):
    class Config:
        frozen = True

# [BAD] - Mutable model allows bypassing validation
user = User(id=1, name="Alice")
user.age = -5  # Invalid value - no error raised!
```

### Assignment Validation Performance

**Constraint:** `validate_assignment=True` MUST NOT be used in performance-critical code.

**Rationale:** Validates on every attribute assignment, causing O(n) validation for n assignments.

**Examples:**

```python
# [BAD] - Performance issue with validate_assignment
class User(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    name: str

for i in range(10000):
    user.name = f"User {i}"  # Validates 10,000 times!
```

---

## Serialization Rules

### Method Selection (v1 vs v2)

**Constraint:** v2 code MUST use `.model_dump()` and `.model_dump_json()`; v1 code MUST use `.dict()` and `.json()`.

**Rationale:** API changed between versions; using wrong methods causes `AttributeError`.

**Examples:**

```python
# [GOOD] - v2 serialization
user.model_dump()
user.model_dump_json()
user.model_dump(exclude_unset=True)

# [GOOD] - v1 serialization
user.dict()
user.json()
user.dict(exclude_unset=True)
```

### Extra Fields Handling

**Constraint:** API models receiving external input MUST use `extra="forbid"` to reject unknown fields.

**Rationale:** Prevents silent acceptance of typos or malicious extra fields.

**Examples:**

```python
# [GOOD] - Reject unknown fields
class CreateUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    email: str

# Request with typo "emial" will fail instead of being silently ignored

# [BAD] - Allow unknown fields (default)
class CreateUserRequest(BaseModel):
    name: str
    email: str

# {"name": "Alice", "emial": "typo@example.com"} silently ignores typo
```

## Error Handling Rules

### ValidationError Handling

**Constraint:** `ValidationError` MUST be caught and converted to structured API responses; silent failures are forbidden.

**Rationale:** Silent failures hide bugs; structured errors enable client-side handling.

**Examples:**

```python
# [GOOD] - Explicit error handling
try:
    user = User(**data)
except ValidationError as e:
    logger.error(f"Validation failed: {e.json()}")
    raise HTTPException(status_code=400, detail=e.errors())

# [BAD] - Silent failure
try:
    user = User(**data)
except ValidationError:
    user = None  # Bug hidden, None propagates
```

## Type Coercion Rules

### Strict Types for Critical Fields

**Constraint:** Fields where coercion could cause bugs MUST use `Strict*` types.

**Rationale:** Default coercion can produce unexpected results (e.g., `"1"` → `True` for bool).

**Examples:**

```python
# [GOOD] - Strict types prevent coercion surprises
from pydantic import StrictBool, StrictInt

class Config(BaseModel):
    enabled: StrictBool  # Only accepts True/False
    count: StrictInt  # Only accepts int, not "123"

# [BAD] - Unexpected coercion
class Config(BaseModel):
    enabled: bool

Config(enabled="yes")  # Becomes True
Config(enabled="1")    # Becomes True
Config(enabled=1)      # Becomes True
```

### Timezone-Aware Datetimes

**Constraint:** Datetime fields requiring timezone awareness MUST validate `tzinfo` is not `None`.

**Rationale:** Naive datetimes cause subtle bugs in distributed systems.

**Examples:**

```python
# [GOOD] - Enforce timezone awareness
class Event(BaseModel):
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def ensure_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("Datetime must be timezone-aware")
        return v

# [BAD] - Accept naive datetime
class Event(BaseModel):
    timestamp: datetime  # No validation, accepts naive datetime
```

## Configuration Rules

### BaseSettings Import (v2)

**Constraint:** In Pydantic v2, `BaseSettings` MUST be imported from `pydantic_settings`, not `pydantic`.

**Rationale:** Settings functionality was moved to separate package in v2.

**Examples:**

```python
# [GOOD] - v2 settings
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    database_url: str

# [GOOD] - v1 settings
from pydantic import BaseSettings

class AppConfig(BaseSettings):
    class Config:
        env_file = ".env"
```

## Performance Rules

### Loop Validation Prohibition

**Constraint:** Pydantic validation MUST NOT occur inside tight loops.

**Rationale:** Validation overhead multiplied by iteration count causes significant latency.

**Examples:**

```python
# [GOOD] - Validate once, iterate validated data
validated_items = [Item(**item) for item in large_list]  # Validate all
for item in validated_items:
    process(item)

# [BAD] - Validate inside loop
for item in large_list:
    validated = Item(**item)  # 10,000 validations!
    process(validated)
```

## Integration Patterns

### FastAPI Request Validation

**Examples:**

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator

app = FastAPI()

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=18, le=150)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()

@app.post("/users")
def create_user(request: CreateUserRequest):
    # FastAPI automatically validates request body
    return {"id": 1, "name": request.name}
```

### ORM Model Conversion

**Examples:**

```python
# [GOOD] - v2 ORM conversion
class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str

# [GOOD] - v1 ORM conversion
class OrderResponse(BaseModel):
    class Config:
        orm_mode = True
```

### Enum Serialization

**Examples:**

```python
from enum import Enum
from pydantic import BaseModel, ConfigDict

class Status(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"

class Order(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: Status

order.model_dump()  # {'status': 'active'} - string, not enum
```

## Related Guides

- [python-ioc-guide.md](python-ioc-guide.md) - Dependency injection patterns
- [python-cli-arguments-guide.md](python-cli-arguments-guide.md) - Configuration management with `BaseSettings`
- [python-logging-guide.md](python-logging-guide.md) - Logging validation errors
