# Go Concurrency Patterns

`github.com/bborbe/run` and `github.com/bborbe/collection` — project-standard goroutine management.

## Core Rule: `go func()` Is a Smell

### RULE go-concurrency/no-raw-go-func (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go file uses the raw `go func() { ... }()` / `go someMethod(...)` syntax outside `main.go` / top-level entry points — instead of one of the `github.com/bborbe/run` strategies (`CancelOnFirstErrorWait`, `CancelOnFirstFinishWait`, `All`, `Sequential`).
**Enforcement**: `rules/go/no-raw-go-func.yml`
**Why**: Raw goroutines have three failure modes the `run` package solves: (1) they leak when the parent context is cancelled but the goroutine doesn't observe it; (2) they race when the parent function returns before the goroutine writes its result; (3) error propagation requires hand-rolled channels + `sync.WaitGroup` that drift toward subtle deadlocks. `run.CancelOnFirstErrorWait` wires context cancellation, error aggregation, and synchronization in one call — every consumer learns the same primitives, refactors stay safe, and goroutine lifetimes are explicit at the type signature.

#### Bad

```go
// Goroutine leaks on error — no cancellation, no wait, no error propagation
go func() { results <- doWork(ctx) }()

// And worse — multiple raw goroutines with hand-rolled sync.WaitGroup
var wg sync.WaitGroup
for _, item := range items {
	wg.Add(1)
	go func(it Item) {
		defer wg.Done()
		_ = process(ctx, it) // error swallowed
	}(item)
}
wg.Wait()
```

#### Good

```go
// run.CancelOnFirstErrorWait — context cancellation, error propagation, deterministic wait
return run.CancelOnFirstErrorWait(ctx, producer, consumer)

// For parallel processing of a slice, use run.All
return run.All(ctx, fns...)
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

### RULE go-concurrency/channel-closed-by-sender-only (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go file calls `close(ch)` on a channel that was passed in as a function parameter from elsewhere — i.e. closed by a consumer/receiver rather than by the goroutine that produces values into it.
**Enforcement**: judgment (ast-grep follow-up: `close(X)` where `X` is a parameter type `chan T` or `chan<- T`; the agent rules in whether the function is the producer or consumer based on whether it sends into `X`)
**Why**: Closing a channel from the receiver side is a textbook race — the sender may still be writing when the close happens, producing `send on closed channel` panic. The Go convention is: **the producer owns the channel and is the only one allowed to close it.** Receivers learn of "no more values" via `for v := range ch` or the `comma-ok` idiom (`v, ok := <-ch`), never by closing themselves. Multi-producer cases use `sync.WaitGroup` + a single dedicated closer goroutine, not concurrent closes (which also panic).

#### Bad

```go
// Consumer closes the channel — race against the producer's still-pending send
func consume(items <-chan Item) {
	for item := range items {
		process(item)
	}
	close(items) // ← wrong direction; would also be a compile error on `<-chan`
}
```

#### Good

```go
// Producer closes; consumer ranges and exits naturally when the channel closes
func produce(ctx context.Context, out chan<- Item) error {
	defer close(out) // ← producer owns the close
	for _, raw := range source {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case out <- transform(raw):
		}
	}
	return nil
}

func consume(in <-chan Item) {
	for item := range in {
		process(item)
	}
}
```


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

1. Never `go func()` — use `run.CancelOnFirstErrorWait` (canonicalised as `go-concurrency/no-raw-go-func`)
2. Caller owns the channel, passes `chan<- T` as parameter
3. Producer closes bounded channels (`defer close(ch)`) (canonicalised as `go-concurrency/channel-closed-by-sender-only`)
4. Always check `ctx.Done()` in consumer loops (cross-references `go-context/cancel-check-in-loop`)
5. Never close channel in unbounded/polling producers

> Note: an earlier revision listed a sixth rule "Capture loop variables by value (`x := x`)". That rule was removed because Go 1.22+ fixed loop-variable capture semantics — the variable is now scoped per iteration. For pre-1.22 projects, the `x := x` workaround is still required; this guide assumes Go 1.22+.

## Antipatterns

See the `#### Bad` blocks under each `### RULE` above for the canonical antipattern shapes. Summary:

- **Raw `go func()`** — `go-concurrency/no-raw-go-func` (leaks, races, hand-rolled `sync.WaitGroup` deadlocks).
- **Consumer closes channel** — `go-concurrency/channel-closed-by-sender-only` (panics on still-pending sends).
- **Unbounded producer with `defer close(ch)`** — bounded-shape primitive misapplied; the polling producer's `defer close` fires when the function returns on ctx-cancel, but the consumer goroutine may still be reading and panic on subsequent sends from anywhere else in the codebase.
- **Hidden `Results()` channel-returning method** — anti-pattern shown in Channel Ownership above; pass `chan<- T` as a parameter instead so ownership is explicit at the call site.
