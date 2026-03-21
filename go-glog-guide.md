# Go glog Logging Levels

> **New projects should use `log/slog`** (stdlib, Go 1.21+) with `cobra` for CLI flag parsing. slog avoids glog's global `flag` pollution and integrates cleanly with structured logging. This guide is for **existing projects that already use glog extensively** — do not introduce glog into new codebases.

Google's [glog](https://github.com/golang/glog) provides more granular logging levels than standard Go logging. This guide explains when to use each level for consistent logging across Go services.

## Error - Always an Error / Requires System Operator Action

Use for genuine errors that require immediate attention:

- Application failures that prevent normal operation
- Database connection failures
- Critical service dependencies unavailable
- Configuration errors preventing startup
- Security violations or authentication failures

```go
glog.Error("Database connection failed:", err)
glog.Errorf("Failed to authenticate user %s: %v", userID, err)
```

## Warning - Probably an Error / Investigate When Possible

Use for unexpected conditions that don't immediately break functionality:

- Deprecated API usage
- Performance degradation warnings
- Resource constraints (high memory/CPU)
- Retryable operation failures
- Non-critical service dependencies unavailable

```go
glog.Warning("API endpoint deprecated, will be removed in v2.0")
glog.Warningf("High memory usage detected: %d%%", memoryPercent)
```

## Info V0 - Production Default / System Operator Information

This is the default production logging level. Only log information that IT operators need to see:

- Application startup/shutdown events
- Service health status changes
- CLI argument processing results
- Recovery from panic situations
- License or compliance notifications

```go
glog.Info("Service started successfully on port 8080")
glog.Infof("Recovered from panic: %v", recovered)
```

## Info V1 - System Operator Debug / Production Troubleshooting

Use when IT needs to debug production issues:

- Configuration details (ports, paths, timeouts)
- Service discovery events
- Load balancer health check results
- Recoverable errors with retry logic
- Resource allocation information

```go
glog.V(1).Infof("Listening on %s, watching directory %s", addr, watchDir)
glog.V(1).Infof("Pod %s marked unhealthy, will retry", podName)
```

## Info V2 - External Communication / Developer Default

Standard level for development environments:

- HTTP request/response logging with status codes
- External API calls and responses
- State transitions in business logic
- Cache hits/misses
- Background job processing

```go
glog.V(2).Infof("HTTP %s %s -> %d (%s)", method, path, statusCode, duration)
glog.V(2).Infof("Cache miss for key %s, fetching from database", key)
```

## Info V3+ - Developer Debug / Deep Troubleshooting

Use for detailed debugging information:

- Function entry/exit tracing
- Variable state dumps
- Algorithm step-by-step execution
- Performance timing details
- Internal data structure contents

```go
glog.V(3).Infof("Processing batch of %d items", len(batch))
glog.V(4).Infof("Internal state: %+v", internalStruct)
```

## Best Practices

1. **Be Consistent**: Use the same level for similar types of events across services
2. **Be Contextual**: Include relevant context (user ID, request ID, operation type)
3. **Be Actionable**: Error and Warning logs should suggest what action to take
4. **Be Measured**: Higher verbosity levels should provide progressively more detail
5. **Use Structured Logging**: Consider key-value pairs for better log parsing

```go
// Good: Contextual and actionable
glog.Errorf("Failed to process user %s request %s: %v", userID, requestID, err)

// Avoid: Vague and unhelpful
glog.Error("Something went wrong")
```
