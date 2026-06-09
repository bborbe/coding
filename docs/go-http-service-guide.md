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

### RULE go-http-service/canonical-admin-endpoints (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: a Go service's admin HTTP server (port 9090, mounted under `/admin/<svc>/...` by the gateway) is missing any of the five always-required endpoints: `/healthz`, `/readiness`, `/metrics`, `/setloglevel/{level}`, `/gc`.
**Enforcement**: `rules/go/canonical-admin-endpoints.yml` flags `router.Path(...)` / `router.Handle(...)` / `mux.Handle(...)` calls registering any of the five canonical paths as a first-pass filter. The agent audits the route table to confirm all five are present; a file with only some endpoints registered fires the rule for the agent to check completeness.
**Why**: The five endpoints are the cross-service contract between every bborbe Go service and the supervisor (Kubernetes probes, Prometheus scrapes, on-call debugging, manual GC inspection). A service missing `/healthz` blocks Kubernetes liveness probes; missing `/readiness` breaks rollout coordination; missing `/setloglevel` forces a StatefulSet edit + pod restart for every debug session. The endpoints are cheap (a few lines each, factory-built) and the cost of omitting one shows up at the worst possible time — usually during an incident.

#### Bad

```go
// main.go — admin server missing /setloglevel and /gc
router := mux.NewRouter()
router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
router.Path("/readiness").Handler(libhttp.NewPrintHandler("OK"))
router.Path("/metrics").Handler(promhttp.Handler())
// debug session means: edit StatefulSet -v=, restart pod, wait — every time
```

#### Good

```go
// main.go — all five canonical endpoints registered
router := mux.NewRouter()
router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
router.Path("/readiness").Handler(libhttp.NewPrintHandler("OK"))
router.Path("/metrics").Handler(promhttp.Handler())
router.Path("/setloglevel/{level}").
    Handler(log.NewSetLoglevelHandler(ctx, log.NewLogLevelSetter(2, 5*time.Minute)))
router.Path("/gc").Handler(libhttp.NewGarbageCollectorHandler())
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

### RULE go-http-service/admin-port-9090 (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: a Go service's admin HTTP server (the one serving `/healthz`, `/metrics`, etc.) defaults to a port other than `9090` — either hardcoded or via a `--listen` flag/env-var whose default isn't `:9090`.
**Enforcement**: `rules/go/admin-port-9090.yml` flags `field_declaration` nodes named `Listen` whose struct tag contains a `default:"..."` value that is not `":9090"`. Fields with no default tag are not caught mechanically — the agent handles those during full struct inspection.
**Why**: 9090 is the cross-service contract for the admin endpoint. Prometheus scrape configs, the gateway's `admin/port: '9090'` annotation, the operator's muscle memory for `kubectl port-forward 9090`, and shared tooling all assume it. A custom port per service breaks scrape configs (Prometheus probes the wrong port → no metrics), breaks the gateway's auto-routing (admin URL doesn't resolve), and forces every operator to look up the per-service port before they can curl an endpoint at 3am. The deviation cost is real; the standardisation cost is zero.

#### Bad

```go
type application struct {
	Listen string `required:"false" arg:"listen" env:"LISTEN" default:":8080"` // custom port
}
```

#### Good

```go
type application struct {
	Listen string `required:"false" arg:"listen" env:"LISTEN" default:":9090"`
}
```

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
