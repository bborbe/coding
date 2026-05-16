# Agent & Command Development Guide

**Purpose**: Guide for creating new Claude Code agents and slash commands following established patterns.

**Last Updated**: 2025-12-22

---

## The Process

### Step 1: Write the Guide (Foundational Documentation)

**Where**: `~/Documents/workspaces/coding/docs/` or Obsidian

**Purpose**: Document the concept, topic, or goal in detail as a simple Markdown file.

**What to include**:
- What you want to achieve
- Why it matters (business/technical context)
- Detailed patterns and examples
- Best practices and anti-patterns
- Templates and reference material

**Examples**:
- `documentation-guide.md` - Complete documentation standards
- `go-testing-guide.md` - Testing patterns and conventions
- `go-factory-pattern.md` - Factory pattern implementation
- `go-http-handler-refactoring-guide.md` - Handler organization

**Key principle**: The guide is the **source of truth**. Agents reference it.

---

### Step 2: Create the Agent (Heavy Lifting)

**Where**: `~/.claude/agents/`

**Purpose**: Implement the logic that analyzes/fixes/generates based on the guide.

**The agent does**:
- References the guide from Step 1
- Implements analysis logic
- Detects violations/gaps
- Provides actionable feedback
- Generates fixes (if applicable)
- Creates comprehensive reports

**Common agent modes**:
- **Review/Analyze mode** - Check for issues, report findings
- **Fix/Generate mode** - Apply fixes, generate code/docs
- **Multiple depth levels** - Quick/Standard/Full analysis

**Key principle**: Agent contains **all implementation logic**.

---

### Step 3: Create the Command (Execution Wrapper)

**Where**: `~/.claude/commands/`

**Purpose**: Thin wrapper that invokes the agent.

**The command does**:
- Parse arguments (mode, directory, options)
- Invoke agent via Task tool
- Present agent's report
- **Nothing else**

**Common command patterns**:

**Analyze + Fix modes**:
```markdown
- `/my-command` or `/my-command analyze` - Review and report
- `/my-command fix` - Apply fixes automatically
```

**Depth levels**:
```markdown
- `/my-command quick` - Fast, structure check only
- `/my-command` or `/my-command standard` - Balanced (default)
- `/my-command full` - Comprehensive, deep analysis
```

**Key principle**: Command is **just the interface** (~50 lines).

---

### Step 4: Integration (Optional)

**Where**: Existing agents/commands (e.g., `/code-review`)

**Purpose**: Integrate into larger workflows if the check/fix is broadly useful.

**Integration points**:
- **Code review** - Add to `/code-review` agent list
- **Pre-commit** - Add to validation workflow
- **Pre-implementation** - Add to guideline check
- **Agent collaboration** - Reference in related agents

**Examples**:
- `documentation-quality-assistant` integrated into code review process
- `go-factory-pattern-assistant` part of standard code review
- `go-http-handler-assistant` invoked during architecture review

**Key principle**: Integrate where it adds value to existing workflows.

---

## Table of Contents

1. [Process Overview](#the-process)
2. [Architecture Principles](#architecture-principles)
3. [Unattended Execution Patterns](#unattended-execution-patterns) ⭐ **CRITICAL**
4. [Data Source Philosophy](#data-source-philosophy) ⭐ **NEW**
5. [Command Development](#command-development)
6. [Agent Development](#agent-development)
7. [XML Tag Patterns](#xml-tag-patterns-preferred-for-complex-agents) ⭐ **NEW**
8. [File Organization](#file-organization)
9. [Naming Conventions](#naming-conventions)
10. [Examples & Templates](#examples--templates)
11. [Integration Patterns](#integration-patterns)
12. [Quality Checklist](#quality-checklist)

---

## Architecture Principles

### Separation of Concerns

**Golden Rule**: Command is the interface, Agent has the knowledge.

**Command Responsibilities** (~50-100 lines):
- Parse and validate arguments
- Provide context (git status, recent changes, etc.)
- Invoke agent(s) via Task tool
- Present agent's report to user
- NO business logic or implementation details

**Agent Responsibilities** (~200-500+ lines):
- Complete workflow implementation
- All analysis and detection logic
- Pattern matching and quality checks
- Severity categorization
- Report generation
- Recommendations and examples
- Integration with other tools/agents

### Why This Matters

**Maintainability**: Logic lives in one place (agent), not scattered across commands
**Reusability**: Agents can be invoked from multiple contexts (commands, other agents, workflows)
**Clarity**: Commands are thin, readable wrappers
**Consistency**: All implementation details follow agent's patterns
**Testability**: Agents can be tested independently

### Real-World Example

**Bad** ❌:
```markdown
# /my-command.md (300 lines)
- Parsing logic
- Detection algorithms
- Quality checks
- Report formatting
- Agent invocation (buried in middle)
```

**Good** ✅:
```markdown
# /my-command.md (50 lines)
- Parse arguments
- Invoke my-assistant agent
- Present report

# my-assistant.md (400 lines)
- All detection algorithms
- All quality checks
- Complete report generation
- All recommendations
```

---

## Unattended Execution Patterns

### Critical Principle: No User Interruptions

**Golden Rule**: Agents must execute without requiring user approval or interaction during normal execution.

**Why this matters**:
- Interruptions break workflow and degrade user experience
- Users expect agents to work autonomously without prompts
- Repeated approval requests for `/tmp/` or system directories are frustrating
- Each interruption adds friction and delays
- Goal is **unattended behavior** - agents that complete their work independently

### Pattern 1: Use Pre-Created Executable Scripts

**Problem**: Generating Python/shell scripts on-the-fly requires writing to `/tmp/`, triggering permission prompts.

**❌ BAD - Inline Script Generation**:
```bash
python3 << 'EOF'
import yt_dlp
# Fetch YouTube transcript
ydl = yt_dlp.YoutubeDL()
# ... script code ...
EOF
```

**Why it's bad**:
- Writes to `/tmp/` → permission prompt
- Not reusable across invocations
- Hard to test independently
- Clutters agent code with implementation details

**✅ GOOD - Pre-Created Script**:
```bash
~/.claude/scripts/youtube-get-transcript.py "https://youtube.com/watch?v=VIDEO_ID"
```

**Setup once**:
```bash
# Create script in ~/.claude/scripts/
cat > ~/.claude/scripts/my-script.py << 'EOF'
#!/usr/bin/env python3
import sys

# Script implementation
result = do_work(sys.argv[1])
print(result)  # Output to stdout
EOF

# Make executable
chmod +x ~/.claude/scripts/my-script.py
```

**Agent configuration**:
```yaml
---
name: my-agent
allowed-tools: Bash(~/.claude/scripts/my-script.py:*)
---
```

**Benefits**:
- **Predictable**: Script logic separate from agent prompts
- **Testable**: Scripts can be tested independently
- **Maintainable**: Updates to logic don't require agent changes
- **Reusable**: Scripts can be called from multiple agents
- **Short agents**: Keeps agent prompts concise and focused

### Pattern 1b: Scripts for Complex Validation Logic

**Use case**: When agents need to perform complex bash logic that would clutter the agent prompt.

**❌ BAD - Complex Logic in Agent Prompt**:
```markdown
## Instructions

Run these bash commands to validate git configuration:

REMOTE_URL=$(git remote get-url origin 2>/dev/null)
if [[ "$REMOTE_URL" =~ bitbucket\.seibert\.tools ]] || \
   [[ "$REMOTE_URL" =~ github\.com[:/]seibert-media/ ]]; then
    REPO_TYPE="seibert"
    EXPECTED_EMAIL="@seibert.group"
    # ... 50 more lines of validation logic ...
elif [[ "$REMOTE_URL" =~ github\.com[:/]bborbe/ ]]; then
    REPO_TYPE="personal"
    # ... more complex logic ...
fi

# ... more validation checks ...
```

**Why it's bad**:
- Agent prompt becomes 100+ lines of bash
- Hard to read and understand the workflow
- Bash syntax errors hard to debug in markdown
- Logic mixed with workflow description

**✅ GOOD - Extract to Script**:

**Script** (`~/.claude/scripts/git-validate-config.sh`):
```bash
#!/usr/bin/env bash
# Git Configuration Validation Script
# Validates git config based on repository context (Seibert vs Personal)

# ... complete validation logic (100+ lines) ...
# Detects repo type from remote URL
# Validates email, GPG key, branch naming, ancestry
# Outputs warnings in consistent format
# Returns 0 (non-blocking)
```

**Agent prompt** (concise):
```markdown
## Instructions

Run validation script:
```bash
~/.claude/scripts/git-validate-config.sh
```

The script will:
- Detect repository type from git remote
- Validate email, GPG key, and signing
- Check branch naming and ancestry (if applicable)
- Display non-blocking warnings with fix commands

**Implementation details:** See `~/Documents/Obsidian/50 Knowledge Base/Git Multi-Context Configuration Pattern.md`
```

**Benefits**:
- Agent prompt stays under 50 lines
- Bash logic tested independently
- Validation logic documented in knowledge base
- Agent focuses on workflow, not implementation
- Easy to update validation rules without touching agent

**Real-world example**: `git-commit-assistant` uses `git-validate-config.sh` to keep agent focused on commit workflow rather than validation implementation.

### Pattern 2: Output to Stdout, Not Files

**Problem**: Writing temp files requires permissions, cleanup, and adds complexity.

**✅ GOOD - Stdout-Based Communication**:

**Generic agent outputs to stdout**:
```markdown
---
name: youtube-transcript-agent
description: Fetch transcript for any YouTube video (generic utility)
tools: Bash
allowed-tools: Bash(~/.claude/scripts/youtube-get-transcript.py:*)
---

## Workflow

Execute script and output to stdout:
```bash
~/.claude/scripts/youtube-get-transcript.py "$URL"
```

Script prints formatted transcript directly to stdout.
No temp files created.
```

**Command captures stdout and writes project files**:
```markdown
---
name: youtube-source-page
allowed-tools: Task, Write
---

## Workflow

Step 1: Launch agent
```
Task(youtube-transcript-agent, url)
```

Step 2: Capture stdout from agent
```
transcript_content = agent_stdout_output
```

Step 3: Write to project file (command knows project structure)
```
Write(
  file_path: "/Users/bborbe/Documents/Obsidian/70 Source Material/YouTube/transcript.md",
  content: transcript_content
)
```
```

**Why this works**:
- Generic agents stay generic (no project paths)
- No temp files needed
- No user interruptions for agents
- Commands handle project-specific I/O
- Enables unattended execution

### Pattern 3: Use Project Paths, Not System Temp

**Problem**: Using `/tmp/` or system directories triggers approval requests.

**❌ BAD - System Temp Directory**:
```bash
# Writes to /tmp/ → user interruption
/tmp/youtube-transcript.md
/tmp/processing/data.json
```

**✅ GOOD - Project Directory**:
```bash
# Within project working directory → no interruption
/Users/bborbe/Documents/Obsidian/70 Source Material/YouTube/VIDEO_ID-transcript.md
/Users/bborbe/Documents/myproject/.cache/processing.json
```

**If temp files are truly needed**:
- Create them in project directory
- Document they're temporary
- Clean them up after use
- Commands handle this, not agents

### Pattern 4: Scope allowed-tools Appropriately

**Problem**: Overly broad permissions (`Bash:*`) allow risky operations and may trigger approval requests.

**❌ BAD - Too Broad**:
```yaml
allowed-tools: Bash:*              # Allows anything
allowed-tools: Bash(python3:*)     # Allows inline scripts
```

**✅ GOOD - Specific and Scoped**:
```yaml
# Specific script only
allowed-tools: Bash(~/.claude/scripts/youtube-get-transcript.py:*)

# Specific command pattern
allowed-tools: Bash(yt-dlp:*)

# Read-only git operations
allowed-tools: Bash(git status:*), Bash(git diff:*)

# Project-specific tools
allowed-tools: Bash(make test:*), Bash(go build:*)
```

### Common Anti-Patterns to Avoid

**❌ Anti-Pattern 1: Inline Script Generation**
```bash
# DON'T DO THIS
python3 << 'EOF'
import yt_dlp
# ... code ...
EOF
```

**Fix**: Create `~/.claude/scripts/script-name.py`

**❌ Anti-Pattern 2: Generic Agents Writing Project Files**
```yaml
# DON'T DO THIS
name: youtube-transcript-agent  # Generic utility
tools: Write                     # Writing project-specific files
# Agent writes to /Users/bborbe/Documents/Obsidian/...
```

**Fix**: Agent outputs to stdout, command writes files

**❌ Anti-Pattern 3: Unnecessary Temp Files**
```markdown
Step 1: Write data to /tmp/data.txt
Step 2: Read /tmp/data.txt
Step 3: Process and delete /tmp/data.txt
```

**Fix**: Pass data via stdout/variables, no files needed

**❌ Anti-Pattern 4: Missing Error Handling**
```bash
~/.claude/scripts/fetch-data.py "$URL"
# Assumes success, doesn't check exit code
```

**Fix**: Check exit codes, provide clear errors
```bash
if ! output=$(~/.claude/scripts/fetch-data.py "$URL" 2>&1); then
    echo "ERROR: Failed to fetch data"
    echo "Details: $output"
    exit 1
fi
```

**❌ Anti-Pattern 5: Glob with Tilde or $HOME Path**
```markdown
# DON'T DO THIS
Use Glob tool to check `~/.claude/prompts/*.md`
Glob pattern="~/Documents/Obsidian/**/*.md"
Glob pattern="$HOME/Documents/Obsidian/**/*.md"
```

**Why it fails**: Glob tool doesn't expand `~` or `$HOME` - they're passed literally and match nothing.

**Fix**: Use absolute paths for Glob patterns
```markdown
# DO THIS
Use Glob tool to check `/Users/bborbe/.claude/prompts/*.md`
Glob pattern="/Users/bborbe/Documents/Obsidian/**/*.md"
```

**Alternative**: Use Bash `ls` which expands `~` via shell
```bash
ls ~/.claude/prompts/*.md
```

### Generic vs Project-Specific Architecture

**Generic Agents** (global, reusable):
- Location: `~/.claude/agents/`
- Output: stdout only
- File operations: None
- Paths: No project-specific paths
- Reusable across: All projects
- Examples: `youtube-transcript-agent`, `web-research-agent`

**Project-Specific Commands** (vault/repo specific):
- Location: `ProjectDir/.claude/commands/`
- Output: User-friendly reports
- File operations: Write to project structure
- Paths: Knows `70 Source Material/YouTube/`, etc.
- Reusable across: This project only
- Examples: `/youtube-source-page` (Obsidian-specific)

**Why this separation matters**:
- Generic agents work anywhere (YouTube transcripts useful in any context)
- Commands encapsulate project knowledge (Obsidian folder structure)
- Easier to test (agents are pure utilities)
- Better reusability (generic agents used by multiple projects)

### Testing for Unattended Execution

**Before deploying**, test the agent/command:

1. **Clean run**: Start fresh Claude Code session
2. **Execute**: Run the command/agent
3. **Watch for interruptions**: Any approval requests = redesign needed
4. **Check temp files**: No files in `/tmp/` or system directories
5. **Verify output**: Agents output to stdout, commands write to project

**If you see approval requests or interruptions**:
- ❌ Agent is writing temp files → redesign to use stdout
- ❌ Agent is generating scripts inline → create pre-made script
- ❌ Agent is writing to system dirs → use project paths
- ❌ Tools aren't scoped → narrow allowed-tools

---

## Data Source Philosophy

### Single Source of Truth Pattern

**Problem**: Complex systems have multiple data sources (config files, APIs, databases, documentation). Scanning all sources is expensive, slow, and can produce inconsistent results.

**Solution**: Designate one authoritative data source and design agents to use only that source.

### When to Use This Pattern

**Use single source of truth when**:
- Multiple data sources exist for same information
- One source is comprehensive and maintained
- Scanning all sources would be expensive (100s+ files, API calls)
- You want to drive documentation quality

**Example from strategy-development-commander**:

```xml
<constraints>
- NEVER scan `backtest/strategy/` YAML files (too many files, expensive)
- NEVER use MCP trading tools (get all information from Obsidian documentation)
- ALWAYS extract information from Obsidian documentation only
</constraints>
```

**Why this works**:
- `backtest/strategy/` has 500+ YAML files → expensive to scan
- MCP tools require API calls → slower, rate limits
- Obsidian documentation is the source of truth → fast, maintained
- **Bonus**: Drives users to keep documentation current

### Documentation Feedback Loop

**Philosophy**: Agents improve data quality by complaining about what's missing.

**The loop**:
```
Agent runs → Finds documentation gaps → Complains in report
     ↓
User sees gaps → Updates documentation → Fixes issues
     ↓
Agent runs again → Fewer gaps → Better strategic decisions
```

**Implementation**:

```xml
<constraints>
- ALWAYS complain about missing documentation to drive quality improvements
- ALWAYS reference companion guide when finding gaps
</constraints>

<documentation_gap_categories>
## Critical (Blocks Assessment)
- No tracker exists → Can't determine phase
- No phase marker → Don't know where strategy is
- No recent date → Can't detect stalled projects

## Important (Affects Quality)
- No variant breakdown → Can't track deployments
- No metrics documented → Can't assess GO/NO-GO
</documentation_gap_categories>
```

**Gap report format**:
```markdown
⚠️ DOCUMENTATION GAPS (Action Required)
───────────────────────────────────────────────────────────────
📖 See: [Guide Path]
    (Templates, examples, and required field reference)

CRITICAL GAPS (Block Assessment):
1. [Item] - NO TRACKER
   • Impact: Cannot determine phase, metrics, or progress
   • Action: Create Development Tracker
   • Template: See Checklist section "Minimal Tracker (Quick Start)"
```

**Benefits**:
- Documentation quality improves over time
- Users learn what agents need
- Agents get better data each run
- Self-reinforcing improvement cycle

### Companion Guide Pattern

**Pattern**: Create a detailed checklist/guide that agents reference when finding gaps.

**Agent references the guide**:
```xml
<constraints>
- ALWAYS reference "40 Trading/Strategy Documentation Checklist for Commander.md" when finding gaps
</constraints>
```

**Guide provides**:
- Templates (minimal, full, hypothesis tracker)
- Required fields with examples
- Common gaps categorized by severity
- Before/after examples from real strategies

**Why this works**:
- Users know exactly where to look for fixes
- Templates make fixing gaps fast
- Examples show what "good" looks like
- Guide is maintained independently of agent

---

## Command Development

### Command Structure Template

**Remember**: Command is just the wrapper. Keep it under 50 lines.

#### Pattern 1: Analyze Only

```markdown
---
allowed-tools: Bash(git diff:+), Bash(git log:+), Bash(git status:+)
argument-hint: [quick|standard|full] [directory]
description: Analyze [thing] for quality/compliance
---

## Context

- Current git status: `!git status`
- Recent changes: `!git diff HEAD~1 -- [pattern]`

## Your task

### Step 1: Parse Arguments

Determine mode (quick|standard|full) and directory.

### Step 2: Invoke Agent

Task tool with:
- subagent_type: "my-assistant"
- prompt: "Analyze [thing] in [mode] mode for [directory]. Reference guide: ~/Documents/workspaces/coding/docs/[guide-name].md"

### Step 3: Present Report

Present the agent's report as-is.
```

#### Pattern 2: Analyze + Fix

```markdown
---
allowed-tools: Bash(git diff:+), Bash(git log:+), Bash(git status:+)
argument-hint: [analyze|fix] [quick|standard|full] [directory]
description: Analyze or fix [thing]
---

## Context

- Current git status: `!git status`
- Recent changes: `!git diff HEAD~1 -- [pattern]`

## Your task

### Step 1: Parse Arguments

Determine action (analyze|fix, defaults to analyze) and mode.

### Step 2: Invoke Agent

Task tool with:
- subagent_type: "my-assistant"
- prompt: "[action] [thing] in [mode] mode for [directory]. Reference guide: ~/Documents/workspaces/coding/docs/[guide-name].md"

### Step 3: Present Report

Present the agent's report/changes as-is.
```

#### Pattern 3: Review Modes Only

```markdown
---
allowed-tools: Bash(git diff:+), Bash(git status:+)
argument-hint: [quick|standard|full] [directory]
description: Review [thing] with configurable depth
---

## Context

- Recent changes: `!git diff HEAD~1 -- [pattern]`

## Your task

Invoke [agent-name] agent with parsed mode and directory.

Task tool with:
- subagent_type: "agent-name"
- prompt: "Review [thing] in [mode] mode for [directory]."
```

**That's it.** Command does nothing else.

### Command Metadata

**Frontmatter fields**:
```yaml
---
allowed-tools: Bash(command:pattern)  # Whitelist of allowed bash commands
argument-hint: "[arg1|arg2] [arg3]"   # Show usage hint to user (MUST be quoted string)
description: Short description         # Shown in /help
---
```

**Important**: The `argument-hint` field **MUST be a quoted string** to display properly in the UI:
- ✅ Correct: `argument-hint: "[personal|seibert]"`
- ✅ Correct: `argument-hint: "[quick|standard|full] [directory]"`
- ❌ Wrong: `argument-hint: [personal|seibert]` (not quoted - won't display)

**Tool patterns**:
- `Bash(git diff:+)` - Allow all git diff variations
- `Bash(git log:+)` - Allow all git log variations
- `Bash(make precommit:+)` - Allow make precommit
- Use `+` for pattern matching, `*` for exact match

### Context Commands

Use `!command` syntax to inject context:

```markdown
## Context

- Current branch: `!git branch --show-current`
- Modified files: `!git diff --name-only`
- Last commit: `!git log -1 --oneline`
```

This gives the agent fresh, accurate context at invocation time.

### Argument Parsing Best Practices

**Mode detection**:
```markdown
- If first arg is `quick|fast` → Quick mode
- If first arg is `full|comprehensive|complete` → Full mode
- Otherwise → Standard mode (default)
```

**Directory handling**:
```markdown
- Remaining args → Directory path
- Default to current directory if not specified
```

**Validation**:
- Keep validation minimal in command
- Let agent handle complex validation
- Only check critical prerequisites (e.g., go.mod exists)

---

## Agent Development

### Agent Structure Template

```markdown
---
name: agent-name
description: When and why to use this agent. Trigger conditions.
tools: Read, Grep, Glob, Bash
color: green|blue|yellow|red
allowed-tools: Bash(specific:commands)
---

# Purpose

Clear statement of what this agent does and when to invoke it.

When invoked:
1. High-level workflow step
2. Another workflow step
3. Final workflow step

[Agent-specific checklist of what it reviews/checks]

## Communication Protocol

[If agent needs to query context or communicate with system]

## Review Modes

[If agent supports multiple depths]

**Quick Mode**:
- Fast checks only
- Structure validation
- Time: < 2 minutes

**Standard Mode** (default):
- Balanced review
- Key quality checks
- Time: 5-10 minutes

**Full Mode**:
- Comprehensive analysis
- All checks
- Time: 15-30 minutes

## Development Workflow

Execute [task] through systematic phases:

### 1. Discovery Phase

What to discover and how:
- File patterns to glob
- Keywords to grep
- Structure to check
- Context to gather

### 2. Analysis Phase

How to analyze what was discovered:
- Quality checks to perform
- Patterns to match
- Issues to identify
- Severity to assign

### 3. Quality Assurance Phase

How to verify the review:
- Completeness checks
- Consistency validation
- Report quality
- Recommendations clarity

## Report Generation

### Report Structure

1. Summary
2. Findings by Category
3. Recommendations
4. Examples
5. Next Steps

### Severity Categorization

- **Critical**: [What qualifies as critical]
- **Important**: [What qualifies as important]
- **Moderate**: [What qualifies as moderate]
- **Minor**: [What qualifies as minor]

## Output Format

```markdown
# [Agent Name] Report

## Summary
[Summary format]

## Findings

### Critical Issues
[Format for critical findings]

### Important Issues
[Format for important findings]

[... more sections ...]
```

## Integration with Other Agents

List related agents and how they collaborate:
- Work with **agent-x** on [shared concern]
- Support **agent-y** by [how it helps]
- Guide **agent-z** on [specific guidance]

**Best Practices**:
- Prioritize [what matters most]
- Explain "why" behind suggestions
- Provide concrete examples
- Be constructive and educational
```

### Agent Metadata

**Frontmatter fields**:
```yaml
---
name: agent-name                      # kebab-case identifier
description: Trigger and purpose      # When to invoke proactively
tools: Read, Grep, Glob, Bash         # Available tools
color: green|blue|yellow|red          # Visual indicator
allowed-tools: Bash(specific:*)       # Tool restrictions
---
```

**Color conventions**:
- `green` - Quality/correctness agents
- `blue` - Documentation/information agents
- `yellow` - Analysis/research agents
- `red` - Security/critical agents

### Workflow Phases

**Standard 3-phase pattern**:

1. **Discovery Phase**
   - What to find (files, patterns, structure)
   - How to find it (glob, grep, read)
   - What context to gather

2. **Analysis Phase**
   - How to analyze findings
   - What checks to perform
   - How to categorize issues

3. **Quality Assurance Phase**
   - How to verify completeness
   - How to ensure quality
   - How to deliver results

### Severity Categories

**Use consistent severity levels**:

- **Critical**: Must fix immediately (security, data loss, blocking issues)
- **Important**: Should fix soon (correctness, maintainability, architecture)
- **Moderate**: Nice to fix (style, minor improvements, optional enhancements)
- **Minor**: Optional (cosmetic, preferences, documentation polish)

**Examples from existing agents**:

**go-quality-assistant**:
- Critical: `context.Background()` in business logic, infinite loops without ctx.Done()
- Important: Error handling issues, missing counterfeiter comments
- Moderate: Non-idiomatic code, glog level misuse
- Minor: GoDoc format issues

**documentation-quality-assistant**:
- Critical: Missing docs/overview.md, no business context
- Important: Missing architecture docs, incomplete PRDs
- Moderate: Missing optional docs, weak documentation
- Minor: Style inconsistencies

---

## XML Tag Patterns (Preferred for Complex Agents)

For agents requiring strong semantic structure, use XML tags instead of Markdown sections. This approach provides clearer parsing, explicit constraints, and better workflow definition.

### When to Use XML Tags

**Use XML tags for**:
- Complex agents with multiple phases
- Agents with hard constraints (NEVER/ALWAYS rules)
- Audit/oversight agents (strategy-development-commander, goal-auditor)
- Agents that generate structured reports
- Multi-step workflows with dependencies

**Use Markdown sections for**:
- Simple single-purpose agents
- Quick utility agents
- Agents with minimal constraints

### Quick Reference

| Tag | Purpose | When to Use |
|-----|---------|-------------|
| `<role>` | Establish expertise and specialization | All XML-structured agents |
| `<constraints>` | Hard NEVER/ALWAYS rules | Agents with prohibitions or requirements |
| `<critical_workflow>` | Ordered execution steps | Complex multi-phase workflows |
| `<data_sources>` | Where to get information | Data-gathering agents |
| `<extraction_fields>` | What to extract and from where | Audit/analysis agents |
| `<evaluation_areas>` | Severity-based criteria | Review/audit agents |
| `<contextual_judgment>` | Adjust expectations by context | Variable complexity assessments |
| `<output_format>` | Exact output template | All agents generating reports |
| `<success_criteria>` | Completion verification | All agents |
| `<final_step>` | User interaction options | Interactive agents |

### XML vs Markdown Comparison

**Markdown approach** (simpler agents):
```markdown
# Purpose
Clear statement of what this agent does...

## Review Modes
- Quick: Structure only
- Standard: Key checks

## Workflow
1. Discovery Phase
2. Analysis Phase
3. Report Generation
```

**XML approach** (complex agents):
```xml
<role>
Expert [domain] [role] specializing in [capability]. You [responsibilities].
</role>

<constraints>
- NEVER [prohibited action]
- ALWAYS [required action]
- [Quality expectations]
</constraints>

<critical_workflow>
1. **Phase 1** - [Description]
   - Step details
2. **Phase 2** - [Description]
   - Step details
</critical_workflow>

<output_format>
[Exact template for agent output]
</output_format>
```

### Example: Strategy Development Commander

Real-world example using full XML pattern:

```xml
<role>
Expert trading strategy development manager specializing in pipeline oversight,
phase assessment, and documentation quality enforcement.
</role>

<constraints>
- NEVER scan `backtest/strategy/` YAML files (too many files, expensive)
- NEVER use MCP trading tools (get all information from Obsidian documentation)
- ALWAYS extract information from Obsidian documentation only
- ALWAYS complain about missing documentation to drive quality improvements
- ALWAYS reference guide when finding gaps
</constraints>

<critical_workflow>
1. **Read Strategy Hub first** - Get baseline list of active strategies
2. **Find all strategy documentation** - Comprehensive scan
3. **Find active tasks** - Identify current work
4. **Build strategy inventory** - Create detailed entries
5. **Identify documentation gaps** - Check required fields
6. **Generate report** - Output structured report
</critical_workflow>

<documentation_gap_categories>
## Critical (Blocks Assessment)
- No tracker exists
- No phase marker

## Important (Affects Quality)
- No variant breakdown
- No metrics documented

## Minor (Nice to Have)
- No hypothesis numbering
</documentation_gap_categories>

<output_format>
═══════════════════════════════════════════════════════════════
                 STRATEGY DEVELOPMENT COMMAND CENTER
═══════════════════════════════════════════════════════════════

📊 EXECUTIVE SUMMARY
...

🔬 DEVELOPMENT PIPELINE
...

⚡ PRIORITY ACTIONS
...

⚠️ DOCUMENTATION GAPS
...

🎯 STRATEGIC RECOMMENDATIONS
...
</output_format>
```

### Full Tag Documentation

For complete syntax, patterns, and examples for each XML tag, see:
- **Obsidian**: `50 Knowledge Base/Claude Code XML Tag Patterns.md`
- **Covers**: Purpose, pattern, example, and guidelines for every tag
- **Includes**: Architecture comparison (command vs agent)

### Command Tags (Minimal Set)

Commands using XML need only three tags:

```xml
<objective>
Invoke the [agent-name] agent to [action] for [purpose].
</objective>

<process>
1. Parse input from $ARGUMENTS
2. Invoke agent with parameters
3. Present results
</process>

<success_criteria>
- Agent invoked successfully
- Arguments passed correctly
- Output includes expected sections
</success_criteria>
```

---

## File Organization

### Directory Structure

```
~/.claude/
├── agents/                    # Agent implementations
│   ├── go-quality-assistant.md
│   ├── documentation-quality-assistant.md
│   └── ...
├── commands/                  # Slash commands
│   ├── code-review.md
│   ├── doc-review.md
│   └── ...
└── docs/                      # Documentation
    └── agent-command-development-guide.md
```

### File Naming

**Agents**: `[domain]-[function]-assistant.md`
- `go-quality-assistant.md` - Go code quality
- `documentation-quality-assistant.md` - Documentation quality
- `go-test-writer-assistant.md` - Test generation
- `go-factory-pattern-assistant.md` - Factory pattern compliance

**Commands**: `[action].md` or `[domain]-[action].md`
- `code-review.md` - Review code
- `doc-review.md` - Review documentation
- `go-write-test.md` - Write Go tests
- `check-guides.md` - Check coding guidelines

---

## Naming Conventions

### Agent Names

**Pattern**: `[domain]-[function]-assistant`

**Examples**:
- `go-quality-assistant` - General Go quality
- `go-test-quality-assistant` - Go test quality
- `go-http-handler-assistant` - HTTP handler patterns
- `documentation-quality-assistant` - Documentation quality
- `godoc-assistant` - GoDoc comments
- `readme-quality-assistant` - README quality

**Avoid**:
- Generic names like `helper`, `checker`, `validator`
- Redundant suffixes like `agent`, `tool`, `service`
- Use `assistant` consistently for quality agents

### Command Names

**Pattern**: `[action]` or `[domain]-[action]`

**Examples**:
- `code-review` - Review code
- `doc-review` - Review documentation
- `go-write-test` - Write tests
- `check-guides` - Check guidelines
- `commit` - Create commit
- `create-prd` - Create PRD

**Avoid**:
- Verbs like `perform`, `execute`, `do`
- Prefixes like `run-`, `start-`
- Suffixes like `-command`, `-cmd`

---

## Examples & Templates

### Example: Code Quality Agent & Command

**Command** (`/code-review`):
```markdown
---
allowed-tools: Bash(git diff:+), Bash(git log:+), Bash(make precommit:+)
argument-hint: [short|standard|full] [directory]
description: Perform comprehensive code review of recent changes
---

## Context

- Current git status: `!git status`
- Recent changes: `!git diff HEAD~1`

## Your task

### Step 1: Parse Arguments

Determine mode (short|standard|full) and directory.

### Step 2: Run Precommit (if exists)

Check for Makefile and run `make precommit` if available.

### Step 3: Invoke Agents

Based on mode, invoke agents in parallel:
- **Standard**: go-quality-assistant, go-factory-pattern-assistant
- **Full**: All 13 agents

### Step 4: Present Report

Consolidated report from all agents.
```

**Agent** (`go-quality-assistant`):
```markdown
---
name: go-quality-assistant
description: Review Go code for idiomatic style, naming, error handling, concurrency
tools: Read, Grep, Glob, Bash
color: green
---

# Purpose

Senior Go engineer performing quality review.

[... complete workflow, checks, severity, reporting ...]
```

### Example: Documentation Agent & Command

**Command** (`/doc-review`):
```markdown
---
allowed-tools: Bash(git diff:+), Bash(git log:+), Bash(git status:+)
argument-hint: [quick|standard|full] [directory]
description: Review documentation for completeness and AI context quality
---

## Context

- Recent doc changes: `!git diff HEAD~1 -- '*.md'`

## Your task

### Step 1: Parse Arguments

Determine mode and directory.

### Step 2: Invoke Agent

Use Task tool to invoke documentation-quality-assistant.

### Step 3: Present Report

Show the agent's comprehensive report.
```

**Agent** (`documentation-quality-assistant`):
```markdown
---
name: documentation-quality-assistant
description: Review docs for completeness, AI context quality, guide adherence
tools: Read, Grep, Glob, Bash
color: blue
---

# Purpose

Technical writer performing documentation review.

[... project detection, structure checks, content analysis, reporting ...]
```

---

## Integration Patterns

### Command → Single Agent

**Simplest pattern**: Command invokes one agent.

```markdown
### Step 2: Invoke Agent

Task tool with:
- subagent_type: "my-assistant"
- prompt: "Review [thing] in [mode] mode."
```

**Example**: `/doc-review` → `documentation-quality-assistant`

### Command → Multiple Agents (Parallel)

**Pattern**: Command invokes multiple agents concurrently.

```markdown
### Step 3: Invoke Agents

Run agents in parallel using multiple Task tool calls in a single message:
1. go-quality-assistant
2. go-factory-pattern-assistant
3. http-handler-assistant
```

**Example**: `/code-review` → Multiple Go agents

### Command → Multiple Agents (Sequential)

**Pattern**: Command invokes agents in sequence (one depends on previous).

```markdown
### Step 3: First Agent

Invoke agent-a to gather context.

### Step 4: Second Agent

Using results from agent-a, invoke agent-b.
```

**Example**: Pre-implementation check → Code generation → Quality review

### Agent → Agent Collaboration

**Pattern**: Agents reference or complement each other.

```markdown
## Integration with Other Agents

Collaborate with specialized agents:
- Work with **godoc-assistant** on documentation completeness
- Support **test-generator** by identifying untested code paths
- Guide **refactoring-specialist** on improvements
```

**Example**: `go-quality-assistant` notes missing docs → `godoc-assistant` adds them

### Command Chaining

**Pattern**: Commands suggest next commands.

```markdown
## Next Steps

Test coverage gaps detected. Quick fix:
- `/go-write-test basic` - Add tests for recent changes
- `/go-write-test standard pkg/user` - Comprehensive tests
```

**Example**: `/code-review` detects missing tests → suggests `/go-write-test`

---

## Quality Checklist

### Before Creating Agent/Command

- [ ] Checked if similar agent/command exists
- [ ] Defined clear purpose and trigger conditions
- [ ] Identified what knowledge/logic agent needs
- [ ] Determined appropriate review modes (if applicable)
- [ ] Outlined workflow phases (Discovery → Analysis → QA)
- [ ] Listed integration points with other agents

### Command Quality

- [ ] Minimal (~50-100 lines)
- [ ] Clear argument parsing
- [ ] Context injection with `!commands`
- [ ] Single Task tool invocation (or explicit parallel)
- [ ] No business logic or implementation details
- [ ] Clear description in frontmatter

### Agent Quality

- [ ] Comprehensive documentation of workflow
- [ ] Clear purpose statement and trigger conditions
- [ ] All detection/analysis logic included
- [ ] Severity categorization defined
- [ ] Report format documented
- [ ] Examples included (before/after)
- [ ] Integration with other agents documented
- [ ] Review modes clearly defined (if applicable)

### Documentation Quality

- [ ] Purpose clearly stated
- [ ] When to invoke documented
- [ ] Workflow steps explained
- [ ] Examples provided
- [ ] Integration points listed
- [ ] Best practices included

### Testing

- [ ] Test with minimal input (quick mode)
- [ ] Test with standard input (default mode)
- [ ] Test with comprehensive input (full mode)
- [ ] Test error cases (missing files, invalid args)
- [ ] Verify report format and clarity
- [ ] Check recommendation quality

### Automated Verification

Use audit commands to verify compliance with this guide:

```bash
# Audit a slash command
/audit-slash-command ~/.claude/commands/my-command.md

# Audit an agent
/audit-agent ~/.claude/agents/my-agent.md
```

These commands check YAML config, structure, patterns, and provide severity-based findings with actionable recommendations.

---

## Reference Examples

### Existing Command/Agent Pairs

**Quality Review**:
- `/code-review` → Multiple Go quality agents
- `/doc-review` → `documentation-quality-assistant`

**Generation**:
- `/go-write-test` → `go-test-writer-assistant`
- `/godoc` → `godoc-assistant`
- `/create-prd` → PRD generation logic

**Analysis**:
- `/check-guides` → `pre-implementation-assistant`
- `/research` → `web-research-agent`, `gemini-research-agent`

**Specialized**:
- `/market-analysis` → `market-analysis-agent`
- `/commit` → Commit workflow with detection

### Study These Examples

**Minimal command**: `/doc-review.md` (~45 lines)
**Comprehensive agent**: `documentation-quality-assistant.md` (~450 lines)

**Multi-agent command**: `/code-review.md` (~180 lines)
**Specialized agent**: `go-quality-assistant.md` (~280 lines)

---

## Quick Start: Creating New Agent/Command

Follow the 4-step process:

### Step 1: Write the Guide

**Location**: `~/Documents/workspaces/coding/docs/my-topic-guide.md`

```markdown
# My Topic Guide

## Purpose
[What you want to achieve and why]

## Patterns
[Detailed patterns, examples, best practices]

## Anti-Patterns
[What to avoid and why]

## Templates
[Copy-paste ready templates]

## Examples
[Before/after examples]
```

**Time**: 1-2 hours for comprehensive guide

---

### Step 2: Create the Agent

**Location**: `~/.claude/agents/my-topic-assistant.md`

```markdown
---
name: my-topic-assistant
description: When to invoke (proactive triggers)
tools: Read, Grep, Glob, Bash
color: green
---

# Purpose
Clear statement referencing the guide from Step 1.

## Review Modes
- Quick: Structure only
- Standard: Key checks
- Full: Comprehensive

## Development Workflow

### 1. Discovery Phase
- What to find (glob patterns, grep keywords)
- Reference guide: ~/Documents/workspaces/coding/docs/my-topic-guide.md

### 2. Analysis Phase
- Check patterns from guide
- Detect violations
- Categorize severity

### 3. Report Generation
- Summary
- Findings by severity
- Examples from guide
- Fix recommendations

## Severity Categories
- Critical: [...]
- Important: [...]
- Moderate: [...]
- Minor: [...]
```

**Time**: 2-3 hours for comprehensive agent

---

### Step 3: Create the Command

**Location**: `~/.claude/commands/my-command.md`

**Choose your pattern**:

**Option A: Analyze Only**
```markdown
---
argument-hint: [quick|standard|full] [directory]
description: Analyze [thing]
---

## Your task
Parse mode, invoke my-topic-assistant, present report.
```

**Option B: Analyze + Fix**
```markdown
---
argument-hint: [analyze|fix] [mode] [directory]
description: Analyze or fix [thing]
---

## Your task
Parse action and mode, invoke my-topic-assistant, present report.
```

**Time**: 15-30 minutes for command wrapper

---

### Step 4: Integration (Optional)

**If broadly useful**, add to `/code-review`:

```markdown
### Step 4: Automated Agent Review

**Standard Mode**:
1. go-quality-assistant
2. go-factory-pattern-assistant
3. my-topic-assistant  ← Add here
```

**Or reference in related agents**:

```markdown
## Integration with Other Agents
- Work with **my-topic-assistant** on [related concern]
```

**Time**: 15-30 minutes for integration

---

## Complete Example: Documentation Review

### Step 1: The Guide (Already exists)
`~/Documents/workspaces/coding/docs/documentation-guide.md`
- 1,695 lines
- Complete documentation standards
- Templates for README, docs/, PRDs, ADRs
- Examples for internal vs public projects

### Step 2: The Agent
`~/.claude/agents/documentation-quality-assistant.md`
- 450 lines
- References documentation-guide.md
- Implements all analysis logic
- Generates comprehensive reports

### Step 3: The Command
`~/.claude/commands/doc-review.md`
- 45 lines
- Parses mode (quick|standard|full)
- Invokes documentation-quality-assistant
- Presents report

### Step 4: Integration
Optionally integrated into `/code-review` for comprehensive reviews.

---

## Auto-Discovery

**For Claude Code**: This guide is referenced in `~/.claude/CLAUDE.md` section "Command and Agent Architecture":

```markdown
## Command and Agent Architecture

See comprehensive guide: ~/.claude/docs/agent-command-development-guide.md

### Quick Reference

**Command** (minimal - ~50-100 lines):
- Argument parsing
- Agent invocation
- NO detailed implementation

**Agent** (comprehensive - detailed):
- All implementation logic
- All patterns and checks
- Complete workflow
- Report generation
```

This enables Claude Code to automatically discover and reference this guide when creating new agents/commands.

---

## Appendix: Command/Agent Registry

### Quality Agents
- `go-quality-assistant` - Go code quality
- `go-test-quality-assistant` - Go test quality
- `documentation-quality-assistant` - Documentation quality
- `godoc-assistant` - GoDoc comments
- `readme-quality-assistant` - README quality
- `go-factory-pattern-assistant` - Factory pattern compliance
- `go-http-handler-assistant` - HTTP handler patterns
- `shellcheck-assistant` - Shell script quality

### Analysis Agents
- `go-security-specialist` - Security vulnerabilities
- `srp-checker` - Single Responsibility Principle
- `go-test-coverage-assistant` - Test coverage gaps
- `pre-implementation-assistant` - Pre-coding guideline check

### Generation Agents
- `go-test-writer-assistant` - Test generation
- `go-tooling-assistant` - Makefile/tools.go setup
- `license-assistant` - License headers
- `meta-agent` - Agent generation

### Workflow Agents
- `go-mod-update` - Dependency updates
- `go-version-manager` - Go version management
- `unattended-work` - Autonomous long-running tasks

### Oversight Agents
- `strategy-development-commander` - Trading strategy pipeline oversight
- `slash-command-auditor` - Slash command compliance audit
- `agent-auditor` - Agent configuration audit

### Research Agents
- `web-research-agent` - Web research
- `gemini-research-agent` - AI-powered analysis
- `atlassian-research-agent` - Confluence/Jira search
- `obsidian-research-agent` - Personal knowledge vault
- `market-analysis-agent` - Trading market analysis

### Commands
- `/code-review` - Comprehensive code review
- `/doc-review` - Documentation review
- `/go-write-test` - Test generation
- `/check-guides` - Guideline reference
- `/commit` - Intelligent git commit
- `/godoc` - GoDoc generation
- `/create-prd` - PRD creation
- `/research` - Multi-source research
- `/market-analysis` - Trading analysis
- `/audit-slash-command` - Audit slash command compliance
- `/audit-agent` - Audit agent configuration
