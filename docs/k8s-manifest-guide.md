# Kubernetes Manifest Layout Guide

How to organize Kubernetes YAML manifests in a service repository. Rules only — no rationale padding.

**Reference**: [`github.com/bborbe/go-skeleton/tree/master/k8s`](https://github.com/bborbe/go-skeleton/tree/master/k8s)

## 1. Location

Manifests live in a `k8s/` folder **next to the code they deploy**, not at repo root.

```
myservice/
├── main.go
├── pkg/
├── Dockerfile
├── Makefile
└── k8s/                          # ← here
    ├── Makefile
    ├── myservice-deploy.yaml
    ├── myservice-svc.yaml
    ├── myservice-ing.yaml
    └── myservice-secret.yaml
```

For repos with multiple deployables, each component has its own `k8s/` folder under its own subdirectory. Do not pool unrelated manifests in a shared top-level `k8s/` or `manifests/`.

## 2. One resource per file

**Never** put multiple Kubernetes resources in a single YAML file. No `---` separators. Split them:

```
# ❌ BAD
k8s/myservice.yaml                 # Deployment + Service + Secret in one file

# ✅ GOOD
k8s/myservice-deploy.yaml          # Deployment
k8s/myservice-svc.yaml             # Service
k8s/myservice-secret.yaml          # Secret
```

Single-resource files diff cleanly, apply individually, and grep-locate by filename.

## 3. Filename convention

Format: `<resource-name>-<type-suffix>.yaml`

- `<resource-name>` = the `metadata.name` of the resource (or its logical base for per-tenant/per-env variants)
- `<type-suffix>` = short, kind-specific (see table below)

```
# resource name "order-processor", kind Deployment
order-processor-deploy.yaml

# resource name "user-api", kind Service
user-api-svc.yaml
```

## 4. Type suffixes

Use these exact suffixes. Consistency matters more than verbosity:

| Suffix | Kind | Notes |
|---|---|---|
| `-deploy.yaml` | `Deployment` | |
| `-sts.yaml` | `StatefulSet` | |
| `-svc.yaml` | `Service` | |
| `-ing.yaml` | `Ingress` | |
| `-cronjob.yaml` | `CronJob` | |
| `-job.yaml` | `Job` | |
| `-secret.yaml` | `Secret` | |
| `-cm.yaml` | `ConfigMap` | prefer over `-configmap.yaml` |
| `-sa.yaml` | `ServiceAccount` | |
| `-role.yaml` | `Role` / `ClusterRole` | |
| `-rolebinding.yaml` | `RoleBinding` / `ClusterRoleBinding` | |
| `-netpol.yaml` | `NetworkPolicy` | |
| `-pdb.yaml` | `PodDisruptionBudget` | |
| `-hpa.yaml` | `HorizontalPodAutoscaler` | |
| `-sm.yaml` | `ServiceMonitor` (prometheus-operator) | |
| `-prometheusrule.yaml` | `PrometheusRule` | `-alert.yaml` also acceptable for alert-only rules |

For custom resources, pick a short suffix (≤12 chars) tied to the CRD kind and use it consistently across the repo. If a kind isn't listed, invent an unambiguous short suffix and document it in the repo's README.

## 5. Compound names

For repos where one directory deploys multiple logical components, prefix the type suffix with the component to disambiguate:

```
k8s/
├── myapp-gateway-deploy.yaml
├── myapp-gateway-svc.yaml
├── myapp-gateway-secret.yaml
├── myapp-command-handler-sts.yaml
├── myapp-command-handler-svc.yaml
└── myapp-requester-cronjob.yaml
```

Component names come before the type suffix, never after.

## 6. Per-tenant / per-env variants

When the same logical resource deploys multiple times (e.g. per tenant or environment), use **one template file** with env-substituted names, not N copies:

```yaml
# order-processor-cronjob.yaml
metadata:
  name: order-processor-{{ "TENANT_ID" | env }}
```

The apply loop iterates tenants and renders. Do NOT create `...-tenant-a.yaml` and `...-tenant-b.yaml`.

## 7. Templating placeholders

Anything that varies per environment or deploy uses an env-substituted placeholder, rendered at apply time. The pattern is `{{ "KEY" | env }}`:

```yaml
metadata:
  name: myservice
  namespace: '{{ "NAMESPACE" | env }}'
spec:
  template:
    spec:
      containers:
        - image: '{{"DOCKER_REGISTRY" | env}}/myservice:{{"BRANCH" | env}}'
          env:
            - name: KAFKA_BROKERS
              value: '{{ "KAFKA_BROKERS" | env }}'
```

`NAMESPACE`, `BRANCH`, `DOCKER_REGISTRY` are **examples**, not a fixed list. Use whatever keys the service needs — namespace, image tag, registry, broker endpoints, feature flags, tenant IDs, etc. The apply loop exports them per environment.

Rule: anything that changes between `dev` / `staging` / `prod` (or between tenants) is a placeholder. Nothing that varies is hardcoded.

## 8. Annotations

Only add annotations that a controller actually reads. Common examples:

```yaml
metadata:
  annotations:
    # image auto-update (keel.sh)
    keel.sh/policy: force
    keel.sh/trigger: poll
    keel.sh/match-tag: "true"
    keel.sh/pollSchedule: "@every 1m"
  labels:
    app: myservice
```

```yaml
# Pod template annotations (scraped by Prometheus)
spec:
  template:
    metadata:
      annotations:
        prometheus.io/path: /metrics
        prometheus.io/port: "9090"
        prometheus.io/scheme: http
        prometheus.io/scrape: "true"
```

```yaml
# Ingress annotations (Traefik)
metadata:
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
```

If your org wants owner/description metadata, pick one consistent prefix (e.g. `example.com/owner`) and apply it uniformly — do not mix prefixes across repos.

## 9. Standard Makefile

The `k8s/` Makefile is a thin wrapper over shared Makefile fragments at the repo root — no targets defined inline:

```makefile
include ../Makefile.variables
include ../Makefile.k8s
```

Typical split:

- `Makefile.variables` — resolved at make time (`BRANCH`, `ROOTDIR`, secret-store path)
- `Makefile.k8s` — defines the `apply` (and `applyOne` if per-tenant) targets
- A per-service env file (e.g. `example.env`, `dev.env`) exports the `{{ "KEY" | env }}` placeholder values; the `apply` target sources it before running the templater

The `apply` target typically reads each `*.yaml` in `k8s/`, pipes through a templating/secret-injection tool that resolves `{{ "KEY" | env | <filter> }}` expressions, then `kubectl apply --context=${CLUSTER_CONTEXT} -f -`. Copy these shared fragments from a nearby service rather than writing from scratch.

## 10. Secrets

Never commit raw secret values. Use a secret-templating tool (SOPS, Sealed Secrets, External Secrets Operator, or a custom templater fed by a vault) that resolves values at apply time:

```yaml
apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: myservice
  namespace: '{{ "NAMESPACE" | env }}'
data:
  sentry-dsn: '{{ "SENTRY_DSN_KEY" | env | vaultLookup | base64 }}'
  api-key:    '{{ "API_KEY" | env | base64 }}'
```

Exact filter functions (`vaultLookup`, `sopsDecrypt`, etc.) depend on your tool. The rule: secret values come from a vault at apply time, never from the YAML in git.

## 11. Deployment image tag

Always pin via `BRANCH` env, never hardcode:

```yaml
image: '{{"DOCKER_REGISTRY" | env}}/myservice:{{"BRANCH" | env}}'
imagePullPolicy: Always
```

`imagePullPolicy: Always` pairs with mutable tags (`master`, `dev`) so pods pick up new builds on restart.

## 12. What does NOT belong in `k8s/`

- Helm charts (use `charts/` or a separate repo)
- Kustomize overlays (use `kustomize/` if adopted)
- Terraform (use `terraform/`)
- Documentation (use `README.md` alongside code)

## Antipatterns

- Multi-resource YAML with `---` separators in one file
- Hardcoded image tags (breaks dev/staging/master branching)
- Raw secret values committed to git
- Per-tenant file copies instead of one templated file
- Manifests at repo root instead of next to the code
- Inconsistent type suffixes (`-deployment.yaml` in one file, `-deploy.yaml` in another)
- Hardcoded namespaces instead of `{{ "NAMESPACE" | env }}`
- Mixing annotation prefixes across repos in the same org
