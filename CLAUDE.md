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
| `go-architecture-patterns.md` | `go-architecture-assistant` (rule-block owner; cross-unit concerns) + `go-quality-assistant` (broader review) |
| `go-context-cancellation-in-loops.md` | `go-context-assistant` |
| `go-error-wrapping-guide.md` | `go-error-assistant` |
| `go-time-injection.md` | `go-time-assistant` |
| `go-prometheus-metrics-guide.md` | `go-metrics-assistant` |
| `go-factory-pattern.md` | `go-factory-pattern-assistant` |
| `go-http-handler-refactoring-guide.md` | `go-http-handler-assistant` |
| `go-json-error-handler-guide.md` | `go-http-handler-assistant` |
| `go-linting-guide.md` | `go-quality-assistant` |
| `go-state-machine-pattern.md` | `go-architecture-assistant` |
| `go-service-implementation-patterns.md` | `go-architecture-assistant` |
| `go-kubernetes-crd-controller-guide.md` | `go-architecture-assistant` |
| `go-functional-options-pattern.md` | `go-quality-assistant` |
| `go-doc-best-practices.md` | `godoc-assistant` |
| `go-testing-guide.md` | `go-test-quality-assistant` |
| `go-security-linting.md` | `go-security-specialist` |
| `go-licensing-guide.md` | `license-assistant` |
| `agent-command-development-guide.md` | `agent-auditor` + `slash-command-auditor` |
| `claude-code-skill-writing-guide.md` | `skill-auditor` |
| `python-architecture-patterns.md` | `python-architecture-assistant` |
| `python-ioc-guide.md` | `python-architecture-assistant` |
| `python-logging-guide.md` | `python-quality-assistant` |
| `python-pydantic-guide.md` | `python-quality-assistant` |
| `python-project-structure.md` | `python-architecture-assistant` |
| `python-makefile-commands.md` | `python-quality-assistant` |
| `go-mod-replace-guide.md` | `go-quality-assistant` |
| `go-glog-guide.md` | `go-quality-assistant` |
| `go-concurrency-patterns.md` | `go-architecture-assistant` |
| `go-http-service-guide.md` | `go-http-handler-assistant` |
| `go-cqrs.md` | `go-architecture-assistant` |
| `go-cli-guide.md` | `go-quality-assistant` |
| `go-enum-type-pattern.md` | `go-architecture-assistant` |
| `go-composition.md` | `go-architecture-assistant` |
| `go-build-args-guide.md` | `go-quality-assistant` |
| `go-mod-dependency-fix-guide.md` | `go-quality-assistant` |
| `go-makefile-commands.md` | `go-quality-assistant` |
| `go-patterns.md` | `go-quality-assistant` |

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

## Dark Factory Workflow

**Never code directly.** All code changes go through the dark-factory pipeline.

### What to do

1. **Assess the change size:**

| Change | Action |
|--------|--------|
| Doc-only edit, README typo, llms.txt entry | Direct commit — no dark-factory ceremony |
| Add a `### RULE` block + ast-grep YAML to an existing doc | Write a prompt → [[Dark Factory - Write Prompts]] |
| Bootstrap pass across many docs | Mirror prompt template per doc → standalone prompts |
| Multi-prompt feature with shared interfaces | Write a spec first → [[Dark Factory - Write Spec]] |

2. **Read the relevant guide before starting** — every time, not from memory:
   - Writing a spec → [[Dark Factory - Write Spec]] + [[Dark Factory Guide#Specs What Makes a Good Spec]]
   - Writing prompts → [[Dark Factory - Write Prompts]] + [[Dark Factory Guide#Prompts What Makes a Good Prompt]]
   - Running prompts → [[Dark Factory - Run]]

3. **Follow the guide step by step.** Do not skip audit steps.

### Key rules

- Prompts go to **`prompts/`** (inbox) — never to `prompts/in-progress/` or `prompts/completed/`
- Specs go to **`specs/`** (inbox) — never to `specs/in-progress/` or `specs/completed/`
- Never number filenames — dark-factory assigns numbers on approve
- Never manually edit frontmatter status — use CLI (`dark-factory prompt approve`, `dark-factory spec approve`)
- Always audit before approving (`/dark-factory:audit-prompt`, `/dark-factory:audit-spec`)
- **Never approve or run dark-factory without explicit user confirmation**
- `autoRelease: false` — dark-factory commits locally; release is handled by maintainer-agent-releaser per `.maintainer.yaml`

## Development Standards

### Build and test

```bash
make precommit       # validates links + JSON syntax (the standard verification command)
make release-check   # adds check-versions on top — run before tagging
make build-index     # regenerates rules/index.json from ### RULE blocks (Phase 1c+)
```

### Project layout

- `docs/` — prose guides + inline `### RULE` blocks (rule source of truth)
- `rules/` — ast-grep YAML detectors (mechanical layer; new in Phase 0+)
- `agents/` — specialist agents; reference docs by path
- `commands/` — slash command thin wrappers
- `scripts/` — build/check helpers (Python stdlib for `build-index.py`, bash for the rest)
- `prompts/`, `specs/` — dark-factory inboxes

### Test conventions

Plugin-only repo — no Go/Python test suite. Quality gates:
- `shellcheck` for `scripts/*.sh`
- `jq` for JSON syntax of `.claude-plugin/*.json`
- Markdown link validation in `make precommit`

## 🚨 Version Alignment — MANDATORY at release time

**Four version strings MUST equal each other at release time:**
1. `CHANGELOG.md` — top `## vX.Y.Z` entry (the most-recent versioned section)
2. `.claude-plugin/plugin.json` — `"version"` field
3. `.claude-plugin/marketplace.json` — `metadata.version`
4. `.claude-plugin/marketplace.json` — `plugins[0].version`

`make check-versions` (script: `scripts/check-versions.sh`) fails non-zero if any of the four diverge. It is NOT wired into `make precommit` — drift during development is allowed; alignment is enforced by `make release-check` before tagging. Same shape as `dark-factory` / `vault-cli` / `semantic-search`.

**Every release commit (Workflow B in `/coding:commit`) bumps all four together** — even guide-only patch releases. Plugin manifests are NOT decoupled from the git tag; users running `claude plugin update coding@coding` rely on the manifest version matching the tag.

Full procedure: see `docs/releasing-coding.md`.

## Release Checklist

When releasing a new version vX.Y.Z, update **all four** version strings together, then commit + tag + push:

1. `CHANGELOG.md` — rename `## Unreleased` → `## vX.Y.Z` (or create new section)
2. `.claude-plugin/plugin.json` — `"version": "X.Y.Z"`
3. `.claude-plugin/marketplace.json` — `metadata.version` and `plugins[0].version` (both → `"X.Y.Z"`)
4. `make release-check` — must pass (precommit + check-versions)
5. `git add -A && git commit -m "release vX.Y.Z" && git tag vX.Y.Z && git push && git push origin vX.Y.Z`

The `/coding:commit` skill should drive this — but if invoked manually, run `make release-check` after the manifest edits and before the commit.

## Writing Docs

- Start with name, brief overview
- Show both GOOD and BAD examples
- Use generic examples (User, Order — not trading domain)
- Use `github.com/bborbe/time`, `bborbe/errors`, `bborbe/collection` in examples
- End with antipatterns section
- Reference related guides with relative links
