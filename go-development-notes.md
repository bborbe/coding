# Go Development Notes

## Key Implementation Notes

- All operations are context-aware for cancellation and timeouts
- Error handling is a key design principle with multiple strategies
- Code follows standard Go conventions with BSD license headers
- Mock generation is automated via `//counterfeiter:generate` comments
- Uses interface segregation with small, focused interfaces

## Execution Strategies
- `github.com/bborbe/run`
- **Sequential**: Execute functions one after another (`Sequential`)
- **Parallel with different error handling**:
    - `CancelOnFirstFinish`: Cancel remaining on first completion
    - `CancelOnFirstError`: Cancel remaining on first error
    - `All`: Execute all and aggregate errors
    - `Run`: Execute all and return error channel

## Core Types
- `github.com/bborbe/run`
- `Func`: Function type `func(context.Context) error` - the basic unit of execution
- `Runnable`: Interface for objects that can be run with context

## Testing Framework
This project uses **Ginkgo v2** (BDD) with **Gomega** matchers:
- Uses Ginkgo/Gomega for BDD-style testing
- Counterfeiter for mock generation
- All major components have corresponding test files
- Tests run in UTC timezone for consistency
- Mocks generated via `counterfeiter` using `//go:generate` directives
- Test suites are in `*_suite_test.go` files like the following:

```
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
	RunSpecs(t, "Test Suite")
}
```

## Dependencies
- Prometheus metrics support
- Standard Go concurrency primitives (sync, context)

### External Libraries
- `github.com/robfig/cron/v3`: Core cron scheduling engine
- `github.com/golang/glog`: Logging

### Benjamin Borbe's Ecosystem
- `github.com/bborbe/run`: Runnable interface (jobs implement `run.Runnable`)
- `github.com/bborbe/errors`: Error handling utilities
- `github.com/bborbe/service`: Service framework for CLI applications
- `github.com/bborbe/collection`: Available for `Ptr()` utilities
- `github.com/bborbe/time`: Available for time operations (prefer over standard `time`)
- `github.com/bborbe/sentry`: Sentry integration for error reporting
