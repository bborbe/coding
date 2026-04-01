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
make precommit    # Validates links in README.md and llms.txt
```

## Release Checklist

When releasing a new version, update version in **all three files**:
1. `CHANGELOG.md` — new `## vX.Y.Z` section
2. `.claude-plugin/plugin.json` — `"version"` field
3. `.claude-plugin/marketplace.json` — both `"version"` fields (metadata + plugins array)

Then commit, tag, and push:
```bash
git tag vX.Y.Z && git push && git push origin vX.Y.Z
```

## Writing Docs

- Start with name, brief overview
- Show both GOOD and BAD examples
- Use generic examples (User, Order — not trading domain)
- Use `github.com/bborbe/time`, `bborbe/errors`, `bborbe/collection` in examples
- End with antipatterns section
- Reference related guides with relative links
