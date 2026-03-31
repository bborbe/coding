# Go Enum Type Pattern

This guide documents the canonical string-based enum pattern used throughout Benjamin Borbe's Go projects - a widely used pattern (50+ implementations across projects).

## When to Use This Pattern

Use this pattern when you need:
- **Type-safe constants** with validation against a known set of values
- **Compile-time guarantees** instead of runtime string matching
- **Collection operations** (Contains, filtering, etc.)
- **Database/JSON serialization** of enumerated values

**Don't use** for simple value wrappers that don't need predefined constants (e.g., user IDs, arbitrary names).

## Core Pattern Structure

### Minimal Complete Implementation

```go
package order

import (
	"context"

	"github.com/bborbe/collection"
	"github.com/bborbe/errors"
	"github.com/bborbe/validation"
)

// 1. Define constants with explicit typing
const (
	PendingOrderStatus    OrderStatus = "pending"
	ProcessingOrderStatus OrderStatus = "processing"
	CompletedOrderStatus  OrderStatus = "completed"
	FailedOrderStatus     OrderStatus = "failed"
)

// 2. Declare available values collection
var AvailableOrderStatuses = OrderStatuses{
	PendingOrderStatus,
	ProcessingOrderStatus,
	CompletedOrderStatus,
	FailedOrderStatus,
}

// 3. Define singular type
type OrderStatus string

// 4. Implement String() method
func (o OrderStatus) String() string {
	return string(o)
}

// 5. Implement Validate() method checking against Available* collection
func (o OrderStatus) Validate(ctx context.Context) error {
	if AvailableOrderStatuses.Contains(o) == false {
		return errors.Wrapf(ctx, validation.Error, "unknown order status '%s'", o)
	}
	return nil
}

// 6. Define plural collection type
type OrderStatuses []OrderStatus

// 7. Implement Contains() method on collection
func (o OrderStatuses) Contains(status OrderStatus) bool {
	return collection.Contains(o, status)
}
```

## Implementation Checklist

When creating a new enum type, ensure you have:

- [ ] Constants with explicit type annotation (`const Name Type = "value"`)
- [ ] `var AvailableXs` collection containing all valid values
- [ ] Singular type definition (`type Status string`)
- [ ] `String() string` method on singular type
- [ ] `Validate(ctx context.Context) error` method checking against `AvailableXs`
- [ ] Plural collection type (`type Statuses []Status`)
- [ ] `Contains()` method on plural type using `github.com/bborbe/collection`

## Usage Example

```go
type Order struct {
	ID       string      `json:"id"`
	Status   OrderStatus `json:"status"`
	Priority Priority    `json:"priority"`
}

func (o Order) Validate(ctx context.Context) error {
	return validation.Validate(ctx, o.Status, o.Priority)
}

func ProcessOrder(ctx context.Context, order Order) error {
	// Type-safe comparison
	if order.Status == CompletedOrderStatus {
		return errors.New("order already completed")
	}

	// Collection operations
	activeStatuses := OrderStatuses{PendingOrderStatus, ProcessingOrderStatus}
	if !activeStatuses.Contains(order.Status) {
		return errors.New("order not in active state")
	}

	// String conversion
	fmt.Printf("Processing order with status: %s\n", order.Status.String())

	// Validation
	if err := order.Validate(ctx); err != nil {
		return errors.Wrapf(ctx, err, "invalid order")
	}

	return nil
}
```

See [Go Validation Framework Guide](go-validation-framework-guide.md) for validation patterns.
