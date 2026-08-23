---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+)
argument-hint: "[short|full|selector] [directory] [--security]"
description: Perform a comprehensive review of local uncommitted/recent changes
---

## Context

- Current git status: `!git status`
- Recent changes (stat): `!git diff --stat HEAD~1`
- Recent commits: `!git log --oneline -5`
- Current branch: `!git branch --show-current`

## Your task

Perform a review of local uncommitted/recent changes (since `HEAD~1`) with configurable depth based on mode. For branch-vs-target review use `/coding:pr-review`; for whole-codebase audit use `/coding:code-review`.

### Step 1: Parse Arguments

Parse the first argument to determine mode:
- If first arg is `short|quick|fast` → **Short mode** (manual review only)
- If first arg is `full|comprehensive|complete` → **Full mode** (all agents, per-owner dispatch)
- Otherwise (including `standard`, `selector`, `--selector`, or no token) → **Selector mode (default)** (in-session classify + adjudicate, zero sub-agent spawns)

`--security` is a position-independent boolean flag that may appear anywhere in the argument list (before or after the mode token and the directory); when present, set `SECURITY_REVIEW=1`, independent of the mode token. It is recognized as a flag and is NOT treated as the directory path by the "Any remaining arguments are treated as the directory path" rule. The flag is never silently ignored — the security pipeline runs in-session over the reviewed scope regardless of mode token; the existing short-mode "skip Step 4" directive applies only to the non-security funnel.

Any remaining arguments are treated as the directory path.

### Step 2: Project Detection

Detect project type to determine which specialist agents to invoke:
- **Go project**: Check for `*.go` files or `go.mod`
- **Python project**: Check for `*.py` files or `pyproject.toml`/`requirements.txt`
- **Node project**: Check for `package.json`. Distinguish backend service (no bundler config, no `.vue`/`.jsx`/`.tsx` sources → `node-quality-assistant` owns it) from frontend application (bundler config or component sources → the `node/*` service rules do NOT apply)
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

Running the full test suite is CI's job; the review needs the result, not a re-run. In **Selector** and **Short** mode, skip this step entirely and include in the Step 5 report: "precommit skipped (selector mode) — CI covers lint+test".

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

Mirrors `commands/pr-review.md` Step 4. The funnel runs first (diff-scoped), then adjudicates findings in-session. **Selector mode (the default)**: in-session classify + adjudicate, zero sub-agent spawns. **Full mode**: keeps per-owner dispatch (all relevant owners + conditional agents). **Short mode**: skips Step 4 entirely.

**Short Mode**: No agents — skip to Step 5.

**Early exit**: if NO changed file has extension `.go`, `.py`, `.js`, `.mjs`, `.cjs`, `.ts`, `.tsx`, or `.vue` AND none matches `CHANGELOG.md`, `go.mod`, `LICENSE*`, `README.md`, `Makefile`, `Makefile.*`, `pyproject.toml`, `package.json`, `tsconfig.json`, `k8s/**`, `agents/**`, `commands/**`, `skills/**`, `docs/**` — the diff cannot match any rule. Skip Step 4 entirely; note "Step 4 skipped: no rule-relevant files changed" in the report. One glance at the diff stat decides this — no tool calls needed.

Changed files under a `node_modules/`, `dist/`, `build/`, or `coverage/` path segment do not count toward this check — they are generated or installed, and a committed bundle is often a single minified multi-megabyte line.
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
"$RUNNER" <directory> <changed files, space-separated> > /tmp/local-review-findings.json
```

Run exactly this one Bash call, once. Emits `{stats, findings_by_owner: {<agent-name>: [...findings]}, errors}` — read it from `/tmp/local-review-findings.json`. Do NOT spawn an agent for this step (the former `coding:ast-grep-runner` agent is deprecated). If the runner is missing or fails: note "mechanical funnel unavailable" for the Step 5 report and continue with Step 4b using judgment-rule triggers only — do NOT investigate (no `find`, no `which`, no path probing).

#### 4b: Findings-scoped candidate computation

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

This produces a list of `<rule-id> <owner>` pairs whose trigger globs match at least one changed file. Rules with `trigger: ["@commits"]` are always included. This output feeds both Selector mode (Steps 4c-sel/4d-sel) and Full mode (per-owner dispatch).

#### Selector mode (the default): Steps 4c-sel and 4d-sel

Steps 4.0, 4a, and 4b-i run unchanged. Resolve the guide and execute Steps 4c-sel and 4d-sel from it — zero sub-agent spawns.

Run exactly this one command, once:

```bash
GUIDE="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/docs/selector-mode-guide.md"
[ -f "$GUIDE" ] || GUIDE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/docs/selector-mode-guide.md"
[ -f "$GUIDE" ] && echo "GUIDE_OK: $GUIDE" || echo "GUIDE_MISSING"
```

If it prints `GUIDE_MISSING`: report "selector guide unavailable" as a **Must Fix toolchain failure** in Step 5 and STOP the selector path — do NOT continue with a mechanical-findings-only review presented as a complete selector review (a review without the judgment tier silently misses every judgment-tier rule; same fail-fast discipline as Step 4.0). Do NOT investigate further (no `find`, no `ls`, no path probing).

If it prints `GUIDE_OK`: Read the file at that path, then execute its **Step 4c-sel CLASSIFY** and **Step 4d-sel ADJUDICATE** with:

- **DIFF** = `git diff HEAD~1` (or directory diff as parsed in Step 1)
- **CANDIDATES** = the Step 4b-i `<rule-id> <owner>` output
- **MECHANICAL_FINDINGS** = `/tmp/local-review-findings.json`
- **Working directory** = the reviewed directory

On the guide's short-circuit condition the report line is `selector clean — no adjudication needed`. Skip this section for short/full mode.

Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.

#### Security mode (under `--security` only)

This subsection runs only when `SECURITY_REVIEW` is set (Step 1). It activates the dormant `## Security Extension (dormant)` in `docs/selector-mode-guide.md` — when the signal is absent, Steps 4c-sel/4d-sel run byte-for-byte as the existing procedure above. It references the frozen pipeline guide (`docs/security/security-review-pipeline.md`), the selector-mode security extension, the verifier agent (`agents/security-verifier.md`), and the polymorphic validator (`scripts/validate-citations.sh`) by name — it does NOT re-implement or re-document the procedure. It runs in **every** mode (short, selector, full) and never bypasses or softens the existing Step 4.0 toolchain fail-fast (ast-grep/sg preflight → "Must Fix toolchain failure") or the Step 4a mechanical funnel — a `--security` review without the mechanical funnel would silently miss every MUST-tier finding.

1. **Recon and model derivation** — per `docs/security/security-review-pipeline.md` (the derivation contract is frozen there): the recon and the adjudicator consume the local diff `git diff HEAD~1` (or the directory diff parsed in Step 1); enumerate entry points from the diff's touched packages (recall-oriented), resolve identities and auth mechanisms, resolve resources and their `authorization_functions`, and derive invariants as `resource → identifier → authorization_function` with `file:line` evidence. Write the model to `/tmp/security-model.json` (session-local, mirroring `/tmp/local-review-findings.json`) and never to any path inside the reviewed directory — if the model is accidentally written in-tree, delete it and rewrite it to the session-local path. Apply the freshness gate (changed-evidence entries re-derived, unchanged carried forward; stale entries whose evidence no longer resolves are dropped and surfaced with the literal `model refresh:` line) and diff-relevant truncation on large repos (note the truncation in the report). Record the attack-surface inventory counts.
2. **Classifier trait groups** — per the dormant extension: exactly six groups `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. `authz` over-selection is non-negotiable: a diff touching a file cited as evidence by an entry point operating on a modeled resource, or cited as evidence by a modeled resource's `authorization_function`, MUST select `authz`. Deterministic invariant selection: a diff touching an invariant's `attack_surfaces` or its `evidence` source forces that `invariant_id` into the applicable set — no LLM judgment, never skipped. The HARD INVARIANT holds: the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
3. **Adjudicator inputs** — the Step 4d-sel adjudicator input gains the diff-relevant model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal. Each applicable invariant is judged against the diff slice with the single question: does this change preserve the invariant? Invariant-kind findings cite `invariant_id`.
4. **Verifier gate** — after adjudication, before emission, run the falsification gate per `agents/security-verifier.md` (7-item falsification checklist; verdict `confirmed | plausible | rejected` with `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, and `reject_reason` required on rejection). It is a hard pre-emission step for `severity=critical` and for `severity=major` when `confidence=confirmed`; every surviving high-severity finding carries a populated `counterevidence_checked`. The execution mechanism (in-session role vs sub-agent spawn) is an implementation detail the session decides, preserving the gate's hard pre-emission property. Residual false kills are caught by the `ai_review` post-post backstop (dismiss + COMMENT + human_review).
5. **Blocking derived, never stored as severity** — `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`; no per-surface config fields, no opt-out flags. A `plausible` critical does NOT block merge — it is reported as a required human review item.
6. **Diff anchoring** — in local mode (PR mode), report security findings ONLY on diff-changed lines or invariants whose attack surface the diff touched; whole-file context is permitted for reasoning, never for gating.
7. **Toolchain/deps pass (fail-closed)** — run a dependency scan over the local repo's dependency manifests (osv-scanner / trivy / govulncheck, whichever are available; govulncheck for Go modules), executed via the `coding:go-security-specialist` agent or in-session per the selector-mode zero-spawn property, and emit findings as `kind=toolchain` carrying `tool`, `package`, `version`, `advisory`, `file`, `line`. A scan failure, a database-fetch timeout, or a flagged vulnerability surfaces as a Must-Fix toolchain finding in the report — never a silent skip.
8. **Citation validation** — the Step 4d-sel citation-validation invocation passes `SECURITY_MODEL_FILE=/tmp/security-model.json` so invariant-kind findings resolve against the session model's `invariants[].id`. Each finding resolves exactly one provenance (`kind=rule` → `rule_id` in `rules/index.json`; `kind=invariant` → `invariant_id` in the model; `kind=toolchain` → no id). Absent an unset/missing/unreadable/unparseable model, invariant findings drop fail-closed (WARN to stderr) and are never kept — the validator enforces this; the command only supplies the model file.

#### Full mode: per-owner dispatch

**Full mode only** — skip this section in selector and short mode.

Compute the dispatch set from Step 4b-i and Step 4a findings:

```
owners_to_spawn = (keys of findings_by_owner) ∪ (owners from active judgment rules)
```

If `owners_to_spawn` is empty AND `findings_by_owner` is empty, report "funnel clean — no adjudication needed" and proceed to Step 5. ZERO LLM spawns.

Otherwise, spawn ONE Task per owner in `owners_to_spawn` **concurrently** — they're independent. Each Task prompt:

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

#### 4c: Context-specific conventions

Load these conventionally when the diff matches:

| If diff touches… | Read first |
|---|---|
| `.env` files OR `k8s/*-secret.yaml` OR templates with `teamvault*` functions | `~/Documents/workspaces/coding/docs/teamvault-conventions.md` (teamvault lookup keys are not exposed credentials) |
| `main.go` of a k8s-deployed service | `~/Documents/workspaces/coding/docs/go-k8s-binary-conventions.md` |
| `k8s/*.yaml` (non-secret) | `~/Documents/workspaces/coding/docs/k8s-manifest-guide.md` |
| `CHANGELOG.md` | `~/Documents/workspaces/coding/docs/changelog-guide.md` |

#### 4d: Citation validation

**Full mode only** (selector mode's own citation call lives in the guide). Walk every finding from the per-owner agent reports and verify its `rule_id` field exists in `rules/index.json`. Drop findings citing missing IDs — they're hallucinations or stale-walker references. Log dropped findings to stderr.

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

Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.

#### Security Findings (under `--security` only)

When `SECURITY_REVIEW` is set, list every security finding (rule, invariant, and toolchain) with `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields (`confidence`, `exploitability`, `impact`, `counterevidence_checked`), and the derived blocking state.

#### Security Model (under `--security` only)

When `SECURITY_REVIEW` is set, record the provenance block: `derived_from` (repo, head, review_id), the entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. A scope containing Go source always produces this block (never a silent skip); a scope with no Go source — including when the Step 4 early-exit fires on a non-rule-relevant diff — states `no Go source — security model not derived` explicitly instead of omitting the section.

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
