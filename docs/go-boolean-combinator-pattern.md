# Go Boolean Combinator Pattern

Pattern for predicate-style interfaces whose implementations compose with `And`, `Or`, and `Not`. Lets callers express compound decisions (e.g. "trusted if author is in allowlist OR is a repo collaborator AND not blocked by label X") without the combinator logic leaking into leaf implementations.

Also known as the **Specification Pattern** in OOP literature.

## When to use

Apply this pattern when:

- You have a single-method "decision" interface (`Check`, `IsTrusted`, `Filtered`, `Allowed`, `Matches`)
- Decisions need to compose with boolean logic
- Compositions may nest (`And{Or{...}, Not{...}}`)
- Each decision needs an explicit reason for traceability (audit logs, error messages, UI feedback)

Skip this pattern when:

- Only one decision is ever applied (no composition)
- Decisions need to share state during evaluation (use Chain of Responsibility instead)
- The "decision" returns a value, not a bool (use Strategy or pipeline patterns)

## Components

A boolean combinator pattern has five parts:

1. **Decision interface** — single method returning a result type
2. **Result type** — bool + description for traceability (never a naked bool)
3. **Func adapter** — function-as-implementation, useful for inline / lambda decisions
4. **`And` combinator** — slice type, all members must vote yes
5. **`Or` combinator** — slice type, any member must vote yes
6. **`Not` wrapper** — function-style negation

## Canonical implementation

```go
package thing

import (
    "context"
    "fmt"
    "strings"

    "github.com/bborbe/errors"
)

// Result captures the decision plus a human-readable description.
// The description is the audit trail: why was this true/false?
type Result interface {
    Success() bool
    Description() string
}

// Check is the single-method decision interface.
type Check interface {
    Check(ctx context.Context, input Input) (Result, error)
}

// CheckFunc adapts a function to the Check interface.
// Useful for inline checks without struct boilerplate.
type CheckFunc func(ctx context.Context, input Input) (Result, error)

func (f CheckFunc) Check(ctx context.Context, input Input) (Result, error) {
    return f(ctx, input)
}

// And succeeds only if every member succeeds.
type And []Check

func (a And) Check(ctx context.Context, input Input) (Result, error) {
    var descriptions []string
    success := true
    for _, c := range a {
        r, err := c.Check(ctx, input)
        if err != nil {
            return nil, errors.Wrapf(ctx, err, "and check failed")
        }
        if !r.Success() {
            success = false
        }
        descriptions = append(descriptions, fmt.Sprintf("[%t] %s", r.Success(), r.Description()))
    }
    return NewResult(success, "and("+strings.Join(descriptions, ", ")+")"), nil
}

// Or succeeds if any member succeeds.
type Or []Check

func (o Or) Check(ctx context.Context, input Input) (Result, error) {
    var descriptions []string
    success := false
    for _, c := range o {
        r, err := c.Check(ctx, input)
        if err != nil {
            return nil, errors.Wrapf(ctx, err, "or check failed")
        }
        if r.Success() {
            success = true
        }
        descriptions = append(descriptions, fmt.Sprintf("[%t] %s", r.Success(), r.Description()))
    }
    return NewResult(success, "or("+strings.Join(descriptions, ", ")+")"), nil
}

// Not inverts the decision of the wrapped check.
func Not(c Check) Check {
    return CheckFunc(func(ctx context.Context, input Input) (Result, error) {
        r, err := c.Check(ctx, input)
        if err != nil {
            return nil, errors.Wrapf(ctx, err, "not check failed")
        }
        return NewResult(!r.Success(), "not("+r.Description()+")"), nil
    })
}
```

## Composition examples

```go
// Simple AND: all conditions must hold
truster := And{
    AuthorAllowlist([]string{"alice", "bob"}),
    NoBlockedLabel("do-not-review"),
}

// Simple OR: any condition wins
truster := Or{
    AuthorAllowlist([]string{"alice"}),
    IsCollaborator(ghClient),
}

// Nested: trusted if (allowlisted OR collaborator) AND not blocked
truster := And{
    Or{
        AuthorAllowlist([]string{"alice"}),
        IsCollaborator(ghClient),
    },
    Not(HasLabel("blocked")),
}

// Inline check via Func adapter
truster := And{
    AuthorAllowlist([]string{"alice"}),
    CheckFunc(func(ctx context.Context, pr Input) (Result, error) {
        if pr.Title == "" {
            return NewResult(false, "title empty"), nil
        }
        return NewResult(true, "title present"), nil
    }),
}
```

## Result types

Always return a structured result, never a naked `bool`. The description field is what makes the pattern auditable.

```go
type result struct {
    success     bool
    description string
}

func NewResult(success bool, description string) Result {
    return &result{success: success, description: description}
}

func (r *result) Success() bool        { return r.success }
func (r *result) Description() string  { return r.description }
```

When a check fails, the description should name the dimension that failed:

```go
// [GOOD] — names the rule
NewResult(false, "author 'alice' not in allowlist [bborbe]")

// [BAD] — opaque
NewResult(false, "untrusted")
```

When `And` / `Or` aggregate multiple results, the description preserves the per-leaf reasons. This is what lets the audit log (or human-review task body, or error message) explain WHY a compound decision came out the way it did.

## Anti-patterns

### Naked `bool` return

```go
// [BAD] — no audit trail; caller can't explain a "no" to the user
type Check interface {
    Check(ctx context.Context, input Input) (bool, error)
}
```

When a compound check returns `false`, you cannot tell which leaf vetoed without re-running with logging enabled.

### Empty list = vacuous truth

```go
// Default-empty And{} returns success; default-empty Or{} returns failure.
// Both are mathematically correct but security-dangerous.
And{}.Check(ctx, input) // → Success: true (vacuous AND)
Or{}.Check(ctx, input)  // → Success: false (vacuous OR)
```

For security-relevant decisions (trust, authorization), an empty configuration is almost always misconfiguration. Detect at construction time:

```go
// [GOOD] Fail-safe: refuse empty configuration
func NewTruster(ctx context.Context, checks []Check) (Check, error) {
    if len(checks) == 0 {
        return nil, errors.Errorf(ctx, "truster requires at least one check")
    }
    return And(checks), nil
}
```

Or treat empty as "always-deny" (for `And` semantics in security contexts), and document loudly.

### Nesting via callbacks

```go
// [BAD] — unrelated to the combinator pattern; not introspectable
truster := func(ctx context.Context, input Input) (Result, error) {
    a, _ := allowlistCheck(ctx, input)
    if a.Success() { return a, nil }
    return collaboratorCheck(ctx, input)
}
```

A function-typed combinator can't be introspected (which leaves are inside? in what order?). Use the slice types — they're inspectable:

```go
// [GOOD] — combinator structure visible at runtime
truster := Or{allowlistCheck, collaboratorCheck}
```

### Side effects in checks

Each `Check` should be a pure decision: same input → same output. Side effects (logging, metric emission, mutation) belong in the orchestrator that *consumes* the result, not in the leaves. A side-effecting check that runs inside `Or` may execute or skip depending on short-circuit order, producing surprising behavior.

### Mutating the input

Checks must NOT mutate their input. The same input is passed to every leaf in `And` / `Or`. If one check mutates `pr.Status`, downstream checks see the mutated state and the order of evaluation becomes a hidden dependency.

## Performance considerations

`And` and `Or` evaluate every member, even after the result is decided. This is intentional: it produces complete audit trails (every leaf's reason is recorded). If short-circuit evaluation matters for cost (e.g., a check that hits an external API), introduce explicit short-circuit variants:

```go
// ShortCircuitAnd stops at the first failure.
type ShortCircuitAnd []Check

func (a ShortCircuitAnd) Check(ctx context.Context, input Input) (Result, error) {
    for _, c := range a {
        r, err := c.Check(ctx, input)
        if err != nil {
            return nil, err
        }
        if !r.Success() {
            return r, nil
        }
    }
    return NewResult(true, "all passed"), nil
}
```

Document the trade-off explicitly: short-circuit versions trade audit completeness for execution cost. Default to non-short-circuit unless cost demands otherwise.

## Related patterns

- **Filter pattern** (`go-filter-pattern.md`) — predicate-based inclusion/exclusion. Single-leaf filters become combinator leaves when composition is needed.
- **Functional composition pattern** (`go-functional-composition-pattern.md`) — generic Interface + Func + List trio. Boolean combinators are a specialization with `And` / `Or` semantics added.
- **Specification pattern** (Eric Evans, DDD) — the OOP origin of this pattern; same structure, different name.

## Checklist for new boolean-combinator implementations

- [ ] Single-method decision interface returning `(Result, error)`
- [ ] `Result` is structured (success + description), never a naked bool
- [ ] `Func`-typed adapter for inline checks
- [ ] `And` slice type with full audit trail in description
- [ ] `Or` slice type with full audit trail in description
- [ ] `Not()` wrapper preserving description
- [ ] Empty-list handling is documented and fail-safe for security uses
- [ ] At least one leaf implementation in the same package as a usage example
- [ ] Test covering nested compositions (`And{Or{...}, Not{...}}`) to lock in algebra
