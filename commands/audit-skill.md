---
description: Audit skill directory against Claude Code Skill Writing Guide for quality and compliance
argument-hint: "<skill-path>"
---

<objective>
Invoke the skill-auditor agent to audit the skill at $ARGUMENTS for compliance with Claude Code Skill Writing Guide best practices.
</objective>

<process>
1. Parse skill path from $ARGUMENTS
   - If path is a directory, use it directly
   - If path doesn't contain `/`, look in `~/.claude/skills/` or project `skills/`
2. Invoke skill-auditor agent with the skill path
3. Agent reads Claude Code Skill Writing Guide first
4. Agent evaluates SKILL.md structure, frontmatter, scripts, content quality
5. Review detailed findings with severity levels, scores, and recommendations
</process>

<success_criteria>
- Agent invoked successfully
- Skill path passed correctly
- Audit includes all evaluation areas from Skill Writing Guide
- Report shows score, critical issues, recommendations, and strengths
</success_criteria>
