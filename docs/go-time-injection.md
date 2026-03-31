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

## Anti-Patterns

- `time.Now()` in production → inject `CurrentDateTimeGetter`
- `time.Time` in structs → `libtime.DateTime`
- `NewCurrentDateTime()` in factory → receive from caller
- Counterfeiter mock for time → use real `SetNow()`
- `nowFunc func() time.Time` → `currentDateTimeGetter libtime.CurrentDateTimeGetter`
- nil fallback to `time.Now()` → require getter in constructor
