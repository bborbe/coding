# Go Linting Guide

Comprehensive guide for golangci-lint v2 configuration, linter rules, and fix strategies used across all Go projects. The canonical config lives in [go-skeleton/.golangci.yml](https://github.com/bborbe/go-skeleton).

## Table of Contents

1. [Configuration Reference](#configuration-reference)
2. [Enabled Linters](#enabled-linters)
3. [Complexity Limits](#complexity-limits)
4. [Banned Packages (depguard)](#banned-packages-depguard)
5. [Security Linting (gosec)](#security-linting-gosec)
6. [Error Checking (errcheck)](#error-checking-errcheck)
7. [Code Style (revive)](#code-style-revive)
8. [Formatters](#formatters)
9. [Test File Exclusions](#test-file-exclusions)
10. [Line Length](#line-length)
11. [Common Fix Strategies](#common-fix-strategies)
12. [Checklist](#checklist)

## Configuration Reference

All projects use golangci-lint v2 with this `.golangci.yml`:

```yaml
version: "2"

run:
  timeout: 5m
  tests: true

linters:
  enable:
    - govet
    - errcheck
    - staticcheck
    - unused
    - revive
    - gosec
    - gocyclo
    - depguard
    - dupl
    - funlen
    - gocognit
    - nestif
    - maintidx
    - errname
    - unparam
    - bodyclose
    - forcetypeassert
    - asasalint
    - prealloc
  settings:
    depguard:
      rules:
        Main:
          deny:
            - pkg: "sigs.k8s.io/structured-merge-diff/v4"
              desc: "use sigs.k8s.io/structured-merge-diff/v6 instead"
            - pkg: "github.com/containerd/containerd"
              desc: "use github.com/containerd/containerd/v2 instead"
            - pkg: "github.com/pkg/errors"
              desc: "use github.com/bborbe/errors instead"
            - pkg: "github.com/bborbe/argument"
              desc: "use github.com/bborbe/argument/v2 instead"
            - pkg: "golang.org/x/net/context"
              desc: "use context from standard library instead"
            - pkg: "golang.org/x/lint/golint"
              desc: "deprecated, use revive or staticcheck instead"
            - pkg: "io/ioutil"
              desc: "deprecated since Go 1.16, use io and os packages instead"
    funlen:
      lines: 80
      statements: 50
    gocognit:
      min-complexity: 20
    nestif:
      min-complexity: 4
    maintidx:
      min-maintainability-index: 20
  exclusions:
    presets:
      - comments
      - std-error-handling
      - common-false-positives
    rules:
      - linters:
          - staticcheck
        text: "SA1019"
      - linters:
          - revive
        path: "_test\\.go$"
        text: "dot-imports"
      - linters:
          - revive
        text: "unused-parameter"
      - linters:
          - revive
        text: "exported"
      - linters:
          - dupl
        path: "_test\\.go$"
      - linters:
          - unparam
        path: "_test\\.go$"

formatters:
  enable:
    - gofmt
    - goimports
```

## Enabled Linters

### Core Linters

| Linter | What it catches | Severity |
|--------|----------------|----------|
| `govet` | Suspicious constructs (printf args, struct tags, unreachable code) | Critical |
| `errcheck` | Unchecked error return values | Critical |
| `staticcheck` | Comprehensive static analysis (SA series) | Critical |
| `unused` | Unused variables, functions, types | Critical |
| `gosec` | Security vulnerabilities (file perms, path injection, subprocess) | Critical |

### Style & Complexity Linters

| Linter | What it catches | Severity |
|--------|----------------|----------|
| `revive` | Go code style (naming, returns, control flow) | Important |
| `gocyclo` | Cyclomatic complexity | Important |
| `funlen` | Function length (>80 lines or >50 statements) | Important |
| `gocognit` | Cognitive complexity (>20) | Important |
| `nestif` | Deeply nested if statements (>4 levels) | Important |
| `maintidx` | Low maintainability index (<20) | Important |
| `errname` | Error variable naming conventions (`ErrFoo`, not `FooError`) | Important |

### Bug Prevention Linters

| Linter | What it catches | Severity |
|--------|----------------|----------|
| `depguard` | Banned package imports | Critical |
| `dupl` | Duplicate code blocks | Warning |
| `unparam` | Unused function parameters | Warning |
| `bodyclose` | Unclosed HTTP response bodies | Critical |
| `forcetypeassert` | Type assertions without ok check | Important |
| `asasalint` | Incorrect `any` usage in variadic functions | Important |
| `prealloc` | Slice preallocation opportunities | Warning |

## Complexity Limits

| Linter | Limit | Description |
|--------|-------|-------------|
| `funlen` | 80 lines / 50 statements | Max function length |
| `gocognit` | 20 complexity | Max cognitive complexity |
| `nestif` | 4 levels | Max if-nesting depth |
| `maintidx` | 20 minimum | Min maintainability index |

### How to Stay Under Limits

- Extract helper functions at 40+ lines (leave room for growth)
- Use early returns instead of nested if/else
- Extract complex conditions: `if s.isReady(ctx)` not `if s.x && s.y || s.z`
- One concern per function
- Table-driven approaches for repetitive logic

```go
// BAD: 6 nesting levels, high complexity
func (s *Service) Process(ctx context.Context, items []Item) error {
    for _, item := range items {
        if item.IsValid() {
            if item.NeedsUpdate() {
                if result, err := s.update(ctx, item); err != nil {
                    if errors.Is(err, ErrNotFound) {
                        // handle not found
                    } else {
                        return err
                    }
                } else {
                    // use result
                }
            }
        }
    }
    return nil
}

// GOOD: early returns, extracted helpers
func (s *Service) Process(ctx context.Context, items []Item) error {
    for _, item := range items {
        if err := s.processItem(ctx, item); err != nil {
            return errors.Wrapf(ctx, err, "process item %s", item.ID)
        }
    }
    return nil
}

func (s *Service) processItem(ctx context.Context, item Item) error {
    if !item.IsValid() {
        return nil
    }
    if !item.NeedsUpdate() {
        return nil
    }
    _, err := s.update(ctx, item)
    if errors.Is(err, ErrNotFound) {
        return nil // expected, skip
    }
    return err
}
```

## Banned Packages (depguard)

| Banned Package | Use Instead | Reason |
|---------------|-------------|--------|
| `github.com/pkg/errors` | `github.com/bborbe/errors` | Context-aware error wrapping |
| `github.com/bborbe/argument` | `github.com/bborbe/argument/v2` | v1 deprecated |
| `golang.org/x/net/context` | `context` (stdlib) | Moved to stdlib in Go 1.7 |
| `golang.org/x/lint/golint` | `revive` or `staticcheck` | Deprecated |
| `io/ioutil` | `io` and `os` packages | Deprecated since Go 1.16 |
| `sigs.k8s.io/structured-merge-diff/v4` | `sigs.k8s.io/structured-merge-diff/v6` | Outdated |
| `github.com/containerd/containerd` | `github.com/containerd/containerd/v2` | Outdated |

## Security Linting (gosec)

### File Permissions (G306)

```go
// BAD: gosec G306 — world-readable
os.WriteFile(path, data, 0644)
os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0644)
os.MkdirAll(dir, 0755)

// GOOD: owner-only permissions
os.WriteFile(path, data, 0600)
os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0600)
os.MkdirAll(dir, 0750)
```

### File Path from Variable (G304)

```go
// BAD: gosec G304 — file path from variable
data, err := os.ReadFile(userPath)

// GOOD: suppress with comment when path is trusted
// #nosec G304 -- path from internal ListQueued(), not user input
data, err := os.ReadFile(trustedPath)
```

### Subprocess from Variable (G204)

```go
// BAD: gosec G204 — command from variable
cmd := exec.CommandContext(ctx, binary, args...)

// GOOD: suppress when command is controlled
// #nosec G204 -- binary is hardcoded constant, args from trusted config
cmd := exec.CommandContext(ctx, "git", "push")
```

### gosec Rules

1. **Default to `0600` for files, `0750` for directories** — always
2. **Never suppress without explanation** — `#nosec G304 -- reason here`
3. **Fix on first attempt** — don't iterate through `make precommit` multiple times
4. **Suppress only when the input is trusted** — internal paths, hardcoded commands
5. **`os.Chmod` return value must be checked** — `if err := os.Chmod(...); err != nil`
6. **Lock/PID files**: use `0600` permissions, not `0644`

## Error Checking (errcheck)

Every error must be checked. Exceptions via `std-error-handling` preset: `Close`, `Write`, `Fprint`.

```go
// BAD: errcheck will fail
os.Remove(path)
os.Chmod(path, 0600)

// GOOD: explicit ignore or handle
_ = os.Remove(path)  // cleanup, error irrelevant
if err := os.Chmod(path, 0600); err != nil {
    return errors.Wrapf(ctx, err, "chmod")
}
```

### Error Naming (errname)

```go
// BAD: errname violation
var FooError = errors.New("foo")
type BarError struct{}

// GOOD: Err prefix for sentinel errors
var ErrFoo = errors.New("foo")
type ErrBar struct{}
```

## Code Style (revive)

Revive enforces Go code style. These rules are **excluded** (won't trigger):

| Excluded Rule | Why |
|---------------|-----|
| `dot-imports` in test files | Ginkgo/Gomega require dot imports |
| `unused-parameter` | Too noisy for interface implementations |
| `exported` | GoDoc enforcement handled separately |

### bodyclose

Always close HTTP response bodies:

```go
// BAD: bodyclose — response body leaked
resp, err := http.Get(url)
if err != nil {
    return err
}
// missing resp.Body.Close()

// GOOD
resp, err := http.Get(url)
if err != nil {
    return err
}
defer resp.Body.Close()
```

### forcetypeassert

Always use the two-value form for type assertions:

```go
// BAD: forcetypeassert — panics on wrong type
val := x.(string)

// GOOD: safe assertion
val, ok := x.(string)
if !ok {
    return errors.Errorf(ctx, "expected string, got %T", x)
}
```

## Formatters

Two formatters run automatically:

| Formatter | Purpose |
|-----------|---------|
| `gofmt` | Standard Go formatting |
| `goimports` | Import grouping and ordering |

Additionally, `golines` (run separately in `make precommit`) enforces max 100 character line length.

## Test File Exclusions

Test files (`_test.go`) get relaxed rules:

| Linter | Exclusion | Reason |
|--------|-----------|--------|
| `revive` (dot-imports) | Allowed in tests | Ginkgo/Gomega require `. "github.com/onsi/ginkgo/v2"` |
| `dupl` | Disabled in tests | Test cases are intentionally repetitive |
| `unparam` | Disabled in tests | Test helpers often have unused params for consistency |

### What Still Applies in Tests

All other linters apply in test files, including:
- `funlen` — test functions can get long, extract helpers
- `errcheck` — check errors even in tests
- `gosec` — security rules apply everywhere
- `nestif` — keep test setup flat

## Line Length

`golines` enforces **max 100 characters**. Write short lines from the start:

```go
// BAD: will be reformatted
result, err := s.longServiceName.DoSomethingComplex(ctx, param1, param2, param3)

// GOOD: already within limit
result, err := s.svc.DoSomething(
    ctx, param1, param2, param3,
)
```

## Common Fix Strategies

### Slice Preallocation (prealloc)

```go
// BAD: prealloc — slice grows dynamically
var results []Result
for _, item := range items {
    results = append(results, process(item))
}

// GOOD: preallocated
results := make([]Result, 0, len(items))
for _, item := range items {
    results = append(results, process(item))
}
```

### Slice Membership (slicescontains)

```go
// BAD: manual loop for membership check
func contains(s []string, v string) bool {
    for _, item := range s {
        if item == v { return true }
    }
    return false
}

// GOOD: use stdlib
import "slices"
slices.Contains(s, v)
```

### Duplicate Code (dupl)

```go
// BAD: duplicated blocks across functions
func (s *Service) CreateUser(ctx context.Context, u User) error {
    if u.Name == "" { return ErrEmptyName }
    if u.Email == "" { return ErrEmptyEmail }
    return s.store.Save(ctx, u)
}
func (s *Service) UpdateUser(ctx context.Context, u User) error {
    if u.Name == "" { return ErrEmptyName }
    if u.Email == "" { return ErrEmptyEmail }
    return s.store.Update(ctx, u)
}

// GOOD: extract shared validation
func (u User) Validate() error {
    if u.Name == "" { return ErrEmptyName }
    if u.Email == "" { return ErrEmptyEmail }
    return nil
}
```

## Checklist

Before running `make precommit`:

- [ ] Functions under 80 lines, nesting under 4 levels
- [ ] Lines under 100 characters
- [ ] No banned packages (depguard)
- [ ] All errors checked or explicitly ignored with `_ =`
- [ ] All `#nosec` annotations have explanatory comments
- [ ] File permissions: `0600` for files, `0750` for directories
- [ ] HTTP response bodies closed with `defer resp.Body.Close()`
- [ ] Type assertions use two-value form `val, ok := x.(Type)`
- [ ] Slices preallocated where length is known
- [ ] `slices.Contains` instead of manual loops
- [ ] License header on new `.go` files
- [ ] Error variables named `ErrFoo`, not `FooError`
