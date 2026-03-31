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

```go
// Register endpoint in HTTP server
router.Path("/setloglevel/{level}").Handler(
    log.NewSetLoglevelHandler(ctx, log.NewLogLevelSetter(2, 5*time.Minute)),
)
```

```bash
curl http://pod:9090/setloglevel/3   # bump temporarily
# auto-resets to 2 after 5 minutes
```

## Rules

- **Don't mix** slog and glog in the same project
- **Don't log + return error** — do one or the other
- **Lowercase messages**
- **No sensitive data** — no tokens, passwords, PII
- **Log at boundaries** — handlers, processors, startup — not deep internals
- **Don't log in tight loops** — log aggregated result, or use sampler
- **V(2) with nothing to report** — skip the log line, or use sampling
