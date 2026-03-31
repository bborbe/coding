---
allowed-tools: Read, Edit
argument-hint: "[file-path]"
description: Refactor a coding guide into structured rule sets for humans and AI agents
---

## Usage

Transform verbose coding guidelines into scannable, AI-optimized rule sets:

```bash
/coding:improve-guide go-testing-guide.md
/coding:improve-guide ~/Documents/workspaces/coding/docs/go-factory-pattern.md
/coding:improve-guide ./docs/architecture-patterns.md
```

## Your Task

### Step 1: Validate Input

Check if file path was provided:
- If no file path: Show usage examples and ask for the guide file to transform
- If file path provided: Continue to Step 2

### Step 2: Invoke Agent

Use the Task tool to invoke the `coding:guide-improvement-assistant` agent.

Task tool with:
- subagent_type: `coding:guide-improvement-assistant`
- prompt: "Transform the guide at [file-path] into a structured rule set. Read the file, apply transformation rules, edit in place, and provide a transformation summary."

### Step 3: Present Results

The agent will:
1. Read and analyze the guide
2. Transform content into structured rules with Constraint/Rationale/Examples format
3. Edit the file in place
4. Return a transformation summary

Present the agent's summary showing:
- Lines reduced
- Rules extracted
- Changes made

## Transformation Applied

Each rule becomes:
```markdown
### [Descriptive Rule Title]

**Constraint:** [MUST/MUST NOT/ONLY statement]

**Rationale:** [Technical consequence]

**Examples:**
```go
// [GOOD]
[correct code]

// [BAD]
[incorrect code]
```
```

## Important Notes

- **Backup first**: Consider committing changes before running if uncertain
- **Preserves meaning**: Technical rules preserved, only removes fluff
- **In-place edit**: Modifies the file directly
- **Review after**: Run `/coding:doc-review` to verify quality
