---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+)
argument-hint: "[short|standard|full] [directory]"
description: Perform a comprehensive code review of recent changes
---

## Context

- Current git status: `!git status`
- Recent changes (stat): `!git diff --stat HEAD~1`
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

**3a. Check for LICENSE file (public repos only)**

First, detect if the repo is public or private:
- Run `git remote -v` and check the URL
- `github.com` → **public** → check LICENSE
- `bitbucket.seibert.tools` or other internal hosting → **private** → skip all license checks

For public repos, use Glob to check if LICENSE file exists in project root:
```
LICENSE or LICENSE.md or LICENSE.txt
```

Store result for later:
- If private repo → skip license-assistant entirely (no LICENSE needed)
- If public and missing → flag for license-assistant in Standard mode, report in Short mode
- If public and present → skip license-assistant in Standard mode

**3b. Run make precommit (Full mode only)**

Running the full test suite is CI's job; the review needs the result, not a re-run. In **Standard** and **Short** mode, skip this step entirely and include in the Step 5 report: "precommit skipped (standard mode) — CI covers lint+test".

**Full mode only**: Check if Makefile exists and has a `precommit` target:
1. Use Read tool to check if Makefile exists (will error if missing)
2. Use Grep tool to search for `^precommit:` pattern in Makefile

If both checks pass, use Task tool with simple-bash-runner agent:
```
Task tool with subagent_type="coding:simple-bash-runner", prompt="cd [directory] && make precommit"
```

This provides automated checks (formatting, linting, tests, security) before running agents. Include the output and any failures in the final report.

If Makefile doesn't exist or lacks `precommit` target, skip this step. If `make precommit` fails, note the failures but continue with the review.

### Step 4: Dispatcher — ast-grep funnel → per-Owner LLM adjudication

Mirrors `commands/pr-review.md` Step 4 (PR #27). Mechanical pre-filter via `coding:ast-grep-runner`; LLM-tier adjudication only for findings that survive plus judgment-tier rules with no mechanical YAML.

**Short Mode**: No agents — skip to Step 5.
- BUT: if LICENSE missing AND repo is public, add to "Should Fix":
  - "Missing LICENSE file"
  - "README missing license section" (check with Grep for `## License` in README.md)

#### 4.0: Toolchain preflight (fail-fast)

Mirror of `commands/pr-review.md` Step 4.0. Verify `ast-grep` is in PATH before invoking the runner; the runner fail-fasts on the same check (`agents/ast-grep-runner.md` Step 0), but doing it here too keeps the failure surface close to the dispatcher:

```bash
cd <directory> && (command -v ast-grep >/dev/null 2>&1 || command -v sg >/dev/null 2>&1) \
  || { echo "ERROR: ast-grep/sg not in PATH. Install via 'npm install -g @ast-grep/cli' (or 'apk add ast-grep' in alpine). pr-reviewer container fix: bborbe/maintainer agent/pr-reviewer/Dockerfile commit 1de083f." >&2; exit 1; }
```

Run exactly this one command, once. If it fails: report the toolchain gap in Step 5 and skip Step 4 entirely. Do NOT investigate further (no `which`, no `ls rules/`, no retry variants).

#### 4a: Mechanical funnel

```
coding:ast-grep-runner agent: "TARGET_DIR=<directory>. Run every ast-grep YAML in rules/<lang>/*.yml. Return findings grouped by Owner per the agent's documented JSON contract."
```

Emits `{stats, findings_by_owner: {<agent-name>: [...findings]}, errors}`.

#### 4b: Per-Owner adjudication

For each `<owner>` in `findings_by_owner` AND for each non-mechanical (judgment-tier) rule whose `owner` matches a per-language agent in `agents/`:

```
coding:<owner> agent: "TARGET_DIR=<directory>.

Pre-filtered mechanical findings (from ast-grep-runner):
<findings_by_owner[<owner>] JSON>

Judgment-tier rules you own (from rules/index.json):
<list of rule ids with enforcement=judgment AND owner=<this agent>>

Adjudicate: for each finding, assign severity (Critical / Important / Optional), add a fix suggestion that cites the rule by ID. Drop any finding whose rule_id is not in the index — that's a stale-walker bug, not your concern.

Also scan the diff for judgment-tier rules listed above and report violations you find there.

Review changed code only."
```

Run per-Owner dispatches **concurrently** — they're independent.

**Timing instrumentation** (mirror of `commands/pr-review.md` Step 4b): **Only when `REVIEW_TIMING=1` is set in the environment** — otherwise skip this instrumentation entirely. Record wall-time of each per-Owner dispatch as a structured event so the funnel's per-Owner ROI is measurable, not anecdotal:

```bash
ts_start=$(date +%s%3N)
# ... invoke coding:<owner> agent ...
ts_end=$(date +%s%3N)
echo "{\"event\":\"per_owner_adjudication\",\"owner\":\"<owner>\",\"findings_in\":<count>,\"wall_ms\":$((ts_end - ts_start))}" >> /tmp/code-review-timing.jsonl
```

Roll-up summary after all owners return:

```bash
# Filter to per_owner_adjudication events only — wc -l over-counts when the
# file has stale lines from a prior unclean run or the summary line itself.
total_ms=$(jq -s 'map(select(.event == "per_owner_adjudication") | .wall_ms) | add' /tmp/code-review-timing.jsonl)
owners_invoked=$(grep -c '"event":"per_owner_adjudication"' /tmp/code-review-timing.jsonl)
echo "{\"event\":\"per_owner_summary\",\"owners_invoked\":$owners_invoked,\"total_ms\":$total_ms}" >> /tmp/code-review-timing.jsonl
```

Diagnostic only — operators read it to answer "is Owner X worth dispatching?" with data. Not part of the Step 5 user-facing report. `code-review.md` has no formal cleanup step (the command works against the current branch in-place; there is no review-worktree to remove), so end the run with `rm -f /tmp/code-review-timing.jsonl` to keep the file from accumulating stale lines across reviews.

#### 4c: Context-specific conventions

Load these conventionally when the diff matches:

| If diff touches… | Read first |
|---|---|
| `.env` files OR `k8s/*-secret.yaml` OR templates with `teamvault*` functions | `~/Documents/workspaces/coding/docs/teamvault-conventions.md` (teamvault lookup keys are not exposed credentials) |
| `main.go` of a k8s-deployed service | `~/Documents/workspaces/coding/docs/go-k8s-binary-conventions.md` |
| `k8s/*.yaml` (non-secret) | `~/Documents/workspaces/coding/docs/k8s-manifest-guide.md` |
| `CHANGELOG.md` | `~/Documents/workspaces/coding/docs/changelog-guide.md` |

#### 4d: Citation validation

```bash
coding:simple-bash-runner agent: "bash scripts/validate-citations.sh <findings.json>"
```

Drops findings citing missing rule IDs; logs drift to stderr.

#### Conditional / full-mode agents (independent of rule-base)

These are file-presence / language-feature checks not yet expressed as RULE blocks in `rules/index.json`. Continue invoking directly:

- **`license-assistant`** — public repos with missing LICENSE
- **`readme-quality-assistant`** — full mode only (README quality)
- **`shellcheck-assistant`** — shell-script review
- **`context7-library-checker`** — full mode; up-to-date library docs
- **`go-version-manager`** / **`go-tooling-assistant`** — full mode; version + Makefile checks

These will migrate to RULE blocks in follow-up PRs as their conventions get canonicalised. For now they fire on the legacy path alongside the dispatcher.

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
