# Go Factory Pattern Guide

Factory functions compose objects by wiring dependencies together. They contain **zero business logic** — only constructor calls. Errors, conditionals, and lifecycle decisions belong elsewhere (in `main.go Run` or in a dedicated `Provider` interface).

## 1. Core Principles

**Factories should only:**
- Pass dependencies to constructors
- Build nested object trees
- Return interface types

**Factories must NOT:**
- Contain loops, conditionals, or business logic
- Have inline function implementations with logic
- Mix object creation with execution
- **Return `error`** — if a constructor can fail at boot, call it from `main.go Run`, not from another factory. Errors are runtime concerns; factories are pure composition. (See sections 5 and 7.)
- **Perform boot-time validation** (e.g. "is this env set? if not, use a noop") — that's config interpretation, owned by `main.go Run`.
- **Return `(_, cleanup, _)`** — cleanup lifecycle is `main.go`'s concern via `defer`, not the factory's.

A useful smell test: if a function in `factory.go` returns `error`, contains `if`/`switch`, or schedules cleanup, it has logic that needs to move — either to `main.go Run` (boot-time concerns) or to a Provider interface (dispatch concerns).

## 2. Factory vs Constructor

A **constructor** (`New*`) takes its dependencies and returns the configured object. It lives in the implementation file (`pkg/userservice.go`) because it's where the implementation lives. Constructors may return `error` when validation or external setup can fail.

A **factory** (`Create*`) takes wiring-level concerns (config values, env-derived inputs) and composes constructors. It lives in `factory.go` because it lives at the composition layer. Factories must NOT return `error`.

The constructor knows nothing about how it's wired; the factory knows nothing about the implementation. That separation is what keeps factories logic-free.

## 3. File Organization

**Services/Applications:**
```text
pkg/factory/factory.go    # All factory functions in ONE file
pkg/thing.go              # Implementation types live in pkg/ (flat)
pkg/big_area/thing.go     # If pkg/ grows large, group into pkg/<subpkg>/
```

**Libraries:**
```text
lib/mylib/factory.go      # NOT lib/mylib/pkg/factory/factory.go
```

**Rule:** Implementation types (structs, interfaces, methods with logic) MUST NOT live inside `pkg/factory/`. The factory package is wiring-only. Impl goes in `pkg/` directly, or in a `pkg/<subpkg>/` sibling package if `pkg/` becomes too large. A file named `pkg/factory/roundtripper.go` containing a `mocoRoundTripper` struct is wrong — move it to `pkg/roundtripper/` (or `pkg/roundtripper.go`).

**Naming:**
- Factories: `Create*` prefix (e.g., `CreateUserService`) — in `factory.go` only
- Constructors: `New*` prefix (e.g., `NewUserService`) — in implementation files only

## 4. Good Factory Examples

### 4.1 Simple Composition
```go
func CreateUserService(db DB, validator Validator) UserService {
    return NewUserService(db, validator, log.DefaultSamplerFactory)
}
```

### 4.2 Nested Composition (Middleware/Decorators)
```go
func CreateMessageHandler(db DB) MessageHandler {
    return NewMessageHandlerBatchTxUpdate(
        db,
        NewMessageHandlerBatchTx(
            NewMessageHandlerTxSkipErrors(
                NewMessageHandlerTxMetrics(
                    NewUserMessageHandlerTx(
                        CreateStoreUserHandlerTx(),
                        log.DefaultSamplerFactory,
                    ),
                    NewMetrics(),
                ),
                log.DefaultSamplerFactory,
            ),
        ),
    )
}
```

### 4.3 Run Function Wrapper
```go
func CreateConsumerRun(provider kafka.SaramaClientProvider, db DB) run.Func {
    return func(ctx context.Context) error {
        return kafka.NewOffsetConsumer(
            provider,
            "topic",
            CreateOffsetManager(db),
            CreateMessageHandler(db),
        ).Consume(ctx)
    }
}
```

**Acceptable anonymous function:** Only when it directly calls a method (like `.Consume(ctx)`) with no additional logic — no `if`, no logging, no error wrapping. The returned type `run.Func` is `func(ctx) error`, so the closure body's signature returns `error` — but **the factory itself returns `run.Func`, not `error`**. That's the distinction.

**Multi-statement wiring is still acceptable.** "No additional logic" limits the *kind* of statements, not the *count*. A `run.Func` closure may contain several pure-wiring statements — e.g. building a `mux.Router` and registering handlers on it — as long as none of them is logic: no `if`/`for`/`switch`, no error wrapping, no logging, no data transformation. Assembling a router and returning `server.Run(ctx)` is composition; a loop over routes or a conditional route is not. See section 11 for a full server-wiring factory.

### 4.4 List Composition
```go
func CreateAuthenticators(cookie CookieGenerator, oauth GoogleOAuth) []Authenticator {
    return []Authenticator{
        NewGoogleAuthenticator(cookie, oauth),
        NewBasicAuthenticator(NewUserProvider()),
    }
}
```

List composition returns `[]Interface`, not `[]ConcreteStruct`. Each element comes from a constructor call — no loops, no filtering.

## 5. When You Need Dispatch — Use a Provider Interface

Factories cannot contain `switch` statements. When runtime selection between objects is needed (e.g. "pick this agent for that task_type"), introduce a **Provider interface** that owns the dispatch logic; the factory wires the provider with a pre-built map.

### ❌ BAD: Dispatch inside the factory
```go
// factory.go
func CreateAgentForTaskType(ctx context.Context, t TaskType, runner Runner) (*Agent, error) {
    switch t {                                              // ❌ conditional
    case TaskTypeClaude:
        return CreateClaudeAgent(runner), nil
    case TaskTypeHealthcheck:
        return NewHealthcheckAgent(runner), nil
    default:
        return nil, errors.Errorf(ctx,                      // ❌ error from factory
            "unknown task_type %q for agent-claude; accepted: [%s %s]",
            t, TaskTypeClaude, TaskTypeHealthcheck)
    }
}
```

**Why bad:** switch + error return + format string = three violations. The switch IS the business logic. The error is dispatch failure, not composition failure. Every binary that needs the same dispatch shape copies this code — across N binaries you have N copies of the same switch.

### ✅ GOOD: Provider interface owns dispatch; factory is pure plumbing
```go
// pkg/agent_provider.go (or lib/ for cross-binary reuse)
type AgentProvider interface {
    Get(ctx context.Context, t TaskType) (*Agent, error)
}

type agentProvider struct {
    name   string                  // for the error message
    agents map[TaskType]*Agent
}

func NewAgentProvider(name string, agents map[TaskType]*Agent) AgentProvider {
    return &agentProvider{name: name, agents: agents}
}

func (p *agentProvider) Get(ctx context.Context, t TaskType) (*Agent, error) {
    if agent, ok := p.agents[t]; ok {
        return agent, nil
    }
    accepted := make([]string, 0, len(p.agents))
    for tt := range p.agents {
        accepted = append(accepted, string(tt))
    }
    sort.Strings(accepted)
    return nil, errors.Errorf(ctx,
        "unknown task_type %q for %s; accepted: %v",
        t, p.name, accepted)
}
```

```go
// factory.go — pure plumbing: no error, no switch, no conditional
func CreateAgentProvider(runner Runner) AgentProvider {
    return NewAgentProvider("agent-claude", map[TaskType]*Agent{
        TaskTypeClaude:      CreateClaudeAgent(runner),
        TaskTypeHealthcheck: NewHealthcheckAgent(runner),
    })
}
```

```go
// main.go — dispatch error handled at the boundary
provider := factory.CreateAgentProvider(runner)
agent, err := provider.Get(ctx, t)
if err != nil { return errors.Wrap(ctx, err, "select agent") }
```

**Benefits:**
- Factory contains only a map literal (zero logic, zero error)
- Dispatch logic lives in `Get` — a single method, tested once
- Adding a task type is a one-line map entry, not a `case` line
- The Provider interface is the seam — easily mocked, swapped, or wrapped

Use this pattern whenever you find yourself writing `CreateXFor*(t T) (X, error)` with a switch.

## 6. Bad Factory Patterns

### 6.1 Inline Business Logic
```go
// ❌ BAD: Loop, error handling, nested anonymous functions
func CreateIndexHandler(db DB, index Index) MessageHandler {
    return NewMessageHandlerBatchTxView(
        db,
        MessageHandlerBatchTxFunc(
            func(ctx context.Context, tx Tx, messages []*Message) error {
                batch := index.NewBatch()
                indexer := NewEventIndexer(NewUserStoreTx(), NewBatchIndex(batch))

                handler := NewUserMessageHandlerTx(
                    UserHandlerTxFunc(
                        func(ctx context.Context, tx Tx, user User) error {
                            return indexer.Add(ctx, tx, user)
                        },
                        func(ctx context.Context, tx Tx, id UserID) error {
                            return indexer.Remove(ctx, tx, id)
                        },
                    ),
                )

                for _, message := range messages {
                    if err := handler.ConsumeMessage(ctx, tx, message); err != nil {
                        return errors.Wrap(ctx, err, "consume failed")
                    }
                }

                return index.Batch(batch)
            },
        ),
    )
}
```

**Why bad:**
- For loop iterating messages
- Inline anonymous functions with logic
- Error handling inside factory

### ✅ FIX: Move Implementation to Separate File
```go
// In factory.go:
func CreateIndexHandler(db DB, index Index) MessageHandler {
    return NewMessageHandlerBatchTxView(db, NewUserIndexHandler(index))
}

// In user_index_handler.go:
type userIndexHandler struct {
    index Index
}

func NewUserIndexHandler(index Index) MessageHandlerBatchTx {
    return &userIndexHandler{index: index}
}

func (h *userIndexHandler) Handle(ctx context.Context, tx Tx, messages []*Message) error {
    batch := h.index.NewBatch()
    // ...logic lives here, in the implementation file...
}
```

### 6.2 Boot-time Conditional Wiring
```go
// ❌ BAD: factory chooses between noop and kafka based on config
func CreateDeliverer(ctx context.Context, taskID TaskID, brokers Brokers) (Deliverer, func(), error) {
    if taskID == "" {                            // ❌ config interpretation
        return NewNoopDeliverer(), func() {}, nil
    }
    if len(brokers) == 0 {                       // ❌ validation
        return nil, nil, errors.Errorf(ctx, "BROKERS must be set")
    }
    producer, err := NewSyncProducer(ctx, brokers)
    if err != nil { return nil, nil, err }       // ❌ error return
    cleanup := func() { producer.Close() }       // ❌ cleanup closure
    return NewKafkaDeliverer(producer), cleanup, nil
}
```

**Why bad:** The factory decides which deliverer to use, validates config, propagates a constructor error, and schedules cleanup. Four roles, none of which are composition.

### ✅ FIX: Lift to `main.go Run`
```go
// factory.go — two small, single-purpose factories, no error, no cleanup
func CreateNoopDeliverer() Deliverer        { return delivery.NewNoopDeliverer() }
func CreateKafkaDeliverer(p SyncProducer)   Deliverer { return delivery.NewKafkaDeliverer(p) }

// main.go — boot-time decisions live here
deliverer := factory.CreateNoopDeliverer()
if a.TaskID != "" {
    if len(a.Brokers) == 0 {
        return errors.Errorf(ctx, "BROKERS must be set when TASK_ID is set")
    }
    producer, err := factory.CreateSyncProducer(ctx, a.Brokers)
    if err != nil { return errors.Wrap(ctx, err, "create producer") }
    defer func() {
        if err := producer.Close(); err != nil {
            glog.Warningf("close producer: %v", err)
        }
    }()
    deliverer = factory.CreateKafkaDeliverer(producer)
}
```

main.go reads as a sequence of well-named factory calls, with the config-driven branching and lifecycle visible at the boot site where it belongs.

## 7. Pass-through Wrappers (Error-returning constructors)

When an underlying constructor returns `error` (e.g. `kafka.NewSyncProducerWithName(ctx, brokers) (SyncProducer, error)`), you have a choice:

- **Preferred**: call it directly from `main.go Run`. No factory wrapper.
- **Acceptable**: a thin pass-through factory like `CreateSyncProducer(ctx, brokers) (SyncProducer, error)` — but **only** if it adds nothing beyond the call (no extra wiring, no logging, no validation, no transformation of the error message). The factory must be one statement: `return kafka.NewSyncProducerWithName(ctx, brokers, "service-name")`. If you add even an error wrap, lift it to main.go.

The pass-through wrapper is permitted because it consolidates the service-name constant in one place, but it's the only exception to the "no error return" rule. Treat it as a smell — every pass-through wrapper makes the next reviewer ask "should this be in main.go?"

## 8. Usage in main.go

Factories wire the application; `main.go Run` interprets config and owns lifecycle:

```go
func main() {
    db := bolt.NewDB(dbPath)
    currentTime := time.NewCurrentDateTime()
    producer := kafka.NewSyncProducer(brokers)

    // Factories build services from pre-validated deps
    userService := pkg.CreateUserService(db, currentTime, producer)

    // main.go decides which factory to call based on config
    var handler http.Handler
    if cfg.AuthEnabled {
        handler = pkg.CreateAuthenticatedHandler(userService)
    } else {
        handler = pkg.CreateOpenHandler(userService)
    }

    // Router assembly is pure wiring — it belongs in a factory, not main.
    // main only decided `handler`; it does not touch the router. (Section 11.)
    pkg.CreateServer(addr, handler).Run(ctx)
}
```

The `if cfg.AuthEnabled` lives in main, not inside a factory. Each factory takes already-validated inputs and returns a fully-configured object. The router — `mux.NewRouter()`, `router.Handle(...)`, wrapping it in a server — is inert composition, so `CreateServer` owns it; main only keeps the config decision. Section 11 makes this boundary explicit.

## 9. Common Antipatterns

### 9.1 Execute Logic in Factory
```go
// ❌ BAD
func CreateService(db DB) Service {
    service := NewService(db)
    service.Initialize()  // Execution!
    return service
}
```

### 9.2 Create Singletons
```go
// ❌ BAD
var instance Service

func CreateService(db DB) Service {
    if instance == nil {
        instance = NewService(db)
    }
    return instance
}
```

### 9.3 Split Factories Across Files
```text
# ❌ BAD
pkg/factory/user_factory.go
pkg/factory/handler_factory.go

# ✅ GOOD
pkg/factory/factory.go  # All factories in one file
```

### 9.4 Return `error` for Dispatch Failure
```go
// ❌ BAD: dispatch error returned from factory
func CreateHandlerForKind(k Kind) (Handler, error) {
    switch k {
    case KindA: return NewHandlerA(), nil
    default:   return nil, errors.New("unknown kind")
    }
}

// ✅ GOOD: Provider interface (see section 5)
type HandlerProvider interface {
    Get(ctx context.Context, k Kind) (Handler, error)
}
```

### 9.5 Boot-time Validation in Factory
```go
// ❌ BAD: env validation inside factory
func CreateConfig(env Env) (Config, error) {
    if env.DBURL == "" { return Config{}, errors.New("DB_URL required") }
    return Config{DB: env.DBURL}, nil
}

// ✅ GOOD: validate in main.go before calling factory
if env.DBURL == "" { return errors.New("DB_URL required") }
cfg := factory.CreateConfig(env.DBURL)
```

## 10. Testing Factories

**Don't unit-test pure-plumbing factories.** A factory that's literally `return New*(a, b, c)` has no logic to verify — the test would assert "the constructor was called with these arguments," which is what reading the file already shows.

Test the **constructors** (`New*`) and their implementations instead. Test the **Provider** interface (which has dispatch logic and an error path) in its own test file.

If you feel the need to test a factory, it probably contains logic that should be extracted. The exception: a one-line "implements interface X" compile-time assertion via `var _ Interface = (&Impl{})` — that's a build-time check, not a test.

## 11. The main.go / factory boundary

Sections 6.2 and 8 push config branching and lifecycle *into* `main.go`. This section states the **complementary half**: once those are there, *nothing else* should remain in `main.go Run`. Every value that main.go neither branches on nor owns the lifecycle of is inert plumbing — and inert plumbing belongs in a factory.

**`main.go Run` keeps exactly three kinds of statement:**
1. **Error-returning boot calls** — constructors that can fail at startup (`NewSyncProducer(...)`, `url.Parse(...)`). Section 7.
2. **Lifecycle** — `defer x.Close()`. Section 6.2.
3. **Config interpretation & branching** — turning env/flags into decisions (`if cfg.AuthEnabled`). Sections 6.2, 8.

Anything else — building a service, wrapping it in a handler, assembling a router, composing a `run.Func` — is composition, and composition is the factory's job.

**The pass-through test:** if main.go builds a value with one factory (or constructor) and then does nothing with it except pass it, unchanged, into exactly one more call, that value should not exist in main.go. Collapse it into the outer factory. A local that main.go never branches on, transforms, or `defer`s is not earning its place at the composition root.

### ❌ BEFORE — main.go holds inert plumbing

```go
// main.go — the run.Func, the intermediate service, and the router all sit here
func (a *application) createHttpServer(port int) run.Func {
    return func(ctx context.Context) error {
        service := factory.CreateOrderService(a.db, a.producer) // built here...
        router := mux.NewRouter()
        router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/orders").
            Handler(factory.CreateOrderHandler(service))        // ...only to be passed here
        return libhttp.NewServerWithPort(port, router).Run(ctx)
    }
}
```

`service` is a pure pass-through: main.go makes no decision with it and never closes it. The whole `run.Func` — router included — is composition living in the wrong file. main.go is longer than its job.

### ✅ AFTER — factory absorbs all composition; main.go wires config only

```go
// factory.go — the run.Func and its router live here; service is composed inline
func CreateHttpServer(db DB, producer Producer, port int) run.Func {
    return func(ctx context.Context) error {
        router := mux.NewRouter()
        router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/orders").
            Handler(CreateOrderHandler(CreateOrderService(db, producer)))
        return libhttp.NewServerWithPort(port, router).Run(ctx)
    }
}
```

```go
// main.go Run — boot errors + lifecycle + config only, then hand off
producer, err := kafka.NewSyncProducer(ctx, brokers) // (1) error-boot
if err != nil {
    return errors.Wrap(ctx, err, "create producer")
}
defer producer.Close()                               // (2) lifecycle
return service.Run(ctx,
    factory.CreateCommandConsumer(...),                 // (3) hand off — pure composition
    factory.CreateHttpServer(db, producer, a.Port),
)
```

The server closure — including the whole `mux` router assembly — is pure wiring: no `if`/`for`/`switch`, no error return from the factory itself (it returns `run.Func`), no lifecycle. That is exactly what section 4.3 permits, just with several registration statements instead of one.

**Why this is a `SHOULD`, not a `MUST`:** leaving a pass-through in main.go doesn't break the factory's purity — the factory is still logic-free. It's a composition-root smell, not a factory violation. But it scatters the object graph across two files and inflates main.go past its three jobs, so collapse it unless there's a reason not to.

## Summary

**Factory Checklist:**
- ✅ All factories in single file: `pkg/factory/factory.go` or `lib/{name}/factory.go`
- ✅ Use `Create*` prefix (constructors use `New*` and live in implementation files)
- ✅ Only constructor calls — zero business logic
- ✅ Returns no `error` (use Provider interface for dispatch — section 5; or call the error-returning constructor from main.go directly — section 7)
- ✅ No boot-time validation (lives in `main.go Run` — section 6.2)
- ✅ No `(_, cleanup, _)` return — cleanup lifecycle owned by `main.go` via `defer` (section 6.2)
- ✅ Move complex logic to implementation files in `pkg/` (or `pkg/<subpkg>/` if `pkg/` is large) — NEVER inside `pkg/factory/`
- ✅ Return interface types
- ✅ `main.go Run` holds only boot errors, lifecycle (`defer`), and config branching — every pure-composition value (including `run.Func` server/consumer wiring) lives in a factory (section 11)

### RULE go-factory/no-error-return (MUST)

**Owner**: go-factory-pattern-assistant
**Applies when**: a Go function whose name starts with `Create` declared in a `*.go` file outside `*_test.go` and `vendor/` has a return type list that includes `error`. The single permitted exception is a pass-through wrapper per section 7 — a one-statement factory that immediately returns an error-returning constructor call without adding wiring, logging, or validation.
**Enforcement**: `rules/go/factory-no-error-return.yml` (mechanical flag) + judgment-tier LLM adjudication for the pass-through wrapper exception.
**Why**: factories are pure composition. Errors are runtime concerns and belong in `main.go Run` or behind a Provider interface (section 5). A factory returning `error` typically signals boot-time validation, dispatch logic, or constructor failure handling living in the wrong layer.

#### Bad

```go
func CreateDeliverer(ctx context.Context, taskID TaskID, brokers Brokers) (Deliverer, func(), error) {
    if taskID == "" {
        return NewNoopDeliverer(), func() {}, nil
    }
    if len(brokers) == 0 {
        return nil, nil, errors.Errorf(ctx, "BROKERS must be set")
    }
    producer, err := NewSyncProducer(ctx, brokers)
    if err != nil { return nil, nil, err }
    cleanup := func() { producer.Close() }
    return NewKafkaDeliverer(producer), cleanup, nil
}
```

#### Good

```go
// main.go — boot-time decisions live here
deliverer := factory.CreateNoopDeliverer()
if a.TaskID != "" {
    if len(a.Brokers) == 0 {
        return errors.Errorf(ctx, "BROKERS must be set when TASK_ID is set")
    }
    producer, err := factory.CreateSyncProducer(ctx, a.Brokers)
    if err != nil { return errors.Wrap(ctx, err, "create producer") }
    defer func() {
        if err := producer.Close(); err != nil {
            glog.Warningf("close producer: %v", err)
        }
    }()
    deliverer = factory.CreateKafkaDeliverer(producer)
}

// factory.go — two small, single-purpose factories, no error, no cleanup
func CreateNoopDeliverer() Deliverer  { return delivery.NewNoopDeliverer() }
func CreateKafkaDeliverer(p SyncProducer) Deliverer { return delivery.NewKafkaDeliverer(p) }
```

### RULE go-factory/no-conditional-in-body (MUST)

**Owner**: go-factory-pattern-assistant
**Applies when**: a Go function whose name starts with `Create` declared in a `*.go` file outside `*_test.go` and `vendor/` contains an `if`, `switch`, or `for` statement anywhere in its body. Anonymous functions inside the body that are pure pass-throughs (single method call, no logic — see section 4.3 `Run Function Wrapper`) are an acceptable exception adjudicated by the judgment tier.
**Enforcement**: `rules/go/factory-no-conditional-in-body.yml` (mechanical flag) + judgment-tier LLM adjudication for the anonymous-function exception.
**Why**: conditionals in a factory mean the factory is making a decision. Decisions belong in `main.go Run` (boot-time) or behind a Provider interface (runtime dispatch). The factory's job is to wire pre-validated dependencies into a constructor call tree.

#### Bad

```go
func CreateAgentForTaskType(ctx context.Context, t TaskType, runner Runner) (*Agent, error) {
    switch t {
    case TaskTypeClaude:
        return CreateClaudeAgent(runner), nil
    case TaskTypeHealthcheck:
        return NewHealthcheckAgent(runner), nil
    default:
        return nil, errors.Errorf(ctx,
            "unknown task_type %q for agent-claude; accepted: [%s %s]",
            t, TaskTypeClaude, TaskTypeHealthcheck)
    }
}
```

#### Good

```go
type AgentProvider interface {
    Get(ctx context.Context, t TaskType) (*Agent, error)
}

// factory.go — pure plumbing: no error, no switch, no conditional
func CreateAgentProvider(runner Runner) AgentProvider {
    return NewAgentProvider("agent-claude", map[TaskType]*Agent{
        TaskTypeClaude:      CreateClaudeAgent(runner),
        TaskTypeHealthcheck: NewHealthcheckAgent(runner),
    })
}

// main.go — dispatch error handled at the boundary
provider := factory.CreateAgentProvider(runner)
agent, err := provider.Get(ctx, t)
if err != nil { return errors.Wrap(ctx, err, "select agent") }
```

### RULE go-factory/no-cleanup-return (MUST)

**Owner**: go-factory-pattern-assistant
**Applies when**: a Go function whose name starts with `Create` declared in a `*.go` file outside `*_test.go` and `vendor/` has a return type list that includes `func()` (a cleanup closure). Common shapes: `(T, func())`, `(T, func(), error)`, `(func(), error)`.
**Enforcement**: `rules/go/factory-no-cleanup-return.yml` (mechanical flag) + judgment-tier LLM adjudication for any legitimate edge case.
**Why**: cleanup lifecycle is `main.go`'s concern via `defer`. A factory returning a cleanup closure forces the caller to know about lifecycle semantics the factory shouldn't own. Lift cleanup to the call site.

#### Bad

```go
func CreateDeliverer(ctx context.Context, taskID TaskID, brokers Brokers) (Deliverer, func(), error) {
    if taskID == "" {
        return NewNoopDeliverer(), func() {}, nil
    }
    if len(brokers) == 0 {
        return nil, nil, errors.Errorf(ctx, "BROKERS must be set")
    }
    producer, err := NewSyncProducer(ctx, brokers)
    if err != nil { return nil, nil, err }
    cleanup := func() { producer.Close() }
    return NewKafkaDeliverer(producer), cleanup, nil
}
```

#### Good

```go
// factory.go — two small, single-purpose factories, no error, no cleanup
func CreateNoopDeliverer() Deliverer        { return delivery.NewNoopDeliverer() }
func CreateKafkaDeliverer(p SyncProducer)  Deliverer { return delivery.NewKafkaDeliverer(p) }

// main.go — cleanup via defer at the call site
producer, err := factory.CreateSyncProducer(ctx, a.Brokers)
if err != nil { return errors.Wrap(ctx, err, "create producer") }
defer func() {
    if err := producer.Close(); err != nil {
        glog.Warningf("close producer: %v", err)
    }
}()
```

### RULE go-factory/no-impl-in-factory-pkg (MUST)

**Owner**: go-factory-pattern-assistant
**Applies when**: a `*.go` file inside `pkg/factory/` (any path matching `**/pkg/factory/*.go`) contains a struct type declaration with non-trivial methods (methods with logic beyond a trivial accessor), an interface declaration with multiple methods, or any function declaration that is NOT a `Create*` factory function. Detecting "non-trivial" requires reading the method body — pure ast-grep can match `type X struct` and method declarations but cannot reliably decide which methods are "trivial".
**Enforcement**: judgment — implementation-vs-trivial-helper distinction needs whole-method reasoning. Mechanical flag can catch structural violations (non-`Create*` function declarations, multi-method interfaces, impl structs) inside `pkg/factory/`, but the "trivial accessor" exception requires LLM adjudication.
**Trigger**: **/factory/**/*.go, **/*factory*.go
**Why**: `pkg/factory/` is wiring-only. Implementation types belong in `pkg/` (flat) or `pkg/<subpkg>/` (grouped). A struct like `mocoRoundTripper` inside `pkg/factory/roundtripper.go` is wrong — move it.

#### Bad

```go
// pkg/factory/roundtripper.go — SAME impl, WRONG directory
package factory

type mocoRoundTripper struct {
    client *http.Client
}

func (r *mocoRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
    // implementation logic lives here
    return r.client.Do(req)
}
```

#### Good

```go
// pkg/roundtripper/roundtripper.go — SAME impl, RIGHT directory
package roundtripper

type mocoRoundTripper struct {
    client *http.Client
}

func (r *mocoRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
    // implementation logic lives here
    return r.client.Do(req)
}

// pkg/factory/factory.go — wiring only
package factory

func CreateRoundTripper() http.RoundTripper {
    return roundtripper.NewMocoRoundTripper()
}
```

### RULE go-factory/main-holds-only-boot-lifecycle-config (SHOULD)

**Owner**: go-factory-pattern-assistant
**Applies when**: a composition root (`main.go`, or a `Run` method on the app struct) holds a value that is built by a `Create*` factory or a `New*` constructor and then used *only* as an unchanged argument to a single subsequent call — no `if`/`switch` branches on it, no transformation, no `defer` on it. Also applies when `main.go` assembles a router, `run.Func`, or handler tree inline instead of delegating to a factory. Deciding whether a value is a pure pass-through vs. a config-driven decision requires reading the whole `Run` function, so this is judgment-tier, not mechanical.
**Enforcement**: judgment — the pass-through-vs-decision distinction needs whole-function reasoning across the composition root; there is no mechanical `.yml`. The reviewer confirms the value is neither branched on, transformed, nor lifecycle-managed before flagging.
**Trigger**: main.go, **/main.go
**Why**: sections 6.2 and 8 push config branching and lifecycle into `main.go`; this rule states the other half. Everything that is *not* a boot error, a lifecycle `defer`, or a config decision is composition and belongs in a factory. A pass-through value split across `main.go` and a factory scatters the object graph and inflates `main.go` beyond its three responsibilities. Unlike the four `MUST` factory rules, this is a `SHOULD`: it doesn't break the factory's purity (the factory stays logic-free), it's a composition-root smell.

#### Bad

```go
// main.go — service is built here only to be passed straight through
func (a *application) createHttpServer(port int) run.Func {
    return func(ctx context.Context) error {
        service := factory.CreateOrderService(a.db, a.producer)
        router := mux.NewRouter()
        router.Path("/orders").Handler(factory.CreateOrderHandler(service))
        return libhttp.NewServerWithPort(port, router).Run(ctx)
    }
}
```

#### Good

```go
// factory.go — the run.Func, router, and intermediate service all live here
func CreateHttpServer(db DB, producer Producer, port int) run.Func {
    return func(ctx context.Context) error {
        router := mux.NewRouter()
        router.Path("/orders").
            Handler(CreateOrderHandler(CreateOrderService(db, producer)))
        return libhttp.NewServerWithPort(port, router).Run(ctx)
    }
}

// main.go Run — boot errors + lifecycle + config only
return service.Run(ctx,
    factory.CreateCommandConsumer(...),
    factory.CreateHttpServer(db, producer, a.Port),
)
```
