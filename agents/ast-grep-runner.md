---
name: ast-grep-runner
description: DEPRECATED — superseded by scripts/ast-grep-runner.sh
model: sonnet
tools: Bash
color: gray
---

# DEPRECATED

This agent is superseded by `scripts/ast-grep-runner.sh`, which produces the
same JSON contract deterministically without an LLM invocation.

**Do not invoke this agent.** If you have a reference to `coding:ast-grep-runner`,
replace it with a `Bash` call to `scripts/ast-grep-runner.sh <target-dir> [changed-file ...]`.

## JSON contract (unchanged)

```json
{
  "stats": { "yamls_run": N, "findings_count": N, "elapsed_ms": N },
  "findings_by_owner": { "<owner-agent>": [ { "rule_id", "rule_level", "file", "line", "column", "matched_text", "message" } ] },
  "errors": []
}
```

See `scripts/ast-grep-runner.sh` for exit codes and diff-scoping behaviour.
