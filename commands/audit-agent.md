---
allowed-tools: Task
description: Audit agent file against Agent & Command Development Guide for quality and compliance
argument-hint: "[path/to/agent.md]"
---

<objective>
Invoke the agent-auditor agent to audit the agent at $ARGUMENTS for compliance with Agent & Command Development Guide best practices.
</objective>

<process>
1. Invoke the `coding:agent-auditor` agent, passing `$ARGUMENTS` as the agent to audit (the agent resolves the path and appends `.md` if needed).
2. Present the agent's audit report.
</process>

<success_criteria>
- Report covers every evaluation area from the Agent & Command Development Guide (frontmatter, role definition, constraints, workflow, evaluation areas, output format, XML structure)
- Report shows score, critical issues, recommendations, and strengths
- Findings cite line numbers and quoted snippets
</success_criteria>
