# Agent & Command Development Guide

Rules-only version. Captures the enforceable conventions for authoring Claude Code agents and slash commands that `coding:agent-auditor` and `coding:slash-command-auditor` check. For deeper rationale, expanded examples, and integration playbooks, consult the official Claude Code documentation at [docs.claude.com/en/docs/claude-code](https://docs.claude.com/en/docs/claude-code).

## The Process

Doc-driven development. The guide is the source of truth; agents reference it; never the other way around.

1. **Write the guide first** — markdown in `docs/`, covers what, why, patterns, anti-patterns, examples.
2. **Create the agent** — `agents/<name>.md` implementing the workflow. References the guide.
3. **Create the command** — `commands/<name>.md` as a thin wrapper invoking the agent.
4. **Test the loop** — run the command, verify the agent reads the guide and produces the expected output.
5. **Iterate on the guide** — every gap surfaced by use goes back into the guide; agents auto-improve as the guide does.

## Architecture Principles

### Separation of Concerns

**Golden Rule**: Command is the interface, Agent has the knowledge.

| | Command (`commands/*.md`) | Agent (`agents/*.md`) |
|---|---|---|
| Size | ~50-100 lines | ~200-500+ lines |
| Responsibility | Parse args, gather context, invoke agent, present report | All analysis, detection, pattern matching, report generation |
| Business logic | **None** | **All of it** |
| Reusability | One-shot interface | Invoked from commands, other agents, workflows |

### RULE agent-cmd/command-thin (MUST)

**Owner**: slash-command-auditor
**Applies when**: any new `commands/*.md` file is added or substantially changed.
**Enforcement**: judgment
**Why**: Commands that grow business logic become unmaintainable. The agent is the home for all detection algorithms, quality checks, and report formatting. Commands that exceed ~100 lines almost always carry leaked logic that belongs in the agent.

#### Bad

```markdown
# /my-command.md (300 lines)
- Argument parsing logic
- Detection algorithms inlined
- Quality check rules inlined
- Report formatting inlined
- Agent invocation buried in the middle
```

#### Good

```markdown
# /my-command.md (50 lines)
- Parse arguments
- Gather context (git status, recent changes)
- Invoke my-assistant agent
- Present report

# my-assistant.md (400 lines)
- All detection algorithms
- All quality checks
- Report generation
- All recommendations
```

## Unattended Execution Patterns

### RULE agent-cmd/no-user-prompts (MUST)

**Owner**: agent-auditor
**Applies when**: any agent or command performs work that could prompt the user (writing to `/tmp/`, requesting permissions, asking confirmation) during normal execution.
**Enforcement**: judgment
**Why**: Interruptions break workflow. Users expect agents to work autonomously. Every approval request adds friction and trains the user to ignore prompts. The goal is unattended behavior.

#### Bad — Inline Script Generation

```bash
# Writes to /tmp/, triggers permission prompt
python3 << 'EOF'
import yt_dlp
ydl = yt_dlp.YoutubeDL()
# ... script code ...
EOF
```

#### Good — Pre-Created Executable Script

```bash
# Lives in ~/.claude/scripts/, no /tmp/ prompt
~/.claude/scripts/youtube-get-transcript.py "https://youtube.com/watch?v=VIDEO_ID"
```

### RULE agent-cmd/scripts-in-claude-dir (MUST)

**Owner**: agent-auditor
**Applies when**: an agent depends on executable scripts (Python, shell) to do real work.
**Enforcement**: judgment
**Why**: Scripts in `~/.claude/scripts/` (or skill-local `scripts/`) are reusable, testable independently, and pre-approved by `permissions` settings. Scripts written on the fly are not.

#### Setup pattern

```bash
# Once, at skill/agent setup time
cat > ~/.claude/scripts/my-script.py << 'EOF'
#!/usr/bin/env python3
import sys
result = do_work(sys.argv[1])
print(result)
EOF
chmod +x ~/.claude/scripts/my-script.py
```

#### Agent invocation

```bash
~/.claude/scripts/my-script.py "$ARGUMENTS"
```

## Data Source Philosophy

### RULE agent-cmd/single-source-of-truth (SHOULD)

**Owner**: agent-auditor
**Applies when**: an agent's domain has multiple potential data sources (config files, APIs, generated artifacts, documentation) and one of them is the authoritative, human-maintained source.
**Enforcement**: judgment
**Why**: Scanning every source is expensive, slow, and produces inconsistent results when sources drift. Pinning to one source forces drift to surface as gaps in *that* source — which is also what drives the documentation feedback loop (below). Performance bonus: single source = bounded scan cost.

#### Pattern

```xml
<constraints>
- NEVER scan generated `build/output/` files (too many files, derived state)
- NEVER call live APIs (rate limits, latency, inconsistent across runs)
- ALWAYS extract information from the canonical documentation directory only
</constraints>
```

### RULE agent-cmd/gap-driven-feedback (SHOULD)

**Owner**: agent-auditor
**Applies when**: an agent depends on documented information that may be incomplete.
**Enforcement**: judgment
**Why**: An agent that silently fills gaps from heuristics produces inconsistent output and never improves. An agent that *complains* about gaps with a precise pointer to the fix surfaces real maintenance work and gets better data on the next run. The feedback loop is the value.

#### Loop

```
Agent runs → finds documentation gaps → reports them with pointers
   ↓
User sees gaps → updates the source → fixes them
   ↓
Agent runs again → fewer gaps → better output
```

#### Gap report shape

```markdown
⚠️ DOCUMENTATION GAPS (Action Required)
────────────────────────────────────────
📖 See: <companion guide path>

CRITICAL GAPS (Block Assessment):
1. <Item> — <what's missing>
   • Impact: <what the agent can't do>
   • Action: <one concrete fix>
   • Template: <pointer to the canonical example>
```

## Command Development

### RULE agent-cmd/command-frontmatter (MUST)

**Owner**: slash-command-auditor
**Applies when**: any `commands/*.md` file is created.
**Enforcement**: judgment
**Why**: Frontmatter is the contract Claude Code reads to dispatch. Missing `description` = no auto-trigger; missing `allowed-tools` = unbounded permissions; missing `argument-hint` = bad UX.

#### Required frontmatter

```yaml
---
description: One-sentence description of what this command does
allowed-tools:
  - Bash(specific-script.sh *)
  - Read
argument-hint: "[arg1|arg2] [arg3]"   # MUST be a quoted string
---
```

### Command structure templates

#### Pattern 1: Analyze only

```markdown
---
description: ...
allowed-tools: [...]
---

## Your task

Invoke the `<name>-assistant` agent with the user's input as context.

Present the agent's report to the user verbatim.
```

#### Pattern 2: Analyze + apply

```markdown
---
description: ...
allowed-tools: [...]
argument-hint: "[--fix]"
---

## Your task

1. Run `<name>-assistant` to analyze.
2. If `--fix` was passed, also invoke `<name>-fixer` to apply changes.
3. Show diff. Ask for confirmation before commit.
```

## Agent Development

### RULE agent-cmd/agent-frontmatter (MUST)

**Owner**: agent-auditor
**Applies when**: any `agents/*.md` file is created.
**Enforcement**: judgment
**Why**: Agents need a `name` + `description` (for Skill-tool auto-invoke) and `tools:` (to bound permissions). Without these the agent is non-discoverable or over-permissioned.

#### Required frontmatter

```yaml
---
name: my-assistant
description: One-sentence summary of when to invoke this agent. Use when <triggers>.
tools: Read, Write, Bash, Grep, Glob
---
```

### Agent body structure (recommended)

```markdown
## When to Use

<concrete triggers + signals; users + auto-discovery>

## Process

1. <step>
2. <step>
3. <step>

## Output Format

<exact shape of the report — headers, severity grouping, etc.>

## Constraints

- NEVER <prohibited action>
- ALWAYS <required action>

## Success Criteria

- <verifiable assertion 1>
- <verifiable assertion 2>
```

## XML Tag Patterns

Use XML tags inside agents when the agent has strong constraints, multiple sub-modes, or structured output requirements. Pattern works well with Claude's instruction-following.

### Common tags

| Tag | Purpose | Use when |
|---|---|---|
| `<constraints>` | Hard NEVER/ALWAYS rules | Agent has prohibitions or requirements |
| `<process>` | Step-by-step workflow | Multi-step agents |
| `<output_format>` | Exact report shape | Structured-output agents |
| `<examples>` | Few-shot exemplars | When pattern matching matters |
| `<error_handling>` | Failure paths | Agents that interact with external systems |

### Example

```xml
<constraints>
- NEVER write to paths outside the working directory
- NEVER execute network requests
- ALWAYS quote findings against the source file with line numbers
</constraints>

<process>
1. Read the input file
2. Apply the rule set (one rule per pass)
3. Aggregate findings
4. Emit the report
</process>
```

## File Organization

```
~/Documents/workspaces/<plugin>/
├── commands/         # slash commands (thin wrappers)
│   └── <name>.md
├── agents/           # agents (the knowledge)
│   └── <name>.md
├── docs/             # source-of-truth guides (rules-only here; comprehensive elsewhere)
│   └── <topic>-guide.md
├── rules/            # ast-grep YAMLs for mechanical rules
│   └── <lang>/
│       └── <slug>.yml
├── skills/           # SKILL.md skills + colocated scripts/
│   └── <name>/
│       ├── SKILL.md
│       └── scripts/
└── scripts/          # plugin-wide helper scripts
```

## Naming Conventions

| Artifact | Convention | Example |
|---|---|---|
| Command file | `<verb>-<noun>.md` or `<noun>.md` | `pr-review.md`, `audit-guide.md` |
| Agent file | `<noun>-<role>.md` | `go-quality-assistant.md`, `agent-auditor.md` |
| Skill dir | `<name>/SKILL.md` | `pr-watch/SKILL.md` |
| Guide file | `<topic>-guide.md` | `go-error-wrapping-guide.md` |
| Rule YAML | `<slug>.yml` | `no-fmt-errorf.yml` |

Slash commands and skills can share names (`/pr-watch` may resolve to either) — prefer one form per concept.

## Quality Checklist

Before merging any new agent or command:

- [ ] **Command ≤ 100 lines** (`agent-cmd/command-thin`)
- [ ] **No user prompts during normal execution** (`agent-cmd/no-user-prompts`)
- [ ] **All scripts pre-created in `~/.claude/scripts/` or skill-local `scripts/`** (`agent-cmd/scripts-in-claude-dir`)
- [ ] **Frontmatter complete** — `description`, `allowed-tools`, `argument-hint` for commands; `name`, `description`, `tools` for agents (`agent-cmd/command-frontmatter`, `agent-cmd/agent-frontmatter`)
- [ ] **Single source of truth identified** when domain has multiple sources (`agent-cmd/single-source-of-truth`)
- [ ] **Gap-driven feedback** — agent reports missing data with pointers to fix (`agent-cmd/gap-driven-feedback`)
- [ ] **References to the guide use `coding/docs/` paths** that exist for any plugin installer (no personal vault paths)
- [ ] **Generic examples only** — use User, Order, Product, Customer in code samples; never project-specific domain terms (e.g. terms tied to a single product line) that other installers won't recognize
- [ ] **`README.md` + `llms.txt` entries** added for the new agent/command

## Further Reading

- [Claude Code documentation](https://docs.claude.com/en/docs/claude-code) — official authoring reference.
- [Claude Code skill writing guide](claude-code-skill-writing-guide.md) — companion guide for `skills/<name>/SKILL.md` artifacts (not covered here).
- Plugin architecture and skill conventions evolve with Claude Code releases; this guide tracks the rules-only subset enforced by the `coding` plugin's auditors.
