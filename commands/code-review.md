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
- If first arg is `--selector` or `selector` → **Selector mode** (in-session classify + adjudicate, zero sub-agent spawns)
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

### Step 4: Dispatcher — ast-grep funnel → findings-scoped LLM adjudication

Mirrors `commands/pr-review.md` Step 4. The funnel runs first (diff-scoped), then adjudication Tasks are spawned only for owners with findings or active judgment rules. **Standard mode**: zero LLM spawns when the funnel is clean and no judgment rules are active. **Full mode**: keeps today's behavior (all relevant owners + conditional agents).

**Short Mode**: No agents — skip to Step 5.

**Early exit (standard mode)**: if NO changed file has extension `.go` or `.py` AND none matches `CHANGELOG.md`, `go.mod`, `LICENSE*`, `README.md`, `Makefile`, `pyproject.toml`, `k8s/**`, `agents/**`, `commands/**`, `skills/**`, `docs/**` — the diff cannot match any rule. Skip Step 4 entirely; note "Step 4 skipped: no rule-relevant files changed" in the report. One glance at the diff stat decides this — no tool calls needed.
- BUT: if LICENSE missing AND repo is public, add to "Should Fix":
  - "Missing LICENSE file"
  - "README missing license section" (check with Grep for `## License` in README.md)

#### 4.0: Toolchain preflight (fail-fast)

Mirror of `commands/pr-review.md` Step 4.0. Verify `ast-grep` is in PATH before invoking the runner; the runner script fail-fasts on the same check (exit 2 + JSON error), but doing it here too keeps the failure surface close to the dispatcher:

```bash
cd <directory> && (command -v ast-grep >/dev/null 2>&1 || command -v sg >/dev/null 2>&1) \
  || { echo "ERROR: ast-grep/sg not in PATH. Install via 'npm install -g @ast-grep/cli' (or 'apk add ast-grep' in alpine). pr-reviewer container fix: bborbe/maintainer agent/pr-reviewer/Dockerfile commit 1de083f." >&2; exit 1; }
```

Run exactly this one command, once. If it fails: report the toolchain gap in Step 5 and skip Step 4 entirely. Do NOT investigate further (no `which`, no `ls rules/`, no retry variants).

#### 4a: Mechanical funnel

Run `scripts/ast-grep-runner.sh` (deterministic — covers ast-grep YAMLs AND script-tier rule-checks, diff-scoped) over the changed files from `git diff --stat HEAD~1`. The script ships with the coding plugin; resolve its path first — plugin install dir, falling back to the local checkout:

```bash
RUNNER="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh"
[ -x "$RUNNER" ] || RUNNER="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/scripts/ast-grep-runner.sh"
[ -x "$RUNNER" ] || RUNNER="$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh"
"$RUNNER" <directory> <changed files, space-separated> > /tmp/code-review-findings.json
```

Run exactly this one Bash call, once. Emits `{stats, findings_by_owner: {<agent-name>: [...findings]}, errors}` — read it from `/tmp/code-review-findings.json`. Do NOT spawn an agent for this step (the former `coding:ast-grep-runner` agent is deprecated). If the runner is missing or fails: note "mechanical funnel unavailable" for the Step 5 report and continue with Step 4b using judgment-rule triggers only — do NOT investigate (no `find`, no `which`, no path probing).

#### 4b: Findings-scoped adjudication (standard mode)

Compute the active judgment-rule set and dispatch owners selectively:

**Step 4b-i: Active judgment rules** — compute which judgment-tier rules are triggered by the diff. Run:

```bash
CHANGED_FILES="<newline-separated list from git diff --stat HEAD~1>"
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
coding:<owner> agent: "TARGET_DIR=<directory>.

Pre-filtered mechanical findings for you (from ast-grep-runner):
<findings_by_owner[<owner>] JSON, or empty array if none>

Active judgment rules you own (from rules/index.json, triggered by this diff):
<list of rule blocks — id + doc_path + applies_when — for this owner only>

Adjudicate: for each mechanical finding, assign severity (Critical / Important / Optional), add a fix suggestion that cites the rule by ID. Drop any finding whose rule_id is not in the index — stale-walker bug, not your concern.

Also scan the diff for each active judgment rule listed above and report violations you find. Read only changed files relevant to those rules.

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

#### Selector mode: Steps 4c-sel and 4d-sel

<!-- SIBLING COPY. commands/pr-review.md carries the CANONICAL version of this section; edit there first, mirror here, diff to verify. Single-file extraction is planned for the default-flip migration step. -->

**Selector mode** replaces Step 4b-ii's per-owner Task dispatch with two in-session steps. Steps 4.0, 4a, and 4b-i run unchanged and produce the candidate set. When the mode argument is `--selector` or `selector`, skip Step 4b-ii and run Steps 4c-sel and 4d-sel instead. When the mode is anything else (short/standard/full), skip this section entirely — the default path below is unchanged.

The diff source is the working-tree diff from `git diff HEAD~1` (or the directory diff as parsed in Step 1), consistent with how this command resolves the diff throughout.

##### Step 4c-sel: CLASSIFY (in-session, no Task spawn)

**Input**: the diff from the current working tree (`git diff HEAD~1`), the `<rule-id> <owner>` candidate list from Step 4b-i, and the `applies_when` text for each candidate from `rules/index.json`.

For each candidate rule, decide: **applicable** or **skipped** with a one-line reason (≤ 8 words).

**Recall contract (embed verbatim)**: "INCLUDE if a reasonable reviewer would want to read this rule before judging. Do not evaluate compliance. Do not evaluate violations. When uncertain, include."

**Skip justification rule**: a skip decision MUST be justified against the rule's `applies_when` text itself — the reason states why the `applies_when` condition does not hold for this diff. NEVER infer a rule's scope from its rule-id name or prefix (e.g. `go-testing/*` rules are NOT necessarily scoped to test files — read the `applies_when`). If the diff plausibly matches the `applies_when` condition, the rule is applicable.

**HARD INVARIANT**: the applicable set MUST be a subset of the candidate set. Every applicable rule_id must appear in the Step 4b-i candidate list. Never add a rule the glob did not produce.

**Architecture-tier bypass**: any candidate rule whose `enforcement` text contains "architecture" OR whose `doc_path` is `go-architecture-patterns.md` and concerns SRP/layering is unconditionally applicable — do not classify, always include it.

**Short-circuit**: if the applicable set is empty AND the mechanical findings from Step 4a are also empty, report:

> `selector clean — no adjudication needed`

and skip Step 4d-sel, proceeding directly to Step 5. Include the candidate count and a note that all candidates were classified as non-applicable in the Step 5 traceability section.

Produce a classify result:
```json
{
  "applicable": ["<rule-id>", "..."],
  "skipped": {
    "<rule-id>": "<one-line reason ≤ 8 words>",
    "...": "..."
  }
}
```

##### Step 4d-sel: ADJUDICATE (in-session, no Task spawn)

**Input**: the full diff (no truncation — this is the load-bearing step), the mechanical findings from Step 4a, and the applicable rules from Step 4c-sel.

For each applicable rule: locate the rule's `doc_path` in `rules/index.json`, then read only the matching `### RULE <id>` block from that file (grep for the heading, read the block — do not read the whole document).

Judge the full diff plus mechanical findings. For each violation found, emit a finding that cites `rule_id` + file + line and lands in the existing report buckets:

- **Must Fix (Critical)** — security, context violations, concurrency bugs, data correctness, SRP (3+ concerns)
- **Should Fix (Important)** — architectural violations, error handling, factory/handler patterns, test gaps
- **Nice to Have (Optional)** — style, naming, minor version issues

Do not emit a per-rule "passed" entry for rules with no violation — silently omit them.

**Batching**: if the applicable set exceeds 20 rules, split adjudication into 2–3 thematic in-session passes (e.g. architecture rules first, then quality rules, then style rules). Each pass runs in the current session — still zero Task spawns. Collect all findings before proceeding to citation validation.

**Citation validation** (same contract as the default Step 4d, but invoked directly — selector mode spawns NO sub-agents, including `coding:simple-bash-runner`): run the validator as a plain Bash call over the adjudication findings before consolidation — findings citing a `rule_id` absent from `rules/index.json` are dropped and logged to stderr. Resolve the script path the same way Step 4a resolves the runner (the reviewed directory may not be the plugin checkout):

```bash
VALIDATOR="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/validate-citations.sh"
[ -x "$VALIDATOR" ] || VALIDATOR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/scripts/validate-citations.sh"
bash "$VALIDATOR" <findings.json>
```

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

#### Selector Mode: Classify Traceability (selector mode only)

Include this section only when the review ran in selector mode. List counts and every classify skip so operators can spot false drops:

- **Candidates**: `<N>` rules matched by Step 4b-i glob filter
- **Applicable**: `<M>` rules selected by Step 4c-sel (M ≤ N)
- **Skipped** (one line each):
  - `<rule-id>` → `<one-line reason>`
  - …

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
