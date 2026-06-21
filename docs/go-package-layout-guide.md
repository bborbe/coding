# Go Package Layout Guide

Default: **one flat `pkg/` directory**. Split into subpackages only when the flat layout gets too big to navigate.

## Default Layout Rule

Put all production code into `pkg/<repo-name>` (or just `pkg/` with a single package name) as a flat package. Files are organized by file-name convention (`<type>.go`, `<type>_test.go`), not by directory.

**Two conventional exceptions** (these always split, even when they only have 1-2 files):

- **`pkg/factory/`** — every project gets one. Centralizes `Create*` wiring per [go-factory-pattern.md](go-factory-pattern.md). The factory's whole job is to be the one place that depends on every other package, so it MUST live in its own package to avoid making everything else depend on it.
- **`pkg/handler/`** — every HTTP service gets one. Per [go-http-handler-refactoring-guide.md](go-http-handler-refactoring-guide.md), HTTP handlers always live in `pkg/handler/`, never inline in `main.go`. Even a single `/healthz` handler goes here.

Both exist by convention regardless of file count. The rest of the code is flat in `pkg/` until a real trigger fires.

```text
notification-service/
├── main.go
└── pkg/
    ├── inventory.go           # was pkg/schedule/inventory.go
    ├── tasks-for-date.go      # was pkg/schedule/tasks_for_date.go
    ├── publisher.go           # was pkg/publisher/publisher.go
    ├── render.go              # was pkg/publisher/render.go
    ├── tick.go                # was pkg/tick/tick.go
    ├── factory/               # always its own package (see Rule)
    │   └── factory.go
    └── handler/               # always its own package (see Rule)
        ├── trigger.go
        └── healthz.go
```

One Go package. One import path. Files grouped by name, not directory.

### GOOD: flat `pkg/` with conventional exceptions split

```go
// [GOOD] pkg/publisher.go
package notification

type Publisher struct { /* ... */ }

func (p *Publisher) Publish(ctx context.Context, msg Message) error { /* ... */ }
```

```go
// [GOOD] pkg/render.go — same package, free function call
package notification

func Render(tmpl string, data any) (string, error) { /* ... */ }
```

```go
// [GOOD] pkg/factory/factory.go — conventional exception, separate package
package factory

import notification "github.com/example/notification-service/pkg" // pkg declares `package notification`

func CreatePublisher(/* deps */) *notification.Publisher { /* ... */ }
```

### BAD: premature type-bucket split

```go
// [BAD] pkg/service/publisher.go
package service

type Publisher struct { /* ... */ }
```

```go
// [BAD] pkg/repository/store.go — now publisher.go must import a sibling
package repository

import "github.com/example/notification-service/pkg/service"
// every feature touches pkg/service + pkg/repository + pkg/handler
```

The BAD layout invents three packages before any of the five split triggers fire — cross-cutting churn replaces cohesion.

## When to split

Extract a subpackage **only** when the flat layout hits a real friction point — never preemptively. Triggers, any one of these:

1. **Independent reuse** — another binary in the same module (or a different repo) needs to import the chunk without dragging the rest.
2. **Independent versioning** — the chunk has its own release cadence different from the parent.
3. **Cycle break** — a circular import between two clusters of files in `pkg/` can only be broken by splitting.
4. **Too many files to navigate** — ≥30 files in `pkg/`, where naming convention alone no longer keeps `cd pkg && ls` readable. Even then, split by *natural seam* (the cluster with the highest internal cohesion), not by *type bucket* (one dir per "model", "handler", "factory" is anti-pattern — see [go-architecture-patterns.md](go-architecture-patterns.md)).
5. **Build-tag isolation** — a chunk uses `//go:build linux` or similar and contaminates the parent's portability.

If none of the above hold, **keep it flat**. A 5-file extracted package costs more in import-path noise + cross-file refactoring friction than it ever saves.

## Why

- Flat `pkg/` minimizes import-path churn during refactors. Moving a function between files is free; moving it between packages rewrites every import.
- Flat layout makes "is this exported?" obvious — every lower-case identifier is package-internal; every upper-case is the public API of the module. Subpackages multiply the public-surface decision per package.
- Premature subpackage split locks in an architectural shape before the code has revealed its real shape. Flat first, split when forced.
- Renaming files is cheap. Renaming directories is cheap. Renaming a package is expensive (imports, godoc, tests, mocks, downstream callers).

## Antipatterns

- **One dir per "concern"** — `pkg/handler/`, `pkg/service/`, `pkg/repository/`. These create cross-cutting churn (every feature touches three dirs) and obscure cohesion. See [go-architecture-patterns.md](go-architecture-patterns.md).
- **One dir per "domain entity"** — `pkg/user/`, `pkg/order/`. Often correct for large products; premature for a single-binary service.
- **Splitting because "it feels cleaner"** — feelings are not a trigger. Run the five-rule check above.
- **Splitting to satisfy a linter (`funlen`, `gocognit`)** — extract a function/method instead. Splitting a package is the wrong knob.
- **Flattening `pkg/factory/` or `pkg/handler/` into `pkg/`** — these are the two conventional exceptions (see Rule). Even with one file, they stay in their own package.

## Migration: subpackages → flat

When a service has prematurely split into `pkg/foo`, `pkg/bar`, `pkg/baz` and none of the five triggers apply:

1. `git mv pkg/foo/*.go pkg/` (rename the package declaration in each file to match `pkg/`'s package name)
2. Rewrite imports — `find . -type f -name '*.go' -exec sed -i '' 's|module/pkg/foo|module/pkg|g' {} +`
3. Resolve symbol collisions (rename internal helpers if two subpackages each had `func helper()`)
4. `make precommit`
5. Delete the empty subpackage directories: `rmdir pkg/foo pkg/bar pkg/baz`

Do this in one PR per service. Don't split the migration across multiple PRs — partial state (some imports rewritten, some not) is a worse problem than the original premature split.

## Related

- [go-architecture-patterns.md](go-architecture-patterns.md) — Interface → Constructor → Struct → Method (works inside one flat package or many)
- [go-factory-pattern.md](go-factory-pattern.md) — `pkg/factory/` is the canonical home for `Create*` wiring (always a separate package, see Rule)
- [go-http-handler-refactoring-guide.md](go-http-handler-refactoring-guide.md) — `pkg/handler/` is the canonical home for HTTP handlers (always a separate package, see Rule)
