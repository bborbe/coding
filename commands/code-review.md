---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+)
argument-hint: "[short|standard|full] [directory]"
description: Perform a comprehensive code review of recent changes
---

## Context

- Current git status: `!git status`
- Recent changes: `!git diff HEAD~1`
- Recent commits: `!git log --oneline -5`
- Current branch: `!git branch --show-current`

## Your task

Perform a code review with configurable depth based on mode.

### Step 1: Parse Arguments

Parse the first argument to determine mode:
- If first arg is `short|quick|fast` → **Short mode** (manual review only)
- If first arg is `full|comprehensive|complete` → **Full mode** (all 13 agents)
- Otherwise → **Standard mode** (4 core agents, default)

Any remaining arguments are treated as the directory path.

### Step 2: Project Detection

Detect project type to determine which specialist agents to invoke:
- **Go project**: Check for `*.go` files or `go.mod`
- **Python project**: Check for `*.py` files or `pyproject.toml`/`requirements.txt`
- **Other languages**: Add detection as needed

### Step 3: Run Automated Checks (All Modes)

**3a. Check for LICENSE file**

Use Glob to check if LICENSE file exists in project root:
```
LICENSE or LICENSE.md or LICENSE.txt
```

Store result for later:
- If missing → flag for license-assistant in Standard mode, report in Short mode
- If present → skip license-assistant in Standard mode

**3b. Run make precommit (if available)**

Check if Makefile exists and has a `precommit` target:
1. Use Read tool to check if Makefile exists (will error if missing)
2. Use Grep tool to search for `^precommit:` pattern in Makefile

If both checks pass, use Task tool with simple-bash-runner agent:
```
Task tool with subagent_type="coding:simple-bash-runner", prompt="cd [directory] && make precommit"
```

This provides automated checks (formatting, linting, tests, security) before running agents. Include the output and any failures in the final report.

If Makefile doesn't exist or lacks `precommit` target, skip this step. If `make precommit` fails, note the failures but continue with the review.

### Step 4: Automated Agent Review

Based on detected mode, invoke agents **in parallel**:

**Short Mode**: No agents - skip to Step 5
- BUT: If LICENSE file is missing (from Step 3a), add to report "Should Fix" section:
  - "Missing LICENSE file"
  - "README missing license section" (check with Grep for `## License` in README.md)

**Standard Mode** (default - core architectural compliance):

*For Go projects:*
1. **go-quality-assistant**: Idiomatic Go patterns, architecture, error handling, context cancellation in loops
2. **go-factory-pattern-assistant**: Factory pattern compliance, zero-business-logic rule (review mode only - no updates)
3. **go-http-handler-assistant**: HTTP handler organization, inline handler detection, architectural patterns (review mode only - no updates)
4. **go-test-coverage-assistant**: Test coverage gaps, missing tests for critical components (review mode only - no updates)

*For Python projects:*
1. **python-quality-assistant**: Idiomatic Python patterns, type hints, error handling, logging, async safety

*For all projects (conditional):*
5. **license-assistant**: ONLY if LICENSE file is missing (from Step 3a) - review mode only

**Full Mode**:

*Go projects:*
1. **godoc-assistant**: Documentation completeness and GoDoc format
2. **go-quality-assistant**: Idiomatic Go patterns, architecture, error handling
3. **go-test-quality-assistant**: Test file quality, Ginkgo/Gomega patterns, mock usage, test suite setup (review mode only - no updates)
4. **go-security-specialist**: Security vulnerabilities, OWASP compliance, dependency scanning
5. **srp-checker**: Single Responsibility Principle compliance, separation of concerns (review mode only - no updates)
6. **go-version-manager**: Go version currency and consistency across project files (check-only mode)
7. **go-tooling-assistant**: Makefile and tools.go configuration validation (review mode only - no updates)
8. **go-factory-pattern-assistant**: Factory pattern implementation, dependency injection, handler wrapping (review mode only - no updates)
9. **go-http-handler-assistant**: HTTP handler organization, inline handler detection, architectural patterns (review mode only - no updates)
10. **go-test-coverage-assistant**: Test coverage gaps, missing tests for critical components (review mode only - no updates)

*Python projects:*
1. **python-quality-assistant**: Code quality, type hints, error handling

*All projects:*
11. **license-assistant**: LICENSE file, README license section (ALWAYS run in full mode, review mode only)
12. **readme-quality-assistant**: README.md quality and completeness (review mode only - no updates)
13. **shellcheck-assistant**: Shell script quality, security, and best practices
14. **context7-library-checker**: Check library usage against up-to-date docs, detect deprecated APIs (review mode only)

Run agents concurrently using multiple Task tool calls in a single message for maximum efficiency.

### Step 5: Consolidated Report

Merge all agent findings into a unified report. Each agent owns its domain — do NOT duplicate their rules here.

Organize by severity:

#### Must Fix (Critical)
Agent-reported critical issues (security, context violations, concurrency bugs, data correctness, transaction deadlocks, circular imports, time.Now()/time.Time usage).

#### Should Fix (Important)
Agent-reported important issues (error handling, architecture, factory/handler patterns, test gaps, tooling, licensing).

#### Nice to Have (Optional)
Agent-reported minor issues (style, documentation, naming conventions, version updates).

### Step 6: Next Steps

If `go-test-coverage-assistant` reported missing tests, suggest:
```
/coding:go-write-test basic    — minimal tests for modified files
/coding:go-write-test standard — comprehensive with error cases
```

### Step 7: Manual Review (Short Mode / Non-Go)

For projects without agent coverage, review manually:
1. Code quality and readability
2. Security vulnerabilities
3. Performance bottlenecks
4. Test coverage
5. Documentation completeness
