# Go CQRS Command-Result Pattern

Send command via Kafka, get result automatically. Library: `github.com/bborbe/cqrs`.

## Core Flow

```
Producer                              Controller
1. NewCommand(op, initiator, id, ev)  3. CommandObjectExecutor.HandleCommand()
2. SendCommandObject() → cmd topic    4. WrapCommandObjectExecutorTxs auto-sends result
                                         → result topic
5. ResultProvider.ResultFor(ctx, cmd)
6. result.Success → done
```

## Kafka Topics (auto-derived from SchemaID)

```go
schemaID := cdb.SchemaID{Group: "core", Kind: "backtest", Version: "v1"}
// → core-backtest-v1-command-{branch}   commands in
// → core-backtest-v1-event-{branch}     state changes
// → core-backtest-v1-result-{branch}    command results (auto)
// → core-backtest-v1-history-{branch}   audit log
```

## Sending a Command

```go
command := commandCreator.NewCommand(operation, initiator, "", event)
commandObjectSender.SendCommandObject(ctx, cdb.CommandObject{
    Command:  command,
    SchemaID: schemaID,
})
```

## Result Sending (Automatic)

`RunCommandConsumerTx` wraps executors with `WrapCommandObjectExecutorTxs`.
No manual result sending. Success/failure published to result topic automatically.

```go
// Controller setup — result wrapping is built-in:
cdb.RunCommandConsumerTx(saramaClientProvider, syncProducer, db,
    schemaID, batchSize, branch, false, 24*time.Hour,
    run.NewTrigger(), commandObjectExecutors)
```

## Waiting for Result

```go
// In-process: channel-based
provider := cdb.NewResultChannelProviderForRequestID()
ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
defer cancel()
result, err := provider.ResultFor(ctx, command)
// result.Success, result.Message, result.RequestID

// Cross-process: consume result topic, match on RequestID
topic := schemaID.ResultTopic(branch)
```

## Skipping Invalid Commands

Return `cdb.ErrCommandObjectSkipped` when a command should be committed but not processed. Framework advances offset, sends no result.

```go
// BAD — silently swallows, no visibility
return nil, nil, nil
// BAD — emits a Failure on the result topic for every occurrence (noisy if caller is non-retryable)
return nil, nil, err
// GOOD — clean skip: no retry, no result emitted, offset advances
return nil, nil, errors.Wrapf(ctx, cdb.ErrCommandObjectSkipped, "reason: %v", err)
```

**Use for:** malformed data, validation failure, duplicates, wrong state, filtered out.
**NOT for:** transient errors (network, disk) — return normal error so the failure is visible on the result topic.

## Handler Errors Do Not Cause Kafka Replay

A common misconception: "If my handler returns `err`, kafka will replay the message forever." Not true for this framework.

The result-sender wrapper catches the handler error, emits a `ResultObjectFailure` to the `*-result` topic, and returns `nil` to the outer kafka consumer. The offset commits on the next batch tick. Each error is **one** Failure on the result topic — not an infinite replay.

```
Handler returns err
  ↓
Wrapper sends ResultObjectFailure to *-result topic
  ↓
Wrapper returns nil to outer message handler
  ↓
Kafka offset commits → next message processed
```

In normal error-handling paths, the only case where offsets do NOT commit is when the result-sender itself fails to publish (e.g. kafka producer broken) — that bubbles a real error and triggers the kafka library's redelivery semantics. Process-level failures (panic escaping the wrapper, SIGKILL, OOM) also skip the commit, but those are infrastructure concerns, not application-level error handling.

**Implications:**

- Returning `err` from a non-retryable condition (wrong state, validation failure) is **functionally safe** — no replay loop — but it produces a `Failure` on the result topic for every occurrence. If a publisher emits N copies of the same command (no state pre-filter, broker confirm retries, etc.) you get N `Failure` entries and N error log lines. Use `ErrCommandObjectSkipped` to avoid that.
- Returning `err` from a **transient** condition (network blip, disk full) is still the right choice — but understand it produces a single Failure result and a single error log, NOT an automatic retry. If you want retry, build it into the handler or the orchestration around it.

**Example pattern:** an order-processing handler returns an `InvalidStateError` whenever a command targets an order already in a terminal state (`Completed`, `Cancelled`). If the publisher does not pre-filter by state and emits N duplicate commands for the same order, the result topic gets N `Failure` entries and the log gets N error lines — none of them retries, all distinct messages. Fix: treat terminal states as an idempotent skip (`ErrCommandObjectSkipped`) rather than an error.

## Rules

### RULE go-cqrs/auto-tx-wrapper-no-manual-wrap (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go CQRS consumer in this framework manually wraps its command executor with `kv.NewTransactionMiddleware` / similar transaction-management code instead of using `RunCommandConsumerTx` (which auto-wraps).
**Enforcement**: `rules/go/auto-tx-wrapper-no-manual-wrap.yml` flags any `call_expression` invoking `NewTransactionMiddleware`. The agent confirms whether the wrapping is adjacent to a `RunCommandConsumerTx` registration (the specific double-wrap anti-pattern).
**Why**: `RunCommandConsumerTx` is the framework's transaction-management entry point. It opens a kv transaction per command, hands the txn-bound store to the executor, commits on success, rolls back on error — exactly once per message, in the exact order the framework expects. Manual wrapping duplicates that logic and introduces subtle drift: the manual wrapper may rollback while the framework also rolls back (double-rollback panic on closed txn), or may commit while the framework expects rollback semantics on a downstream failure. The bug surfaces as "this CQRS consumer occasionally double-applies state changes" — hard to reproduce, harder to diagnose.

#### Bad

```go
// Manual transaction wrapping — duplicates RunCommandConsumerTx's contract
wrappedExecutor := kv.NewTransactionMiddleware(db, executor)
err := cdb.RunCommandConsumerTx(saramaClientProvider, syncProducer, db,
    schemaID, wrappedExecutor) // double-wrapping smell — Tx variant already wraps
```

#### Good

```go
// Tx auto-wrapped — framework owns the transaction lifecycle
err := cdb.RunCommandConsumerTx(saramaClientProvider, syncProducer, db,
    schemaID, executor)
```

### RULE go-cqrs/skipped-not-nil-for-non-retryable (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go CQRS executor handles a *non-retryable* condition (idempotent skip, command targets an already-terminal entity, duplicate detected, validation against immutable state failed) by returning `nil` or an arbitrary `err` instead of `ErrCommandObjectSkipped`.
**Enforcement**: judgment (semantic — distinguishing "non-retryable skip" from "transient error worth a Failure result" requires reading the executor's intent)
**Why**: Three different result-topic outcomes hinge on the executor's return:
- `nil` → `ResultObjectSuccess` published. The publisher thinks the command succeeded.
- `err` → `ResultObjectFailure` published, one per occurrence. Duplicate publisher emissions produce N Failure entries + N error log lines + N noisy alerts.
- `ErrCommandObjectSkipped` → no result sent, offset commits silently.

For non-retryable conditions (terminal state, duplicate, immutable-validation failure), only `Skipped` is correct: publishing `Success` lies to the publisher; publishing `Failure` spams the result topic. The classic bug: an order processor returns `InvalidStateError` for `Completed` orders. Publisher retries 50× on a network blip → result topic gets 50 Failure entries and the on-call sees 50 alerts for an idempotent no-op.

#### Bad (variant A — `return err`)

```go
func (e *Executor) Execute(ctx context.Context, cmd Command) error {
	order := e.store.Get(cmd.OrderID)
	if order.Status == Completed {
		// produces noisy Failure result; N duplicate commands → N Failure entries +
		// N error log lines + N alerts on the on-call's pager
		return errors.New("order already completed")
	}
	// ... real work
}
```

#### Bad (variant B — `return nil`)

```go
func (e *Executor) Execute(ctx context.Context, cmd Command) error {
	order := e.store.Get(cmd.OrderID)
	if order.Status == Completed {
		// publishes Success — lies to the publisher; downstream code thinks
		// the command actually advanced the entity state
		return nil
	}
	// ... real work
}
```

#### Good

```go
func (e *Executor) Execute(ctx context.Context, cmd Command) error {
	order := e.store.Get(cmd.OrderID)
	if order.Status == Completed {
		// silent idempotent skip, no result published, offset commits cleanly
		return cdb.ErrCommandObjectSkipped
	}
	// ... real work
}
```

### Other rules (judgment-tier, not yet canonicalised as RULE blocks)

- Never consume event topic to wait for command results — use result topic
- Normal `err` returns are NOT retried by the framework; they emit one Failure result and commit the offset — same offset behaviour as Skipped, different result-topic behaviour
- `SendResultEnabled() == false` + no error → no result sent
- Context timeout → `ResultFor()` returns `Success: false`

## Checklist

- [ ] Command has RequestID for correlation
- [ ] Controller uses `RunCommandConsumerTx` (auto-wraps)
- [ ] Consumer reads result topic, not event topic
- [ ] Timeout via context, not manual timer
- [ ] Non-retryable situations return `ErrCommandObjectSkipped`, not `nil`
