# Node Service Guide

How to build a long-running Node.js backend service: project layout, configuration, logging, health endpoints, metrics, graceful shutdown, and the couplings between the source and its Kubernetes manifest.

## Goal

Every Node service is a container in Kubernetes, scraped by Prometheus and supervised by liveness and readiness probes. This guide defines the contract that makes a service operable in that environment. New services copy the structure; the rules below are what review enforces.

Scope: backend services. Frontend applications (Vue, Astro) have their own guides.

Assumed stack: Node 22+, express 5, `prom-client`, the built-in `node:test` runner, eslint flat config plus prettier.

## Project Layout

```
src/
├── index.js          entrypoint — wiring, signals, lifecycle
├── config.js         environment parsed once, validated
├── log.js            structured logging
├── server.js         express app factory
└── handlers/         route handlers (flat in src/ until 3+ exist)
test/
k8s/
```

Keep handlers flat in `src/` while there are fewer than three; introduce `src/handlers/` once the directory earns it. This is layout preference, not a rule — no failure mode rides on it.

## Configuration

Environment is read **once, at startup, in one module**. Everything downstream receives the resolved object.

```js
'use strict';

const config = {
  host: process.env.HOST || '0.0.0.0',
  port: parseInt(process.env.PORT || '8080', 10),
  logLevel: (process.env.LOG_LEVEL || 'info').toLowerCase(),

  // Must stay below the pod's terminationGracePeriodSeconds, or the pod is
  // SIGKILLed mid-drain.
  shutdownTimeoutMs: parseInt(process.env.SHUTDOWN_TIMEOUT_MS || '10000', 10),

  // Injected at image build time; surfaced on /version so a running pod can be
  // traced back to a commit.
  build: {
    version: process.env.BUILD_GIT_VERSION || 'dev',
    commit: process.env.BUILD_GIT_COMMIT || 'none',
    date: process.env.BUILD_DATE || 'unknown',
  },
};

/** Collect every problem, so one restart surfaces all of them. */
config.check = () => {
  const problems = [];
  if (!Number.isInteger(config.port) || config.port < 1 || config.port > 65535) {
    problems.push(`invalid PORT: ${process.env.PORT}`);
  }
  if (!config.apiKey) problems.push('API_KEY is not set');
  return problems;
};

module.exports = config;
```

The entrypoint calls it before anything else starts:

```js
const problems = config.check();
if (problems.length > 0) {
  for (const p of problems) log.error('invalid configuration', { problem: p });
  process.exit(1);
}
```

### RULE node/config/env-read-at-boundary (MUST)

**Owner**: node-quality-assistant
**Applies when**: `process.env` is read outside the configuration module — in a handler, a service class, or any module other than `config.js`. Hand-run diagnostics under `tools/` or `scripts/` are exempt; they have no config module to route through.
**Enforcement**: `rules/node/env-read-at-boundary.yml` (JavaScript) and `rules/node/env-read-at-boundary-ts.yml` (TypeScript) flag `process.env.<VAR>` access; config, entrypoint, tooling-config, `tools/`, `scripts/` and test files are excluded in the rule. The agent confirms the reading module is not itself a bootstrap module.
**Trigger**: **/*.js, **/*.ts
**Why**: environment scattered through modules makes the service's real configuration surface impossible to enumerate, defeats fail-fast validation (a typo in a rarely-hit code path fails in production rather than at boot), and makes tests depend on ambient process state instead of an injected value.

#### Bad

```js
function createOrderHandler() {
  return async (req, res) => {
    // Read on every request; a missing value fails here, not at startup.
    const timeout = parseInt(process.env.ORDER_TIMEOUT_MS || '5000', 10);
    res.json(await fetchOrder(req.params.id, timeout));
  };
}
```

#### Good

```js
function createOrderHandler({ orderTimeoutMs }) {
  return async (req, res) => {
    res.json(await fetchOrder(req.params.id, orderTimeoutMs));
  };
}
```

### RULE node/config/validate-before-serving (MUST)

**Owner**: node-quality-assistant
**Applies when**: the configuration module exports no validation function, or the entrypoint starts the server without calling it and exiting non-zero on failure.
**Enforcement**: judgment — the agent reads `config.js` for an exported validator and the entrypoint for a call preceding `listen`.
**Trigger**: **/*.js, **/*.ts
**Why**: a service that boots with bad configuration and dies on its first real request is worse than one that refuses to start — Kubernetes reports the second as `CrashLoopBackOff` with a clear log line, while the first passes its probes and silently serves errors. Returning a list rather than throwing on the first problem means one restart cycle reveals every misconfiguration instead of one per attempt.

#### Bad

```js
// Throws at import time: dies before logging is configured, reports only the
// first problem, and makes the module awkward to require in a test.
if (!process.env.API_KEY) throw new Error('API_KEY is not set');
```

#### Good

```js
config.check = () => {
  const problems = [];
  if (!config.apiKey) problems.push('API_KEY is not set');
  if (!config.databaseUrl) problems.push('DATABASE_URL is not set');
  return problems;
};
```

### RULE node/config/data-not-behaviour (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: the configuration module exports domain predicates or business logic (for example an authorisation check) alongside its values. A `check()` validator is exempt — it validates the config itself.
**Enforcement**: judgment — the agent inspects exported function properties on the config object and classifies each as validation or domain logic.
**Trigger**: **/*.js, **/*.ts
**Why**: configuration is a value. Once it carries behaviour, every consumer of that behaviour depends on the whole config object, and faking it in a test means constructing a config rather than passing a function. Domain predicates belong in the module that owns the concern.

#### Bad

```js
config.isAllowed = (userId) => config.allowedUserIds.includes(userId);
module.exports = config;
```

#### Good

```js
// src/authorization.js
function createAuthorizer({ allowedUserIds }) {
  return { isAllowed: (userId) => allowedUserIds.includes(userId) };
}
```

## Logging

Structured JSON, one object per line — what log aggregators parse and what `kubectl logs | jq` reads.

```js
const LEVELS = { error: 0, warn: 1, info: 2, debug: 3 };
const threshold = LEVELS[config.logLevel] ?? LEVELS.info;

function emit(level, msg, fields = {}) {
  if (LEVELS[level] > threshold) return;
  const line = JSON.stringify({ ts: new Date().toISOString(), level, msg, ...fields });
  (level === 'error' || level === 'warn' ? process.stderr : process.stdout).write(line + '\n');
}
```

### RULE node/logging/structured-not-console (MUST)

**Owner**: node-quality-assistant
**Applies when**: `console.log`, `console.error`, or `console.warn` is called in service code under `src/`. Diagnostic scripts under `tools/` or `scripts/` are exempt — a terminal is their interface.
**Enforcement**: `rules/node/structured-not-console.yml` (JavaScript) and `rules/node/structured-not-console-ts.yml` (TypeScript) flag `console.<method>` calls; `tools/`, `scripts/`, and test files are excluded in the rule. The agent confirms the file is service code.
**Trigger**: src/**/*.js, src/**/*.ts
**Why**: `console.log` emits unstructured text interleaved into the same stream as structured records, so a single line breaks log-aggregation parsing for the whole stream. It also carries no level, which means it cannot be filtered in production and cannot be suppressed when a service gets noisy.

#### Bad

```js
console.log('order created', order.id);
```

#### Good

```js
log.info('order created', { orderId: order.id });
```

### RULE node/logging/errors-to-stderr (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: the logging module writes every level to the same stream, rather than sending `error` and `warn` to stderr and the rest to stdout.
**Enforcement**: judgment — the agent reads the log module's write target selection.
**Trigger**: **/*.js, **/*.ts
**Why**: keeping the streams separate preserves the distinction end to end — `kubectl logs` can show only stderr, container runtimes and log shippers can route the two differently, and a human tailing a busy service can see failures without filtering. Collapsing both into stdout throws away a signal that costs nothing to keep.

## Health Endpoints

Liveness and readiness answer **different questions**, and conflating them causes outages.

| Endpoint | Question | Failure consequence | May check dependencies? |
|---|---|---|---|
| `/healthz` | Is this process alive? | Kubernetes **restarts** the pod | **No** |
| `/readiness` | Should this pod receive traffic? | Pod removed from Service endpoints | Yes |
| `/version` | What is running? | — | — |

```js
router.get('/healthz', (_req, res) => res.json({ status: 'ok' }));

router.get('/readiness', (_req, res) => {
  const ready = isReady();
  // 503 (not 500) is what makes Kubernetes drain rather than restart.
  res.status(ready ? 200 : 503).json({ status: ready ? 'ready' : 'not-ready' });
});
```

The transport is not prescribed. An express service mounts a router; a worker or bot with no HTTP surface can serve the same three endpoints from `node:http` rather than taking on express for three routes. What is prescribed is the **contract**: the paths, the status codes, and the dependency rule.

### RULE node/health/liveness-has-no-dependencies (MUST)

**Owner**: node-quality-assistant
**Applies when**: the `/healthz` handler queries a database, calls an external service, checks a connection state, or otherwise depends on anything outside the process.
**Enforcement**: judgment — the agent traces the liveness handler body for I/O and external calls.
**Trigger**: **/*.js, **/*.ts
**Why**: a liveness failure makes Kubernetes restart the pod. If liveness checks a dependency, an outage in that dependency restarts every replica simultaneously — converting a partial degradation into a total one, and adding a reconnect storm to whatever was already failing. Dependency state belongs in readiness, where failure only drains traffic.

#### Bad

```js
router.get('/healthz', async (_req, res) => {
  await db.ping();                      // a database blip now restarts every pod
  res.json({ status: 'ok' });
});
```

#### Good

```js
router.get('/healthz', (_req, res) => res.json({ status: 'ok' }));

router.get('/readiness', async (_req, res) => {
  const ready = await db.ping().then(() => true).catch(() => false);
  res.status(ready ? 200 : 503).json({ status: ready ? 'ready' : 'not-ready' });
});
```

### RULE node/health/readiness-returns-503 (MUST)

**Owner**: node-quality-assistant
**Applies when**: the readiness handler signals not-ready with a status other than 503 — typically 500.
**Enforcement**: judgment — the agent reads the readiness handler for the status code used on the not-ready branch. A mechanical detector is planned.
**Trigger**: **/*.js, **/*.ts
**Why**: 503 tells Kubernetes the pod is temporarily unable to serve, so it is removed from Service endpoints and left running. 500 reads as an application fault, and combined with a liveness probe on the same path it escalates a transient dependency problem into a restart loop.

## Metrics

Every service exposes `/metrics`. Services run in Kubernetes with Prometheus scraping them; a service without metrics is unobservable in production.

```js
const registry = new client.Registry();
client.collectDefaultMetrics({ register: registry });

const httpRequests = new client.Counter({
  name: 'http_requests_total',
  help: 'HTTP requests by method, route and status',
  labelNames: ['method', 'route', 'status'],
  registers: [registry],
});

app.use((req, res, next) => {
  res.on('finish', () => {
    // req.route is undefined for 404s; falling back to the raw path would give
    // unbounded label cardinality, so bucket them as "unmatched".
    const route = req.route?.path || (res.statusCode === 404 ? 'unmatched' : req.path);
    httpRequests.inc({ method: req.method, route, status: res.statusCode });
  });
  next();
});
```

### RULE node/metrics/service-exposes-metrics (MUST)

**Owner**: node-quality-assistant
**Applies when**: a long-running service has no `/metrics` route, or no `prom-client` dependency in `package.json`.
**Enforcement**: judgment — the agent checks `package.json` for `prom-client` and the route table for a `/metrics` registration. One-shot CLI tools and scripts are exempt.
**Trigger**: package.json, src/**/*.js, src/**/*.ts
**Why**: services deploy to Kubernetes with Prometheus scraping them. Without `/metrics` there is no request rate, no error rate, no latency distribution and no saturation signal — the service cannot be alerted on, and an incident is diagnosed by reading logs by hand. The endpoint costs a handful of lines, and a service that already serves health endpoints has the HTTP surface for free.

### RULE node/metrics/bounded-label-cardinality (MUST)

**Owner**: node-quality-assistant
**Applies when**: a metric label is populated from a raw request path, a user identifier, or any other unbounded value rather than a matched route pattern.
**Enforcement**: judgment — the agent checks metric label values for `req.path`, `req.url`, or `req.originalUrl` used without a bounding fallback. A mechanical detector is planned.
**Trigger**: **/*.js, **/*.ts
**Why**: Prometheus creates one time series per unique label combination. A raw path label means every 404 against a scanned URL creates a permanent series, and a single crawler can exhaust the scrape target's memory and take the monitoring stack down with it. Use the matched route pattern, and bucket unmatched requests under a constant.

#### Bad

```js
httpRequests.inc({ method: req.method, route: req.path, status: res.statusCode });
```

#### Good

```js
const route = req.route?.path || (res.statusCode === 404 ? 'unmatched' : req.path);
httpRequests.inc({ method: req.method, route, status: res.statusCode });
```

### RULE node/metrics/own-registry (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: metrics are registered on `prom-client`'s global default registry instead of an explicitly constructed `client.Registry()`.
**Enforcement**: judgment — the agent checks whether metrics are constructed with an explicit `registers` option against an owned registry, or fall through to the global default. A mechanical detector is planned.
**Trigger**: **/*.js, **/*.ts
**Why**: the global registry is process-wide shared state. Two test cases registering the same metric name throw a duplicate-registration error, forcing tests to run in isolation or clear global state between them. An owned registry is passed explicitly and disposed with the app.

## Graceful Shutdown

The ordering matters and is the whole point.

```js
let ready = true;

function shutdown(signal) {
  log.info('shutting down', { signal });
  ready = false; // fail readiness FIRST, keep serving in-flight traffic

  const timer = setTimeout(() => {
    log.error('graceful shutdown timed out, forcing exit');
    process.exit(1);
  }, config.shutdownTimeoutMs);
  timer.unref(); // don't let the timer itself hold the process open

  server.close((err) => {
    clearTimeout(timer);
    process.exit(err ? 1 : 0);
  });
}

for (const sig of ['SIGTERM', 'SIGINT']) process.on(sig, () => shutdown(sig));
```

### RULE node/lifecycle/readiness-fails-before-close (MUST)

**Owner**: node-quality-assistant
**Applies when**: the signal handler calls `server.close()` without first flipping the readiness flag to false.
**Enforcement**: judgment — the agent reads the shutdown path for the ordering of the readiness mutation relative to `server.close()`.
**Trigger**: **/*.js, **/*.ts
**Why**: Kubernetes sends SIGTERM and removes the pod from Service endpoints concurrently, not in sequence. Closing the listener immediately refuses connections that were routed in during that window, surfacing as connection-reset errors to clients on every single deploy. Failing readiness first gives the endpoint controller time to stop sending traffic while in-flight requests still complete.

#### Bad

```js
process.on('SIGTERM', () => {
  server.close(() => process.exit(0));  // requests already in flight are refused
});
```

#### Good

```js
process.on('SIGTERM', () => {
  ready = false;
  server.close(() => process.exit(0));
});
```

### RULE node/lifecycle/handles-sigterm (MUST)

**Owner**: node-quality-assistant
**Applies when**: a long-running service registers no `SIGTERM` handler.
**Enforcement**: judgment — the agent checks entrypoint files containing a `listen` call for a `SIGTERM` handler registration. A mechanical detector is planned.
**Trigger**: src/**/*.js, src/**/*.ts
**Why**: without a handler, SIGTERM kills the process immediately and every in-flight request is dropped on each rollout, node drain, and scale-down. SIGINT should share the same path so local `Ctrl-C` exercises the production shutdown behaviour rather than a different one.

### RULE node/lifecycle/crash-on-unhandled-rejection (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: `unhandledRejection` or `uncaughtException` is handled by logging and continuing, rather than logging and exiting non-zero.
**Enforcement**: `rules/node/unhandled-rejection-exits.yml` (JavaScript) and `rules/node/unhandled-rejection-exits-ts.yml` (TypeScript) match `process.on("unhandledRejection"|"uncaughtException", ...)` whose handler contains no `process.exit`.
**Trigger**: **/*.js, **/*.ts
**Why**: after an uncaught exception the process is in an unknown state — a request may be half-written, a transaction half-applied, a lock still held. Continuing produces corruption that is far harder to diagnose than a restart. In Kubernetes a crash is cheap and observable: the pod restarts, the restart count increments, and an alert can fire on it.

### RULE node/lifecycle/shutdown-timer-unref (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: the shutdown forced-exit timer is created without `.unref()`.
**Enforcement**: judgment — the agent checks the shutdown timer for an `.unref()` call. A mechanical detector is planned.
**Trigger**: **/*.js, **/*.ts
**Why**: a referenced timer keeps the event loop alive for its full duration. If the server closes quickly the process still lingers until the timeout elapses, turning a fast shutdown into one that always takes the maximum grace period — and on a rolling deploy that delay multiplies across every pod.

## Error Handling

Express recognises an error handler **by arity** — four parameters, always.

```js
// Four args — Express only treats this as an error handler with the arity.
app.use((err, _req, res, _next) => {
  log.error('unhandled request error', { error: err.message, stack: err.stack });
  res.status(500).json({ error: 'internal server error' });
});
```

### RULE node/http/error-handler-arity (MUST)

**Owner**: node-quality-assistant
**Applies when**: a middleware intended as an error handler is registered with fewer than four parameters.
**Enforcement**: judgment — the agent checks `app.use` callbacks whose first parameter is named `err` or `error` for four declared parameters. A mechanical detector is planned.
**Trigger**: **/*.js, **/*.ts
**Why**: express distinguishes error middleware from ordinary middleware purely by parameter count. A three-parameter function is silently registered as normal middleware, so it never receives errors, and every failure falls through to express's default handler — which leaks a stack trace to the client in development mode and produces an HTML response from a JSON API.

### RULE node/http/explicit-body-limit (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: `express.json()` or `express.urlencoded()` is mounted without an explicit `limit`.
**Enforcement**: `rules/node/express-body-limit.yml` (JavaScript) and `rules/node/express-body-limit-ts.yml` (TypeScript) match `express.json()` / `express.urlencoded()` called with no arguments.
**Trigger**: **/*.js, **/*.ts
**Why**: the default limit is 100kb, which is either too permissive or too restrictive for most services and is invisible either way. Stating it makes the service's accepted request size a reviewed decision rather than a framework default nobody checked, and it is the cheapest available guard against memory exhaustion from oversized bodies.

## Testing

The built-in runner, no framework.

```js
const test = require('node:test');
const assert = require('node:assert');

/** Start the app on an ephemeral port so tests never collide. */
function withServer(app, fn) {
  return new Promise((resolve, reject) => {
    const server = app.listen(0, '127.0.0.1', async () => {
      const base = `http://127.0.0.1:${server.address().port}`;
      try {
        await fn(base);
        resolve();
      } catch (e) {
        reject(e);
      } finally {
        server.close();
      }
    });
  });
}

test('readiness returns 503 when not ready, so k8s drains instead of restarting', async () => {
  await withServer(createApp({ isReady: () => false }), async (base) => {
    assert.equal((await fetch(`${base}/readiness`)).status, 503);
  });
});
```

Two conventions worth keeping:

- **Ephemeral ports.** `listen(0)` lets the OS assign a free port, so parallel tests and a running local instance never collide with a hardcoded one.
- **Name the reason, not the mechanic.** `'readiness returns 503 when not ready, so k8s drains instead of restarting'` records why the assertion exists. When someone later "simplifies" it to 500, the test name argues back.

### RULE node/test/ephemeral-port (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: a test starts a server on a hardcoded port.
**Enforcement**: judgment — the agent checks `listen(...)` calls in test files for a hardcoded non-zero port. A mechanical detector is planned.
**Trigger**: test/**/*.js, test/**/*.ts, **/*.test.js, **/*.test.ts
**Why**: a fixed port makes the suite fail when a local instance is already running, and makes two test files unable to run concurrently. The failure presents as a flaky `EADDRINUSE` unrelated to the code under test, which is expensive to diagnose relative to passing `0`.

## Dependency Injection

The app factory takes its dependencies as arguments rather than reaching for module-level state.

```js
function createApp({ isReady } = {}) { /* ... */ }
```

### RULE node/architecture/inject-dependencies (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: an app or handler factory reads mutable module-level state instead of accepting it as a parameter.
**Enforcement**: judgment — the agent checks factory functions for references to module-scope mutable bindings.
**Trigger**: src/**/*.js, src/**/*.ts
**Why**: injected dependencies let a test drive the exact state it needs — a readiness check that returns false, a clock fixed to a known time — without mutating globals and restoring them afterwards. Module-level state also forces test files into a shared-fixture ordering dependency, where one test's mutation leaks into the next.

## Kubernetes Couplings

Two invariants span the source and the manifest, so neither file can be reviewed correctly alone. See `k8s-manifest-guide.md` for generic manifest concerns (security context, resource limits, probe shape); only the node-specific couplings live here.

```yaml
metadata:
  annotations:
    prometheus.io/scrape: 'true'
    prometheus.io/port: '8080'
    prometheus.io/path: /metrics
spec:
  # Must exceed SHUTDOWN_TIMEOUT_MS, or the pod is SIGKILLed mid-drain.
  terminationGracePeriodSeconds: 30
```

### RULE node/k8s/scrape-annotation-matches-metrics (MUST)

**Owner**: node-quality-assistant
**Applies when**: a Deployment is annotated `prometheus.io/scrape: 'true'` while the service exposes no `/metrics` route, or the service exposes `/metrics` while the Deployment carries no scrape annotation.
**Enforcement**: judgment — the agent cross-references the manifest annotations against the route table.
**Trigger**: k8s/**/*.yaml, src/**/*.js, src/**/*.ts
**Why**: the two halves fail silently in opposite directions. An annotation without an endpoint makes Prometheus log scrape errors for a target that will never answer; an endpoint without an annotation means the metrics are computed, exported, and never collected — the service looks instrumented right up until someone needs a dashboard during an incident.

### RULE node/k8s/grace-period-exceeds-shutdown-timeout (MUST)

**Owner**: node-quality-assistant
**Applies when**: `terminationGracePeriodSeconds` in the Deployment is less than or equal to the service's `SHUTDOWN_TIMEOUT_MS` default or configured value.
**Enforcement**: judgment — the agent compares the manifest value against the config default and any env override in the same manifest.
**Trigger**: k8s/**/*.yaml
**Why**: the grace period is the hard deadline before SIGKILL. If the application's own drain timeout is equal or longer, the pod is killed part-way through draining and the graceful shutdown path never completes — so all the shutdown-ordering work above is discarded on every deploy, and the symptom (occasional reset connections during rollouts) looks like a networking problem rather than a configuration one.

## TypeScript

New services are TypeScript; the rules above apply unchanged to `.ts` sources. Node runs `.ts` directly by stripping type annotations, so no build step is required — but stripping does **not** type-check, so `tsc --noEmit` must run in `make check` or the annotations are decoration. Prefer erasable syntax (string-literal unions over `enum`, explicit field assignment over constructor parameter properties) so the no-build-step property holds.

## Related

- `node-makefile-commands.md` — build, test, and check targets
- `k8s-manifest-guide.md` — generic manifest conventions
- `go-http-service-guide.md` — the equivalent contract in Go
- `vue3-typescript-frontend-guide.md` — frontend applications
