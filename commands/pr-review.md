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
coding:simple-bash-runner agent: "cd <REVIEW_DIR> && make precommit"
```

Include failures in report. Continue regardless.

### Step 4: Dispatcher — ast-grep funnel → per-Owner LLM adjudication

The dispatcher replaces the previous hardcoded "load conventions + invoke fixed agent list" flow with a doc-driven pipeline backed by `rules/index.json`. Mechanical pre-filter via `coding:ast-grep-runner`; LLM-tier adjudication only for findings that survive, plus judgment-tier rules that have no mechanical YAML.

**Short Mode**: No agents — skip to Step 5.

#### 4a: Mechanical funnel

```
coding:ast-grep-runner agent: "TARGET_DIR=<REVIEW_DIR>. Run every ast-grep YAML in rules/<lang>/*.yml. Return findings grouped by Owner per the agent's documented JSON contract."
```

The runner emits `{stats, findings_by_owner: {<agent-name>: [...findings]}, errors}`.

#### 4b: Per-Owner adjudication

For each `<owner>` in `findings_by_owner` AND for each non-mechanical (judgment-tier) rule whose `owner` matches a per-language agent in `agents/`:

```
coding:<owner> agent: "REVIEW_DIR=<REVIEW_DIR>.

Pre-filtered mechanical findings (from ast-grep-runner):
<findings_by_owner[<owner>] JSON>

Judgment-tier rules you own (from rules/index.json):
<list of rule ids with enforcement=judgment AND owner=<this agent>>

Adjudicate: for each finding, assign severity (Critical / Important / Optional), add a fix suggestion that cites the rule by ID, and report findings citing only rule_ids that exist in rules/index.json. Drop any finding whose rule_id is not in the index — that's a stale-walker bug, not your concern.

Also scan the diff for judgment-tier rules listed above and report violations you find there.

Only review changed files from the diff. Exclude vendor/ and node_modules/."
```

Run these per-owner dispatches **concurrently** — they're independent.

#### 4c: Context-specific conventions (kept from prior Step 2.5)

Some review questions still benefit from a full-doc read even in dispatcher mode. Load these conventionally when the diff matches:

| If diff touches… | Read first |
|---|---|
| `.env` files OR `k8s/*-secret.yaml` OR templates with `teamvault*` functions | `~/Documents/workspaces/coding/docs/teamvault-conventions.md` (so secrets review does not flag teamvault LOOKUP KEYS — short alphanumeric values like `kLoejw` — as exposed credentials) |
| `main.go` of a service deployed to k8s (HTTP server, StatefulSet, Deployment) | `~/Documents/workspaces/coding/docs/go-k8s-binary-conventions.md` |
| `k8s/*.yaml` (non-secret) | `~/Documents/workspaces/coding/docs/k8s-manifest-guide.md` |
| `CHANGELOG.md` | `~/Documents/workspaces/coding/docs/changelog-guide.md` |

Inside the YOLO container the docs are mounted at `/home/node/.claude/plugins/marketplaces/coding/docs/`.

#### 4d: Citation validation

Before consolidating in Step 5, walk every finding from 4b's agent reports and verify its `rule_id` field exists in `rules/index.json`. Drop findings citing missing IDs — they're hallucinations or stale-walker references. Log dropped findings to stderr so the post-review smoke can detect drift.

```bash
coding:simple-bash-runner agent: "bash scripts/validate-citations.sh <findings.json>"
```

The script exits non-zero if any finding's `rule_id` is not in `rules/index.json`; the dispatcher logs the offenders and continues with the validated subset.

#### Conditional agents (independent of rule-base)

- **license-assistant**: Only if LICENSE missing (independent of rules/index.json — file-presence check)
- **readme-quality-assistant** / **shellcheck-assistant** / **context7-library-checker**: Full Mode only; called as before

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
