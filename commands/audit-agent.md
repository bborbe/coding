---
description: Audit agent file against Agent & Command Development Guide for quality and compliance
argument-hint: "<agent-path>"
---

<objective>
Invoke the agent-auditor agent to audit the agent at $ARGUMENTS for compliance with Agent & Command Development Guide best practices.
</objective>

<process>
1. Parse agent path from $ARGUMENTS
   - If path doesn't contain `/`, look in `~/.claude/agents/` or project `.claude/agents/`
   - If no `.md` extension, append it
2. Invoke agent-auditor agent with the agent path
3. Agent reads Agent & Command Development Guide first
4. Agent evaluates YAML frontmatter, role definition, constraints, workflow, evaluation areas, output format, XML structure
5. Review detailed findings with severity levels, scores, and recommendations
</process>

<success_criteria>
- Agent invoked successfully
- Agent path passed correctly
- Audit includes all evaluation areas from Agent & Command Development Guide
- Report shows score, critical issues, recommendations, and strengths
</success_criteria>
