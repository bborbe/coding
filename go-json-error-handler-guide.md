# JSON Error Handler Guide

## Overview

This guide covers the standardized JSON error handler pattern from `github.com/bborbe/http` for returning structured error responses in HTTP APIs. Use this instead of plain text errors to enable clients to parse and handle errors programmatically.

**See also:**
- [go-http-handler-refactoring-guide.md](go-http-handler-refactoring-guide.md) - HTTP handler organization and architectural patterns
- [go-factory-pattern.md](go-factory-pattern.md) - Factory function patterns for handler creation

## When to Use

| Scenario | Handler |
|----------|---------|
| Public APIs, MCP tools, external clients | `NewJSONErrorHandler` |
| Internal services with log access | `NewErrorHandler` (plain text) |
| Database transactions (update) | `NewJSONUpdateErrorHandlerTx` |
| Database transactions (read-only) | `NewJSONViewErrorHandlerTx` |

**Default choice**: Use `NewJSONErrorHandler` for all new HTTP handlers. The structured response format improves debugging and client integration.

## Error Response Structure

All JSON errors follow this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "columnGroup '' is unknown",
    "details": {
      "field": "columnGroup",
      "expected": "day|week|month|year"
    }
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | Error type identifier |
| `message` | string | Yes | Human-readable error message |
| `details` | map[string]string | No | Structured context data |

## Standard Error Codes

| Code | HTTP Status | Usage |
|------|-------------|-------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters, malformed input |
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `UNAUTHORIZED` | 401 | Authentication required or failed |
| `FORBIDDEN` | 403 | Authenticated but insufficient permissions |
| `INTERNAL_ERROR` | 500 | Unexpected server errors (default) |

Use constants from the library:

```go
libhttp.ErrorCodeValidation   // "VALIDATION_ERROR"
libhttp.ErrorCodeNotFound     // "NOT_FOUND"
libhttp.ErrorCodeUnauthorized // "UNAUTHORIZED"
libhttp.ErrorCodeForbidden    // "FORBIDDEN"
libhttp.ErrorCodeInternal     // "INTERNAL_ERROR"
```

## Basic Usage

### Simple JSON Error Handler

```go
handler := libhttp.NewJSONErrorHandler(
    libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error {
        // Your handler logic
        if err != nil {
            return err // Returns 500 INTERNAL_ERROR by default
        }
        return nil
    }),
)
```

### Error with Status Code Only

Use `WrapWithStatusCode` when you only need a custom HTTP status:

```go
if resource == nil {
    return libhttp.WrapWithStatusCode(
        errors.New(ctx, "user not found"),
        http.StatusNotFound,
    )
}
// Returns: 404 with code "INTERNAL_ERROR" (no code specified)
```

### Error with Code and Status

Use `WrapWithCode` for typed error codes:

```go
if columnGroup == "" {
    return libhttp.WrapWithCode(
        errors.New(ctx, "columnGroup is required"),
        libhttp.ErrorCodeValidation,
        http.StatusBadRequest,
    )
}
```

**Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "columnGroup is required"
  }
}
```

### Error with Structured Details

Use `WrapWithDetails` to add context:

```go
if columnGroup == "" {
    return libhttp.WrapWithDetails(
        errors.New(ctx, "columnGroup '' is unknown"),
        libhttp.ErrorCodeValidation,
        http.StatusBadRequest,
        map[string]string{
            "field":    "columnGroup",
            "received": columnGroup,
            "expected": "day|week|month|year",
        },
    )
}
```

**Response:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "columnGroup '' is unknown",
    "details": {
      "field": "columnGroup",
      "received": "",
      "expected": "day|week|month|year"
    }
  }
}
```

## Transaction Handlers

For database operations with automatic transaction management:

### Update Operations (Read-Write)

```go
handler := libhttp.NewJSONUpdateErrorHandlerTx(
    db,
    libhttp.WithErrorTxFunc(func(ctx context.Context, tx libkv.Tx, resp http.ResponseWriter, req *http.Request) error {
        // Transaction commits on nil return, rolls back on error
        return nil
    }),
)
```

### Read-Only Operations

```go
handler := libhttp.NewJSONViewErrorHandlerTx(
    db,
    libhttp.WithErrorTxFunc(func(ctx context.Context, tx libkv.Tx, resp http.ResponseWriter, req *http.Request) error {
        // Read-only transaction
        return nil
    }),
)
```

## Factory Pattern Integration

Combine with the factory pattern for clean dependency injection:

**pkg/handler/search.go:**
```go
func NewSearchHandler(store SearchStore) libhttp.WithError {
    return libhttp.WithErrorFunc(func(ctx context.Context, resp http.ResponseWriter, req *http.Request) error {
        query := req.URL.Query().Get("q")
        if query == "" {
            return libhttp.WrapWithDetails(
                errors.New(ctx, "search query is required"),
                libhttp.ErrorCodeValidation,
                http.StatusBadRequest,
                map[string]string{"field": "q", "reason": "missing_required_parameter"},
            )
        }

        results, err := store.Search(ctx, query)
        if err != nil {
            return errors.Wrap(ctx, err, "search failed")
        }

        return libhttp.SendJSONResponse(ctx, resp, results, http.StatusOK)
    })
}
```

**pkg/factory/factory.go:**
```go
func CreateSearchHandler(store SearchStore) http.Handler {
    return libhttp.NewJSONErrorHandler(handler.NewSearchHandler(store))
}
```

**main.go:**
```go
router.Path("/api/search").Handler(factory.CreateSearchHandler(searchStore))
```

## Migration from Plain Text Errors

### Before (Plain Text)

```go
// Returns: "request failed: columnGroup '' is unknown"
handler := libhttp.NewErrorHandler(myHandler)
```

### After (JSON)

```go
// Returns: {"error": {"code": "INTERNAL_ERROR", "message": "columnGroup '' is unknown"}}
handler := libhttp.NewJSONErrorHandler(myHandler)
```

### Transaction Migration

```go
// Before
handler := libhttp.NewUpdateErrorHandlerTx(db, myHandler)

// After
handler := libhttp.NewJSONUpdateErrorHandlerTx(db, myHandler)
```

## Common Patterns

### Validation Error Pattern

```go
func validateRequest(ctx context.Context, req *Request) error {
    if req.Email == "" {
        return libhttp.WrapWithDetails(
            errors.New(ctx, "email is required"),
            libhttp.ErrorCodeValidation,
            http.StatusBadRequest,
            map[string]string{"field": "email", "reason": "required"},
        )
    }
    if !isValidEmail(req.Email) {
        return libhttp.WrapWithDetails(
            errors.New(ctx, "invalid email format"),
            libhttp.ErrorCodeValidation,
            http.StatusBadRequest,
            map[string]string{"field": "email", "reason": "invalid_format", "received": req.Email},
        )
    }
    return nil
}
```

### Not Found Pattern

```go
user, err := store.FindByID(ctx, userID)
if err != nil {
    return errors.Wrap(ctx, err, "find user failed")
}
if user == nil {
    return libhttp.WrapWithDetails(
        errors.Newf(ctx, "user %s not found", userID),
        libhttp.ErrorCodeNotFound,
        http.StatusNotFound,
        map[string]string{"resource": "user", "id": string(userID)},
    )
}
```

### Authorization Pattern

```go
if !hasPermission(ctx, user, resource) {
    return libhttp.WrapWithDetails(
        errors.New(ctx, "insufficient permissions"),
        libhttp.ErrorCodeForbidden,
        http.StatusForbidden,
        map[string]string{"resource": resource.Type, "action": "write"},
    )
}
```

### Internal Error (Default)

For unexpected errors, don't wrap with code - let the handler use defaults:

```go
result, err := externalService.Call(ctx)
if err != nil {
    // Returns 500 INTERNAL_ERROR automatically
    return errors.Wrap(ctx, err, "external service call failed")
}
```

## Details Field Conventions

Use consistent keys in the `details` map:

| Key | Description | Example |
|-----|-------------|---------|
| `field` | Field that caused the error | `"email"` |
| `reason` | Machine-readable reason | `"required"`, `"invalid_format"` |
| `received` | Value that was received | `""`, `"not-an-email"` |
| `expected` | Expected value or format | `"valid email address"` |
| `resource` | Resource type for not found | `"user"`, `"order"` |
| `id` | Resource identifier | `"user-123"` |
| `action` | Action being attempted | `"read"`, `"write"`, `"delete"` |
| `limit` | Limit that was exceeded | `"100"` |
| `current` | Current value | `"150"` |

## Testing

### Unit Testing Handlers

```go
func TestSearchHandler_ValidationError(t *testing.T) {
    g := NewGomegaWithT(t)

    store := &mocks.SearchStore{}
    handler := libhttp.NewJSONErrorHandler(NewSearchHandler(store))

    req := httptest.NewRequest("GET", "/search", nil) // Missing ?q=
    resp := httptest.NewRecorder()

    handler.ServeHTTP(resp, req)

    g.Expect(resp.Code).To(Equal(http.StatusBadRequest))
    g.Expect(resp.Header().Get("Content-Type")).To(Equal("application/json"))

    var errResp libhttp.ErrorResponse
    json.NewDecoder(resp.Body).Decode(&errResp)

    g.Expect(errResp.Error.Code).To(Equal("VALIDATION_ERROR"))
    g.Expect(errResp.Error.Details["field"]).To(Equal("q"))
}
```

### Testing Error Parsing (Client Side)

```go
func TestClientParsesJSONError(t *testing.T) {
    g := NewGomegaWithT(t)

    // Simulated error response
    body := `{"error":{"code":"NOT_FOUND","message":"user not found","details":{"id":"123"}}}`

    var errResp libhttp.ErrorResponse
    err := json.Unmarshal([]byte(body), &errResp)

    g.Expect(err).To(BeNil())
    g.Expect(errResp.Error.Code).To(Equal("NOT_FOUND"))
    g.Expect(errResp.Error.Message).To(Equal("user not found"))
    g.Expect(errResp.Error.Details["id"]).To(Equal("123"))
}
```

## Anti-Patterns

### Don't: Use Wrong Error Code for Status

```go
// Wrong: 404 status but VALIDATION_ERROR code
return libhttp.WrapWithCode(
    errors.New(ctx, "user not found"),
    libhttp.ErrorCodeValidation, // Should be ErrorCodeNotFound
    http.StatusNotFound,
)
```

### Don't: Expose Internal Details

```go
// Wrong: Exposes database details
return libhttp.WrapWithDetails(
    err,
    libhttp.ErrorCodeInternal,
    http.StatusInternalServerError,
    map[string]string{
        "query": "SELECT * FROM users WHERE id = ?", // Security risk!
        "connection": "postgres://user:pass@host/db", // Never expose!
    },
)
```

### Don't: Use Generic Messages

```go
// Wrong: Not helpful for debugging
return libhttp.WrapWithCode(
    errors.New(ctx, "error"),
    libhttp.ErrorCodeValidation,
    http.StatusBadRequest,
)

// Right: Specific and actionable
return libhttp.WrapWithDetails(
    errors.New(ctx, "date format invalid"),
    libhttp.ErrorCodeValidation,
    http.StatusBadRequest,
    map[string]string{
        "field": "from",
        "received": fromParam,
        "expected": "YYYY-MM-DD",
    },
)
```

## Quick Reference

### Import

```go
import libhttp "github.com/bborbe/http"
```

### Function Summary

| Function | Purpose |
|----------|---------|
| `NewJSONErrorHandler(handler)` | Wrap handler to return JSON errors |
| `NewJSONUpdateErrorHandlerTx(db, handler)` | JSON errors + update transaction |
| `NewJSONViewErrorHandlerTx(db, handler)` | JSON errors + read-only transaction |
| `WrapWithStatusCode(err, status)` | Add HTTP status to error |
| `WrapWithCode(err, code, status)` | Add error code and HTTP status |
| `WrapWithDetails(err, code, status, details)` | Add code, status, and details |

### Error Code Constants

```go
libhttp.ErrorCodeValidation   // "VALIDATION_ERROR" → 400
libhttp.ErrorCodeNotFound     // "NOT_FOUND" → 404
libhttp.ErrorCodeUnauthorized // "UNAUTHORIZED" → 401
libhttp.ErrorCodeForbidden    // "FORBIDDEN" → 403
libhttp.ErrorCodeInternal     // "INTERNAL_ERROR" → 500
```
