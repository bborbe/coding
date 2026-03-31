# Go Concurrency Patterns

`github.com/bborbe/run` and `github.com/bborbe/collection` — project-standard goroutine management.

## Core Rule: `go func()` Is a Smell

Raw goroutines leak, race, and are hard to test. Use `run.CancelOnFirstErrorWait` instead.

```go
// Bad — goroutine leaks on error
go func() { results <- doWork(ctx) }()

// Good
return run.CancelOnFirstErrorWait(ctx, producer, consumer)
```

## `run` Package

`run.Func = func(context.Context) error`

| Function | Behaviour |
|----------|-----------|
| `run.CancelOnFirstErrorWait` | Cancels all on first error, waits for all |
| `run.CancelOnFirstFinishWait` | Cancels all when first finishes, waits |
| `run.All` | Runs all, aggregates all errors |
| `run.Sequential` | Stops on first error |

## Producer/Consumer — Unbounded (no close)

Use when producer polls indefinitely until ctx cancelled:

```go
func (s *syncLoop) Run(ctx context.Context) error {
    results := make(chan ScanResult, 1)
    return run.CancelOnFirstErrorWait(
        ctx,
        func(ctx context.Context) error {
            return s.scanner.Run(ctx, results) // never closes results
        },
        func(ctx context.Context) error {
            for {
                select {
                case <-ctx.Done():
                    return nil
                case result := <-results:
                    // process result
                }
            }
        },
    )
}
```

## Producer/Consumer — Bounded (with close)

Use when producer finishes a finite dataset:

```go
func process(ctx context.Context) error {
    ch := make(chan Item, runtime.NumCPU())
    return run.CancelOnFirstErrorWait(
        ctx,
        func(ctx context.Context) error {
            defer close(ch) // signals consumer we're done
            return fetchAll(ctx, ch)
        },
        func(ctx context.Context) error {
            for {
                select {
                case <-ctx.Done():
                    return ctx.Err()
                case item, ok := <-ch:
                    if !ok { return nil } // channel closed
                    if err := handle(ctx, item); err != nil { return err }
                }
            }
        },
    )
}
```

## Channel Ownership

**Caller creates and owns the channel. Pass `chan<- T` into producer.**

```go
// Good — caller owns channel, producer only sends
type Scanner interface {
    Run(ctx context.Context, results chan<- ScanResult) error
}

// Bad — hidden channel, forces two-method interface
type Scanner interface {
    Run(ctx context.Context) error
    Results() <-chan ScanResult // anti-pattern
}
```

## `collection` Package — Bounded Helpers

Require producer to `defer close(ch)`. Do NOT use for unbounded producers.

```go
// Process each item
err := collection.ChannelFnMap(ctx,
    func(ctx context.Context, ch chan<- Item) error {
        defer close(ch); return db.FetchAll(ctx, ch)
    },
    func(ctx context.Context, item Item) error { return process(ctx, item) },
)

// Collect to slice
items, err := collection.ChannelFnList(ctx,
    func(ctx context.Context, ch chan<- Item) error {
        defer close(ch); return db.FetchAll(ctx, ch)
    },
)
```

## Choosing the Right Tool

| Situation | Use |
|-----------|-----|
| Bounded dataset, process each item | `collection.ChannelFnMap` |
| Bounded dataset, collect to slice | `collection.ChannelFnList` |
| Unbounded polling loop | `run.CancelOnFirstErrorWait` + manual select |
| Multiple independent tasks | `run.CancelOnFirstErrorWait` or `run.All` |
| Sequential pipeline steps | `run.Sequential` |

## Gotcha: `CancelOnFirstErrorWait` + `errors.Is`

When ctx is cancelled, errors are joined with `errors.Join`. `errors.Is(err, context.Canceled)` may match even when the real error is a domain error.

Fix: use a domain sentinel:

```go
var errReachedUntil = errors.New("reached until")
if errors.Is(err, errReachedUntil) { return nil }
```

## Rules

1. Never `go func()` — use `run.CancelOnFirstErrorWait`
2. Caller owns the channel, passes `chan<- T` as parameter
3. Producer closes bounded channels (`defer close(ch)`)
4. Always check `ctx.Done()` in consumer loops
5. Never close channel in unbounded/polling producers
6. Capture loop variables by value: `x := x`
