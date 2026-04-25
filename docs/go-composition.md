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
