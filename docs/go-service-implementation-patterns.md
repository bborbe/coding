# Go Service Implementation Patterns

This guide captures practical decision-making patterns and implementation choices for building Go services correctly from the beginning. These patterns emerged from real-world refactoring experiences and help avoid common pitfalls that require major restructuring later.

## Table of Contents

1. [Service Architecture Decision Framework](#service-architecture-decision-framework)
2. [Type Design Patterns](#type-design-patterns)
3. [Dependency Injection Best Practices](#dependency-injection-best-practices)
4. [Implementation Patterns](#implementation-patterns)
5. [Package Organization Principles](#package-organization-principles)
6. [Decision Checklists](#decision-checklists)

## Service Architecture Decision Framework

### Provider vs Registry Pattern

**Use Static Provider Pattern When:**
- Implementation set is fixed at compile time
- Performance matters (switch statements are faster than map lookups)
- Simple, predictable behavior is preferred
- Few implementations (< 10 types)

```go
// Static Provider - Good for fixed set of implementations
type UserProvider interface {
    Get(ctx context.Context, userType UserType) (UserService, error)
}

func (p *userProvider) Get(ctx context.Context, userType UserType) (UserService, error) {
    switch userType {
    case AdminUser:
        return NewAdminUserService(p.deps...), nil
    case RegularUser:
        return NewRegularUserService(p.deps...), nil
    default:
        return nil, errors.Errorf(ctx, "unknown user type: %s", userType)
    }
}
```

**Use Dynamic Registry Pattern When:**
- Implementations can be registered at runtime
- Plugin-like architecture is needed
- Large number of implementations
- Third-party extensions are expected

```go
// Dynamic Registry - Good for extensible systems
type ProcessorRegistry struct {
    processors map[string]ProcessorCreator
}

func (r *ProcessorRegistry) Register(name string, creator ProcessorCreator) {
    r.processors[name] = creator
}
```

### Interface vs Concrete Implementation Design

**Always Use Public Interface + Private Implementation:**

```go
// ✅ Good: Public interface, private implementation
type OrderService interface {
    Process(ctx context.Context, order Order) error
    Validate(ctx context.Context, order Order) error
}

type orderService struct {  // private
    repository OrderRepository
    validator  OrderValidator
    logger     log.Logger
}

func NewOrderService(deps...) OrderService {  // returns interface
    return &orderService{...}
}
```

**Avoid Public Structs:**

```go
// ❌ Bad: Exposes implementation details
type OrderService struct {  // public struct
    Dependencies map[string]interface{}
}
```

## Type Design Patterns

### Type vs Implementation Separation

**Separate Domain Types from Business Logic:**

```go
// Domain type - represents categories/enum-like values
type OrderType string

const (
    MarketOrder OrderType = "market"
    LimitOrder  OrderType = "limit"
    StopOrder   OrderType = "stop"
)

// Business interface - represents behavior
type OrderProcessor interface {
    Process(ctx context.Context, order Order) error
    Validate(ctx context.Context, order Order) error
}
```

**Benefits:**
- Clear separation between "what type" vs "how it works"
- Type-safe constants instead of string literals
- Easy to extend with new types without touching business logic

### Domain Modeling and Naming

**Choose Domain-Appropriate Names:**

```go
// ✅ Good: Domain-specific, clear intent
type PaymentProcessor interface {  // What it represents
    Process(...) error             // What it does
}

type PaymentType string           // What category it belongs to

// ❌ Bad: Technical implementation focus
type PaymentHandler interface {   // Focuses on technical aspect
    Handle(...) error             // Generic technical term
}
```

**Naming Guidelines:**
- Use domain language, not technical implementation details
- Interfaces should describe capability (`Processor`, `Validator`, `Repository`)
- Types should describe categorization (`OrderType`, `PaymentType`, `UserRole`)
- Methods should describe intent (`Process`, `Validate`, `Store`)

## Dependency Injection Best Practices

### Constructor Injection vs Context Objects

**✅ Good: Constructor Dependency Injection**

```go
type EmailService struct {
    smtpClient   SMTPClient
    templateRepo TemplateRepository
    logger       log.Logger
}

func NewEmailService(
    smtpClient SMTPClient,
    templateRepo TemplateRepository,
    logger log.Logger,
) EmailService {
    return &EmailService{
        smtpClient:   smtpClient,
        templateRepo: templateRepo,
        logger:       logger,
    }
}
```

**❌ Bad: Context Object Anti-Pattern**

```go
// Avoid passing dependencies through context objects
type ServiceContext struct {
    SMTPClient   SMTPClient
    TemplateRepo TemplateRepository
    Logger       log.Logger
}

func (e *EmailService) Send(..., serviceCtx ServiceContext) {
    // Dependencies passed through method calls
}
```

**Why Constructor Injection is Better:**
- Dependencies are explicit and immutable
- Easier to test with mocked dependencies
- Compile-time dependency validation
- Cleaner method signatures

### Factory Pattern Implementation

**Use Factory for Complex Construction:**

```go
func NewUserServiceProvider(
    userRepo UserRepository,
    validator UserValidator,
    logger log.Logger,
) UserProvider {
    return &userProvider{
        userRepo:  userRepo,
        validator: validator,
        logger:    logger,
    }
}

func (p *userProvider) Get(ctx context.Context, userType UserType) (UserService, error) {
    switch userType {
    case AdminUser:
        return NewAdminUserService(p.userRepo, p.validator, p.logger), nil
    case RegularUser:
        return NewRegularUserService(p.userRepo, p.validator, p.logger), nil
    }
}
```

## Implementation Patterns

### Static vs Dynamic Performance Considerations

**Static Switch Statements for Known Sets:**

```go
// ✅ Fast: Compiled switch statement
func (p *processorProvider) Get(ctx context.Context, processType ProcessType) (Processor, error) {
    switch processType {
    case ImageProcess:
        return NewImageProcessor(p.deps...), nil
    case VideoProcess:
        return NewVideoProcessor(p.deps...), nil
    case AudioProcess:
        return NewAudioProcessor(p.deps...), nil
    }
}
```

**Dynamic Map Lookups for Extensible Sets:**

```go
// Slower but flexible: Runtime map lookup
var processors = map[ProcessType]func(...deps) Processor{
    ImageProcess: NewImageProcessor,
    VideoProcess: NewVideoProcessor,
    AudioProcess: NewAudioProcessor,
}
```

**Decision Criteria:**
- Static: Fixed set, performance critical, simple
- Dynamic: Extensible, plugin architecture, complex initialization

### Method Naming Patterns

**Use Intent-Revealing Names:**

```go
// ✅ Good: Clear intent and domain meaning
func (s *orderService) Process(ctx context.Context, order Order) error
func (s *orderService) Validate(ctx context.Context, order Order) error
func (r *orderRepository) Store(ctx context.Context, order Order) error

// ❌ Bad: Generic or ambiguous
func (s *orderService) Handle(...)     // Generic: handle what?
func (r *orderRepository) Save(...)    // Ambiguous: save vs store vs persist
func (s *orderService) Execute(...)    // Generic: execute what operation?
```

## Package Organization Principles

### Package Naming and Structure

**✅ Good: Single-Purpose, Flat Structure**

```
pkg/
├── user/               # Single purpose, singular noun
│   ├── user.go            # Interface definition
│   ├── user-type.go       # Type definitions  
│   ├── provider.go        # Provider implementation
│   ├── admin.go           # Individual implementations
│   ├── regular.go
│   └── guest.go
├── order/
│   ├── order.go
│   ├── processor.go
│   └── validator.go
└── payment/
    ├── payment.go
    └── gateway.go
```

**❌ Bad: Nested, Plural, Multi-Purpose**

```
pkg/
├── handlers/
│   ├── users/          # Nested under handlers
│   │   ├── processors/    # Deeply nested
│   │   ├── validators/    # Separate concerns mixed
│   │   └── utilities/
│   └── orders/
│       └── managers/   # Vague responsibility
```

### File Organization Guidelines

**When to Split Files:**

1. **Interface Definition**: Always in separate file (`user.go`, `order.go`)
2. **Type Definitions**: Separate if complex (`user-type.go`, `order-type.go`)
3. **Individual Implementations**: One per file (`admin.go`, `guest.go`)
4. **Provider/Factory**: Separate file (`provider.go`, `factory.go`)
5. **Utilities**: Only if shared across multiple implementations (`utils.go`)

## Decision Checklists

### Before Writing Any Service

**Architecture Questions:**
- [ ] Will implementations change at runtime? (Registry vs Provider)
- [ ] Are dependencies fixed at construction? (Constructor injection)
- [ ] Is this a single concern? (Package responsibility)
- [ ] What domain terms best describe this? (Naming)

**Type Design Questions:**
- [ ] Do I need to separate type categories from implementations?
- [ ] Should this be an interface or concrete type?
- [ ] Are my names domain-focused or implementation-focused?

**Package Organization Questions:**
- [ ] Does this package have a single, clear responsibility?
- [ ] Am I nesting packages unnecessarily?
- [ ] Are file names descriptive of their contents?

### During Implementation

**Code Quality Checks:**
- [ ] Are all dependencies injected through constructors?
- [ ] Are implementations private with public interfaces?
- [ ] Am I using domain language consistently?
- [ ] Are method signatures clean and purposeful?

**Performance Considerations:**
- [ ] Is this performance-critical? (Consider static vs dynamic)
- [ ] Will this create objects frequently? (Consider constructor overhead)
- [ ] Are interfaces minimal and focused?

### Before Committing

**Final Validation:**
- [ ] Can I easily add a new implementation?
- [ ] Are dependencies mockable for testing?
- [ ] Do package names reflect their purpose?
- [ ] Would a new team member understand the structure?

## Real-World Example: Service Evolution

### Initial Monolithic Handler (What Not to Do)

```go
// ❌ Bad: Monolithic switch statement in handler
func NewOrderHandler(...) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        switch r.URL.Query().Get("type") {
        case "market":
            // 50 lines of market order logic here
        case "limit":
            // 40 lines of limit order logic here
        case "stop":
            // 60 lines of stop order logic here
        }
    }
}
```

**Problems:**
- Handler responsible for business logic
- Hard to test individual order types
- Difficult to add new order types
- Mixed concerns (HTTP handling + business logic)

### Proper Implementation (Follow These Patterns)

```go
// ✅ Good: Proper separation of concerns

// 1. Domain type definition
type OrderType string
const (
    MarketOrder OrderType = "market"
    LimitOrder  OrderType = "limit"
    StopOrder   OrderType = "stop"
)

// 2. Business interface
type OrderProcessor interface {
    Process(ctx context.Context, order Order) error
}

// 3. Provider interface with private implementation
type OrderProvider interface {
    Get(ctx context.Context, orderType OrderType) (OrderProcessor, error)
}

// 4. Clean handler that delegates
func NewOrderHandler(provider OrderProvider) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        orderType := OrderType(r.URL.Query().Get("type"))
        processor, err := provider.Get(r.Context(), orderType)
        if err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }
        
        var order Order
        if err := json.NewDecoder(r.Body).Decode(&order); err != nil {
            http.Error(w, err.Error(), http.StatusBadRequest)
            return
        }
        
        if err := processor.Process(r.Context(), order); err != nil {
            http.Error(w, err.Error(), http.StatusInternalServerError)
            return
        }
        
        w.WriteHeader(http.StatusOK)
    }
}
```

**Benefits:**
- Single responsibility principle
- Easy to test and extend
- Clear separation of concerns
- Domain-focused naming
- Proper dependency injection

This structure scales naturally and avoids the need for major refactoring as the service grows.

## Common Anti-Patterns to Avoid

### 1. The "Manager" Anti-Pattern
```go
// ❌ Bad: Vague responsibility
type UserManager struct { ... }
type OrderManager struct { ... }

// ✅ Good: Clear purpose
type UserService struct { ... }
type OrderProcessor struct { ... }
```

### 2. The "Util" Anti-Pattern
```go
// ❌ Bad: Dumping ground for random functions
package utils
func ProcessOrder(...) { ... }
func ValidateUser(...) { ... }

// ✅ Good: Domain-specific organization
package order
func (p *processor) Process(...) { ... }

package user  
func (v *validator) Validate(...) { ... }
```

### 3. The "God Interface" Anti-Pattern
```go
// ❌ Bad: Too many responsibilities
type UserService interface {
    Create(...)
    Update(...)
    Delete(...)
    SendEmail(...)
    ProcessPayment(...)
    GenerateReport(...)
}

// ✅ Good: Single responsibility interfaces
type UserService interface {
    Create(...)
    Update(...)
    Delete(...)
}

type EmailService interface {
    Send(...)
}

type PaymentService interface {
    Process(...)
}
```

Following these patterns will help you build maintainable, testable, and scalable Go services from the start.