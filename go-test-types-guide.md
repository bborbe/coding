# Go Test Types Guide

This guide defines **what** each test type is, **when** to use it, and **what dependencies** are appropriate. For **how to write tests** with Ginkgo/Gomega syntax, see [go-testing-guide.md](go-testing-guide.md). For **mocking strategies**, see [go-mocking-guide.md](go-mocking-guide.md).

All tests use Ginkgo v2 + Gomega and follow the same file naming conventions, distinguished by their dependency patterns rather than separate files or build tags.

## Table of Contents

1. [Overview](#overview)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [End-to-End Tests](#end-to-end-tests)
5. [Decision Framework](#decision-framework)
6. [Test Organization](#test-organization)
7. [Common Antipatterns](#common-antipatterns)

## Overview

### Test Type Philosophy

All tests live in standard `*_test.go` files within the same test suite. There are **no separate files** for different test types, **no build tags**, and **no Ginkgo labels**. Test types are distinguished solely by their **dependency patterns**.

### The Three Test Types

| Test Type | Scope | Dependencies | Purpose | Speed | Runs with `make test`? |
|-----------|-------|-------------|---------|-------|------------------------|
| **Unit** | Single file/component | All mocked (Counterfeiter fakes) | Validate business logic in isolation | ⚡ Fast (ms) | ✅ Yes |
| **Integration** | Multiple files/components | In-memory/in-process only (no external resources) | Validate component interactions | ⚙️ Medium (seconds) | ✅ Yes |
| **End-to-End** | Full system | External resources (DB servers, APIs, K8s) | Validate complete workflows | 🐢 Slow (minutes) | ❌ No (explicit only) |

### Key Principle: The Testing Pyramid

```
     /\
    /E2E\      ← Few, critical user flows only
   /------\
  /  Integ \   ← Component boundaries, data layer
 /----------\
/    Unit    \  ← Most tests here: business logic
--------------
```

**Critical rule:** Most tests should be unit tests. Integration and E2E tests are **supplements**, not replacements.

### What "External" Means

**External resources** (E2E test territory):
- Database servers (PostgreSQL, MySQL, MongoDB running as separate processes)
- HTTP calls to external APIs over the network
- Kubernetes clusters or Docker containers
- Message brokers (Kafka, RabbitMQ running as separate services)
- Cloud services (AWS, GCP, Azure)

**In-memory/In-process resources** (Integration test territory):
- `libbadgerkv.OpenMemory()` - in-process database
- `libmemorykv.OpenMemory()` - in-process key-value store
- `libboltkv.OpenTemp()` - temporary local file (no network)
- Real data types (`http.Response`, `sarama.ConsumerMessage`)
- Utility libraries (`libtime`, `math`, `encoding/json`)

**The key distinction:** If it requires a network call or separate process, it's external. If it runs in the same process as your test, it's in-memory.

## Unit Tests

### What Unit Tests ARE

Unit tests validate **business logic of a single file/component** by:
- Testing a single component in isolation (one struct, function, or method)
- Mocking **all dependencies** using Counterfeiter fakes
- Running entirely in memory with no I/O
- Executing in milliseconds
- Being fully deterministic and repeatable

### What Unit Tests ARE NOT

Unit tests do **NOT**:
- Test multiple files/components together
- Use databases (even in-memory ones)
- Make any network calls
- Access the filesystem
- Depend on other tests or shared state

### When to Write Unit Tests

Write unit tests to validate:
- Business logic and calculations
- Validation rules and error handling
- State transitions and workflows
- Algorithm correctness
- Data transformations
- Retry and backoff logic
- Message parsing and serialization

### Unit Test Pattern

```go
// pkg/user-service_test.go
package pkg_test

import (
	"context"
	"errors"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/myorg/myapp/pkg"
	"github.com/myorg/myapp/pkg/mocks"
)

var _ = Describe("UserServiceRetry", func() {
	var ctx context.Context
	var err error
	var mockUserService *mocks.UserService  // ALL dependencies mocked
	var maxRetries int
	var result *domain.User

	BeforeEach(func() {
		ctx = context.Background()
		mockUserService = &mocks.UserService{}  // Counterfeiter mock
		maxRetries = 1
	})

	JustBeforeEach(func() {
		userServiceRetry := pkg.NewUserServiceRetry(
			run.Backoff{
				Retries: maxRetries,
				Delay:   0,
			},
			mockUserService,
		)
		result, err = userServiceRetry.GetUser(ctx, "user-123")
	})

	Context("successful fetch", func() {
		BeforeEach(func() {
			mockUserService.GetUserReturns(&domain.User{
				ID:    "user-123",
				Email: "john@example.com",
			}, nil)
		})

		It("returns no error", func() {
			Expect(err).To(BeNil())
		})

		It("returns user", func() {
			Expect(result).NotTo(BeNil())
			Expect(result.Email).To(Equal("john@example.com"))
		})

		It("calls fetch once", func() {
			Expect(mockUserService.GetUserCallCount()).To(Equal(1))
		})
	})

	Context("fetch fails with retries", func() {
		BeforeEach(func() {
			maxRetries = 3
			mockUserService.GetUserReturnsOnCall(0, nil, errors.New("network error"))
			mockUserService.GetUserReturnsOnCall(1, nil, errors.New("network error"))
			mockUserService.GetUserReturnsOnCall(2, &domain.User{ID: "user-123"}, nil)
		})

		It("returns no error after retry", func() {
			Expect(err).To(BeNil())
		})

		It("retries exactly 3 times", func() {
			Expect(mockUserService.GetUserCallCount()).To(Equal(3))
		})
	})
})
```

**Key points:**
- Import from `mocks` package for all dependencies
- Use `Returns()` and `ReturnsOnCall()` to control behavior
- Verify call counts and arguments with `CallCount()` and `ArgsForCall()`
- No real I/O - everything is mocked
- Fast execution (milliseconds)

## Integration Tests

### What Integration Tests ARE

Integration tests validate **how multiple files/components work together** by:
- Testing multiple internal components as a unit (across multiple files)
- Using **in-memory/in-process resources** (in-memory BadgerDB/BoltDB/MemoryKV)
- Using **real data structures** (HTTP response types, Kafka message types)
- Verifying persistence, transactions, and state management
- Testing at component boundaries (repositories, stores, handlers)
- Running in-process with no external network calls

### What Integration Tests ARE NOT

Integration tests do **NOT**:
- Call real external APIs or services (no network calls)
- Connect to external database servers (no PostgreSQL/MySQL containers)
- Make HTTP calls to external services
- Connect to real Kubernetes clusters
- Require Docker containers or external processes
- Test end-to-end user workflows

### When to Write Integration Tests

Write integration tests to validate:
- Database operations (CRUD, transactions, queries)
- Data serialization and deserialization
- Message handling and parsing
- Transaction semantics (commit/rollback)
- Multi-component workflows within boundaries
- Repository and store implementations

### Integration Test Pattern: Database Operations

```go
// pkg/user-store_test.go
package pkg_test

import (
	"context"

	libbadgerkv "github.com/bborbe/badgerkv"  // REAL database
	libkv "github.com/bborbe/kv"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/myorg/myapp/pkg"
	"github.com/myorg/myapp/domain"
)

var _ = Describe("UserStore", func() {
	var ctx context.Context
	var err error
	var userStore pkg.UserStore
	var userID string
	var db libkv.DB  // REAL in-memory database

	BeforeEach(func() {
		ctx = context.Background()
		userID = "user-123"
		db, err = libbadgerkv.OpenMemory(ctx)  // Real database instance
		Expect(err).To(BeNil())
		userStore = pkg.NewUserStore(db)
	})

	AfterEach(func() {
		if db != nil {
			_ = db.Close()
		}
	})

	Context("Get", func() {
		var user *domain.User

		JustBeforeEach(func() {
			user, err = userStore.Get(ctx, userID)
		})

		Context("user exists", func() {
			BeforeEach(func() {
				err = userStore.Save(ctx, domain.User{
					ID:    userID,
					Name:  "John Doe",
					Email: "john@example.com",
				})
				Expect(err).To(BeNil())
			})

			It("returns no error", func() {
				Expect(err).To(BeNil())
			})

			It("returns correct user", func() {
				Expect(user).NotTo(BeNil())
				Expect(user.ID).To(Equal(userID))
				Expect(user.Name).To(Equal("John Doe"))
			})
		})

		Context("user not found", func() {
			It("returns not found error", func() {
				Expect(err).NotTo(BeNil())
				Expect(err.Error()).To(ContainSubstring("not found"))
			})
		})
	})
})
```

**Key points:**
- Use `libbadgerkv.OpenMemory()` or `libmemorykv.OpenMemory()` for real database
- Test actual persistence and retrieval
- Verify transaction semantics
- Clean up database in `AfterEach`
- Still fast (seconds, not minutes)

### Integration Test Pattern: Transactions

```go
// pkg/order-store_test.go
package pkg_test

import (
	"context"
	"errors"

	libbadgerkv "github.com/bborbe/badgerkv"
	libkv "github.com/bborbe/kv"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/myorg/myapp/pkg"
	"github.com/myorg/myapp/domain"
)

var _ = Describe("OrderStore", func() {
	var ctx context.Context
	var err error
	var orderStore pkg.OrderStore
	var orderID string
	var db libkv.DB

	BeforeEach(func() {
		ctx = context.Background()
		db, err = libbadgerkv.OpenMemory(ctx)
		Expect(err).To(BeNil())
		orderID = "order-123"
		orderStore = pkg.NewOrderStore()
	})

	AfterEach(func() {
		if db != nil {
			_ = db.Close()
		}
	})

	Context("transaction commit", func() {
		var order *domain.Order

		JustBeforeEach(func() {
			// Use real transaction API
			err = db.View(ctx, func(ctx context.Context, tx libkv.Tx) error {
				order, err = orderStore.Get(ctx, tx, orderID)
				return err
			})
		})

		Context("after successful write", func() {
			BeforeEach(func() {
				err = db.Update(ctx, func(ctx context.Context, tx libkv.Tx) error {
					return orderStore.Save(ctx, tx, domain.Order{
						ID:       orderID,
						Product:  "Widget",
						Quantity: 5,
						Status:   domain.StatusPending,
					})
				})
				Expect(err).To(BeNil())
			})

			It("retrieves persisted order", func() {
				Expect(order).NotTo(BeNil())
				Expect(order.ID).To(Equal(orderID))
				Expect(order.Product).To(Equal("Widget"))
				Expect(order.Status).To(Equal(domain.StatusPending))
			})
		})
	})

	Context("transaction rollback", func() {
		It("does not persist on error", func() {
			err := db.Update(ctx, func(ctx context.Context, tx libkv.Tx) error {
				err := orderStore.Save(ctx, tx, domain.Order{
					ID:      orderID,
					Product: "Widget",
				})
				Expect(err).To(BeNil())

				// Force rollback
				return errors.New("rollback")
			})
			Expect(err).NotTo(BeNil())

			// Verify data was not persisted
			var order *domain.Order
			err = db.View(ctx, func(ctx context.Context, tx libkv.Tx) error {
				order, err = orderStore.Get(ctx, tx, orderID)
				return err
			})
			Expect(err).NotTo(BeNil())
			Expect(order).To(BeNil())
		})
	})
})
```

**Key points:**
- Test real transaction commit/rollback behavior
- Use `db.Update()` and `db.View()` with real transaction API
- Verify data persistence across transaction boundaries
- Test error handling in transactions

### Integration Test Pattern: Message Handling

```go
// pkg/user-event-handler_test.go
package pkg_test

import (
	"context"

	"github.com/IBM/sarama"  // REAL Kafka message types
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"github.com/myorg/myapp/pkg"
	"github.com/myorg/myapp/pkg/mocks"
)

var _ = Describe("UserEventHandler", func() {
	var ctx context.Context
	var err error
	var eventHandler pkg.MessageHandler
	var consumerMessage *sarama.ConsumerMessage  // REAL Kafka message
	var mockEventPublisher *mocks.EventPublisher  // MOCKED publisher

	BeforeEach(func() {
		ctx = context.Background()
		consumerMessage = &sarama.ConsumerMessage{}
		mockEventPublisher = &mocks.EventPublisher{}
		eventHandler = pkg.NewUserEventHandler(mockEventPublisher)
	})

	Context("ConsumeMessage", func() {
		JustBeforeEach(func() {
			err = eventHandler.ConsumeMessage(ctx, consumerMessage)
		})

		Context("valid user update", func() {
			BeforeEach(func() {
				consumerMessage = &sarama.ConsumerMessage{
					Key:   []byte("user-123"),
					Value: []byte(`{"name":"John Doe","email":"john@example.com","active":true}`),
				}
			})

			It("returns no error", func() {
				Expect(err).To(BeNil())
			})

			It("publishes update event", func() {
				Expect(mockEventPublisher.PublishCallCount()).To(Equal(1))
			})

			It("publishes correct user data", func() {
				_, _, user := mockEventPublisher.PublishArgsForCall(0)
				Expect(user.Name).To(Equal("John Doe"))
				Expect(user.Email).To(Equal("john@example.com"))
			})
		})

		Context("invalid JSON", func() {
			BeforeEach(func() {
				consumerMessage = &sarama.ConsumerMessage{
					Value: []byte(`{invalid json`),
				}
			})

			It("returns error", func() {
				Expect(err).NotTo(BeNil())
				Expect(err.Error()).To(ContainSubstring("unmarshal"))
			})
		})
	})
})
```

**Key points:**
- Use real message types (`sarama.ConsumerMessage`)
- Test actual message parsing and deserialization
- Mock external senders/publishers
- Validate both success and error paths

## End-to-End Tests

### What E2E Tests ARE

End-to-end tests validate **complete user workflows with external dependencies** by:
- Running the full application stack
- Using **real external resources** (database servers, message brokers, APIs)
- Making actual HTTP/gRPC requests over the network
- Connecting to real Kubernetes clusters or Docker containers
- Testing critical business flows from start to finish
- Verifying system behavior in realistic production-like conditions

### What E2E Tests ARE NOT

E2E tests do **NOT**:
- Replace unit or integration tests
- Test every possible scenario (only critical paths)
- Focus on implementation details
- Run automatically with `make test` (run explicitly only)
- Run in CI for every commit (often in separate pipeline)

### When to Write E2E Tests

Write E2E tests for:
- Critical user journeys (signup, checkout, payment flow)
- Multi-system integrations
- Compliance and regulatory requirements
- Smoke tests for production deployments
- Disaster recovery scenarios

### E2E Test Pattern

```go
// Example: Full e-commerce checkout workflow E2E test
var _ = Describe("E2E: Checkout Workflow", func() {
	var ctx context.Context
	var apiClient *http.Client
	var baseURL string

	BeforeSuite(func() {
		// Start full stack (Docker Compose, k3s, etc.)
		baseURL = "http://localhost:8080"
		apiClient = &http.Client{Timeout: 30 * time.Second}
	})

	AfterSuite(func() {
		// Tear down full stack
	})

	Context("complete order checkout", func() {
		var orderID string

		It("creates new order", func() {
			resp, err := apiClient.Post(
				baseURL+"/api/orders",
				"application/json",
				bytes.NewBuffer([]byte(`{
					"product": "Widget",
					"quantity": 2,
					"price": 29.99
				}`)),
			)
			Expect(err).To(BeNil())
			Expect(resp.StatusCode).To(Equal(http.StatusCreated))

			var order Order
			err = json.NewDecoder(resp.Body).Decode(&order)
			Expect(err).To(BeNil())
			orderID = order.ID
		})

		It("processes payment", func() {
			resp, err := apiClient.Post(
				baseURL+"/api/orders/"+orderID+"/payment",
				"application/json",
				bytes.NewBuffer([]byte(`{"amount": 59.98}`)),
			)
			Expect(err).To(BeNil())
			Expect(resp.StatusCode).To(Equal(http.StatusOK))
		})

		It("confirms order status", func() {
			resp, err := apiClient.Get(
				baseURL + "/api/orders/" + orderID,
			)
			Expect(err).To(BeNil())

			var order Order
			err = json.NewDecoder(resp.Body).Decode(&order)
			Expect(err).To(BeNil())
			Expect(order.Status).To(Equal("CONFIRMED"))
		})
	})
})
```

**Key points:**
- Requires full environment setup
- Tests real HTTP/gRPC APIs
- Validates complete workflows
- Slow execution (minutes)
- Limited coverage of critical paths only

## Decision Framework

### When to Write Each Test Type

```
┌─────────────────────────────────────────────────────────┐
│ START: What are you testing?                           │
└─────────────────────────────────────────────────────────┘
                         │
                         ├─ Single file/component with business logic?
                         │  → UNIT TEST (all mocked, one file)
                         │
                         ├─ Multiple files/components together (in-process)?
                         │  → INTEGRATION TEST (in-memory DB, no network)
                         │
                         ├─ Database operations across multiple components?
                         │  → INTEGRATION TEST (in-memory DB)
                         │
                         ├─ Message parsing with multiple handlers?
                         │  → INTEGRATION TEST (real types, multiple files)
                         │
                         ├─ External API calls or database servers?
                         │  → E2E TEST (real external resources)
                         │
                         └─ Complete user workflow with external services?
                            → E2E TEST (full stack with network)
```

### Specific Scenarios

| Scenario | Test Type | Scope | Dependencies |
|----------|-----------|-------|--------------|
| Validate discount calculation | Unit | Single file | All mocked |
| Test retry logic with backoff | Unit | Single file | Mock client, real backoff |
| Save/retrieve from database | Integration | Multiple files | In-memory DB (no external DB server) |
| Transaction commit/rollback | Integration | Multiple files | In-memory DB |
| Parse Kafka message + store | Integration | Multiple files | In-memory DB, real message types |
| HTTP response parsing + storage | Integration | Multiple files | In-memory DB, real response types |
| Multi-step order processing | Integration | Multiple files | In-memory DB (no external services) |
| Call external API endpoint | E2E | Full system | Real HTTP calls to external services |
| Connect to PostgreSQL database | E2E | Full system | Real external database server |
| Complete checkout flow | E2E | Full system | External DB, APIs, services |

### The "Mock vs Real" Decision Tree

```
For each dependency, ask:

1. Is it external (network call, external DB server, external API)?
   YES → This is E2E test territory (or mock it for integration test)
   NO  → Continue...

2. Are you testing a single file/component?
   YES → UNIT TEST: Mock all dependencies
   NO  → Continue...

3. Are you testing multiple files/components together?
   YES → INTEGRATION TEST: Use in-memory/in-process resources

   For each dependency in integration test:
   - Database needed? → Use in-memory (libbadgerkv.OpenMemory)
   - Message types? → Use real types (sarama.ConsumerMessage)
   - HTTP types? → Use real types (http.Response)
   - External API call? → MOCK IT (no network in integration tests)
   - Utility library? → Use REAL (libtime, math, parsing)

4. Does it require real external resources (DB server, K8s, external API)?
   YES → E2E TEST: Real external dependencies with network calls
```

## Test Organization

### File Structure

All test types coexist in the same files:

```
pkg/
├── user-service.go
├── user-service_test.go        ← Unit + Integration tests together
├── pkg_suite_test.go           ← Suite setup with //go:generate
└── mocks/
    ├── user-service.go         ← Generated by counterfeiter
    └── user-repository.go
```

### Test Suite Setup

Every package has exactly one suite file:

```go
// pkg_suite_test.go
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

### Running Tests

```bash
# Run all tests (unit + integration together) - default behavior
make test

# Run tests for specific package
ginkgo run pkg/

# Run tests matching pattern
ginkgo -focus="UserStore" ./...

# Generate mocks before testing
go generate ./...

# Full precommit (includes tests)
make precommit

# E2E tests are NOT run by default - must be run explicitly
# (separate pipeline, manual trigger, or dedicated make target)
```

**Critical notes:**
- `make test` runs **both unit AND integration tests** together (default behavior)
- Unit and integration tests are **NOT separated** - they run together
- E2E tests are **NEVER run automatically** - they must be triggered explicitly
- This ensures fast CI/CD feedback loops while keeping comprehensive coverage

## Common Antipatterns

### ❌ DON'T: Mock Everything in Integration Tests

```go
// BAD: Integration test with all mocks (this is actually a unit test!)
var _ = Describe("UserStore Integration", func() {
	var mockDB *mocks.DB        // WRONG: Mocked database
	var mockTx *mocks.Tx        // WRONG: Mocked transaction

	BeforeEach(func() {
		mockDB = &mocks.DB{}
		mockTx = &mocks.Tx{}
		mockDB.UpdateReturns(nil)
	})

	// This is a unit test pretending to be integration!
})
```

```go
// GOOD: Real database for integration test
var _ = Describe("UserStore Integration", func() {
	var db libkv.DB              // REAL database

	BeforeEach(func() {
		db, err = libbadgerkv.OpenMemory(ctx)  // REAL in-memory DB
		Expect(err).To(BeNil())
	})

	AfterEach(func() {
		_ = db.Close()
	})
})
```

### ❌ DON'T: Use Real External APIs in Tests

```go
// BAD: Calling real external API
var _ = Describe("WeatherService", func() {
	It("fetches from production API", func() {
		// WRONG: Makes real HTTP call to external service
		data, err := fetcher.Fetch("https://api.weather.com/current")
		Expect(err).To(BeNil())
	})
})
```

```go
// GOOD: Mock external API client
var _ = Describe("WeatherService", func() {
	var mockAPIClient *mocks.APIClient

	BeforeEach(func() {
		mockAPIClient = &mocks.APIClient{}
		mockAPIClient.GetReturns(&http.Response{
			StatusCode: http.StatusOK,
			Body:       io.NopCloser(bytes.NewBufferString(`{"temp":72,"conditions":"sunny"}`)),
		}, nil)
	})
})
```

### ❌ DON'T: Write Integration Tests for Business Logic

```go
// BAD: Integration test for pure calculation
var _ = Describe("DiscountCalculator", func() {
	var db libkv.DB  // WRONG: No database needed!

	BeforeEach(func() {
		db, _ = libbadgerkv.OpenMemory(ctx)
	})

	It("calculates 10% discount", func() {
		result := CalculateDiscount(100.0, 0.1)  // Pure function!
		Expect(result).To(Equal(90.0))
	})
})
```

```go
// GOOD: Unit test for pure business logic
var _ = Describe("DiscountCalculator", func() {
	It("calculates 10% discount", func() {
		result := CalculateDiscount(100.0, 0.1)
		Expect(result).To(Equal(90.0))
	})
	// No database, no mocks - just pure logic
})
```

### ❌ DON'T: Test Implementation Details

```go
// BAD: Testing internal implementation
var _ = Describe("OrderProcessor", func() {
	var mockValidator *mocks.Validator

	It("calls validation exactly twice", func() {
		processor.Process(order)
		Expect(mockValidator.ValidateCallCount()).To(Equal(2))  // BRITTLE
	})
})
```

```go
// GOOD: Test behavior, not implementation
var _ = Describe("OrderProcessor", func() {
	var mockValidator *mocks.Validator

	Context("with invalid order", func() {
		BeforeEach(func() {
			mockValidator.ValidateReturns(errors.New("invalid"))
		})

		It("returns validation error", func() {
			err := processor.Process(order)
			Expect(err).To(MatchError(ContainSubstring("invalid")))
		})
	})
})
```

### ❌ DON'T: Depend on Test Execution Order

```go
// BAD: Tests depend on each other
var globalOrder Order

It("creates order", func() {
	globalOrder = CreateOrder()  // WRONG: Side effect
})

It("processes order", func() {
	err := Process(globalOrder)  // WRONG: Depends on previous test
	Expect(err).To(BeNil())
})
```

```go
// GOOD: Independent tests
var _ = Describe("OrderProcessor", func() {
	var order Order

	BeforeEach(func() {
		order = CreateTestOrder()  // Fresh for each test
	})

	It("creates order", func() {
		err := store.Save(ctx, order)
		Expect(err).To(BeNil())
	})

	It("processes order", func() {
		err := processor.Process(ctx, order)
		Expect(err).To(BeNil())
	})
})
```

### ❌ DON'T: Mix Multiple Test Types in One Test

```go
// BAD: Mixing unit and integration concerns
var _ = Describe("UserHandler", func() {
	var mockClient *mocks.APIClient
	var db libkv.DB  // CONFUSING: Mixed concerns

	It("fetches and stores user", func() {
		mockClient.FetchReturns(user, nil)  // Unit test behavior
		err := handler.Handle(ctx)

		// Then checks real database
		stored, _ := db.Get(ctx, userID)  // Integration test behavior
		Expect(stored).NotTo(BeNil())
	})
})
```

```go
// GOOD: Separate unit and integration tests
var _ = Describe("UserHandler", func() {
	Context("unit test: fetch logic", func() {
		var mockClient *mocks.APIClient
		var mockStore *mocks.UserStore

		BeforeEach(func() {
			mockClient = &mocks.APIClient{}
			mockStore = &mocks.UserStore{}
		})

		It("calls client and store", func() {
			mockClient.FetchReturns(user, nil)
			err := handler.Handle(ctx)
			Expect(mockStore.SaveCallCount()).To(Equal(1))
		})
	})

	Context("integration test: persistence", func() {
		var db libkv.DB

		BeforeEach(func() {
			db, _ = libbadgerkv.OpenMemory(ctx)
		})

		It("stores user in database", func() {
			err := store.Save(ctx, user)
			Expect(err).To(BeNil())

			retrieved, err := store.Get(ctx, user.ID)
			Expect(retrieved).To(Equal(user))
		})
	})
})
```

## Summary

### Quick Reference

**Unit Tests:**
- ✅ Single file/component scope
- ✅ All dependencies mocked with Counterfeiter
- ✅ Business logic, calculations, validation
- ✅ Fast execution (milliseconds)
- ✅ Runs with `make test`
- ❌ No databases or multiple components

**Integration Tests:**
- ✅ Multiple files/components together
- ✅ In-memory databases (`libbadgerkv.OpenMemory()`) - no external DB servers
- ✅ Real data types (Kafka, HTTP) but mocked external services
- ✅ Component boundaries and persistence
- ✅ Runs with `make test`
- ❌ No external network calls or resources

**End-to-End Tests:**
- ✅ Full running system with external dependencies
- ✅ Real external database servers (PostgreSQL, MySQL)
- ✅ Real HTTP/gRPC calls to external APIs
- ✅ Real Kubernetes clusters or Docker containers
- ✅ Critical user workflows only
- ❌ Does NOT run with `make test` - explicit execution only
- ❌ Not a replacement for unit/integration tests

### Test Type Selection Checklist

Before writing a test, ask:

1. **Am I testing a single file/component?** → Unit test (all mocked)
2. **Am I testing multiple files/components together?** → Integration test (in-memory only)
3. **Does this need an external resource (DB server, external API)?** → E2E test (explicit only)
4. **Does this require in-memory database?** → Integration test (not unit)
5. **Is this testing implementation details?** → Refactor to test behavior
6. **Can this run fast without network calls?** → Unit or Integration (not E2E)

### The Golden Rule

> **Unit and Integration tests run together with `make test` and must be fast.**
>
> **E2E tests require external resources and only run when explicitly triggered.**

By following these patterns, you'll build a comprehensive, fast, and maintainable test suite that provides confidence in your code while keeping CI/CD pipelines fast and reliable.
