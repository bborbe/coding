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

- Never consume event topic to wait for command results — use result topic
- `RunCommandConsumerTx` wraps executors automatically — don't wrap manually
- `ErrCommandObjectSkipped` skips silently (no result sent) — use for non-retryable situations
- Normal `err` returns are NOT retried by the framework; they emit one Failure result and commit the offset — same offset behaviour as Skipped, different result-topic behaviour
- `SendResultEnabled() == false` + no error → no result sent
- Context timeout → `ResultFor()` returns `Success: false`

## Checklist

- [ ] Command has RequestID for correlation
- [ ] Controller uses `RunCommandConsumerTx` (auto-wraps)
- [ ] Consumer reads result topic, not event topic
- [ ] Timeout via context, not manual timer
- [ ] Non-retryable situations return `ErrCommandObjectSkipped`, not `nil`
