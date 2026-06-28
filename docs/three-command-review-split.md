# Three-Command Review Split — Design Note

**Status**: Draft (proposed shape; not yet implemented)
**Tracking PR**: this PR (docs-only — locks the shape before any command-file changes land)

## Problem

Today the plugin ships two review commands and **both review the diff** — different diff sources, but both delta-scoped:

| Command | Scope today |
|---|---|
| `/coding:pr-review` | `git diff origin/<target>...HEAD` — branch vs target (PR-shaped) |
| `/coding:code-review` | `git diff HEAD~1` — uncommitted / most-recent local change |

The name `code-review` implies "review the code" — operator-readable expectation is a whole-codebase audit, not a delta against HEAD~1. The current behavior is closer to a pre-commit local check. Two commands, two diff-scopes, one missing scope (whole codebase). Operators reaching for `/coding:code-review` to audit an inherited codebase or do a periodic health-check get a 1-commit diff instead.

## Proposed shape

Three commands, three distinct scopes; names match scopes:

| Command | Scope | What's at this scope | Status |
|---|---|---|---|
| `/coding:pr-review` | remote, branch diff vs target | the PR you're about to merge | **unchanged** |
| `/coding:local-review` | local, uncommitted / most-recent | what you just typed, pre-commit | **renamed from current `/coding:code-review`** |
| `/coding:code-review` | whole codebase | total health; baseline-aware | **new, built ground-up** |

### Why `local-review` over `changes-review`

The contrast pair `pr-review` (remote, against target branch on GitHub) / `local-review` (local, on this machine, pre-push) reads cleanly. Scope is in the name. `changes-review` is also valid but less crisp — `pr-review` is also "changes", just remote-scoped changes.

### Why `code-review` for the whole-codebase command

The operator's mental model when typing `/coding:code-review` is "review the code", not "review this 1-commit delta". Aligning behavior with name reduces "wait, which one does what?" confusion. The trade-off — existing users running `/coding:code-review` for pre-commit checks see behavior change — is mitigated by the deprecation stub (below).

## Critical mechanisms for whole-codebase review to be useful

A naive "run all rules against every file" implementation is **worse than nothing** on any non-trivial codebase: hundreds of pre-existing tech-debt findings drown the signal. Three mechanisms make it work:

### 1. Severity filter (default-on)

Default scope = **Must Fix + Should Fix only**. Nice-to-Have suppressed unless explicitly requested via flag. On a mature codebase, Nice-to-Have can dominate output; filtering it default-on keeps the report scannable. Flag: `/coding:code-review --include-optional` to opt in.

### 2. Rule-id dedup

When a single rule fires N times across the codebase (e.g., 47 `no-fmt-errorf` violations), the report shows **one entry per rule_id with a sample of 3-5 file:line locations + a total count**, not 47 separate findings. Dedup happens at the report-consolidation stage (Step 5).

Example:

```
### Should Fix

- **go-errors/no-fmt-errorf** — 47 occurrences. Replace `fmt.Errorf` with `errors.Wrapf` / `errors.Errorf` from `github.com/bborbe/errors`.
  Sample sites:
  - pkg/storage/base.go:144
  - pkg/ops/update.go:91
  - pkg/handler/foo.go:203
  - …and 44 more
```

### 3. Baseline file (`.code-review-baseline.yaml`)

The operator can commit a baseline that says **"these N pre-existing findings are accepted; only flag NEW ones."** This turns full-audit from "all tech debt" into "what's drifted since last sweep" — the actually useful mode.

Format (sketch):

```yaml
# .code-review-baseline.yaml — accepted pre-existing findings
# Regenerate with: /coding:code-review --refresh-baseline
generated_at: "2026-06-28T20:00:00Z"
generated_at_sha: a7ef2bd
accepted:
  go-errors/no-fmt-errorf:
    count: 47
    sample:
      - pkg/storage/base.go:144
      - pkg/ops/update.go:91
  go-time/no-time-now-direct:
    count: 12
    # …
```

Subsequent `/coding:code-review` runs compare the current finding set against `accepted`:
- **NEW** findings (rule_id × file:line not in baseline) → reported normally
- **CARRIED** findings (already in baseline) → suppressed; mentioned in traceability section as count
- **REMOVED** findings (in baseline but no longer present) → reported as "fixed since baseline" (positive signal)

### 4. golangci-lint passthrough (Go projects only)

For Go projects, run `golangci-lint run ./...` first and incorporate its findings into the mechanical-tier funnel. Avoids re-implementing what the toolchain already does well at the AST level. LLM adjudication then focuses on judgment-tier rules (architecture, layering, abstractions) where it adds real value.

## Migration plan

1. **PR 1 (this doc)** — design note merged. Locks the shape.
2. **PR 2** — rename existing `commands/code-review.md` → `commands/local-review.md`. Single-file move + grep-and-replace internal refs. Bot review approves quickly. Plugin version bump (e.g., 0.25.0 → 0.26.0 — minor bump signals renamed surface).
3. **PR 3** — deprecation stub: `commands/code-review.md` becomes a thin compatibility shim that prints "did you mean `/coding:local-review`? whole-codebase audit is moving to this name in v0.27.0." Plus opens an issue tracking the new behavior land date.
4. **PR 4** — implement the new whole-codebase `/coding:code-review`: severity filter, rule-id dedup, baseline-file logic. The largest PR; gets its own design review.
5. **PR 5** — flip the deprecation: `commands/code-review.md` now invokes the whole-codebase logic; deprecation message removed.

PRs 2 + 3 + 5 ship within a single minor version cycle so the deprecation window is short (operator sees the new name for ~1-2 releases, then the new behavior). PR 4 can sit between 3 and 5 without timing pressure.

## What this doc does NOT decide

- Exact CLI flag names beyond `--include-optional` and `--refresh-baseline` (defer to PR 4)
- Whether judgment rules need to be re-tagged with `applies_to: diff | codebase | both` (likely yes, but the inventory belongs in PR 4)
- How `golangci-lint` failure interacts with the report (block, warn, ignore?)
- Whether the baseline format should be shared with `golangci-lint`'s own `--new` flag mechanism (it does the same thing for its rules)

## Open questions

1. **Should `--refresh-baseline` require a clean working tree?** Generating a baseline from a tree with uncommitted work bakes accidental local cruft into the accepted set.
2. **Baseline file location** — repo root (`.code-review-baseline.yaml`) or hidden (`.claude/code-review-baseline.yaml`)? Repo root is more discoverable; hidden is less noise.
3. **Multi-project monorepos** — one baseline file or one per service? Monorepos with `subproject/` services may want per-project baselines to keep churn local.
4. **How does the audit interact with `.claude-ignore` / `.gitignore`** — should the auditor skip ignored files? Almost certainly yes (don't audit `node_modules/`, `vendor/`, generated code), but worth deciding the override mechanism.

## Related

- `commands/pr-review.md` — current diff-scoped reviewer for branch vs target
- `commands/code-review.md` — current diff-scoped reviewer for local changes (to be renamed to `local-review.md` per PR 2)
- `docs/selector-mode-guide.md` — adjudication mechanics; works either scope (file-set source–agnostic), no changes needed
- `scripts/ast-grep-runner.sh` — mechanical funnel; takes a file list, scope-agnostic
- `rules/index.json` — rule catalog; potentially needs `applies_to` tagging in PR 4
