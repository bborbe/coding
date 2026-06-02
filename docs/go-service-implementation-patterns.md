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

### RULE go-service-impl/provider-vs-registry-choice (SHOULD)

**Owner**: go-architecture-assistant
**Applies when**: a Go service needs to dispatch to one of several implementations and the code uses the wrong dispatch shape for the set's openness: a `map[string]Creator` registry for a closed compile-time set, or a compiled `switch` for an open runtime-extensible set.
**Enforcement**: judgment (semantic — depends on whether the implementation set is closed or open)
**Why**: Static `switch` is faster (compiled jump table vs. map lookup + indirect call), trivially exhaustive (compiler-checked via `default:` + `errors.Errorf`), and refactor-friendly (renames propagate). Dynamic map-based registries are necessary when implementations register themselves at runtime (plugin systems, third-party extensions) but the cost — lost compile-time exhaustiveness, harder-to-test, registration-order sensitivity — is real. Match the shape to the problem: closed set → switch; open set → registry. Defaulting to one or the other regardless of context produces both unnecessary overhead and brittle systems.

#### Bad

```go
// Fixed 3-implementation set, runtime registry — overkill.
// Also violates `go-architecture/no-globals-or-singletons` (MUST): init()
// initialises a package-level Registry with all the bound creators —
// untestable in parallel, hidden dependency graph.
type ProcessorRegistry struct {
	processors map[string]ProcessorCreator
}

func init() {
	r := &ProcessorRegistry{processors: make(map[string]ProcessorCreator)}
	r.Register("image",    NewImageProcessor)    // these never change
	r.Register("video",    NewVideoProcessor)
	r.Register("document", NewDocumentProcessor)
}
```

#### Good

```go
// Fixed set → compiled switch; exhaustiveness checked at compile time
type ProcessorProvider interface {
	Get(ctx context.Context, t ProcessType) (Processor, error)
}

func (p *processorProvider) Get(ctx context.Context, t ProcessType) (Processor, error) {
	switch t {
	case ProcessImage:
		return NewImageProcessor(p.deps...), nil
	case ProcessVideo:
		return NewVideoProcessor(p.deps...), nil
	case ProcessDocument:
		return NewDocumentProcessor(p.deps...), nil
	default:
		return nil, errors.Errorf(ctx, "unknown processor type: %s", t)
	}
}

// Plugin-extensible set → registry; new types register at startup
type PluginRegistry struct {
	plugins map[string]PluginCreator
}

func (r *PluginRegistry) Register(name string, creator PluginCreator) { r.plugins[name] = creator }
```

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

### RULE go-service-impl/no-context-object-injection (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go service method receives a struct (by value OR by pointer) named `Context` / `ServiceContext` / `Deps` / etc. that bundles multiple service dependencies (logger, repository, validator, etc.) and passes them through method calls instead of through the constructor.
**Enforcement**: judgment (ast-grep follow-up: method signature with a parameter type matching `<Name>Context` or `*<Name>Context` / `<Name>Deps` or `*<Name>Deps` where the struct contains 2+ service-interface fields — value and pointer shapes share the anti-pattern)
**Why**: Context-object injection is the rebrand of global state — every method becomes "give me everything, I'll pick what I need." Three failure modes: (1) compile-time can't tell which deps a method actually uses, so refactors and dead-code detection break; (2) tests need to construct a full context object for every call site, even for methods that touch one dependency; (3) the context grows over time (the "we'll just add one more field" trap), and unused fields linger forever. Constructor injection forces the dep set to be minimal and visible at the type signature.

#### Bad

```go
type ServiceContext struct {
	SMTPClient   SMTPClient
	TemplateRepo TemplateRepository
	Logger       log.Logger
}

func (e *EmailService) Send(ctx context.Context, msg Message, svcCtx ServiceContext) error {
	svcCtx.Logger.Info("sending")
	return svcCtx.SMTPClient.Send(ctx, msg)  // hidden dep set; compile-time can't see it
}
```

#### Good

```go
type EmailService interface {
	Send(ctx context.Context, msg Message) error
}

type emailService struct {
	smtpClient   SMTPClient
	templateRepo TemplateRepository
	logger       log.Logger
}

func NewEmailService(
	smtpClient SMTPClient,
	templateRepo TemplateRepository,
	logger log.Logger,
) EmailService {
	return &emailService{smtpClient: smtpClient, templateRepo: templateRepo, logger: logger}
}

func (e *emailService) Send(ctx context.Context, msg Message) error {
	e.logger.Info("sending")              // dep is a struct field, visible at type
	return e.smtpClient.Send(ctx, msg)
}
```

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