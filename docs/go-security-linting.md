# Go Security Linting (gosec)

`gosec` runs as part of `make precommit`. Know the common findings and fix them correctly on the first attempt.

## File Permissions

```go
// ❌ BAD: gosec G306 — world-readable
os.WriteFile(path, data, 0644)
os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0644)
os.MkdirAll(dir, 0755)

// ✅ GOOD: owner-only permissions
os.WriteFile(path, data, 0600)
os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0600)
os.MkdirAll(dir, 0750)
```

## File Path from Variable

```go
// ❌ BAD: gosec G304 — file path from variable
data, err := os.ReadFile(userPath)

// ✅ GOOD: suppress with comment when path is trusted
// #nosec G304 -- path from internal ListQueued(), not user input
data, err := os.ReadFile(trustedPath)
```

## Subprocess from Variable

```go
// ❌ BAD: gosec G204 — command from variable
cmd := exec.CommandContext(ctx, binary, args...)

// ✅ GOOD: suppress when command is controlled
// #nosec G204 -- binary is hardcoded constant, args from trusted config
cmd := exec.CommandContext(ctx, "git", "push")
```

## Rules

1. **Default to `0600` for files, `0750` for directories** — always
2. **Never suppress without explanation** — `#nosec G304 -- reason here`
3. **Fix on first attempt** — don't iterate through `make precommit` multiple times
4. **Suppress only when the input is trusted** — internal paths, hardcoded commands
5. **`os.Chmod` return value must be checked** — `if err := os.Chmod(...); err != nil`
6. **Lock/PID files**: use `0600` permissions, not `0644`

## Checklist

- [ ] All `os.WriteFile` / `os.OpenFile` use `0600`
- [ ] All `os.MkdirAll` use `0750`
- [ ] All `#nosec` have explanatory comments
- [ ] All `os.Chmod` return values checked (or explicitly `_ =` with comment)
- [ ] No `os.ReadFile` with untrusted paths without `#nosec` + reason

### RULE go-security/file-perms-too-permissive (MUST)

**Owner**: go-security-specialist
**Applies when**: `os.WriteFile($PATH, $DATA, $PERM)` or `os.OpenFile($PATH, $FLAGS, $PERM)` calls in a `*.go` file outside `*_test.go` and `vendor/`, where `$PERM` is a literal octal that is NOT `0600` / `0o600`.
**Enforcement**: `rules/go/file-perms-too-permissive.yml`
**Why**: world-readable file permissions (e.g. `0644`) expose configuration data, lock files, and other artifacts to any process on the host. gosec G306 flags this; the convention is owner-only `0600` for ALL files unless there is a specific reason documented via `#nosec` with explanation.

#### Bad

```go
os.WriteFile(path, data, 0644)
os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0644)
```

#### Good

```go
os.WriteFile(path, data, 0600)
os.OpenFile(path, os.O_CREATE|os.O_WRONLY, 0600)
```

### RULE go-security/dir-perms-too-permissive (MUST)

**Owner**: go-security-specialist
**Applies when**: `os.MkdirAll($PATH, $PERM)` or `os.Mkdir($PATH, $PERM)` calls in a `*.go` file outside `*_test.go` and `vendor/`, where `$PERM` is a literal octal that is NOT `0750` / `0o750`.
**Enforcement**: `rules/go/dir-perms-too-permissive.yml`
**Why**: world-readable directories (e.g. `0755`) expose contents to any process on the host. The convention is `0750` (owner-rwx + group-rx, no world) for ALL agent-created directories.

#### Bad

```go
os.MkdirAll(dir, 0755)
os.Mkdir(dir, 0755)
```

#### Good

```go
os.MkdirAll(dir, 0750)
os.Mkdir(dir, 0750)
```

### RULE go-security/nosec-requires-reason (MUST)

**Owner**: go-security-specialist
**Applies when**: a `// #nosec <CODE>` comment in a `*.go` file outside `*_test.go` and `vendor/` appears WITHOUT a `-- <reason>` text component on the same line.
**Enforcement**: `rules/go/nosec-requires-reason.yml`
**Why**: bare `#nosec` suppresses a finding without explaining why the input is trusted. The next reviewer has no audit trail. Mandate `// #nosec G304 -- path from internal ListQueued(), not user input` style.

#### Bad

```go
// #nosec G304
data, err := os.ReadFile(userPath)
```

#### Good

```go
// #nosec G304 -- path from internal ListQueued(), not user input
data, err := os.ReadFile(trustedPath)
```

### RULE go-security/chmod-return-checked (MUST)

**Owner**: go-security-specialist
**Applies when**: an `os.Chmod($PATH, $PERM)` call in a `*.go` file outside `*_test.go` and `vendor/` whose return value is discarded (no `if err := os.Chmod(...); err != nil` wrapper, no `_ = os.Chmod(...)` with an explanatory comment). Detecting "return value used in error check" requires reading the surrounding statement — pure ast-grep cannot reliably distinguish a checked `os.Chmod(...)` from an unchecked one without false positives.
**Enforcement**: judgment
**Why**: silent `os.Chmod` failures leave file permissions in an unexpected state. The convention is either `if err := os.Chmod(...); err != nil { return ... }` or explicit `_ = os.Chmod(...)` with a comment explaining why the error is ignored.

#### Bad

```go
os.Chmod(path, 0600)
```

#### Good

```go
if err := os.Chmod(path, 0600); err != nil {
    return errors.Wrapf(ctx, err, "chmod %s", path)
}
```
