---
allowed-tools: Task, Bash(git ls-files:+), Bash(git status:+), Bash(git log:+), Bash(git branch:+)
argument-hint: "[short|full|selector] [directory] [--include-optional] [--refresh-baseline] [--security]"
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
- `--security` → set `SECURITY_REVIEW=1`, activating the dormant `## Security Extension (dormant)` in `docs/selector-mode-guide.md` over the reviewed scope. It is a position-independent boolean flag, independent of the mode token and the other flags (`--include-optional`, `--refresh-baseline`). When set, the security pipeline (Step 4 Security mode) runs in-session over the whole repo regardless of mode token — the existing short-mode "skip Step 5 entirely" directive applies only to the non-security adjudication. The flag is never silently ignored.

**`--refresh-baseline` × `--security`**: when `--refresh-baseline` is set, the command writes the current finding set to `.code-review-baseline.yaml` and exits WITHOUT a report (existing behavior, unchanged) — on such an invocation no security pipeline runs, because there is no review being performed; this is not a silent ignore of the flag, it is the maintenance-mode exit that produces no findings at all.

Defaults are conservative — `selector` mode + Must Fix + Should Fix only — because whole-codebase output on a mature codebase is otherwise overwhelming.

## Step 1: Walk the codebase

Build the file-set the funnel processes:

```bash
cd <directory> && git ls-files | grep -E '\.(go|py|js|mjs|cjs|ts|tsx|vue|md|yaml|yml|sh)$' > /tmp/code-review-filelist.txt
```

Exclude vendored, installed, and generated trees:

```bash
grep -v -E '(^|/)(vendor|node_modules|dist|build|coverage|\.git)/' /tmp/code-review-filelist.txt > /tmp/code-review-files.txt
mv /tmp/code-review-files.txt /tmp/code-review-filelist.txt
```

`dist/`, `build/`, and `coverage/` matter once JavaScript and TypeScript are in scope: a committed bundle is generated, minified, and often a single multi-megabyte line. Reviewing it produces findings nobody can act on and can exhaust the context window on one file. The pattern is anchored to a path segment rather than the line start, so a nested `frontend/app/dist/` is excluded too.

Then drop generated sources, which the path filter above cannot catch:

```bash
while IFS= read -r f; do
  head -25 "$f" | grep -q 'Code generated .* DO NOT EDIT' || echo "$f"
done < /tmp/code-review-filelist.txt > /tmp/code-review-files.txt
mv /tmp/code-review-files.txt /tmp/code-review-filelist.txt
```

Generated code lives in ordinary package directories — `k8s/client/`, `mocks/`, `zz_generated.deepcopy.go` — so no path pattern finds it. Its findings are unactionable by construction: the file says DO NOT EDIT, regeneration reverts any edit, and a genuine defect belongs upstream in the generator, not in this repo's review.

**Scan the first ~25 lines, not the first line.** Placement varies by generator: `counterfeiter` emits the marker on line 1, while `client-gen` emits a licence header first and the marker on line 4. A `head -3` check silently misses every client-gen file.

Measured on `bborbe/backup` (2026-08-10): 97 of 553 findings came from 25 client-gen files under `k8s/client/**` plus the `mocks/` tree, and **44+ of the 102 findings that reached adjudication were refuted for no reason other than being generated** — the largest single adjudication cost on that repo.

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

#### Security mode (under `--security` only)

This subsection runs only when `SECURITY_REVIEW` is set (Step 0). It activates the dormant `## Security Extension (dormant)` in `docs/selector-mode-guide.md` — when the signal is absent, the existing Steps 0–10 above run byte-for-byte as written. It references the frozen pipeline guide (`docs/security/security-review-pipeline.md`), the selector-mode security extension, the verifier agent (`agents/security-verifier.md`), and the polymorphic validator (`scripts/validate-citations.sh`) by name — it does NOT re-implement or re-document the procedure. In audit mode the scope is the whole repo — no diff anchoring — and the security pipeline runs in every mode (short, selector, full); it never bypasses or softens the existing Step 3 toolchain fail-fast (ast-grep/sg preflight → "Must Fix toolchain failure") or the Step 4 mechanical funnel.

1. **Scope and recon** — audit scope is the whole tracked codebase as of HEAD, so there is no diff anchoring: every security finding is in scope regardless of the baseline diff or the severity filter. Per `docs/security/security-review-pipeline.md` (the derivation contract is frozen there), enumerate entry points over the whole codebase (recall-oriented), resolve identities and auth mechanisms, resolve resources and their `authorization_functions`, and derive invariants as `resource → identifier → authorization_function` with `file:line` evidence. Write the model to `/tmp/security-model.json` (session-local, mirroring `/tmp/code-review-findings.json`) and never to any path inside the reviewed repo — if the model is accidentally written in-tree, delete it and rewrite it to the session-local path. Apply the freshness gate (changed-evidence entries re-derived, unchanged-evidence entries carried forward; stale entries whose evidence no longer resolves are dropped and surfaced with the literal `model refresh:` line) and note whole-repo truncation on large repos in the report. Record the attack-surface inventory counts.
2. **Classifier trait groups** — per the dormant extension: exactly six groups `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets`. `authz` over-selection is non-negotiable: a whole-repo file cited as evidence by an entry point operating on a modeled resource, or cited as evidence by a modeled resource's `authorization_function`, MUST select `authz`. Deterministic invariant selection: any invariant whose `attack_surfaces` or `evidence` source resolves in scope forces that `invariant_id` into the applicable set — no LLM judgment, never skipped. The HARD INVARIANT holds: the applicable set is a subset of the Step 5 candidate set (the whole-codebase judgment-rule candidates this command computes in Step 5); trait groups never add a rule the glob did not produce.
3. **Adjudicator inputs** — the Step 5 selector-mode adjudication (the same 4d-sel contract) gains the whole-repo model subset, the applicable invariants with their evidence authorization functions, and the attack-surface inventory as a drift signal. Each applicable invariant is judged with the single question: does the code preserve the invariant? Invariant-kind findings cite `invariant_id`.
4. **Verifier gate** — after adjudication, before emission, run the falsification gate per `agents/security-verifier.md` (7-item falsification checklist; verdict `confirmed | plausible | rejected` with `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, and `reject_reason` required on rejection). It is a hard pre-emission step for `severity=critical` and for `severity=major` when `confidence=confirmed`; every surviving high-severity finding carries a populated `counterevidence_checked`. The execution mechanism (in-session role vs sub-agent spawn) is an implementation detail the session decides, preserving the gate's hard pre-emission property. Residual false kills are caught by the `ai_review` post-post backstop (dismiss + COMMENT + human_review).
5. **Blocking derived, never stored as severity** — `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`; no per-surface config fields, no opt-out flags. A `plausible` critical does NOT block — it is reported as a required human review item.
6. **Toolchain/deps pass (fail-closed)** — run a dependency scan over the whole-repo dependency manifests (osv-scanner / trivy / govulncheck, whichever are available; govulncheck for Go modules), executed via the `coding:go-security-specialist` agent or in-session per the selector-mode zero-spawn property, and emit findings as `kind=toolchain` carrying `tool`, `package`, `version`, `advisory`, `file`, `line`. A scan failure, a database-fetch timeout, or a flagged vulnerability surfaces as a Must-Fix toolchain finding in the report — never a silent skip.
7. **Citation validation** — the Step 5 citation-validation invocation passes `SECURITY_MODEL_FILE=/tmp/security-model.json` so invariant-kind findings resolve against the session model's `invariants[].id`. Each finding resolves exactly one provenance (`kind=rule` → `rule_id` in `rules/index.json`; `kind=invariant` → `invariant_id` in the model; `kind=toolchain` → no id). Absent an unset/missing/unreadable/unparseable model, invariant findings drop fail-closed (WARN to stderr) and are never kept — the validator enforces this; the command only supplies the model file.

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

#### Security Findings (under `--security` only)

When `SECURITY_REVIEW` is set, list every security finding (rule, invariant, and toolchain) with `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields (`confidence`, `exploitability`, `impact`, `counterevidence_checked`), and the derived blocking state. **Render each finding's verdict fields as JSON** (`"confidence": "confirmed"`, `"exploitability": "high"`, `"impact": "high"`, `"counterevidence_checked": [...]`, `"blocking": true`) — the fields must be machine-greppable exactly as the scenarios assert. This section is a **baseline-independent whole-repo inventory** — it lists every security finding regardless of the Step 6 baseline diff and the Step 7 severity filter, which continue to govern only the normal severity buckets above (`--include-optional` does not suppress a security finding); derived blocking applies to every listed security finding. Security findings are NOT classified into the baseline's NEW/CARRIED/FIXED buckets.

#### Security Model (under `--security` only)

When `SECURITY_REVIEW` is set, record the provenance block: `derived_from` (repo, head, review_id), the entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. A whole-repo scope containing Go source always produces this block (never a silent skip); a scope with no Go source states `no Go source — security model not derived` explicitly instead of omitting the section.

## Step 10: Next steps

- If `--refresh-baseline` was just set up: commit `.code-review-baseline.yaml` so subsequent runs know the starting point.
- If NEW findings dominate: suggest opening focused fix-PRs grouped by rule_id (one PR per rule = clear scope, easy review).
- If FIXED-SINCE-BASELINE > 0: suggest refreshing the baseline (`--refresh-baseline`) to lock in the improvement so it can't regress unnoticed.

## Constraints

- Scope is the **whole tracked codebase** as of HEAD — not the working tree, not the staged set. Use `git ls-files`.
- Vendored / generated files (vendor/, node_modules/, .git/) are always excluded.
- Read-only — never modify code. The only file write is `.code-review-baseline.yaml` under `--refresh-baseline`.
- All paths in findings are repo-relative (no absolute, no `~/`) — same convention as the other review commands.
