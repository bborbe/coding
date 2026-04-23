# Go Module Replace Guide

When to use `replace` in `go.mod`, and when not to.

## Rule

- **Replace inside a single repo** → **OK**. Multi-module repos (monorepos with several `go.mod`) use relative-path replaces so sibling modules resolve to the working tree, not a released version.
- **Replace across repo boundaries** → **NO**. Never use a `replace` that points outside the current repo's checkout. Consume cross-repo modules as released pseudo-versions or tagged releases.

## Why

**Inside repo:** the replace is part of the monorepo's contract. Every clone has the sibling module at the same relative path. CI, builds, and contributors see the same resolution. Changes to the sibling are reviewed in the same PR.

**Across repos:** the replace points to a path that only exists on your machine. Anyone else cloning the repo gets a broken build. CI can't resolve it. The module graph becomes non-reproducible. Worse, it hides the fact that consumers of your module require an unreleased change — the dependency looks fine locally but breaks the moment someone else pulls it.

## Correct patterns

### Inside repo (monorepo)

```go
// services/api/go.mod
module github.com/acme/monorepo/services/api

require github.com/acme/monorepo/libs/shared v0.0.0-...

replace github.com/acme/monorepo/libs/shared => ../../libs/shared
```

Sibling module `libs/shared` is always available at the relative path; the replace pins local development to the working tree.

### Across repos (released version)

```go
// consumer/lib/go.mod
module github.com/acme/consumer/lib

require github.com/acme/producer/lib v0.0.0-20260403114524-913de8870914
// NO replace directive — module resolves via GOPROXY
```

The consumer pulls a specific tagged or pseudo-version from the module proxy. To upgrade, bump the version string and run `go mod tidy`.

## Development workflow for cross-repo changes

1. Make change in producer repo (e.g. `acme/producer`).
2. Commit and push.
3. Tag or let the commit be pseudo-versioned.
4. In consumer repo (e.g. `acme/consumer`), run `go get github.com/acme/producer/lib@<version>` and `go mod tidy`.

Never shortcut step 2-3 with a local replace. The extra ceremony exists specifically to prevent broken builds for everyone else.

## Exceptions

None in practice. If you feel you need a cross-repo replace, one of these is almost always better:

- Publish a pre-release version (`v0.0.0-YYYYMMDDHHMMSS-commitsha`) and pin to it.
- Vendor the producer code temporarily.
- Restructure so the two modules live in the same repo.

## Antipatterns

```go
// ❌ BAD — cross-repo relative replace
// consumer/go.mod
replace github.com/acme/producer/lib => ../../producer/lib
// Builds locally, breaks for everyone else. CI fails: path doesn't exist in their checkout.
```

```go
// ❌ BAD — replace to "test" an unreleased change
replace github.com/acme/producer/lib => /Users/alice/work/producer/lib
// Machine-specific absolute path. Hides the fact the consumer requires unreleased code.
```

```go
// ✅ GOOD — pseudo-version after producer push
require github.com/acme/producer/lib v0.0.0-20260403114524-913de8870914
// No replace. Reproducible for everyone.
```

## Related

- [Go modules docs: replace directive](https://go.dev/ref/mod#go-mod-file-replace)
- [Go Mod Dependency Fix](go-mod-dependency-fix-guide.md) — troubleshooting module resolution
