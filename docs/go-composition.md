# Go Service Composition

Orchestrators compose small single-responsibility services. Never call package-level functions directly from business logic.

### RULE go-composition/no-package-function-calls-in-business-logic (MUST)

**Owner**: go-architecture-assistant
**Applies when**: a Go service method calls a top-level package function (`prompt.ListQueued(...)`, `git.CommitAndRelease(...)`) directly instead of receiving the equivalent capability through an injected interface declared in the same package as the consumer.
**Enforcement**: judgment (ast-grep follow-up: `call_expression` of the form `<package>.<Function>(...)` inside method bodies, where `<package>` is a non-stdlib non-bborbe-library import; the agent rules out leaf packages whose functions are pure helpers).
**Why**: Direct package-function calls are hidden dependencies. The constructor doesn't surface them, tests can't mock them, and replacing the implementation requires editing every call site instead of swapping one constructor argument. Wrapping each capability in a small interface (`PromptScanner`, `Releaser`) makes the dep graph explicit at the type signature, makes Counterfeiter-mockable points obvious, and lets factories swap real for fake without touching business logic. The cost is one interface declaration per wrapped capability; the value is testability + composability + Single Responsibility at the right granularity.

#### Bad

```go
// runner calls package functions directly — untestable, uncomposable
type runner struct {
	dir      string
	executor Executor // only this dep is visible at the constructor
}

func (r *runner) Run(ctx context.Context) error {
	prompt.ResetExecuting(ctx, r.dir)            // hidden dep on package prompt
	prompt.NormalizeFilenames(ctx, r.dir)        // hidden dep
	queued, _ := prompt.ListQueued(ctx, r.dir)   // hidden dep
	for _, p := range queued {
		r.executor.Execute(ctx, p)
	}
	git.CommitAndRelease(ctx, "release")         // hidden dep on package git
	return nil
}
```

#### Good

```go
// Runner is the orchestration interface — small (1 method), drives the workflow
// via injected dependencies declared as their own interfaces.
type Runner interface {
	Run(ctx context.Context) error
}

// PromptScanner returns the queued prompts that have not yet been executed.
type PromptScanner interface {
	ListQueued(ctx context.Context) ([]Prompt, error)
}

// Releaser commits and tags the most recent execution batch.
type Releaser interface {
	CommitAndRelease(ctx context.Context, title string) error
}

// runner is the canonical Runner implementation. All deps surfaced as
// injected interfaces — constructor tells the full story.
type runner struct {
	scanner  PromptScanner
	executor Executor
	releaser Releaser
}

// NewRunner returns a Runner wired with the given scanner, executor, and
// releaser. Each dep is a separate interface so factories can swap real for
// fake without touching business logic.
func NewRunner(scanner PromptScanner, executor Executor, releaser Releaser) Runner {
	return &runner{scanner: scanner, executor: executor, releaser: releaser}
}
```

## Anti-Pattern: God Object

```go
// ❌ BAD: Runner calls package functions directly — untestable, uncomposable
func (r *runner) Run(ctx context.Context) error {
    prompt.ResetExecuting(ctx, r.dir)       // hard dependency
    prompt.NormalizeFilenames(ctx, r.dir)    // hard dependency
    queued := prompt.ListQueued(ctx, r.dir)  // hard dependency
    r.executor.Execute(ctx, content, ...)   // only this is injected!
    git.CommitAndRelease(ctx, title)         // hard dependency
}
```

Problems:
- Can't mock `prompt.*` or `git.*` in tests
- Can't swap implementations
- Constructor doesn't show what the service needs
- Violates SRP — one struct does scanning, executing, releasing

## Good Pattern: Compose Small Services

```go
// ✅ GOOD: Each service does ONE thing
type PromptScanner interface {
    ListQueued(ctx context.Context) ([]Prompt, error)
}

type Releaser interface {
    CommitAndRelease(ctx context.Context, title string) error
}

type Executor interface {
    Execute(ctx context.Context, content string, logFile string, name string) error
}

// Orchestrator composes them — constructor shows ALL deps
type runner struct {
    scanner  PromptScanner
    executor Executor
    releaser Releaser
}

func NewRunner(scanner PromptScanner, executor Executor, releaser Releaser) Runner {
    return &runner{scanner: scanner, executor: executor, releaser: releaser}
}

// Factory wires everything
func CreateRunner(promptsDir string) Runner {
    return NewRunner(
        prompt.NewScanner(promptsDir),
        executor.NewDockerExecutor(),
        git.NewReleaser(),
    )
}
```

### RULE go-composition/small-interfaces-1-2-methods (SHOULD)

**Owner**: go-architecture-assistant
**Applies when**: a Go interface declares 3+ methods spanning more than one logical capability — i.e. consumers of the interface use a subset of methods, and the unused-by-this-consumer methods are inferred from method-count plus call-site analysis.
**Enforcement**: judgment (ast-grep follow-up: `type_declaration` with `interface_type` body containing 3+ method specifications; the "one logical capability" check is semantic)
**Why**: The Go convention is "the bigger the interface, the weaker the abstraction" (Rob Pike). A 5-method interface forces every consumer to depend on all 5 methods even when they only use 1 — Counterfeiter generates 5 stubs per test, refactors propagate everywhere, and Interface Segregation Principle violations breed. 1-2 method interfaces are easier to mock, easier to compose, and make each consumer's actual dep surface visible at the type signature. Existing standard library interfaces (`io.Reader`, `io.Writer`, `sort.Interface`, `error`) show the shape: small, focused, composable. SHOULD-level because composition cases (`io.ReadWriteCloser`) and certain framework interfaces legitimately bundle several methods.

#### Bad

```go
// Fat interface — consumers that only need to log get the kitchen sink
type Service interface {
	Log(msg string)
	Save(ctx context.Context, item Item) error
	Load(ctx context.Context, id string) (Item, error)
	Delete(ctx context.Context, id string) error
	Notify(ctx context.Context, evt Event) error
}
```

#### Good

```go
// Logger emits a single log line. Tiny interface — one method.
type Logger interface {
	Log(ctx context.Context, msg string)
}

// ItemStore is the CRUD-like persistence interface for Item entities.
// Three methods because they form one coherent capability (item lifecycle).
type ItemStore interface {
	Save(ctx context.Context, item Item) error
	Load(ctx context.Context, id string) (Item, error)
	Delete(ctx context.Context, id string) error
}

// Notifier publishes an event to the downstream notification fabric.
type Notifier interface {
	Notify(ctx context.Context, evt Event) error
}

// Service composes the three focused interfaces above. Consumers that need
// only one capability take only that one as a parameter — Service is the
// type for the rare consumer that legitimately needs all three.
// Embedded interfaces satisfy ISP: each focused interface is independently
// mockable; Service just declares the union.
type Service interface {
	Logger
	ItemStore
	Notifier
}
```

## Rules

1. **Small interfaces** — 1-2 methods per interface (canonicalised as `go-composition/small-interfaces-1-2-methods`)
2. **All deps via constructor** — never call `pkg.Function()` from business logic (canonicalised as `go-composition/no-package-function-calls-in-business-logic`)
3. **Constructor shows intent** — reading `NewRunner(scanner, executor, releaser)` tells you exactly what it needs
4. **Package functions → wrap in interface** — if you call `git.Push()` directly, extract a `Pusher` interface
5. **Factory composes** — `CreateRunner()` wires all small services together
6. **Test with mocks** — every injected interface gets a counterfeiter mock

## Smell Test

If your constructor has 0-1 dependencies but your methods call 5+ package functions → god object. Refactor: wrap each package in an interface, inject via constructor.

## Package Extraction: Start Flat, Subdivide on Evidence

The decision "should this be its own package?" is independent from "should this be its own type?" Default to a single `pkg/` (plus `pkg/handler/` and `pkg/factory/`) and only extract subpackages when there is concrete evidence that the new boundary earns its keep.

### Extraction Rules

1. **Default: one `pkg/`** — new code goes in `pkg/foo.go`, `pkg/bar.go`, `pkg/baz.go`. Composition (interfaces, constructors, factories) happens within the package.
2. **`pkg/handler/`** — HTTP / RPC / message handlers (top-of-stack, depends on everything).
3. **`pkg/factory/`** — wiring layer (creates everything, depends on everything; bottom-of-call-graph).
4. **Extract to `pkg/<subdomain>/` only when one of these is true:**
   - ≥2 distinct external callers consume the code (not just `pkg/factory` wiring it once)
   - A clear subdomain has formed: multiple files belong together AND have a stable external boundary (e.g. `pkg/storage/`, `pkg/auth/`)
   - The code is reusable across repos (genuinely a library)

### Symptoms of premature extraction

If the new package shows any of these, it should probably be a file inside `pkg/`:

- **Local-interface duplication** — the new package redeclares a "minimal" version of an interface that already exists, "to avoid an import cycle"
- **Single consumer** — only `pkg/foo` (the original caller) uses it; `pkg/factory` wires it once and that's it
- **Adapter shims** — `pkg/factory` contains an `xAdapter` struct just to translate types between two of your own packages
- **Constructor sprawl** — every extraction adds N parameters to the parent constructor; factory.go grows linearly with package count
- **Phantom cycle workarounds** — `var dep Dep` field set via `obj.SetDep(d)` after construction because the constructor "can't" take it

### Why eager extraction hurts

```go
// ❌ Eager — every concept is its own package
pkg/order/
pkg/ordervalidator/    ← only used by order
pkg/orderpricer/       ← only used by order
pkg/ordernotifier/     ← only used by order
pkg/orderaudit/        ← only used by order
pkg/orderdispatcher/   ← only used by order + 1
// ... 10 more
```

Each leaf redefines a "local Customer interface" because importing the real one cycles; `factory.go` bloats with `Create<X>` functions for every leaf; `NewOrder` parameter list grows to 30+; cross-leaf refactors require coordinated multi-package edits.

```go
// ✅ Flat — concepts are FILES inside one package
pkg/
  order.go            ← public Order interface + order struct
  order_validator.go  ← unexported orderValidator helper
  order_pricer.go     ← orderPricer
  order_notifier.go   ← orderNotifier
  order_audit.go      ← orderAudit
  // ...
```

No import cycles, no local-interface duplication; same constructor injection, same testability via counterfeiter; `factory.go` stays small; refactors are single-package edits.

### When the boundary IS earned

Extract when something genuinely independent forms:

- `pkg/storage/` — caching/persistence layer used by multiple domain packages
- `pkg/auth/` — auth concern with its own external API surface
- `pkg/cache/` — used by multiple unrelated callers; has its own configuration shape
- `pkg/git/` — wrapping a stdlib-adjacent dependency, multiple callers, clear seam

The test: **"if we deleted this package, would the reorganisation be obvious or would there be ambiguity about where the contents go?"** If the answer is "obvious — it just becomes files in `pkg/`," it didn't earn its boundary.

## Anti-Pattern: Test-Only Package-Level Mutable State

Same problem as the god object, different shape: production code declares `var X = default` at package level whose only purpose is to let tests override it via a `SetX(d) (restore func())` helper. Often forces a `sync.Mutex` to satisfy `-race`.

```go
// ❌ BAD: test seam leaked into production
var sweepIntervalMu sync.Mutex
var sweepInterval = 60 * time.Second
func getSweepInterval() time.Duration { ... }   // mutex-guarded
func SetSweepInterval(d time.Duration) (restore func()) { ... }  // _test.go
```

```go
// ✅ GOOD: constructor parameter; tests just pass a small value
func NewProcessor(..., sweepInterval time.Duration) Processor { ... }
```

Rule: configurable values that vary between production and tests are **constructor parameters**, not package vars. The default lives in `main.go` / the factory, not at package scope.

(See `go-time-injection.md` for the canonical exception: `libtime.Now` is intentionally a package var because `libtime.ParseTime("NOW-7d")` cannot accept an injected getter — that's a documented carve-out, not the default.)

## Checklist

- Every external dependency is an injected interface
- No `pkg.Function()` calls from business logic methods
- Constructor parameter list shows ALL dependencies
- Each interface has 1-2 methods (rarely 3+)
- Factory function wires all deps together
