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

### RULE go-enum-type/typed-constants-with-collection (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go package introduces a finite set of enum-like values (status codes, kinds, modes, etc.) declared as untyped `const` strings or `const` ints, without a paired typed `string`/`int` newtype AND without an `Available<Name>s` collection containing every valid value.
**Enforcement**: judgment (ast-grep follow-up: `const_declaration` of `string` literals with shared semantic prefix; pair-check against the existence of a `type X string` newtype + a `var AvailableXs Xs` collection in the same package)
**Why**: Untyped enum constants spread through the codebase as bare strings — every call site can pass any string, every comparison can typo, and the linter has no signal that "scheduled" / "completed" / "pending" are meant to be members of a closed set. Typed constants paired with an `AvailableXs` collection turn the enum into a first-class type the type-checker enforces and that `Validate()` can range over. The `Available*` collection is what makes the pattern self-describing — a new contributor reads the package and immediately sees the full value space.

#### Bad

```go
// Untyped string constants — every call site can pass any string
const (
	OrderStatusPending    = "pending"
	OrderStatusProcessing = "processing"
	OrderStatusCompleted  = "completed"
	OrderStatusFailed     = "failed"
)

func Process(status string) error { // accepts any string; typo silent
	if status == "compleated" { ... } // compiles cleanly; runtime no-op
}
```

#### Good

```go
type OrderStatus string

const (
	PendingOrderStatus    OrderStatus = "pending"
	ProcessingOrderStatus OrderStatus = "processing"
	CompletedOrderStatus  OrderStatus = "completed"
	FailedOrderStatus     OrderStatus = "failed"
)

type OrderStatuses []OrderStatus

var AvailableOrderStatuses = OrderStatuses{
	PendingOrderStatus,
	ProcessingOrderStatus,
	CompletedOrderStatus,
	FailedOrderStatus,
}

func Process(status OrderStatus) error { // type-checked at call site
	// ...
}
```

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

### RULE go-enum-type/validate-against-available-collection (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go enum type's `Validate(ctx context.Context) error` method validates against an inline switch / hardcoded value list / regex, instead of `AvailableXs.Contains(value)`.
**Enforcement**: judgment (ast-grep follow-up: `method_declaration` named `Validate` on an enum-shaped type, body containing inline `switch` / `||` chain over string literals, paired with the package having a defined `AvailableXs` collection)
**Why**: Validating against an inline switch duplicates the enum's value space — adding a new enum constant requires updating both `const (...)` and the `Validate()` body, and the type checker can't enforce the pair. Range-over-`AvailableXs` collapses the two into one declaration: the collection IS the validation source, so the only place to add a value is the collection literal. Adds-a-constant-but-forgets-to-update-validate becomes structurally impossible.

#### Bad

```go
func (o OrderStatus) Validate(ctx context.Context) error {
	switch o {
	case PendingOrderStatus, ProcessingOrderStatus,
	     CompletedOrderStatus, FailedOrderStatus:
		return nil
	default:
		return errors.Wrapf(ctx, validation.Error, "unknown order status '%s'", o)
	}
	// Adding a new status to const(...) without updating this switch
	// produces silent validation failures.
}
```

#### Good

```go
func (o OrderStatus) Validate(ctx context.Context) error {
	if !AvailableOrderStatuses.Contains(o) {
		return errors.Wrapf(ctx, validation.Error, "unknown order status '%s'", o)
	}
	return nil
}
// Adding a new status to AvailableOrderStatuses automatically extends
// the validation surface. Single source of truth.
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
