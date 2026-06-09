# Go k8s binary conventions

Every Go binary that runs in a k8s pod (StatefulSet, Deployment, CronJob, ephemeral Job) MUST follow these conventions. Missing pieces produce silent operational failures: probes never pass, Prometheus never scrapes, operators can't tell if the pod is healthy without `kubectlquant logs`.

## TL;DR

| Piece | Required | Why |
|---|---|---|
| `service.Main(ctx, app, &SentryDSN, &SentryProxy)` entry | yes | Sentry init, panic recovery, structured exit |
| `application` struct with `argument` tags | yes | Env binding + CLI args + length-redacted secret display |
| `display:"length"` on every secret field | yes | Logs print "length=42" not the secret itself |
| `Listen` arg defaulting to `:9090` | yes | Convention; matches scrape annotations |
| `/healthz` + `/readiness` HTTP handlers | yes | k8s livenessProbe / readinessProbe target |
| `/metrics` HTTP handler (`promhttp.Handler()`) | yes | Prometheus scrape |
| Probes + ports + `prometheus.io/scrape` annotations in k8s sts/deploy | yes | Without them, scrape silently never happens |
| `run.CancelOnFirstFinish(ctx, work..., httpServer)` | yes | One goroutine exit cancels the others; clean shutdown |
| Auth via `application` struct fields, not `os.Getenv` | yes | Framework handles defaults + validation + redaction |

### RULE go-k8s-binary/secret-fields-need-display-length (MUST)

**Owner**: go-security-specialist
**Applies when**: an `application` struct field in a Go k8s-deployed binary holds secret material (PEM key, OAuth token, password, API key, JWT signing secret) without the `display:"length"` tag — meaning glog / structured-logging dumps of the application config will print the secret value.
**Enforcement**: `rules/go/secret-fields-need-display-length.yml` flags `field_declaration` whose name contains `PEM` / `Token` / `Secret` / `Password` / `Key` / `Credential` and whose tag either lacks `display:"length"` or is absent entirely. The agent dismisses incidental name matches (e.g. `MasterKey` for a non-credential master record).
**Why**: `argument.Parse()` prints the application config at startup. Without `display:"length"`, the secret value lands in stdout / glog / log aggregators — searchable, indexed, and impossible to redact retroactively once the log batch has shipped. `display:"length"` substitutes `length=42` for the value, preserving the "is it set?" signal without the leak. The tag costs zero runtime; the leak costs a credential rotation.

### RULE go-k8s-binary/argument-struct-not-os-getenv (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go k8s-deployed binary calls `os.Getenv("FOO")` to read a config / auth value that's already declared as an `application` struct field bound via `argument` tags.
**Enforcement**: `rules/go/argument-struct-not-os-getenv.yml` flags any `os.Getenv(...)` call expression. `main.go` and `cmd/**` are excluded (early bootstrap is permitted). The agent confirms whether the matching call site duplicates an already-bound struct field.
**Why**: `argument.Parse()` already populates the struct field with the right precedence (CLI flag > env var > default), validates `required:"true"` fields at startup, and redacts via `display:"length"`. Calling `os.Getenv` directly duplicates the env-read, skips the validation, and bypasses the redaction (`os.Getenv("PEM_KEY")` returns the raw secret with no `display:"length"` involvement). Use `a.PEMKey` etc.

## Application struct shape

```go
type application struct {
    SentryDSN   string `required:"false" arg:"sentry-dsn"   env:"SENTRY_DSN"   usage:"SentryDSN"     display:"length"`
    SentryProxy string `required:"false" arg:"sentry-proxy" env:"SENTRY_PROXY" usage:"Sentry Proxy"`

    Listen       string `required:"false" arg:"listen" env:"LISTEN" usage:"HTTP listen address (healthz/readiness/metrics)" default:":9090"`
    Stage        string `required:"true"  arg:"stage"  env:"STAGE"  usage:"Deployment stage (dev|prod)"`

    // Domain-specific fields follow...

    // Secrets MUST carry display:"length" so glog never prints the value:
    PEMKey  string `required:"false" arg:"pem-key" env:"PEM_KEY" usage:"GitHub App PEM key" display:"length"`
    GHToken string `required:"false" arg:"gh-token" env:"GH_TOKEN" usage:"Legacy PAT" display:"length"`
}
```

**Required fields:**
- `SentryDSN`, `SentryProxy` — `service.Main` mutates these pointers; bind once at top.
- `Listen` — drives the HTTP server port; default `:9090` matches Prometheus scrape annotations.
- `Stage` — `dev` / `prod`; routes namespace + frontmatter + secret lookup.

**Tag semantics** (from `github.com/bborbe/argument/v2`):
- `arg:"foo-bar"` — CLI flag `-foo-bar`
- `env:"FOO_BAR"` — env var (k8s injection target)
- `required:"true"` — refuse to start if absent
- `default:"value"` — fallback when not set
- `display:"length"` — log `length=N` instead of value (use on EVERY secret)
- `usage:"…"` — printed by `--help`

## main entry

```go
func main() {
    app := &application{}
    os.Exit(service.Main(context.Background(), app, &app.SentryDSN, &app.SentryProxy))
}
```

`context.Background()` here is the only allowed call in production code per `go-context-cancellation-in-loops.md` § Allowed exceptions. Everywhere else inside `Run(ctx, ...)` use the passed `ctx`.

## Auth: use struct fields, not os.Getenv

```go
// BAD — duplicates the framework's job + skips display:length redaction
func (a *application) resolveAuth(ctx context.Context) (*http.Client, error) {
    appID, _ := strconv.ParseInt(os.Getenv("APP_ID"), 10, 64)
    pemKey := []byte(os.Getenv("PEM_KEY"))
    // ...
}

// GOOD — reads what argument.Parse already populated
func (a *application) resolveAuth(ctx context.Context) (*http.Client, error) {
    pemKey := []byte(a.PEMKey)
    if a.AppID != 0 && a.InstallationID != 0 && len(pemKey) != 0 {
        return factory.CreateGitHubAppClient(ctx, a.AppID, a.InstallationID, pemKey)
    }
    // ...
}
```

`os.Getenv` skips the framework's defaults, type parsing, and length redaction. It also creates an invisible second source of truth that drifts from the struct.

## HTTP server: mandatory triple

Every binary serves three endpoints on `a.Listen`:

```go
func (a *application) runHTTPServer(work run.Func) run.Func {
    return func(ctx context.Context) error {
        router := mux.NewRouter()
        router.Path("/healthz").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/readiness").Handler(libhttp.NewPrintHandler("OK"))
        router.Path("/metrics").Handler(promhttp.Handler())
        // Domain-specific routes (optional):
        // router.Path("/trigger").Handler(...)
        // router.Path("/setloglevel/{level}").Handler(log.NewSetLoglevelHandler(...))
        glog.V(2).Infof("http server listening on %s", a.Listen)
        return libhttp.NewServer(a.Listen, router).Run(ctx)
    }
}
```

- `/healthz` and `/readiness` MUST return 200 unconditionally (binary running = healthy). Keep them trivial; never put database / upstream checks here — those belong in `/metrics` as gauges.
- `/metrics` exposes Prometheus counters / histograms registered via `prometheus.MustRegister(...)`.

## Compose: HTTP + work loop via run.CancelOnFirstFinish

```go
func (a *application) Run(ctx context.Context, _ libsentry.Client) error {
    // ... setup ...
    return run.CancelOnFirstFinish(ctx,
        a.pollLoop(work, interval),    // domain goroutine
        a.runHTTPServer(work),          // HTTP triple
    )
}
```

`run.CancelOnFirstFinish` cancels the others as soon as any goroutine returns. This gives clean shutdown on:
- `ctx.Done()` (k8s SIGTERM) — both goroutines cancel
- HTTP server error — poll loop cancels
- Poll loop returns (one-shot binaries) — HTTP server cancels

## k8s manifest: matching annotations + probes + ports

```yaml
spec:
  template:
    metadata:
      annotations:
        prometheus.io/path: /metrics
        prometheus.io/port: "9090"
        prometheus.io/scheme: http
        prometheus.io/scrape: "true"
    spec:
      containers:
        - name: service
          ports:
            - containerPort: 9090
              name: http
          livenessProbe:
            httpGet:
              path: /healthz
              port: 9090
              scheme: HTTP
            failureThreshold: 5
            initialDelaySeconds: 10
            timeoutSeconds: 5
          readinessProbe:
            httpGet:
              path: /readiness
              port: 9090
              scheme: HTTP
            initialDelaySeconds: 5
            timeoutSeconds: 5
```

**All four are mandatory:**
- `prometheus.io/scrape: "true"` + matching `port`/`path`/`scheme` — without these, Prometheus silently never scrapes
- `containerPort: 9090` named `http` — k8s exposes the port; matching Service routes traffic
- `livenessProbe` — k8s restarts pod if `/healthz` fails
- `readinessProbe` — k8s removes pod from endpoints until `/readiness` passes

## Sibling Service for admin gateway routing

```yaml
apiVersion: v1
kind: Service
metadata:
  name: <service-name>
  namespace: '{{ "NAMESPACE" | env }}'
  annotations:
    admin/port: '9090'
    admin/path: ''
spec:
  clusterIP: None
  selector:
    app: <service-name>
  ports:
    - name: http
      port: 9090
      targetPort: 9090
      protocol: TCP
```

The `admin/port` + `admin/path` annotations are read by the admin gateway (`https://<stage>.quant.benjamin-borbe.de/admin/<service>/<path>`). Without the Service, the admin gateway can't proxy + operators can't hit the binary's HTTP endpoints from outside the cluster.

## Reference implementations

Copy these shapes:

| Binary | Path |
|---|---|
| Long-running watcher | `bborbe/maintainer/watcher/github-pr/main.go` |
| Long-running watcher (state-machine) | `bborbe/maintainer/watcher/github-build/main.go` |
| Pattern B Job (k8s Job per task) | `bborbe/maintainer/agent/pr-reviewer/main.go` |
| Smoke-test one-shot | `bborbe/maintainer/watcher/github-build/cmd/run-once/main.go` |

The one-shot variants skip the HTTP server — they exit on completion, k8s never schedules them long enough to need probes. Everything else MUST follow this guide.

## Common failure modes

| Symptom | Cause |
|---|---|
| Pod restarts every 30s | `/healthz` not implemented; livenessProbe failing |
| Metrics dashboard empty after deploy | Missing `prometheus.io/scrape: "true"` annotation, or wrong port |
| Service routes 404 | `Service` resource missing OR `targetPort` mismatch |
| Secret values leaked in `argument_print` logs | Missing `display:"length"` on secret field |
| Pod runs but `kubectlquant exec ... wget http://localhost:9090/metrics` returns nothing | Binary didn't call `libhttp.NewServer(a.Listen, router).Run(ctx)` |
| Probes fail intermittently in load | `failureThreshold` too low; use `5` for liveness, `3` for readiness |

## Related

- [[go-http-service-guide.md]] — HTTP handler patterns
- [[go-prometheus-metrics-guide.md]] — metric naming + pre-init
- [[go-context-cancellation-in-loops.md]] — context propagation rules (including the `context.Background()` in `main()` exception)
- [[go-glog-guide.md]] — log levels for the v= flag
- [[k8s-manifest-guide.md]] — broader manifest conventions
