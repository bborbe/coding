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
