---
allowed-tools: Task, Bash(git status:+), Bash(git log:+), Bash(git branch:+), Glob, Read
argument-hint: "[directory]"
description: Deep architectural review of a whole codebase — top-down structure + dimensions (data flow, failure, concurrency, observability, drift) consolidated into Must/Should/Could
---

## Context

- Current git status: `!git status`
- Current branch: `!git branch --show-current`
- Recent commits: `!git log --oneline -5`

## Your Task

Run a **whole-codebase architectural review** — not a diff. Two parallel agents, orthogonal scopes, consolidated into Must/Should/Could with file:line citations.

Different altitude from `/coding:code-review` (diff-scoped, per-PR) and deeper than `/coding:audit-architecture` (single-agent quick scan). Use when:

- Auditing a codebase quarterly for structural health
- Before scaling a service (team, traffic, complexity)
- After persistent friction signals "the design is fighting us"
- Onboarding a codebase you didn't write

### Step 1: Parse Arguments

- Argument = target directory (default: current directory `.`)
- Never resolve `~` — pass as given

### Step 2: Detect Project Type and Baseline

Use Glob to detect:

- **Go project** — `*.go` files or `go.mod`
- **Python project** — `*.py` files or `pyproject.toml` / `requirements.txt`
- **Mixed** — both present → run the Go top-down agent AND the Python top-down agent AND the dimensions agent (three Tasks in parallel)

Read stated architecture docs first (drift baseline). Check for:

- `docs/architecture.md`, `docs/architecture-flow.md`, `docs/design.md`
- ADRs in `docs/adr/` or `docs/decisions/`
- Root-level `ARCHITECTURE.md`

Note their existence (or absence) for Step 4's drift assessment.

### Step 3: Invoke Agents in Parallel

Run all agents (2 or 3, per Step 2 detection) in a single message via Task tool.

**Agent A (Go variant) — Top-down structural:**

- subagent_type: `coding:go-architecture-assistant`
- prompt: "Top-down architecture review of [directory]. Start from entry point (main.go, cmd/) → pkg/ → internal packages. Assess: (1) entry point — composition root vs business-logic leak; (2) package structure — SRP at package level; flag grab-bag packages (util, common, helpers); (3) layering and dependency direction (inward toward domain); (4) separation of concerns at type level (real multi-responsibility, not line count); (5) abstraction seams (right places interface'd? noise interfaces?); (6) notable good patterns to preserve. Read-only. file:line citations for every finding. Skip vendor/, mocks/, node_modules/. Report: one-paragraph verdict + section per concern + 'what's working well' section."

**Agent A (Python variant) — Top-down structural:**

- subagent_type: `coding:python-architecture-assistant`
- prompt: "Top-down architecture review of [directory]. Start from entry point (`__main__.py`, `cli.py`, FastAPI/Flask app factory) → top-level package → submodules. Assess: (1) entry point — composition root vs business-logic leak; (2) module/package structure — SRP at module level; flag grab-bag modules (`utils`, `common`, `helpers`); (3) layering and dependency direction (domain must not import framework/ORM/HTTP client); (4) separation of concerns at class level (real multi-responsibility, not file length); (5) import-time side effects (top-level side effects, registry mutations on import); (6) mixin/inheritance abuse (deep MRO, diamond hierarchies); (7) abstraction seams (Protocol/ABC at the right altitude? noise interfaces?); (8) notable good patterns to preserve. Read-only. file:line citations for every finding. Skip `.venv/`, `__pycache__/`, `build/`, `dist/`. Report: one-paragraph verdict + section per concern + 'what's working well' section."

**Agent B — Dimensions pass (run in parallel with A):**

The dimensions pass is open-ended behavioral exploration (data flow tracing, failure-path walks, drift detection), not rule-tier adjudication. There is no `rules/index.json` entry to cite, no judgment-tier rule set scoped to it, and no `coding:*` agent currently owns this altitude — so we route to the generic `claude` agent with a focused prompt. A future `coding:architecture-dimensions-assistant` extraction would need its own `docs/` guide + rule entries to earn its keep; until that exists, the generic route is correct.

- subagent_type: `claude`
- prompt: "Extend a separately-running top-down architecture review of [directory] with these orthogonal dimensions. Do NOT redo top-down work. Cover: (1) data flow end-to-end — trace one critical command from entry to side-effects; state distribution; ordering guarantees; idempotency; (2) failure & resilience — walk unhappy paths; timeout/retry/backoff consistency; ctx cancellation propagation; recovery from partial failure; (3) concurrency & lifecycle — goroutine/task ownership; leak paths; shared mutable state protection; (4) observability — correlation IDs across process boundaries; structured logging consistency; debuggability in prod without redeploys; (5) cross-cutting consistency — subprocess spawn, error wrapping, retry, config loading reinvented vs centralized; (6) config/secrets/blast radius — least privilege; resource limits; credential mount modes; (7) evolvability test — count files touched to add one plausible next feature; (8) architectural drift — stated patterns (in docs/) vs implemented; permanent 'temporary' workarounds. Read-only. Severity tag per finding (Critical/Major/Moderate/Minor). End with 'Top 5 highest-leverage fixes'. file:line citations required."

### Step 4: Consolidate into Must / Should / Could

Merge both agent reports. Apply **architectural** severity judgment — not mechanical (line count, name length):

| Severity | Definition |
|----------|------------|
| **Must Fix** | Correctness, security, data integrity, hard layering violation |
| **Should Fix** | Evolvability, observability, drift; will slow development |
| **Could Fix** | Quality of life; no immediate pain |

Cite file:line on every finding. Drop hallucinations (findings without verifiable citations).

### Step 5: Top 5 Highest-Leverage Fixes

Pick the 5 items with the best (impact / cost) ratio across all severities. These become the actionable shortlist — prioritized recommendation, not exhaustive checklist.

### Step 6: Suggest Follow-Up (Optional)

If findings warrant action, suggest:

- Create a Goal page (Must Fix items as Success Criteria; Should Fix as tasks)
- Per-finding task pages, sequenced by severity
- ADR if any finding surfaced an unstated design decision

Do not create files automatically — surface the suggestion.

## What Gets Reviewed

**Whole codebase**, not a diff. Two orthogonal passes:

- **Top-down** — entry point, packages, layering, seams (structural)
- **Dimensions** — data flow, failure, concurrency, observability, drift (behavioral)

Skip vendor/, mocks/, generated files, lock files.

## Notes

- **Read-only** — agents never modify code
- **Different from `/coding:audit-architecture`** — that's a single-agent quick scan; this is deep parallel with dimensions coverage and Must/Should/Could consolidation
- **Different from `/coding:code-review`** — that's diff-scoped, per-PR; this is whole-codebase, quarterly cadence
- **Skip for small codebases** (<5k LOC) and pre-product-market-fit work
- **Severity discipline** — Must Fix is for correctness/security/data integrity, not "function too long"
- **Output is actionable** — 5 highest-leverage fixes, not a 30-item checklist
