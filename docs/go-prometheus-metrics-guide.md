# Go Prometheus Metrics Guide

Rules-only version. For full architecture, push gateway internals, testing/alerting/perf playbooks, and the real-world example, see the comprehensive reference in Obsidian Knowledge Base (`Go Prometheus Metrics Reference`).

This guide captures the enforceable conventions for Prometheus metrics in bborbe Go services — the patterns that `coding:go-metrics-assistant` checks during `/coding:pr-review`.

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

## Counter Pre-Initialization Pattern

**MUST pre-initialize counters with `.Add(0)` for all known label combinations.** This ensures metrics exist in Prometheus even when no events have occurred, preventing `absent()` alert false negatives.

```go
func init() {
	prometheus.MustRegister(
		requestErrorTotal,
	)

	// Pre-initialize all known label combinations to 0
	for _, reason := range []string{"timeout", "validation", "internal"} {
		requestErrorTotal.With(prometheus.Labels{
			"reason": reason,
		}).Add(0)
	}
}
```

**Why:** Without pre-initialization, `rate(metric[5m])` returns no data (not zero) for unseen label combos. Alert expressions like `rate(errors_total[5m]) > 0.1` silently skip absent series instead of evaluating to false.

## Composed Metrics Interface Pattern

**MUST split large Metrics interfaces into focused sub-interfaces when a service has distinct metric domains.** Compose them into a single Metrics interface for the factory.

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

**Why:** Components that only send notifications should depend on `MetricsNotificationSender`, not the full `Metrics` interface. Follows Interface Segregation Principle.

## Metric Types & Design

### Choosing the Right Type

| Question | Yes → | No → |
|---|---|---|
| Can the value decrease? | Gauge | Counter |
| Does it only `.Inc()`? | Counter | — |
| Need distribution / percentiles? | Histogram | — |
| Need exact quantiles, can't define buckets? | Summary | Histogram |

**MUST NOT use GaugeVec for values that only increase.** If a metric only calls `.Inc()`, it MUST be a `CounterVec`. Using Gauge for monotonically increasing values breaks `rate()` and `increase()` queries.

```go
// BAD: Gauge for counter-like metric
candleHandleTotalCounter = prometheus.NewGaugeVec(prometheus.GaugeOpts{
	Name: "total_counter",
}, []string{"broker"})

// GOOD: Counter for values that only increase
candleHandleTotalCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "total",
}, []string{"broker"})
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

### Counter `_total` Suffix Rule

**MUST end counter metric names with `_total`.** Prometheus naming convention enforced by newer client versions.

```go
// BAD
Name: "requests_processed",
Name: "errors_count",

// GOOD
Name: "requests_processed_total",
Name: "errors_total",
```

### Help String Quality Rule

**MUST write unique, accurate Help strings for every metric.** Never copy-paste Help from another metric. Help strings appear in `/metrics` output and Grafana metric explorer — wrong descriptions cause confusion during incidents.

```go
// BAD: Copy-pasted Help
signalSendSuccessCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "success_total",
	Help: "Candle Handle Total Counter", // Wrong! This is signal sender
})

// GOOD
signalSendSuccessCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "success_total",
	Help: "Total number of successfully sent signals",
})
```

### Label Naming Consistency

**MUST use the same label name for the same concept across all metrics in a project.** Inconsistent label names break dashboards and PromQL joins.

```go
// BAD
orderHandleCounter.With(prometheus.Labels{"product": product.String()})
notificationSendCounter.With(prometheus.Labels{"item": product.String()})

// GOOD
orderHandleCounter.With(prometheus.Labels{"product": product.String()})
notificationSendCounter.With(prometheus.Labels{"product": product.String()})
```

Define label-name constants to enforce consistency:

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

- Comprehensive reference (full architecture, push gateway, alerting playbooks, real-world example): `Personal/50 Knowledge Base/Go Prometheus Metrics Reference.md` in the Obsidian vault.
- [prometheus/client_golang](https://github.com/prometheus/client_golang) — official Go client.
- [Prometheus naming conventions](https://prometheus.io/docs/practices/naming/).
