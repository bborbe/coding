# Go State Machine Pattern

This guide documents the **phase-dispatched state machine pattern** for long-running, resumable workflows that span multiple short-lived process invocations. Each phase is independent, emits a result envelope, and an external controller advances the workflow by spawning the next phase.

For the conceptual background (states, transitions, Mealy/Moore, statecharts, Petri nets, actor model), see your CS reference materials. This guide is the practical Go implementation.

## When to Use This Pattern

Use this pattern when you need:

- **Long-running workflows** that exceed a single process lifetime (Kubernetes Jobs, batch tasks, queue workers)
- **Resumable execution** — a phase can crash and restart at the last persisted phase
- **Heterogeneous phase logic** — some phases are deterministic Go, others call external systems (LLMs, third-party APIs)
- **External coordination** — a controller reads phase output and decides what to spawn next
- **Auditable transitions** — phase + status are written to a durable store (database, K8s CR, message bus)

**Don't use** for:

- In-process orchestration where goroutines + channels are simpler — see `go-concurrency-patterns.md`
- Workflows that always complete in one process call
- Sub-second state changes — process spawn overhead dominates

## Core Pattern Structure

Four collaborating pieces:

1. **Phase enum** — string-typed constants naming each step
2. **Status enum** — terminal/non-terminal outcome of a single phase invocation
3. **Result envelope** — what each phase emits (`Status`, `NextPhase`, payload)
4. **Phase dispatcher** — entrypoint logic that selects per-phase code path

A **controller** outside the process (queue worker, K8s reconciler, scheduler) reads the result envelope, persists state, and spawns the next phase.

### Minimal Complete Implementation

```go
package order

import (
	"context"
	"os"

	"github.com/bborbe/errors"
)

// 1. Phase enum — frozen, ordered, forward-only
type Phase string

const (
	PhaseValidating Phase = "validating"
	PhaseCharging   Phase = "charging"
	PhaseFulfilling Phase = "fulfilling"
	PhaseShipping   Phase = "shipping"
	PhaseDone       Phase = "done"
)

// 2. Status enum — outcome of a single phase invocation
type Status string

const (
	StatusDone       Status = "done"        // phase succeeded; advance via NextPhase
	StatusFailed     Status = "failed"      // unrecoverable
	StatusNeedsInput Status = "needs_input" // human intervention required
)

// 3. Result envelope — emitted by each phase, consumed by the controller
type Result struct {
	Status    Status `json:"status"`
	Message   string `json:"message,omitempty"`
	NextPhase Phase  `json:"next_phase,omitempty"` // empty = terminal
	Output    string `json:"output,omitempty"`     // optional rich payload
}

// 4. Phase dispatcher — selects the per-phase handler
func Run(ctx context.Context) (*Result, error) {
	phase := Phase(os.Getenv("PHASE"))
	switch phase {
	case PhaseValidating:
		return runValidatingPhase(ctx)
	case PhaseCharging:
		return runChargingPhase(ctx)
	case PhaseFulfilling:
		return runFulfillingPhase(ctx)
	case PhaseShipping:
		return runShippingPhase(ctx)
	default:
		return nil, errors.Errorf(ctx, "unknown phase %q", phase)
	}
}
```

### Phase Handler Signature

Every phase handler returns a `*Result`. The handler decides:

- `Status` — outcome of THIS invocation
- `NextPhase` — which phase the controller should spawn next; empty means terminal

```go
func runValidatingPhase(ctx context.Context) (*Result, error) {
	if err := validate(ctx); err != nil {
		return &Result{Status: StatusFailed, Message: err.Error()}, nil
	}
	return &Result{
		Status:    StatusDone,
		NextPhase: PhaseCharging,
	}, nil
}

func runChargingPhase(ctx context.Context) (*Result, error) {
	receipt, err := charge(ctx)
	if err != nil {
		return &Result{Status: StatusFailed, Message: err.Error()}, nil
	}
	return &Result{
		Status:    StatusDone,
		NextPhase: PhaseFulfilling,
		Output:    receipt.JSON(),
	}, nil
}

func runShippingPhase(ctx context.Context) (*Result, error) {
	if err := handToCarrier(ctx); err != nil {
		return &Result{Status: StatusFailed, Message: err.Error()}, nil
	}
	return &Result{
		Status:    StatusDone,
		NextPhase: PhaseDone, // terminal — controller marks workflow complete
	}, nil
}
```

## Status vs. Phase — the critical distinction

These are **two independent dimensions**:

- **Phase** = WHERE in the workflow we are
- **Status** = HOW the current phase invocation ended

A common bug: collapsing them into one field. The controller uses both:

| Status | NextPhase | Controller action |
|--------|-----------|-------------------|
| `done` | non-empty (e.g. `charging`) | persist `phase=charging, status=in_progress`; spawn next phase |
| `done` | empty or `done` | persist `phase=done, status=completed`; workflow terminates |
| `failed` | (ignored) | persist `status=failed`; alert operator |
| `needs_input` | (ignored) | persist `status=in_progress, phase=human_review`; pause for human |

**Status persistence rule.** Keep `status=in_progress` while `NextPhase` is non-terminal. Without this, the controller marks the task `completed` after the first phase and stops spawning, stalling the workflow.

```go
// In your controller's persist function:
if result.NextPhase == "" || result.NextPhase == PhaseDone {
	state.Status = "completed"
} else {
	state.Status = "in_progress"
	state.Phase = result.NextPhase
}
```

## Heterogeneous Phases — pure Go and external runners

Different phases can use different runtimes. The dispatcher hides this from callers. A typical mix: some phases are deterministic Go (rule checks, transformers), others delegate to an external runner (LLM, ML model, third-party workflow engine).

```go
type ExternalRunner interface {
	Run(ctx context.Context, instructions string) (*Result, error)
}

func Run(ctx context.Context, runner ExternalRunner) (*Result, error) {
	phase := Phase(os.Getenv("PHASE"))

	// Pure-Go phases — short, deterministic, no external dependency
	switch phase {
	case PhaseValidating:
		return runValidatingPhase(ctx)
	case PhaseShipping:
		return runShippingPhase(ctx)
	}

	// Phases that delegate to an external runner
	instructions, ok := selectInstructions(phase)
	if !ok {
		return nil, errors.Errorf(ctx, "unknown phase %q", phase)
	}
	return runner.Run(ctx, instructions)
}
```

Pure-Go phases are preferred when:

- Logic is deterministic (parsers, comparators, formatters, rule checks)
- Output is structured (no free-form text needed)
- Tests can cover the behavior with fixtures

## External controller contract

The controller is OUTSIDE this process. It reads the `Result`, persists state, and decides whether to spawn the next phase. The phase code does NOT advance state itself.

Typical controller loop:

```text
1. Read pending task → extract current phase
2. Spawn worker process with PHASE=<current-phase>
3. Read worker's Result envelope (stdout, K8s pod log, message bus)
4. Persist:
   - if Status=done && NextPhase non-terminal: phase=NextPhase, status=in_progress
   - if Status=done && NextPhase terminal:     phase=done,      status=completed
   - if Status=needs_input:                    phase=human_review, status=in_progress
   - if Status=failed:                         status=failed
5. If status=in_progress and phase != human_review: re-queue for next iteration
```

## Loops and backward edges

The pattern is **forward-only by default**: a worker emits `NextPhase` referring to a *later* phase, never an earlier one. This prevents autonomous infinite loops in long-running agents and bounds total work per task.

But real workflows need iteration: retries on transient failures, agent re-planning, operator-driven requeues. There are four ways to handle these without breaking forward-only-by-default:

### 1. Interventional Reset (controller-driven backward edge)

An external actor — operator, scheduled job, watcher service — flips the persisted state from `failed` back to `approved` and resets `phase` to the start. The worker stays ignorant; the cycle is the controller's responsibility.

```text
worker:     emits Status=failed → halts
operator:   directly updates state.Status=approved, state.Phase=PhaseValidating
controller: sees approved → re-spawns the worker
```

This is the right answer for retries triggered by humans or by a separate retry policy. Use it for transient infrastructure failures, missing prerequisites, prompt tuning iterations.

### 2. Phase Unrolling (linearize a small bounded loop)

If iteration is bounded (e.g. one retry max), give each iteration its own named phase:

```go
const (
	PhaseDrafting  Phase = "drafting"
	PhaseReviewing Phase = "reviewing"
	PhaseRevising  Phase = "revising" // conceptually a loop, but a distinct phase
	PhaseFinalized Phase = "finalized"
)
```

**Pros:** Highly auditable — you know exactly which iteration the workflow is on.
**Cons:** Doesn't scale to N iterations.

### 3. Sub-Phase / Do-While (push the loop inside the worker)

If iterations are unbounded, keep the external FSM forward-only and run the loop in-memory inside one worker phase. The external phase is something broad like `PhaseResolving`. Inside `runResolvingPhase()`, an in-process loop iterates until a condition is met.

**Pros:** External controller's database is not spammed with high-frequency transitions. Top-level FSM stays clean.
**Cons:** If the worker crashes mid-loop, iteration progress is lost; the phase restarts from scratch.

### 4. Controlled Loop with Circuit Breaker (worker emits backward edge)

If a worker genuinely must emit a backward `NextPhase`, **enforce a circuit breaker** in the controller. Carry an `attempt` counter in the persisted state; the controller increments on each backward transition and fails the workflow if the counter exceeds a maximum.

```go
// [GOOD] Worker increments attempt counter; controller enforces the cap.
func runEvaluatingPhase(ctx context.Context, attempts int) (*Result, error) {
	if attempts >= 3 {
		return &Result{
			Status:  StatusFailed,
			Message: "max evaluation attempts reached",
		}, nil
	}
	if !looksGood(ctx) {
		return &Result{
			Status:    StatusDone,
			NextPhase: PhaseGenerating, // backward edge — circuit breaker MUST exist
		}, nil
	}
	return &Result{Status: StatusDone, NextPhase: PhaseDone}, nil
}
```

```go
// [BAD] Backward edge with no attempt counter — infinite loop risk.
return &Result{Status: StatusDone, NextPhase: PhaseGenerating}, nil
```

### Choosing between the four

| Scenario | Pattern |
|----------|---------|
| Operator wants to retry a failed task | **Interventional Reset** |
| At most 1–2 known iterations | **Phase Unrolling** |
| Iterations bounded but variable, no cross-phase observability needed | **Sub-Phase loop** |
| Worker must autonomously decide to retry, controller must observe | **Circuit Breaker** |

## Parallel sub-phases (Fork/Join)

Sometimes a single phase needs to fan out into independent sub-tasks and join the results before emitting the phase's `Result`. Don't use raw `go func() { ... }` for this — see `go-concurrency-patterns.md` for the project rule. Use `bborbe/run` primitives.

Each sub-task is a `run.Func = func(context.Context) error`. Capture results into pointers in the enclosing scope; combine after the parallel section completes.

```go
import (
	"context"

	"github.com/bborbe/errors"
	"github.com/bborbe/run"
)

func runFulfillingPhase(ctx context.Context, repo Repo, orderID string) (*Result, error) {
	var (
		customer *Customer
		product  *Product
		shipping *ShippingQuote
	)

	fetchCustomer := func(ctx context.Context) error {
		c, err := repo.LoadCustomer(ctx, orderID)
		if err != nil {
			return errors.Wrapf(ctx, err, "load customer for order %q", orderID)
		}
		customer = c
		return nil
	}
	fetchProduct := func(ctx context.Context) error {
		p, err := repo.LoadProduct(ctx, orderID)
		if err != nil {
			return errors.Wrapf(ctx, err, "load product for order %q", orderID)
		}
		product = p
		return nil
	}
	fetchShipping := func(ctx context.Context) error {
		q, err := repo.QuoteShipping(ctx, orderID)
		if err != nil {
			return errors.Wrapf(ctx, err, "quote shipping for order %q", orderID)
		}
		shipping = q
		return nil
	}

	// Fork: run all three in parallel; cancel siblings on first error
	if err := run.CancelOnFirstErrorWait(ctx, fetchCustomer, fetchProduct, fetchShipping); err != nil {
		return &Result{Status: StatusFailed, Message: err.Error()}, nil
	}

	// Join: deterministic logic on the assembled inputs
	if err := reserveInventory(ctx, customer, product, shipping); err != nil {
		return &Result{Status: StatusFailed, Message: err.Error()}, nil
	}
	return &Result{Status: StatusDone, NextPhase: PhaseShipping}, nil
}
```

For the full primitive reference (`run.All`, `run.Sequential`, `run.CancelOnFirstFinishWait`) and producer/consumer patterns, see `go-concurrency-patterns.md`. For state-machine sub-phases, `run.CancelOnFirstErrorWait` is almost always the right choice: one failed sub-task invalidates the join, so cancel the others to free resources.

## Anti-patterns

### ❌ Status as the only state field

```go
// [BAD] No phase — controller cannot decide what to spawn next.
type State struct {
	Status string `json:"status"` // "in_progress"
}
```

```go
// [GOOD] Phase + status — both required.
type State struct {
	Status string `json:"status"` // "in_progress"
	Phase  Phase  `json:"phase"`  // "charging"
}
```

### ❌ Phase increment inside the worker

```go
// [BAD] Worker mutates persisted state itself — race when controller restarts.
func runChargingPhase(ctx context.Context, repo Repo) (*Result, error) {
	repo.SetPhase(ctx, PhaseFulfilling) // controller's job, not yours
	return &Result{Status: StatusDone}, nil
}
```

```go
// [GOOD] Worker emits NextPhase; controller persists it.
func runChargingPhase(ctx context.Context) (*Result, error) {
	return &Result{Status: StatusDone, NextPhase: PhaseFulfilling}, nil
}
```

### ❌ Cycles without explicit guards

This pattern is forward-only by default. Backward edges require either an Interventional Reset (controller-driven) or a Circuit Breaker (worker-driven, with attempt counter). Don't reuse phase names for re-entry without one of those mechanisms — see "Loops and backward edges" above.

### ❌ Free-form `NextPhase` strings

Always emit values from the frozen `Phase` enum. Strings outside the enum (typos, status words) cause silent stalls. Validate at the controller boundary:

```go
// [GOOD] Controller validates worker output before persisting.
func validateNextPhase(ctx context.Context, p Phase) error {
	for _, valid := range AvailablePhases {
		if p == valid {
			return nil
		}
	}
	return errors.Errorf(ctx, "invalid next_phase %q from worker", p)
}
```

### ❌ Phase logic in the factory

The factory has zero business logic. Phase selection lives in the entrypoint (`main.go` or the dispatcher), not in factory constructors. The factory wires dependencies; it does not branch on phase. See `go-factory-pattern.md`.

### ❌ Raw `go func()` in fork/join

```go
// [BAD] Leaks goroutines, no error propagation, untestable.
go func() { fetchA(ctx) }()
go func() { fetchB(ctx) }()
```

```go
// [GOOD] Use run.CancelOnFirstErrorWait — see fork/join section above.
err := run.CancelOnFirstErrorWait(ctx, fetchA, fetchB)
```

## Testing

- **Per-phase tests** — table-driven over fixture inputs; assert `Status` and `NextPhase`. See `go-testing-guide.md` for Ginkgo/Gomega style.
- **Dispatcher test** — assert each `PHASE` env var routes to the correct handler.
- **Controller integration** — fake worker emits various `Result` envelopes; assert persisted state transitions match the contract table above.
- **Circuit breaker test** — for any phase that emits a backward `NextPhase`, assert the controller correctly increments the attempt counter and fails on overflow.

## When NOT to use this pattern

- **Single-shot workflows** — a function call is simpler.
- **Tightly-coupled phases** — if two phases must share in-process state, merge them.
- **High-frequency state changes** — process spawn overhead per phase dominates. For sub-second transitions, use a goroutine state machine, an actor library, or a stateful in-memory FSM.
- **Workflows with rich nested hierarchy** — if you need composite states with orthogonal regions and history pseudo-states, use a hierarchical-FSM library (e.g. a Stateless port for Go) instead of hand-rolling.

## See also

- `go-concurrency-patterns.md` — `bborbe/run` primitives, channel ownership, producer/consumer
- `go-factory-pattern.md` — why factories must not contain phase logic
- `go-enum-type-pattern.md` — string-based enums for `Phase` and `Status`
- `go-error-wrapping-guide.md` — `errors.Wrapf` for sub-task failures
- `go-testing-guide.md` — Ginkgo/Gomega test patterns
