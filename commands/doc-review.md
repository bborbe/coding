---
allowed-tools: Bash(git diff:*), Bash(git log:*), Bash(git status:*)
argument-hint: [quick|standard|full] [directory]
description: Perform comprehensive documentation review of recent changes
---

## Context

- Current git status: `!git status`
- Recent doc changes: `!git diff HEAD~1 -- '*.md'`
- Recent commits: `!git log --oneline -5`
- Current branch: `!git branch --show-current`

## Your task

Invoke the **documentation-quality-assistant** agent to perform documentation review.

### Step 1: Parse Arguments

Parse arguments to determine mode and directory:
- First arg if `quick|fast` → Quick mode
- First arg if `full|comprehensive|complete` → Full mode
- Otherwise → Standard mode (default)
- Remaining args → Directory path

### Step 2: Invoke Agent

Use the Task tool to invoke the documentation-quality-assistant agent:

```
Task tool with:
- subagent_type: "documentation-quality-assistant"
- prompt: "Perform documentation review in [mode] mode for directory [directory]. Review documentation for completeness, AI context quality, and adherence to documentation guide at docs/documentation-guide.md. Provide consolidated report with severity-ranked findings and actionable recommendations."
```

The agent will handle:
- Project type detection
- Documentation discovery
- Quality analysis
- Report generation
- Recommendations

### Step 3: Present Report

The agent returns a comprehensive report. Present it to the user as-is.
