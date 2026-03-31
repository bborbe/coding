---
description: Audit slash command file against Agent & Command Development Guide for quality and compliance
argument-hint: "<command-path>"
---

<objective>
Invoke the slash-command-auditor agent to audit the slash command at $ARGUMENTS for compliance with Agent & Command Development Guide best practices.
</objective>

<process>
1. Parse command path from $ARGUMENTS
   - If path doesn't contain `/`, look in `~/.claude/commands/` or project `.claude/commands/`
   - If no `.md` extension, append it
2. Invoke slash-command-auditor agent with the command path
3. Agent reads Agent & Command Development Guide first
4. Agent evaluates YAML frontmatter, argument handling, structure, tool restrictions, content quality
5. Review detailed findings with severity levels, scores, and recommendations
</process>

<success_criteria>
- Agent invoked successfully
- Command path passed correctly
- Audit includes all evaluation areas from Agent & Command Development Guide
- Report shows score, critical issues, recommendations, and strengths
</success_criteria>
