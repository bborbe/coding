---
allowed-tools: Task, Bash(git ls-files:+), Bash(git status:+), Bash(git log:+), Bash(git branch:+)
argument-hint: "[short|full|selector] [directory] [--include-optional] [--refresh-baseline]"
description: Whole-codebase audit — severity-filtered + baseline-aware
---

## Context

- Current git status: `!git status`
- Current branch: `!git branch --show-current`
- Tracked file count: `!git ls-files | wc -l`

## Your task

Whole-codebase architectural + quality audit. **Different scope from `/coding:pr-review` and `/coding:local-review`** — see table:

| Command | Scope | Use when |
|---|---|---|
| `/coding:pr-review` | branch diff vs target | reviewing a PR before merge |
| `/coding:local-review` | uncommitted / `HEAD~1` diff | pre-commit local check |
| `/coding:code-review` (this) | **whole codebase** | onboarding, drift audit, periodic health-check |

Design rationale: see `docs/three-command-review-split.md`.

## Step 0: Parse Arguments

- First positional → mode (`short` / `full` / `selector` (default))
- Second positional → directory (default: current)
- `--include-optional` → include `Nice to Have` findings (default: filtered out)
- `--refresh-baseline` → write current finding set to `.code-review-baseline.yaml` and exit (no report)

Defaults are conservative — `selector` mode + Must Fix + Should Fix only — because whole-codebase output on a mature codebase is otherwise overwhelming.

## Step 1: Walk the codebase

Build the file-set the funnel processes:

```bash
cd <directory> && git ls-files | grep -E '\.(go|py|md|yaml|yml|sh)$' > /tmp/code-review-filelist.txt
```

Exclude vendor + node_modules:

```bash
grep -v -E '^(vendor/|node_modules/|\.git/)' /tmp/code-review-filelist.txt > /tmp/code-review-files.txt
mv /tmp/code-review-files.txt /tmp/code-review-filelist.txt
```

This is the **scope source** — every file the audit considers. Replaces the diff-based file list that `/coding:pr-review` and `/coding:local-review` use.

## Step 2: Project Detection + LICENSE check

Same as `/coding:pr-review` Step 2 + 3a — Go/Python detection drives which judgment rules trigger; LICENSE-presence is the conditional `license-assistant` gate.

Skip `make precommit` (Step 3b in pr-review) — full lint+test on a whole codebase is CI's job; running it here is wasteful.

## Step 3: Toolchain preflight (fail-fast)

Identical to `/coding:pr-review` Step 4.0 — verify `ast-grep` is available. Failure → "Must Fix toolchain failure" in report; skip Step 4.

## Step 4: Mechanical funnel — whole codebase

```bash
RUNNER="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh"
[ -x "$RUNNER" ] || RUNNER="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/marketplaces/coding/scripts/ast-grep-runner.sh"
[ -x "$RUNNER" ] || RUNNER="$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh"
"$RUNNER" <directory> $(cat /tmp/code-review-filelist.txt | tr '\n' ' ') > /tmp/code-review-findings.json
```

The runner is scope-agnostic — it processes whatever file list it receives. We pass the whole codebase.

## Step 5: Adjudication

Selector mode (default) follows `docs/selector-mode-guide.md` § Step 4c-sel CLASSIFY + Step 4d-sel ADJUDICATE — identical to `/coding:pr-review`'s Step 4, with one change:

- **`DIFF`** input → the full content of changed-or-relevant files (the guide is source-agnostic; pass concatenated file contents OR pass the file paths as context — the adjudicator reads what it needs).
- **`MECHANICAL_FINDINGS`** → `/tmp/code-review-findings.json` (whole-codebase output).
- **`CANDIDATES`** → judgment-tier rules whose `trigger` glob matches at least one file in the codebase (most rules will match).

Full mode → per-owner dispatch identical to `/coding:pr-review` Step 4b-ii, but the `<owner>` agents receive the whole-file-set scope.

Short mode → skip Step 5 entirely; report only the toolchain status + file count.

## Step 6: Baseline diff (the critical noise-reduction step)

Without this, whole-codebase output drowns the operator in pre-existing tech debt. Read `.code-review-baseline.yaml` from the directory root:

```bash
BASELINE="<directory>/.code-review-baseline.yaml"
[ -f "$BASELINE" ] && yq eval '.accepted' "$BASELINE" > /tmp/code-review-baseline.json 2>/dev/null || echo "{}" > /tmp/code-review-baseline.json
```

For each finding from Step 5:
- **CARRIED** — `(rule_id, file:line)` matches an `accepted` entry in the baseline → suppress from report, count in traceability section as "carried from baseline"
- **NEW** — finding not in baseline → report normally
- **FIXED-SINCE-BASELINE** — entry in baseline that has NO matching finding in current run → report as positive signal (line N's `no-fmt-errorf` was accepted, now gone)

Without a baseline file, every finding is NEW. First run on a mature codebase: huge report (this is the operator's signal to either fix the highest-value subset OR generate a baseline with `--refresh-baseline` and start tracking deltas).

## Step 7: Severity filter + dedup

**Severity filter** (default-on): suppress `Nice to Have` findings unless `--include-optional` flag was passed.

**Rule-id dedup**: group findings by `rule_id`. For each rule with ≥ 4 occurrences, emit ONE summary entry with the top 5 file:line citations + total count instead of N separate findings:

```
- **<rule-id>** — N occurrences across M files. <fix suggestion>
  Sample sites:
  - file1.go:42
  - file2.go:107
  - file3.go:18
  - …and (N−3) more
```

Rules with < 4 occurrences → list individually (no dedup benefit, more information loss than gain).

## Step 8: `--refresh-baseline` mode

If the flag was set: write the CURRENT finding set (post-Step 5, pre-Step 6) to `.code-review-baseline.yaml`:

```yaml
# .code-review-baseline.yaml — accepted pre-existing findings.
# Regenerate: /coding:code-review --refresh-baseline
generated_at: "<UTC ISO8601>"
generated_at_sha: "<git rev-parse HEAD>"
accepted:
  <rule_id>:
    count: <N>
    sample:
      - file1.go:42
      - file2.go:107
      - file3.go:18
```

Then exit — do NOT produce a report. The next normal `/coding:code-review` run will treat these as baseline and report only NEW findings.

**Constraint**: `--refresh-baseline` requires a clean working tree (`git status --porcelain` empty). Baking accidental local cruft into accepted findings is exactly the failure mode this guards against. Refuse with a clear error if dirty.

## Step 9: Consolidated Report

Three buckets (per `/coding:pr-review` Step 5):

#### Must Fix (Critical)
#### Should Fix (Important)
#### Nice to Have (Optional)
*(suppressed by default; pass `--include-optional` to include)*

#### Baseline traceability section

- **Baseline**: `<present | not present>` (`.code-review-baseline.yaml`)
- **Findings before baseline diff**: `<total count>`
- **Carried from baseline (suppressed)**: `<count>`
- **NEW (since baseline)**: `<count>`
- **FIXED since baseline (positive)**: `<count>`
- **Severity-filtered (Nice to Have suppressed)**: `<count>` (or "all severities shown" if `--include-optional`)

#### Selector mode traceability (selector mode only)

Per `docs/selector-mode-guide.md` § Traceability Report Section.

## Step 10: Next steps

- If `--refresh-baseline` was just set up: commit `.code-review-baseline.yaml` so subsequent runs know the starting point.
- If NEW findings dominate: suggest opening focused fix-PRs grouped by rule_id (one PR per rule = clear scope, easy review).
- If FIXED-SINCE-BASELINE > 0: suggest refreshing the baseline (`--refresh-baseline`) to lock in the improvement so it can't regress unnoticed.

## Constraints

- Scope is the **whole tracked codebase** as of HEAD — not the working tree, not the staged set. Use `git ls-files`.
- Vendored / generated files (vendor/, node_modules/, .git/) are always excluded.
- Read-only — never modify code. The only file write is `.code-review-baseline.yaml` under `--refresh-baseline`.
- All paths in findings are repo-relative (no absolute, no `~/`) — same convention as the other review commands.
