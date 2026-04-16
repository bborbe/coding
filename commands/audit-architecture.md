---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+), Glob
argument-hint: "[directory]"
description: Audit architecture — detect naive extractions, layering leaks, boundary violations
---

## Context

- Current git status: `!git status`
- Recent changes: `!git diff HEAD~1 --stat`
- Current branch: `!git branch --show-current`

## Your Task

Perform a standalone architecture audit focused on **design quality**, not style.

Catches:
- Naive extractions (helpers pulled out just to satisfy length linters)
- Package/module boundary violations
- Dependency direction errors (domain depending on infra/framework)
- Layering leaks (handlers touching DB, domain importing HTTP)
- Abstraction seams missing or over-used
- God packages/modules (`util`, `helpers`, `common` as grab bags)
- Class/struct split without responsibility split
- Import-time side effects (Python)
- Mixin abuse (Python)

### Step 1: Parse Arguments

- Argument = target directory (default: current directory `.`)
- Never resolve `~` — pass as given

### Step 2: Detect Project Type

Use Glob to detect:
- **Go project** — `*.go` files or `go.mod`
- **Python project** — `*.py` files or `pyproject.toml` / `requirements.txt`
- **Mixed** — both present → run both agents

### Step 3: Invoke Agent(s)

Run in parallel using Task tool:

**Go project:**
- subagent_type: `coding:go-architecture-assistant`
- prompt: "Audit Go architecture in [directory]. Focus on: (1) naive extractions driven by funlen/gocognit — helpers called once, generic names (*Impl, *Helper, *Part), introduced in commits where a function dropped to ~79 lines; (2) package boundary violations and dependency direction; (3) layering leaks; (4) abstraction seam quality. Report findings with severity, real structural fixes (not relocation), and the 5 diagnostic questions answered per flagged helper. Read-only — never modify code."

**Python project:**
- subagent_type: `coding:python-architecture-assistant`
- prompt: "Audit Python architecture in [directory]. Focus on: (1) naive extractions driven by C901/PLR0915/pylint length rules — helpers called once, generic names (_impl, _helper, _step), introduced at threshold boundaries; (2) module/package boundary violations; (3) dependency direction (domain must not import framework/ORM); (4) import-time side effects; (5) mixin abuse and deep inheritance; (6) abstraction seams via Protocol/ABC. Report findings with severity, real structural fixes, and the 5 diagnostic questions answered per flagged helper. Read-only."

### Step 4: Present Results

Present each agent's full report. If both ran, group by language.

If no findings: state clearly, no filler.

## What Gets Audited

**Cross-unit concerns only** (unit-level SRP belongs to `srp-checker`; style/idioms to `go-quality-assistant` / `python-quality-assistant`):

- Naive vs. real refactors — distinguished by the 5 diagnostic questions
- Package/module boundaries
- Dependency direction (inward: adapter → app → domain)
- Layering (handler/service/domain separation)
- Abstraction quality (missing seams, over-abstraction)
- God packages/modules
- Extraction quality (does it create a test seam? does it name a concept?)

## Notes

- **Read-only** — agents never modify code
- **Complements `srp-checker`** — SRP = one unit, one reason; architecture = cross-unit design
- **Complements `/coding:code-review full`** — already includes these agents; this command is for standalone focused review
- **Skip on trivial changes** — architecture review is for structural work, not one-line fixes
