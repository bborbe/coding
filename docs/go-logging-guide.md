# Go Logging

**New projects:** `log/slog` (stdlib). **Existing with glog:** keep `glog`, don't mix.

## slog (New Projects)

```go
import "log/slog"

slog.Info("service started", "port", port, "dir", watchDir)
slog.Error("process failed", "error", err, "prompt", name)
slog.Warn("high memory", "percent", memPct)
slog.Debug("cache miss", "key", cacheKey)

// With context
slog.InfoContext(ctx, "processing", "file", path)
```

Always use key-value pairs. Never `slog.Info(fmt.Sprintf(...))`.

## glog (Existing Projects)

```go
import "github.com/golang/glog"

glog.Errorf("failed to process %s: %v", id, err)   // requires operator action
glog.Warningf("retry %d for %s", attempt, id)       // unexpected, non-fatal
glog.Infof("service started on port %d", port)      // V0: startup/shutdown only
glog.V(1).Infof("config: addr=%s dir=%s", addr, dir) // V1: prod troubleshooting
glog.V(2).Infof("scan cycle: %d changed", n)         // V2: heartbeat (use sampling!)
glog.V(3).Infof("processing item %s", id)            // V3: per-item debug detail
glog.V(4).Infof("raw state: %+v", state)             // V4: trace everything
```

**V(2) = production heartbeat** — only log when something meaningful happened (e.g. N > 0), or use a sampler. Default `LOGLEVEL=2`.
**V(3) = developer debug** — enable temporarily to see per-item detail.
**V(4) = trace** — full internals.

## Log Sampling (glog projects)

Use `github.com/bborbe/log` to reduce noise in hot paths:

```go
// Constructor — create sampler once
type myHandler struct {
    logSampler log.Sampler
}
func NewMyHandler(logSamplerFactory log.SamplerFactory) *myHandler {
    return &myHandler{logSampler: logSamplerFactory.Sampler()}
}

// Hot path — check before logging
if h.logSampler.IsSample() {
    glog.V(2).Infof("processed %d items", count)
}
```

| Sampler | Behaviour |
|---------|-----------|
| `log.NewSampleTime(d)` | At most once per duration |
| `log.NewSampleMod(n)` | Every N-th call |
| `log.NewSamplerGlogLevel(n)` | When verbosity ≥ n |
| `log.SamplerList{...}` | OR of multiple samplers |

`log.DefaultSamplerFactory` = `SamplerList{NewSampleTime(10s), NewSamplerGlogLevel(4)}` — standard for `JSONSender`/`EventObjectSender`.

Pass `log.SamplerFactory` (not `log.Sampler`) to constructors for testability.

## Runtime Log Level

Bump glog `-v` at runtime via `/setloglevel/{N}` — auto-resets after 5 min:

```bash
curl http://pod:9090/setloglevel/3   # 3 = enable V(1)..V(3)
curl http://pod:9090/setloglevel/4   # 4 = +V(4) debug paths
```

Wiring: see [go-http-service-guide.md](go-http-service-guide.md) for the canonical admin endpoint block (router registration, baseline level, TTL).

## External Calls — Always Log

Any call that crosses the process boundary (HTTP, gRPC, DB, message bus, subprocess) is logged on response. Without this, runtime mysteries — "did the payment send? did the webhook deliver? did the job enqueue?" — become guesswork from indirect signals. The log line is the audit trail.

Minimum payload: method + path/op + status code + latency. Add error message on non-success. Never log credentials, request bodies with secrets, or full response bodies — log lengths/counts instead.

```go
// HTTP client — one log line per call
// [GOOD]
status, body, err := doRequest(ctx, client, token, "POST", url, payload)
glog.Infof("http POST %s status=%d body_len=%d", path, status, len(body))
if err != nil {
    glog.Warningf("http POST %s failed: %v", path, err)
}

// [BAD] — silent boundary: caller has no audit trail
status, body, err := doRequest(ctx, client, token, "POST", url, payload)
if err != nil {
    return err
}

// gRPC client — log on response
// [GOOD]
resp, err := client.SomeRPC(ctx, req)
glog.Infof("rpc %s.%s status=%v", service, method, statusOf(err))

// DB query — log latency on hot queries
// [GOOD]
start := time.Now()
rows, err := db.QueryContext(ctx, query, args...)
glog.Infof("db query=%s rows=%d elapsed=%v", queryName, count, time.Since(start))
```

**Hot path?** Wrap with a sampler so high-frequency calls don't drown the log:

```go
if c.logSampler.IsSample() {
    glog.Infof("queue publish topic=%s partition=%d offset=%d", topic, p, offset)
}
```

**Verbosity choice**: `glog.Infof` (V0) for low-frequency external calls where every call matters (payments, deploys, webhook sends, audit-relevant API writes). `glog.V(2)` + sampler for high-frequency (message-bus publishes, cache lookups, polling). Avoid `V(3)+` for boundary calls — they're operational signal, not debug detail.

**What to grep for later**: pick a consistent prefix per boundary so `kubectl logs ... | grep http` returns everything. Examples: `http POST`, `rpc UserService.GetUser`, `db query`, `subprocess exec`.

## Rules

- **Don't mix** slog and glog in the same project
- **Don't log + return error** — do one or the other
- **Lowercase messages**
- **No sensitive data** — no tokens, passwords, PII
- **Log at boundaries** — handlers, processors, startup — not deep internals
- **Don't log in tight loops** — log aggregated result, or use sampler
- **V(2) with nothing to report** — skip the log line, or use sampling
- **Every external call logs its response** — see "External Calls" above. Default V0 for low-frequency; sampled V(2) for hot paths. No silent boundaries.
