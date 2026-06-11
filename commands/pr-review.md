---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+), Bash(git fetch:+), Bash(git worktree:+), Bash(git branch:+), Bash(rm -rf:+)
argument-hint: "<target-branch> [short|standard|full|selector]"
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

#### 0a-pre: Short-circuit — skip worktree creation if already at PR head

After parsing arguments, before fetching, run exactly this one check:

```bash
git fetch origin <SOURCE_BRANCH> && [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/<SOURCE_BRANCH>)" ] && [ -z "$(git status --porcelain)" ] && echo "ALREADY_AT_HEAD"
```

If this prints `ALREADY_AT_HEAD`: set `REVIEW_DIR` = current directory, skip steps 0b and 0d (no worktree to create or remove), and proceed directly to 0c (generate diff). Do not run any further git exploration (worktree list, show-ref, rev-parse variants) — this check is authoritative.

Rationale: in the agent pod the cwd is already a worktree at PR HEAD; the unconditional worktree dance costs ~18 extra tool calls per review.

If the output does not contain `ALREADY_AT_HEAD`, fall through to 0b as normal.

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
- `--selector` or `selector` → **Selector mode** (in-session classify + adjudicate, zero sub-agent spawns)
- Otherwise → **Standard mode** (4 core agents, default)

### Step 2: Project Detection

Detect project type in `REVIEW_DIR`:
- **Go**: `go.mod` exists
- **Python**: `pyproject.toml` or `requirements.txt` exists

### Step 3: Run Automated Checks (All Modes)

**3a. Check for LICENSE file** in `REVIEW_DIR` root.

**3b. Run make precommit (Full mode only)**

Running the full test suite is CI's job; the review needs the result, not a re-run. In **Standard** and **Short** mode, skip this step entirely and include in the Step 5 report: "precommit skipped (standard mode) — CI covers lint+test".

**Full mode only**: Check if `REVIEW_DIR/Makefile` exists and has `precommit` target. If yes:
```
coding:simple-bash-runner agent: "cd <REVIEW_DIR> && make precommit"
```

Include failures in report. Continue regardless.

### Step 4: Dispatcher — ast-grep funnel → findings-scoped LLM adjudication

The dispatcher runs the full mechanical+script funnel first (diff-scoped), then spawns adjudication Tasks only for owners that have findings or active judgment rules. **Standard mode**: zero LLM spawns when the funnel is clean and no judgment rules are active. **Full mode**: keeps today's behavior (all relevant owners + conditional agents).

**Short Mode**: No agents — skip to Step 5.

**Early exit (standard mode)**: if NO changed file has extension `.go` or `.py` AND none matches `CHANGELOG.md`, `go.mod`, `LICENSE*`, `README.md`, `Makefile`, `pyproject.toml`, `k8s/**`, `agents/**`, `commands/**`, `skills/**`, `docs/**` — the diff cannot match any rule. Skip Step 4 entirely; note "Step 4 skipped: no rule-relevant files changed" in the report. One glance at the Step 0c diff stat decides this — no tool calls needed.

#### 4.0: Toolchain preflight (fail-fast)

Before invoking the runner, verify `ast-grep` is available in PATH. The runner script fail-fasts on the same check (exit 2 + JSON error), but doing it here too keeps the failure surface close to the dispatcher so the user sees a single clear error rather than the runner's JSON envelope:

```bash
cd <REVIEW_DIR> && (command -v ast-grep >/dev/null 2>&1 || command -v sg >/dev/null 2>&1) \
  || { echo "ERROR: ast-grep/sg not in PATH. Install via 'npm install -g @ast-grep/cli' (or 'apk add ast-grep' in alpine). pr-reviewer container fix: bborbe/maintainer agent/pr-reviewer/Dockerfile commit 1de083f." >&2; exit 1; }
```

Run exactly this one command, once. If it fails: report the toolchain gap in Step 5 (Must Fix) and skip Step 4 entirely. Do NOT investigate further (no `which`, no `ls rules/`, no retry variants). A review without the mechanical funnel would silently miss every MUST-tier YAML finding.

#### 4a: Mechanical funnel

Run `scripts/ast-grep-runner.sh` (deterministic — covers ast-grep YAMLs AND script-tier rule-checks, diff-scoped) over the changed files identified from `git diff --stat` in Step 0c. The script ships with the coding plugin; resolve its path first — plugin install dir, falling back to the local checkout:

```bash
RUNNER="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh"
[ -x "$RUNNER" ] || RUNNER="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/scripts/ast-grep-runner.sh"
[ -x "$RUNNER" ] || RUNNER="$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh"
"$RUNNER" <REVIEW_DIR> <changed files, space-separated> > /tmp/pr-review-findings.json
```

Run exactly this one Bash call, once. The runner emits `{stats, findings_by_owner: {<agent-name>: [...findings]}, errors}` — read it from `/tmp/pr-review-findings.json`. Do NOT spawn an agent for this step (the former `coding:ast-grep-runner` agent is deprecated). If the runner is missing or fails: note "mechanical funnel unavailable" for the Step 5 report and continue with Step 4b using judgment-rule triggers only — do NOT investigate (no `find`, no `which`, no path probing).

#### 4b: Findings-scoped adjudication (standard mode)

Compute the active judgment-rule set and dispatch owners selectively:

**Step 4b-i: Active judgment rules** — compute which judgment-tier rules are triggered by the diff. Run:

```bash
CHANGED_FILES="<newline-separated list from git diff --stat>"
jq -r --arg files "$CHANGED_FILES" '
  [ .[] | select(.enforcement_type == "judgment") |
    select(
      .trigger == null or
      (.trigger | any(. as $pat |
        ($files | split("\n") | .[] |
          (. == $pat) or
          (($pat | startswith("@")) and $pat == "@commits") or
          (($pat | contains("*")) and
            (. | test("^" + ($pat | gsub("\\."; "\\.") | gsub("\\*\\*/"; "°") | gsub("\\*\\*"; "±") | gsub("\\*"; "[^/]*") | gsub("\\?"; "[^/]") | gsub("°"; "(.*/)?") | gsub("±"; ".*")) + "$"))
          )
        )
      ))
    )
  ] | .[] | .id + " " + .owner
' rules/index.json
```

This produces a list of `<rule-id> <owner>` pairs whose trigger globs match at least one changed file. Rules with `trigger: ["@commits"]` are always included.

**Step 4b-ii: Dispatch set** — the set of owners to spawn is:

```
owners_to_spawn = (keys of findings_by_owner) ∪ (owners from active judgment rules)
```

If `owners_to_spawn` is empty AND `findings_by_owner` is empty, report "funnel clean — no adjudication needed" and proceed to Step 5. ZERO LLM spawns.

Otherwise, spawn ONE Task per owner in `owners_to_spawn` **concurrently**. Owners NOT in the set are NOT spawned — no exceptions in standard mode. Each Task prompt:

```
coding:<owner> agent: "REVIEW_DIR=<REVIEW_DIR>.

Pre-filtered mechanical findings for you (from ast-grep-runner):
<findings_by_owner[<owner>] JSON, or empty array if none>

Active judgment rules you own (from rules/index.json, triggered by this diff):
<list of rule blocks — id + doc_path + applies_when — for this owner only>

Adjudicate: for each mechanical finding, assign severity (Critical / Important / Optional), add a fix suggestion that cites the rule by ID. Drop any finding whose rule_id is not in the index — stale-walker bug, not your concern.

Also scan the diff for each active judgment rule listed above and report violations you find. Read only changed files relevant to those rules.

Only review changed files from the diff. Exclude vendor/ and node_modules/."
```

**Timing instrumentation**: **Only when `REVIEW_TIMING=1` is set in the environment** — otherwise skip this instrumentation entirely. Record the wall-time of each per-Owner dispatch as a structured event. Recommended shape — one log line per Owner before and after the agent runs:

```bash
ts_start=$(date +%s%3N)
# ... invoke coding:<owner> agent ...
ts_end=$(date +%s%3N)
echo "{\"event\":\"per_owner_adjudication\",\"owner\":\"<owner>\",\"findings_in\":<count>,\"wall_ms\":$((ts_end - ts_start))}" >> /tmp/pr-review-timing.jsonl
```

After all per-Owner dispatches return, append a roll-up summary line:

```bash
# Filter to per_owner_adjudication events only — wc -l over-counts when the
# file has stale lines from a prior unclean run or the summary line itself.
total_ms=$(jq -s 'map(select(.event == "per_owner_adjudication") | .wall_ms) | add' /tmp/pr-review-timing.jsonl)
owners_invoked=$(grep -c '"event":"per_owner_adjudication"' /tmp/pr-review-timing.jsonl)
echo "{\"event\":\"per_owner_summary\",\"owners_invoked\":$owners_invoked,\"total_ms\":$total_ms}" >> /tmp/pr-review-timing.jsonl
```

The timing file `/tmp/pr-review-timing.jsonl` is purely diagnostic — it lets operators answer "is Owner X worth dispatching?" with data instead of intuition. Not part of the Step 5 user-facing report; include it in the cleanup step for the review worktree so it gets removed after Step 6.

#### Selector mode: Steps 4c-sel and 4d-sel

When the mode argument is `--selector` or `selector`: Steps 4.0, 4a, and 4b-i run unchanged. Skip Step 4b-ii. Resolve the guide and execute Steps 4c-sel and 4d-sel from it — zero sub-agent spawns:

```bash
GUIDE="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/docs/selector-mode-guide.md"
[ -f "$GUIDE" ] || GUIDE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/docs/selector-mode-guide.md"
```

Read the guide, then execute its **Step 4c-sel CLASSIFY** and **Step 4d-sel ADJUDICATE** with:

- **DIFF** = the Step 0c diff (`git diff origin/<TARGET_BRANCH>...HEAD`)
- **CANDIDATES** = the Step 4b-i `<rule-id> <owner>` output
- **MECHANICAL_FINDINGS** = `/tmp/pr-review-findings.json`
- **Working directory** = `REVIEW_DIR`

On the guide's short-circuit condition the report line is `selector clean — no adjudication needed`. When the mode is anything else (short/standard/full), skip this section entirely.

Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.

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

#### Selector Mode: Classify Traceability (selector mode only)

Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.

### Step 6: Next Steps Recommendation

If test coverage gaps found, suggest `/go-write-test` commands.

### Step 7: Manual Review (All Projects)

Focus on changed code only. After review, **clean up the worktree** (Step 0d).
