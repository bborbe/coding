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

## Field bounds

Each finding's `matched_text` is bounded to 8192 bytes and its `message` to
1024 bytes. Both are cut on a UTF-8 rune boundary; a cut never emits a partial
multi-byte sequence. A field that was cut ends with
`…[truncated, original <N> bytes]`, where `<N>` is the pre-cut byte length.

The marker is part of the string value, not a separate JSON field. The consumer
(`bborbe/github-pr-review-agent/pkg/funnel.go`) unmarshals findings into a fixed
seven-field struct and re-marshals it, so an extra field would be stripped; an
in-string marker survives any consumer that passes the string through.

A `matched_text` or `message` under its bound is emitted byte-for-byte as
before, with no marker.

See `scripts/ast-grep-runner.sh` for exit codes and diff-scoping behaviour.
