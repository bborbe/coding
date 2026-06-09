# Go Time Injection

Use `github.com/bborbe/time` for all time operations. Never call `time.Now()` directly.

## Import

```go
import libtime "github.com/bborbe/time"
import libtimetest "github.com/bborbe/time/test"  // tests only
```

## Types — Use Instead of stdlib

| stdlib | libtime |
|--------|---------|
| `time.Time` | `libtime.DateTime` (timestamps), `libtime.Date` (date-only) |
| `time.Duration` | `libtime.Duration` (supports weeks/days) |

Convert: `time.Time(dateTime)` / `libtime.DateTime(stdTime)`

## Creation — Once in main.go

```go
currentDateTime := libtime.NewCurrentDateTime()
service := pkg.NewService(currentDateTime)
```

Never create inside factory/service — always receive as parameter.

## Constructor — Accept CurrentDateTimeGetter

```go
func NewService(
    currentDateTimeGetter libtime.CurrentDateTimeGetter,
) Service {
    return &service{currentDateTimeGetter: currentDateTimeGetter}
}

type service struct {
    currentDateTimeGetter libtime.CurrentDateTimeGetter
}

func (s *service) Process(ctx context.Context) {
    now := s.currentDateTimeGetter.Now() // returns libtime.DateTime
}
```

## Domain Objects — Use DateTime

```go
type Order struct {
    Created  libtime.DateTime  `json:"created"`
    Modified libtime.DateTime  `json:"modified"`
    Timeout  libtime.Duration  `json:"timeout"`
}
```

## Testing — SetNow, Never Mock

```go
var currentDateTime libtime.CurrentDateTime

BeforeEach(func() {
    currentDateTime = libtime.NewCurrentDateTime()
    currentDateTime.SetNow(libtimetest.ParseDateTime("2023-12-25T10:00:00Z"))
    service = NewService(currentDateTime)
})
```

Test helpers (panic on error — tests only):
- `libtimetest.ParseDateTime("2023-12-25T15:30:00Z")`
- `libtimetest.ParseDate("2023-12-25")`
- `libtimetest.ParseDuration("1h30m")`

## Parsing in Production

```go
dt, err := libtime.ParseDateTime(ctx, "2023-12-25T15:30:00Z")
dur, err := libtime.ParseDuration(ctx, "1w2d3h")
```

## Duration Constants

```go
libtime.Day   // 24h
libtime.Week  // 7d
```

## Testing `NOW`/`NOW-7d` Parsing — Package-Level `libtime.Now`

`libtime.ParseTime` / `libtime.ParseDate` resolve relative expressions like `NOW`, `NOW-7d`, `NOW+1h` by calling the **package-level** `libtime.Now` variable — NOT an injected `CurrentDateTimeGetter`.

If your production code uses `ParseTime("NOW-7d")` and you need deterministic tests, monkey-patch the package var:

```go
import libtime "github.com/bborbe/time"

var _ = Describe("parses NOW-7d", func() {
    var originalNow func() time.Time

    BeforeEach(func() {
        originalNow = libtime.Now
        libtime.Now = func() time.Time {
            return time.Date(2026, 4, 14, 12, 0, 0, 0, time.UTC)
        }
    })

    AfterEach(func() {
        libtime.Now = originalNow  // restore — other tests depend on real clock
    })

    It("resolves NOW-7d to 2026-04-07", func() {
        d, err := libtime.ParseDate(ctx, "NOW-7d")
        Expect(err).NotTo(HaveOccurred())
        Expect(d.Format("2006-01-02")).To(Equal("2026-04-07"))
    })
})
```

Why this is separate from `CurrentDateTimeGetter`:
- `CurrentDateTimeGetter` is a dependency you inject into your own structs — your code calls `getter.Now()`.
- `libtime.Now` is a library-internal free function used by the parser — you don't control the call site.

Always `defer`-restore the original — parallel tests or subsequent specs will break if you leave the patched value.

## Anti-Patterns

- `time.Now()` in production → inject `CurrentDateTimeGetter`
- `time.Time` in structs → `libtime.DateTime`
- `NewCurrentDateTime()` in factory → receive from caller
- Counterfeiter mock for time → use real `SetNow()`
- `nowFunc func() time.Time` → `currentDateTimeGetter libtime.CurrentDateTimeGetter`
- nil fallback to `time.Now()` → require getter in constructor

### RULE go-time/no-time-now-direct (MUST)

**Owner**: go-time-assistant
**Applies when**: any `*.go` file outside `main.go`, `*_test.go`, `vendor/` calls `time.Now()` directly.
**Enforcement**: `rules/go/no-time-now-direct.yml`
**Why**: `time.Now()` is non-deterministic and untestable; production code must inject a `libtime.CurrentDateTimeGetter` and tests must use `libtime.SetNow()`.

#### Bad

```go
func (s *service) Process(ctx context.Context) {
    now := time.Now()
    // ...
}
```

#### Good

```go
func (s *service) Process(ctx context.Context) {
    now := s.currentDateTimeGetter.Now()
    // ...
}
```

### RULE go-time/no-time-time-in-fields (MUST)

**Owner**: go-time-assistant
**Applies when**: any Go struct field is declared with stdlib type `time.Time` or `time.Duration`.
**Enforcement**: `rules/go/no-time-time-in-fields.yml`
**Why**: `libtime.DateTime` and `libtime.Duration` carry marshalling and timezone discipline; stdlib types lose both at the type boundary.

#### Bad

```go
type Order struct {
    Created  time.Time
    Timeout  time.Duration
}
```

#### Good

```go
type Order struct {
    Created  libtime.DateTime
    Timeout  libtime.Duration
}
```

### RULE go-time/inject-getter-not-create (MUST)

**Owner**: go-time-assistant
**Applies when**: a factory or constructor file outside `main.go` calls `libtime.NewCurrentDateTime()`.
**Enforcement**: judgment
**Trigger**: **/*.go
**Why**: factories must be pure composition; creating `libtime.CurrentDateTime` inside a factory hardcodes the clock and breaks the test-time `SetNow` override. ast-grep cannot reliably distinguish a factory call site from a test fixture — whole-function context is required.

#### Bad

```go
func NewService() Service {
    currentDateTime := libtime.NewCurrentDateTime()
    return &service{currentDateTimeGetter: currentDateTime}
}
```

#### Good

```go
func NewService(currentDateTimeGetter libtime.CurrentDateTimeGetter) Service {
    return &service{currentDateTimeGetter: currentDateTimeGetter}
}
```
