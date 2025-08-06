# Go Mocking Guide

Comprehensive guide for mock generation, usage, and best practices in Go using Counterfeiter. This guide consolidates mocking patterns from across the development ecosystem.

## 1. Overview

Mocking is essential for testing Go services that depend on external interfaces. This guide covers:
- Mock generation with Counterfeiter
- Testing patterns with Ginkgo v2 and Gomega
- Mock verification and setup strategies
- Integration testing with mixed real/mock dependencies
- What to mock vs what NOT to mock
- Mock discovery and location strategies
- Common antipatterns to avoid

### Core Tools
- **[Counterfeiter](https://github.com/maxbrunsfeld/counterfeiter)**: Generates type-safe mocks from interfaces
- **[Ginkgo v2](https://onsi.github.io/ginkgo/)**: BDD testing framework
- **[Gomega](https://onsi.github.io/gomega/)**: Assertion library

### Key Principle: Mock Granularity

**Mock at interface boundaries, not implementation details.** This keeps tests focused on your code's behavior while remaining maintainable and realistic.

- Mock external systems and unstable dependencies
- Use real implementations for stable, internal utilities
- Focus mocks on testing your business logic, not library internals

## 2. What to Mock vs What NOT to Mock

### 🎯 What TO Mock

#### External Dependencies
- **Database connections** - Mock the service layer interface, not the DB driver itself
- **HTTP clients** - Mock client interfaces, not individual HTTP calls
- **Message queues** - Mock producer/consumer interfaces (like `SyncProducer`)
- **Third-party services** - Mock client interfaces (like `sentry.Client`)

#### Interface Boundaries
- **Service interfaces** - Mock `Service`, `ResourceFetcher`, `ResourceSender` interfaces
- **Cross-cutting concerns** - Mock interfaces for logging, metrics, caching
- **I/O operations** - Mock file systems, network calls, external APIs

```go
// ✅ GOOD: Mock external dependency at interface boundary
mockSyncProducer := &kafkaMocks.SyncProducer{}
resourceSender := pkg.NewResourceSender(mockSyncProducer, realLogger)
```

### ❌ What NOT to Mock

#### Value Objects & Data Structures
- **Simple types** - Don't mock `string`, `int`, `time.Time`
- **Data containers** - Don't mock structs like `FetchResult`, `ProducerMessage`, `User`
- **Domain models** - Don't mock business entities that are just data holders

#### Standard Library & Utilities
- **Built-in functions** - Don't mock `json.Marshal`, `context.Background()`
- **Utility libraries** - Use real `log.DefaultSamplerFactory`, not mocks
- **Pure functions** - Don't mock stateless helper functions

#### Implementation Details
- **Internal parsing logic** - Use real implementations when they're stable
- **Key building functions** - Don't mock `PrimaryKeys.BuildKey()` - that's testing library internals
- **Complex business logic** - Test the real implementation, not a mock

```go
// ❌ BAD: Over-mocking simple utilities
mockLogSamplerFactory := &logMocks.SamplerFactory{}
mockJSONMarshaler := &mocks.JSONMarshaler{}

// ✅ GOOD: Use real implementations for stable utilities
resourceSender := pkg.NewResourceSender(
    mockSyncProducer,           // Mock external dependency
    log.DefaultSamplerFactory,  // Real stable utility
)
```

**Key points:**
- Mock external boundaries, use real internal implementations
- Don't mock what you don't own (standard library, third-party internals)
- Focus mocks on testing your business logic and integration points

## 3. Mock Discovery and Location Strategies

### Standard Mock Locations

```
# Project structure for mocks
./mocks/                           # Local project mocks
./vendor/.../mocks/                # Vendor library pre-existing mocks
lib/kafka/mocks/sync-producer.go   # Kafka ecosystem mocks
lib/sentry/mocks/sentry-client.go  # Sentry ecosystem mocks
github.com/bborbe/log/mocks/       # Log utility mocks
github.com/bborbe/[lib]/mocks/     # Other ecosystem library mocks
```

### Systematic Mock Discovery

Before creating new mocks, use this discovery strategy:

```bash
# 1. Check for existing mocks
ls **/mocks/*.go

# 2. Find counterfeiter generation directives
grep -r "counterfeiter:generate"

# 3. Check vendor directories for pre-existing mocks
find vendor -name "mocks" -type d

# 4. Look for existing test suite setup
find . -name "*suite_test.go" -exec grep -l "go:generate" {} \;
```

**Critical Process:**
1. **Check existing mocks first** - Many libraries already provide mocks
2. **Look for counterfeiter directives** - Understand current generation setup
3. **Check vendor directories** - Library mocks often pre-exist
4. **Generate only if missing** - Use `//counterfeiter:generate` comments

### Mock Location Examples

```go
// Ecosystem library mocks (often pre-exist)
import "github.com/bborbe/log/mocks"
import "lib/kafka/mocks"

// Local project mocks (generated)
import "your-project/mocks"

// Usage with mixed real/mock dependencies
service := pkg.NewOrderProcessor(
    &mocks.PaymentAPI{},           // Mock external service
    log.DefaultSamplerFactory,     // Real utility from ecosystem
    libtime.NewCurrentDateTime(),  // Real time utility
)
```

## 4. Interface Design for Mocking

### Interface-First Approach

Always define interfaces with counterfeiter generation comments:

```go
package service

import "context"

//counterfeiter:generate -o ../mocks/user-service.go --fake-name UserService . UserService
type UserService interface {
    GetUser(ctx context.Context, id string) (*User, error)
    CreateUser(ctx context.Context, user *User) error
    DeleteUser(ctx context.Context, id string) error
    FindUsers(ctx context.Context, filter func(User) bool) ([]User, error)
}

type User struct {
    ID   string `json:"id"`
    Name string `json:"name"`
    Email string `json:"email"`
}
```

**Key points:**
- All methods accept `context.Context` as first parameter
- Use descriptive interface names and method signatures
- Include counterfeiter generation directive
- Specify output directory and fake name clearly

### Implementation Pattern

```go
package service

import (
    "context"
    "github.com/bborbe/errors"
    libtime "github.com/bborbe/time"
)

type userService struct {
    db              DB
    validator       UserValidator
    currentDateTime libtime.CurrentDateTime
}

func NewUserService(
    db DB,
    validator UserValidator,
    currentDateTime libtime.CurrentDateTime,
) UserService {
    return &userService{
        db:              db,
        validator:       validator,
        currentDateTime: currentDateTime,
    }
}

func (s *userService) GetUser(ctx context.Context, id string) (*User, error) {
    if id == "" {
        return nil, errors.New(ctx, "user ID cannot be empty")
    }
    
    user, err := s.db.FindByID(ctx, id)
    if err != nil {
        return nil, errors.Wrap(ctx, err, "failed to find user")
    }
    
    return user, nil
}
```

## 5. Mock Generation Setup

### Project Structure

```
pkg/
├── service/
│   ├── user.go              # Interface definitions
│   ├── user_service.go      # Implementation
│   └── user_service_test.go # Tests
├── mocks/                   # Generated mocks directory
│   └── user-service.go      # Generated by counterfeiter
└── suite_test.go           # Ginkgo test suite setup
```

### Test Suite Setup

Create `suite_test.go` in your package root:

```go
package service_test

import (
    "testing"

    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
)

//go:generate go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate

func TestService(t *testing.T) {
    RegisterFailHandler(Fail)
    RunSpecs(t, "Service Suite")
}
```

**Key points:**
- `//go:generate` directive runs counterfeiter for all packages
- Ginkgo v2 test runner setup
- Generates all mocks when `go generate` is run

### Mock Generation Command

```bash
# Generate all mocks for the project
go generate ./...

# Or run counterfeiter directly
go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate
```

## 6. Mock Usage Patterns

### Basic Mock Setup

```go
package service_test

import (
    "context"
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
    "your-project/mocks"
    "your-project/service"
    libtime "github.com/bborbe/time"
    libtimetest "github.com/bborbe/time/test"
)

var _ = Describe("UserService", func() {
    var (
        ctx             context.Context
        userService     service.UserService
        mockDB          *mocks.DB
        mockValidator   *mocks.UserValidator
        currentDateTime libtime.CurrentDateTime
    )

    BeforeEach(func() {
        ctx = context.Background()
        
        // Create mocks
        mockDB = &mocks.DB{}
        mockValidator = &mocks.UserValidator{}
        
        // Setup fixed time for tests
        currentDateTime = libtime.NewCurrentDateTime()
        currentDateTime.SetNow(libtimetest.ParseDateTime("2023-12-25T00:00:00Z"))
        
        // Create service with mocked dependencies
        userService = service.NewUserService(mockDB, mockValidator, currentDateTime)
    })

    Describe("GetUser", func() {
        Context("when user exists", func() {
            It("returns the user", func() {
                // Arrange
                expectedUser := &service.User{
                    ID:   "user123",
                    Name: "John Doe",
                    Email: "john@example.com",
                }
                mockDB.FindByIDReturns(expectedUser, nil)
                
                // Act
                result, err := userService.GetUser(ctx, "user123")
                
                // Assert
                Expect(err).ToNot(HaveOccurred())
                Expect(result).To(Equal(expectedUser))
                
                // Verify mock interactions
                Expect(mockDB.FindByIDCallCount()).To(Equal(1))
                actualCtx, actualID := mockDB.FindByIDArgsForCall(0)
                Expect(actualCtx).To(Equal(ctx))
                Expect(actualID).To(Equal("user123"))
            })
        })
    })
})
```

### Mock Return Values

#### Simple Returns
```go
// Return same values for all calls
mockService.GetUserReturns(&User{ID: "123"}, nil)

// Return different values for specific calls
mockService.GetUserReturnsOnCall(0, &User{ID: "first"}, nil)
mockService.GetUserReturnsOnCall(1, &User{ID: "second"}, nil)
```

#### Stub Functions
```go
// Complex behavior with custom logic
mockService.FindUsersStub = func(ctx context.Context, filter func(User) bool) ([]User, error) {
    users := []User{
        {ID: "1", Name: "Alice"},
        {ID: "2", Name: "Bob"},
    }
    
    var filtered []User
    for _, user := range users {
        if filter(user) {
            filtered = append(filtered, user)
        }
    }
    
    return filtered, nil
}
```

### Mock Verification Patterns

#### Call Count Verification
```go
// Verify method was called
Expect(mockService.GetUserCallCount()).To(Equal(1))

// Verify method was never called
Expect(mockService.DeleteUserCallCount()).To(BeZero())

// Verify multiple calls
Expect(mockService.CreateUserCallCount()).To(Equal(3))
```

#### Argument Verification
```go
// Verify arguments for single call
actualCtx, actualID := mockService.GetUserArgsForCall(0)
Expect(actualCtx).To(Equal(ctx))
Expect(actualID).To(Equal("expected-id"))

// Verify arguments for multiple calls
for i := 0; i < mockService.CreateUserCallCount(); i++ {
    actualCtx, actualUser := mockService.CreateUserArgsForCall(i)
    Expect(actualCtx).To(Equal(ctx))
    Expect(actualUser).ToNot(BeNil())
}
```

## 7. Advanced Mock Patterns

### Error Testing
```go
Context("when database fails", func() {
    It("returns wrapped error", func() {
        // Arrange
        dbError := errors.New(ctx, "database connection failed")
        mockDB.FindByIDReturns(nil, dbError)
        
        // Act
        result, err := userService.GetUser(ctx, "user123")
        
        // Assert
        Expect(result).To(BeNil())
        Expect(err).To(HaveOccurred())
        Expect(err.Error()).To(ContainSubstring("failed to find user"))
        Expect(err.Error()).To(ContainSubstring("database connection failed"))
    })
})
```

### Sequence Testing
```go
Context("when called multiple times", func() {
    It("handles different responses", func() {
        // Arrange - setup different responses for each call
        mockDB.FindByIDReturnsOnCall(0, &User{ID: "1"}, nil)
        mockDB.FindByIDReturnsOnCall(1, nil, errors.New(ctx, "not found"))
        mockDB.FindByIDReturnsOnCall(2, &User{ID: "3"}, nil)
        
        // Act & Assert - first call succeeds
        user1, err1 := userService.GetUser(ctx, "1")
        Expect(err1).ToNot(HaveOccurred())
        Expect(user1.ID).To(Equal("1"))
        
        // Second call fails
        user2, err2 := userService.GetUser(ctx, "2")
        Expect(err2).To(HaveOccurred())
        Expect(user2).To(BeNil())
        
        // Third call succeeds
        user3, err3 := userService.GetUser(ctx, "3")
        Expect(err3).ToNot(HaveOccurred())
        Expect(user3.ID).To(Equal("3"))
    })
})
```

### Integration Testing with Mixed Dependencies

```go
var _ = Describe("OrderService Integration", func() {
    var (
        ctx              context.Context
        orderService     service.OrderService
        realDB           *bolt.DB  // Real database for persistence
        mockPayment      *mocks.PaymentAPI
        mockNotifier     *mocks.NotificationService
        currentDateTime  libtime.CurrentDateTime
    )

    BeforeEach(func() {
        ctx = context.Background()
        
        // Setup real database
        var err error
        realDB, err = bolt.Open(":memory:", 0600, nil)
        Expect(err).ToNot(HaveOccurred())
        
        // Setup mocks for external services
        mockPayment = &mocks.PaymentAPI{}
        mockNotifier = &mocks.NotificationService{}
        
        currentDateTime = libtime.NewCurrentDateTime()
        currentDateTime.SetNow(libtimetest.ParseDateTime("2023-12-25T00:00:00Z"))
        
        // Create service with mixed dependencies
        orderService = service.NewOrderService(
            realDB,               // Real database
            mockPayment,          // Mock payment service
            mockNotifier,         // Mock notifier
            currentDateTime,
        )
    })

    AfterEach(func() {
        realDB.Close()
    })

    Context("when processing order", func() {
        It("integrates real and mock components", func() {
            // Arrange
            mockPayment.ProcessPaymentReturns(&PaymentResult{
                TransactionID: "tx123",
                Status:       "success",
            }, nil)
            
            order := &Order{
                ID:       "order123",
                Amount:   100.50,
                UserID:   "user456",
            }
            
            // Act
            result, err := orderService.ProcessOrder(ctx, order)
            
            // Assert
            Expect(err).ToNot(HaveOccurred())
            Expect(result.TransactionID).To(Equal("tx123"))
            
            // Verify mock interactions
            Expect(mockPayment.ProcessPaymentCallCount()).To(Equal(1))
            actualCtx, actualRequest := mockPayment.ProcessPaymentArgsForCall(0)
            Expect(actualCtx).To(Equal(ctx))
            Expect(actualRequest.Amount).To(Equal(100.50))
            
            // Verify notifications were sent
            Expect(mockNotifier.NotifyCallCount()).To(Equal(1))
            notifyCtx, message := mockNotifier.NotifyArgsForCall(0)
            Expect(notifyCtx).To(Equal(ctx))
            Expect(message).To(ContainSubstring("order123"))
            
            // Verify data was persisted (real database)
            storedOrder, err := orderService.GetOrder(ctx, "order123")
            Expect(err).ToNot(HaveOccurred())
            Expect(storedOrder.ID).To(Equal("order123"))
        })
    })
})
```

## 8. Mock Management Best Practices

### 1. Mock Generation Policy

**CRITICAL RULES:**

- **Never create manual mock classes** - always use Counterfeiter
- **Ask users where mocks are located** if you can't find existing ones  
- **Only add counterfeiter comments to current service interfaces**
- **Look for existing `*_suite_test.go` files** to understand mock setup
- **All mocks must be in `mocks/` directory** and generated via Counterfeiter

### 2. Mock Lifecycle

```go
BeforeEach(func() {
    // Create fresh mocks for each test
    mockService = &mocks.UserService{}
    
    // Reset any shared state
    ctx = context.Background()
})

AfterEach(func() {
    // Verify no unexpected interactions
    // This happens automatically with Ginkgo cleanup
})
```

### 3. Mock Verification Strategy

```go
// GOOD: Verify both behavior and interactions
It("processes user correctly", func() {
    // Arrange
    mockValidator.ValidateReturns(nil)
    
    // Act
    err := userService.ProcessUser(ctx, user)
    
    // Assert behavior
    Expect(err).ToNot(HaveOccurred())
    
    // Verify interactions
    Expect(mockValidator.ValidateCallCount()).To(Equal(1))
    actualCtx, actualUser := mockValidator.ValidateArgsForCall(0)
    Expect(actualCtx).To(Equal(ctx))
    Expect(actualUser).To(Equal(user))
})
```

### 4. Time Handling in Mocks

```go
BeforeEach(func() {
    // Setup consistent time for all tests
    currentDateTime = libtime.NewCurrentDateTime()
    currentDateTime.SetNow(libtimetest.ParseDateTime("2023-12-25T00:00:00Z"))
    
    // Create service with fixed time
    userService = service.NewUserService(mockDB, currentDateTime)
})
```

## 9. Common Antipatterns to Avoid

### DON'T: Create Manual Mock Classes
```go
// DON'T DO THIS
type MockUserService struct {
    GetUserFunc func(context.Context, string) (*User, error)
    calls       []string
}

func (m *MockUserService) GetUser(ctx context.Context, id string) (*User, error) {
    m.calls = append(m.calls, "GetUser")
    if m.GetUserFunc != nil {
        return m.GetUserFunc(ctx, id)
    }
    return nil, nil
}
```

```go
// DO THIS instead - use Counterfeiter
//counterfeiter:generate -o ../mocks/user-service.go --fake-name UserService . UserService
type UserService interface {
    GetUser(ctx context.Context, id string) (*User, error)
}

// In tests:
mockService := &mocks.UserService{}
```

### DON'T: Skip Mock Verification
```go
// DON'T DO THIS - no verification
It("calls service", func() {
    mockService.ProcessReturns(nil)
    
    err := handler.Handle(ctx, request)
    
    Expect(err).ToNot(HaveOccurred())
    // Missing: verify Process was called with correct arguments
})
```

```go
// DO THIS - verify mock interactions
It("calls service with correct parameters", func() {
    mockService.ProcessReturns(nil)
    
    err := handler.Handle(ctx, request)
    
    Expect(err).ToNot(HaveOccurred())
    Expect(mockService.ProcessCallCount()).To(Equal(1))
    actualCtx, actualRequest := mockService.ProcessArgsForCall(0)
    Expect(actualCtx).To(Equal(ctx))
    Expect(actualRequest).To(Equal(request))
})
```

### DON'T: Use Shared Mock State
```go
// DON'T DO THIS - shared mock state
var sharedMock = &mocks.UserService{}

var _ = Describe("UserHandler", func() {
    It("test 1", func() {
        sharedMock.GetUserReturns(user1, nil)
        // Test logic
    })
    
    It("test 2", func() {
        // Previous test's setup affects this test!
        sharedMock.GetUserReturns(user2, nil)
        // Test logic
    })
})
```

```go
// DO THIS - fresh mocks per test
var _ = Describe("UserHandler", func() {
    var mockService *mocks.UserService
    
    BeforeEach(func() {
        mockService = &mocks.UserService{}
        handler = NewUserHandler(mockService)
    })
    
    It("test 1", func() {
        mockService.GetUserReturns(user1, nil)
        // Clean test with fresh mock
    })
    
    It("test 2", func() {
        mockService.GetUserReturns(user2, nil)
        // Clean test with fresh mock
    })
})
```

### DON'T: Over-Mock Internal Dependencies
```go
// DON'T DO THIS - mocking internal utilities
mockTime := &mocks.TimeProvider{}
mockLogger := &mocks.Logger{}
mockConfig := &mocks.Config{}

service := NewUserService(mockDB, mockTime, mockLogger, mockConfig)
```

```go
// DO THIS - mock only external dependencies, use real internal ones
realTime := libtime.NewCurrentDateTime()
realLogger := log.NewLogger()
realConfig := config.New()

service := NewUserService(mockExternalAPI, realTime, realLogger, realConfig)
```

## 10. Integration with Makefile Commands

### Standard Makefile Targets

```makefile
.PHONY: generate test

generate:
	go generate ./...
	
test: generate
	ginkgo -r --randomizeAllSpecs --randomizeSuites --race --trace

precommit: generate test
	# Ensures mocks are up to date before commit
```

**Key points:**
- `make generate` creates/updates all mocks
- `make test` runs after generation to ensure consistency
- `make precommit` includes mock generation verification

## 11. Directory Structure Best Practices

```
project/
├── cmd/
│   └── main.go
├── pkg/
│   ├── service/
│   │   ├── user.go              # Interface definitions
│   │   ├── user_service.go      # Implementation
│   │   └── user_service_test.go # Tests with mocks
│   ├── api/
│   │   ├── handler.go
│   │   └── handler_test.go
│   └── suite_test.go           # Test suite with generate directive
├── mocks/                       # All generated mocks
│   ├── user-service.go
│   ├── payment-api.go
│   └── notification-service.go
├── go.mod
├── go.sum
└── Makefile
```

**Critical Notes:**
- All mocks in single `mocks/` directory at project root
- Test files alongside implementation files
- Single `suite_test.go` with `//go:generate` directive
- Generated mocks are committed to repository
- Makefile ensures mocks stay current

## Summary: Mock Boundaries, Not Implementation

**Key Takeaway**: Mock external boundaries, use real internal implementations. This approach:

- **Keeps tests realistic** - Tests behave like production code
- **Reduces maintenance** - Fewer mocks to update when internals change  
- **Improves reliability** - Real utilities are more stable than mocks
- **Focuses testing** - Tests verify your business logic, not library behavior

**Quick Decision Guide:**
- External service/database? → **Mock the interface**
- Standard library function? → **Use real implementation**  
- Your business logic? → **Test real implementation**
- Unstable dependency? → **Mock at boundary**
- Simple utility? → **Use real implementation**

This comprehensive mocking guide ensures consistent, testable Go services with proper mock generation, usage, and verification patterns throughout the development ecosystem.