# Go Tools Versioning Guide

How to version-pin CLI tools (linters, scanners, code generators) used by Go projects in the bborbe ecosystem — without polluting `go.mod` with the tools' transitive dependencies.

## TL;DR

- **Don't** put CLI tools in `tools.go`
- **Do** declare versions in `tools.env`
- **Do** invoke tools via `go run pkg@$(VERSION)` in the Makefile
- **Do** invoke `//go:generate` directives with `go run pkg@version` (hardcoded version per directive)

## Why Not `tools.go`?

The historical pattern was a `tools.go` file with `//go:build tools` that imports each CLI tool:

```go
//go:build tools
package tools

import (
    _ "github.com/golangci/golangci-lint/v2/cmd/golangci-lint"
    _ "github.com/google/osv-scanner/v2/cmd/osv-scanner"
    _ "github.com/maxbrunsfeld/counterfeiter/v6"
    // ...
)
```

This pins versions in `go.mod` so all developers run the same tool versions. **However, it has serious problems:**

### Problem 1: Transitive Dependency Pollution

Importing a tool via `tools.go` pulls every transitive dependency of that tool into your project's `go.mod`. A typical bborbe library ends up with **400+ indirect requires** — most of them lint-tool internals (linters, AST walkers, container scanners, etc.) — even though the library itself only depends on `pkg/errors`.

This:

- Slows `go mod tidy` and `go build`
- Bloats `vendor/` directories (in projects that vendor)
- Causes version conflicts that require `replace` workarounds (cellbuf, go-header, go-diskfs, ginkgolinter, …)
- Breaks `go install` and `go run pkg@version` for downstream consumers (because the conflicting versions get baked into the require graph)

### Problem 2: Cascade Through Library Imports

If a library `agent/lib` has `tools.go` importing osv-scanner, and a downstream service `code-reviewer` depends on `agent/lib`, then `code-reviewer`'s `go mod tidy` traverses `agent/lib`'s `tools.go` (because the `tools` build tag is activated globally during dep resolution). The transitive lint deps cascade down through every library in the tree.

A single broken tool can block the entire dependency graph.

### Problem 3: Replaces Become Permanent Workarounds

The conflicts produced by tools.go are usually patched with `replace` directives in `go.mod`:

```go
replace (
    github.com/charmbracelet/x/cellbuf => github.com/charmbracelet/x/cellbuf v0.0.15
    github.com/denis-tingaikin/go-header => github.com/denis-tingaikin/go-header v0.5.0
    github.com/diskfs/go-diskfs => github.com/diskfs/go-diskfs v1.7.0
    github.com/nunnatsa/ginkgolinter/types => github.com/nunnatsa/ginkgolinter v0.19.1
)
```

These accumulate over time. Every project copies them. Removing `tools.go` makes them all unnecessary.

## What `tools.go` Was Trying to Solve

The two legitimate concerns:

1. **Reproducible tool versions** — every developer / CI run uses the same lint/scan/generate tool versions
2. **Vendoring for offline / air-gapped builds** — tools available without network on each `make`

## The Replacement: `tools.env` + Makefile `@version`

### `tools.env` — One Source of Truth

A flat key-value file at the repo root with the canonical version of every tool:

```makefile
ADDLICENSE_VERSION         ?= v1.2.0
COUNTERFEITER_VERSION      ?= v6.12.2
ERRCHECK_VERSION           ?= v1.10.0
GINKGO_VERSION             ?= v2.28.3
GOIMPORTS_REVISER_VERSION  ?= v3.12.6
GOLANGCI_LINT_VERSION      ?= v2.11.4
GOLINES_VERSION            ?= v0.13.0
GO_MODTOOL_VERSION         ?= v0.7.1
GOSEC_VERSION              ?= v2.26.1
GOVULNCHECK_VERSION        ?= v1.3.0
OSV_SCANNER_VERSION        ?= v2.3.1
```

Every repo keeps its `tools.env` in sync with `~/Documents/workspaces/coding/templates/tools.env` (the canonical version). When upgrading a tool, update the canonical file and propagate to all repos.

The `?=` (instead of `=`) lets a developer override per-shell:

```bash
GOLANGCI_LINT_VERSION=v2.11.5 make lint  # try a newer version locally
```

### Makefile — Use `@version`

Each tool invocation uses `go run pkg@$(VERSION)` instead of `go run -mod=mod pkg`:

```makefile
include tools.env

.PHONY: lint
lint:
	go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@$(GOLANGCI_LINT_VERSION) run ./...

.PHONY: gosec
gosec:
	go run github.com/securego/gosec/v2/cmd/gosec@$(GOSEC_VERSION) -exclude=G104 ./...

.PHONY: osv-scanner
osv-scanner:
	go run github.com/google/osv-scanner/v2/cmd/osv-scanner@$(OSV_SCANNER_VERSION) --recursive .
```

`go run pkg@v` builds the tool in a **temporary module** that uses the tool's own `go.mod`. The host project's `go.mod` is untouched.

### `//go:generate` Directives

For code generators invoked via `//go:generate` (typically counterfeiter), hardcode the version directly:

```go
//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate
```

`go generate` substitutes shell environment variables, but it's simpler and explicit to pin the version at the point of use. Versions stay in sync with `tools.env` by convention, not enforcement.

## What Goes in `tools.go` (If Anything)

**Nothing.** Delete it.

If a project genuinely needs to vendor a tool binary into a Docker image (and `go run @version` in the build is too slow), use a multi-stage Dockerfile that runs `go install pkg@version` in the build stage and copies the binary to the final image. This is local to that project, not a general pattern.

## Tools Without `go install` Support

Some tools don't support `go install` reliably:

- **trivy** — Aqua Security distributes a binary. Install via `apt`/`apk`/`brew`. Invoke as a system binary in the Makefile (no `go run`).
- **osv-scanner** — Currently broken upstream for `go install osv-scanner@v2.3.2+` due to a transitive dep (`buildtools/build`) that Go's module loader can't resolve. **Pin to `v2.3.1`** until upstream releases a fix. Alternative: install the SLSA-compliant prebuilt binary via `brew install osv-scanner` and invoke it as a system binary like trivy.

## Migration Steps

For each repo:

1. **Sync `tools.env`** from `~/Documents/workspaces/coding/templates/tools.env`
2. **Update `Makefile`** — every `go run -mod=mod pkg` becomes `go run pkg@$(VERSION)`. Add `include tools.env` at the top.
3. **Update `//go:generate` directives** — replace `go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate` with `go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate`
4. **Delete `tools.go`**
5. **Manually trim `go.mod`** to its real direct deps (no replace block, no lint/scanner indirects). Run `go mod tidy` to repopulate the legitimate indirect requires.
6. **Run `make precommit`** to verify everything passes
7. **Commit + release** — the diff should show `go.mod` shrinking from 400+ lines to under 30

The `updater` tool detects migration via `tools.go` absence and automatically removes the four obsolete replaces (`cellbuf`, `go-header`, `go-diskfs`, `ginkgolinter/types`) on the next `updater all` run. See `~/Documents/workspaces/updater/src/updater/gomod_excludes.py` (`TOOLS_GO_OBSOLETE_REPLACES`).

## Migration Order Across Libraries

Libraries form a dependency tree. Migrate leaves first, root last. When a leaf is migrated and released, downstream libraries' `go mod tidy` no longer pulls in the leaf's tools.go-era pollution.

For the bborbe ecosystem the order is approximately:

```
errors → run, validation → collection, sentry → math → parse → time
       → argument/v2, k8s, log, metrics, vault-cli
       → kv ↔ http (cycle — release together)
       → strimzi, memorykv → service → boltkv → kafka → cqrs → agent/lib
```

After all libraries migrate, downstream services (code-reviewer, etc.) get a clean dependency graph automatically.

## Pitfalls

- **`gosec` prints `Gosec : dev`** when run via `go run pkg@version`. This is cosmetic — the version metadata isn't compiled in. Functionality is unaffected.
- **`go mod tidy -e` can truncate go.mod** if package resolution fails partway. After deleting `tools.go`, write a minimal known-good `go.mod` (just direct deps + `go 1.x`) and run `go mod tidy` from there. Don't run `tidy -e` on the polluted go.mod.
- **`go run pkg@version` ignores local `replace` directives.** Replaces in your go.mod do NOT affect tools invoked this way — the tool is built in a temp module with its own dep graph. This is why some tools (like osv-scanner v2.3.2+) can't be locally patched and must be pinned to a working upstream version.
- **CI cold-start is slower** the first time a tool is invoked at a given version (Go has to compile it). Subsequent runs hit the build cache. For tight CI loops, install the binary in the CI image.

## References

- Canonical templates: `~/Documents/workspaces/coding/templates/{tools.env,Makefile.library,Makefile.service}`
- Updater logic: `~/Documents/workspaces/updater/src/updater/gomod_excludes.py`
- Pilot example: `bborbe/errors v1.5.11` (commit "release v1.5.11")
