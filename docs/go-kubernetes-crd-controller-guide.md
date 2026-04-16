# Go Kubernetes CRD Controller Guide

How to define and consume a Kubernetes Custom Resource Definition (CRD) in a Go service. This pattern is used in production across multiple bborbe Go services including [`bborbe/alert`](https://github.com/bborbe/alert), [`bborbe/cqrs/cdb`](https://github.com/bborbe/cqrs), and [`bborbe/cqrs/raw`](https://github.com/bborbe/cqrs).

## 0. Before you start — use `bborbe/k8s`

[`github.com/bborbe/k8s`](https://github.com/bborbe/k8s) provides generic primitives that eliminate most of the boilerplate in sections 5–6 of this guide:

- `k8s.Type` — interface your types implement (`Equal`, `Identifier`, `Validate`, `String`)
- `k8s.EventHandler[T Type]` — typed event handler interface (`OnAdd` / `OnUpdate` / `OnDelete` / `Get`)
- `k8s.NewEventHandler[T Type]()` — generic thread-safe in-memory store
- `k8s.NewResourceEventHandler[T Type](ctx, handler)` → `cache.ResourceEventHandler` adapter

If your service already depends on `bborbe/k8s` (most do), use these instead of hand-writing the store and adapter. The hand-written skeletons in sections 5–6 are documented only for services that cannot take the dependency.

## 1. When to use this pattern

Use a CRD when:
- Configuration or state is declarative and managed via `kubectl apply`
- External actors (humans, CI, other controllers) need to add/remove entries without redeploying the service
- The service must react to changes (add/update/delete) without a restart

Do NOT use this pattern when:
- Config is static and only changes with deployments (use env vars or ConfigMap)
- You need transactional semantics across many entries (use a database)
- The data is high-cardinality or high-churn (CRDs are stored in etcd — keep under ~1000 entries)

## 2. Repository layout

### CRD library (types + generated client)

Lives in a dedicated package or sub-module. Follows `kubernetes/code-generator` conventions exactly:

```
myservice/
├── k8s/
│   ├── apis/
│   │   └── <group>.example.com/         # your API group, e.g. example.com
│   │       ├── register.go               # const GroupName = "<group>.example.com"
│   │       └── v1/
│   │           ├── doc.go                # +groupName marker
│   │           ├── register.go           # SchemeBuilder, AddToScheme
│   │           ├── types.go              # CR struct + Spec + List + markers
│   │           └── zz_generated.deepcopy.go   # GENERATED
│   └── client/                           # GENERATED
│       ├── clientset/versioned/
│       ├── informers/externalversions/
│       ├── listers/
│       └── applyconfiguration/
└── hack/
    ├── boilerplate.go.txt
    ├── tools.go                          # _ "k8s.io/code-generator"
    └── update-codegen.sh                 # invokes client-gen, informer-gen, lister-gen, applyconfiguration-gen, deepcopy-gen
```

**Reference implementations**:
- `github.com/bborbe/alert` (library)
- `github.com/bborbe/cqrs/cdb` + `github.com/bborbe/cqrs/raw` (libraries)

The client must be **generated** via `hack/update-codegen.sh` — do NOT hand-write or use `client-go/dynamic`. The dynamic client is acceptable only when the CR schema is unknown at compile time; that is never the case for a first-party CRD.

### Consumer service (controller/watcher)

```
myservice/
├── main.go
├── k8s/                                   # Deployment manifests (ServiceAccount, RBAC, Deployment)
│   ├── <name>-sa.yaml
│   ├── <name>-clusterrole.yaml
│   ├── <name>-clusterrolebinding.yaml
│   └── <name>-deploy.yaml
└── pkg/
    ├── k8s-connector.go                   # Sets up the informer + self-installs the CRD
    └── factory/factory.go                 # Wiring
```

Nothing else. With `bborbe/k8s`, the event-handler and store files collapse into `k8s.NewEventHandler[T]()` + `k8s.NewResourceEventHandler[T]()` called from the factory. If `bborbe/k8s` is off-limits, add `pkg/event-handler.go` (cast adapter) + `pkg/event-handler-<resource>.go` (typed handler) + `pkg/<resource>-store.go` (state holder) — see the fallbacks in sections 5–6.

**Reference implementations**:
- [`github.com/bborbe/alert`](https://github.com/bborbe/alert) — consumer reacts to alert CRs and dispatches notifications (stateless reactor shape)

## 3. Types package (library side)

### `k8s/apis/<group>.example.com/v1/types.go`

```go
var _ k8s.Type = MyResource{}

// +genclient
// +genclient:noStatus
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

type MyResource struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              MyResourceSpec `json:"spec"`
}

func (r MyResource) Equal(other k8s.Type) bool {
    switch o := other.(type) {
    case MyResource:
        return r.Spec == o.Spec
    case *MyResource:
        return r.Spec == o.Spec
    }
    return false
}

func (r MyResource) Identifier() k8s.Identifier {
    return k8s.Identifier(k8s.BuildName(r.Namespace, r.Name))
}

func (r MyResource) Validate(ctx context.Context) error {
    // return validation errors here; called by the generic store
    return nil
}

func (r MyResource) String() string { return r.Name }

type MyResourceSpec struct {
    Field1 string `json:"field1"`
    Field2 int    `json:"field2"`
}

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

type MyResourceList struct {
    metav1.TypeMeta `json:",inline"`
    metav1.ListMeta `json:"metadata,omitempty"`
    Items           []MyResource `json:"items"`
}
```

Markers are mandatory — `client-gen` and `deepcopy-gen` consume them. The `k8s.Type` methods make the type compatible with `k8s.NewEventHandler[T]()` and `k8s.NewResourceEventHandler[T]`.

### `k8s/apis/<group>.example.com/v1/register.go`

Standard boilerplate — copy from `cqrs/raw` or `alert` and change `GroupName`.

### Code generation setup

The generated client under `k8s/client/` comes from `k8s.io/code-generator`. Copy the following from `bborbe/alert`:

```
myservice/
├── hack/
│   ├── boilerplate.go.txt         # license header for generated files
│   └── update-codegen.sh          # sources vendor/k8s.io/code-generator/kube_codegen.sh
└── Makefile
    └── generatek8s:               # target: bash hack/update-codegen.sh
```

Add to `tools.go`:

```go
import _ "k8s.io/code-generator/cmd/validation-gen"
```

Workflow when types change:

```bash
go mod vendor                      # populate vendor/ (codegen reads from it)
make generatek8s                   # regenerates k8s/client/** and zz_generated.deepcopy.go
make ensure                        # go mod tidy; rm -rf vendor
git add k8s/ && git commit         # generated files are committed
```

`generatek8s` is intentionally **separate from `generate`** (which runs mocks). Codegen is expensive and runs manually — the generated tree is stable day-to-day. Do not add `generatek8s` to `precommit`.

## 4. K8sConnector interface (consumer side)

Every bborbe CRD consumer has this exact interface:

```go
// Package `controller` defines K8sConnector; mock name and filename include
// the `controller` prefix per repo-wide naming convention (see go-mocking-guide.md).
//counterfeiter:generate -o ../mocks/controller-k8s-connector.go --fake-name ControllerK8sConnector . K8sConnector
type K8sConnector interface {
    SetupCustomResourceDefinition(ctx context.Context) error
    Listen(ctx context.Context, resourceEventHandler cache.ResourceEventHandler) error
}

func NewK8sConnector(kubeconfig string) K8sConnector {
    return &k8sConnector{kubeconfig: kubeconfig}
}
```

### `SetupCustomResourceDefinition` — self-install

The service creates/updates its own CRD on startup. **Do NOT ship a separate CRD YAML manifest** — the schema lives in Go code so the service and the CRD stay in lockstep.

```go
func (k *k8sConnector) SetupCustomResourceDefinition(ctx context.Context) error {
    config, err := k.createKubernetesConfig()
    if err != nil { return errors.Wrap(ctx, err, "build k8s config") }
    clientset, err := apiextensionsClient.NewForConfig(config)
    if err != nil { return errors.Wrap(ctx, err, "build apiextensions clientset") }

    existing, err := clientset.ApiextensionsV1().CustomResourceDefinitions().
        Get(ctx, crdName, metav1.GetOptions{})
    if err != nil {
        // Not found → create
        return k.createCrd(ctx, clientset)
    }
    // Found → update spec in place
    return k.updateCrd(ctx, existing, clientset)
}

func createSpec() apiextensionsv1.CustomResourceDefinitionSpec {
    return apiextensionsv1.CustomResourceDefinitionSpec{
        Group: "<group>.bborbe.dev",
        Names: apiextensionsv1.CustomResourceDefinitionNames{
            Kind:     "MyResource",
            ListKind: "MyResourceList",
            Plural:   "myresources",
            Singular: "myresource",
        },
        Scope: "Namespaced",
        Versions: []apiextensionsv1.CustomResourceDefinitionVersion{
            {Name: "v1", Served: true, Storage: true, Schema: /* OpenAPIV3Schema */},
        },
    }
}
```

**Scope**: always `Namespaced` (use namespaces for dev/prod isolation). Cluster-scope is only justified when the resource is genuinely global (nodes, storage classes).

**Schema**: provide a strict OpenAPIV3Schema for first-party CRDs. Use `XPreserveUnknownFields: ptr.To(true)` (from `k8s.io/utils/ptr`) only when the CR wraps arbitrary user content — `bborbe/cqrs/raw` does this because its `Spec` is a marshalled event payload.

**RBAC**: the service account needs `get/create/update/patch` on `customresourcedefinitions.apiextensions.k8s.io` plus `get/list/watch` on the CR group.

### `Listen` — start the informer

```go
func (k *k8sConnector) Listen(ctx context.Context, handler cache.ResourceEventHandler) error {
    config, err := k.createKubernetesConfig()
    if err != nil { return errors.Wrap(ctx, err, "build k8s config") }
    clientset, err := versioned.NewForConfig(config)
    if err != nil { return errors.Wrap(ctx, err, "build clientset") }

    factory := externalversions.NewSharedInformerFactory(clientset, defaultResync)
    _, err = factory.MyGroup().V1().MyResources().Informer().AddEventHandler(handler)
    if err != nil { return errors.Wrap(ctx, err, "add event handler") }

    stopCh := make(chan struct{})
    factory.Start(stopCh)
    select {
    case <-ctx.Done():
    case <-stopCh:
    }
    return nil
}

const defaultResync = 5 * time.Minute
```

`Listen` blocks until context is cancelled. The caller (`service.Run`) manages the lifecycle — usually one goroutine.

## 5. Event handlers

### Preferred: use `bborbe/k8s` generics

If the type implements `k8s.Type` (see section 3), both the typed handler and the `cache.ResourceEventHandler` adapter are one-liners:

```go
// Typed handler with built-in in-memory store:
eventHandler := k8s.NewEventHandler[v1.MyResource]()

// Adapter to the informer:
adapter := k8s.NewResourceEventHandler[v1.MyResource](ctx, eventHandler)

// Read the current set anywhere:
items, _ := eventHandler.Get(ctx)
```

`NewEventHandler[T]` is thread-safe, de-duplicates via `Equal`, and de-allocates on `OnDelete`. `NewResourceEventHandler[T]` does the type cast and logs mismatches with `glog.V(2)`.

### Fallback: hand-written (when you cannot depend on `bborbe/k8s`)

Split into a cast-adapter (untyped) and a domain handler (typed). Use this only if `bborbe/k8s` is off-limits.

```go
// pkg/event-handler-<resource>.go — domain-typed handler
type EventHandlerMyResource interface {
    OnAdd(ctx context.Context, obj v1.MyResource) error
    OnUpdate(ctx context.Context, oldObj, newObj v1.MyResource) error
    OnDelete(ctx context.Context, obj v1.MyResource) error
}

// pkg/event-handler.go — adapter to cache.ResourceEventHandler
func NewEventHandler(ctx context.Context, inner EventHandlerMyResource) cache.ResourceEventHandler {
    return cache.ResourceEventHandlerFuncs{
        AddFunc:    func(obj any) { /* cast *v1.MyResource → inner.OnAdd */ },
        UpdateFunc: func(oldObj, newObj any) { /* cast both → inner.OnUpdate */ },
        DeleteFunc: func(obj any) { /* cast → inner.OnDelete */ },
    }
}
```

Full bodies: see `k8s_resource-event-handler.go` in `bborbe/k8s` — it is exactly what you would write.

## 6. State management

The adapter is stateless. State lives in the typed handler:

- **Stateless reactor** (bborbe/alert, bborbe/cqrs): handler translates CR events into side effects (Kafka commands, k8s resources). No local state.
- **In-memory store** (typical for config-lookup CRDs): use `k8s.NewEventHandler[T]()` — thread-safe, keyed by `Identifier()`, deduplicated via `Equal()`. Query with `handler.Get(ctx)` which returns `[]T`.
- **Durable store**: wrap `k8s.EventHandler[T]` with a custom implementation that writes to a KV DB (e.g. BoltDB, BadgerDB) inside a transaction. Use this when restart must not lose state or when cross-process sharing is needed.

### Lookup pattern

The generic `Get(ctx) ([]T, error)` is the only read API — no indexed lookup. For high-read-rate lookups, maintain an adjacent index or cache one level above the handler:

```go
items, err := eventHandler.Get(ctx)
if err != nil { return errors.Wrap(ctx, err, "get items") }
for _, it := range items {
    if it.Spec.Assignee == target {
        return it, nil
    }
}
return v1.MyResource{}, errors.Wrapf(ctx, ErrNotFound, "assignee %q", target)
```

Linear scan is fine for the small sets CRDs typically hold (<~100). If the set grows, consider a bespoke store that does not use `k8s.NewEventHandler` directly.

### Hand-written fallback (no `bborbe/k8s`)

If you cannot depend on `bborbe/k8s`, write a store behind `sync.RWMutex` with `Put/Delete/Find` + `ErrNotFound` sentinel. Match the `k8s.EventHandler[T]` shape so swapping in is a one-line change later.

## 7. Antipatterns

- **No `Lister` / `Indexer` usage.** The generated `Lister` exists but is not used in this pattern — domain handlers receive typed values directly. A store is simpler to mock and reason about than a cache.
- **No `WaitForCacheSync` on startup.** Informers sync sub-second in practice; waiting adds a failure mode (timeout) without benefit. If a lookup arrives before sync completes, return `ErrNotFound` → caller logs and retries. This is the "eventual consistency" contract all bborbe CRD consumers assume.
- **No separate CRD YAML manifest.** Self-install in `SetupCustomResourceDefinition` so the schema and the service version move together.
- **No `client-go/dynamic` client for first-party CRDs.** Use generated typed clientsets. Dynamic is a fallback for CRDs you do not own.
- **No deadlocks in the store.** The handler runs on the informer's goroutine; a lookup from another goroutine must not call back into the handler.

## 8. Testing

- **K8sConnector**: mock `apiextensionsClient` via `apiextensions-apiserver/pkg/client/clientset/clientset/fake`. Assert `Create` called when CRD absent, `Update` called when present. Inject the fake via a `CRDClientBuilder func(*rest.Config) (apiextensionsclient.Interface, error)` injection point on the connector.
- **Types**: test `Equal`, `Identifier`, `Validate`, `String` with Ginkgo. `Equal` must cover both `T` and `*T` paths.
- **Handler (bborbe/k8s)**: `k8s.NewEventHandler[T]()` has its own coverage in the library — no extra tests needed. Write integration-style specs that assert `Get(ctx)` returns the expected set after a sequence of `OnAdd/OnUpdate/OnDelete` calls.
- **Handler (hand-written fallback)**: Counterfeiter-mock dependencies; table-driven Ginkgo specs for each event; include a concurrent-access test (100 goroutines) and a `Find(unknown)` → `ErrNotFound` case.

## 9. Factory wiring

`pkg/factory/factory.go` (with `bborbe/k8s`):

```go
func CreateK8sConnector(kubeconfig string) pkg.K8sConnector {
    return pkg.NewK8sConnector(kubeconfig)
}

func CreateEventHandler() k8s.EventHandler[v1.MyResource] {
    return k8s.NewEventHandler[v1.MyResource]()
}

func CreateResourceEventHandler(ctx context.Context, inner k8s.EventHandler[v1.MyResource]) cache.ResourceEventHandler {
    return k8s.NewResourceEventHandler[v1.MyResource](ctx, inner)
}
```

Factory contains zero logic — see [go-factory-pattern.md](./go-factory-pattern.md).

## 10. `main.go` integration

```go
func (a *application) Run(ctx context.Context, sentry libsentry.Client) error {
    connector := factory.CreateK8sConnector("")  // in-cluster
    if err := connector.SetupCustomResourceDefinition(ctx); err != nil {
        return errors.Wrap(ctx, err, "setup CRD")
    }
    eventHandler := factory.CreateEventHandler()              // k8s.EventHandler[v1.MyResource]
    adapter := factory.CreateResourceEventHandler(ctx, eventHandler)

    return run.All(ctx,
        func(ctx context.Context) error { return connector.Listen(ctx, adapter) },
        // ... other services call eventHandler.Get(ctx) to read current set ...
    )
}
```

The informer runs in its own goroutine; lookup consumers run in theirs. Cancellation of `ctx` stops both. Consumers that need typed lookups hold the `k8s.EventHandler[v1.MyResource]` reference and call `Get(ctx)` directly — no separate store interface is needed.

## 11. Checklist

- [ ] `k8s/apis/<group>.bborbe.dev/v1/types.go` with `+genclient` + `+genclient:noStatus` + deepcopy markers
- [ ] CR type implements `k8s.Type` (`Equal`, `Identifier`, `Validate`, `String`) — compile-time assert `var _ k8s.Type = MyResource{}`
- [ ] `hack/update-codegen.sh` + `hack/boilerplate.go.txt` + `tools.go` import of `k8s.io/code-generator/cmd/validation-gen`
- [ ] `Makefile` has `generatek8s` target (NOT in `precommit`); `k8s/client/*` + `zz_generated.deepcopy.go` committed
- [ ] `K8sConnector` interface with `SetupCustomResourceDefinition` + `Listen`; `CRDClientBuilder` injection point for testing
- [ ] Scope = `Namespaced`, strict OpenAPIV3Schema (unless wrapping arbitrary payload)
- [ ] RBAC: `customresourcedefinitions` write + CR group get/list/watch
- [ ] `k8s.NewEventHandler[T]()` for state; `k8s.NewResourceEventHandler[T]` for informer adapter — no hand-written store unless `bborbe/k8s` unavailable
- [ ] Counterfeiter mock for connector; integration-style Ginkgo tests over `Get(ctx)`
- [ ] `service.Run`-managed informer lifecycle
- [ ] No `Lister`, no `WaitForCacheSync`, no separate CRD YAML, no hand-written clientset

## 12. References

Production examples to copy-adapt:

| Repository | Role | Notes |
|------------|------|-------|
| [`github.com/bborbe/alert`](https://github.com/bborbe/alert) | Library + consumer | Types + generated client + stateless-reactor consumer |
| [`github.com/bborbe/cqrs`](https://github.com/bborbe/cqrs) | Library | `cdb` + `raw` modules share the same shape; `raw` uses `XPreserveUnknownFields` for arbitrary payloads |

Related guides:
- [go-factory-pattern.md](./go-factory-pattern.md) — factory wiring rules
- [go-mocking-guide.md](./go-mocking-guide.md) — Counterfeiter directives
- [go-error-wrapping-guide.md](./go-error-wrapping-guide.md) — `errors.Wrapf` / sentinels
