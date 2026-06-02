# Go Testing Guide

Rules-only version. Captures the enforceable testing conventions that `coding:go-test-quality-assistant`, `coding:go-test-writer-assistant`, and `coding:go-test-coverage-assistant` check during `/coding:pr-review`. For deeper background (database patterns, JSON/serialization, integration setups, full Ginkgo/Gomega API), consult the official documentation linked at the end of this file.

## Framework

Built on **[Ginkgo v2](https://onsi.github.io/ginkgo/)** (BDD) + **[Gomega](https://onsi.github.io/gomega/)** (matchers) + **[Counterfeiter](https://github.com/maxbrunsfeld/counterfeiter)** (mocks).

Key principles:

- BDD: tests describe behavior, not implementation.
- Tests are independent and idempotent.
- Mocks at interface boundaries; real implementations for internal utilities.
- All time handling uses UTC (`time.Local = time.UTC` in suite setup).

## Critical Rules

**MUST NOT use stdlib `testing` table-driven tests.** Always use Ginkgo `DescribeTable`/`Entry`. If a `*_suite_test.go` with Ginkgo imports exists in the package, all tests must use Ginkgo.

```go
// BAD — stdlib table-driven test
func TestFoo(t *testing.T) {
	tests := []struct{ input, want string }{ ... }
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) { ... })
	}
}

// GOOD — Ginkgo DescribeTable
var _ = DescribeTable("foo",
	func(input, expected string) {
		Expect(foo(input)).To(Equal(expected))
	},
	Entry("case A", "in1", "out1"),
	Entry("case B", "in2", "out2"),
)
```

**MUST NOT use `testing.T` directly** in packages that have a Ginkgo test suite. Use `Describe`/`Context`/`It`/`DescribeTable`/`Entry` instead.

**MUST NOT call an error-returning function bare in an `It` block.** `errcheck` (run by `make precommit`) will fail. Wrap with a matcher that documents intent:

- Expecting success: `Expect(someFunc(ctx)).To(Succeed())`
- Expecting failure: `Expect(someFunc(ctx)).To(HaveOccurred())`
- Need the error: `err := someFunc(ctx); Expect(err).To(MatchError(...))`

```go
// BAD — errcheck: "Error return value not checked"
It("calls Save exactly twice", func() {
	service.Process(ctx)
	Expect(store.SaveCallCount()).To(Equal(2))
})

// GOOD — error explicitly accounted for
It("calls Save exactly twice", func() {
	Expect(service.Process(ctx)).To(HaveOccurred())
	Expect(store.SaveCallCount()).To(Equal(2))
})
```

## Test Suite Setup

**MUST provide a `*_suite_test.go` file in every package with tests.** Without it, Ginkgo specs are not discovered and `make test` silently misses coverage.

### Standard Package Suite

```go
// Copyright (c) 2026 Benjamin Borbe All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package pkg_test

import (
	"testing"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/format"
)

//go:generate go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate
func TestSuite(t *testing.T) {
	time.Local = time.UTC
	format.TruncatedDiff = false
	RegisterFailHandler(Fail)
	suiteConfig, reporterConfig := GinkgoConfiguration()
	suiteConfig.Timeout = 60 * time.Second
	RunSpecs(t, "Test Suite", suiteConfig, reporterConfig)
}
```

Requirements:

- **External test package**: `package_test` suffix (e.g. `pkg_test`, `user_test`) — keeps tests honest about exported surface.
- **UTC timezone**: `time.Local = time.UTC` — eliminates locale flakiness.
- **Full diffs**: `format.TruncatedDiff = false` — never hide assertion failures.
- **Suite timeout**: `suiteConfig.Timeout` — safety net against hanging tests.
- **`//go:generate`**: enables `go generate ./...` for Counterfeiter mocks.

### Main Package Suite (special case)

**MUST include `main_test.go` for every binary project.** Without it, build failures are not caught by `make test`.

```go
// Copyright (c) 2026 Benjamin Borbe All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

//go:generate go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate

package main_test

import (
	"testing"
	"time"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/onsi/gomega/format"
	"github.com/onsi/gomega/gexec"
)

var _ = Describe("Main", func() {
	It("Compiles", func() {
		var err error
		_, err = gexec.Build(".", "-mod=mod", "-buildvcs=false")
		Expect(err).NotTo(HaveOccurred())
	})
})

func TestSuite(t *testing.T) {
	time.Local = time.UTC
	format.TruncatedDiff = false
	RegisterFailHandler(Fail)
	suiteConfig, reporterConfig := GinkgoConfiguration()
	suiteConfig.Timeout = 60 * time.Second
	RunSpecs(t, "Main Suite", suiteConfig, reporterConfig)
}
```

The `Compiles` test verifies buildability via `gexec.Build` with `-buildvcs=false`. Main is the **only** exception to the standard pattern — all other packages (internal, pkg, cmd subpackages) use the standard form.

## AAA Pattern + Lifecycle

Tests follow **Arrange / Act / Assert** via Ginkgo lifecycle hooks:

- `BeforeEach` — setup before each `It` (Arrange)
- `JustBeforeEach` — action just before each `It`, after all `BeforeEach` (Act)
- `AfterEach` — cleanup after each `It`
- `Context` — groups related scenarios
- `It` — individual assertions

```go
var _ = Describe("Product", func() {
	var ctx context.Context
	var product domain.Product
	var result domain.Price

	BeforeEach(func() {
		ctx = context.Background()
		product = domain.Product{Name: "Example", Price: 99.99}
	})

	Context("CalculateDiscount", func() {
		JustBeforeEach(func() {
			result = product.CalculateDiscount(0.1)
		})

		It("returns correct discounted price", func() {
			Expect(result).To(Equal(domain.Price(89.99)))
		})
	})
})
```

## Test Timeouts

**MUST set a suite-level timeout.** Every suite file includes `suiteConfig.Timeout` as a safety net against hanging tests.

Per-spec timeout:

```go
It("does something within 2s", func(ctx context.Context) {
	// test body
}, SpecTimeout(2*time.Second))
```

Per-node timeout for `Describe`/`Context`/`It`:

```go
Describe("slow subsystem", func() {
	It("completes within 5s", func(ctx SpecContext) {
		Eventually(ctx, func() bool { return ready }).Should(BeTrue())
	}, NodeTimeout(5*time.Second))
})
```

## Mock Generation

**MUST use Counterfeiter-generated mocks.** Never hand-write mocks — they drift from the interface and break silently.

### Generate Directive

Place a `//counterfeiter:generate` line above each interface that needs a mock, then `go generate ./...` produces the fake.

```go
//counterfeiter:generate -o mocks/user-service.go --fake-name UserService . Service
type Service interface {
	Create(ctx context.Context, user User) error
	Get(ctx context.Context, id string) (*User, error)
}
```

Conventions:

- **`-o mocks/<file>.go`** — mocks live in a `mocks/` subpackage, never alongside production code.
- **`--fake-name <Name>`** — drop the `Fake` prefix; Counterfeiter's default `FakeService` becomes `UserService` for cleaner test code.
- **One mock per file** — never bundle multiple fakes in one generated file.

### Mock Usage

```go
mockService := &mocks.UserService{}
mockService.CreateReturns(nil)

err := caller.DoSomething(ctx, mockService)
Expect(err).To(Succeed())

// Verify call count + args
Expect(mockService.CreateCallCount()).To(Equal(1))
actualCtx, actualUser := mockService.CreateArgsForCall(0)
Expect(actualCtx).To(Equal(ctx))
Expect(actualUser.Name).To(Equal("test"))
```

## Time Handling

**MUST inject time via `libtime.CurrentDateTimeGetter` from `github.com/bborbe/time`.** Never call `time.Now()` directly in business logic — tests cannot control it.

```go
import libtime "github.com/bborbe/time"

var _ = Describe("Service", func() {
	var currentDateTime libtime.CurrentDateTime
	var service Service
	var fixedTime time.Time

	BeforeEach(func() {
		fixedTime = time.Date(2026, 6, 2, 12, 0, 0, 0, time.UTC)
		currentDateTime = libtime.NewCurrentDateTime()
		currentDateTime.SetNow(fixedTime)
		service = NewService(currentDateTime)
	})

	It("uses the injected time", func() {
		Expect(service.GetTimestamp()).To(Equal(fixedTime))
	})
})
```

Helpers:

```go
import libtimetest "github.com/bborbe/time/test"

fixedTime := libtimetest.ParseDateTime("2026-06-02T00:00:00Z")

Expect(actualTime).To(BeTemporally("~", expectedTime, time.Second))
Expect(actualTime).To(BeTemporally(">", beforeTime))
Expect(actualTime).To(BeTemporally("<=", afterTime))
```

## Error Testing

Prefer matchers that document intent over manual `err != nil` checks.

| Use case | Matcher |
|---|---|
| Function should succeed | `Expect(fn()).To(Succeed())` |
| Function should fail | `Expect(fn()).To(HaveOccurred())` |
| Specific error value | `Expect(err).To(MatchError(target))` |
| Substring in message | `Expect(err).To(MatchError(ContainSubstring("not found")))` |
| Specific error type | `var target *MyErr; Expect(errors.As(err, &target)).To(BeTrue())` |

```go
Context("Validate", func() {
	var err error

	JustBeforeEach(func() {
		err = service.Validate(ctx, input)
	})

	Context("valid input", func() {
		It("returns no error", func() {
			Expect(err).To(Succeed())
		})
	})

	Context("empty value", func() {
		BeforeEach(func() {
			input.Value = ""
		})

		It("returns validation error", func() {
			Expect(err).To(MatchError(ContainSubstring("value cannot be empty")))
		})
	})
})
```

Error-type assertions:

```go
It("returns NotFoundError for missing items", func() {
	_, err := service.Get(ctx, "nonexistent")
	Expect(err).To(MatchError(&NotFoundError{}))
})

It("returns ValidationError for invalid data", func() {
	err := service.Create(ctx, InvalidData{})
	var validationErr *ValidationError
	Expect(errors.As(err, &validationErr)).To(BeTrue())
	Expect(validationErr.Field).To(Equal("name"))
})
```

## Test Organization & Naming

**File naming conventions:**

- Test files: `feature_test.go` (kebab-case: `user-service_test.go`)
- Suite file: `<pkg>_suite_test.go` (e.g. `pkg_suite_test.go`)
- Package: `<pkg>_test` — external test package, separate from implementation

**Test naming pattern** — descriptive hierarchy that reads as a sentence:

```go
var _ = Describe("UserService", func() {
	Context("Create", func() {
		Context("with valid data", func() {
			It("creates user successfully", func() { ... })
		})

		Context("with invalid email", func() {
			It("returns validation error", func() { ... })
		})
	})
})
```

**Directory layout:**

```
pkg/
├── user-service.go
├── user-service_test.go
├── pkg_suite_test.go
└── mocks/
    ├── user-repository.go
    └── email-service.go
```

## Table-Driven Tests

```go
var _ = Describe("UnitConverter", func() {
	var converter UnitConverter

	BeforeEach(func() {
		converter = NewUnitConverter()
	})

	DescribeTable("unit conversions",
		func(from, to string, value, expected float64) {
			result, err := converter.Convert(from, to, value)
			Expect(err).To(Succeed())
			Expect(result).To(BeNumerically("~", expected, 0.001))
		},
		Entry("meters to feet", "m", "ft", 1.0, 3.281),
		Entry("feet to meters", "ft", "m", 3.281, 1.0),
		Entry("celsius to fahrenheit", "C", "F", 0.0, 32.0),
	)
})
```

## Stdlib Preferences

Use `slices.Contains` instead of manual loops — the `slicescontains` linter enforces this:

```go
// BAD — linter will reject
func contains(s []string, v string) bool {
	for _, item := range s {
		if item == v {
			return true
		}
	}
	return false
}

// GOOD
import "slices"
slices.Contains(s, v)
```

## Best Practices

1. **Clear hierarchy** — `Describe` (unit under test) → `Context` (scenario) → `It` (single assertion or tightly coupled set).
2. **Verify both behavior and calls** — assert return value plus mock call count + args for the right side of the contract.
3. **Independent tests** — fresh setup in `BeforeEach`; never share state across `It` blocks via package-level vars.
4. **Comprehensive error paths** — happy path + every distinct failure mode (invalid input, dependency error, timeout) gets its own `Context`.

## Anti-Patterns

1. **Testing implementation details** — assert behavior (return value, observable side effect), not which helper method was called internally.
2. **Large, unfocused `It` blocks** — one `It` per behavior; if a test exercises create + update + delete, split into three `Context`s.
3. **Only happy-path coverage** — every error-returning function needs a failure-path `Context`.
4. **Test data dependencies** — never `var globalTestData TestData` shared across tests. Build fresh data in `BeforeEach`.

## Further Reading

- [Ginkgo v2](https://onsi.github.io/ginkgo/) — BDD test framework reference.
- [Gomega](https://onsi.github.io/gomega/) — matcher reference.
- [Counterfeiter](https://github.com/maxbrunsfeld/counterfeiter) — mock generator.
- [`github.com/bborbe/time`](https://github.com/bborbe/time) — injectable time utilities.
- [`github.com/bborbe/errors`](https://github.com/bborbe/errors) — error wrapping utilities used in test assertions.
