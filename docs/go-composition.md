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

## Checklist

- Every external dependency is an injected interface
- No `pkg.Function()` calls from business logic methods
- Constructor parameter list shows ALL dependencies
- Each interface has 1-2 methods (rarely 3+)
- Factory function wires all deps together
