# CLAUDE.md

Instructions for working on the `bborbe/coding` plugin repository.

## What This Is

Claude Code plugin with coding guidelines (`docs/`), quality agents (`agents/`), and slash commands (`commands/`). Installed via `claude plugin install coding`.

## Rules

### General-Purpose Content Only

- **NEVER** include trading/project-specific examples (no Candle, Epic, Broker, SignalStore)
- **ALWAYS** use generic examples (User, Order, Product, Customer)
- This repo serves anyone learning Go/Python patterns

### Doc ↔ Agent Alignment

Each enforceable guide in `docs/` should have a matching agent in `agents/`. The agent reads its doc as source of truth — rules live in docs, not duplicated in agents.

| Doc | Agent |
|-----|-------|
| `go-architecture-patterns.md` | `go-quality-assistant` |
| `go-context-cancellation-in-loops.md` | `go-context-assistant` |
| `go-error-wrapping-guide.md` | `go-error-assistant` |
| `go-time-injection.md` | `go-time-assistant` |
| `go-prometheus-metrics-guide.md` | `go-metrics-assistant` |
| `go-factory-pattern.md` | `go-factory-pattern-assistant` |
| `go-http-handler-refactoring-guide.md` | `go-http-handler-assistant` |
| `go-doc-best-practices.md` | `godoc-assistant` |
| `go-testing-guide.md` | `go-test-quality-assistant` |
| `go-security-linting.md` | `go-security-specialist` |
| `go-licensing-guide.md` | `license-assistant` |

Reference-only docs (patterns, setup guides) don't need agents.

### Command = Thin Wrapper

Commands parse arguments, detect project type, invoke agents, merge reports. No inline rules — delegate to agents.

### Plugin Namespacing

All agent references from commands must use `coding:` prefix:
```
subagent_type="coding:go-quality-assistant"
```

### Self-Contained

No references to `~/.claude/`, `/Users/bborbe/`, or other personal paths. Plugin must work for anyone who installs it.

## File Structure

```
.claude-plugin/     Plugin metadata (marketplace.json, plugin.json)
agents/             Quality agents (read docs/, invoked by commands/)
commands/           Slash commands (thin wrappers around agents)
docs/               Coding guidelines (source of truth for rules)
skills/             IDE launchers (vscode, intellij)
templates/          Project templates (Makefile, tools.go, .gitignore)
```

## When Changing Files

### Adding a new guide
1. Create `docs/new-guide.md`
2. Add to `README.md` in appropriate table
3. Update `llms.txt`
4. If enforceable: create matching agent in `agents/`
5. If agent created: add to `code-review.md` agent list

### Adding a new agent
1. Create `agents/new-agent.md` with matching doc reference
2. Add to `code-review.md` (standard or full mode)
3. Add to `README.md` agents table

### Adding a new command
1. Create `commands/new-command.md` — thin wrapper
2. Use `coding:` prefix for agent references
3. Add to `README.md` commands table

### Renaming/deleting
1. Update all cross-references in other docs
2. Update README.md tables
3. Update llms.txt
4. Update code-review.md if agent affected

## Build

```bash
make precommit    # Validates links + JSON syntax + version alignment (4 places)
```

## 🚨 Version Alignment — MANDATORY

**Four version strings MUST always equal each other:**
1. `CHANGELOG.md` — top `## vX.Y.Z` entry (the most-recent versioned section)
2. `.claude-plugin/plugin.json` — `"version"` field
3. `.claude-plugin/marketplace.json` — `metadata.version`
4. `.claude-plugin/marketplace.json` — `plugins[0].version`

`make precommit` runs `check-versions` which fails the build if any of the four diverge. Never commit a release with mismatched versions.

**Every release commit (Workflow B in `/coding:commit`) bumps all four together** — even guide-only patch releases. Plugin manifests are NOT decoupled from the git tag; users running `claude plugin update coding@coding` rely on the manifest version matching the tag.

## Release Checklist

When releasing a new version vX.Y.Z, update **all four** version strings together, then commit + tag + push:

1. `CHANGELOG.md` — rename `## Unreleased` → `## vX.Y.Z` (or create new section)
2. `.claude-plugin/plugin.json` — `"version": "X.Y.Z"`
3. `.claude-plugin/marketplace.json` — `metadata.version` and `plugins[0].version` (both → `"X.Y.Z"`)
4. `make precommit` — must pass (includes `check-versions`)
5. `git add -A && git commit -m "release vX.Y.Z" && git tag vX.Y.Z && git push && git push origin vX.Y.Z`

The `/coding:commit` skill should drive this — but if invoked manually, run `make precommit` after the manifest edits and before the commit.

## Writing Docs

- Start with name, brief overview
- Show both GOOD and BAD examples
- Use generic examples (User, Order — not trading domain)
- Use `github.com/bborbe/time`, `bborbe/errors`, `bborbe/collection` in examples
- End with antipatterns section
- Reference related guides with relative links
