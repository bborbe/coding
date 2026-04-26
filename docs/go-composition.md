# Go Service Composition

Orchestrators compose small single-responsibility services. Never call package-level functions directly from business logic.

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

## Rules

1. **Small interfaces** — 1-2 methods per interface (SRP)
2. **All deps via constructor** — never call `pkg.Function()` from business logic
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
