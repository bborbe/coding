# Go Patterns (YOLO)

## Core Pattern: Interface → Constructor → Struct → Method

```go
// 1. Interface with counterfeiter comment — mock name and filename MUST be
//    prefixed with the source package (here `service`) to avoid collisions in
//    the flat mocks/ directory. See go-mocking-guide.md for full rules.
//counterfeiter:generate -o ../../mocks/service-my-service.go --fake-name ServiceMyService . MyService
type MyService interface {
    Do(ctx context.Context, input Input) error
}

// 2. Constructor returns interface, not struct
func NewMyService(dep SomeDep) MyService {
    return &myService{dep: dep}
}

// 3. Private struct
type myService struct {
    dep SomeDep
}

// 4. Methods on pointer receiver
func (s *myService) Do(ctx context.Context, input Input) error {
    result, err := s.dep.Call(ctx, input)
    if err != nil {
        return errors.Wrap(ctx, err, "call failed")
    }
    return nil
}
```

## Key Rules

**Error handling** — always wrap with context (see `go-error-wrapping.md` for full rules):
```go
return errors.Wrapf(ctx, err, "operation failed")  // github.com/bborbe/errors
// Never fmt.Errorf. Never context.Background() — add ctx param instead.
```

**Context** — always pass through, never create `context.Background()` in business logic. If a function lacks ctx, add it as a parameter:
```go
func (s *myService) Process(ctx context.Context, ...) error { ... }
```

**Mocks** — always use counterfeiter, never write manually. Both the filename and the `--fake-name` MUST include the source package as a prefix:
```go
// On interface (source file in package `service`):
//counterfeiter:generate -o ../../mocks/service-dep.go --fake-name ServiceDep . Dep

// In *_suite_test.go (one per package, triggers generation):
//go:generate go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate
```

**NEVER** use `//go:generate counterfeiter ...` — it calls a globally installed binary which may be built with the wrong Go version. Always use the two-part pattern above: `//counterfeiter:generate` on the interface + `//go:generate go run -mod=mod ...` in suite_test.go.

### RULE go-patterns/bborbe-collection-ptr-not-helpers (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go file declares a custom pointer helper function (`func stringPtr(s string) *string { return &s }`, `func intPtr(...)`, etc.) instead of importing `github.com/bborbe/collection` and calling `collection.Ptr(...)`.
**Enforcement**: judgment (ast-grep follow-up: `function_declaration` returning a pointer-to-builtin with a body containing only `return &<param>`)
**Why**: Every codebase that needs pointer values for optional struct fields ends up writing 3-5 of these helpers. They proliferate across packages, each one slightly differently named (`strPtr` vs `stringPtr` vs `pStr`), and tests do their own (`stringPtr("test")` in test A, `&[]string{"test"}[0]` in test B). `github.com/bborbe/collection.Ptr` is a generic single helper that handles every type. Adopting it everywhere collapses the proliferation to one import line per package and lets refactors find every usage with `grep collection.Ptr`.

#### Bad

```go
// Custom helpers — proliferate across packages
func stringPtr(s string) *string { return &s }
func intPtr(i int) *int          { return &i }
func boolPtr(b bool) *bool       { return &b }

req := APIRequest{
	Name: stringPtr("alice"),
	Age:  intPtr(30),
}
```

#### Good

```go
import libcollection "github.com/bborbe/collection"

req := APIRequest{
	Name: libcollection.Ptr("alice"),  // generic — works for every type
	Age:  libcollection.Ptr(30),
}
```

### RULE go-patterns/switch-over-if-chain-for-dispatch (SHOULD)

**Owner**: go-quality-assistant
**Applies when**: a Go file dispatches behaviour on an enum-typed value (`OrderStatus`, `WorkflowMode`, `Phase`) using an `if/else if/else` chain over equality comparisons, instead of a `switch` statement with explicit cases + a `default` arm returning an error for unknown values.
**Enforcement**: judgment (ast-grep follow-up: `if_statement` chains with 3+ branches comparing the same expression to enum-typed constants; the agent rules in the "this is dispatch, not coincidental equality checks" case)
**Why**: A `switch` over an enum with explicit cases + `default: return errors.Errorf(ctx, "unknown X: %s", v)` makes three things visible: (1) every recognised value is named in its own case, so `grep` finds dispatch sites; (2) the `default` arm catches "we added a new enum value but forgot to handle it here" — surfaces as a real error at runtime instead of silent fallthrough; (3) the structure documents the closed set the function understands. `if/else` chains hide all three: dispatch sites look like arbitrary conditionals, missing-case is silent, and reading the function doesn't surface the value space.

#### Bad

```go
// if/else chain over 3+ enum values — silent fallthrough,
// new enum value silently runs handleDirect
if w.mode == config.WorkflowPR {
	return w.handlePR(ctx)
} else if w.mode == config.WorkflowMerge {
	return w.handleMerge(ctx)
} else if w.mode == config.WorkflowRebase {
	return w.handleRebase(ctx)
}
return w.handleDirect(ctx) // ← also runs when mode is the new WorkflowDarkFactory we forgot to handle
```

#### Good

```go
// switch with explicit cases + default — new enum value triggers default error
switch w.mode {
case config.WorkflowDirect:
	return w.handleDirect(ctx)
case config.WorkflowPR:
	return w.handlePR(ctx)
case config.WorkflowMerge:
	return w.handleMerge(ctx)
case config.WorkflowRebase:
	return w.handleRebase(ctx)
default:
	return errors.Errorf(ctx, "unknown workflow: %s", w.mode)
}
```

**Pointer utilities** — use `github.com/bborbe/collection`:
```go
val := libcollection.Ptr("hello")  // not func strPtr(s string) *string
```

**Switch over if-chain** — use `switch` when dispatching on a type/enum value:
```go
// ✅ explicit cases, catches unknown values
switch w.mode {
case config.WorkflowDirect:
    return w.handleDirect(ctx)
case config.WorkflowPR:
    return w.handlePR(ctx)
default:
    return fmt.Errorf("unknown workflow: %s", w.mode)
}

// ❌ silent fallthrough, easy to miss a case
if w.mode == config.WorkflowPR { ... }
return w.handleDirect(ctx)
```

## File Structure

```
project/
├── main.go
├── pkg/
│   ├── domain/     # types, interfaces
│   ├── storage/    # data access
│   └── ops/        # business logic
└── mocks/          # generated by counterfeiter
```

## Verification

```bash
make test        # run tests (NEVER go build ./...)
make precommit   # full validation before commit
go generate -mod=mod ./...  # regenerate mocks after interface changes
```

**Mono-repo warning:** If the project has multiple `go.mod` files (e.g. `trading/`), NEVER run `make test` or `make precommit` at the root — it recurses into all subdirs and takes 10+ minutes. Run only in the changed service directory:

```bash
# ✅ correct
cd core/myservice && make test

# ❌ wrong
cd /workspace && make test
```
