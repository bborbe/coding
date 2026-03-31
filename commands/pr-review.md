---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+), Bash(git fetch:+), Bash(git worktree:+), Bash(git branch:+), Bash(rm -rf:+)
argument-hint: "<target-branch> [short|standard|full]"
description: Review current branch diff against target branch (excludes vendor/node_modules)
---

## Context

- Current directory: `!pwd`
- Current branch: `!git branch --show-current`

## Your task

Review current branch diff against a target branch. Uses a temporary git worktree so the main checkout stays untouched.

For Bitbucket PRs, use `/bitbucket-pr-review <url>` instead.

### Step 0: Create Worktree and Generate Diff

#### 0a: Parse arguments

- First argument: `TARGET_BRANCH` (default: `master`)
- Second argument: mode (see Step 1)
- `REPO_DIR` = current directory
- `SOURCE_BRANCH` = current branch

#### 0b: Fetch and create worktree

IMPORTANT: Never use `git -C` — breaks auto-approval.

```bash
cd <REPO_DIR> && git fetch origin
```

```bash
cd <REPO_DIR> && git worktree remove /tmp/pr-review-<repo>-<SOURCE_BRANCH> --force 2>/dev/null; true
```

```bash
cd <REPO_DIR> && git worktree add /tmp/pr-review-<repo>-<SOURCE_BRANCH> origin/<SOURCE_BRANCH> --detach
```

Set `REVIEW_DIR=/tmp/pr-review-<repo>-<SOURCE_BRANCH>` for all subsequent steps.

#### 0c: Generate diff

```bash
cd <REVIEW_DIR> && git diff origin/<TARGET_BRANCH>...HEAD -- . ':(exclude,glob)**/vendor/**' ':(exclude,glob)**/node_modules/**'
```

```bash
cd <REVIEW_DIR> && git diff --stat origin/<TARGET_BRANCH>...HEAD -- . ':(exclude,glob)**/vendor/**' ':(exclude,glob)**/node_modules/**'
```

If diff is empty, clean up worktree and report "No changes to review" and stop.

#### 0d: Cleanup (after ALL review steps complete)

```bash
cd <REPO_DIR> && git worktree remove /tmp/pr-review-<repo>-<SOURCE_BRANCH> --force
```

**IMPORTANT**: ALL subsequent steps must use `REVIEW_DIR` paths. Never read from the main checkout. All agent prompts MUST include: "Only review changed files from the diff. Exclude vendor/ and node_modules/. Do not flag issues in unchanged or vendored code."

### Step 1: Parse Mode Argument

- `short|quick|fast` → **Short mode** (manual review only)
- `full|comprehensive|complete` → **Full mode** (all agents)
- Otherwise → **Standard mode** (4 core agents, default)

### Step 2: Project Detection

Detect project type in `REVIEW_DIR`:
- **Go**: `go.mod` exists
- **Python**: `pyproject.toml` or `requirements.txt` exists

### Step 3: Run Automated Checks (All Modes)

**3a. Check for LICENSE file** in `REVIEW_DIR` root.

**3b. Run make precommit (if available)**

Check if `REVIEW_DIR/Makefile` exists and has `precommit` target. If yes:
```
simple-bash-runner agent: "cd <REVIEW_DIR> && make precommit"
```

Include failures in report. Continue regardless.

### Step 4: Automated Agent Review

All agent prompts MUST specify `REVIEW_DIR` as the working directory.

**Short Mode**: No agents — skip to Step 5.

**Standard Mode** (default):

*Go projects:*
1. **go-quality-assistant**: Idiomatic Go, error handling, context usage
2. **go-factory-pattern-assistant**: Factory compliance, zero-business-logic (review only)
3. **go-http-handler-assistant**: Handler organization, inline detection (review only)
4. **go-test-coverage-assistant**: Coverage gaps (review only)

*Python projects:*
1. **python-quality-assistant**: Style, type hints, error handling, async safety

*Conditional:*
- **license-assistant**: Only if LICENSE missing

**Full Mode**:

*Go projects:*
1-10: godoc, go-quality, go-test-quality, go-security, srp-checker, go-version-manager, go-tooling, go-factory-pattern, go-http-handler, go-test-coverage

*All projects:*
11-14: license, readme-quality, shellcheck, context7-library-checker

Run agents concurrently.

### Step 5: Consolidated Report

**IMPORTANT**: Only report findings for changed code from the diff.

**MANDATORY**: Always include all three headers. Write "None." if empty.

#### Must Fix (Critical)
- Security vulnerabilities, context.Background() in business logic, concurrency bugs, data correctness, transaction deadlocks, business logic in factories, SRP violations (3+ concerns), outdated Go (2+ minor behind), missing test suites, manual mocks, direct time in tests

#### Should Fix (Important)
- Error handling, architectural violations, SRP (business+I/O), factory methods outside pkg/factory/, inline handlers, missing tests, missing docs, Go version issues, wrong test naming, wrong Counterfeiter config, missing license

#### Nice to Have (Optional)
- Style, code organization, Go patch updates, tool updates, naming conventions, copyright headers

### Step 6: Next Steps Recommendation

If test coverage gaps found, suggest `/go-write-test` commands.

### Step 7: Manual Review (All Projects)

Focus on changed code only. After review, **clean up the worktree** (Step 0d).
