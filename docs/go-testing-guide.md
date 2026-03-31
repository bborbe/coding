# Go Testing Guide

This comprehensive guide covers **how to write tests** using the Go testing framework. For understanding **what type of test to write** and **when**, see [go-test-types-guide.md](go-test-types-guide.md). For **mocking strategies**, see [go-mocking-guide.md](go-mocking-guide.md).

The testing framework is built on **Ginkgo v2** (BDD) with **Gomega** matchers, focusing on readable, maintainable, and comprehensive tests.

## Table of Contents

1. [Framework Overview](#framework-overview)
2. [Test Suite Setup](#test-suite-setup)
3. [Basic Test Structure](#basic-test-structure)
4. [Mock Generation & Usage](#mock-generation--usage)
5. [Database Testing Patterns](#database-testing-patterns)
6. [Time Handling in Tests](#time-handling-in-tests)
7. [Error Testing Strategies](#error-testing-strategies)
8. [JSON & Serialization Testing](#json--serialization-testing)
9. [Integration Test Patterns](#integration-test-patterns)
10. [Test Organization & Naming](#test-organization--naming)
11. [Common Testing Utilities](#common-testing-utilities)
12. [Best Practices & Anti-patterns](#best-practices--anti-patterns)

## Framework Overview

### Core Technologies
- **[Ginkgo v2](https://onsi.github.io/ginkgo/)**: BDD-style testing framework
- **[Gomega](https://onsi.github.io/gomega/)**: Matcher/assertion library
- **[Counterfeiter](https://github.com/maxbrunsfeld/counterfeiter)**: Mock generation
- **BoltDB**: Database testing with temporary instances
- **github.com/bborbe/* Libraries**: 
  - **[time](https://github.com/bborbe/time)**: Time utilities with dependency injection
  - **[errors](https://github.com/bborbe/errors)**: Enhanced error handling with context
  - **[collection](https://github.com/bborbe/collection)**: Collection utilities (Ptr, etc.)
  - **[validation](https://github.com/bborbe/validation)**: Validation framework
  - **[run](https://github.com/bborbe/run)**: Concurrent execution patterns
  - **[log](https://github.com/bborbe/log)**: Structured logging
  - **[kv](https://github.com/bborbe/kv)**: Key-value store abstractions  
  - **[boltkv](https://github.com/bborbe/boltkv)**: BoltDB key-value implementation
  - **[kafka](https://github.com/bborbe/kafka)**: Kafka client utilities
  - **[http](https://github.com/bborbe/http)**: HTTP server/client utilities
  - **[sentry](https://github.com/bborbe/sentry)**: Sentry error reporting integration
  - **[cron](https://github.com/bborbe/cron)**: Cron job utilities
  - **[service](https://github.com/bborbe/service)**: Service framework for CLI applications
  - **[k8s](https://github.com/bborbe/k8s)**: Kubernetes utilities
  - **[math](https://github.com/bborbe/math)**: Mathematical utilities
  - **[parse](https://github.com/bborbe/parse)**: Parsing utilities

### Key Testing Principles
- **Behavior-Driven Development (BDD)**: Tests describe behavior, not implementation
- **Descriptive Test Names**: Clear intent and expected outcomes
- **Test Isolation**: Each test is independent and idempotent
- **Mock-First Approach**: Use mocks for external dependencies
- **UTC Timezone**: Consistent time handling across all tests

### Critical Rules
- **Never use stdlib `testing` table-driven tests** (`[]struct` loops with `t.Run`). Always use Ginkgo `DescribeTable`/`Entry` for table-driven tests. If a `*_suite_test.go` with Ginkgo imports exists in the package, all tests must use Ginkgo.
- **Never use `testing.T` directly** in packages that have a Ginkgo test suite. Use `Describe`/`Context`/`It`/`DescribeTable`/`Entry` blocks instead.

```go
// ❌ WRONG — stdlib table-driven test
func TestFoo(t *testing.T) {
    tests := []struct{ input, want string }{ ... }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) { ... })
    }
}

// ✅ CORRECT — Ginkgo DescribeTable
var _ = DescribeTable("foo",
    func(input, expected string) {
        Expect(foo(input)).To(Equal(expected))
    },
    Entry("case A", "in1", "out1"),
    Entry("case B", "in2", "out2"),
)
```

## Test Suite Setup

Every Go package with tests requires a `*_suite_test.go` file. There are two patterns depending on whether the package is `main` or a regular package.

### Standard Package Test Suite

**Every non-main package** must have this test suite structure:

```go
// Copyright (c) 2025 Benjamin Borbe All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

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
	suiteConfig, reporterConfig := GinkgoConfiguration()
	suiteConfig.Timeout = 60 * time.Second
	RunSpecs(t, "Test Suite", suiteConfig, reporterConfig)
}
```

**Key requirements:**
- **Copyright Header**: BSD-style license header with current year
- **External Test Package**: Use `package_test` suffix (e.g., `pkg_test`, `user_test`)
- **UTC Timezone**: `time.Local = time.UTC` ensures consistent time handling across all tests
- **Full Diffs**: `format.TruncatedDiff = false` shows complete comparison failures
- **Mock Generation**: `//go:generate` directive enables `go generate ./...` to create mocks
- **Simple Suite Name**: Use descriptive name like "Test Suite", "Package Test Suite", etc.

### Main Package Test Suite (Special Case)

**Main packages** use a different pattern focused on compilation verification:

```go
// Copyright (c) 2023 Benjamin Borbe All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package main_test

import (
	"testing"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/gexec"
)

var _ = Describe("Main", func() {
	It("Compiles", func() {
		var err error
		_, err = gexec.Build(".", "-mod=mod")
		Expect(err).NotTo(HaveOccurred())
	})
})

func TestSuite(t *testing.T) {
	RegisterFailHandler(Fail)
	suiteConfig, reporterConfig := GinkgoConfiguration()
	suiteConfig.Timeout = 60 * time.Second
	RunSpecs(t, "Main Suite", suiteConfig, reporterConfig)
}
```

**Key differences for main packages:**
- **Copyright Header**: BSD-style license header (may use older year)
- **External Test Package**: Use `main_test` package name
- **No Time/Format Setup**: Omit `time.Local` and `format.TruncatedDiff` configuration
- **No Mock Generation**: Omit `//go:generate` directive (main packages don't have interfaces)
- **Compilation Test**: Include `Compiles` test using `gexec.Build` to verify buildability
- **Simplified Suite**: Minimal test suite focused on build verification

### Critical Notes
- **Main package is the ONLY exception** to the standard test suite pattern
- All other packages (including internal, pkg, cmd subpackages) use the standard pattern
- The compilation test ensures the main package builds correctly as part of test execution
- **Every binary project MUST have `main_test.go`** — missing it means build failures are not caught by `make test`

### Stdlib Preferences

Use `slices.Contains` instead of manual loops for slice membership checks — the `slicescontains` linter enforces this:
```go
// BAD — linter will reject
func contains(s []string, v string) bool {
    for _, item := range s {
        if item == v { return true }
    }
    return false
}

// GOOD
import "slices"
slices.Contains(s, v)
```
- Main packages typically have minimal logic; business logic belongs in testable packages

## Basic Test Structure

### AAA Pattern with Ginkgo
Tests follow **Arrange**, **Act**, **Assert** pattern using Ginkgo lifecycle hooks:

```go
var _ = Describe("Product", func() {
	var ctx context.Context
	var err error
	var product domain.Product
	var result domain.Price

	// ARRANGE: Set up test data
	BeforeEach(func() {
		ctx = context.Background()
		product = domain.Product{
			Name:     "Example Product",
			Price:    99.99,
			Quantity: 10,
		}
	})

	Context("CalculateDiscount", func() {
		// ACT: Execute the method under test
		JustBeforeEach(func() {
			result = product.CalculateDiscount(0.1) // 10% discount
		})

		Context("with valid discount", func() {
			// ASSERT: Verify expectations
			It("returns correct discounted price", func() {
				Expect(result).To(Equal(domain.Price(89.99)))
			})
		})

		Context("with maximum discount", func() {
			BeforeEach(func() {
				product.Price = 100.0
			})

			It("applies discount correctly", func() {
				result = product.CalculateDiscount(0.5) // 50% discount
				Expect(result).To(Equal(domain.Price(50.0)))
			})
		})
	})
})
```

### Lifecycle Hooks
- **`BeforeEach`**: Setup executed before each `It` block
- **`JustBeforeEach`**: Action executed just before each `It` block (after all `BeforeEach`)
- **`AfterEach`**: Cleanup executed after each `It` block
- **`Context`**: Groups related test scenarios
- **`It`**: Individual test assertions

### Test Timeouts

#### Suite-Level Timeout (Recommended Default)

Set a default timeout for the entire suite to prevent stuck tests from running indefinitely:

```go
func TestSuite(t *testing.T) {
	time.Local = time.UTC
	format.TruncatedDiff = false
	RegisterFailHandler(Fail)
	suiteConfig, reporterConfig := GinkgoConfiguration()
	suiteConfig.Timeout = 60 * time.Second
	RunSpecs(t, "Test Suite", suiteConfig, reporterConfig)
}
```

**Every suite file should include `suiteConfig.Timeout`** as a safety net against hanging tests.

#### Per-Spec Timeout

Each Ginkgo `It` block can have its own timeout using `SpecTimeout`:

```go
It("does something within 2s", func(ctx context.Context) {
    // test code
}, SpecTimeout(2*time.Second))
```

If the test body takes longer than the specified timeout, Ginkgo automatically aborts the spec.

#### Per-Node Timeout

Use `NodeTimeout` on `Describe`/`Context`/`It` nodes to limit individual nodes:

```go
Describe("slow subsystem", func() {
    It("completes within 5s", func(ctx SpecContext) {
        // use ctx for cancellation-aware operations
        Eventually(ctx, func() bool { return ready }).Should(BeTrue())
    }, NodeTimeout(5*time.Second))
}, NodeTimeout(30*time.Second))
```

#### CLI Flag

Override the suite timeout from the command line:
```bash
ginkgo --timeout=120s ./...
```

### Nested Contexts
Use nested `Context` blocks to organize test scenarios:

```go
Context("Validate", func() {
	JustBeforeEach(func() {
		err = product.Validate(ctx)
	})

	Context("success cases", func() {
		It("returns no error", func() {
			Expect(err).To(BeNil())
		})
	})

	Context("error cases", func() {
		Context("name missing", func() {
			BeforeEach(func() {
				product.Name = ""
			})

			It("returns error", func() {
				Expect(err).NotTo(BeNil())
			})
		})

		Context("negative price", func() {
			BeforeEach(func() {
				product.Price = -10.0
			})

			It("returns error", func() {
				Expect(err).NotTo(BeNil())
			})
		})
	})
})
```

## Mock Generation & Usage

For comprehensive mocking patterns, mock discovery, and best practices, see **[go-mocking-guide.md](go-mocking-guide.md)**.

For understanding when to use mocks vs real implementations, see **[go-test-types-guide.md](go-test-types-guide.md)**.

**Quick Reference:**
```bash
# Generate mocks
go generate ./...

# Mock setup in tests
mockService := &mocks.UserService{}
mockService.CreateReturns(nil)
```

**Key Principle**: Mock external dependencies at interface boundaries, use real implementations for internal utilities.

## Database Testing Patterns

### BoltDB Testing Setup

```go
var _ = Describe("UserStore", func() {
	var ctx context.Context
	var err error
	var db libboltkv.DB
	var store domain.UserStore

	BeforeEach(func() {
		ctx = context.Background()
		
		// Create temporary database
		db, err = libboltkv.OpenTemp(ctx)
		Expect(err).To(BeNil())
		
		store = domain.NewUserStore(db)
	})

	AfterEach(func() {
		// Always clean up database
		_ = db.Close()
		_ = db.Remove()
	})

	Context("Save and Get", func() {
		var user domain.User
		var retrieved *domain.User

		BeforeEach(func() {
			user = domain.User{
				ID:    "user-123",
				Name:  "John Doe",
				Email: "john@example.com",
			}
		})

		JustBeforeEach(func() {
			err = store.Save(ctx, user)
			Expect(err).To(BeNil())
			
			retrieved, err = store.Get(ctx, user.ID)
		})

		It("returns no error", func() {
			Expect(err).To(BeNil())
		})

		It("returns correct user", func() {
			Expect(retrieved).NotTo(BeNil())
			Expect(retrieved.ID).To(Equal(user.ID))
			Expect(retrieved.Name).To(Equal(user.Name))
		})
	})
})
```

### Transaction Testing

```go
var _ = Describe("TransactionalService", func() {
	var ctx context.Context
	var db libboltkv.DB
	var service TransactionalService

	BeforeEach(func() {
		ctx = context.Background()
		db, _ = libboltkv.OpenTemp(ctx)
		service = NewTransactionalService(db)
	})

	AfterEach(func() {
		_ = db.Close()
		_ = db.Remove()
	})

	Context("transaction rollback on error", func() {
		It("does not persist changes when error occurs", func() {
			err := service.ProcessWithError(ctx, "test-id")
			Expect(err).NotTo(BeNil())

			// Verify no data was persisted
			_, err = service.Get(ctx, "test-id")
			Expect(err).To(MatchError(ContainSubstring("not found")))
		})
	})
})
```

## Time Handling in Tests

### Fixed Time Setup

```go
var _ = Describe("TimeService", func() {
	var ctx context.Context
	var currentDateTime libtime.CurrentDateTime
	var service TimeService
	var fixedTime time.Time

	BeforeEach(func() {
		ctx = context.Background()
		fixedTime = time.Date(2023, 12, 25, 12, 0, 0, 0, time.UTC)
		
		// Create controllable time
		currentDateTime = libtime.NewCurrentDateTime()
		currentDateTime.SetNow(fixedTime)
		
		service = NewTimeService(currentDateTime)
	})

	Context("timestamp generation", func() {
		var result time.Time

		JustBeforeEach(func() {
			result = service.GetCurrentTime()
		})

		It("returns fixed time", func() {
			Expect(result).To(Equal(fixedTime))
		})
	})

	Context("time progression", func() {
		It("advances time when updated", func() {
			initial := service.GetCurrentTime()
			
			// Advance time by 1 hour
			newTime := fixedTime.Add(time.Hour)
			currentDateTime.SetNow(newTime)
			
			advanced := service.GetCurrentTime()
			Expect(advanced).To(Equal(newTime))
			Expect(advanced).To(BeTemporally(">", initial))
		})
	})
})
```

### Time Utilities for Tests

```go
import libtimetest "github.com/bborbe/time/test"

// Parsing helper
fixedTime := libtimetest.ParseDateTime("2023-12-25T00:00:00Z")

// Time comparisons
Expect(actualTime).To(BeTemporally("~", expectedTime, time.Second))
Expect(actualTime).To(BeTemporally(">", beforeTime))
Expect(actualTime).To(BeTemporally("<=", afterTime))
```

## Error Testing Strategies

### Comprehensive Error Testing

```go
var _ = Describe("ValidationService", func() {
	var ctx context.Context
	var service ValidationService
	var input Input

	BeforeEach(func() {
		ctx = context.Background()
		service = NewValidationService()
		input = Input{Value: "valid"}
	})

	Context("Validate", func() {
		var err error

		JustBeforeEach(func() {
			err = service.Validate(ctx, input)
		})

		Context("valid input", func() {
			It("returns no error", func() {
				Expect(err).To(BeNil())
			})
		})

		Context("invalid input", func() {
			Context("empty value", func() {
				BeforeEach(func() {
					input.Value = ""
				})

				It("returns validation error", func() {
					Expect(err).NotTo(BeNil())
					Expect(err.Error()).To(ContainSubstring("value cannot be empty"))
				})
			})

			Context("value too long", func() {
				BeforeEach(func() {
					input.Value = strings.Repeat("a", 1000)
				})

				It("returns length error", func() {
					Expect(err).NotTo(BeNil())
					Expect(err.Error()).To(ContainSubstring("value too long"))
				})
			})
		})

		Context("external dependency failure", func() {
			var mockValidator *mocks.ExternalValidator

			BeforeEach(func() {
				mockValidator = &mocks.ExternalValidator{}
				service = NewValidationServiceWithValidator(mockValidator)
				
				mockValidator.ValidateReturns(errors.New("external service down"))
			})

			It("wraps external error", func() {
				Expect(err).NotTo(BeNil())
				Expect(err.Error()).To(ContainSubstring("external service down"))
			})
		})
	})
})
```

### Error Type Testing

```go
Context("specific error types", func() {
	It("returns NotFoundError for missing items", func() {
		_, err := service.Get(ctx, "nonexistent")
		Expect(err).To(MatchError(&NotFoundError{}))
	})

	It("returns ValidationError for invalid data", func() {
		err := service.Create(ctx, InvalidData{})
		var validationErr *ValidationError
		Expect(errors.As(err, &validationErr)).To(BeTrue())
		Expect(validationErr.Field).To(Equal("name"))
	})
})
```

## JSON & Serialization Testing

### JSON Marshaling/Unmarshaling

```go
var _ = Describe("User JSON", func() {
	var user domain.User
	var jsonBytes []byte
	var err error

	BeforeEach(func() {
		user = domain.User{
			ID:    "user-123",
			Name:  "John Doe",
			Email: "john@example.com",
		}
	})

	Context("Marshal", func() {
		JustBeforeEach(func() {
			jsonBytes, err = json.Marshal(user)
		})

		It("returns no error", func() {
			Expect(err).To(BeNil())
		})

		It("produces correct JSON", func() {
			expected := `{"id":"user-123","name":"John Doe","email":"john@example.com"}`
			Expect(string(jsonBytes)).To(Equal(expected))
		})
	})

	Context("Unmarshal", func() {
		var unmarshaled domain.User

		JustBeforeEach(func() {
			jsonStr := `{"id":"user-123","name":"John Doe","email":"john@example.com"}`
			err = json.Unmarshal([]byte(jsonStr), &unmarshaled)
		})

		It("returns no error", func() {
			Expect(err).To(BeNil())
		})

		It("recreates correct object", func() {
			Expect(unmarshaled).To(Equal(user))
		})
	})

	Context("round trip", func() {
		It("preserves data through marshal/unmarshal", func() {
			jsonBytes, err := json.Marshal(user)
			Expect(err).To(BeNil())

			var restored domain.User
			err = json.Unmarshal(jsonBytes, &restored)
			Expect(err).To(BeNil())

			Expect(restored).To(Equal(user))
		})
	})
})
```

## Integration Test Patterns

### Service Integration Testing

```go
var _ = Describe("OrderProcessor Integration", func() {
	var ctx context.Context
	var processor OrderProcessor
	var mockPayment *mocks.PaymentAPI
	var mockNotifier *mocks.NotificationService
	var db libboltkv.DB

	BeforeEach(func() {
		ctx = context.Background()
		
		// Setup real database
		db, _ = libboltkv.OpenTemp(ctx)
		
		// Setup mocks for external dependencies
		mockPayment = &mocks.PaymentAPI{}
		mockNotifier = &mocks.NotificationService{}
		
		// Create service with mix of real and mock dependencies
		processor = NewOrderProcessor(
			domain.NewOrderStore(db), // Real store
			mockPayment,              // Mock payment service
			mockNotifier,             // Mock notifier
		)
	})

	AfterEach(func() {
		_ = db.Close()
		_ = db.Remove()
	})

	Context("process order end-to-end", func() {
		var order domain.OrderRequest
		var result *domain.Order

		BeforeEach(func() {
			order = domain.OrderRequest{
				ID:       "order-123",
				Product:  "laptop",
				Quantity: 2,
				Amount:   2500.00,
			}

			// Mock successful payment response
			mockPayment.ProcessPaymentReturns(&PaymentResult{
				ID:     "payment-123",
				Status: "success",
			}, nil)
		})

		JustBeforeEach(func() {
			result, err = processor.ProcessOrder(ctx, order)
		})

		It("processes successfully", func() {
			Expect(err).To(BeNil())
			Expect(result).NotTo(BeNil())
		})

		It("stores order in database", func() {
			stored, err := processor.store.Get(ctx, result.ID)
			Expect(err).To(BeNil())
			Expect(stored.Product).To(Equal(order.Product))
		})

		It("calls payment service with correct parameters", func() {
			Expect(mockPayment.ProcessPaymentCallCount()).To(Equal(1))
			// Verify payment call parameters...
		})

		It("sends notification", func() {
			Expect(mockNotifier.NotifyCallCount()).To(Equal(1))
		})
	})
})
```

### Label-Based Test Organization (Optional)

Ginkgo v2 supports labels for categorizing tests, enabling selective test execution. While not widely used in the ecosystem (less than 1% of tests), labels can be useful for separating unit and integration tests.

#### Applying Labels to Tests

```go
var _ = Describe("UserService", func() {
	// Unit test with label
	Context("Validate", Label("unit"), func() {
		It("returns error for invalid email", func() {
			err := service.Validate(ctx, "not-an-email")
			Expect(err).NotTo(BeNil())
		})
	})

	// Integration test with label and real database
	Context("Create", Label("integration"), func() {
		var db libboltkv.DB

		BeforeEach(func() {
			db, _ = libboltkv.OpenTemp(ctx)
		})

		AfterEach(func() {
			_ = db.Close()
			_ = db.Remove()
		})

		It("creates user in database", func() {
			user := domain.User{
				ID:    "user-123",
				Email: "john@example.com",
			}
			err := service.Create(ctx, user)
			Expect(err).To(BeNil())

			retrieved, err := service.Get(ctx, user.ID)
			Expect(err).To(BeNil())
			Expect(retrieved.Email).To(Equal(user.Email))
		})
	})
})
```

#### Running Tests by Label

```bash
# Run all tests (default)
ginkgo run ./...

# Run only unit tests
ginkgo run --label-filter="unit" ./...

# Run only integration tests
ginkgo run --label-filter="integration" ./...

# Run tests excluding integration
ginkgo run --label-filter="!integration" ./...

# Combine label filters
ginkgo run --label-filter="unit && !slow" ./...
```

#### Standard Label Conventions

| Label | Purpose | Typical Speed |
|-------|---------|---------------|
| `unit` | Tests single components with mocks | Fast (milliseconds) |
| `integration` | Tests multiple components together (internal only) | Medium (seconds) |
| `e2e` | Tests with external dependencies (databases, APIs, etc.) | Slow (seconds to minutes) |
| `slow` | Long-running tests (large datasets, timeouts, etc.) | Very slow (minutes) |

**Key points:**
- Labels are optional - most tests in the ecosystem don't use them
- Consistent labeling enables fast feedback loops in CI/CD
- Use `Label("integration")` for tests with real databases or file I/O
- Use `Label("unit")` for fast tests with mocks only
- Multiple labels can be applied: `Label("integration", "slow")`
- Standard test files remain `*_test.go` (no separate `*_integration_test.go` files)

## Test Organization & Naming

### File Naming Conventions
- **Test Files**: `feature_test.go` (e.g., `user-service_test.go`)
- **Suite Files**: `package_suite_test.go` (e.g., `pkg_suite_test.go`)
- **Package**: `package_test` (separate from implementation package)

### Test Naming Patterns

```go
// Good: Descriptive hierarchy
var _ = Describe("UserService", func() {
	Context("Create", func() {
		Context("with valid data", func() {
			It("creates user successfully", func() {
				// Test implementation
			})
		})
		
		Context("with invalid email", func() {
			It("returns validation error", func() {
				// Test implementation
			})
		})
	})
})

// Good: Specific behavior description
var _ = Describe("Order", func() {
	Context("CalculateTotal", func() {
		Context("order with discount applied", func() {
			It("returns correct total amount", func() {
				// Test implementation
			})
		})
	})
})
```

### Directory Structure
```
pkg/
├── user-service.go
├── user-service_test.go
├── pkg_suite_test.go
└── mocks/
    ├── user-repository.go
    ├── email-service.go
    └── generated_mocks.go
```

## Common Testing Utilities

### Custom Matchers

```go
// Custom matcher for testing value equality with tolerance
func BeWithinTolerance(expected domain.Value, tolerance domain.Value) types.GomegaMatcher {
	return &withinToleranceMatcher{
		expected:  expected,
		tolerance: tolerance,
	}
}

// Usage in tests
Expect(actualValue).To(BeWithinTolerance(domain.Value(100.50), domain.Value(0.01)))
```

### Test Data Builders

```go
// Builder pattern for test data
func NewTestOrder() *OrderBuilder {
	return &OrderBuilder{
		order: domain.Order{
			ID:       "test-order",
			Product:  "laptop",
			Quantity: 2,
			Price:    999.99,
		},
	}
}

func (b *OrderBuilder) WithProduct(product string) *OrderBuilder {
	b.order.Product = product
	return b
}

func (b *OrderBuilder) WithDiscount(discount float64) *OrderBuilder {
	b.order.Discount = domain.Price(discount).Ptr()
	return b
}

func (b *OrderBuilder) Build() domain.Order {
	return b.order
}

// Usage in tests
order := NewTestOrder().
	WithProduct("smartphone").
	WithDiscount(50.00).
	Build()
```

### Table-Driven Tests with Ginkgo

```go
var _ = Describe("UnitConverter", func() {
	var converter UnitConverter

	BeforeEach(func() {
		converter = NewUnitConverter()
	})

	DescribeTable("unit conversions",
		func(from, to string, value, expected float64) {
			result, err := converter.Convert(from, to, value)
			Expect(err).To(BeNil())
			Expect(result).To(BeNumerically("~", expected, 0.001))
		},
		Entry("meters to feet", "m", "ft", 1.0, 3.281),
		Entry("feet to meters", "ft", "m", 3.281, 1.0),
		Entry("celsius to fahrenheit", "C", "F", 0.0, 32.0),
		Entry("same unit", "m", "m", 100.0, 100.0),
	)
})
```

## Best Practices & Anti-patterns

### ✅ Best Practices

**1. Clear Test Organization**
```go
// Good: Clear hierarchy and descriptive names
var _ = Describe("InputValidator", func() {
	Context("ValidateInput", func() {
		Context("when input is valid", func() {
			It("returns no error", func() {
				// Test valid input
			})
		})
		
		Context("when input format is invalid", func() {
			It("returns format validation error", func() {
				// Test invalid format
			})
		})
	})
})
```

**2. Proper Mock Usage**
```go
// Good: Verify both behavior and calls
BeforeEach(func() {
	mockService.ProcessReturns(expectedResult, nil)
})

It("calls service with correct parameters", func() {
	Expect(mockService.ProcessCallCount()).To(Equal(1))
	actualCtx, actualData := mockService.ProcessArgsForCall(0)
	Expect(actualCtx).To(Equal(ctx))
	Expect(actualData).To(Equal(testData))
})
```

**3. Independent Tests**
```go
// Good: Each test is isolated
BeforeEach(func() {
	// Fresh setup for each test
	ctx = context.Background()
	service = NewTestService()
})
```

**4. Comprehensive Error Testing**
```go
// Good: Test both success and failure paths
Context("success case", func() {
	It("returns expected result", func() {
		// Test success
	})
})

Context("error cases", func() {
	Context("invalid input", func() {
		It("returns validation error", func() {
			// Test validation error
		})
	})
	
	Context("external service failure", func() {
		It("handles service error gracefully", func() {
			// Test external error handling
		})
	})
})
```

### ❌ Anti-patterns

**1. Testing Implementation Details**
```go
// Bad: Testing internal implementation
It("calls helper method twice", func() {
	result := service.Process(data)
	// This test is too coupled to implementation
})

// Good: Testing behavior
It("processes data correctly", func() {
	result := service.Process(data)
	Expect(result.Status).To(Equal(ProcessedStatus))
})
```

**2. Large, Unfocused Tests**
```go
// Bad: One test doing too much
It("handles entire user lifecycle", func() {
	// Creates user
	// Updates user
	// Deletes user
	// Tests multiple unrelated behaviors
})

// Good: Separate focused tests
Context("Create", func() {
	It("creates user with valid data", func() {
		// Test only creation
	})
})

Context("Update", func() {
	It("updates user information", func() {
		// Test only update
	})
})
```

**3. Missing Error Cases**
```go
// Bad: Only testing happy path
It("processes request", func() {
	result := service.Process(validInput)
	Expect(result).NotTo(BeNil())
})

// Good: Testing both success and failure
Context("with valid input", func() {
	It("processes successfully", func() {
		// Test success
	})
})

Context("with invalid input", func() {
	It("returns validation error", func() {
		// Test error handling
	})
})
```

**4. Test Data Dependencies**
```go
// Bad: Tests depend on each other
var globalTestData TestData

It("creates data", func() {
	globalTestData = service.Create(input)
})

It("uses created data", func() {
	result := service.Process(globalTestData) // Depends on previous test
})

// Good: Independent test data
BeforeEach(func() {
	testData = CreateTestData() // Fresh data for each test
})
```

## Running Tests

### Make Commands
```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run specific package tests
ginkgo run pkg/

# Run tests matching pattern
ginkgo -focus="Order" pkg/

# Generate mocks
go generate ./...

# Run quality checks (includes tests)
make precommit
```

### CI/CD Integration
Tests are automatically run as part of the precommit process and must pass before code can be committed. The make precommit command runs:
- Test execution with coverage requirements
- Mock generation verification
- Static analysis and linting
- Code formatting validation

This comprehensive testing approach ensures reliable, maintainable code throughout any Go application, with clear patterns that all developers can follow for consistent, high-quality tests.