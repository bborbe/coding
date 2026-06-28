# Architecture Dimensions Guide

How to review a whole codebase for **behavioral** architectural quality, complementing the **structural** review owned by `go-architecture-assistant` / `python-architecture-assistant`.

## When to apply

- Whole-codebase audit (not a diff)
- Quarterly architectural health check
- Before scaling a service (team, traffic, complexity)
- Onboarding a codebase you didn't write

**Do NOT use for diff review** — `/coding:local-review` and `/coding:pr-review` cover per-PR work.

## Scope: structural vs behavioral

| Concern | Owned by |
|---------|----------|
| Package boundaries, dependency direction, abstraction seams, SRP at package level | `go-architecture-assistant` / `python-architecture-assistant` (structural) |
| Data flow, failure paths, concurrency, observability, drift, blast radius | This guide (behavioral) |

The two pass together cover whole-codebase architectural health. Run in parallel via `/coding:architecture-review`.

## The eight dimensions

Review one per pass; don't blur them. Each finding cites file:line.

### 1. Data flow end-to-end

Trace ONE critical command from entry point to all side-effects. Don't survey — pick one path and walk it.

**Check:**

- Where does state live? (filesystem, in-memory, external system — usually multiple)
- Ordering guarantees? At-least-once delivery implies duplicates; is every consumer idempotent?
- Half-state recovery on partial failure?
- Are state transitions owned by one component, or fanned across several?

**Severity:**

- **Critical** if state can be lost on crash; duplicate processing causes incorrect external side-effects; state machine has multiple owners with divergent interpretations.
- **Major** if recovery requires manual operator action; ordering is fragile but eventually-consistent.
- **Moderate** if idempotency is documented but not enforced.

### 2. Failure & resilience

Walk unhappy paths explicitly. Don't assume; check each one.

**Check:**

- Subprocess dies — handled, or daemon stalls?
- Network unreachable — bounded retry with backoff?
- Daemon SIGTERM mid-operation — recoverable on next start, or corrupt state?
- Timeout / retry / backoff consistency. Jitter?
- Context cancellation propagation top-to-bottom.

**Severity:**

- **Critical** if a partial failure leaves the system in an unrecoverable state; daemon hangs forever on common failure mode.
- **Major** if retry logic is reinvented per package with different semantics; no timeout on external call.
- **Moderate** if error is swallowed/logged but operator has no signal.

### 3. Concurrency & lifecycle

Goroutine / task ownership: who starts, who stops?

**Check:**

- Goroutine leak paths on error?
- Context threading all the way down (no `context.Background()` in business logic)?
- Shared mutable state — protected by mutex, or by goroutine ownership? Documented?
- Graceful shutdown contract — `sync.WaitGroup` / `errgroup` / equivalent?
- Process-wide state (`os.Chdir`, env vars) that races with concurrent operations?

**Severity:**

- **Critical** if process-wide mutable state races with concurrent goroutines; locks held across operations that can hang forever.
- **Major** if shutdown is abrupt (background work continues after exit); leak path on common error.
- **Moderate** if mutex protection is correct but undocumented.

### 4. Observability

Can you debug a stuck operation in production without adding logs and redeploying?

**Check:**

- Correlation IDs that survive cross-process / cross-Kafka / cross-subprocess hops?
- Structured logging (`slog.With` or equivalent) used consistently, or every site rebuilds attrs from scratch?
- Field-key drift across packages (same domain object logged with different keys)?
- Logger output complete (boot phase too, not just steady-state)?
- Dynamic log level control, or static at startup?
- Debug endpoints (`/debug/pprof`, per-object state dump, log tail) — present?

**Severity:**

- **Major** if no correlation ID across process boundaries; can't grep one request end-to-end.
- **Major** if field keys drift across packages for the same domain object.
- **Moderate** if no dynamic log-level control; investigation requires redeploy.

### 5. Cross-cutting consistency

Same problem solved the same way across packages, or each one reinvents?

**Check:**

- Subprocess spawning — one wrapper, or N raw `exec.Command*` sites?
- Error wrapping convention — one library used consistently?
- Retry logic — central helper, or per-package?
- Config loading — one path, or scattered?
- HTTP clients — shared transport + timeout, or one-off `http.DefaultClient.Do` per package?

Especially relevant for AI-generated code — agents transcribe specs and drift from house style unless conventions are centralized.

**Severity:**

- **Major** if a foundational concern (subprocess, retry) has 3+ patterns coexisting.
- **Moderate** if conventions are documented but not enforced.
- **Minor** if two small patterns coexist with no operational impact.

### 6. Configuration, secrets, blast radius

**Check:**

- Config layering precedence (default < global < project < env < arg) — explicit and tested?
- Secrets resolution — at load time or at use time? Documented?
- RBAC / least privilege — container runs as root? Credentials mounted read-write?
- Resource limits — `--memory`, `--cpus`, `--pids-limit` set with sane defaults?
- Filesystem hardening — `--read-only`, `--security-opt no-new-privileges`, `--cap-drop ALL`?
- Tokens scoped per-repo / per-tenant, or global?

**Severity:**

- **Critical** if container runs as root with read-write credential mount; no resource limits on operator-untrusted code.
- **Critical** if config validation passes but runtime ignores the field (silent misconfiguration trap).
- **Major** if secrets convention is inconsistent across the codebase.

### 7. Evolvability test (meta-test)

Pick one plausible next feature. Count files / packages you'd touch.

**Check:**

- Shotgun surgery → abstraction is at the wrong altitude.
- Touching one file → boundary is right OR abstraction is premature (does the feature actually need swap-in/swap-out?).
- Dead-code dispatch — config field exists but runtime always picks one path? (Silent misconfiguration.)
- Asymmetric abstractions — one provider has its own package, another is hardcoded in a "generic" package?

**Severity:**

- **Critical** if a configurable feature is dead code at runtime (silent misconfig).
- **Major** if adding a sibling implementation requires touching 10+ files; one impl exists in its own package while another leaks into "generic" code.

### 8. Architectural drift

Stated architecture (in `docs/`, ADRs, CLAUDE.md) vs implemented reality.

**Check:**

- Stated patterns the code violates?
- Documents that lie (claim a refactor shipped that didn't, claim Phase 2 done when only Phase 1 landed)?
- "Temporary" workarounds (band-aid forwarders, one-time migrations on every boot, legacy compat probes) that are now permanent?
- Package inventory in CLAUDE.md vs actual `pkg/` listing — drift?
- ADR Phase markers — Phase 1 shipped but Phase 2 unstarted with `TODO` in source?

**Severity:**

- **Major** if a security ADR's Phase 2 is unshipped but production defaults assume Phase 2 (e.g. "secure defaults will land later" → never landed).
- **Major** if CLAUDE.md / README describes a different architecture than the code.
- **Moderate** if "temporary" workarounds carry justifying comments but no removal plan.

## Output contract

Every finding MUST include:

- **Severity tag** — Critical / Major / Moderate / Minor (architectural judgment, not "function too long")
- **file:line citation** — `pkg/foo/bar.go:42`; drop any finding without one
- **Why it matters** — one sentence
- **Real fix** — not "consider refactoring"; name the structural change

Report ends with **Top 5 highest-leverage fixes** — best (impact / cost) ratio across all severities. The actionable shortlist, not an exhaustive checklist.

## Anti-patterns

| ❌ | ✅ |
|---|---|
| "Function too long" / "too many params" → mechanical, not architectural | "40-param factory call duplicated across 2 sites — silent positional drift" |
| Long checklist with no file:line citations | Specific finding with `pkg/foo/bar.go:123` |
| Generic checklist parroting | Findings rooted in actual file paths and named types from the reviewed repo |
| "Refactor everything" plan | Top 5 highest-leverage fixes, sequenced, each independently shippable |
| Cover all 8 dimensions equally even if 3 don't apply | Skip dimensions that genuinely don't apply (e.g. observability for a CLI with no long-running state) |
| Re-do the structural review | This is the BEHAVIORAL pass; structural is the sibling agent's job |

## Skip directives

Exclude from review:

- `vendor/`, `node_modules/`, `mocks/`, generated files (`*_gen.go`, `*.pb.go`)
- Lock files (`go.sum`, `package-lock.json`, `uv.lock`)
- Tests (`*_test.go`, `tests/`) — review production code; test quality is a separate concern owned by `go-test-quality-assistant` / `python-quality-assistant`

## Relationship to other agents/commands

- `coding:go-architecture-assistant` / `coding:python-architecture-assistant` — sibling structural pass; run in parallel via `/coding:architecture-review`
- `coding:srp-checker` — unit-level SRP; this guide handles cross-cutting consistency
- `/coding:local-review` — diff-scoped per-PR review (different altitude)
- `/coding:audit-architecture` — quick single-agent structural scan (lighter alternative)
