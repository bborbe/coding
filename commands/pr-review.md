---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+), Bash(git fetch:+), Bash(git worktree:+), Bash(git branch:+), Bash(rm -rf:+)
argument-hint: "<target-branch> [short|full|selector] [--security]"
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
- `--security` is a position-independent boolean flag that may appear anywhere in the argument list (before or after `TARGET_BRANCH` and the mode token); when present, set `SECURITY_REVIEW=1`. It is independent of the mode token and `TARGET_BRANCH`.

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
- `full|comprehensive|complete` → **Full mode** (all agents, per-owner dispatch)
- Otherwise (including `standard`, `selector`, `--selector`, or no token) → **Selector mode (default)** (in-session classify + adjudicate, zero sub-agent spawns)
- When `SECURITY_REVIEW` is set, the security-mode steps in Step 4 run in **every** mode — including short mode, which otherwise skips Step 4 (the existing short-mode "skip Step 4" directive applies only to the non-security funnel) — the flag is never silently ignored.

### Step 2: Project Detection

Detect project type in `REVIEW_DIR`:
- **Go**: `go.mod` exists
- **Python**: `pyproject.toml` or `requirements.txt` exists
- **Node**: `package.json` exists. Distinguish the two flavours — they own different rule sets:
  - **Backend service** — no bundler config (`vite.config.*`, `next.config.*`, `astro.config.*`) and no `.vue`/`.jsx`/`.tsx` sources. Owned by `node-quality-assistant`.
  - **Frontend application** — bundler config or component sources present. The `node/*` service rules do NOT apply; see `vue3-typescript-frontend-guide.md` / `astro-development-guide.md`.

### Step 3: Run Automated Checks (All Modes)

**3a. Check for LICENSE file** in `REVIEW_DIR` root.

**3b. Run make precommit (Full mode only)**

Running the full test suite is CI's job; the review needs the result, not a re-run. In **Selector** and **Short** mode, skip this step entirely and include in the Step 5 report: "precommit skipped (selector mode) — CI covers lint+test".

**Full mode only**: Check if `REVIEW_DIR/Makefile` exists and has `precommit` target. If yes:
```
coding:simple-bash-runner agent: "cd <REVIEW_DIR> && make precommit"
```

Include failures in report. Continue regardless.

### Step 4: Dispatcher — ast-grep funnel → findings-scoped LLM adjudication

The dispatcher runs the full mechanical+script funnel first (diff-scoped), then adjudicates findings in-session. **Selector mode (the default)**: in-session classify + adjudicate, zero sub-agent spawns. **Full mode**: keeps per-owner dispatch (all relevant owners + conditional agents). **Short mode**: skips Step 4 entirely.

**Short Mode**: No agents — skip to Step 5.

**Early exit**: if NO changed file has extension `.go`, `.py`, `.js`, `.mjs`, `.cjs`, `.ts`, `.tsx`, or `.vue` AND none matches `CHANGELOG.md`, `go.mod`, `LICENSE*`, `README.md`, `Makefile`, `Makefile.*`, `pyproject.toml`, `package.json`, `tsconfig.json`, `k8s/**`, `agents/**`, `commands/**`, `skills/**`, `docs/**` — the diff cannot match any rule. Skip Step 4 entirely; note "Step 4 skipped: no rule-relevant files changed" in the report. One glance at the Step 0c diff stat decides this — no tool calls needed.

Changed files under a `node_modules/`, `dist/`, `build/`, or `coverage/` path segment do not count toward this check — they are generated or installed, and a committed bundle is often a single minified multi-megabyte line.

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

#### 4b: Findings-scoped candidate computation

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

- **DIFF** = the Step 0c diff (`git diff origin/<TARGET_BRANCH>...HEAD`)
- **CANDIDATES** = the Step 4b-i `<rule-id> <owner>` output
- **MECHANICAL_FINDINGS** = `/tmp/pr-review-findings.json`
- **Working directory** = `REVIEW_DIR`

On the guide's short-circuit condition the report line is `selector clean — no adjudication needed`. Skip this section for short/full mode.

Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.

#### Security mode (under `--security` only)

This subsection runs only when `SECURITY_REVIEW` is set (Step 0a). It activates the dormant `## Security Extension (dormant)` in `docs/selector-mode-guide.md` — when the signal is absent, Steps 4c-sel/4d-sel run byte-for-byte as the existing procedure above. It references the frozen pipeline guide (`docs/security/security-review-pipeline.md`), the selector-mode security extension, the verifier agent (`agents/security-verifier.md`), and the polymorphic validator (`scripts/validate-citations.sh`) by name — it does NOT re-implement or re-document the procedure. It runs in **every** mode (short, selector, full) and never bypasses or softens the existing Step 4.0 toolchain fail-fast (ast-grep/sg preflight → "Must Fix toolchain failure") or the Step 4a mechanical funnel — a `--security` review without the mechanical funnel would silently miss every MUST-tier finding.

1. **Recon and model derivation** — per `docs/security/security-review-pipeline.md` (the derivation contract is frozen there): enumerate entry points from the diff's touched packages (recall-oriented), resolve identities and auth mechanisms, resolve resources and their `authorization_functions`, and derive invariants as `resource → identifier → authorization_function` with `file:line` evidence. Write the model to `/tmp/security-model.json` (session-local, mirroring `/tmp/pr-review-findings.json`) and never to any path inside the reviewed repo — if the model is accidentally written in-tree, delete it and rewrite it to the session-local path. Apply the freshness gate (changed-evidence entries re-derived, unchanged carried forward; stale entries whose evidence no longer resolves are dropped and surfaced with the literal `model refresh:` line) and diff-relevant truncation on large repos (note the truncation in the report). Record the attack-surface inventory counts.
2. **Classifier trait groups** — per the dormant extension: exactly six groups `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. `authz` over-selection is non-negotiable: a diff touching a file cited as evidence by an entry point operating on a modeled resource, or cited as evidence by a modeled resource's `authorization_function`, MUST select `authz`. Deterministic invariant selection: a diff touching an invariant's `attack_surfaces` or its `evidence` source forces that `invariant_id` into the applicable set — no LLM judgment, never skipped. The HARD INVARIANT holds: the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
3. **Adjudicator inputs** — the Step 4d-sel adjudicator input gains the diff-relevant model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal. Each applicable invariant is judged against the diff slice with the single question: does this change preserve the invariant? Invariant-kind findings cite `invariant_id`.
4. **Verifier gate** — after adjudication, before emission, run the falsification gate per `agents/security-verifier.md` (7-item falsification checklist; verdict `confirmed | plausible | rejected` with `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, and `reject_reason` required on rejection). It is a hard pre-emission step for `severity=critical` and for `severity=major` when `confidence=confirmed`; every surviving high-severity finding carries a populated `counterevidence_checked`. The execution mechanism (in-session role vs sub-agent spawn) is an implementation detail the session decides, preserving the gate's hard pre-emission property. Residual false kills are caught by the `ai_review` post-post backstop (dismiss + COMMENT + human_review).
5. **Blocking derived, never stored as severity** — `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`; no per-surface config fields, no opt-out flags. A `plausible` critical does NOT block merge — it is reported as a required human review item.
6. **Diff anchoring** — in PR mode, report security findings ONLY on diff-changed lines or invariants whose attack surface the diff touched; whole-file context is permitted for reasoning, never for gating.
7. **Toolchain/deps pass (fail-closed)** — run a dependency scan over the reviewed repo (osv-scanner / trivy / govulncheck, whichever are available; govulncheck for Go modules), executed via the `coding:go-security-specialist` agent or in-session per the selector-mode zero-spawn property, and emit findings as `kind=toolchain` carrying `tool`, `package`, `version`, `advisory`, `file`, `line`. A scan failure, a database-fetch timeout, or a flagged vulnerability surfaces as a Must-Fix toolchain finding in the report — never a silent skip.
8. **Citation validation** — the Step 4d-sel citation-validation invocation passes `SECURITY_MODEL_FILE=/tmp/security-model.json` so invariant-kind findings resolve against the session model's `invariants[].id`. Each finding resolves exactly one provenance (`kind=rule` → `rule_id` in `rules/index.json`; `kind=invariant` → `invariant_id` in the model; `kind=toolchain` → no id). Absent an unset/missing/unreadable/unparseable model, invariant findings drop fail-closed (WARN to stderr) and are never kept — the validator enforces this; the command only supplies the model file.

#### Full mode: per-owner dispatch

**Full mode only** — skip this section in selector and short mode.

Compute the dispatch set from Step 4b-i and Step 4a findings:

```
owners_to_spawn = (keys of findings_by_owner) ∪ (owners from active judgment rules)
```

If `owners_to_spawn` is empty AND `findings_by_owner` is empty, report "funnel clean — no adjudication needed" and proceed to Step 5. ZERO LLM spawns.

Otherwise, spawn ONE Task per owner in `owners_to_spawn` **concurrently**. Each Task prompt:

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

**Full mode only** (selector mode's own citation call lives in the guide). Before consolidating in Step 5, walk every finding from the per-owner agent reports and verify its `rule_id` field exists in `rules/index.json`. Drop findings citing missing IDs — they're hallucinations or stale-walker references. Log dropped findings to stderr so the post-review smoke can detect drift.

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

**MANDATORY**: Every finding must be attributable. Write each finding as a list item that **begins** with a bold file reference, and append the rule tag when the finding comes from a rule:

```
- **`pkg/server/handler.go:42`** — ctx.Done() is never checked in this loop, so shutdown hangs. *(rule: `go-context/cancellation-check`)*
```

- The item's **first** bold run must **be** the file reference and nothing else — not a summary phrase, not a heading, not the issue's name. `- **Inconsistent due_date choice**` is wrong even though it is bold and first; `- **`task/x.yaml:24`** — inconsistent due_date choice` is right.
- Accepted shapes, and only these: ``**`path:LINE`**``, ``**`path`**`` (whole file), ``**`path:START-END`**``.
- A path mentioned later in the prose does not count. Never infer a path you did not see in the diff.
- Append ``*(rule: `<id>`)*`` verbatim when the finding maps to a rule id from `rules/index.json`; omit it when the finding is not rule-derived.
- A finding you cannot tie to a file is not reportable as a finding. Put general remarks under a separate `**Notes:**` block after the three sections, never as a bullet inside one.

This applies to every severity section and to all three modes.

#### Must Fix (Critical)
- Security vulnerabilities, context.Background() in business logic, concurrency bugs, data correctness, transaction deadlocks, business logic in factories, SRP violations (3+ concerns), outdated Go (2+ minor behind), missing test suites, manual mocks, direct time in tests

#### Should Fix (Important)
- Error handling, architectural violations, SRP (business+I/O), factory methods outside pkg/factory/, inline handlers, missing tests, missing docs, Go version issues, wrong test naming, wrong Counterfeiter config, missing license

#### Nice to Have (Optional)
- Style, code organization, Go patch updates, tool updates, naming conventions, copyright headers

#### Selector Mode: Classify Traceability (selector mode only)

Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.

#### Security Findings (under `--security` only)

When `SECURITY_REVIEW` is set, list every security finding (rule, invariant, and toolchain) with `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields (`confidence`, `exploitability`, `impact`, `counterevidence_checked`), and the derived blocking state.

#### Security Model (under `--security` only)

When `SECURITY_REVIEW` is set, record the provenance block: `derived_from` (repo, head, review_id), the entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. A scope containing Go source always produces this block (never a silent skip); a scope with no Go source — including when the Step 4 early-exit fires on a non-rule-relevant diff — states `no Go source — security model not derived` explicitly instead of omitting the section.

### Step 6: Next Steps Recommendation

If test coverage gaps found, suggest `/go-write-test` commands.

### Step 7: Manual Review (All Projects)

Focus on changed code only. After review, **clean up the worktree** (Step 0d).
