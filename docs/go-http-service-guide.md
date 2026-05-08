# Go HTTP Service Guide

How to set up the HTTP server in a Go service: the canonical admin endpoint block, port conventions, and wiring.

## Goal

Every long-running Go service exposes a consistent admin HTTP server with operational endpoints (health, metrics, runtime debug). New services copy this block verbatim — only add endpoints, never remove or rename the standard ones.

## Canonical Server

```go
import (
    "context"
    "time"

    libhttp "github.com/bborbe/http"
    libkv "github.com/bborbe/kv"
    "github.com/bborbe/log"
    libsentry "github.com/bborbe/sentry"
    "github.com/bborbe/run"
    "github.com/golang/glog"
    "github.com/gorilla/mux"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

func (a *application) createHTTPServer(
    sentryClient libsentry.Client,
    db libkv.DB,
) run.Func {
    return func(ctx context.Context) error {
        ctx, cancel := context.WithCancel(ctx)
        defer cancel()

        router := mux.NewRouter()
        router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/readiness").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/metrics").Handler(promhttp.Handler())
        router.Path("/setloglevel/{level}").
            Handler(log.NewSetLoglevelHandler(ctx, log.NewLogLevelSetter(2, 5*time.Minute)))
        router.Path("/gc").Handler(libhttp.NewGarbageCollectorHandler())

        // Conditional — only when the service has a kv DB
        router.Path("/resetdb").Handler(libkv.NewResetHandler(db, cancel))
        router.Path("/resetbucket/{BucketName}").Handler(libkv.NewResetBucketHandler(db, cancel))

        glog.V(2).Infof("starting http server listen on %s", a.Listen)
        return libhttp.NewServer(a.Listen, router).Run(ctx)
    }
}
```

## Endpoint Catalog

| Endpoint | Required | Purpose | Library |
|---|---|---|---|
| `/healthz` | always | Liveness probe (always 200 OK) | `libhttp.NewPrintHandler` |
| `/readiness` | always | Readiness probe (200 OK or 503 if not ready) | `libhttp.NewPrintHandler` |
| `/metrics` | always | Prometheus scrape endpoint | `promhttp.Handler()` |
| `/setloglevel/{level}` | always | Raise glog `-v` at runtime, auto-resets after 5 min | `log.NewSetLoglevelHandler` |
| `/gc` | always | Manually trigger Go GC for memory inspection | `libhttp.NewGarbageCollectorHandler` |
| `/resetdb` | conditional (kv) | Drop and recreate boltdb buckets — restarts service via cancel | `libkv.NewResetHandler` |
| `/resetbucket/{BucketName}` | conditional (kv) | Drop a single bucket — restarts service | `libkv.NewResetBucketHandler` |
| `/trigger` | conditional (poller) | Manually fire a periodic job out-of-cycle | `libhttp.NewBackgroundRunHandler` |
| `/sentryalert` | conditional (alerts) | Send a test event to Sentry | factory-built |
| `/testloglevel` | conditional (debug) | Emit log lines at every level for verification | factory-built |

## Port Conventions

- **Always `9090`** for the admin HTTP server. Mirrors the standard across all bborbe services and the Prometheus scrape annotations.
- Listen address comes from a flag/env: `Listen string \`required:"false" arg:"listen" env:"LISTEN" default:":9090"\``.
- Public API (frontend-accessible data) lives on a different prefix (`/api/1.0/...`) — typically same port via the same router, or a separate listener.

## `/setloglevel/{level}` — Constructor Args

```go
log.NewLogLevelSetter(2, 5*time.Minute)
//                    ^  ^
//                    |  auto-reset window — level reverts to baseline after TTL
//                    baseline glog `-v` (must match the StatefulSet `-v=` arg)
```

For glog level meanings (`V(1)` vs `V(3)` vs `V(4)`) and curl usage, see [go-logging-guide.md](go-logging-guide.md).

## Kubernetes Service Wiring

Pair the server with a Service manifest carrying the gateway annotations so the admin URL is reachable through the public ingress:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  annotations:
    admin/port: '9090'
    admin/path: ''
spec:
  ports:
    - name: http
      port: 9090
```

Routes auto-register at `https://<stage>.example.com/admin/<service>/...` once the gateway's service watcher sees the annotated svc. No ingress edit needed.

## Server Lifecycle

- Use `libhttp.NewServer(listen, router).Run(ctx)` — handles graceful shutdown on `ctx.Done()`.
- Wrap the function as a `run.Func` so it composes with other long-running goroutines via `run.NewListGroup` or similar.
- The closure captures `ctx` and a `cancel` derived from it. `/resetdb` and `/resetbucket` invoke `cancel()` to force a restart after destructive ops — that's by design, the service should be supervised by Kubernetes.

## Security

- The admin block has **no authentication** at the service level. Auth lives at the gateway (`FrontendGatewayAdminPermission` in the bborbe stack).
- Never expose port 9090 directly via NodePort/LoadBalancer. Cluster-internal only.
- Destructive endpoints (`/resetdb`, `/resetbucket`) trust the network boundary. If your service runs outside the gateway's auth umbrella, add middleware.

## Anti-Patterns

❌ **Custom port per service** — breaks scrape configs and gateway annotations.
✅ Always `9090`.

❌ **Renaming `/healthz` to `/health`** — breaks Kubernetes probe defaults and shared tooling.
✅ Use the standard names verbatim.

❌ **Adding business endpoints next to admin endpoints** — pollutes `/admin/<svc>/...`. Public traffic shouldn't share routes with destructive admin endpoints.
✅ Mount business handlers under `/api/1.0/...` (no `admin/path` annotation needed for them).

❌ **Skipping `/setloglevel`** — forces StatefulSet edits + pod restart for every debug session.
✅ Always include it — 2 lines, no cost.

❌ **`db` arg passed but service has no DB** — wires a dependency that doesn't exist.
✅ Drop `db libkv.DB` from the signature; omit `/resetdb` and `/resetbucket`.

❌ **Default log level 0 in `NewLogLevelSetter`** — masks INFO and above when level reverts.
✅ Pass `2` (matches StatefulSet `-v=2` default).

## Validation Checklist

- [ ] `/healthz`, `/readiness`, `/metrics`, `/setloglevel/{level}`, `/gc` all registered
- [ ] Listen port is `9090`
- [ ] Service yaml has `admin/port: '9090'` and `admin/path: ''` annotations
- [ ] `libhttp.NewServer` (or equivalent) wraps the router
- [ ] `ctx` and `cancel` are scoped inside the closure for shutdown propagation
- [ ] Conditional endpoints (`/resetdb`, `/trigger`, `/sentryalert`) only present when their dependency is in scope
- [ ] No business endpoints mixed into the admin block

## References

- `go-skeleton/main.go` — canonical reference implementation
- [go-logging-guide.md](go-logging-guide.md) — `/setloglevel/{level}` details, glog verbosity levels
- [go-prometheus-metrics-guide.md](go-prometheus-metrics-guide.md) — `/metrics` endpoint and metric definitions
- [go-http-handler-refactoring-guide.md](go-http-handler-refactoring-guide.md) — refactoring inline handlers into factories
- [go-architecture-patterns.md](go-architecture-patterns.md) — broader service architecture
