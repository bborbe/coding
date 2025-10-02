# HTTP Handler Refactoring Guide

## Overview

This guide helps developers refactor HTTP handlers in Go services from inline definitions in `main.go` to properly
organized handler packages. This refactoring improves code maintainability, testability, and follows established Go
service patterns.

## Why Refactor Handlers?

### Problems with Inline Handlers in main.go

- **Code Organization**: Business logic mixed with application bootstrap code
- **Maintainability**: Large, complex main.go files become hard to navigate
- **Testability**: Inline handlers are difficult to unit test in isolation
- **Reusability**: Handler logic can't be reused across different contexts
- **Consistency**: Different services have different patterns

### Benefits of Proper Handler Organization

- **Separation of Concerns**: Clear separation between handler logic and application setup
- **Testable Code**: Handlers can be unit tested with mocked dependencies
- **Consistent Patterns**: All services follow the same architecture
- **Maintainable Code**: Handler logic is easy to find and modify
- **Better Naming**: Descriptive names clarify handler functionality

## The Go Handler Pattern

### Directory Structure

```
service/
├── main.go
├── pkg/
│   ├── factory/
│   │   └── factory.go     # Factory methods for dependency injection
│   └── handler/
│       ├── handler_suite_test.go
│       ├── exists.go      # Individual handler files
│       ├── forward-invoice.go
│       └── forward-all-invoices.go
```

### Handler Function Signatures

**HTTP Error Handlers** (most common):

```go
func NewExistsHandler(dependencies...) libhttp.WithError {
    return libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error {
        // Handler logic here
        return nil
    })
}
```

**Background Task Handlers**:

```go
func NewForwardAllInvoicesHandler(dependencies...) run.Func {
    return func(ctx context.Context) error {
        // Background task logic here
        return nil
    }
}
```

**JSON API Handlers**:

```go
func NewDataHandler(dependencies...) libhttp.WithError {
    return libhttp.NewJsonHandler(libhttp.JsonHandlerFunc(func(ctx context.Context, req *http.Request) (interface{}, error) {
        // JSON response logic here
        return data, nil
    }))
}
```

### Factory Pattern

Factory methods in `pkg/factory/factory.go` handle dependency injection:

```go
func CreateExistsHandler(db libkv.DB) http.Handler {
    return libhttp.NewErrorHandler(handler.NewExistsHandler(db))
}

func CreateForwardAllInvoicesHandler(ctx context.Context, forwarder pkg.InvoiceForwarder) http.Handler {
    return libhttp.NewBackgroundRunHandler(ctx, handler.NewForwardAllInvoicesHandler(forwarder))
}
```

## Before/After Example

### Before: Inline Handler in main.go

```go
router.Path("/exists/{invoiceID:.+}").Handler(libhttp.NewErrorHandler(libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error {
    vars := mux.Vars(req)
    invoiceID := commerce.InvoiceID(vars["invoiceID"])
    if err := invoiceID.Validate(ctx); err != nil {
        return errors.Wrap(ctx, err, "validate failed")
    }
    libhttp.WriteAndGlog(resp, "invoice %s", invoiceID)

    commerceInvoiceStore := pkg.NewCommerceInvoiceStore(db)
    commerceInvoiceExists, err := commerceInvoiceStore.Exists(ctx, invoiceID)
    if err != nil {
        return errors.Wrapf(ctx, err, "view failed")
    }
    libhttp.WriteAndGlog(resp, "commerceInvoiceExists = %v", commerceInvoiceExists)

    // ... more logic
    return nil
})))
```

### After: Organized Handler

**pkg/handler/exists.go**:

```go
package handler

import (
    "context"
    "net/http"

    libkv "github.com/bborbe/kv"
    "github.com/bborbe/errors"
    libhttp "github.com/bborbe/http"
    "github.com/gorilla/mux"

    "your-org/your-service/pkg"
)

func NewExistsHandler(db libkv.DB) libhttp.WithError {
    return libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error {
        // ... more logic
        return nil
    })
}
```

**pkg/factory/factory.go**:

```go
func CreateExistsHandler(db libkv.DB) http.Handler {
    return libhttp.NewErrorHandler(handler.NewExistsHandler(db))
}
```

**main.go**:

```go
router.Path("/exists/{invoiceID:.+}").Handler(factory.CreateExistsHandler(db))
```

## Step-by-Step Refactoring Process

### 1. Identify Inline Handlers

Look for patterns like:

- `libhttp.NewErrorHandler(libhttp.WithErrorFunc(func(...) error { ... }))`
- `libhttp.NewBackgroundRunHandler(ctx, func(ctx context.Context) error { ... })`
- Large anonymous functions passed to router handlers

### 2. Create Handler Package Structure

```bash
mkdir -p pkg/handler
touch pkg/handler/handler_suite_test.go
```

### 3. Extract Handler Logic

For each inline handler:

1. **Create handler file**: Use descriptive kebab-case names (`forward-invoice.go`, `exists.go`)
2. **Extract function**: Move the handler logic to a `New[Purpose]Handler` function
3. **Return proper interface**: Use `libhttp.WithError` for HTTP handlers, `run.Func` for background tasks
4. **Add dependencies as parameters**: Instead of closures, pass dependencies explicitly

### 4. Create Factory Methods

In `pkg/factory/factory.go`:

1. **Add factory function**: `Create[Purpose]Handler` that handles dependency injection
2. **Wrap handler**: Use appropriate wrapper (`libhttp.NewErrorHandler`, `libhttp.NewBackgroundRunHandler`)
3. **Import handler package**: Add import for your handler package

### 5. Update main.go

Replace inline handlers with factory calls:

```go
// Before
router.Path("/endpoint").Handler(libhttp.NewErrorHandler(libhttp.WithErrorFunc(func(...) { ... })))

// After  
router.Path("/endpoint").Handler(factory.CreateEndpointHandler(dependencies...))
```

### 6. Choose Descriptive Names

Replace generic names with descriptive ones:

### 7. Clean Up Imports

Remove unused imports from all modified files:

```bash
make format  # This usually handles import cleanup
```

### 8. Run Tests

Validate the refactoring:

```bash
make test
make precommit
```

## Naming Conventions

### Handler Files

- Use kebab-case: `fetch-details.go`, `forward-invoice.go`
- Be descriptive: Avoid generic names like `handler.go`, `send.go`
- Use action-oriented names: `forward-`, `fetch-`, `list-`, `delete-`

### Handler Functions

- Pattern: `New[Purpose]Handler`
- Examples: `NewForwardInvoiceHandler`, `NewFetchDetailsHandler`
- Use PascalCase for function names

### Factory Functions

- Pattern: `Create[Purpose]Handler`
- Examples: `CreateForwardInvoiceHandler`, `CreateFetchDetailsHandler`

## Testing Guidelines

### Handler Testing

Create `*_test.go` files for handlers:

```go
func TestNewExistsHandler(t *testing.T) {
    // Create mocks
    db := &mocks.DB{}
    
    // Create handler
    handler := NewExistsHandler(db)
    
    // Test the handler
    // ...
}
```

### Integration Testing

Test the factory methods:

```go
func TestCreateExistsHandler(t *testing.T) {
    db := createTestDB()
    handler := factory.CreateExistsHandler(db)
    
    // Test with actual HTTP request
    // ...
}
```

## Common Patterns

### HTTP Error Handlers

Most common pattern for REST endpoints:

```go
func NewResourceHandler(store ResourceStore) libhttp.WithError {
    return libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error {
        // Handle HTTP request, return error for issues
        return nil
    })
}
```

### Background Task Handlers

For cron jobs or manual triggers:

```go
func NewProcessAllHandler(processor Processor) run.Func {
    return func(ctx context.Context) error {
        // Background processing logic
        return processor.ProcessAll(ctx)
    }
}
```

### JSON API Handlers

For REST APIs returning JSON:

```go
func NewDataHandler(fetcher DataFetcher) libhttp.WithError {
    return libhttp.NewJsonHandler(libhttp.JsonHandlerFunc(func(ctx context.Context, req *http.Request) (interface{}, error) {
        data, err := fetcher.Fetch(ctx)
        return data, err
    }))
}
```

## Migration Checklist

- [ ] All inline handlers moved to `pkg/handler/` files
- [ ] Factory methods created in `pkg/factory/factory.go`
- [ ] main.go updated to use factory methods
- [ ] Handler files use descriptive names
- [ ] Handler functions follow naming conventions
- [ ] Unused imports removed from all files
- [ ] Tests pass: `make test`
- [ ] Pre-commit checks pass: `make precommit`

## Reference Examples

### Pattern Variations

Different services may have slightly different patterns based on their needs, but all should follow the core principles:

1. Handlers in `pkg/handler/` package
2. Factory methods for dependency injection
3. Descriptive naming
4. Proper return types (`libhttp.WithError`, `run.Func`)
