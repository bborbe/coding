# Go Context Cancellation in For Loops

Long-running loops may ignore cancellation until they finish. Add a
non-blocking context check in each iteration to ensure fast shutdown and
deadline compliance.

## Core Pattern

``` go
for _, item := range items {
    select {
    case <-ctx.Done():
        return errors.Wrap(ctx, ctx.Err(), "context cancelled during processing")
    default:
    }

    // Process item...
}
```

## Key Points

-   Use a non-blocking `select` with `default`.
-   Place the cancellation check at the top of the loop.
-   Wrap errors with clear context and include `ctx.Err()`.

## When to Apply

-   Large collections
-   Expensive per-item work
-   Retry loops with backoff
-   Paginated API callbacks
-   Any loop with significant total runtime

## Examples

### Processing Items

``` go
for _, item := range items {
    select {
    case <-ctx.Done():
        return errors.Wrap(ctx, ctx.Err(), "context cancelled")
    default:
    }

    if err := process(ctx, item); err != nil {
        return errors.Wrap(ctx, err, "process item")
    }
}
```

### Retry Loop

``` go
for attempt := 0; attempt < maxRetries; attempt++ {
    select {
    case <-ctx.Done():
        return errors.Wrap(ctx, ctx.Err(), "context cancelled during retry")
    default:
    }

    if attempt > 0 {
        time.Sleep(time.Duration(1<<attempt) * time.Second)
    }

    if err := do(ctx); err != nil {
        lastErr = err
        continue
    }
    return nil
}
return lastErr
```

### Paginated Callbacks

``` go
err := req.Pages(ctx, func(page *Page) error {
    for _, item := range page.Items {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        // Process item...
    }
    return nil
})
```

## Anti-Patterns

**Blocking check**

``` go
<-ctx.Done() // Wrong: blocks if context never cancels
```

**Checking after work**

``` go
process(ctx, item)
// Suboptimal: cancellation checked too late
```

**Missing context**

``` go
return ctx.Err() // Not descriptive
```

## Why This Matters

Without context cancellation checks, loops:
- **Prevent graceful shutdown** - SIGKILL leaves data inconsistent
- **Waste resources** - Cancelled requests still consume CPU/network/DB
- **Break SLAs** - Timed-out work clogs goroutine pools, cascades latency
- **Cost money** - Autoscalers react to artificial load

**Example:** 10,000 items × 100ms = 16 minutes. Without checks, cancelling has no effect.

## Testing

### Cancel Mid-Loop
```go
It("stops early when context cancelled", func() {
    ctx, cancel := context.WithCancel(ctx)
    processed := 0

    go func() {
        time.Sleep(10 * time.Millisecond)
        cancel()
    }()

    err := processItems(ctx, items, func(item Item) {
        processed++
        time.Sleep(5 * time.Millisecond)
    })

    Expect(err).To(MatchError(context.Canceled))
    Expect(processed).To(BeNumerically("<", len(items)))
})
```

### Deadline Enforcement
```go
It("respects deadline in long loop", func() {
    ctx, cancel := context.WithTimeout(ctx, 50*time.Millisecond)
    defer cancel()

    err := processLargeCollection(ctx, largeItems)

    Expect(err).To(MatchError(context.DeadlineExceeded))
})
```

**Rule:** If a loop runs >few milliseconds, cancellation is mandatory.
