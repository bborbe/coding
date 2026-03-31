# Go Parse Pattern Guide

This guide documents the standardized parse pattern used across Benjamin Borbe's Go ecosystem for converting dynamic/untyped input into typed values with fallback support.

## When to Use This Pattern

Use this pattern when you need:
- **Type conversion** from `interface{}` or `any` to specific types
- **Graceful fallbacks** when parsing fails (API responses, config files, user input)
- **Consistent error handling** across parsing operations

**Don't use** for simple type assertions where you control the type (use direct type assertion instead).

## Core Pattern Structure

The parse pattern consists of two complementary functions:

1. **Parse Function** - Returns value (or pointer) and error
2. **ParseDefault Function** - Returns value directly, using fallback on error

### Pattern Signatures

```go
// For primitive types (int, string, bool, etc.)
func ParseX(ctx context.Context, value any) (X, error)
func ParseXDefault(ctx context.Context, value any, defaultValue X) X

// For custom types (enums, domain types)
func ParseX(ctx context.Context, value any) (*X, error)
func ParseXDefault(ctx context.Context, value any, defaultValue X) X
```

**Key points:**
- Parse functions accept `any` (or `interface{}`) to handle dynamic input
- Primitive type parsers return the value directly: `(int, error)`
- Custom type parsers return a pointer: `(*CustomType, error)` to allow nil on error
- ParseDefault functions never return errors, using the default value on failure
- All functions accept `context.Context` as first parameter for error wrapping

## 1. Implementing the Parse Pattern

For primitive types (int, string, bool, etc.), use `github.com/bborbe/parse`:

```go
import libparse "github.com/bborbe/parse"

str, err := libparse.ParseString(ctx, value)
i := libparse.ParseIntDefault(ctx, value, 0)
```

For custom types (especially enums following the [Go Enum Type Pattern](go-enum-type-pattern.md)), implement both Parse and ParseDefault functions:

### Complete Implementation Example

```go
package order

import (
	"context"

	"github.com/bborbe/collection"
	libparse "github.com/bborbe/parse"
	"github.com/bborbe/errors"
	"github.com/bborbe/validation"
)

// Enum constants
const (
	PendingOrderStatus    OrderStatus = "pending"
	ProcessingOrderStatus OrderStatus = "processing"
	CompletedOrderStatus  OrderStatus = "completed"
	FailedOrderStatus     OrderStatus = "failed"
)

// Available values collection
var AvailableOrderStatuses = OrderStatuses{
	PendingOrderStatus,
	ProcessingOrderStatus,
	CompletedOrderStatus,
	FailedOrderStatus,
}

// ParseOrderStatus converts any value to an OrderStatus pointer
func ParseOrderStatus(ctx context.Context, value any) (*OrderStatus, error) {
	str, err := libparse.ParseString(ctx, value)
	if err != nil {
		return nil, errors.Wrapf(ctx, err, "parse string failed")
	}
	status := OrderStatus(str)

	if err := status.Validate(ctx); err != nil {
		return nil, errors.Wrapf(ctx, err, "invalid order status")
	}

	return status.Ptr(), nil
}

// ParseOrderStatusDefault converts any value to an OrderStatus with fallback
func ParseOrderStatusDefault(ctx context.Context, value any, defaultValue OrderStatus) OrderStatus {
	status, err := ParseOrderStatus(ctx, value)
	if err != nil {
		return defaultValue
	}
	return *status
}

// OrderStatus enum type
type OrderStatus string

func (o OrderStatus) String() string {
	return string(o)
}

func (o OrderStatus) Validate(ctx context.Context) error {
	if !AvailableOrderStatuses.Contains(o) {
		return errors.Wrapf(ctx, validation.Error, "order status '%s' is unknown", o)
	}
	return nil
}

func (o OrderStatus) Ptr() *OrderStatus {
	return &o
}

// OrderStatuses collection type
type OrderStatuses []OrderStatus

func (o OrderStatuses) Contains(status OrderStatus) bool {
	return collection.Contains(o, status)
}
```

**Key points:**
- Use `libparse.ParseString()` as the first step for string-based enums
- Return `*CustomType` (pointer) to allow nil on error
- Validate the parsed value against available constants
- The Default variant dereferences the pointer after checking for error
- Always include proper error context wrapping

## 2. Testing Parse Functions

```go
var _ = Describe("ParseOrderStatus", func() {
	var ctx context.Context

	BeforeEach(func() {
		ctx = context.Background()
	})

	// Test Parse variant
	It("parses valid string", func() {
		result, err := order.ParseOrderStatus(ctx, "pending")
		Expect(err).NotTo(HaveOccurred())
		Expect(*result).To(Equal(order.PendingOrderStatus))
	})

	It("returns error for invalid value", func() {
		result, err := order.ParseOrderStatus(ctx, "invalid")
		Expect(err).To(HaveOccurred())
		Expect(result).To(BeNil())
	})

	// Test ParseDefault variant
	It("returns parsed value on success", func() {
		result := order.ParseOrderStatusDefault(ctx, "pending", order.FailedOrderStatus)
		Expect(result).To(Equal(order.PendingOrderStatus))
	})

	It("returns default value on error", func() {
		result := order.ParseOrderStatusDefault(ctx, "invalid", order.FailedOrderStatus)
		Expect(result).To(Equal(order.FailedOrderStatus))
	})
})
```

**Key points:**
- Test valid and invalid inputs for both Parse and ParseDefault
- Verify error returns and nil pointers for Parse variant
- Verify default value fallback for ParseDefault variant

## 3. Advanced Patterns

```go
import (
	"context"
	"strings"

	libparse "github.com/bborbe/parse"
	"github.com/bborbe/errors"
)

func ParseEmailAddress(ctx context.Context, value any) (*EmailAddress, error) {
	str, err := libparse.ParseString(ctx, value)
	if err != nil {
		return nil, errors.Wrapf(ctx, err, "parse string failed")
	}

	// Transform before validation
	normalized := strings.ToLower(strings.TrimSpace(str))
	email := EmailAddress(normalized)

	if err := email.Validate(ctx); err != nil {
		return nil, errors.Wrapf(ctx, err, "invalid email")
	}
	return email.Ptr(), nil
}
```

**Key points:**
- Common transformations: trimming whitespace, normalizing case, formatting
- Always validate after transformation

## 4. Common Antipatterns to Avoid

### DON'T: Return Value Instead of Pointer for Custom Types

```go
// DON'T - can't distinguish error from zero value
func ParseOrderStatus(ctx context.Context, value any) (OrderStatus, error)

// DO - pointer allows nil on error
func ParseOrderStatus(ctx context.Context, value any) (*OrderStatus, error)
```

### DON'T: Ignore Error in ParseDefault

```go
// DON'T - could panic on nil dereference
func ParseOrderStatusDefault(ctx context.Context, value any, defaultValue OrderStatus) OrderStatus {
	status, _ := ParseOrderStatus(ctx, value)
	return *status  // panics if status is nil
}

// DO - check error explicitly
func ParseOrderStatusDefault(ctx context.Context, value any, defaultValue OrderStatus) OrderStatus {
	status, err := ParseOrderStatus(ctx, value)
	if err != nil {
		return defaultValue
	}
	return *status
}
```

### DON'T: Skip Error Wrapping

```go
// DON'T - loses context
return nil, err

// DO - wrap with context
return nil, errors.Wrapf(ctx, err, "parse string failed")
```

### DON'T: Skip Validation

```go
// DON'T - accepts invalid values
func ParseOrderStatus(ctx context.Context, value any) (*OrderStatus, error) {
	str, err := libparse.ParseString(ctx, value)
	if err != nil {
		return nil, errors.Wrapf(ctx, err, "parse string failed")
	}
	return OrderStatus(str).Ptr(), nil  // No validation
}

// DO - validate before returning
func ParseOrderStatus(ctx context.Context, value any) (*OrderStatus, error) {
	str, err := libparse.ParseString(ctx, value)
	if err != nil {
		return nil, errors.Wrapf(ctx, err, "parse string failed")
	}
	status := OrderStatus(str)
	if err := status.Validate(ctx); err != nil {
		return nil, errors.Wrapf(ctx, err, "invalid order status")
	}
	return status.Ptr(), nil
}
```

## Summary

The parse pattern provides:
- **Consistent API** across all parse operations (Parse + ParseDefault)
- **Type safety** with proper error handling
- **Graceful fallbacks** for optional configuration and user input
- **Library integration** with `github.com/bborbe/parse` for primitives
- **Custom type support** for enums and domain types

**Implementation checklist:**
- [ ] Parse function with `(ctx, value)` → `(*Type, error)` for custom types
- [ ] Parse function with `(ctx, value)` → `(Type, error)` for primitives
- [ ] ParseDefault function with `(ctx, value, defaultValue)` → `Type`
- [ ] Error wrapping with context using `github.com/bborbe/errors`
- [ ] Validation of parsed values before returning
- [ ] Comprehensive tests for both Parse and ParseDefault variants
