Tags: [[Claude Code]] [[Claude Code Plugin System]] [[Claude Code Agent Development]]

---

How to write Claude Code skills — self-contained capabilities that auto-activate based on conversation context.

### RULE skill-writing/scripts-in-scripts-subdir (MUST)

**Owner**: skill-auditor
**Applies when**: a Claude Code skill places executable scripts (`*.sh`, `*.py`) directly alongside `SKILL.md` instead of in a `scripts/` subdirectory.
**Enforcement**: `scripts/rule-checks.sh` (finds `*.sh`/`*.py` directly inside `skills/<name>/` at depth-1)
**Why**: The `scripts/` subdirectory keeps `SKILL.md` discoverable at a glance (one file at top level), groups all executables under a single permission-allowed glob pattern (`Bash(scripts/*.sh)`), and matches the convention every existing bborbe skill follows. Loose-next-to-SKILL.md scripts produce ambiguity ("is this part of the skill or a stray script?") and require enumerating individual files in the skill's `allowed-tools`.

### RULE skill-writing/skill-md-frontmatter-required (MUST)

**Owner**: skill-auditor
**Applies when**: a `skills/<name>/SKILL.md` file is missing the required frontmatter fields — `name:` (must match the directory name) and `description:` (Claude's discovery signal).
**Enforcement**: judgment (YAML-frontmatter inspection: presence of `name` + `description` at the top of every SKILL.md)
**Why**: `description:` is the trigger phrase Claude pattern-matches against conversation context to auto-activate the skill. Without it, the skill is invisible to autonomous discovery — users must type the full `/plugin:skill-name` slash command every time. `name:` is the dispatch key the runtime resolves; mismatch with the directory name produces 404s on invocation. Both fields are cheap to add and break the skill loudly if absent.

## Structure

```
skills/my-skill/
├── SKILL.md              ← required (instructions Claude reads)
└── scripts/
    └── my-script.sh      ← optional (executable logic)
```

Scripts go in a `scripts/` subdirectory, not loose next to SKILL.md.

## SKILL.md Template

```markdown
---
name: my-skill
description: What this does and WHEN to use it. Be specific — triggers matching.
---

## Prerequisites
- What must be true before running

## Steps

1. Run the script:
`` `bash
bash scripts/my-script.sh [args]
`` `

2. Verify output and report to user.

## Success Criteria
- How to know it worked
```

## Slash Command to Invoke a Skill

Skills auto-activate by description match, but users also want `/plugin:skill-name`. Create a thin command wrapper in `commands/`:

**`commands/my-skill.md`:**

```markdown
---
description: Short description of what the skill does
allowed-tools: Skill(plugin-name:my-skill)
---

Invoke the plugin-name:my-skill skill.
```

The command delegates entirely to the skill via `Skill()` tool. No script paths, no logic — just invocation.

## Script Path Resolution

Scripts use **relative paths** (`scripts/watch.sh`), not absolute paths. Claude reads the SKILL.md and executes the script from the skill's directory context.

**Never hardcode paths** like `~/Documents/workspaces/...` or `~/.claude/plugins/marketplaces/...` — these break portability.

## Example: Watch Skill

**`skills/watch/SKILL.md`:**

```markdown
---
name: watch
description: Watch dark-factory progress with sound alerts. Use when user wants to monitor daemon execution.
---

## Prerequisites
- Daemon must be running

## Steps

1. Run via Bash tool with `run_in_background: true` and `timeout: 600000`:
`` `bash
bash scripts/watch.sh [project-dir]
`` `
   - If project dir given, uses it
   - If cwd has `.dark-factory.yaml`, uses cwd
   - Otherwise, auto-detects via `.dark-factory.lock`

2. Show sound legend:
   - 3x Sosumi = failed
   - Basso = stuck >15min
   - Glass = all complete

## Success Criteria
- Script exits 0 on queue completion
- Failed prompts detected and alerted
- Stuck prompts (>15min) alerted
```

**`skills/watch/scripts/watch.sh`:**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Auto-detect project directory
if [ -n "${1:-}" ]; then
  PROJECT_DIR="$1"
elif [ -f ".dark-factory.yaml" ]; then
  PROJECT_DIR="."
else
  # Search for running daemon via lock files
  PROJECT_DIR=""
  for lock in $(find ~/Documents/workspaces -name ".dark-factory.lock" -type f 2>/dev/null); do
    dir=$(dirname "$lock")
    pid=$(cat "$lock" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      PROJECT_DIR="$dir"
      break
    fi
  done
  if [ -z "$PROJECT_DIR" ]; then
    echo "ERROR: No project found."
    exit 1
  fi
fi

cd "$PROJECT_DIR"
echo "Watching: $(pwd)"

# main logic here
```

**`commands/watch.md`:**

```markdown
---
description: Watch dark-factory progress with sound alerts
allowed-tools: Skill(dark-factory:watch)
---

Invoke the dark-factory:watch skill.
```

## Plugin Directory Layout

```
my-plugin/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── commands/           ← user-invoked /commands (thin wrappers)
│   └── my-skill.md    ← invokes skill via Skill() tool
├── skills/             ← auto-activated skills
│   └── my-skill/
│       ├── SKILL.md
│       └── scripts/
│           └── my-script.sh
└── agents/             ← subagent definitions
```

## Key Rules

| Rule | Detail |
|------|--------|
| `description` triggers matching | Be specific — Claude uses this to decide when to activate |
| SKILL.md < 500 lines | Keep focused, one responsibility |
| Scripts in `scripts/` subdir | Not loose next to SKILL.md |
| Scripts must be executable | `chmod +x` after creating |
| Use `set -euo pipefail` | Fail fast in bash scripts |
| Preconditions in script | Check requirements before running |
| Relative script paths | `bash scripts/my-script.sh`, never absolute |
| Command = thin wrapper | `allowed-tools: Skill(name)` + "Invoke the skill." |

## Skill vs Command vs Agent

| Type | When to use |
|------|-------------|
| **Skill** | Self-contained capability with optional scripts. Auto-activates by description match. |
| **Command** | User-invoked via `/name`. Thin wrapper that invokes a skill via `Skill()` tool. |
| **Agent** | Autonomous subagent with own tool access. For complex multi-step workflows. |

## Checklist

- [ ] `SKILL.md` has `name` and `description` in frontmatter
- [ ] `description` explains WHEN to activate (not just what it does)
- [ ] Steps are numbered and concrete
- [ ] Success criteria section present
- [ ] Scripts in `scripts/` subdirectory
- [ ] Bash scripts have `#!/usr/bin/env bash` and `set -euo pipefail`
- [ ] Scripts are `chmod +x`
- [ ] Preconditions checked before main logic
- [ ] Matching command in `commands/` using `Skill()` tool
- [ ] No hardcoded absolute paths
