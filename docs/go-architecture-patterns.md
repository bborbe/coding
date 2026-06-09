# Go Code Patterns for Services

This document defines the standard Go code patterns used in the Services platform. These patterns ensure consistency, maintainability, and adherence to Go best practices across all services.

## Overview

The standard pattern for Go packages in the Services follows this structure:
1. **Interface** - Define the contract
2. **Constructor** - Create instances with dependency injection
3. **Struct** - Private implementation
4. **One main method** - Core functionality
5. **Helper methods** - Supporting functionality (optional)

## 1. Interface → Constructor → Struct → Method Pattern

### RULE go-architecture/counterfeiter-directive-on-interface (MUST)

**Owner**: go-architecture-assistant
**Applies when**: an exported `interface` declaration in a non-`main` Go service package (i.e. likely substituted via mocks in tests) has no preceding `//counterfeiter:generate` line. Concrete trigger: any package with `*_test.go` files that import a `mocks` package, plus every exported interface in that package.
**Enforcement**: `rules/go/counterfeiter-directive-on-interface.yml`
**Why**: Hand-written mocks drift silently — when the interface gains a method, the mock keeps satisfying the old surface and tests pass against a stale contract. The `//counterfeiter:generate` directive forces `go generate ./...` to regenerate the fake, so any drift surfaces immediately at code-gen time. Missing the directive means the fake isn't regenerated, the test doesn't exercise the new method, and the bug ships.

#### Bad

```go
// No counterfeiter directive — mock won't regenerate when interface changes
type UserService interface {
	Create(ctx context.Context, user User) error
	Get(ctx context.Context, id UserID) (*User, error)
}
```

#### Good

```go
//counterfeiter:generate -o ../mocks/service-user-service.go --fake-name ServiceUserService . UserService
type UserService interface {
	Create(ctx context.Context, user User) error
	Get(ctx context.Context, id UserID) (*User, error)
}
```

### Interface Definition

Always start with a clear interface definition with counterfeiter comments for mock generation:

```go
// UserService handles user operations.
// Mock name and filename are prefixed with the source package (here `service`)
// so mocks/ stays collision-free across packages. See go-mocking-guide.md.
//counterfeiter:generate -o ../mocks/service-user-service.go --fake-name ServiceUserService . UserService
type UserService interface {
    Create(ctx context.Context, user User) error
    Get(ctx context.Context, id UserID) (*User, error)
}
```

**Key points:**
- Use counterfeiter comments for all interfaces
- Include context.Context as first parameter in all methods that return a error
- Use descriptive interface names ending with the service purpose
- Document the interface purpose clearly

### RULE go-architecture/new-prefix-constructor-naming (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go function outside `pkg/factory/**` returns an exported interface or struct type and is intended to be the canonical construction site, but the function name does not start with `New`.
**Enforcement**: `rules/go/new-prefix-constructor-naming.yml` (mechanical first-pass flags exported functions returning exported types without `New` prefix; `pkg/factory/**` excluded) + judgment-tier LLM adjudication to rule out `Create*` factories, helper functions, and non-constructor uses.
**Why**: `New*` is the universal Go signal for "this is the constructor — give it deps, get back a ready-to-use object". Without it, consumers can't tell `UserService(...)` from a regular function call; tooling (IDE search, godoc grouping, godoc renderers) treats it as ordinary; refactors don't surface the construction site. The convention is cheap; ignoring it costs every consumer a second of "wait, is this the constructor?". The `Create*` factory prefix is a deliberate exception scoped to `pkg/factory/**` — that's the factory pattern's home, not the service-construction site this rule covers.

#### Bad

```go
// Service-package construction sites — should all be New*
func MakeUserService(db bolt.DB, logger log.Logger) UserService { ... }
func BuildUserService(db bolt.DB, logger log.Logger) UserService { ... }
func UserSvc(db bolt.DB, logger log.Logger) UserService { ... }
```

#### Good

```go
func NewUserService(
	db bolt.DB,
	logger log.Logger,
	currentDateTime libtime.CurrentDateTime,
	userValidator UserValidator,
) UserService { ... }
```

### RULE go-architecture/constructor-returns-interface (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go `New*` constructor returns the concrete struct type (`*userService`) instead of the interface it implements (`UserService`).
**Enforcement**: `rules/go/constructor-returns-interface.yml` flags every `func NewXxx(...) *ConcreteStruct` declaration. The agent decides per-finding whether the returned concrete type has a corresponding interface in the same package (real violation) or is a data-holder / config / DTO struct without an interface (exempt) — the same-package interface lookup needs cross-file reasoning ast-grep can't do in a single rule.
**Why**: Returning the concrete struct leaks implementation: callers can reach for non-interface methods, type-assert downstream, depend on private struct fields via reflection. Returning the interface forces every consumer through the contract surface — refactors stay contained, mocks stay drop-in, dependency direction stays one-way.

#### Bad

```go
// Returns concrete struct — leaks implementation
func NewUserService(...) *userService {
	return &userService{...}
}
```

#### Good

```go
// Returns interface — consumers see only the contract
func NewUserService(...) UserService {
	return &userService{...}
}
```

### Constructor Function

Create constructor functions using the `New*` pattern:

```go
func NewUserService(
    db bolt.DB,
    logger log.Logger,
    currentDateTime libtime.CurrentDateTime,
    userValidator UserValidator,
) UserService {
    return &userService{
        db:              db,
        logger:          logger,
        currentDateTime: currentDateTime,
        userValidator:   userValidator,
    }
}
```

**Key points:**
- Always use `New*` naming pattern matching the interface
- Use dependency injection for all dependencies
- Return the interface type, not the concrete struct
- Order dependencies logically (db, external services, utilities)

### RULE go-architecture/private-struct-matches-interface (SHOULD)

**Owner**: go-architecture-assistant
**Applies when**: a Go package exposes an exported interface (e.g. `UserService`) and the package contains exactly one struct implementing every method of that interface, but the struct's name is not the interface name with the first letter lowercased (`userService`).
**Enforcement**: judgment (paired-declaration scan: for each exported interface, find structs with matching method sets in the same package and check name correspondence — single-implementation packages only)
**Trigger**: **/*.go
**Why**: When `UserService`'s implementation is `userService`, every reader knows at a glance which struct backs which interface — godoc renders them adjacent, IDE outlines pair them, refactors find them with one rename. When the implementation is `defaultUserService` / `userServiceImpl` / `internalUser`, every reader has to grep to find the link, and "which struct implements this interface" becomes a research task.

#### Bad

```go
type UserService interface { ... }

// Mismatched name — pairing not self-evident
type userServiceImpl struct { ... }
```

#### Good

```go
type UserService interface { ... }

// Same name, first letter lowercased — pairing self-evident
type userService struct { ... }
```

### Private Struct Implementation

```go
type userService struct {
    db              bolt.DB
    logger          log.Logger
    currentDateTime libtime.CurrentDateTime
    userValidator   UserValidator
}
```

**Key points:**
- Use lowercase struct name (private)
- Match interface name but lowercase
- Include all dependencies as fields
- Order fields consistently with constructor parameters

### Main Methods

```go
func (u *userService) Create(ctx context.Context, user User) error {
    if err := u.userValidator.Validate(ctx, user); err != nil {
        return errors.Wrap(ctx, err, "validate user failed")
    }
    
    user.CreatedAt = u.currentDateTime.Now()
    
    if err := u.saveUser(ctx, user); err != nil {
        return errors.Wrap(ctx, err, "save user failed")
    }
    
    return nil
}

func (u *userService) Get(ctx context.Context, id UserID) (*User, error) {
    user, err := u.loadUser(ctx, id)
    if err != nil {
        return nil, errors.Wrap(ctx, err, "load user failed")
    }
    
    return user, nil
}
```

### Helper Methods (Optional)

```go
func (u *userService) saveUser(ctx context.Context, user User) error {
    return u.db.Update(func(tx *bolt.Tx) error {
        bucket := tx.Bucket([]byte("users"))
        data, err := json.Marshal(user)
        if err != nil {
            return errors.Wrap(ctx, err, "marshal user failed")
        }
        return bucket.Put([]byte(user.ID.String()), data)
    })
}

func (u *userService) loadUser(ctx context.Context, id UserID) (*User, error) {
    var user User
    err := u.db.View(func(tx *bolt.Tx) error {
        bucket := tx.Bucket([]byte("users"))
        data := bucket.Get([]byte(id.String()))
        if data == nil {
            return errors.New("user not found")
        }
        return json.Unmarshal(data, &user)
    })
    return &user, err
}
```

## 2. main.go Pattern

### Application Struct

```go
type application struct {
    Port         int    `required:"false" arg:"port" env:"PORT" usage:"port to listen" default:"9090"`
    DataDir      string `required:"true" arg:"datadir" env:"DATADIR" usage:"data directory"`
    KafkaBrokers string `required:"true" arg:"kafka-brokers" env:"KAFKA_BROKERS" usage:"kafka brokers"`
    SentryDSN    string `required:"false" arg:"sentry-dsn" env:"SENTRY_DSN" usage:"Sentry DSN"`
    SentryProxy  string `required:"false" arg:"sentry-proxy" env:"SENTRY_PROXY" usage:"Sentry Proxy"`
}
```

### Main Function

```go
func main() {
    app := &application{}
    os.Exit(service.Main(context.Background(), app, &app.SentryDSN, &app.SentryProxy))
}
```

## Key Components
- **ConcurrentRunner**: Manages concurrent execution with limits (`run_concurrent-runner.go`)
- **Trigger System**: Fire/Done pattern for synchronization (`run_trigger.go`, `run_trigger-multi.go`)
- **Error Handling**: Aggregate multiple errors (`run_errors.go`)
- **Utilities**: Retry, skip, delay, panic handling, metrics, logging

### Run Method

```go
func (a *application) Run(
    ctx context.Context,
    sentryClient sentry.Client,
) error {
    // Initialize databases
    db, err := bolt.OpenDir(a.DataDir)
    if err != nil {
        return errors.Wrap(ctx, err, "open bolt db failed")
    }
    defer db.Close()

    // Initialize producers/consumers
    syncProducer, err := producer.NewSyncProducer(ctx, kafka.ParseBrokersFromString(a.KafkaBrokers), producer.NewSyncProducerMetrics())
    if err != nil {
        return errors.Wrap(ctx, err, "create sync producer failed")
    }
    defer syncProducer.Close()

    // Start services
    return service.Run(
        ctx,
        a.createHttpServer(db, syncProducer),
        a.createConsumer(sentryClient, db, syncProducer),
    )
}
```

### Creator Methods

```go
func (a *application) createHttpServer(db bolt.DB, syncProducer producer.SyncProducer) run.Func {
    return func(ctx context.Context) error {
        ctx, cancel := context.WithCancel(ctx)
        defer cancel()

        userService := pkg.NewUserService(db, log.DefaultSamplerFactory.Sampler(), libtime.NewCurrentDateTime(), pkg.NewUserValidator())
        userHandler := pkg.NewUserHandler(userService)

        router := mux.NewRouter()
        router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/readiness").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/metrics").Handler(promhttp.Handler())
        router.Handle("/users", handler.NewErrorHandler(userHandler))

        return libhttp.NewServerWithPort(a.Port, router).Run(ctx)
    }
}
```

## 3. Factory Pattern

Factory functions handle complex object creation and dependency composition. Factories contain **zero business logic** - only constructor calls to wire dependencies together.

```go
func CreateMessageHandler(
    sentryClient sentry.Client,
    syncProducer producer.SyncProducer,
) consumer.MessageHandler {
    return consumer.SendErrorsToSentry(
        consumer.NewMetricsMessageHandler(
            CreateUserMessageHandler(syncProducer),
            consumer.NewMessageHandlerMetrics(),
        ),
        sentryClient,
        log.DefaultSamplerFactory,
    )
}
```

**Key points:**
- All factory functions in single file: `pkg/factory/factory.go` or `lib/{name}/factory.go`
- Use `Create*` prefix for factories, `New*` for constructors
- No loops, conditionals, or business logic - only composition
- Move complex inline logic to separate implementation files

**See [go-factory-pattern.md](go-factory-pattern.md) for comprehensive factory pattern guidance.**

## 4. Common Patterns

### Time Handling

Always use `github.com/bborbe/time` instead of standard `time` package:

```go
import libtime "github.com/bborbe/time"

type service struct {
    currentDateTime libtime.CurrentDateTime
}

func NewService(currentDateTime libtime.CurrentDateTime) Service {
    return &service{
        currentDateTime: currentDateTime,
    }
}

func (s *service) DoSomething(ctx context.Context) error {
    now := s.currentDateTime.Now() // No context parameter
    // Use now...
    return nil
}

// In main.go
currentDateTime := libtime.NewCurrentDateTime()
service := pkg.NewService(currentDateTime)

// In tests
import libtimetest "github.com/bborbe/time/test"

func TestSomething(t *testing.T) {
    currentDateTime := libtime.NewCurrentDateTime()
    currentDateTime.SetNow(libtimetest.ParseDateTime("2023-12-25T00:00:00Z"))
    // Test with fixed time
}
```

### Pointer Utilities

Use `github.com/bborbe/collection` for pointer utilities:

```go
import libcollection "github.com/bborbe/collection"

// Instead of custom helper functions
func stringPtr(s string) *string { return &s } // DON'T DO THIS

// Use collection.Ptr
value := libcollection.Ptr("hello")
```

### Error Handling

Always wrap errors with context:

```go
import "github.com/bborbe/errors"

func (s *service) DoSomething(ctx context.Context) error {
    result, err := s.dependency.CallSomething(ctx)
    if err != nil {
        return errors.Wrap(ctx, err, "call something failed")
    }
    return nil
}
```

### Context Usage

**Golden Rules:**
- Always use `context.Context` as the first parameter in functions that can return an error
- Pass context through all function calls - never create new context.Background() in the middle of a call chain
- Use context for cancellation, timeouts, and values
- **NEVER use `context.Background()` in business logic, error handling, or service methods**

**✅ DO: Pass context from caller**
```go
func (s *service) ProcessData(ctx context.Context, data Data) error {
    if err := s.validator.Validate(ctx, data); err != nil {
        return errors.Wrap(ctx, err, "validation failed") // Use ctx from caller
    }
    
    result, err := s.processor.Process(ctx, data) // Pass ctx through
    if err != nil {
        return errors.Wrap(ctx, err, "processing failed") // Use ctx from caller
    }
    
    return s.storage.Save(ctx, result) // Pass ctx through
}
```

**❌ DON'T: Create context.Background() in service methods**
```go
func (s *service) ProcessData(ctx context.Context, data Data) error {
    if err := s.validator.Validate(ctx, data); err != nil {
        // WRONG: Don't create new background context
        return errors.Wrap(context.Background(), err, "validation failed")
    }
    return nil
}
```

**✅ DO: Use context.Background() only in these cases:**
- `main.go` entry points and top-level initialization
- Test setup (when you need a root context for testing)
- Background goroutines that should not be cancelled by request contexts

### Infinite Loops with Context Cancellation

**CRITICAL:** All infinite loops must check for context cancellation to prevent getting stuck when context is cancelled.

**✅ DO: Always include context cancellation in infinite loops**
```go
func (s *service) RunWorker(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
            // Your work here
            if err := s.processNextItem(ctx); err != nil {
                return errors.Wrap(ctx, err, "process item failed")
            }
            
            // Optional: add delay between iterations
            time.Sleep(100 * time.Millisecond)
        }
    }
}
```

**❌ DON'T: Create infinite loops without context cancellation**
```go
func (s *service) RunWorker(ctx context.Context) error {
    for {
        // WRONG: Loop will never exit when context is cancelled
        if err := s.processNextItem(ctx); err != nil {
            return err
        }
    }
}
```

**Key points:**
- Always use `select` with `case <-ctx.Done():` in infinite loops
- Return `ctx.Err()` when context is cancelled to preserve cancellation reason
- Place the select statement at the beginning of the loop iteration
- Consider adding delays between iterations to avoid busy waiting

## 5. Naming Conventions

### Interfaces
- Use descriptive names ending with purpose: `UserService`, `OrderProcessor`, `DataConverter`
- Start with uppercase for public interfaces
- Keep interface names concise but clear

### Structs
- Use lowercase for private implementations: `userService`, `orderProcessor`
- Match interface name but lowercase

### Constructor Functions
- Always start with `New`: `NewUserService`, `NewOrderProcessor`
- Return interface type, not concrete struct

### Methods
- Use clear, action-oriented names: `Create`, `Get`, `Process`, `Convert`
- Start with uppercase for public methods
- Use lowercase for private helper methods

## 6. Testing Patterns

### Mock Handling Policy

For comprehensive mocking patterns and best practices, see **[go-mocking-guide.md](go-mocking-guide.md)**.

**CRITICAL RULES:**
- Never generate fake mock classes manually - always use counterfeiter
- Ask user where existing mocks are located before creating new ones
- Only add counterfeiter comments to current service interfaces
- All mocks must be in `mocks/` directory and generated via Counterfeiter

### Test Structure Example

```go
func TestUserService_Create_Success(t *testing.T) {
    // Setup with mocks and real utilities
    currentDateTime := libtime.NewCurrentDateTime()
    db := &mocks.DB{}                        // Mock external dependency
    
    service := NewUserService(
        db, 
        log.DefaultSamplerFactory.Sampler(), // Real utility
        currentDateTime,                     // Real utility
    )
    
    // Test business logic
    err := service.Create(context.Background(), User{ID: "123"})
    assert.NoError(t, err)
}
```

## 7. Dependency Injection Best Practices

### RULE go-architecture/no-globals-or-singletons (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go service package introduces a service dependency (logger, DB, HTTP client, time getter, etc.) via any of: (a) a package-level `var` declaration, (b) initialisation inside `func init()`, or (c) lazy initialisation via `sync.Once` keyed to a package-level pointer. All three patterns share the same test-ordering and parallelism problems.
**Enforcement**: `rules/go/no-globals-or-singletons.yml` covers the most common variant — `var X = NewY(...)` / `var X = CreateY(...)` package-level declarations whose RHS is a New*/Create* constructor call. The `init()` and `sync.Once` variants stay judgment-tier (the agent makes the final call based on body inspection); the YAML catches the highest-frequency case mechanically.
**Why**: Package-level service deps are global state. They (1) make tests order-dependent (one test mutates the global, the next sees it), (2) prevent parallelism (`go test -p N` shares the var), (3) hide the dependency graph (callers can't see what's used), and (4) make refactors fragile (changing the dep means tracing every package that imports the global). Constructor injection makes the graph explicit and the lifecycle controllable.

#### Bad

```go
// Package-level globals — every consumer shares them
var (
	defaultLogger = log.New()
	defaultDB     = bolt.MustOpen("data.db")
	defaultNow    = libtime.NewCurrentDateTime()
)

func DoWork(ctx context.Context) error {
	defaultLogger.Info("starting")  // implicit dep — hidden from caller
	return defaultDB.Update(ctx, ...)
}
```

#### Good

```go
type UserService interface {
	Create(ctx context.Context, user User) error
}

func NewUserService(
	logger log.Logger,
	db bolt.DB,
	currentDateTime libtime.CurrentDateTime,
) UserService {
	return &userService{logger: logger, db: db, currentDateTime: currentDateTime}
}

func (u *userService) Create(ctx context.Context, user User) error {
	u.logger.Info("creating user")  // explicit dep — caller controls
	return u.db.Update(ctx, ...)
}
```

### Service Composition
- Inject all dependencies through constructors
- Use interfaces for all dependencies
- Avoid global variables or singletons
- Initialize dependencies in main.go or factory functions

### Layered Architecture
```
main.go
  ↓
factory.go (complex creation)
  ↓
pkg/service.go (business logic)
  ↓
pkg/repository.go (data access)
```

## 8. Execution Strategies and Core Types

### Execution Strategies with github.com/bborbe/run

The `github.com/bborbe/run` package provides several execution strategies for handling concurrent operations:

- **Sequential**: Execute functions one after another (`Sequential`)
- **Parallel with different error handling**:
    - `CancelOnFirstFinish`: Cancel remaining on first completion
    - `CancelOnFirstError`: Cancel remaining on first error
    - `All`: Execute all and aggregate errors
    - `Run`: Execute all and return error channel

### Core Types

- `Func`: Function type `func(context.Context) error` - the basic unit of execution
- `Runnable`: Interface for objects that can be run with context

```go
import "github.com/bborbe/run"

// Example of using execution strategies
func (a *application) Run(ctx context.Context, sentryClient sentry.Client) error {
    return run.All(
        ctx,
        a.createHttpServer(db, syncProducer),
        a.createConsumer(sentryClient, db, syncProducer),
    )
}
```

## 9. Benjamin Borbe's Ecosystem Libraries

### Core Libraries
- `github.com/bborbe/run`: Runnable interface and execution strategies
- `github.com/bborbe/errors`: Error handling utilities with context wrapping
- `github.com/bborbe/service`: Service framework for CLI applications
- `github.com/bborbe/collection`: Collection utilities including `Ptr()` function
- `github.com/bborbe/time`: Time operations with dependency injection
- `github.com/bborbe/sentry`: Sentry integration for error reporting

### External Libraries
- `github.com/robfig/cron/v3`: Core cron scheduling engine
- `github.com/golang/glog`: Logging (see go-glog.md for level guidelines)

### Testing Framework
This ecosystem uses **Ginkgo v2** (BDD) with **Gomega** matchers:
- Counterfeiter for mock generation via `//go:generate` directives
- All major components have corresponding test files
- Tests run in UTC timezone for consistency
- Test suites are in `*_suite_test.go` files

Example test suite structure:
```go
package pkg_test

import (
    "testing"
    "time"

    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
    "github.com/onsi/gomega/format"
)

//go:generate go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate
func TestSuite(t *testing.T) {
    time.Local = time.UTC
    format.TruncatedDiff = false
    RegisterFailHandler(Fail)
    RunSpecs(t, "Test Suite")
}
```

**Key Implementation Notes:**
- All operations are context-aware for cancellation and timeouts
- Error handling is a key design principle with multiple strategies
- Code follows standard Go conventions with BSD license headers
- Mock generation is automated via `//counterfeiter:generate` comments
- Uses interface segregation with small, focused interfaces

## 10. File Organization

```
service-name/
├── main.go              # Application entry point
├── pkg/
│   ├── service.go       # Main business logic interfaces
│   ├── handler.go       # HTTP handlers
│   ├── repository.go    # Data access
│   ├── factory.go       # Complex object creation (if needed)
│   └── types.go         # Domain types
├── mocks/              # Generated counterfeiter mocks
├── k8s/                # Kubernetes manifests
├── go.mod
└── go.sum
```

## 11. Common Antipatterns to Avoid

### DON'T: Create custom pointer helper functions
```go
// DON'T DO THIS
func stringPtr(s string) *string { return &s }
func intPtr(i int) *int { return &i }

// DO THIS instead
import libcollection "github.com/bborbe/collection"
value := libcollection.Ptr("hello")
```

### DON'T: Use standard time package
```go
// DON'T DO THIS
import "time"
now := time.Now()

// DO THIS instead
import libtime "github.com/bborbe/time"
type Service struct {
    currentDateTime libtime.CurrentDateTime
}
now := s.currentDateTime.Now()
```

### DON'T: Skip error wrapping
```go
// DON'T DO THIS
if err != nil {
    return err
}

// DO THIS instead
if err != nil {
    return errors.Wrap(ctx, err, "operation failed")
}
```

### DON'T: Use context.Background() instead of caller's context
```go
// DON'T DO THIS - creates new background context in business logic
func (s *service) extractMetadata(document *Document) (*Metadata, error) {
    if document.Content == nil {
        // WRONG: Using context.Background() instead of caller's context
        return nil, errors.Errorf(context.Background(), "document has no content")
    }
    return parseMetadata(document.Content), nil
}

func (s *service) ProcessDocument(ctx context.Context, document *Document) error {
    metadata, err := s.extractMetadata(document) // Lost context chain!
    if err != nil {
        return err
    }
    // ... rest of processing
}

// DO THIS - pass context through the call chain
func (s *service) extractMetadata(ctx context.Context, document *Document) (*Metadata, error) {
    if document.Content == nil {
        // CORRECT: Use context from caller
        return nil, errors.Errorf(ctx, "document has no content")
    }
    return parseMetadata(document.Content), nil
}

func (s *service) ProcessDocument(ctx context.Context, document *Document) error {
    metadata, err := s.extractMetadata(ctx, document) // Context preserved!
    if err != nil {
        return err
    }
    // ... rest of processing
}
```

### RULE go-architecture/business-logic-not-in-main (MUST)

**Owner**: go-architecture-assistant
**Applies when**: `main.go` (production code only — `main_test.go` is exempt) or `application.Run` contains domain operations (validation, business rules, data transformation, decision logic) instead of delegating to a service in `pkg/`.
**Enforcement**: judgment (semantic check — what counts as "business logic" requires reading the code). Coarse ast-grep filter is possible: `main.go` containing imports of `bborbe/errors` or `bborbe/validation` is a strong signal that domain logic leaked out of `pkg/`; production-file-scoped, `_test.go` excluded.
**Trigger**: **/main.go
**Why**: `main.go` is for wiring: parsing flags, building dependencies, starting goroutines, handling shutdown. Business logic in `main.go` is untestable (Ginkgo suites can't exercise it without `gexec.Build` overhead), unreachable from other binaries (CLI tool vs HTTP server vs worker — they should share `pkg/` code), and impossible to refactor without touching the entry-point. Keep `main.go` thin; push every domain operation into a service.

#### Bad

```go
// Domain logic mixed into main.go
func (a *application) Run(ctx context.Context, sentryClient sentry.Client) error {
	// ... setup code ...

	// Business logic — wrong place
	user := User{Name: "John"}
	if user.Name == "" {
		return errors.New("invalid user")
	}
	if err := persistUser(user); err != nil {
		return err
	}
	return nil
}
```

#### Good

```go
// main.go wires; pkg/ owns domain
func (a *application) Run(ctx context.Context, sentryClient sentry.Client) error {
	// ... setup code ...
	service := pkg.NewUserService(a.db, a.logger, a.currentDateTime)
	if err := service.ProcessUsers(ctx); err != nil {
		return errors.Wrap(ctx, err, "process users failed")
	}
	return nil
}

// pkg/user-service.go has the domain
func (s *userService) ProcessUsers(ctx context.Context) error {
	// All validation, persistence, decision logic here
	return nil
}
```

### DON'T: Mix business logic in main.go
```go
// DON'T DO THIS - business logic in main.go
func (a *application) Run(ctx context.Context, sentryClient sentry.Client) error {
    // ... setup code ...
    
    // Business logic should be in pkg/
    user := User{Name: "John"}
    if user.Name == "" {
        return errors.New("invalid user")
    }
}

// DO THIS - move business logic to pkg/
func (a *application) Run(ctx context.Context, sentryClient sentry.Client) error {
    // ... setup code ...
    service := pkg.NewUserService(...)
    return service.ProcessUsers(ctx)
}
```

This pattern documentation ensures consistency across all services and makes the codebase more maintainable and understandable for all developers working on the platform.
