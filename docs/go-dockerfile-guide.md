# Go Dockerfile Guide

The canonical container packaging for Go services and binaries in this ecosystem. One multi-stage shape, two runtime choices, and a shared `Makefile.docker` build block — so every image is built, tagged, mirrored, and deployed the same way.

Reference implementation: `~/Documents/workspaces/go-skeleton/` (Dockerfile + Makefile.docker + main.go). Deployed instances: `trading/frontend/gateway`, `github-releaser-agent`, `k8s-secret-syncer`.

## Canonical shape

A pure Go binary that speaks HTTP and needs nothing beyond its own binary should be **scratch**: nothing to patch, nothing to audit, smallest possible surface.

```dockerfile
ARG DOCKER_REGISTRY=docker.io
FROM ${DOCKER_REGISTRY}/golang:1.26.6 AS build
ARG BUILD_GIT_COMMIT=none
ARG BUILD_DATE=unknown
COPY . /workspace
WORKDIR /workspace
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -mod=vendor -ldflags "-s" -a -installsuffix cgo -o /main

FROM ${DOCKER_REGISTRY}/alpine:3.24 AS alpine
RUN apk --no-cache add ca-certificates

FROM scratch
ARG BUILD_GIT_COMMIT=none
ARG BUILD_DATE=unknown
COPY --from=build /main /main
COPY --from=alpine /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /usr/local/go/lib/time/zoneinfo.zip /
ENV ZONEINFO=/zoneinfo.zip
ENV BUILD_GIT_COMMIT=${BUILD_GIT_COMMIT}
ENV BUILD_DATE=${BUILD_DATE}
ENTRYPOINT ["/main"]
```

### The pieces, and why each is mandatory

| Piece | Why |
|---|---|
| `golang:1.26.x` builder | Version must match `go.mod`'s `go` directive (pin drift causes silent toolchain mismatch — see [go-tools-versioning-guide.md](go-tools-versioning-guide.md)) |
| `-trimpath` | Strips build paths — reproducible builds, no local absolute paths leaked |
| `-mod=vendor` | Reproducible deps, offline build. Vendor is generated JIT by `check-go-mod`, never committed (see below) |
| `CGO_ENABLED=0` | Static binary — no libc dependency at runtime, runs on any base |
| `-ldflags "-s"` | Strip symbol table — smaller image, nothing a debugger of the container needs |
| `-a -installsuffix cgo` | Force rebuild of all packages, skip cached cgo artifacts |
| `ca-certificates.crt` | Required for any outbound TLS (HTTPS to APIs/upstreams). Without it, `x509: certificate signed by unknown authority` at runtime |
| `zoneinfo.zip` + `ZONEINFO` | Go's embedded timezone data. Without it, non-UTC time formatting returns empty/`Local` incorrectly |
| `ENTRYPOINT ["/main"]` | No flags — listen/config come from env (`LISTEN`, config paths) injected by the manifest, per [go-k8s-binary-conventions.md](go-k8s-binary-conventions.md) |

### The `DOCKER_REGISTRY` arg

Parameterized so the same Dockerfile builds for docker.io and the cluster mirror:

- **Standalone repos** default `ARG DOCKER_REGISTRY=docker.io`; `make buca` passes `--build-arg DOCKER_REGISTRY=docker.io`.
- **Quant-cluster services** (trading, agent fleet) hardcode `ARG DOCKER_REGISTRY=docker.prod.nuke.benjamin-borbe.de:443` so builds resolve base images from the local mirror.

The arg applies to the **base images** (`FROM`). The output image tag is set by the Makefile (`-t $(DOCKER_REGISTRY)/$(SERVICE):$(TAG)`), not the Dockerfile.

## When to use alpine-with-tooling instead

Scratch breaks the moment the binary shells out to an external tool. Add an alpine runtime stage with the tools the binary actually execs — nothing more.

| Base | Add | Use when |
|---|---|---|
| scratch + ca-certs + zoneinfo | — | Pure Go binary, no subprocesses (default — routers, gateways, fetchers, controllers) |
| alpine | `git`, `gnupg`, `openssh-client`, `tini` | Binary shells out to git/ssh (e.g. `git-rest`) |
| alpine | `rsync`, `openssh-client`, `tzdata` | Binary shells out to rsync/ssh (e.g. `auth-http-proxy`) |
| claude-yolo / claude-code runtime | node, claude plugin, gh | Agent images that run Claude Code (e.g. `github-*-agent`, `dark-factory-agent`) |

Rule of thumb: **the runtime carries what the binary execs at runtime, never what the developer needed at build time.** Build-time tools (Go toolchain, linters) stay in the build stage and are discarded.

`tini` is the exception that's always safe: if the binary might spawn subprocesses, wrapping `ENTRYPOINT ["/sbin/tini", "--", "/main"]` gives proper PID-1 signal forwarding.

## Makefile.docker build block

The `build`/`upload`/`clean`/`buca` targets are uniform across every Go service with a Dockerfile. Copy the block from a reference repo — it is **not** per-service bespoke.

```makefile
DOCKER_REGISTRY ?= docker.io
ifeq ($(VERSION),)
	VERSION := $(shell git describe --tags `git rev-list --tags --max-count=1`)
endif

.PHONY: build
build: check-go-mod
	DOCKER_BUILDKIT=1 \
	docker build \
	--pull \
	--no-cache \
	--rm=true \
	--platform=linux/amd64 \
	--build-arg DOCKER_REGISTRY=$(DOCKER_REGISTRY) \
	--build-arg BUILD_GIT_VERSION=$$(git describe --tags --always --dirty) \
	--build-arg BUILD_GIT_COMMIT=$$(git rev-parse --short HEAD) \
	--build-arg BUILD_DATE=$$(date -u +%Y-%m-%dT%H:%M:%SZ) \
	-t $(DOCKER_REGISTRY)/bborbe/$(SERVICE):$(VERSION) \
	-f Dockerfile .

.PHONY: check-go-mod
check-go-mod:
	@if [ -f "go.mod" ]; then \
		echo "go.mod found, running go mod vendor..."; \
		go mod vendor; \
	fi

.PHONY: upload
upload:
	docker push $(DOCKER_REGISTRY)/bborbe/$(SERVICE):$(VERSION)

.PHONY: clean
clean:
	docker rmi $(DOCKER_REGISTRY)/bborbe/$(SERVICE):$(VERSION) || true
	rm -rf vendor

.PHONY: buca
buca: build upload clean apply
```

Key points:

- **`check-go-mod` runs `go mod vendor` JIT** before the build — the Dockerfile's `-mod=vendor` needs the vendor dir present, but vendor is gitignored and never committed. `go mod tidy` where code is edited; `go mod vendor` only where `docker build` runs (see [go-build-args-guide.md § Vendor handling](go-build-args-guide.md)).
- **The three build args** (`BUILD_GIT_VERSION`/`BUILD_GIT_COMMIT`/`BUILD_DATE`) are mandatory — declared as `ARG`, mirrored to `ENV`, surfaced as OCI labels. See [go-build-args-guide.md](go-build-args-guide.md) for the full rule.
- **`--platform=linux/amd64`** pins the arch — the nuke cluster nodes are amd64; an arm64 image silently fails to schedule or runs under emulation.
- **`apply`** is deploy: for monorepo services it recurses into subdirs; for standalone publish-only repos it's a documented no-op (`@echo "skip apply — publish-only"`). The deployment config lives in the `quant` repo, not in the service repo.
- `SERVICE` is the only per-service variable — `trading/Makefile.docker` sets it per subdir, standalone repos set it in their own Makefile.

## Build args in the binary

The three build args are not just image metadata — the binary itself exposes them via `-ldflags "-X"` into an argument struct with matching `env:` tags, logs them at startup, and publishes a `build_info` Prometheus gauge. This is the complete loop: Makefile passes them → Dockerfile declares/mirrors them → runtime reports them. Missing any hop loses the provenance chain. Follow [go-build-args-guide.md](go-build-args-guide.md) — it owns this rule.

## Probes and metrics

A k8s-deployed Go binary exposes `/healthz`, `/readiness`, `/metrics` on its `LISTEN` address via `github.com/bborbe/service`. The manifest mirrors this: probes target the same port, `prometheus.io/scrape` annotations match, and a sibling Service carries the `admin/port` annotation for gateway routing. The Dockerfile needs no changes for this — but the image must be built from a binary that follows [go-k8s-binary-conventions.md](go-k8s-binary-conventions.md).

## Common failure modes

| Symptom | Cause |
|---|---|
| `x509: certificate signed by unknown authority` at runtime | `ca-certificates.crt` missing from scratch stage — service makes outbound HTTPS |
| Wrong timezone / empty time strings | `zoneinfo.zip` + `ZONEINFO` missing |
| Build fails `-mod=vendor: package not in vendor` | `check-go-mod` step missing from Makefile `build` — vendor not generated |
| Image built on arm64 Mac won't run in cluster | `--platform=linux/amd64` missing from `docker build` |
| `golang:1.2x` toolchain mismatch errors | Builder tag doesn't match `go.mod` `go` directive |
| Pod restarts / never ready | Binary doesn't implement `/healthz`/`/readiness` — see [go-k8s-binary-conventions.md](go-k8s-binary-conventions.md) |

## Reference implementations

| Repo | Runtime | Notes |
|---|---|---|
| `go-skeleton` | scratch | Canonical template — copy from here |
| `trading/frontend/gateway` | scratch | Quant-deployed, hardcoded nuke registry |
| `github-releaser-agent` | claude runtime | Agent image — tooling + plugin |
| `k8s-secret-syncer` | scratch | Plain k8s binary, `-mod=mod` variant |

## Related

- [go-build-args-guide.md](go-build-args-guide.md) — the three build args, OCI labels, vendor handling (owner of the RULE)
- [go-k8s-binary-conventions.md](go-k8s-binary-conventions.md) — probes, metrics, manifest conventions
- [k8s-manifest-guide.md](k8s-manifest-guide.md) — manifest layout and templating
- [go-tools-versioning-guide.md](go-tools-versioning-guide.md) — toolchain pinning
- [go-makefile-commands.md](go-makefile-commands.md) — general Makefile targets
