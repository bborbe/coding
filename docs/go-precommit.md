# Go Precommit Checks

`make precommit` runs these checks. Know the rules BEFORE writing code to avoid iteration loops.

## Complexity Limits (golangci-lint)

```yaml
funlen:    80 lines max per function    # split into helper functions
gocognit:  20 complexity max            # reduce nesting, early returns
nestif:    4 nesting levels max         # extract conditions into methods
maintidx:  20 maintainability min       # keep functions focused
```

**How to stay under limits:**
- Extract helper functions at 40+ lines (leave room for growth)
- Use early returns instead of nested if/else
- Extract complex conditions: `if s.isReady(ctx)` not `if s.x && s.y || s.z`
- One concern per function

## Line Length

`golines` enforces **max 100 characters**. Write short lines from the start:
```go
// ❌ BAD: will be reformatted
result, err := s.longServiceName.DoSomethingComplex(ctx, param1, param2, param3)

// ✅ GOOD: already within limit
result, err := s.svc.DoSomething(
    ctx, param1, param2, param3,
)
```

## Banned Packages (depguard)

```go
// ❌ BANNED                          // ✅ USE INSTEAD
"github.com/pkg/errors"              // github.com/bborbe/errors
"github.com/bborbe/argument"         // github.com/bborbe/argument/v2
"golang.org/x/net/context"           // context (stdlib)
"golang.org/x/lint/golint"           // revive or staticcheck
"io/ioutil"                          // io and os packages
```

## Error Checking (errcheck)

Every error must be checked. Exceptions: `Close`, `Write`, `Fprint`.

```go
// ❌ BAD: errcheck will fail
os.Remove(path)
os.Chmod(path, 0600)

// ✅ GOOD
_ = os.Remove(path)  // cleanup, error irrelevant
if err := os.Chmod(path, 0600); err != nil {
    return errors.Wrap(ctx, err, "chmod")
}
```

## License Headers (addlicense)

Every `.go` file needs BSD header. Auto-added by `make precommit` but write it yourself on new files:
```go
// Copyright (c) 2026 Benjamin Borbe All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.
```

## Mock Generation

`make precommit` deletes and regenerates `mocks/`. Never hand-write mocks.

## Checklist (before running make precommit)

- [ ] Functions under 80 lines
- [ ] Nesting under 4 levels
- [ ] Lines under 100 chars
- [ ] No banned packages
- [ ] All errors checked
- [ ] License header on new files
- [ ] `#nosec` annotations have reasons (see `go-security-linting.md`)
- [ ] Use `slices.Contains` instead of manual loops — `slicescontains` linter enforces this
