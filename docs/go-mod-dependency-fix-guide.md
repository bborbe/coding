# Go Module Dependency Fix Guide

Guide for diagnosing and fixing Go module dependency compilation failures, particularly transitive dependency breakage from pre-release commits.

## Common Symptom

```
# github.com/some/dependency
../go/pkg/mod/github.com/some/dependency@v0.x.y-0.timestamp-hash/file.go:123:
cannot use X (type A) as type B
```

Build fails on a **transitive dependency** you don't control, typically a pre-release pseudo-version (`v0.x.y-0.YYYYMMDD-hash`) pulled in by a direct dependency.

## Root Cause

A direct dependency (e.g., `osv-scanner v2.3.5`) requires a transitive dependency at a pre-release commit that doesn't compile with your Go version. The pre-release commit was created before a Go release introduced breaking changes (e.g., type signature changes in stdlib).

## Diagnosis Steps

### 1. Identify the Broken Package

From the error, note:
- **Broken package**: `github.com/some/dependency` (the one that fails to compile)
- **Version**: pseudo-version like `v0.x.y-0.20260318-hash`
- **Error type**: usually type mismatches from Go stdlib changes

### 2. Find Who Requires It

```bash
go mod graph | grep "broken/dependency"
```

This shows which direct dependency pulls in the broken version.

### 3. Check Available Versions

```bash
# Tagged releases
go list -m -versions github.com/broken/dependency

# Current version in use
go list -m -json github.com/broken/dependency | grep Version
```

### 4. Check If Newer Commits Exist

```bash
GOPROXY=direct go list -m -versions github.com/broken/dependency
```

## Fix Strategies (in order of preference)

### Strategy 1: Run `go mod tidy`

Often the simplest fix. The dependency graph may be inconsistent after `go get -u`. Running `go mod tidy` re-resolves all dependencies and may select compatible versions.

```bash
go mod tidy
go build ./...
```

**Why this works:** `go get -u` updates individual modules but can leave the overall graph inconsistent. `go mod tidy` recalculates the minimum version selection (MVS) for the entire graph, which may resolve transitive dependencies differently.

### Strategy 2: Upgrade Direct Dependencies

Upgrade the libraries that pull in the broken transitive dependency. Their newer versions may require a fixed version.

```bash
# Upgrade specific direct dependencies
go get -u github.com/your/direct-dep@latest

# Then re-tidy
go mod tidy
```

### Strategy 3: Add a Replace Directive

Force the broken module to a working version:

```bash
# In go.mod, add:
replace github.com/broken/dependency => github.com/broken/dependency v0.4.5
```

**Caution:** This can cause runtime issues if the requiring module depends on APIs only in the newer version.

### Strategy 4: Downgrade the Requiring Module

```bash
go get github.com/requiring/module@v2.3.3
go mod tidy
```

**Caution:** May cascade into many other downgrades. Check with:
```bash
go get -d github.com/requiring/module@v2.3.3
# Review the output before committing
```

### Strategy 5: Exclude the Broken Version

```bash
# In go.mod, add:
exclude github.com/broken/dependency v0.4.6-0.20260318175007-ec4239d68fb9
```

Then run `go mod tidy` to let Go pick the next valid version.

### Strategy 6: Pin to a Newer Commit

If the fix exists on main but isn't tagged:

```bash
go get github.com/broken/dependency@main
go mod tidy
```

## Prevention

### RULE go-mod-dependency-fix/tidy-after-get-update (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go project's CHANGELOG / git history shows a `go get -u <pkg>` or `go get <pkg>@<version>` operation that was committed without a subsequent `go mod tidy` (`go.sum` shows added entries but no removed-but-no-longer-needed entries; or `go.mod` has new `require` lines but `go.sum` has unused hashes).
**Enforcement**: judgment (semantic — typically caught at PR review: the commit message says "update X" but the diff doesn't have the `go mod tidy` side effects)
**Why**: `go get -u` and `go get @version` update individual modules but leave the dependency graph inconsistent — transitively required modules at older incompatible versions stay pinned, transitively-no-longer-needed modules linger in `go.sum`. The next contributor's `go build` fails with cryptic version-conflict errors. `go mod tidy` recalculates Minimum Version Selection (MVS) for the entire graph after every dep change — it's the canonical "leave the graph clean" step. Skipping it is the #1 cause of the broken-build-after-merge problem.

#### Bad

```bash
go get -u github.com/some/lib@latest
git add go.mod go.sum
git commit -m "update some/lib"
# next contributor: 'go build ./...' errors with transitive version conflicts
```

#### Good

```bash
go get -u github.com/some/lib@latest
go mod tidy           # ← reconciles the graph
go build ./...        # verify it still compiles
git add go.mod go.sum
git commit -m "update some/lib"
```

### RULE go-mod-dependency-fix/exclude-over-cross-repo-replace (SHOULD)

**Owner**: go-quality-assistant
**Applies when**: a Go project pins around a known-broken upstream transitive version by adding a `replace` directive that points at a different repo (forked code, pseudo-version on a different module path) instead of an `exclude` directive that lets MVS pick the next valid version.
**Enforcement**: judgment (semantic — `replace` for known-broken-version-skip and `replace` for cross-repo-pinning look identical in `go.mod`; the intent is the differentiator)
**Why**: `exclude` is the right primitive for "this specific version is broken; let MVS choose another." It says "skip version v0.4.6-..., pick the next valid one." `replace` is the right primitive for "redirect this module to a different source location" — fine for same-repo monorepo paths (see `go-mod-replace/no-cross-repo-replace`), wrong for "pin to an upstream fix that exists on main but isn't tagged." A `replace` to upstream-main hides the fact that the project requires an unreleased commit; an `exclude` of the broken version makes the skip explicit and lets the next valid upstream tag resolve normally.

#### Bad

```go
// go.mod — pinning around a broken transitive via cross-repo replace
replace github.com/broken/dep => github.com/myfork/dep v0.4.5-fixed
// hides the fact that the upstream commit is broken; introduces a fork dependency
```

#### Good

```go
// go.mod — excluding the broken version lets MVS pick the next valid one
exclude github.com/broken/dep v0.4.6-0.20260318175007-ec4239d68fb9
// Then: go mod tidy → MVS picks v0.4.5 (the previous valid tag) or v0.4.7 if released
```

### Other prevention bullets (judgment-tier, not yet canonicalised as RULE blocks)

1. **Test compilation before committing** — `make test` (NOT `go build ./...`) catches transitive breakage AND test failures
2. **Pin tool dependencies carefully** — tools in `tools.go` pull large dependency trees
3. **Watch Go release notes** — stdlib type changes (like `os.FileInfo` → `io/fs.DirEntry`) break pre-release dependencies first

## Real-World Example: osv-scalibr + Go 1.26

**Problem:** `osv-scanner v2.3.5` requires `osv-scalibr v0.4.6-0.20260318...` (pre-release). This commit uses `os.FileInfo` where Go 1.26 expects `io/fs.DirEntry`, causing compilation failure.

**What failed:**
- `go get github.com/google/osv-scalibr@v0.4.5` — cascaded downgrades across 15+ modules
- `go get github.com/google/osv-scalibr@latest` — latest tag is v0.4.5, same cascade

**What worked:** `go mod tidy` after upgrading direct bborbe dependencies (`boltkv`, `kv`, `run`). The re-resolved dependency graph provided compatible transitive dependencies that made osv-scalibr compile.

**Key insight:** The compilation error wasn't in osv-scalibr's own code but in how its dependencies interacted with Go 1.26. Changing other parts of the dependency graph (upgrading unrelated direct deps) changed the resolved versions of shared transitive deps, fixing the build.

## Quick Reference

| Situation | Try First |
|-----------|-----------|
| Build fails after `go get -u` | `go mod tidy` |
| Pre-release pseudo-version broken | Upgrade direct deps, then `go mod tidy` |
| No tagged fix available upstream | `replace` directive or `exclude` |
| Cascade of downgrades | Don't force; try `go mod tidy` path instead |
| Tool dependency (`tools.go`) broken | Consider separate `go.mod` for tools |
