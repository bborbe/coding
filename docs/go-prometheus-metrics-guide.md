# Go Prometheus Metrics Guide

This comprehensive guide covers Prometheus metrics implementation patterns and best practices for building observable Go applications. The framework is built on **prometheus/client_golang** with patterns for both push gateway (jobs/cronjobs) and pull-based (services) metrics collection.

## Table of Contents

1. [Framework Overview](#framework-overview)
2. [Metrics Architecture Patterns](#metrics-architecture-patterns)
3. [Push Gateway Implementation](#push-gateway-implementation)
   - [Custom Registry Pattern for Job Isolation](#custom-registry-pattern-for-job-isolation)
4. [Metric Types & Design](#metric-types--design)
5. [Interface Patterns](#interface-patterns)
6. [Naming & Labeling Best Practices](#naming--labeling-best-practices)
7. [Handler Integration](#handler-integration)
8. [Testing Strategies](#testing-strategies)
   - [Testing Custom Registry Pattern](#testing-custom-registry-pattern)
9. [Alerting Patterns](#alerting-patterns)
10. [Performance Considerations](#performance-considerations)
11. [Best Practices & Anti-patterns](#best-practices--anti-patterns)

## Framework Overview

### Core Technologies
- **[prometheus/client_golang](https://github.com/prometheus/client_golang)**: Official Prometheus client library
- **[prometheus/pushgateway](https://prometheus.io/docs/instrumenting/pushing/)**: Push gateway for batch jobs and short-lived processes
- **Prometheus Server**: Time-series database and metrics collection system
- **Grafana**: Visualization and dashboards (optional but recommended)

### Key Principles
- **Metric Types**: Use appropriate metric types (Counter, Gauge, Histogram, Summary)
- **Label Design**: Efficient labeling without creating high cardinality
- **Registration**: Register metrics once during initialization
- **Interface Abstraction**: Use interfaces for testability and modularity
- **Performance**: Minimize collection overhead and memory usage

### Collection Strategies

**Pull-Based (Services):**
- Long-running services expose `/metrics` endpoint
- Prometheus server scrapes metrics at regular intervals
- Better for persistent applications

**Push-Based (Jobs/Cronjobs):**
- Short-lived processes push metrics to Push Gateway
- Prometheus scrapes metrics from Push Gateway
- Better for batch jobs and cronjobs

## Metrics Architecture Patterns

### Interface-Based Metrics Design

**Always Use Public Interface + Private Implementation:**

```go
//counterfeiter:generate -o ../mocks/metrics.go --fake-name Metrics . Metrics
type Metrics interface {
	UserCreated(userType string)
	UserLoginAttempt(userType string, success bool)
	RequestDuration(endpoint string, duration time.Duration)
	ActiveConnections(count int)
}

type metrics struct{}

func NewMetrics() Metrics {
	return &metrics{}
}

func (m *metrics) UserCreated(userType string) {
	userCreatedCounter.With(prometheus.Labels{
		"type": userType,
	}).Inc()
}

func (m *metrics) UserLoginAttempt(userType string, success bool) {
	userLoginAttemptsCounter.With(prometheus.Labels{
		"type":    userType,
		"success": strconv.FormatBool(success),
	}).Inc()
}

func (m *metrics) RequestDuration(endpoint string, duration time.Duration) {
	requestDurationHistogram.With(prometheus.Labels{
		"endpoint": endpoint,
	}).Observe(duration.Seconds())
}

func (m *metrics) ActiveConnections(count int) {
	activeConnectionsGauge.Set(float64(count))
}
```

### Metric Registration Pattern

**Register Metrics in init() Function:**

```go
var (
	userCreatedCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "app",
		Subsystem: "user",
		Name:      "created_total",
		Help:      "Total number of users created",
	}, []string{"type"})

	userLoginAttemptsCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "app",
		Subsystem: "user",
		Name:      "login_attempts_total",
		Help:      "Total number of login attempts",
	}, []string{"type", "success"})

	requestDurationHistogram = prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "request_duration_seconds",
		Help:      "HTTP request duration in seconds",
		Buckets:   prometheus.DefBuckets,
	}, []string{"endpoint"})

	activeConnectionsGauge = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "active_connections",
		Help:      "Number of active HTTP connections",
	})
)

func init() {
	prometheus.MustRegister(
		userCreatedCounter,
		userLoginAttemptsCounter,
		requestDurationHistogram,
		activeConnectionsGauge,
	)
}
```

### Counter Pre-Initialization Pattern

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

### Composed Metrics Interface Pattern

**MUST split large Metrics interfaces into focused sub-interfaces when a service has distinct metric domains.** Compose them into a single Metrics interface for the factory.

```go
//counterfeiter:generate -o ../mocks/metrics.go --fake-name Metrics . Metrics
type Metrics interface {
	MetricsCandleHandler
	MetricsSignalSender
}

type MetricsCandleHandler interface {
	CandleHandleTotalCounterInc(broker core.BrokerIdentifier, epic core.Epic)
	CandleHandleFailureCounterInc(broker core.BrokerIdentifier, epic core.Epic)
	CandleHandleSuccessCounterInc(broker core.BrokerIdentifier, epic core.Epic)
}

type MetricsSignalSender interface {
	SignalSendTotalCounterInc(broker core.BrokerIdentifier, epic core.Epic, strategy core.StrategyIdentifier)
	SignalSendFailureCounterInc(broker core.BrokerIdentifier, epic core.Epic, strategy core.StrategyIdentifier)
}
```

**Why:** Components that only send signals should depend on `MetricsSignalSender`, not the full `Metrics` interface. Follows Interface Segregation Principle.

### Service Integration Pattern

**Dependency Injection for Metrics:**

```go
type UserService interface {
	CreateUser(ctx context.Context, user User) error
	LoginUser(ctx context.Context, credentials Credentials) error
}

type userService struct {
	repository UserRepository
	validator  UserValidator
	metrics    Metrics
}

func NewUserService(
	repository UserRepository,
	validator UserValidator,
	metrics Metrics,
) UserService {
	return &userService{
		repository: repository,
		validator:  validator,
		metrics:    metrics,
	}
}

func (s *userService) CreateUser(ctx context.Context, user User) error {
	if err := s.validator.Validate(ctx, user); err != nil {
		return err
	}

	if err := s.repository.Store(ctx, user); err != nil {
		return err
	}

	// Record successful user creation
	s.metrics.UserCreated(user.Type)
	return nil
}

func (s *userService) LoginUser(ctx context.Context, credentials Credentials) error {
	user, err := s.repository.GetByUsername(ctx, credentials.Username)
	if err != nil {
		s.metrics.UserLoginAttempt(credentials.UserType, false)
		return err
	}

	if !s.validator.ValidatePassword(credentials.Password, user.HashedPassword) {
		s.metrics.UserLoginAttempt(credentials.UserType, false)
		return errors.New("invalid credentials")
	}

	s.metrics.UserLoginAttempt(credentials.UserType, true)
	return nil
}
```

## Push Gateway Implementation

### Push Gateway Client

```go
package metrics

import (
	"context"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/push"
)

//counterfeiter:generate -o ../mocks/pusher.go --fake-name Pusher . Pusher
type Pusher interface {
	Push(ctx context.Context) error
}

func NewPusher(gatewayURL, jobName string) Pusher {
	return &pusher{
		pusher: push.New(gatewayURL, jobName).
			Gatherer(prometheus.DefaultGatherer),
	}
}

type pusher struct {
	pusher *push.Pusher
}

func (p *pusher) Push(ctx context.Context) error {
	return p.pusher.PushContext(ctx)
}
```

### Custom Registry Pattern for Job Isolation

**When to Use Custom Registry vs DefaultGatherer:**

Use **Custom Registry** when:
- Running batch jobs/cronjobs that should have isolated metrics
- You want to avoid collecting all default Go runtime metrics
- Multiple jobs run in the same process and need separate metric namespaces
- You need precise control over which metrics are pushed to the gateway

Use **DefaultGatherer** when:
- Running long-lived services that expose `/metrics` endpoint
- You want to include Go runtime metrics (memory, goroutines, etc.)
- Simple push gateway usage without metric isolation requirements

**Custom Registry Implementation:**

```go
package metrics

import (
	"context"
	"strings"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/push"
)

//counterfeiter:generate -o ../mocks/pusher.go --fake-name Pusher . Pusher
// Pusher interface supports both default and custom registries
type Pusher interface {
	Push(ctx context.Context) error
	Collector(registry *prometheus.Registry) Pusher
}

type pusher struct {
	pusher *push.Pusher
}

// NewPusher creates a pusher with DefaultGatherer
func NewPusher(gatewayURL, jobName string) Pusher {
	return &pusher{
		pusher: push.New(gatewayURL, jobName).
			Gatherer(prometheus.DefaultGatherer),
	}
}

// Collector configures the pusher to use a custom registry
func (p *pusher) Collector(registry *prometheus.Registry) Pusher {
	p.pusher = p.pusher.Gatherer(registry)
	return p
}

func (p *pusher) Push(ctx context.Context) error {
	return p.pusher.PushContext(ctx)
}

// BuildName creates dynamic job names for multi-dimensional job identification
func BuildName(parts ...string) string {
	return strings.Join(parts, "_")
}
```

**Registry-Specific Metrics Registration:**

```go
package metrics

import (
	"time"

	"github.com/prometheus/client_golang/prometheus"
	libtime "github.com/bborbe/time"
)

// JobMetrics encapsulates metrics for a specific job with custom registry
type JobMetrics struct {
	registry        *prometheus.Registry
	currentDateTime libtime.CurrentDateTime

	itemsProcessed     *prometheus.CounterVec
	processingDuration *prometheus.HistogramVec
	lastRunTimestamp   prometheus.Gauge
}

// NewJobMetrics creates metrics registered to a custom registry
func NewJobMetrics(registry *prometheus.Registry, currentDateTime libtime.CurrentDateTime) *JobMetrics {
	m := &JobMetrics{
		registry:        registry,
		currentDateTime: currentDateTime,

		itemsProcessed: prometheus.NewCounterVec(prometheus.CounterOpts{
			Namespace: "job",
			Subsystem: "processing",
			Name:      "items_total",
			Help:      "Total number of items processed",
		}, []string{"status"}),

		processingDuration: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Namespace: "job",
			Subsystem: "processing",
			Name:      "duration_seconds",
			Help:      "Processing duration in seconds",
			Buckets:   []float64{0.1, 0.5, 1, 2, 5, 10, 30, 60},
		}, []string{"operation"}),

		lastRunTimestamp: prometheus.NewGauge(prometheus.GaugeOpts{
			Namespace: "job",
			Name:      "last_run_timestamp_seconds",
			Help:      "Timestamp of last job run",
		}),
	}

	// Register all metrics to the custom registry
	registry.MustRegister(
		m.itemsProcessed,
		m.processingDuration,
		m.lastRunTimestamp,
	)

	return m
}

func (m *JobMetrics) RecordItemProcessed(ctx context.Context, status string) {
	m.itemsProcessed.With(prometheus.Labels{
		"status": status,
	}).Inc()
}

func (m *JobMetrics) RecordOperationDuration(ctx context.Context, operation string, duration time.Duration) {
	m.processingDuration.With(prometheus.Labels{
		"operation": operation,
	}).Observe(duration.Seconds())
}

func (m *JobMetrics) RecordJobRun(ctx context.Context) {
	m.lastRunTimestamp.Set(float64(m.currentDateTime.Now().Unix()))
}
```

**Complete Job Implementation with Custom Registry:**

```go
package main

import (
	"context"
	"log"
	"time"

	"github.com/bborbe/errors"
	"github.com/golang/glog"
	"github.com/prometheus/client_golang/prometheus"
	libtime "github.com/bborbe/time"
)

type CommandJob struct {
	serviceName      string
	schemaID         string
	commandOperation string
	currentDateTime  libtime.CurrentDateTime
	metrics          *JobMetrics
}

func NewCommandJob(serviceName, schemaID, commandOperation string, currentDateTime libtime.CurrentDateTime) *CommandJob {
	return &CommandJob{
		serviceName:      serviceName,
		schemaID:         schemaID,
		commandOperation: commandOperation,
		currentDateTime:  currentDateTime,
	}
}

func (a *CommandJob) Run(ctx context.Context) error {
	// Create isolated registry for this job
	registry := prometheus.NewRegistry()

	// Create metrics with custom registry
	a.metrics = NewJobMetrics(registry, a.currentDateTime)

	// Build dynamic job name from job dimensions
	jobName := metrics.BuildName(a.serviceName, a.schemaID, a.commandOperation)

	// Create pusher with custom registry
	pusher := metrics.NewPusher(
		"http://pushgateway.monitoring:9090",
		jobName,
	).Collector(registry)

	// Push metrics on completion (success or failure)
	defer func() {
		if err := pusher.Push(ctx); err != nil {
			glog.Warningf("prometheus push with job(%s) failed: %v", jobName, err)
			return
		}
		glog.V(2).Infof("prometheus push with job(%s) completed", jobName)
	}()

	// Record job execution
	a.metrics.RecordJobRun(ctx)

	// Execute job logic
	if err := a.executeCommand(ctx); err != nil {
		a.metrics.RecordItemProcessed(ctx, "error")
		return errors.Wrapf(ctx, err, "execute command %s for schema %s", a.commandOperation, a.schemaID)
	}

	a.metrics.RecordItemProcessed(ctx, "success")
	return nil
}

func (a *CommandJob) executeCommand(ctx context.Context) error {
	start := time.Now()
	defer func() {
		a.metrics.RecordOperationDuration(ctx, a.commandOperation, time.Since(start))
	}()

	// Your command logic here
	glog.V(2).Infof("executing command: %s for schema: %s", a.commandOperation, a.schemaID)

	// Simulate work
	time.Sleep(100 * time.Millisecond)

	return nil
}

func main() {
	// Create dependencies
	currentDateTime := libtime.NewCurrentDateTime()

	job := NewCommandJob("order-service", "order-schema-v1", "process-orders", currentDateTime)

	ctx := context.Background()
	if err := job.Run(ctx); err != nil {
		log.Fatalf("job failed: %v", err)
	}

	log.Println("job completed successfully")
}
```

**Dynamic Job Naming Patterns:**

```go
// Pattern 1: Service + Operation
jobName := metrics.BuildName(serviceName, operation)
// Example: "user-service_create-user"

// Pattern 2: Service + Schema + Operation (multi-tenant)
jobName := metrics.BuildName(serviceName, schemaID, operation)
// Example: "order-service_order-schema-v1_process-orders"

// Pattern 3: Environment + Service + Operation
jobName := metrics.BuildName(environment, serviceName, operation)
// Example: "production_order-service_process-orders"

// Pattern 4: Full dimensional naming
jobName := metrics.BuildName(environment, region, serviceName, schemaID, operation)
// Example: "production_us-east-1_order-service_order-schema-v1_process-orders"
```

**Key Benefits of Custom Registry Pattern:**

1. **Metric Isolation**: Each job has its own metric namespace
2. **Clean Pushes**: Only job-specific metrics are pushed (no Go runtime metrics)
3. **Multi-Job Support**: Multiple jobs can run in same process without metric conflicts
4. **Precise Control**: Explicit control over which metrics are collected and pushed
5. **Dynamic Naming**: Job names can include operational dimensions for better organization

### Job/Cronjob Usage Pattern

```go
func main() {
	// Create metrics pusher
	pusher := metrics.NewPusher("http://pushgateway:9091", "batch-job")

	// Setup defer to push metrics on completion
	defer func() {
		if err := pusher.Push(context.Background()); err != nil {
			log.Printf("prometheus push failed: %v", err)
		}
		log.Printf("prometheus push completed")
	}()

	// Your job logic here
	if err := runBatchJob(); err != nil {
		log.Fatalf("batch job failed: %v", err)
	}
}

func runBatchJob() error {
	// Job implementation with metrics collection
	metrics := metrics.NewMetrics()

	// Process items and record metrics
	for _, item := range items {
		if err := processItem(item); err != nil {
			metrics.ItemProcessed("error")
			return err
		}
		metrics.ItemProcessed("success")
	}

	return nil
}
```

### Advanced Push Gateway Configuration

```go
type PusherConfig struct {
	GatewayURL string
	JobName    string
	Instance   string
	Grouping   map[string]string
}

func NewAdvancedPusher(config PusherConfig) Pusher {
	pusher := push.New(config.GatewayURL, config.JobName)

	if config.Instance != "" {
		pusher = pusher.Instance(config.Instance)
	}

	for key, value := range config.Grouping {
		pusher = pusher.Grouping(key, value)
	}

	return &pusher{
		pusher: pusher.Gatherer(prometheus.DefaultGatherer),
	}
}
```

## Metric Types & Design

### Choosing the Right Type

**Decision Rule:**

| Question | Yes → | No → |
|----------|-------|------|
| Can the value decrease? | Gauge | Counter |
| Does it only `.Inc()`? | Counter | — |
| Need distribution/percentiles? | Histogram | — |
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

### Counter - Monotonically Increasing Values

**Use For:** Events, requests, errors, completed operations

```go
var (
	httpRequestsCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "requests_total",
		Help:      "Total number of HTTP requests",
	}, []string{"method", "endpoint", "status"})
)

func (m *metrics) HTTPRequestCompleted(method, endpoint string, statusCode int) {
	httpRequestsCounter.With(prometheus.Labels{
		"method":   method,
		"endpoint": endpoint,
		"status":   strconv.Itoa(statusCode),
	}).Inc()
}
```

### Gauge - Current State Values

**Use For:** Current connections, queue sizes, temperatures, memory usage

```go
var (
	queueSizeGauge = prometheus.NewGaugeVec(prometheus.GaugeOpts{
		Namespace: "app",
		Subsystem: "queue",
		Name:      "size",
		Help:      "Current number of items in queue",
	}, []string{"queue_name"})
)

func (m *metrics) QueueSizeChanged(queueName string, size int) {
	queueSizeGauge.With(prometheus.Labels{
		"queue_name": queueName,
	}).Set(float64(size))
}

// For values that can increase or decrease
func (m *metrics) QueueItemAdded(queueName string) {
	queueSizeGauge.With(prometheus.Labels{
		"queue_name": queueName,
	}).Inc()
}

func (m *metrics) QueueItemRemoved(queueName string) {
	queueSizeGauge.With(prometheus.Labels{
		"queue_name": queueName,
	}).Dec()
}
```

### Histogram - Distribution of Values

**Use For:** Request durations, response sizes, batch sizes

```go
var (
	requestDurationHistogram = prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "request_duration_seconds",
		Help:      "HTTP request duration in seconds",
		Buckets:   []float64{0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
	}, []string{"method", "endpoint"})
)

func (m *metrics) HTTPRequestDuration(method, endpoint string, duration time.Duration) {
	requestDurationHistogram.With(prometheus.Labels{
		"method":   method,
		"endpoint": endpoint,
	}).Observe(duration.Seconds())
}
```

### Summary - Quantiles Over Time

**Use For:** When you need specific quantiles but can't predict bucket boundaries

```go
var (
	responseSizeSummary = prometheus.NewSummaryVec(prometheus.SummaryOpts{
		Namespace:  "app",
		Subsystem:  "http",
		Name:       "response_size_bytes",
		Help:       "HTTP response size in bytes",
		Objectives: map[float64]float64{0.5: 0.05, 0.9: 0.01, 0.99: 0.001},
	}, []string{"endpoint"})
)

func (m *metrics) HTTPResponseSize(endpoint string, sizeBytes int) {
	responseSizeSummary.With(prometheus.Labels{
		"endpoint": endpoint,
	}).Observe(float64(sizeBytes))
}
```

## Interface Patterns

### Handler with Metrics Integration

```go
type OrderHandler interface {
	ProcessOrder(ctx context.Context, order Order) error
}

type orderHandler struct {
	processor OrderProcessor
	metrics   Metrics
}

func NewOrderHandler(processor OrderProcessor, metrics Metrics) OrderHandler {
	return &orderHandler{
		processor: processor,
		metrics:   metrics,
	}
}

func (h *orderHandler) ProcessOrder(ctx context.Context, order Order) error {
	start := time.Now()

	err := h.processor.Process(ctx, order)

	// Record processing time
	h.metrics.OrderProcessingDuration(order.Type, time.Since(start))

	if err != nil {
		h.metrics.OrderProcessed(order.Type, "error")
		return err
	}

	h.metrics.OrderProcessed(order.Type, "success")
	return nil
}
```

### Wrapper Pattern for Existing Services

```go
// Wrap existing service with metrics
func NewMetricsWrapper(service UserService, metrics Metrics) UserService {
	return &userServiceMetrics{
		service: service,
		metrics: metrics,
	}
}

type userServiceMetrics struct {
	service UserService
	metrics Metrics
}

func (s *userServiceMetrics) CreateUser(ctx context.Context, user User) error {
	start := time.Now()
	err := s.service.CreateUser(ctx, user)

	s.metrics.OperationDuration("create_user", time.Since(start))

	if err != nil {
		s.metrics.OperationResult("create_user", "error")
	} else {
		s.metrics.OperationResult("create_user", "success")
	}

	return err
}
```

## Naming & Labeling Best Practices

### Metric Naming Conventions

**Standard Format:** `{namespace}_{subsystem}_{metric_name}_{unit}`

```go
//  Good: Clear, descriptive names
var (
	httpRequestsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "app",           // Application identifier
		Subsystem: "http",          // Component/subsystem
		Name:      "requests_total", // What is being measured + _total for counters
		Help:      "Total number of HTTP requests processed",
	}, []string{"method", "status"})

	databaseConnectionsActive = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "app",
		Subsystem: "database",
		Name:      "connections_active",
		Help:      "Number of active database connections",
	})

	requestDurationSeconds = prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "request_duration_seconds", // Include unit in name
		Help:      "HTTP request duration in seconds",
	}, []string{"endpoint"})
)
```

**Naming Guidelines:**
- Use `snake_case` for metric names
- Include units in the name (`_seconds`, `_bytes`, `_total`)
- Be descriptive but concise
- Use consistent namespace/subsystem across related metrics

**Counter `_total` Suffix Rule:**

**MUST end counter metric names with `_total`.** This is a Prometheus naming convention enforced by newer client versions.

```go
// BAD: Missing _total suffix
Name: "requests_processed",
Name: "errors_count",

// GOOD: Counters end with _total
Name: "requests_processed_total",
Name: "errors_total",
```

**Help String Quality Rule:**

**MUST write unique, accurate Help strings for every metric.** Never copy-paste Help from another metric. Help strings appear in `/metrics` output and Grafana metric explorer — wrong descriptions cause confusion during incidents.

```go
// BAD: Copy-pasted Help from another metric
signalSendSuccessCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "success_total",
	Help: "Candle Handle Total Counter",  // Wrong! This is signal sender, not candle handler
})

// GOOD: Describes THIS metric accurately
signalSendSuccessCounter = prometheus.NewCounterVec(prometheus.CounterOpts{
	Name: "success_total",
	Help: "Total number of successfully sent signals",
})
```

### Label Design Best Practices

**Label Naming Consistency Rule:**

**MUST use the same label name for the same concept across all metrics in a project.** Inconsistent label names break dashboards and PromQL joins.

```go
// BAD: Same concept, different label names across metrics
candleHandleCounter.With(prometheus.Labels{"epic": epic.String()})     // uses "epic"
signalSendCounter.With(prometheus.Labels{"symbol": epic.String()})     // uses "symbol"

// GOOD: Pick one label name, use it everywhere
candleHandleCounter.With(prometheus.Labels{"epic": epic.String()})
signalSendCounter.With(prometheus.Labels{"epic": epic.String()})
```

**Tip:** Define label name constants to enforce consistency:
```go
const (
	labelBroker   = "broker"
	labelEpic     = "epic"
	labelStrategy = "strategy"
)
```


** Good Label Design:**

```go
// Low cardinality, meaningful dimensions
httpRequestsCounter.With(prometheus.Labels{
	"method":   "GET",           // Limited set: GET, POST, PUT, DELETE
	"endpoint": "/api/users",    // Grouped endpoints, not individual IDs
	"status":   "200",           // HTTP status codes
}).Inc()
```

**L Bad Label Design (High Cardinality):**

```go
// Avoid: Creates too many unique time series
httpRequestsCounter.With(prometheus.Labels{
	"user_id":     "12345",        // Unique per user - HIGH cardinality
	"request_id":  "req-abc-123",  // Unique per request - VERY HIGH cardinality
	"timestamp":   "2023-12-25",   // Date-based labels - HIGH cardinality
	"ip_address":  "192.168.1.1",  // IP addresses - HIGH cardinality
}).Inc()
```

### Cardinality Management

**Keep Label Combinations Under Control:**

```go
//  Good: Estimate cardinality
// methods(4) * endpoints(~20) * statuses(~10) = ~800 time series
var requestsCounter = prometheus.NewCounterVec(
	prometheus.CounterOpts{...},
	[]string{"method", "endpoint_group", "status"},
)

// Group related endpoints to control cardinality
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

## Handler Integration

### HTTP Middleware Pattern

```go
func MetricsMiddleware(metrics Metrics) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()

			// Wrap ResponseWriter to capture status code
			wrapper := &responseWriter{
				ResponseWriter: w,
				statusCode:     http.StatusOK,
			}

			next.ServeHTTP(wrapper, r)

			// Record metrics after request completion
			metrics.HTTPRequestCompleted(
				r.Method,
				getEndpointGroup(r.URL.Path),
				wrapper.statusCode,
			)
			metrics.HTTPRequestDuration(
				r.Method,
				getEndpointGroup(r.URL.Path),
				time.Since(start),
			)
		})
	}
}

type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (w *responseWriter) WriteHeader(statusCode int) {
	w.statusCode = statusCode
	w.ResponseWriter.WriteHeader(statusCode)
}
```

### Business Logic Integration

**Record Metrics at Business Event Boundaries:**

```go
func (s *orderService) ProcessOrder(ctx context.Context, order Order) error {
	// Record order received
	s.metrics.OrderReceived(order.Type, order.Priority)

	// Validate order
	if err := s.validator.Validate(ctx, order); err != nil {
		s.metrics.OrderValidationFailed(order.Type, err.Error())
		return errors.Wrap(err, "order validation failed")
	}
	s.metrics.OrderValidationSucceeded(order.Type)

	// Process payment
	start := time.Now()
	if err := s.paymentService.ProcessPayment(ctx, order.Payment); err != nil {
		s.metrics.PaymentProcessingFailed(order.Type, err.Error())
		return errors.Wrap(err, "payment processing failed")
	}
	s.metrics.PaymentProcessingDuration(order.Type, time.Since(start))

	// Store order
	if err := s.repository.Store(ctx, order); err != nil {
		s.metrics.OrderStorageFailed(order.Type, err.Error())
		return errors.Wrap(err, "order storage failed")
	}

	// Record successful completion
	s.metrics.OrderProcessingCompleted(order.Type)
	return nil
}
```

## Testing Strategies

### Unit Testing Metrics Interface

```go
var _ = Describe("UserService Metrics", func() {
	var ctx context.Context
	var userService UserService
	var mockRepository *mocks.UserRepository
	var mockValidator *mocks.UserValidator
	var mockMetrics *mocks.Metrics

	BeforeEach(func() {
		ctx = context.Background()
		mockRepository = &mocks.UserRepository{}
		mockValidator = &mocks.UserValidator{}
		mockMetrics = &mocks.Metrics{}

		userService = NewUserService(mockRepository, mockValidator, mockMetrics)
	})

	Context("CreateUser", func() {
		var user User
		var err error

		BeforeEach(func() {
			user = User{
				ID:   "user-123",
				Type: "premium",
				Name: "John Doe",
			}
		})

		JustBeforeEach(func() {
			err = userService.CreateUser(ctx, user)
		})

		Context("successful creation", func() {
			BeforeEach(func() {
				mockValidator.ValidateReturns(nil)
				mockRepository.StoreReturns(nil)
			})

			It("records user created metric", func() {
				Expect(mockMetrics.UserCreatedCallCount()).To(Equal(1))
				actualUserType := mockMetrics.UserCreatedArgsForCall(0)
				Expect(actualUserType).To(Equal("premium"))
			})

			It("returns no error", func() {
				Expect(err).To(BeNil())
			})
		})

		Context("validation failure", func() {
			BeforeEach(func() {
				mockValidator.ValidateReturns(errors.New("invalid user"))
			})

			It("does not record user created metric", func() {
				Expect(mockMetrics.UserCreatedCallCount()).To(Equal(0))
			})

			It("returns validation error", func() {
				Expect(err).NotTo(BeNil())
				Expect(err.Error()).To(ContainSubstring("invalid user"))
			})
		})
	})
})
```

### Integration Testing with Real Metrics

```go
var _ = Describe("Metrics Integration", func() {
	var registry *prometheus.Registry
	var metrics Metrics

	BeforeEach(func() {
		// Create isolated registry for testing
		registry = prometheus.NewRegistry()
		metrics = NewMetricsWithRegistry(registry)
	})

	Context("UserCreated metric", func() {
		BeforeEach(func() {
			metrics.UserCreated("premium")
			metrics.UserCreated("premium")
			metrics.UserCreated("basic")
		})

		It("records correct metric values", func() {
			metricFamilies, err := registry.Gather()
			Expect(err).To(BeNil())

			// Find user created metric
			var userCreatedMetric *dto.MetricFamily
			for _, mf := range metricFamilies {
				if mf.GetName() == "app_user_created_total" {
					userCreatedMetric = mf
					break
				}
			}

			Expect(userCreatedMetric).NotTo(BeNil())
			Expect(userCreatedMetric.GetType()).To(Equal(dto.MetricType_COUNTER))

			// Verify metric values
			metrics := userCreatedMetric.GetMetric()
			Expect(len(metrics)).To(Equal(2)) // premium and basic

			for _, metric := range metrics {
				labels := metric.GetLabel()
				for _, label := range labels {
					if label.GetName() == "type" {
						switch label.GetValue() {
						case "premium":
							Expect(metric.GetCounter().GetValue()).To(Equal(2.0))
						case "basic":
							Expect(metric.GetCounter().GetValue()).To(Equal(1.0))
						}
					}
				}
			}
		})
	})
})
```

### Testing Push Gateway Integration

```go
var _ = Describe("Metrics Pusher", func() {
	var pusher Pusher
	var testServer *httptest.Server
	var receivedData []byte

	BeforeEach(func() {
		// Mock push gateway server
		testServer = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			var err error
			receivedData, err = ioutil.ReadAll(r.Body)
			Expect(err).To(BeNil())
			w.WriteHeader(http.StatusOK)
		}))

		pusher = NewPusher(testServer.URL, "test-job")
	})

	AfterEach(func() {
		testServer.Close()
	})

	Context("Push", func() {
		BeforeEach(func() {
			// Register and set some test metrics
			testCounter := prometheus.NewCounter(prometheus.CounterOpts{
				Name: "test_metric_total",
				Help: "Test metric for push gateway",
			})
			prometheus.MustRegister(testCounter)
			testCounter.Inc()
		})

		AfterEach(func() {
			prometheus.Unregister(prometheus.NewCounter(prometheus.CounterOpts{
				Name: "test_metric_total",
				Help: "Test metric for push gateway",
			}))
		})

		It("pushes metrics to gateway", func() {
			err := pusher.Push(context.Background())
			Expect(err).To(BeNil())
			Expect(len(receivedData)).To(BeNumerically(">", 0))
			Expect(string(receivedData)).To(ContainSubstring("test_metric_total"))
		})
	})
})
```

### Testing Custom Registry Pattern

```go
var _ = Describe("Custom Registry Metrics", func() {
	var ctx context.Context
	var registry *prometheus.Registry
	var jobMetrics *JobMetrics
	var currentDateTime libtime.CurrentDateTime

	BeforeEach(func() {
		ctx = context.Background()
		registry = prometheus.NewRegistry()
		currentDateTime = libtime.NewCurrentDateTime()
		jobMetrics = NewJobMetrics(registry, currentDateTime)
	})

	Context("JobMetrics with custom registry", func() {
		Context("RecordItemProcessed", func() {
			BeforeEach(func() {
				jobMetrics.RecordItemProcessed(ctx, "success")
				jobMetrics.RecordItemProcessed(ctx, "success")
				jobMetrics.RecordItemProcessed(ctx, "error")
			})

			It("records correct metric values", func() {
				metricFamilies, err := registry.Gather()
				Expect(err).To(BeNil())

				// Find items processed metric
				var itemsMetric *dto.MetricFamily
				for _, mf := range metricFamilies {
					if mf.GetName() == "job_processing_items_total" {
						itemsMetric = mf
						break
					}
				}

				Expect(itemsMetric).NotTo(BeNil())
				Expect(itemsMetric.GetType()).To(Equal(dto.MetricType_COUNTER))

				// Verify metric values by status
				metrics := itemsMetric.GetMetric()
				Expect(len(metrics)).To(Equal(2)) // success and error

				for _, metric := range metrics {
					labels := metric.GetLabel()
					for _, label := range labels {
						if label.GetName() == "status" {
							switch label.GetValue() {
							case "success":
								Expect(metric.GetCounter().GetValue()).To(Equal(2.0))
							case "error":
								Expect(metric.GetCounter().GetValue()).To(Equal(1.0))
							}
						}
					}
				}
			})
		})

		Context("RecordOperationDuration", func() {
			BeforeEach(func() {
				jobMetrics.RecordOperationDuration(ctx, "process-orders", 100*time.Millisecond)
				jobMetrics.RecordOperationDuration(ctx, "process-orders", 200*time.Millisecond)
				jobMetrics.RecordOperationDuration(ctx, "validate-data", 50*time.Millisecond)
			})

			It("records histogram values", func() {
				metricFamilies, err := registry.Gather()
				Expect(err).To(BeNil())

				// Find duration metric
				var durationMetric *dto.MetricFamily
				for _, mf := range metricFamilies {
					if mf.GetName() == "job_processing_duration_seconds" {
						durationMetric = mf
						break
					}
				}

				Expect(durationMetric).NotTo(BeNil())
				Expect(durationMetric.GetType()).To(Equal(dto.MetricType_HISTOGRAM))

				// Verify we have metrics for both operations
				metrics := durationMetric.GetMetric()
				Expect(len(metrics)).To(Equal(2)) // process-orders and validate-data

				// Verify sample counts
				for _, metric := range metrics {
					labels := metric.GetLabel()
					for _, label := range labels {
						if label.GetName() == "operation" {
							switch label.GetValue() {
							case "process-orders":
								Expect(metric.GetHistogram().GetSampleCount()).To(Equal(uint64(2)))
							case "validate-data":
								Expect(metric.GetHistogram().GetSampleCount()).To(Equal(uint64(1)))
							}
						}
					}
				}
			})
		})

		Context("RecordJobRun", func() {
			var fixedTime time.Time

			BeforeEach(func() {
				fixedTime = time.Date(2023, 12, 25, 10, 30, 0, 0, time.UTC)
				currentDateTime = libtimetest.NewCurrentDateTime()
				currentDateTime.SetNow(fixedTime)
				jobMetrics = NewJobMetrics(registry, currentDateTime)

				jobMetrics.RecordJobRun(ctx)
			})

			It("records timestamp gauge", func() {
				metricFamilies, err := registry.Gather()
				Expect(err).To(BeNil())

				// Find timestamp metric
				var timestampMetric *dto.MetricFamily
				for _, mf := range metricFamilies {
					if mf.GetName() == "job_last_run_timestamp_seconds" {
						timestampMetric = mf
						break
					}
				}

				Expect(timestampMetric).NotTo(BeNil())
				Expect(timestampMetric.GetType()).To(Equal(dto.MetricType_GAUGE))

				// Verify timestamp value
				metrics := timestampMetric.GetMetric()
				Expect(len(metrics)).To(Equal(1))
				Expect(metrics[0].GetGauge().GetValue()).To(Equal(float64(fixedTime.Unix())))
			})
		})
	})

	Context("Registry isolation", func() {
		var registry2 *prometheus.Registry
		var jobMetrics2 *JobMetrics

		BeforeEach(func() {
			// Create two separate registries
			registry2 = prometheus.NewRegistry()
			jobMetrics2 = NewJobMetrics(registry2, currentDateTime)

			// Record different values in each
			jobMetrics.RecordItemProcessed(ctx, "success")
			jobMetrics2.RecordItemProcessed(ctx, "error")
		})

		It("keeps metrics isolated between registries", func() {
			// Check first registry
			metricFamilies1, err := registry.Gather()
			Expect(err).To(BeNil())

			var itemsMetric1 *dto.MetricFamily
			for _, mf := range metricFamilies1 {
				if mf.GetName() == "job_processing_items_total" {
					itemsMetric1 = mf
					break
				}
			}

			Expect(itemsMetric1).NotTo(BeNil())
			metrics1 := itemsMetric1.GetMetric()
			Expect(len(metrics1)).To(Equal(1)) // Only "success" status

			// Check second registry
			metricFamilies2, err := registry2.Gather()
			Expect(err).To(BeNil())

			var itemsMetric2 *dto.MetricFamily
			for _, mf := range metricFamilies2 {
				if mf.GetName() == "job_processing_items_total" {
					itemsMetric2 = mf
					break
				}
			}

			Expect(itemsMetric2).NotTo(BeNil())
			metrics2 := itemsMetric2.GetMetric()
			Expect(len(metrics2)).To(Equal(1)) // Only "error" status

			// Verify they have different label values
			Expect(metrics1[0].GetLabel()[0].GetValue()).To(Equal("success"))
			Expect(metrics2[0].GetLabel()[0].GetValue()).To(Equal("error"))
		})
	})
})
```

## Alerting Patterns

Prometheus alerting transforms metrics into actionable notifications when conditions are met. This section covers comprehensive alerting patterns for building reliable monitoring systems.

### Alert Rule Structure

**Standard Alert Rule Format:**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: application-alerts
  namespace: monitoring
spec:
  groups:
  - name: application.rules
    rules:
    - alert: HighErrorRate
      expr: |
        (
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m]))
        ) > 0.05
      for: 2m
      labels:
        severity: warning
        team: backend
        service: user-service
      annotations:
        summary: "High error rate detected"
        description: "Error rate is {{ $value | humanizePercentage }} for service {{ $labels.service }}"
        runbook_url: "https://runbooks.example.com/high-error-rate"
```

### Alert Severity Levels

**Implement Tiered Alerting with Escalation:**

```yaml
# Warning: Early indication of potential issues
- alert: HighResponseTime
  expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Response times are elevated"
    description: "95th percentile response time is {{ $value }}s"

# Critical: Immediate attention required
- alert: HighResponseTimeCritical
  expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 1.0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Response times are critically high"
    description: "95th percentile response time is {{ $value }}s"

# Page: Wake up on-call engineer
- alert: ServiceDown
  expr: up{job="user-service"} == 0
  for: 1m
  labels:
    severity: page
  annotations:
    summary: "Service is completely down"
    description: "User service has been down for more than 1 minute"
```

### Common Alert Patterns

#### 1. Rate-Based Alerts

**Error Rate Monitoring:**

```yaml
# Error rate too high
- alert: HighErrorRate
  expr: |
    (
      sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
      /
      sum(rate(http_requests_total[5m])) by (service)
    ) > 0.01
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "High error rate for {{ $labels.service }}"
    description: "Error rate is {{ $value | humanizePercentage }}"

# Request rate anomaly
- alert: RequestRateAnomaly
  expr: |
    abs(
      sum(rate(http_requests_total[5m])) by (service)
      -
      avg_over_time(sum(rate(http_requests_total[5m])) by (service)[1h])
    ) > (
      2 * stddev_over_time(sum(rate(http_requests_total[5m])) by (service)[1h])
    )
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Unusual request rate pattern for {{ $labels.service }}"
```

#### 2. Latency-Based Alerts

**Response Time Monitoring:**

```yaml
# High latency warning
- alert: HighLatency
  expr: |
    histogram_quantile(0.95,
      sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
    ) > 0.2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High latency detected for {{ $labels.service }}"
    description: "95th percentile latency is {{ $value }}s"

# Latency trend alert
- alert: LatencyTrend
  expr: |
    (
      histogram_quantile(0.95,
        sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
      )
      -
      histogram_quantile(0.95,
        sum(rate(http_request_duration_seconds_bucket[5m] offset 1h)) by (le, service)
      )
    ) > 0.1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Latency trending upward for {{ $labels.service }}"
```

#### 3. Throughput and Capacity Alerts

**Resource Utilization:**

```yaml
# High CPU usage
- alert: HighCPUUsage
  expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High CPU usage on {{ $labels.instance }}"
    description: "CPU usage is {{ $value }}%"

# Memory pressure
- alert: HighMemoryUsage
  expr: |
    (
      node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes
    ) / node_memory_MemTotal_bytes * 100 > 90
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High memory usage on {{ $labels.instance }}"
    description: "Memory usage is {{ $value }}%"

# Disk space warning
- alert: DiskSpaceLow
  expr: |
    (
      node_filesystem_avail_bytes{fstype!="tmpfs"}
      / node_filesystem_size_bytes{fstype!="tmpfs"}
    ) * 100 < 10
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Disk space low on {{ $labels.instance }}"
    description: "Only {{ $value }}% disk space available on {{ $labels.mountpoint }}"
```

#### 4. Business Logic Alerts

**Application-Specific Monitoring:**

```yaml
# Queue depth alert
- alert: QueueDepthHigh
  expr: queue_size > 1000
  for: 2m
  labels:
    severity: warning
    queue: "{{ $labels.queue_name }}"
  annotations:
    summary: "Queue {{ $labels.queue_name }} is backing up"
    description: "Queue depth is {{ $value }} items"

# Processing failure rate
- alert: ProcessingFailureRate
  expr: |
    (
      sum(rate(job_processed_total{status="failed"}[5m])) by (job_type)
      /
      sum(rate(job_processed_total[5m])) by (job_type)
    ) > 0.05
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "High failure rate for {{ $labels.job_type }}"
    description: "Failure rate is {{ $value | humanizePercentage }}"

# User activity anomaly
- alert: UserActivityAnomaly
  expr: |
    abs(
      sum(rate(user_logins_total[10m]))
      -
      avg_over_time(sum(rate(user_logins_total[10m]))[2h])
    ) > (
      3 * stddev_over_time(sum(rate(user_logins_total[10m]))[2h])
    )
  for: 10m
  labels:
    severity: info
  annotations:
    summary: "Unusual user activity pattern detected"
```

#### 5. Absence and Health Check Alerts

**Service Health Monitoring:**

```yaml
# Service absence
- alert: ServiceAbsent
  expr: absent(up{job="user-service"}) == 1
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "User service is absent from monitoring"
    description: "No metrics received from user-service for over 1 minute"

# Metrics staleness
- alert: MetricsStale
  expr: (time() - process_start_time_seconds) > 86400
  for: 0m
  labels:
    severity: warning
  annotations:
    summary: "Service {{ $labels.job }} has stale metrics"
    description: "Service has been running for {{ $value | humanizeDuration }} without restart"

# Health check failure
- alert: HealthCheckFailing
  expr: probe_success{job="blackbox"} == 0
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Health check failing for {{ $labels.instance }}"
    description: "Endpoint {{ $labels.instance }} has been failing health checks"
```

### Advanced Alert Patterns

#### Multi-Condition Alerts

**Complex Logic with Multiple Metrics:**

```yaml
# Service degradation (high latency + high error rate)
- alert: ServiceDegraded
  expr: |
    (
      histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.5
      and
      (
        sum(rate(http_requests_total{status=~"5.."}[5m]))
        /
        sum(rate(http_requests_total[5m]))
      ) > 0.02
    )
  for: 3m
  labels:
    severity: critical
  annotations:
    summary: "Service is degraded (high latency + errors)"
    description: "Both latency and error rates are elevated"
```

#### Time-Based Conditions

**Temporal Logic in Alerts:**

```yaml
# Business hours vs off-hours thresholds
- alert: HighLatencyBusinessHours
  expr: |
    histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.1
    and on() hour() >= 9 < 17
    and on() (day_of_week() > 0 < 6)
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "High latency during business hours"

- alert: HighLatencyOffHours
  expr: |
    histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.5
    and on() (hour() < 9 or hour() >= 17 or day_of_week() == 0 or day_of_week() == 6)
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High latency during off hours"
```

#### Predictive Alerts

**Forecasting Based on Trends:**

```yaml
# Disk space will be full in 4 hours
- alert: DiskWillFillSoon
  expr: |
    predict_linear(node_filesystem_free_bytes[1h], 4*3600) < 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Disk will be full soon on {{ $labels.instance }}"
    description: "Based on current trends, disk {{ $labels.device }} will be full in ~4 hours"

# Memory leak detection
- alert: MemoryLeakDetected
  expr: |
    deriv(process_resident_memory_bytes[30m]) > 1000000  # 1MB/30min increase
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Potential memory leak in {{ $labels.job }}"
    description: "Memory usage increasing by {{ $value | humanizeBytes }}/30min"
```

### Alert Management Best Practices

#### Alert Grouping and Routing

**Organize Alerts by Service and Team:**

```yaml
groups:
  - name: user-service.rules
    interval: 30s
    rules:
      # All user service related alerts

  - name: infrastructure.rules
    interval: 60s
    rules:
      # Infrastructure alerts with longer evaluation interval

  - name: business-logic.rules
    interval: 15s
    rules:
      # Business critical alerts with shorter interval
```

#### Alert Labels for Routing

**Strategic Labeling for AlertManager:**

```yaml
- alert: DatabaseConnectionPool
  expr: database_connections_active / database_connections_max > 0.8
  for: 2m
  labels:
    severity: warning
    team: backend
    service: user-service
    component: database
    environment: production
    priority: high
  annotations:
    summary: "Database connection pool near exhaustion"
    playbook: "https://wiki.example.com/db-connection-pool"
    dashboard: "https://grafana.example.com/d/database-overview"
```

#### Silence Patterns

**Design Alerts to be Silenceable:**

```yaml
# Good: Includes identifying labels for targeted silencing
- alert: HighDiskUsage
  expr: disk_usage_percent > 85
  labels:
    severity: warning
    host: "{{ $labels.instance }}"
    mountpoint: "{{ $labels.mountpoint }}"

# Bad: Missing specific labels makes silencing difficult
- alert: HighDiskUsage
  expr: disk_usage_percent > 85
  labels:
    severity: warning
```

### Testing Alert Rules

#### Unit Testing Alerts

**Prometheus Rule Testing with promtool:**

```yaml
# alerts_test.yaml
rule_files:
  - "alerts.yaml"

evaluation_interval: 1m

tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{job="user-service",status="500"}'
        values: '0+1x10'  # 10 points increasing by 1
      - series: 'http_requests_total{job="user-service",status="200"}'
        values: '0+20x10' # 10 points increasing by 20

    alert_rule_test:
      - eval_time: 5m
        alertname: HighErrorRate
        exp_alerts:
          - exp_labels:
              severity: warning
              job: user-service
            exp_annotations:
              summary: "High error rate for user-service"
```

```bash
# Run alert tests
promtool test rules alerts_test.yaml
```

#### Integration Testing

**Test Alerts in Staging Environment:**

```go
func TestAlertIntegration(t *testing.T) {
    // Generate high error rate
    for i := 0; i < 100; i++ {
        http.Get("http://service/error-endpoint")
    }

    // Wait for alert evaluation
    time.Sleep(5 * time.Minute)

    // Check if alert fired
    alerts := queryPrometheusAlerts("HighErrorRate")
    assert.NotEmpty(t, alerts)
}
```

### Alert Documentation Patterns

#### Runbook Integration

**Link Alerts to Actionable Documentation:**

```yaml
- alert: DatabaseConnectionFailure
  annotations:
    summary: "Cannot connect to database"
    description: "Service {{ $labels.job }} cannot connect to database for {{ $for }}"
    runbook_url: "https://runbooks.example.com/database-connection-failure"
    dashboard_url: "https://grafana.example.com/d/database-dashboard"
    escalation_policy: "page-database-team"
```

#### Template Functions for Annotations

**Rich Alert Descriptions:**

```yaml
annotations:
  summary: "{{ $labels.service }} error rate is {{ $value | humanizePercentage }}"
  description: |
    Error rate for {{ $labels.service }} has been above {{ $threshold | humanizePercentage }}
    for more than {{ $for }}. Current rate: {{ $value | humanizePercentage }}.

    Affected endpoints:
    {{ range query "topk(5, sum(rate(http_requests_total{status=~\"5..\",service=\"" }}{{ $labels.service }}{{ "\"}[5m])) by (endpoint))" }}
    - {{ .Labels.endpoint }}: {{ .Value | printf "%.2f" }} req/s{{ end }}

  graph_url: |
    https://grafana.example.com/render/d-solo/error-rate-dashboard
    ?from={{ ($value.Timestamp.Add(-3600)).Unix }}000
    &to={{ $value.Timestamp.Unix }}000
    &var-service={{ $labels.service }}
```

This comprehensive alerting section provides patterns for building robust monitoring that transforms metrics into actionable insights, ensuring reliable service operation and rapid incident response.

## Performance Considerations

### Efficient Metric Registration

** Good: Register Once During Initialization**

```go
func init() {
	// Register all metrics once at startup
	prometheus.MustRegister(
		requestsCounter,
		responseTimeHistogram,
		activeConnectionsGauge,
	)
}
```

**L Bad: Registering During Request Handling**

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
	// DON'T DO THIS: Registering metrics on every request
	counter := prometheus.NewCounter(prometheus.CounterOpts{
		Name: "requests_total",
	})
	prometheus.MustRegister(counter) // Expensive and will panic after first call
	counter.Inc()
}
```

### Label Value Optimization

**Pre-compute Label Values:**

```go
type MetricsOptimizer struct {
	statusCodeLabels map[int]prometheus.Labels
	methodLabels     map[string]prometheus.Labels
}

func NewMetricsOptimizer() *MetricsOptimizer {
	return &MetricsOptimizer{
		statusCodeLabels: make(map[int]prometheus.Labels),
		methodLabels:     make(map[string]prometheus.Labels),
	}
}

func (m *MetricsOptimizer) getStatusLabel(code int) prometheus.Labels {
	if label, exists := m.statusCodeLabels[code]; exists {
		return label
	}

	label := prometheus.Labels{"status": strconv.Itoa(code)}
	m.statusCodeLabels[code] = label
	return label
}
```

### Memory-Efficient Collectors

**Use Const Labels for Static Information:**

```go
var (
	// Static information that won't change
	serviceInfo = prometheus.NewGaugeVec(prometheus.GaugeOpts{
		Namespace: "app",
		Name:      "info",
		Help:      "Service information",
		ConstLabels: prometheus.Labels{
			"version":     "1.0.0",
			"environment": "production",
			"service":     "user-service",
		},
	}, []string{})
)
```

## Best Practices & Anti-patterns

###  Best Practices

**1. Use Interfaces for Testability**
```go
// Good: Interface allows mocking
type Metrics interface {
	RecordEvent(eventType string)
}

// Implementation
type metrics struct{}
func (m *metrics) RecordEvent(eventType string) { ... }

// Service uses interface
func NewService(metrics Metrics) Service { ... }
```

**2. Fail Fast with MustRegister**
```go
// Good: Application fails at startup if metrics can't be registered
func init() {
	prometheus.MustRegister(requestsCounter)
}
```

**3. Use Appropriate Metric Types**
```go
// Good: Counter for events that only increase
userRegistrationsCounter.Inc()

// Good: Gauge for current state
activeUsersGauge.Set(float64(count))

// Good: Histogram for request durations
requestDurationHistogram.Observe(duration.Seconds())
```

**4. Group Related Metrics**
```go
// Good: Logical grouping with consistent naming
var (
	userRegistrationsTotal = prometheus.NewCounter(...)
	userLoginAttemptsTotal = prometheus.NewCounter(...)
	userActiveGauge        = prometheus.NewGauge(...)
)
```

**5. Handle Errors Gracefully in Push Gateway**
```go
// Good: Don't fail the application if metrics push fails
defer func() {
	if err := pusher.Push(ctx); err != nil {
		log.Printf("metrics push failed (non-fatal): %v", err)
	}
}()
```

### L Anti-patterns

**1. High Cardinality Labels**
```go
// Bad: User ID creates high cardinality
requestsCounter.With(prometheus.Labels{
	"user_id": userID, // Could be millions of unique values
}).Inc()

// Good: Use user type/category instead
requestsCounter.With(prometheus.Labels{
	"user_type": getUserType(user), // Limited set: premium, basic, admin
}).Inc()
```

**2. Using Metrics for Debugging**
```go
// Bad: Metrics are not for debugging information
debugInfo.With(prometheus.Labels{
	"function":  "processOrder",
	"line":      "123",
	"timestamp": time.Now().String(),
}).Set(1)

// Good: Use proper logging for debugging
log.Printf("processing order at line 123")
```

**3. Inconsistent Naming**
```go
// Bad: Inconsistent naming patterns
var (
	userCount     = prometheus.NewGauge(...)    // Missing namespace
	httpRequests  = prometheus.NewCounter(...)  // Different style
	response_time = prometheus.NewHistogram(...) // snake_case vs camelCase
)

// Good: Consistent naming
var (
	appUserActiveTotal        = prometheus.NewGauge(...)
	appHTTPRequestsTotal      = prometheus.NewCounter(...)
	appHTTPResponseTimeSeconds = prometheus.NewHistogram(...)
)
```

**4. Metrics in Hot Paths Without Consideration**
```go
// Bad: Expensive operations in hot path
func processItem(item Item) {
	start := time.Now()

	// Complex label computation
	category := computeComplexCategory(item) // Expensive operation
	region := getRegionFromIP(item.IP)       // Network call

	processedItemsCounter.With(prometheus.Labels{
		"category": category,
		"region":   region,
	}).Inc()

	processItemsHistogram.Observe(time.Since(start).Seconds())
}

// Good: Pre-compute expensive labels or use simpler alternatives
func processItem(item Item) {
	start := time.Now()

	// Use pre-computed or cached values
	category := item.PrecomputedCategory // Set during item creation

	processedItemsCounter.With(prometheus.Labels{
		"category": category,
	}).Inc()

	processItemsHistogram.Observe(time.Since(start).Seconds())
}
```

**5. Ignoring Metric Collection Performance**
```go
// Bad: Creating new labels map for every call
func recordMetric(userType string, status string) {
	labels := prometheus.Labels{ // New allocation every time
		"user_type": userType,
		"status":    status,
	}
	counter.With(labels).Inc()
}

// Good: Reuse label maps or use metric vectors efficiently
var labelPool = sync.Pool{
	New: func() interface{} { return make(prometheus.Labels) },
}

func recordMetric(userType string, status string) {
	labels := labelPool.Get().(prometheus.Labels)
	defer labelPool.Put(labels)

	// Clear and reuse
	for k := range labels {
		delete(labels, k)
	}
	labels["user_type"] = userType
	labels["status"] = status

	counter.With(labels).Inc()
}
```

## Real-World Implementation Example

Here's a comprehensive example bringing together all the patterns:

```go
package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// Metrics interface for dependency injection and testing
//counterfeiter:generate -o mocks/metrics.go --fake-name Metrics . Metrics
type Metrics interface {
	HTTPRequestReceived(method, endpoint string)
	HTTPRequestCompleted(method, endpoint string, statusCode int, duration time.Duration)
	UserOperationCompleted(operation string, success bool)
	ActiveConnections(count int)
}

// Metrics implementation
type metrics struct{}

func NewMetrics() Metrics {
	return &metrics{}
}

func (m *metrics) HTTPRequestReceived(method, endpoint string) {
	httpRequestsInFlight.With(prometheus.Labels{
		"method":   method,
		"endpoint": endpoint,
	}).Inc()
}

func (m *metrics) HTTPRequestCompleted(method, endpoint string, statusCode int, duration time.Duration) {
	httpRequestsInFlight.With(prometheus.Labels{
		"method":   method,
		"endpoint": endpoint,
	}).Dec()

	httpRequestsTotal.With(prometheus.Labels{
		"method":   method,
		"endpoint": endpoint,
		"status":   http.StatusText(statusCode),
	}).Inc()

	httpRequestDuration.With(prometheus.Labels{
		"method":   method,
		"endpoint": endpoint,
	}).Observe(duration.Seconds())
}

func (m *metrics) UserOperationCompleted(operation string, success bool) {
	status := "failure"
	if success {
		status = "success"
	}

	userOperationsTotal.With(prometheus.Labels{
		"operation": operation,
		"status":    status,
	}).Inc()
}

func (m *metrics) ActiveConnections(count int) {
	httpActiveConnections.Set(float64(count))
}

// Metrics registration
var (
	httpRequestsInFlight = prometheus.NewGaugeVec(prometheus.GaugeOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "requests_in_flight",
		Help:      "Number of HTTP requests currently being processed",
	}, []string{"method", "endpoint"})

	httpRequestsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "requests_total",
		Help:      "Total number of HTTP requests processed",
	}, []string{"method", "endpoint", "status"})

	httpRequestDuration = prometheus.NewHistogramVec(prometheus.HistogramOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "request_duration_seconds",
		Help:      "HTTP request duration in seconds",
		Buckets:   prometheus.DefBuckets,
	}, []string{"method", "endpoint"})

	httpActiveConnections = prometheus.NewGauge(prometheus.GaugeOpts{
		Namespace: "app",
		Subsystem: "http",
		Name:      "active_connections",
		Help:      "Number of active HTTP connections",
	})

	userOperationsTotal = prometheus.NewCounterVec(prometheus.CounterOpts{
		Namespace: "app",
		Subsystem: "user",
		Name:      "operations_total",
		Help:      "Total number of user operations",
	}, []string{"operation", "status"})
)

func init() {
	prometheus.MustRegister(
		httpRequestsInFlight,
		httpRequestsTotal,
		httpRequestDuration,
		httpActiveConnections,
		userOperationsTotal,
	)
}

// HTTP middleware with metrics
func MetricsMiddleware(metrics Metrics) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			endpoint := getEndpointGroup(r.URL.Path)

			metrics.HTTPRequestReceived(r.Method, endpoint)

			wrapper := &responseWriter{ResponseWriter: w, statusCode: 200}
			next.ServeHTTP(wrapper, r)

			metrics.HTTPRequestCompleted(r.Method, endpoint, wrapper.statusCode, time.Since(start))
		})
	}
}

type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (w *responseWriter) WriteHeader(code int) {
	w.statusCode = code
	w.ResponseWriter.WriteHeader(code)
}

func getEndpointGroup(path string) string {
	switch {
	case path == "/health":
		return "health"
	case path == "/metrics":
		return "metrics"
	case path == "/api/users":
		return "users"
	default:
		return "other"
	}
}

// Service with metrics integration
type UserService struct {
	metrics Metrics
}

func NewUserService(metrics Metrics) *UserService {
	return &UserService{metrics: metrics}
}

func (s *UserService) CreateUser(ctx context.Context, user User) error {
	// Business logic here...
	success := true // Determine based on actual result

	s.metrics.UserOperationCompleted("create", success)
	return nil
}

type User struct {
	ID   string
	Name string
}

func main() {
	metrics := NewMetrics()
	userService := NewUserService(metrics)

	// HTTP handlers
	http.Handle("/metrics", promhttp.Handler())
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	http.HandleFunc("/api/users", func(w http.ResponseWriter, r *http.Request) {
		user := User{ID: "123", Name: "John"}
		if err := userService.CreateUser(r.Context(), user); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusCreated)
	})

	// Apply metrics middleware
	handler := MetricsMiddleware(metrics)(http.DefaultServeMux)

	log.Println("Starting server on :8080")
	log.Println("Metrics available at http://localhost:8080/metrics")
	log.Fatal(http.ListenAndServe(":8080", handler))
}
```

This comprehensive guide provides the foundation for implementing robust, observable Go applications with Prometheus metrics, following best practices for maintainability, testability, and performance.