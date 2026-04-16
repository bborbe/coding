# Go Kubernetes CRD Controller Guide

How to define and consume a Kubernetes Custom Resource Definition (CRD) in a Go service. This pattern is used in production across multiple bborbe Go services including [`bborbe/alert`](https://github.com/bborbe/alert), [`bborbe/cqrs/cdb`](https://github.com/bborbe/cqrs), and [`bborbe/cqrs/raw`](https://github.com/bborbe/cqrs).

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
    ├── event-handler.go                   # Adapts cache.ResourceEventHandler → typed domain handler
    ├── event-handler-<resource>.go        # Typed domain handler (OnAdd/OnUpdate/OnDelete with *v1.X)
    ├── <resource>-store.go                # Optional: state holder (in-memory map, KV, DB)
    └── factory/factory.go                 # Wiring
```

**Reference implementations**:
- [`github.com/bborbe/alert`](https://github.com/bborbe/alert) — consumer reacts to alert CRs and dispatches notifications (stateless reactor shape)

## 3. Types package (library side)

### `k8s/apis/<group>.bborbe.dev/v1/types.go`

```go
// +genclient
// +genclient:noStatus
// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

type MyResource struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`
    Spec              MyResourceSpec `json:"spec"`
}

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

Markers are mandatory — `client-gen` and `deepcopy-gen` consume them.

### `k8s/apis/<group>.bborbe.dev/v1/register.go`

Standard boilerplate — copy from `cqrs/raw` or `alert` and change `GroupName`.

## 4. K8sConnector interface (consumer side)

Every bborbe CRD consumer has this exact interface:

```go
//counterfeiter:generate -o ../mocks/k8s-connector.go --fake-name K8sConnector . K8sConnector
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

## 5. Event handlers — two files

Split into a cast-adapter (untyped) and a domain handler (typed). This keeps the domain handler testable with plain struct values instead of `any`.

### `pkg/event-handler-<resource>.go` — domain-typed handler

```go
type EventHandlerMyResource interface {
    OnAdd(ctx context.Context, obj v1.MyResource) error
    OnUpdate(ctx context.Context, oldObj, newObj v1.MyResource) error
    OnDelete(ctx context.Context, obj v1.MyResource) error
}

func NewEventHandlerMyResource(store MyResourceStore) EventHandlerMyResource {
    return &eventHandlerMyResource{store: store}
}

type eventHandlerMyResource struct { store MyResourceStore }

func (e *eventHandlerMyResource) OnAdd(ctx context.Context, obj v1.MyResource) error {
    e.store.Put(obj.Name, convert(obj))
    return nil
}
// OnUpdate, OnDelete similarly
```

### `pkg/event-handler.go` — adapter to `cache.ResourceEventHandler`

```go
func NewEventHandler(ctx context.Context, inner EventHandlerMyResource) cache.ResourceEventHandler {
    return cache.ResourceEventHandlerFuncs{
        AddFunc: func(obj any) {
            typed, ok := obj.(*v1.MyResource)
            if !ok { glog.V(2).Infof("cast failed"); return }
            if err := inner.OnAdd(ctx, *typed); err != nil {
                glog.V(2).Infof("add failed: %v", err)
            }
        },
        UpdateFunc: func(oldObj, newObj any) {
            oldT, ok1 := oldObj.(*v1.MyResource)
            newT, ok2 := newObj.(*v1.MyResource)
            if !ok1 || !ok2 { glog.V(2).Infof("cast failed"); return }
            if err := inner.OnUpdate(ctx, *oldT, *newT); err != nil {
                glog.V(2).Infof("update failed: %v", err)
            }
        },
        DeleteFunc: func(obj any) {
            typed, ok := obj.(*v1.MyResource)
            if !ok { glog.V(2).Infof("cast failed"); return }
            if err := inner.OnDelete(ctx, *typed); err != nil {
                glog.V(2).Infof("delete failed: %v", err)
            }
        },
    }
}
```

The adapter file is boilerplate — the only thing that changes between CRDs is the `*v1.MyResource` type.

## 6. State management

The adapter is stateless. State, when needed, lives in a store injected into the domain handler:

- **Stateless reactor** (bborbe/alert, bborbe/cqrs): handler translates CR events into side effects (Kafka commands, k8s resources). No local state.
- **In-memory store** (typical for config-lookup CRDs): thread-safe `map[key]Value` behind a `sync.RWMutex`. Handler updates on add/update/delete; consumers read via a lookup method.
- **Durable store**: handler writes to a KV DB (e.g. BoltDB, BadgerDB) inside a transaction; consumers query the DB. Use this when restart must not lose state or when cross-process sharing is needed.

### In-memory store skeleton

```go
//counterfeiter:generate -o ../mocks/myresource-store.go --fake-name MyResourceStore . MyResourceStore
type MyResourceStore interface {
    Put(key string, value MyResource)
    Delete(key string)
    Find(ctx context.Context, key string) (MyResource, error)
}

var ErrNotFound = stderrors.New("not found")

type myResourceStore struct {
    mu   sync.RWMutex
    data map[string]MyResource
}

func NewMyResourceStore() MyResourceStore {
    return &myResourceStore{data: map[string]MyResource{}}
}

func (s *myResourceStore) Put(key string, v MyResource) {
    s.mu.Lock(); defer s.mu.Unlock()
    s.data[key] = v
}

func (s *myResourceStore) Delete(key string) {
    s.mu.Lock(); defer s.mu.Unlock()
    delete(s.data, key)
}

func (s *myResourceStore) Find(ctx context.Context, key string) (MyResource, error) {
    s.mu.RLock(); defer s.mu.RUnlock()
    if v, ok := s.data[key]; ok { return v, nil }
    return MyResource{}, errors.Wrapf(ctx, ErrNotFound, "find key %q", key)
}
```

## 7. Antipatterns

- **No `Lister` / `Indexer` usage.** The generated `Lister` exists but is not used in this pattern — domain handlers receive typed values directly. A store is simpler to mock and reason about than a cache.
- **No `WaitForCacheSync` on startup.** Informers sync sub-second in practice; waiting adds a failure mode (timeout) without benefit. If a lookup arrives before sync completes, return `ErrNotFound` → caller logs and retries. This is the "eventual consistency" contract all bborbe CRD consumers assume.
- **No separate CRD YAML manifest.** Self-install in `SetupCustomResourceDefinition` so the schema and the service version move together.
- **No `client-go/dynamic` client for first-party CRDs.** Use generated typed clientsets. Dynamic is a fallback for CRDs you do not own.
- **No deadlocks in the store.** The handler runs on the informer's goroutine; a lookup from another goroutine must not call back into the handler.

## 8. Testing

- **K8sConnector**: mock `apiextensionsClient` via `apiextensions-apiserver/pkg/client/clientset/clientset/fake`. Assert `Create` called when CRD absent, `Update` called when present.
- **EventHandlerMyResource**: pass a Counterfeiter-mocked store; assert `Put(key, value)` / `Delete(key)` called with the right arguments. Test each of OnAdd/OnUpdate/OnDelete.
- **Adapter** (`event-handler.go`): Counterfeiter-mock the domain handler. Assert the adapter calls the typed method when given a `*v1.MyResource`, and logs + returns when given something else.
- **Store**: table-driven Ginkgo specs for Put/Delete/Find. Include a concurrent-access test (100 goroutines) to exercise the RWMutex. Include a `Find(unknown)` → `ErrNotFound` case.

## 9. Factory wiring

`pkg/factory/factory.go`:

```go
func CreateK8sConnector(kubeconfig string) pkg.K8sConnector {
    return pkg.NewK8sConnector(kubeconfig)
}

func CreateMyResourceStore() pkg.MyResourceStore {
    return pkg.NewMyResourceStore()
}

func CreateEventHandlerMyResource(store pkg.MyResourceStore) pkg.EventHandlerMyResource {
    return pkg.NewEventHandlerMyResource(store)
}

func CreateResourceEventHandler(ctx context.Context, inner pkg.EventHandlerMyResource) cache.ResourceEventHandler {
    return pkg.NewEventHandler(ctx, inner)
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
    store := factory.CreateMyResourceStore()
    eventHandler := factory.CreateEventHandlerMyResource(store)
    adapter := factory.CreateResourceEventHandler(ctx, eventHandler)

    return run.All(ctx,
        func(ctx context.Context) error { return connector.Listen(ctx, adapter) },
        // ... other services that read from `store` ...
    )
}
```

The informer runs in its own goroutine; lookup consumers run in theirs. Cancellation of `ctx` stops both.

## 11. Checklist

- [ ] `k8s/apis/<group>.bborbe.dev/v1/types.go` with `+genclient` + `+genclient:noStatus` + deepcopy markers
- [ ] `hack/update-codegen.sh` runs clean; `k8s/client/*` generated
- [ ] `K8sConnector` interface with `SetupCustomResourceDefinition` + `Listen`
- [ ] Scope = `Namespaced`, strict OpenAPIV3Schema (unless wrapping arbitrary payload)
- [ ] RBAC: `customresourcedefinitions` write + CR group get/list/watch
- [ ] `EventHandlerMyResource` domain-typed interface + adapter in separate files
- [ ] Store (if stateful) with RWMutex + `ErrNotFound` sentinel
- [ ] Counterfeiter mocks for connector + store + domain handler
- [ ] Ginkgo tests for all four components
- [ ] `service.Run`-managed informer lifecycle
- [ ] No `Lister`, no `WaitForCacheSync`, no separate CRD YAML

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
