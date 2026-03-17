# Go Error Wrapping with github.com/bborbe/errors

All errors must be wrapped with context using `github.com/bborbe/errors`.
Never use `fmt.Errorf` or bare `return err`. The library enriches errors
with structured data from `context.Context`, enabling better debugging
and observability.

## Why Context Matters

Every wrapping function accepts `ctx context.Context` as its first argument.
Internally, `AddContextDataToError(ctx, ...)` extracts structured data
previously added via `errors.AddToContext(ctx, key, value)` and attaches
it to the error. Using `context.Background()` loses all this data — the
wrapping becomes pointless.

**Never fabricate context.** If a function lacks `ctx`, add it as a
parameter and propagate from callers.

## API Reference

| Function | Purpose | Signature |
|----------|---------|-----------|
| `Wrapf` | Wrap existing error with formatted message | `Wrapf(ctx, err, format, args...) error` |
| `Wrap` | Wrap existing error with plain message | `Wrap(ctx, err, message) error` |
| `New` | Create new error with plain message | `New(ctx, message) error` |
| `Errorf` | Create new error with formatted message | `Errorf(ctx, format, args...) error` |
| `AddToContext` | Add structured data to ctx for error enrichment | `AddToContext(ctx, key, value) context.Context` |

All `Wrap`/`Wrapf` functions return `nil` when `err` is `nil`.

## Core Patterns

### Wrapping an Existing Error

```go
result, err := s.repo.Fetch(ctx, id)
if err != nil {
    return nil, errors.Wrapf(ctx, err, "fetch account %s", id)
}
```

### Creating a New Error

```go
return errors.Errorf(ctx, "unsupported period type: %s", periodType)
```

### Sentinel Errors

Package-level sentinel errors use stdlib `errors` aliased as `stderrors`
to avoid collision with `github.com/bborbe/errors`:

```go
import (
    stderrors "errors"

    "github.com/bborbe/errors"
)

var ErrNotFound = stderrors.New("not found")
```

### Enriching Context with Data

```go
func (s *svc) Process(ctx context.Context, accountID string) error {
    ctx = errors.AddToContext(ctx, "accountID", accountID)
    // Any error wrapped from here on carries accountID
    result, err := s.dep.Do(ctx)
    if err != nil {
        return errors.Wrapf(ctx, err, "process account")
    }
    return nil
}
```

## Key Rules

1. **Never bare `return err`** — always `errors.Wrapf(ctx, err, "description")`
2. **Never `fmt.Errorf`** — use `errors.Wrapf` (wrapping) or `errors.Errorf` (new error)
3. **Never `context.Background()` in business logic** — add `ctx context.Context` parameter instead
4. **Multi-return wrapping** — `return nil, errors.Wrapf(ctx, err, "...")`
5. **Inner closures** — do NOT wrap inside callbacks (`db.Update`, `filepath.WalkDir`) when the outer scope already wraps
6. **Remove unused imports** — after replacing `fmt.Errorf`, remove `"fmt"` if unused
7. **Sentinel errors** — `var ErrXxx = stderrors.New("...")` with aliased stdlib import

## Where context.Background() Is Allowed

- `main.go` (entry point)
- Test files (`*_test.go`)
- Top-level goroutine spawners in main

Never in:
- Business logic (`pkg/`)
- Handlers (`pkg/handler/`)
- Factory files (`pkg/factory/`)
- Any method on a service struct

## Examples

### Fix: Function Missing ctx

```go
// WRONG — fabricating context
func (s *svc) validate(input string) error {
    return errors.Errorf(context.Background(), "invalid: %s", input)
}

// CORRECT — add ctx parameter, update all callers
func (s *svc) validate(ctx context.Context, input string) error {
    return errors.Errorf(ctx, "invalid: %s", input)
}
```

### Fix: Replace fmt.Errorf

```go
// WRONG
return fmt.Errorf("fetch failed: %w", err)

// CORRECT — wrapping existing error
return errors.Wrapf(ctx, err, "fetch failed")
```

### Fix: New Error Without Cause

```go
// WRONG
return fmt.Errorf("unknown type: %s", t)

// CORRECT — no cause to wrap
return errors.Errorf(ctx, "unknown type: %s", t)
```

### Inner Closures — Do Not Double-Wrap

```go
// Outer function already wraps
func (s *svc) Save(ctx context.Context, data Data) error {
    err := s.db.Update(func(tx *bolt.Tx) error {
        // Inner closure: bare return is OK here
        // The outer Wrapf below will add context
        return tx.Bucket(key).Put(id, encoded)
    })
    if err != nil {
        return errors.Wrapf(ctx, err, "save data %s", data.ID)
    }
    return nil
}
```

## Anti-Patterns

**Bare return**
```go
if err != nil {
    return err // No context, no stack trace
}
```

**fmt.Errorf**
```go
return fmt.Errorf("failed: %w", err) // No context data, no stack trace
```

**context.Background() in business logic**
```go
return errors.Wrapf(context.Background(), err, "failed")
// Loses all structured data from caller's context
```

**Double-wrapping inner closures**
```go
err := s.db.Update(func(tx *bolt.Tx) error {
    if err := put(tx); err != nil {
        return errors.Wrapf(ctx, err, "put") // Redundant — outer wraps too
    }
    return nil
})
return errors.Wrapf(ctx, err, "update") // Double-wrapped
```

## Testing

### Verify Error Messages

```go
It("wraps error with context", func() {
    dep.DoReturns(stderrors.New("connection refused"))

    _, err := svc.Process(ctx, "acc-123")

    Expect(err).To(HaveOccurred())
    Expect(err.Error()).To(ContainSubstring("process account"))
    Expect(err.Error()).To(ContainSubstring("connection refused"))
})
```

### Verify Context Data Attached

```go
It("attaches context data to error", func() {
    ctx = errors.AddToContext(ctx, "requestID", "req-456")
    dep.DoReturns(stderrors.New("timeout"))

    _, err := svc.Process(ctx, "acc-123")

    Expect(errors.DataFromError(err)).To(HaveKeyWithValue("requestID", "req-456"))
})
```

### Verify Sentinel Error

```go
It("returns ErrNotFound for missing item", func() {
    _, err := svc.Get(ctx, "nonexistent")

    Expect(err).To(MatchError(ErrNotFound))
})
```
