# Go Prometheus Metrics Guide

Rules-only version. Captures the enforceable Prometheus conventions for Go services — the patterns that `coding:go-metrics-assistant` checks during `/coding:pr-review`. For deeper background (push gateway internals, alerting playbooks, full real-world example), consult the official Prometheus documentation linked at the end of this file.

## Framework Overview

Built on `prometheus/client_golang`. Two collection strategies:

- **Pull-based (services)**: long-running services expose `/metrics`; Prometheus scrapes.
- **Push-based (jobs/cronjobs)**: short-lived processes push to a push gateway; Prometheus scrapes the gateway.

Key principles:

- Use the appropriate metric type (Counter, Gauge, Histogram, Summary).
- Keep label cardinality bounded.
- Register metrics once during initialization.
- Use interfaces for testability.
- Pre-initialize counters with `.Add(0)` so absent series don't silently break alerts.

### RULE go-prometheus/counter-pre-initialization (MUST)

**Owner**: go-metrics-assistant
**Applies when**: a CounterVec is registered for a label set whose value domain is small, bounded, and known at compile time (typically < 20 combinations — enum, fixed slice of strings, etc.). For large or unbounded domains, prefer `absent()` checks in alerting rules instead.
**Enforcement**: judgment
**Why**: Without pre-initialization, `rate(metric[5m])` returns *no data* (not zero) for unseen label combos. Alert expressions like `rate(errors_total[5m]) > 0.1` silently skip absent series instead of evaluating to false — so the alert never fires when the system is fine *and never fires when the system is broken either*. `absent()` checks don't save you because the series literally doesn't exist yet.

#### Bad

```go
func init() {
	prometheus.MustRegister(requestErrorTotal)
	// No pre-init — "timeout" / "validation" / "internal" series don't exist
	// until the first error of each type occurs. `absent(requestErrorTotal{reason="timeout"})`
	// fires forever; `rate(requestErrorTotal[5m]) > 0.1` never fires.
}
```

#### Good

```go
func init() {
	prometheus.MustRegister(requestErrorTotal)

	// Pre-initialize all known label combinations to 0
	for _, reason := range []string{"timeout", "validation", "internal"} {
		requestErrorTotal.With(prometheus.Labels{
			"reason": reason,
		}).Add(0)
	}
}
```

### RULE go-prometheus/composed-metrics-interface (SHOULD)

**Owner**: go-metrics-assistant
**Applies when**: a single `Metrics` interface aggregates methods spanning two or more distinct functional domains (handlers + senders + schedulers + …), forcing consumers to depend on methods they don't use.
**Enforcement**: judgment
**Why**: Interface Segregation Principle. Components that only send notifications should depend on `MetricsNotificationSender`, not the full `Metrics` interface. Narrow interfaces produce smaller Counterfeiter mocks, clearer test setup, and make accidental coupling visible at the type signature.

#### Bad

```go
// One fat interface — every consumer pulls every method
type Metrics interface {
	OrderHandleTotalCounterInc(tenant core.TenantID, product core.ProductID)
	OrderHandleFailureCounterInc(tenant core.TenantID, product core.ProductID)
	OrderHandleSuccessCounterInc(tenant core.TenantID, product core.ProductID)
	NotificationSendTotalCounterInc(tenant core.TenantID, product core.ProductID, channel core.ChannelID)
	NotificationSendFailureCounterInc(tenant core.TenantID, product core.ProductID, channel core.ChannelID)
}
```

#### Good

```go
//counterfeiter:generate -o ../mocks/api-metrics.go --fake-name ApiMetrics . Metrics
type Metrics interface {
	MetricsOrderHandler
	MetricsNotificationSender
}

type MetricsOrderHandler interface {
	OrderHandleTotalCounterInc(tenant core.TenantID, product core.ProductID)
	OrderHandleFailureCounterInc(tenant core.TenantID, product core.ProductID)
	OrderHandleSuccessCounterInc(tenant core.TenantID, product core.ProductID)
}

type MetricsNotificationSender interface {
	NotificationSendTotalCounterInc(tenant core.TenantID, product core.ProductID, channel core.ChannelID)
	NotificationSendFailureCounterInc(tenant core.TenantID, product core.ProductID, channel core.ChannelID)
}
```

## Metric Types & Design

### Choosing the Right Type

| Question | Yes → | No → |
|---|---|---|
| Can the value decrease? | Gauge | Counter |
| Does it only `.Inc()`? | Counter | — |
| Need distribution / percentiles? | Histogram | — |
| Need exact quantiles, can't define buckets? | Summary | Histogram |

### RULE go-prometheus/no-gauge-for-monotonic (MUST)

**Owner**: go-metrics-assistant
**Applies when**: a `prometheus.NewGaugeVec` / `prometheus.NewGauge` registers a metric the code only ever increments (only `.Inc()` / `.Add(positive)` call sites, never `.Set()` / `.Dec()` / `.Sub()`).
**Enforcement**: judgment
**Why**: `rate()` and `increase()` are type-agnostic — they interpret *any* downward movement in the sample series as a counter reset and adjust accordingly. With a Gauge, a legitimate decrease (e.g. queue drains) is treated as a reset, producing nonsense rates. With a Counter, the type signals that the value can only increase, so PromQL's reset detection is sound. Dashboards built on a Gauge-used-as-counter silently produce wrong numbers.

#### Bad

```go
// Gauge for counter-like metric — rate() and increase() return nonsense
orderHandleTotalCounter = prometheus.NewGaugeVec(prometheus.GaugeOpts{
	Name: "order_handle_total",
}, []string{"tenant"})
```

#### Good

```go
// Counter for values that only increase
orderHandleTotalCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "order_handle_total",
}, []string{"tenant"})
```

### Counter — Monotonically Increasing

Use for events, requests, errors, completed operations.

```go
httpRequestsCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Namespace: "app",
	Subsystem: "http",
	Name:      "requests_total",
	Help:      "Total number of HTTP requests",
}, []string{"method", "endpoint", "status"})
```

### Gauge — Current State

Use for current connections, queue sizes, temperatures, memory usage.

```go
queueSizeGauge = prometheus.NewGaugeVec(prometheus.GaugeOpts{
	Namespace: "app",
	Subsystem: "queue",
	Name:      "size",
	Help:      "Current number of items in queue",
}, []string{"queue_name"})
```

### Histogram — Distribution

Use for request durations, response sizes, batch sizes.

```go
requestDurationHistogram = prometheus.NewHistogramVec(prometheus.HistogramOpts{
	Namespace: "app",
	Subsystem: "http",
	Name:      "request_duration_seconds",
	Help:      "HTTP request duration in seconds",
	Buckets:   []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
}, []string{"method", "endpoint"})
```

### Summary — Quantiles Over Time

Use when you need specific quantiles but can't predict bucket boundaries.

```go
responseSizeSummary = prometheus.NewSummaryVec(prometheus.SummaryOpts{
	Namespace:  "app",
	Subsystem:  "http",
	Name:       "response_size_bytes",
	Help:       "HTTP response size in bytes",
	Objectives: map[float64]float64{0.5: 0.05, 0.9: 0.01, 0.99: 0.001},
}, []string{"endpoint"})
```

## Naming & Labeling Best Practices

### Metric Naming Conventions

**Standard format:** `{namespace}_{subsystem}_{metric_name}_{unit}`

```go
httpRequestsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
	Namespace: "app",            // Application identifier
	Subsystem: "http",           // Component/subsystem
	Name:      "requests_total", // What is being measured + _total for counters
	Help:      "Total number of HTTP requests processed",
}, []string{"method", "status"})
```

Guidelines:

- Use `snake_case` for metric names.
- Include units in the name (`_seconds`, `_bytes`, `_total`).
- Be descriptive but concise.
- Use consistent namespace/subsystem across related metrics.

### RULE go-prometheus/counter-total-suffix (MUST)

**Owner**: go-metrics-assistant
**Applies when**: a `prometheus.CounterOpts` struct literal sets a `Name:` field whose string value does not end with `_total`.
**Enforcement**: judgment (ast-grep follow-up)
**Why**: Prometheus naming convention; newer `client_golang` versions enforce this at registration time (panic). Counters without `_total` also fail the OpenMetrics spec and confuse Grafana auto-completion.

#### Bad

```go
prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "requests_processed", // missing _total
	Help: "...",
}, []string{"method"})
```

#### Good

```go
prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "requests_processed_total",
	Help: "...",
}, []string{"method"})
```

### RULE go-prometheus/help-string-quality (MUST)

**Owner**: go-metrics-assistant
**Applies when**: any `prometheus.{Counter,Gauge,Histogram,Summary}Opts` struct literal sets a `Help:` field that (a) is empty, (b) duplicates another metric's Help verbatim, or (c) describes a different metric (copy-paste residue).
**Enforcement**: judgment
**Why**: Help strings appear in `/metrics` output and the Grafana metric explorer. Wrong descriptions cause real confusion during incidents — the on-call sees a Help string that contradicts the metric name, can't tell which is wrong, and burns minutes verifying. Empty Help strings make alert ownership ambiguous.

#### Bad

```go
// Empty Help — useless in /metrics and Grafana
emptyHelpCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "requests_total",
	Help: "",
}, []string{"method"})

// Duplicate Help across two distinct metrics — collapses to one entry in the explorer
orderHandleTotalCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "order_handle_total",
	Help: "Total number of operations",
}, []string{"tenant"})
notificationSendTotalCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "notification_send_total",
	Help: "Total number of operations", // identical Help, different metric
}, []string{"tenant"})

// Copy-paste residue — Help describes the wrong metric
notificationSendSuccessCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "success_total",
	Help: "Order Handle Total Counter", // Wrong! This is the notification sender
})
```

#### Good

```go
notificationSendSuccessCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "success_total",
	Help: "Total number of successfully sent notifications",
})
```

### RULE go-prometheus/label-naming-consistency (MUST)

**Owner**: go-metrics-assistant
**Applies when**: two or more metrics in the same project reference the same conceptual entity using different label names (e.g. `product` vs `item` for product ID; `tenant` vs `customer` vs `org`).
**Enforcement**: judgment
**Why**: Inconsistent label names silently break PromQL joins (`on(product)` only joins series that share the label) and Grafana dashboards (variable interpolation can't unify across panels). The cost shows up at 3am when a dashboard is half-empty and no one knows why.

#### Bad

```go
orderHandleCounter.With(prometheus.Labels{"product": product.String()})
notificationSendCounter.With(prometheus.Labels{"item": product.String()}) // same concept, different label
```

#### Good

```go
orderHandleCounter.With(prometheus.Labels{"product": product.String()})
notificationSendCounter.With(prometheus.Labels{"product": product.String()})
```

Define label-name constants to enforce consistency at compile time:

```go
const (
	labelTenant  = "tenant"
	labelProduct = "product"
	labelChannel = "channel"
)
```

### Cardinality Management

Keep label combinations bounded.

```go
// Good: low cardinality
httpRequestsCounter.With(prometheus.Labels{
	"method":   "GET",        // Limited set
	"endpoint": "/api/users", // Grouped, not per-ID
	"status":   "200",        // HTTP status codes
}).Inc()

// Bad: high cardinality (millions of unique series)
httpRequestsCounter.With(prometheus.Labels{
	"user_id":    "12345",         // Unique per user
	"request_id": "req-abc-123",   // Unique per request
	"ip_address": "192.168.1.1",   // IPs
}).Inc()
```

Group related endpoints:

```go
func getEndpointGroup(path string) string {
	switch {
	case strings.HasPrefix(path, "/api/users"):
		return "users"
	case strings.HasPrefix(path, "/api/orders"):
		return "orders"
	case strings.HasPrefix(path, "/health"):
		return "health"
	default:
		return "other"
	}
}
```

## Best Practices

### 1. Use Interfaces for Testability

```go
type Metrics interface {
	RecordEvent(eventType string)
}

func NewService(metrics Metrics) Service { ... }
```

### 2. Fail Fast with MustRegister

```go
func init() {
	prometheus.MustRegister(requestsCounter)
}
```

### 3. Group Related Metrics

```go
var (
	userRegistrationsTotal = prometheus.NewCounter(...)
	userLoginAttemptsTotal = prometheus.NewCounter(...)
	userActiveGauge        = prometheus.NewGauge(...)
)
```

### 4. Handle Errors Gracefully in Push Gateway

```go
defer func() {
	if err := pusher.Push(ctx); err != nil {
		log.Printf("metrics push failed (non-fatal): %v", err)
	}
}()
```

## Anti-Patterns

### 1. High Cardinality Labels

```go
// BAD: user_id creates high cardinality
requestsCounter.With(prometheus.Labels{
	"user_id": userID, // Could be millions of unique values
}).Inc()

// GOOD: Use user type/category instead
requestsCounter.With(prometheus.Labels{
	"user_type": getUserType(user), // Limited set: premium, basic, admin
}).Inc()
```

### 2. Using Metrics for Debugging

```go
// BAD: Metrics are not for debugging info
debugInfo.With(prometheus.Labels{
	"function":  "processOrder",
	"line":      "123",
	"timestamp": time.Now().String(),
}).Set(1)

// GOOD: Use proper logging
log.Printf("processing order at line 123")
```

### 3. Inconsistent Naming

```go
// BAD
var (
	userCount     = prometheus.NewGauge(...)     // Missing namespace
	httpRequests  = prometheus.NewCounter(...)   // Different style
	response_time = prometheus.NewHistogram(...) // snake_case vs camelCase
)

// GOOD
var (
	appUserActiveTotal         = prometheus.NewGauge(...)
	appHTTPRequestsTotal       = prometheus.NewCounter(...)
	appHTTPResponseTimeSeconds = prometheus.NewHistogram(...)
)
```

### 4. Metrics in Hot Paths Without Consideration

```go
// BAD: Expensive operations in hot path
func processItem(item Item) {
	start := time.Now()
	category := computeComplexCategory(item) // Expensive
	region := getRegionFromIP(item.IP)       // Network call
	processedItemsCounter.With(prometheus.Labels{
		"category": category,
		"region":   region,
	}).Inc()
	processItemsHistogram.Observe(time.Since(start).Seconds())
}

// GOOD: Pre-compute expensive labels
func processItem(item Item) {
	start := time.Now()
	processedItemsCounter.With(prometheus.Labels{
		"category": item.PrecomputedCategory,
	}).Inc()
	processItemsHistogram.Observe(time.Since(start).Seconds())
}
```

## Further Reading

- [prometheus/client_golang](https://github.com/prometheus/client_golang) — official Go client.
- [Prometheus naming conventions](https://prometheus.io/docs/practices/naming/).
- [Prometheus instrumentation best practices](https://prometheus.io/docs/practices/instrumentation/).
- [Prometheus histograms and summaries](https://prometheus.io/docs/practices/histograms/).
