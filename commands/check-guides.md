---
allowed-tools: Read, Grep, Bash(ls:*)
argument-hint: [task description]
description: Review relevant coding guidelines before starting implementation
---

## Usage

Before starting to code, check which guidelines are relevant for your task:

```bash
/check-guides "write tests for main package"
/check-guides "create factory for user service"
/check-guides "add HTTP handler for invoice forwarding"
/check-guides "implement metrics for background worker"
```

## Your Task

You are helping the developer identify relevant coding guidelines BEFORE they start implementing. This prevents common pattern violations.

### Step 1: Validate Input

Check if task description was provided:
- If no task description: Show usage examples and ask for task description
- If task description provided: Continue to Step 2

### Step 2: Invoke Pre-Implementation Assistant

Use the Task tool to invoke the `pre-implementation-assistant` agent with the task description.

Example:
```
Task tool with subagent_type='coding:pre-implementation-assistant'
Prompt: "Analyze this task and recommend relevant coding guidelines: [user's task description]"
```

### Step 3: Display Summary

After the agent completes, output a CONCISE summary:

```
✅ Guidelines checked

Found [N] relevant guides:
- guide-name.md (lines X-Y) - reason
- guide-name.md (lines X-Y) - reason

Ready to implement following documented patterns.
```

If no guides found:
```
✅ Guidelines checked

No specific guides found for this task.
Consider general patterns in docs/

Ready to implement.
```

Keep it brief - user can scroll up to see agent's detailed output.

## Example Flow

**User runs**: `/check-guides "write tests for main package"`

**You invoke**: `pre-implementation-assistant` with task: "write tests for main package"

**Agent returns**: Recommendation to read `go-testing-guide.md` lines 95-141 (Main Package Special Case) with explanation that main packages use a different test pattern

**Result**: Developer reads the guide FIRST, then implements correctly, avoiding the need to fix violations later in code review.

## Important Notes

- This is a **preventive** workflow - catches issues before code is written
- Complements `/code-review` which is **reactive** - catches issues after code is written
- Reading 5 minutes of guidelines saves 30 minutes of rework
- Not all tasks match keywords - that's ok, agent provides general guidance

## Prevention > Detection

This command follows the philosophy: **Better to read guidelines before coding than fix violations in code review**.
