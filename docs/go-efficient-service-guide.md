# Go Efficient Service Guide

How to write a Go service that is cheap in CPU and memory from the start, idle time included. Scope is resource efficiency only: CPU, memory, I/O and idle cost. Diagnosing a service that is already too expensive is a separate job: profile it first (section 8), then apply the rules below.

## Goal

Most services sit idle most of the time, so **idle cost is a budget of its own**, equal to peak cost. Every rule here can be answered yes/no from a diff. Baseline is Go 1.23+; version notes are inline.

## 1. Design: Do Less Work

**Subscribe to events; never poll something that can push.** Use Kubernetes watches/informers, Kafka consumption, webhooks, fsnotify or channels. A blocked watch costs ~0 CPU while idle; a poller pays interval × work forever.

**When polling is unavoidable: derive the interval from the freshness the consumer needs, back off on "no change" and on errors, reset on change, add jitter, stop when nobody is interested.**

```go
// Bad: fixed 1s forever, even with zero interest
for range time.Tick(time.Second) { check(ctx) }

// Good: adaptive and stoppable
d := minInterval
t := time.NewTimer(d)
defer t.Stop()
for {
    select {
    case <-ctx.Done():
        return errors.Wrap(ctx, ctx.Err(), "poll cancelled")
    case <-t.C:
    }
    if changed, err := check(ctx); err == nil && changed {
        d = minInterval
    } else {
        d = min(d*2, maxInterval)
    }
    t.Reset(d + rand.N(d/10)) // math/rand/v2; minInterval ≥ 1s keeps d/10 > 0
}
```

**Never spawn a subprocess per request, tick or item.** Use the library behind the CLI. If the CLI is unavoidable, run it once in batch mode. Each `exec` costs fork + exec + runtime init + its own RSS, and fan-out turns a traffic spike into a process storm.

```go
// Bad: a process per item
for _, id := range ids { exec.CommandContext(ctx, "tool", "get", id).Output() }
// Good: one process, many items, or the library call
exec.CommandContext(ctx, "tool", append([]string{"get"}, ids...)...).Output()
```

**Read Kubernetes state from an informer cache, never `List` in a loop.** Run one active replica for controllers and pollers (leader election); standby replicas hold no watches.

**Keep startup cheap.** No heavy work in `init()` or package-level vars; build clients lazily (`sync.OnceValue`) unless the first request needs them.

## 2. Idle Cost

**Block, never spin.** No `for { select { ...; default: } }`, no `time.Sleep` polling loop. A parked goroutine costs a few KiB of stack and zero CPU.

**Every goroutine has an owner and an exit path through `context`.** Start goroutines via `github.com/bborbe/run` or `errgroup`; verify with `go.uber.org/goleak` in tests. Leaked goroutines retain their stacks and everything they reference, and show as steadily rising `go_goroutines`.

**One reused `time.Timer` instead of `time.After` in a loop; `defer t.Stop()` on every Ticker/Timer.** Since Go 1.23 unreferenced timers are garbage-collected even if never stopped, so `time.After` no longer leaks — but it still allocates a timer and channel per iteration, and a live ticker still wakes the scheduler every tick. Coalesce periodic jobs onto one scheduler goroutine and pick the coarsest interval that meets the requirement.

```go
// Bad
for { select { case m := <-msgs: handle(m); case <-time.After(30 * time.Second): flush() } }
// Good
t := time.NewTimer(30 * time.Second)
defer t.Stop()
for {
    select {
    case <-ctx.Done():
        return
    case m := <-msgs:
        handle(m)
    case <-t.C:
        flush()
        t.Reset(30 * time.Second) // flush every 30s regardless of traffic
    }
}
```

**Close what you open, on every path including shutdown:** response bodies, watchers, informers, Kafka readers/writers, `rows`, bbolt/Badger handles. Pass `context.Context` into every blocking call so abandoned work stops.

**Shut down idle resources, not just busy ones.** Set `Transport.IdleConnTimeout`, drop caches nobody read for N minutes, stop watches for tenants no longer in use. Keep informer resync at the default (or longer) and use `RequeueAfter` for objects that need periodic re-checks.

## 3. Memory

**Set `GOMEMLIMIT` to 85–90% of the container memory limit; 70–80% when the service mmaps a lot (bbolt, Badger) or uses cgo.** It is a *soft* limit on memory the Go runtime maps and has not released (roughly `Sys - HeapReleased`). It excludes C allocations and `syscall.Mmap`'d files, so leave headroom for those. As usage approaches the limit the GC runs more often; the GC CPU limiter caps GC at roughly 50% CPU, so the process may exceed the limit and be OOM-killed instead of thrashing. It is a pressure valve, not OOM protection.

**Keep `GOGC=100` for long-running services.** `GOGC=off` does not disable the limit — the limit is respected even with `GOGC=off` — but the heap then grows to the limit before any collection: fine for a batch job with a known peak, wasteful for an idle service.

```yaml
resources:
  requests: {cpu: 50m, memory: 128Mi}
  limits:   {memory: 128Mi}            # memory request == limit
env:
  - {name: GOMEMLIMIT, value: "115MiB"} # ~90% of the limit
```

**Know RSS ≠ heap.** After a spike the heap shrinks at the next GC, but RSS drops only as the scavenger returns pages. Alert on RSS (what the OOM killer sees); debug with heap profiles. Never call `debug.FreeOSMemory()` on a timer.

**Preallocate when the size is known:** `make([]T, 0, n)`, `make(map[K]V, n)`, `strings.Builder.Grow(n)`.

**Keep data in one representation along a path.** Each `[]byte`↔`string` conversion copies, except where the compiler elides it (`m[string(b)]` lookups and `string(b) == "x"` comparisons do not allocate). On hot paths use `strconv.Append*`, `bytes.Buffer`, `strings.Builder` instead of `fmt.Sprintf` and `+=`.

**Use `sync.Pool` only with a benchmark showing fewer allocs and better ns/op.** Pool pointers, `Reset()` before `Put`, and drop oversized buffers (e.g. > 64 KiB) instead of returning them.

**Bound every cache by size *and* age** (LRU with TTL, e.g. `hashicorp/golang-lru/v2/expirable`), and collapse concurrent misses with `singleflight`. An unbounded `map` used as a cache is a memory leak.

```go
// Bad
var cache = map[string]*Order{} // grows forever
// Good
cache := expirable.NewLRU[string, *Order](10_000, nil, 5*time.Minute)
```

**Rebuild long-lived maps after mass deletion.** `delete` and `clear` remove entries; neither is documented to release the map's storage. Copy the live entries into a fresh map sized for them; do not rely on `maps.Clone` to shrink.

```go
func shrink[K comparable, V any](m map[K]V) map[K]V {
    n := make(map[K]V, len(m))
    for k, v := range m {
        n[k] = v
    }
    return n
}
```

**Do not let small slices or strings pin large backing arrays.** `slices.Clone` / `strings.Clone` anything you keep from a large buffer; replace `q = q[1:]` queues with a ring buffer. `slices.Delete` zeroes the vacated tail; hand-rolled deletes from `[]*T` must nil it themselves.

**Do not hold per-request data in long-lived structs** (errors wrapping whole bodies, Sentry scopes, loggers with payloads). Keep IDs.

**Stream, do not slurp.** No `io.ReadAll` / `os.ReadFile` on input of unbounded size. Use `json.Decoder` element by element, `bufio.Scanner`, `io.Copy`, cursors and pagination; cap request bodies with `http.MaxBytesReader`.

```go
dec := json.NewDecoder(http.MaxBytesReader(w, req.Body, 1<<20))
if _, err := dec.Token(); err != nil { return errors.Wrap(ctx, err, "read [") }
for dec.More() {
    var o Order
    if err := dec.Decode(&o); err != nil { return errors.Wrap(ctx, err, "decode order") }
    process(ctx, o)
}
```

**Shrink controller caches:** scope by namespace or label, strip `managedFields` with a cache transform, use metadata-only watches where the spec is not needed.

**Size embedded KV stores explicitly.** Badger's defaults assume a big host: cap `MemTableSize`, `NumMemtables`, `BlockCacheSize`. With bbolt keep read transactions short — a long one blocks page reuse and grows the file and its mmap.

## 4. CPU

**Parse and compile once:** config at startup, `regexp.MustCompile` at package level, templates once. Swap reloaded config via `atomic.Pointer`. Never use `json.Marshal`/`Unmarshal` as a deep copy; pass `[]byte` through when you only forward.

**Batch writes:** one DB transaction per batch, bbolt `db.Batch`, Badger `WriteBatch`, Kafka producer batching, offset commits on an interval rather than per message. Debounce bursts of events before reconciling.

**Bound concurrency.** Never `go f(item)` per item of unbounded input; use `errgroup.SetLimit`, a semaphore, a fixed worker pool, or the `run`/`collection` helpers from [Concurrency Patterns](go-concurrency-patterns.md). CPU-bound: about `GOMAXPROCS` workers. I/O-bound: size to downstream capacity.

```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(8)
for _, o := range orders {
    g.Go(func() error { return process(ctx, o) })
}
return g.Wait()
```

**Guard hot-path logging.** No per-message Info logs in consumers; use `glog.V(n)` guards ([glog](go-glog-guide.md)) and log aggregates. Arguments are evaluated even when the record is dropped.

**Retry with exponential backoff, jitter, a max attempt count and `ctx`.** An uncapped tight retry turns one outage into a CPU and upstream storm.

**No `defer` inside a long loop.** Deferred closes pile up until the function returns; extract the loop body into a function. Count lines in chunks (`bytes.Count`) rather than reading the whole file.

## 5. I/O

**One shared `http.Client` per process or upstream, with a deadline on every call.** `http.DefaultClient` has no timeout. Raise `Transport.MaxIdleConnsPerHost` (default 2) for high fan-out to one host.

**Drain and close every response body**, or the connection is not returned to the keep-alive pool:

```go
defer func() {
    _, _ = io.Copy(io.Discard, io.LimitReader(resp.Body, 64<<10))
    _ = resp.Body.Close()
}()
```

**Set server timeouts:** `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout`, `IdleTimeout`. Zero means never, so dead clients pin goroutines.

**Configure DB pools** (`SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxIdleTime`) so the pool shrinks when the service goes quiet.

**Kill N+1:** `IN (...)`, multi-get, batch APIs, or reads from the informer cache.

**Never rescan on the request path** — no per-request directory walk, `/proc` scan or full `List()`. Watch, or snapshot on a coarse timer and serve from an `atomic.Pointer`.

**Let idle Kafka consumers long-poll:** fetch max-wait in seconds, min-bytes > 1 where latency allows.

## 6. Kubernetes Sizing

**Set requests from measured p95 over ≥ 7 days plus ~20% headroom.** Use VPA in recommend-only mode (`updateMode: "Off"`) or `quantile_over_time(0.95, …)`.

**Memory: request == limit**, limit ≈ peak RSS × 1.2–1.3, then `GOMEMLIMIT` from that limit. Memory is incompressible.

**CPU: measure throttling before setting a limit.** CFS quota is enforced per 100 ms period; once used up, every thread stalls until the next period, which shows as tail latency on an otherwise idle node. For latency-sensitive services keep the request and drop the limit (or set it ≥ 2× request) and alert on throttling > 5%. Since Go 1.25 `GOMAXPROCS` follows the cgroup CPU limit on Linux; with no limit, set `GOMAXPROCS` to about ceil(request), minimum 2. Before Go 1.25 use `go.uber.org/automaxprocs`.

**Choose the workload type by duty cycle:**
- Work runs at most every few minutes and starts quickly → `CronJob` (`concurrencyPolicy: Forbid`, `activeDeadlineSeconds`, `ttlSecondsAfterFinished`), not a sleeping `Deployment`.
- Event-driven, idle for long stretches, cold start acceptable → scale to zero (KEDA on queue lag).
- Needs a warm cache, long-lived watch or leader state → `Deployment` with minimal requests and the idle rules above.

## 7. Observability for Efficiency

**Keep the default Go and process collectors and export:** `process_resident_memory_bytes`, `go_memstats_heap_inuse_bytes`, `go_goroutines`, `go_gc_duration_seconds`, `process_cpu_seconds_total`, `process_open_fds`, and a request or message rate. See [Prometheus Metrics](go-prometheus-metrics-guide.md).

**Write a budget per service** in its README, with idle and active budgets kept separate: idle CPU (millicores), idle RSS, peak RSS, max goroutines, plus a per-workload efficiency ratio — CPU seconds per 1k requests or messages, bytes allocated per request, CPU seconds per reconcile. Budgets come from the measured baseline plus ~20%.

**Alert on sustained deviation from the baseline, not on absolutes:**

```promql
process_resident_memory_bytes > 1.3 * quantile_over_time(0.95, process_resident_memory_bytes[7d] offset 1d)
deriv(go_goroutines[1h]) > 0.05
rate(container_cpu_cfs_throttled_periods_total[5m]) / rate(container_cpu_cfs_periods_total[5m]) > 0.05
```

**Bound Prometheus label cardinality** — no user IDs, raw paths, object names or error strings; every label combination is a live series. **Sample Sentry** (`TracesSampleRate` ≤ 0.05), do not report expected errors, never capture inside retry loops.

**Register pprof handlers only on the admin server** (port 9090, see [HTTP Service](go-http-service-guide.md)), never on the public listener.

## 8. Measurement Discipline

**No optimisation merges without before/after numbers.** Never optimise from one reading.

**Micro-benchmarks:** `b.Loop()` (Go 1.24+) with `-benchmem -count=10`, compared by `benchstat`; accept only deltas benchstat reports as significant. Benchmark on the Go version you deploy — Go 1.26 made the Green Tea garbage collector the default, which shifts GC cost.

```bash
go test -run='^$' -bench=BenchmarkEncode -benchmem -count=10 ./pkg > old.txt
# apply change
go test -run='^$' -bench=BenchmarkEncode -benchmem -count=10 ./pkg > new.txt
benchstat old.txt new.txt
```

**Gate CI on allocations, not nanoseconds** — `testing.AllocsPerRun` is deterministic; ns/op on shared runners is noise.

**Load tests and RSS:** ≥ 3 runs per version, same load, build flags, node type and warm-up; report median and spread. Verify in the container with the real limits.

**Profile, then fix the top entry.** `go tool pprof` on `profile` (CPU), `heap` (`inuse_space` for retention, `alloc_space` for churn) and `goroutine` (leaks). A 60 s CPU profile of an idle pod should be nearly empty — anything in it is idle cost.

## Antipatterns

| Antipattern | Required fix |
|---|---|
| Full rescan (files, pods, processes, table) per request | Watch, or timer snapshot served from memory |
| Unbounded `map` / slice as cache or registry | Size + TTL bound; rebuild after mass deletes |
| `go f(item)` per item of unbounded input | `errgroup.SetLimit` or worker pool |
| `time.After` inside a loop | One `time.Timer`, `Reset` per iteration |
| `time.Tick` in a long-lived loop / ticker held without `Stop()` | `NewTicker` + `defer Stop()` |
| `select { default: }` spin loop | Block on channels and `ctx.Done()` |
| Polling a CLI / `exec` per request | Library, informer, or one batched invocation |
| Fixed-interval poll with no backoff | Backoff + jitter + stop when idle |
| Retry loop without backoff or cap | Exponential backoff + jitter + max attempts + ctx |
| `http.Client{}` per call | One shared client per upstream |
| Response body not drained/closed | `io.Copy(io.Discard, …)` then `Close()` |
| Outbound call without a deadline | `Client.Timeout` or `context.WithTimeout` |
| `io.ReadAll` on unbounded input | `MaxBytesReader` + streaming decoder |
| `os.ReadFile` to count lines | `bufio.Reader` + `bytes.Count` over chunks |
| Regexp / template / YAML parsed per request | Package-level or startup-time, `atomic.Pointer` swap |
| `json.Marshal` + `Unmarshal` as deep copy | Typed copy function |
| Logging per message at Info in hot loops | `glog.V(n)` guard, aggregate counters |
| Small sub-slice of a huge buffer retained | `slices.Clone` the part you keep |
| `defer` inside a long loop | Extract the body into a function |
| High-cardinality Prometheus labels | Bounded labels; detail goes to logs |
| Short informer resync "to be safe" | Default resync + `RequeueAfter` |
| Sleeping `Deployment` for an hourly job | `CronJob` |
| `GOGC=off` in a long-running service | Default `GOGC` + `GOMEMLIMIT` |
| No CPU limit and no `GOMAXPROCS` (pre-1.25) | `GOMAXPROCS` ≈ ceil(request) or `automaxprocs` |

## PR Acceptance Rule

Reject a PR that introduces any of:

1. **Unbounded growth** — a cache, map, queue, slice or goroutine set with no size bound or exit path.
2. **Continuous needless background work** — polling, a ticker, or a watch that runs while nothing changes and has an event-driven or backoff alternative.
3. **Unmeasured performance claims** — a change justified by speed or memory without before/after `benchstat` or ≥ 3-run load numbers.

## Related

- [Concurrency Patterns](go-concurrency-patterns.md) — goroutine ownership, channels
- [glog](go-glog-guide.md) — `V(n)` gating of hot-path logs
- [Context Cancellation in Loops](go-context-cancellation-in-loops.md) — `ctx.Done()` checks
- [HTTP Service](go-http-service-guide.md) — admin port, `/metrics`, `/gc`
- [Prometheus Metrics](go-prometheus-metrics-guide.md) — metric types and labels
- [K8s Manifest Guide](k8s-manifest-guide.md) — resources and env in manifests
