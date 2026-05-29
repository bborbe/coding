---
allowed-tools: Task
description: Audit skill directory against Claude Code Skill Writing Guide for quality and compliance
argument-hint: "[path/to/skill]"
---

<objective>
Invoke the skill-auditor agent to audit the skill at $ARGUMENTS for compliance with Claude Code Skill Writing Guide best practices.
</objective>

<process>
1. Invoke the `coding:skill-auditor` agent, passing `$ARGUMENTS` as the skill to audit (the agent resolves the path, directory or name).
2. Present the agent's audit report.
</process>

<success_criteria>
- Report covers every evaluation area from the Claude Code Skill Writing Guide (SKILL.md structure, frontmatter, scripts, content quality)
- Report shows score, critical issues, recommendations, and strengths
- Findings cite line numbers and quoted snippets
</success_criteria>
