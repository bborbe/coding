# Go Validation Framework Guide

This guide explains how to use the `github.com/bborbe/validation` library effectively in Go projects.

## Table of Contents

- [Overview](#overview)
- [Basic Patterns](#basic-patterns)
- [Logical Operators](#logical-operators)
- [Common Validators](#common-validators)
- [Advanced Patterns](#advanced-patterns)
- [Domain Type Integration](#domain-type-integration)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Common Examples](#common-examples)

## Overview

The `github.com/bborbe/validation` library provides a declarative approach to validation with composable validators. It follows these key principles:

- **Composable**: Validators can be combined using logical operators
- **Named**: Field names can be attached to validators for clear error messages
- **Type-safe**: Works with Go's type system and generics
- **Context-aware**: All validation functions accept `context.Context`

## Basic Patterns

### Simple Field Validation

```go
import "github.com/bborbe/validation"

func (u User) Validate(ctx context.Context) error {
    return validation.All{
        validation.Name("username", validation.NotEmptyString(u.Username)),
        validation.Name("email", validation.NotEmptyString(u.Email)),
    }.Validate(ctx)
}
```

### Domain Type Validation

```go
// Leverage existing Validate methods on domain types
func (r Request) Validate(ctx context.Context) error {
    return validation.All{
        validation.Name("userId", r.UserID),         // Uses UserID.Validate()
        validation.Name("category", r.Category),     // Uses Category.Validate()
        validation.Name("priority", r.Priority),     // Uses Priority.Validate()
    }.Validate(ctx)
}
```

## Logical Operators

### validation.All (AND Logic)

All validators must pass. Use for mandatory field validation:

```go
return validation.All{
    validation.Name("username", validation.NotEmptyString(user.Username)),
    validation.Name("email", validation.NotEmptyString(user.Email)),
    validation.Name("age", validation.HasValidationFunc(func(ctx context.Context) error {
        if user.Age < 18 {
            return errors.New(ctx, "must be 18 or older")
        }
        return nil
    })),
}.Validate(ctx)
```

### validation.Any (OR Logic)

At least one validator must pass. Use for optional-but-required scenarios:

```go
// At least one contact method must be provided
return validation.Any{
    validation.Name("email", validation.NotEmptyString(r.Email)),
    validation.Name("phone", validation.NotEmptyString(r.Phone)),
    validation.Name("address", validation.NotEmptyString(r.Address)),
}.Validate(ctx)
```

## Common Validators

### String Validation

```go
// Non-empty string
validation.NotEmptyString(value)

// String length constraints
validation.StringMinLength(5)
validation.StringMaxLength(100)

// Regular expression matching
validation.StringRegexp(`^[a-zA-Z0-9]+$`)

// Specific string values
validation.StringEquals("expected")
```

### Nil/Existence Checks

```go
validation.NotNil(pointer)
validation.Nil(pointer)
validation.True(boolValue)
validation.False(boolValue)
```

### Custom Validation Functions

```go
validation.HasValidationFunc(func(ctx context.Context) error {
    if customCondition {
        return errors.New(ctx, "custom validation failed")
    }
    return nil
})
```

## Advanced Patterns

### Conditional Validation

```go
return validation.All{
    validation.Name("orderType", o.OrderType),
    validation.Name("price", validation.HasValidationFunc(func(ctx context.Context) error {
        switch o.OrderType {
        case "limit":
            if o.Price == nil {
                return errors.New(ctx, "price required for limit orders")
            }
        case "market":
            if o.Price != nil {
                return errors.New(ctx, "price not allowed for market orders")
            }
        }
        return nil
    })),
}.Validate(ctx)
```

### Nested Struct Validation

```go
type Project struct {
    Name        string
    Description string
    Owner       User
    Tasks       []Task
}

func (p Project) Validate(ctx context.Context) error {
    return validation.All{
        validation.Name("name", validation.NotEmptyString(p.Name)),
        validation.Name("owner", p.Owner),        // Calls User.Validate()
        validation.Name("tasks", p.Tasks),        // Calls Tasks.Validate()
    }.Validate(ctx)
}
```

### Collection Validation

```go
type Tasks []Task

func (t Tasks) Validate(ctx context.Context) error {
    for i, task := range t {
        if err := task.Validate(ctx); err != nil {
            return errors.Wrapf(ctx, err, "task[%d] validation failed", i)
        }
    }
    return nil
}
```

## Domain Type Integration

### Domain Type Validation

Well-designed domain types implement their own validation:

```go
// UserType validates against available user types
func (u UserType) Validate(ctx context.Context) error {
    validTypes := []UserType{"admin", "user", "guest"}
    for _, validType := range validTypes {
        if u == validType {
            return nil
        }
    }
    return errors.Wrapf(ctx, validation.Error, "userType(%s) is invalid", u)
}

// Status validates against available statuses
func (s Status) Validate(ctx context.Context) error {
    validStatuses := []Status{"active", "inactive", "pending"}
    for _, validStatus := range validStatuses {
        if s == validStatus {
            return nil
        }
    }
    return errors.Wrapf(ctx, validation.Error, "status(%s) is invalid", s)
}
```

### Leveraging Domain Validation

Always prefer using domain type validation over custom checks:

```go
// GOOD: Uses domain validation
return validation.All{
    validation.Name("userType", u.UserType),    // Validates against valid user types
    validation.Name("status", u.Status),        // Validates against valid statuses
}.Validate(ctx)

// AVOID: Custom validation that duplicates domain logic
return validation.All{
    validation.Name("userType", validation.NotEmptyString(string(u.UserType))),  // Just length check
}.Validate(ctx)
```

## Error Handling

### Named Errors

Use `validation.Name()` to provide context in error messages:

```go
return validation.All{
    validation.Name("username", validation.NotEmptyString(user.Username)),
    validation.Name("email", validation.NotEmptyString(user.Email)),
}.Validate(ctx)

// Error: "username: string is empty"
// Error: "email: string is empty"
```

### Custom Error Messages

```go
validation.HasValidationFunc(func(ctx context.Context) error {
    if user.Age < 18 {
        return errors.New(ctx, "user must be at least 18 years old")
    }
    return nil
})
```

### Error Wrapping

```go
if err := validator.Validate(ctx); err != nil {
    return errors.Wrapf(ctx, err, "validation failed for request")
}
```

## Best Practices

### 1. Prefer Domain Type Validation

```go
// GOOD: Uses domain type's built-in validation
validation.Name("category", u.Category)

// AVOID: Manual validation that might miss business rules
validation.Name("category", validation.NotEmptyString(string(u.Category)))
```

### 2. Use Descriptive Names

```go
// GOOD: Clear field names
validation.Name("userIdentifier", u.UserIdentifier)
validation.Name("contactMethod", u.ContactMethod)

// AVOID: Generic or unclear names
validation.Name("field1", u.UserIdentifier)
validation.Name("type", u.ContactMethod)
```

### 3. Group Related Validations

```go
return validation.All{
    // Required fields
    validation.Name("userID", r.UserID),
    validation.Name("action", r.Action),

    // Permission validation
    validation.Name("permissions", r.Permissions),
    validation.Name("role", r.Role),

    // Conditional validation based on action type
    validation.HasValidationFunc(func(ctx context.Context) error {
        return r.validateActionSpecificFields(ctx)
    }),
}.Validate(ctx)
```

### 4. Keep Validation Methods Simple

```go
func (r Request) Validate(ctx context.Context) error {
    // Simple, declarative validation
    return validation.All{
        validation.Name("field1", r.Field1),
        validation.Name("field2", r.Field2),
        validation.Name("complex", validation.HasValidationFunc(r.validateComplexRules)),
    }.Validate(ctx)
}

func (r Request) validateComplexRules(ctx context.Context) error {
    // Complex logic extracted to separate method
    // ... implementation
}
```

### 5. Handle Empty vs Invalid Values

```go
// For optional fields that must be valid when present
validation.Any{
    validation.StringEquals(""),                  // Empty is OK
    validation.Name("url", validation.StringURL(r.URL)), // OR must be valid URL
}

// For at-least-one-required scenarios
validation.Any{
    validation.Name("email", validation.NotEmptyString(r.Email)),
    validation.Name("phone", validation.NotEmptyString(r.Phone)),
}
```

## Common Examples

### Search Request Validation (OR Logic)

```go
func (r SearchRequest) Validate(ctx context.Context) error {
    return validation.Any{
        validation.Name("name", validation.NotEmptyString(r.Name)),
        validation.Name("category", r.Category),
        validation.Name("status", r.Status),
        validation.Name("userID", r.UserID),
        validation.Name("dateRange", r.DateRange),
    }.Validate(ctx)
}
```

### Complex Business Logic Validation

```go
func (r CreateOrderRequest) Validate(ctx context.Context) error {
    return validation.All{
        validation.Name("customerID", r.CustomerID),
        validation.Name("productID", r.ProductID),
        validation.Name("quantity", validation.HasValidationFunc(func(ctx context.Context) error {
            if r.Quantity <= 0 {
                return errors.Errorf(ctx, "quantity must be greater than 0")
            }
            return nil
        })),
        validation.Name("price", validation.HasValidationFunc(func(ctx context.Context) error {
            if r.Price != nil && r.Price.Amount <= 0 {
                return errors.Errorf(ctx, "price must be greater than 0")
            }
            return nil
        })),
    }.Validate(ctx)
}
```

### Nested Structure Validation

```go
func (p Project) Validate(ctx context.Context) error {
    return validation.All{
        validation.Name("name", validation.NotEmptyString(p.Name)),
        validation.Name("owner", p.Owner),
        validation.Name("tasks", p.Tasks),
    }.Validate(ctx)
}
```

## Integration with Error System

The validation framework integrates with the project's error handling:

```go
import (
    "github.com/bborbe/errors"
    "github.com/bborbe/validation"
)

// Domain types use validation.Error for consistent error classification
func (s Status) Validate(ctx context.Context) error {
    validStatuses := []Status{"active", "inactive", "pending"}
    for _, validStatus := range validStatuses {
        if s == validStatus {
            return nil
        }
    }
    return errors.Wrapf(ctx, validation.Error, "status(%s) is invalid", s)
}
```

This guide should help you implement consistent, maintainable validation throughout your Go codebase.