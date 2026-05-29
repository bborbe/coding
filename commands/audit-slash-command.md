---
allowed-tools: Task
description: Audit slash command file against Agent & Command Development Guide for quality and compliance
argument-hint: "[path/to/command.md]"
---

<objective>
Invoke the slash-command-auditor agent to audit the slash command at $ARGUMENTS for compliance with Agent & Command Development Guide best practices.
</objective>

<process>
1. Invoke the `coding:slash-command-auditor` agent, passing `$ARGUMENTS` as the command to audit (the agent resolves the path and appends `.md` if needed).
2. Present the agent's audit report.
</process>

<success_criteria>
- Report covers every evaluation area from the Agent & Command Development Guide (frontmatter, argument handling, structure, tool restrictions, content quality)
- Report shows score, critical issues, recommendations, and strengths
- Findings cite line numbers and quoted snippets
</success_criteria>
