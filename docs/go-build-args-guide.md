# Go Build Args Guide

Three build-time values — **git version, git commit, build date** — are injected into every Go service so the runtime can report exactly which source was compiled, which commit it came from, and when. They surface in startup logs and as OCI image labels.

This guide defines the canonical layout. Reference implementation: `~/Documents/workspaces/go-skeleton/` (Makefile.docker, Dockerfile, main.go).

## Why these three

| Arg | Derived from | Answers |
|---|---|---|
| `BUILD_GIT_VERSION` | `git describe --tags --always --dirty` | "Which release is running?" (`v0.52.7`, or SHA if untagged, or `*-dirty` if tree had uncommitted changes) |
| `BUILD_GIT_COMMIT` | `git rev-parse --short HEAD` | "Exact source hash" — unambiguous even across tag renames |
| `BUILD_DATE` | `date -u +%Y-%m-%dT%H:%M:%SZ` | "When was this image built?" — separates dev/staging/prod builds with identical source |

**Why both version and commit**: `git describe` is friendlier for operators but ambiguous when multiple commits share a tag history. The short SHA is the authoritative source pointer. Keep both — cost is negligible, debugging benefit is large.

**Why `--dirty`**: a `make buca` accidentally run from a worktree with uncommitted changes tags the image as `v0.52.7-dirty`, making it obvious in logs that the deployed binary isn't reproducible from the declared version. Catches mistakes like building from the dark-factory-active master branch while it's mid-commit.

## Layout

Four files per service participate.

### 1. `Makefile.docker`

The Docker build target passes all three as `--build-arg`:

```makefile
.PHONY: build
build:
	DOCKER_BUILDKIT=1 \
	docker build \
	--rm=true \
	--platform=linux/amd64 \
	--build-arg DOCKER_REGISTRY=$(DOCKER_REGISTRY) \
	--build-arg BRANCH=$(BRANCH) \
	--build-arg BUILD_GIT_VERSION=$$(git describe --tags --always --dirty) \
	--build-arg BUILD_GIT_COMMIT=$$(git rev-parse --short HEAD) \
	--build-arg BUILD_DATE=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
	-t $(DOCKER_REGISTRY)/$(SERVICE):$(BRANCH) \
	-f Dockerfile .
```

Order convention: `BUILD_GIT_VERSION` → `BUILD_GIT_COMMIT` → `BUILD_DATE`. Put `BUILD_GIT_VERSION` first because operators read it first.

Escape note: `$$(...)` (double dollar) is required inside Makefiles to defer shell expansion from `make` to `sh`.

### 2. `Dockerfile`

Declare each arg, mirror to ENV (so the container sees it at runtime), and surface as OCI image labels (so `docker inspect` sees it without starting the container):

```dockerfile
ARG BUILD_GIT_VERSION=dev
ARG BUILD_GIT_COMMIT=none
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.version="${BUILD_GIT_VERSION}"
LABEL org.opencontainers.image.revision="${BUILD_GIT_COMMIT}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"

ENV BUILD_GIT_VERSION=${BUILD_GIT_VERSION}
ENV BUILD_GIT_COMMIT=${BUILD_GIT_COMMIT}
ENV BUILD_DATE=${BUILD_DATE}
```

Defaults (`dev`, `none`, `unknown`) make the Dockerfile usable without build args — local `docker build .` still produces a runnable image, just without provenance. CI/`make buca` always passes real values.

OCI labels use the official `org.opencontainers.image.*` namespace — tooling (docker inspect, registry UIs, supply-chain scanners) reads them without custom configuration.

### 3. Argument struct (`main.go` or `cmd/<service>/main.go`)

Use `github.com/bborbe/argument` (or the project's standard argument parser) with `env:` tags matching the ENV vars from the Dockerfile:

```go
import libtime "github.com/bborbe/time"

type Argument struct {
	// ... other service-specific args

	BuildGitVersion string            `required:"false" arg:"build-git-version" env:"BUILD_GIT_VERSION" usage:"Build Git version (git describe --tags --always --dirty)" default:"dev"`
	BuildGitCommit  string            `required:"false" arg:"build-git-commit"  env:"BUILD_GIT_COMMIT"  usage:"Build Git commit hash"                                  default:"none"`
	BuildDate       *libtime.DateTime `required:"false" arg:"build-date"        env:"BUILD_DATE"        usage:"Build timestamp (RFC3339)"`
}
```

Order: `BuildGitVersion` → `BuildGitCommit` → `BuildDate`, matching the Makefile order.

`BuildDate` uses `*libtime.DateTime` (not `string`) so parsing happens once at startup — later code gets a real timestamp, not a string it has to re-parse.

`default:"dev"` / `default:"none"` mirror the Dockerfile defaults so local `go run .` without env vars still works.

### 4. Startup log

When the service starts, log all three args explicitly. Most services use a generic `argument_print` helper that reflects over the struct — if so, no log-site change is needed and the new field surfaces automatically. If the service logs args manually, add a sibling log line:

```go
glog.Infof("Argument: BuildGitVersion '%s'", arg.BuildGitVersion)
glog.Infof("Argument: BuildGitCommit '%s'", arg.BuildGitCommit)
glog.Infof("Argument: BuildDate '%s'", arg.BuildDate.Format(time.RFC3339))
```

Expected runtime output:

```
Argument: BuildGitVersion 'v0.52.7'
Argument: BuildGitCommit '615f9cc'
Argument: BuildDate '2026-04-24T12:10:00Z'
```

`v0.52.7-dirty` instead of `v0.52.7` is an immediate red flag: the deployed binary wasn't built from a clean tagged source.

## Prometheus metric

Expose the build args as a single Prometheus gauge so deployments, rollouts, and stuck-image incidents are visible in Grafana without SSH-ing to pods. Use the shared helper from `github.com/bborbe/metrics` — do NOT inline.

### Helper

`github.com/bborbe/metrics.BuildInfoMetrics` publishes a single shared gauge `build_info{version, commit}` whose value is the build timestamp in Unix seconds. Service identification comes from the Prometheus `job` label set by the scrape config, not a metric label — so every binary that imports the package writes to the same metric name and dashboards work uniformly.

### Usage

```go
import (
	libmetrics "github.com/bborbe/metrics"
)

func (a *application) Run(ctx context.Context, sentryClient libsentry.Client) error {
	libmetrics.NewBuildInfoMetrics().SetBuildInfo(
		a.BuildGitVersion,
		a.BuildGitCommit,
		a.BuildDate,
	)
	// ... rest of startup
}
```

Call exactly once at startup, right after argument parsing. `SetBuildInfo` is a no-op when `BuildDate` is nil (local `go run` without build args), so it's safe in all environments.

### Why this shape

- **Value = build timestamp (Unix seconds)**. Lets you query "how old is the running binary" — `time() - build_info` — and alert on stale deploys.
- **Labels = version + commit**. Lets you count unique versions in the fleet (`count by (version) (build_info)`), detect partial rollouts (multiple version values), and correlate crashes to a specific release.
- **Service identification via Prometheus `job` label**, not a metric label. The `job` label is set by the scrape config (one per service), so adding it to the metric would duplicate information and widen cardinality.
- **No `date` label**. Date is the value, not a label — date-as-label explodes cardinality (every build = new time series).
- **Cardinality bound**: `version × commit` is finite (one row per release shipped). A `*-dirty` value IS a distinct data point worth seeing.
- **Shared package**: putting the helper in `github.com/bborbe/metrics` means every service reports the same metric name with the same label shape. Dashboards and alerts work across the whole fleet without per-project customisation.

### Useful queries

```promql
# Which version is each replica running?
build_info

# Unique versions currently deployed across the fleet (filter by job to narrow to one service)
count by (version) (build_info{job="agent-task-controller"})

# Service age in seconds
time() - build_info

# Alert: build older than 90 days
time() - build_info > 86400 * 90
```

## Rollout checklist

For every Go service with a `Dockerfile`:

- [ ] `Makefile.docker` has all three `--build-arg` lines
- [ ] `Dockerfile` declares all three `ARG` with defaults, all three `ENV`, and all three OCI `LABEL`s
- [ ] `Argument` struct has the three fields with matching `env:` tags
- [ ] Startup log surfaces all three (or uses a reflective argument-print helper)
- [ ] `make precommit` passes
- [ ] Post-deploy, the service logs `BuildGitVersion '<expected-tag>'` — verify it matches the intended release tag

## Reference

- Template repo: `~/Documents/workspaces/go-skeleton/` — Makefile.docker, Dockerfile, main.go, argument struct
- OCI image spec: <https://github.com/opencontainers/image-spec/blob/main/annotations.md> — canonical keys for `org.opencontainers.image.*` labels
- Related: [go-makefile-commands.md](go-makefile-commands.md)
