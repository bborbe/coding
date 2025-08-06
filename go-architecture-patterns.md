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

### Interface Definition

Always start with a clear interface definition with counterfeiter comments for mock generation:

```go
// UserService handles user operations
//counterfeiter:generate -o ../mocks/user-service.go --fake-name UserService . UserService
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

## 3. factory.go Pattern

Factory functions handle complex object creation with multiple dependencies:

```go
func CreateMessageHandler(
    sentryClient sentry.Client,
    syncProducer producer.SyncProducer,
    schemaRegistry cdb.SchemaRegistry,
    schemaID cdb.SchemaID,
) consumer.MessageHandler {
    return consumer.SendErrorsToSentry(
        consumer.NewMetricsMessageHandler(
            cdb.NewConverterEventObjectMessageHandler(
                CreateConverter(schemaRegistry, schemaID),
                CreateEventSender(syncProducer),
                log.DefaultSamplerFactory,
            ),
            consumer.NewMessageHandlerMetrics(),
        ),
        sentryClient,
        log.DefaultSamplerFactory,
    )
}

func CreateConverter(schemaRegistry cdb.SchemaRegistry, schemaID cdb.SchemaID) cdb.Converter {
    return cdb.NewConverter(schemaRegistry, schemaID)
}
```

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
