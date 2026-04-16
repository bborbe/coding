---
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[file-path]"
description: Audit a coding guide against style, structure, and quality standards
---

## Usage

Audit a coding guide file before publishing or as part of guide maintenance:

```bash
/coding:audit-guide go-testing-guide.md
/coding:audit-guide docs/go-kubernetes-crd-controller-guide.md
/coding:audit-guide ~/Documents/workspaces/coding/docs/go-factory-pattern.md
```

## Your Task

### Step 1: Validate Input

Check if file path was provided:
- If no file path: Show usage examples and ask for the guide file to audit
- If file path provided: Continue to Step 2

### Step 2: Parse Path

- If argument has no path prefix (e.g. `go-testing-guide.md`), prepend `docs/`
- If argument has no `.md` extension, append it
- Otherwise use exactly as provided — never resolve `~`

### Step 3: Invoke Agent

Use the Task tool to invoke the `coding:guide-auditor` agent.

Task tool with:
- subagent_type: `coding:guide-auditor`
- prompt: "Audit the coding guide at [resolved-path]. Evaluate structure, content quality, self-containment, cross-references, indexing (README.md + llms.txt + agents/ + CLAUDE.md), and markdown quality. Report findings with severity, score, and recommendations."

### Step 4: Present Results

The agent will:
1. Read the guide file
2. Check indexing in `README.md`, `llms.txt`, `CLAUDE.md`, `agents/`
3. Evaluate against all criteria
4. Return a structured audit report with score and findings

Present the agent's full report. Keep any additional commentary brief.

## What Gets Audited

- **Structure** — H1, overview, heading hierarchy, antipatterns section
- **Content quality** — generic examples (no trading domain), GOOD/BAD pairs, bborbe libs, no filler
- **Self-contained** — no personal paths, no internal URLs
- **Cross-references** — relative links, no broken internal links
- **Indexing** — `README.md`, `llms.txt`, matching agent, `CLAUDE.md` Doc↔Agent table
- **Markdown quality** — code fence languages, tables, consistent formatting

## Important Notes

- **Read-only** — agent never modifies the guide
- **Complements `/coding:improve-guide`** — audit identifies issues, improve restructures
- **Run before publishing** — catches missing index entries, personal paths, trading examples
- **Run periodically** — guides drift as the plugin evolves
