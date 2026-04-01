# CLAUDE.md Guide

Guide for writing CLAUDE.md files. CLAUDE.md is operational context for AI agents working in the codebase — it tells them how to change the code safely.

## CLAUDE.md vs README.md

| | README.md | CLAUDE.md |
|---|---|---|
| **Audience** | Humans browsing GitHub | AI agents coding in the project |
| **Purpose** | What it does, install, use | How to change the code safely |
| **Tone** | Welcoming, explanatory | Terse, imperative |
| **Contains** | Features, install, usage, config, license | Build commands, architecture map, constraints |
| **Never contains** | Architecture internals, workflow rules | Install instructions, feature marketing |

### Rule of Thumb

- If a human needs it to **use** the project → README.md
- If an agent needs it to **change** the project → CLAUDE.md
- If both need it → README.md gets the user-facing version, CLAUDE.md gets the dev-facing version

### What NOT to Put in CLAUDE.md

- Install/usage instructions (README)
- Feature descriptions or marketing (README)
- Full API docs (docs/ or GoDoc)
- History or rationale for past decisions (ADRs)
- Content derivable from code (`git log`, `grep`, reading files)

## Structure

Every CLAUDE.md follows this order:

```markdown
# CLAUDE.md

One-line project summary.

## Development Standards
[build, test, env, toolchain]

## Architecture
[package map, entry points, key files]

## Key Design Decisions
[constraints the agent must respect]
```

Optional sections (add only when needed):
- **Release Checklist** — multi-file version bumps
- **Plugin/Extension** — if project ships a plugin
- **Workflow Extensions** — dark-factory, CI-specific rules

## 1. Project Summary

One sentence. The agent needs domain context, not a sales pitch.

```markdown
# CLAUDE.md

Obsidian vault task management CLI — fast CRUD for markdown files.
```

```markdown
# CLAUDE.md

Dependency updater — batch-updates Go modules, Python packages, and Docker images.
```

## 2. Development Standards

What the agent needs to build, test, and validate changes.

### What to Include

- **Toolchain** — language, package manager, build system
- **Build commands** — `make precommit`, `make test`
- **Environment variables** — anything needed before builds (e.g., `GOPRIVATE`)
- **Test conventions** — framework, mock tool, test package style
- **Coding guidelines** — link to shared guidelines if applicable

### Example: Go Project

```markdown
## Development Standards

This project follows the [coding-guidelines](https://github.com/bborbe/coding-guidelines).

### Build and test

- `make precommit` — lint + format + generate + test + checks
- `make test` — tests only

### Test conventions

- Ginkgo/Gomega test framework
- Counterfeiter for mocks (`mocks/` dir)
- External test packages (`*_test`)
```

### Example: Python Project

```markdown
## Development Standards

### Toolchain

- Python project using `uv` and `hatchling`
- Source at `src/updater/`
- `make precommit` — format + test + lint + typecheck
- `make test` — tests only

### Test conventions

- pytest test framework
- Tests in `tests/`
```

### Example: Private Modules

```markdown
### Environment

Before any Go commands that resolve modules:

```bash
export GOPRIVATE=bitbucket.seibert.tools/*
export GONOSUMCHECK=bitbucket.seibert.tools/*
```
```

## 3. Architecture

The agent's map of the codebase. Tells it where to look and what each part owns.

### Rules

- One line per package/directory or key file
- Start with the entry point
- Describe what it does, not how
- Use function/type names, never line numbers
- For CLI tools: include entry point → pipeline/command mapping

### Example: Package Map

```markdown
## Architecture

- `main.go` — CLI entry point, subcommands: `run`, `status`, `prompt approve`
- `pkg/config/` — Configuration parsing (`.dark-factory.yaml`)
- `pkg/executor/` — Execute single prompt via Docker container
- `pkg/factory/` — Wire dependencies, create processor
- `pkg/git/` — Git operations: clone, branch, commit, push, PR
- `pkg/processor/` — Core orchestration: pick up prompts, execute, handle results
```

### Example: CLI Entry Points with Pipelines

For projects with multiple CLI commands mapping to different workflows:

```markdown
## Architecture

### CLI Entry Points -> Pipelines

| Command | Function | Pipeline Steps |
|---------|----------|----------------|
| `update-deps` | `main_async` | GitSync -> GoVersion -> Excludes -> Deps -> Precommit -> Changelog -> Commit |
| `update-go-only` | `main_go_only_async` | Same but GoDepSkipStep instead of GoDepUpdateStep |
| `release-only` | `main_release_async` | Release -> GitCommit -> GitPush |

### Adding a new pipeline

1. Add `process_single_*` function in `cli.py`
2. Add `main_*_async` + `main_*` entry points
3. Register entry point in `pyproject.toml`
4. Add tests
```

### Example: Pointer to External Doc

When architecture is complex, keep CLAUDE.md brief and point to a doc:

```markdown
## Architecture & Patterns

See **[docs/development-patterns.md](docs/development-patterns.md)** — architecture, adding commands, multi-vault, output format, testability, naming.
```

## 4. Key Design Decisions

Constraints the agent must respect. Without these, the agent will make reasonable-looking changes that violate your architecture.

### What to Include

- Architectural invariants (what talks to what)
- State management approach
- Processing model (sequential, parallel, retry)
- Forbidden patterns

### Example

```markdown
## Key Design Decisions

- **Frontmatter = state** — no database, prompt file frontmatter tracks status
- **YOLO has NO git access** — all git ops on host; clone mounted read-write for code only
- **Sequential processing** — one prompt at a time per project
- **Stop on failure** — never skip failed prompts
- **Factory functions are pure composition** — no conditionals, no I/O, no context.Background()
- **`pkg/ops/` is a library layer** — operations return structured results, never write to stdout
- **No direct file editing of go.mod** — always use `go mod edit` commands
```

## 5. Release Checklist (Optional)

Only when releasing requires updating multiple files beyond CHANGELOG.md.

```markdown
## Release Checklist

When releasing a new version, update version in **all three files**:
1. `CHANGELOG.md` — new `## vX.Y.Z` section
2. `.claude-plugin/plugin.json` — `"version"` field
3. `.claude-plugin/marketplace.json` — both `"version"` fields
```

## Common Mistakes

### README content in CLAUDE.md

The agent doesn't need install instructions, feature lists, or usage examples. It needs build commands, architecture, and constraints.

**Bad:** Listing all CLI flags and usage examples in CLAUDE.md.
**Good:** CLI flag docs in README.md, entry point -> pipeline mapping in CLAUDE.md.

### Too much detail

CLAUDE.md is not documentation. It's operational context. Keep it scannable.

**Bad:** Explaining the history of why you chose Ginkgo over `testing`.
**Good:** `Ginkgo/Gomega test framework` — the agent knows what to do.

### Missing architectural constraints

The agent will happily refactor your factory to include business logic, add `context.Background()` calls, or put handlers in `main.go` — unless you tell it not to.

**Bad:** No mention of zero-business-logic factory rule.
**Good:** `Factory functions are pure composition — no conditionals, no I/O, no context.Background()`

### Stale information

Use function/type names, not line numbers. Keep CLAUDE.md updated when architecture changes. Stale CLAUDE.md is worse than no CLAUDE.md.

### Duplicating README

If CLAUDE.md and README.md both list CLI commands, they will drift apart. Pick one owner per piece of content.

## Checklist

Before committing a CLAUDE.md:

- [ ] One-line project summary at the top
- [ ] Build command documented (`make precommit` or equivalent)
- [ ] Test framework and mock tool named
- [ ] Environment variables listed (if any)
- [ ] Every key package/directory has a one-line description
- [ ] Key design decisions that an agent could violate are listed
- [ ] No line numbers — use function/type names instead
- [ ] No stale references to removed code
- [ ] No README content (install, usage, features) duplicated here
- [ ] No content derivable from code (git log, grep)
