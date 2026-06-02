# Go Logging

**New projects:** `log/slog` (stdlib). **Existing with glog:** keep `glog`, don't mix.

## Rules

### RULE go-logging/no-mixing-slog-and-glog (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go file in a project that already uses one logging library (`log/slog` OR `github.com/golang/glog`) imports the other one — meaning the codebase emits both stdlib structured logs and glog's V-leveled string logs from the same binary.
**Enforcement**: judgment (semantic — distinguishing "this binary already uses X; the new import of Y is wrong" from "this is a new binary that happens to coexist with X-using siblings in the monorepo" requires checking which logger the rest of the same module uses; ast-grep partial: detect both `import "log/slog"` AND `import "github.com/golang/glog"` co-occurring in any single `.go` file)
**Why**: Mixing the two loggers in one binary fragments the operator's view: log aggregators see two different formats (slog's structured key-values vs glog's free-form Errorf strings), grep patterns from one side miss the other, and verbosity gating (`-v` for glog, log level for slog) controls only half the output. Migration is an explicit project-level decision — either all-slog or all-glog — not a per-file choice that creeps in during PR review.

#### Bad

```go
import (
	"log/slog"
	"github.com/golang/glog"
)

func process() {
	slog.Info("starting", "items", 42)   // structured
	glog.Infof("done with %d items", 42) // unstructured — different format same binary
}
```

#### Good

```go
// Existing glog project — keep glog throughout
import "github.com/golang/glog"

func process() {
	glog.Infof("starting items=%d", 42)
	glog.Infof("done items=%d", 42)
}
```

### RULE go-logging/no-log-and-return-error (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go function logs an error (via `glog.Errorf` / `slog.Error` / `log.Printf` / similar) and then also returns the same error to the caller — meaning the error is reported twice: once at the inner site and again upstream when the caller (or its caller) logs the propagated error.
**Enforcement**: judgment (semantic — distinguishing "intentional inner log + return for diagnostic visibility" from "accidental double-log" requires reading the caller's handling; ast-grep partial: `if err != nil { glog.Errorf(...); return ..., err }` pattern in any non-main, non-test Go file)
**Why**: Logging at the inner site AND returning means the same error lands in the log twice — once with the inner context, once with the outer wrapper. Aggregators count it as two events, alerts double-fire, and the stack-trace breadcrumbs disagree about where the error actually originated. Pick one: either log at the boundary (`main.go`, top-level handler) and let the inner code return; OR consume the error inline (log it, recover, return success). Never both.

#### Bad

```go
func fetchUser(ctx context.Context, id string) (*User, error) {
	user, err := store.Get(ctx, id)
	if err != nil {
		glog.Errorf("failed to fetch user %s: %v", id, err) // logged here
		return nil, errors.Wrapf(ctx, err, "fetch user")    // AND returned — logged again upstream
	}
	return user, nil
}
```

#### Good

```go
// Inner: return only — the boundary decides what to log
func fetchUser(ctx context.Context, id string) (*User, error) {
	user, err := store.Get(ctx, id)
	if err != nil {
		return nil, errors.Wrapf(ctx, err, "fetch user %s", id)
	}
	return user, nil
}

// Boundary (HTTP handler / main.go): log once with full context
func (h *handler) Get(w http.ResponseWriter, r *http.Request) {
	user, err := h.svc.FetchUser(r.Context(), id)
	if err != nil {
		glog.Errorf("get user %s: %+v", id, err) // log once at the boundary
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
}
```

### RULE go-logging/external-call-logs-response (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go function makes a call that crosses the process boundary (HTTP client, gRPC client, database query, message-bus publish, subprocess `exec`) without emitting a single log line summarising the call's outcome (method/op + status/result + latency, plus error message on failure).
**Enforcement**: judgment (semantic — identifying "this is a boundary call" requires recognising the client package (`http.Client.Do`, `*sql.DB.Query`, `client.SomeRPC`, `kafka.Producer.Send`, `exec.Command`) and verifying no log statement follows; ast-grep partial: `call_expression` matching known boundary clients without a sibling glog/slog call in the same block)
**Why**: Boundary calls are the audit trail. Without a log line per call, runtime mysteries — "did the payment send? did the webhook deliver? did the job enqueue?" — become guesswork from indirect signals (downstream alerts, partial state in a DB, support tickets). The log line lets operators answer "what crossed the wire?" without redeploying with extra instrumentation. Minimum payload: method + path/op + status code + latency; add error message on non-success. Never log credentials, request bodies with secrets, or full response bodies — log lengths/counts instead.

#### Bad

```go
// Silent boundary — caller has no audit trail
status, body, err := doRequest(ctx, client, token, "POST", url, payload)
if err != nil {
	return err
}
return parseBody(body)
```

#### Good

```go
status, body, err := doRequest(ctx, client, token, "POST", url, payload)
glog.Infof("http POST %s status=%d body_len=%d", path, status, len(body))
if err != nil {
	glog.Warningf("http POST %s failed: %v", path, err)
	return err
}
return parseBody(body)
```

### RULE go-logging/no-sensitive-data-in-logs (MUST)

**Owner**: go-security-specialist
**Applies when**: a Go log statement (`glog.Infof` / `slog.Info` / `log.Printf` / similar) interpolates a value whose name or content suggests sensitive material (password, token, secret, key, PEM, JWT, raw request body containing credentials, full session cookie).
**Enforcement**: judgment (semantic — distinguishing "credential" from "credential-shaped name on a public value (e.g. `publicKey`)" requires reading the source and intent; ast-grep partial: `call_expression` matching `glog.*` / `slog.*` with format args including identifiers matching `(?i)password|token|secret|.*Key|PEM|JWT|credential|authorization`)
**Why**: Logged credentials land in stdout, log aggregators, cloud logging backends — searchable, indexed, and impossible to redact once the batch has shipped. A single `glog.Infof("config: %+v", cfg)` on a struct that contains a `PEMKey` field leaks the key to every operator with log access. Use `display:"length"` tags (see `go-k8s-binary/secret-fields-need-display-length`), log lengths instead of values (`body_len=%d`), and never interpolate raw credential-shaped variables into log strings.

#### Bad

```go
// %+v dumps the whole struct including the PEMKey field — secret in the log
glog.Infof("config: %+v", cfg)

// Direct interpolation
glog.Infof("authenticated with token=%s", token)
```

#### Good

```go
// Length only — operators know it's set without seeing the value
glog.Infof("config: stage=%s pem_key_len=%d", cfg.Stage, len(cfg.PEMKey))
glog.Infof("authenticated token_len=%d", len(token))
```

### RULE go-logging/lowercase-log-messages (SHOULD)

**Owner**: go-quality-assistant
**Applies when**: a Go log call's message string starts with an uppercase letter (`glog.Infof("Service started ...")`, `slog.Info("Failed to ...")`).
**Enforcement**: judgment (ast-grep follow-up: pattern over `glog.{Info,Warning,Error,Fatal}{,f}` / `slog.{Info,Warn,Error,Debug}` first-string-literal argument matching `^"[A-Z]`)
**Why**: Convention — log lines are streamed mid-sentence into structured-log search tools; lowercase makes the multi-source stream look uniform (no random capitalised mid-line "Failed to" tokens), and matches Go's stdlib `log` package convention. Cheap to maintain via grep; consistency pays off when operators eyeball thousands of log lines per minute.

#### Bad

```go
glog.Infof("Service started on port %d", port)
slog.Error("Failed to parse request", "error", err)
```

#### Good

```go
glog.Infof("service started on port %d", port)
slog.Error("failed to parse request", "error", err)
```

### RULE go-logging/no-tight-loop-without-sampler (SHOULD)

**Owner**: go-quality-assistant
**Applies when**: a Go log statement appears inside a `for` loop body that processes more than ~100 items per iteration without being gated by a `log.Sampler` / `IsSample()` check or a `glog.V(N)` verbosity guard.
**Enforcement**: judgment (semantic — distinguishing "tight inner loop" from "small bounded outer loop" requires reading the loop bound; ast-grep partial: `call_expression` matching `glog.{Info,Warning}{,f}` / `slog.{Info,Warn}` inside a `for_statement` body without a sibling `if .IsSample()` / `glog.V(N)` guard)
**Why**: Unsampled log calls in hot paths produce log gigabytes per minute — drowning real operator signal, inflating cloud-logging cost, and adding non-trivial latency to the loop itself (sync.Mutex contention inside `glog` on heavy concurrent writes). Sampling preserves the "is something happening?" signal at sustainable volume. `github.com/bborbe/log` provides `NewSampleTime(d)` (once per duration), `NewSampleMod(n)` (every N-th), `NewSamplerGlogLevel(n)` (gated by verbosity).

#### Bad

```go
for _, item := range items {
	if err := process(item); err != nil {
		glog.Warningf("process %s failed: %v", item.ID, err) // every iteration, no sampler
	}
}
```

#### Good

```go
for _, item := range items {
	if err := process(item); err != nil {
		if h.logSampler.IsSample() {
			glog.Warningf("process %s failed: %v", item.ID, err)
		}
	}
}
// Or: aggregate and log once after the loop
var failures int
for _, item := range items {
	if err := process(item); err != nil {
		failures++
	}
}
if failures > 0 {
	glog.Warningf("processed %d items, %d failures", len(items), failures)
}
```

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

## Related Rules

- [`go-cli/slog-not-glog-in-new-projects`](go-cli-guide.md) — new projects should pick `slog`, not introduce `glog`
- [`go-glog/use-v-for-debug-not-info`](go-glog-guide.md) — V0 (bare `glog.Info`) is operator-default; debug-shaped lines go behind `V(N)`
- [`go-k8s-binary/secret-fields-need-display-length`](go-k8s-binary-conventions.md) — application-config secret fields carry `display:"length"` so `argument.Parse()` startup dump never prints values
