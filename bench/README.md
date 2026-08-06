# bench — code-review outcome benchmark

The missing tier of this repo's test pyramid:

| Tier | Location | Answers |
|---|---|---|
| Unit | `rule-tests/` | does this rule match what I meant? |
| Contract | `scripts/acceptance.sh` | does the dispatcher route correctly? |
| E2E | `scenarios/` | does the pipeline walk end to end? |
| **Outcome** | **`bench/`** | **does the rule set actually catch bugs?** |

A *configuration* is the tuple `(rules + commands state, model, effort level)`. The bench scores a configuration against a curated set of expected findings, so a rule, model, or effort change carries a measured before/after instead of shipping blind.

Goal: `[[PR Review Bench]]` in the Personal vault.

## Current state

Only `prs.json` exists — the development fixture. The runner, golden set, and scoring are not built yet.

## `prs.json`

Five already-merged PRs, deliberately **not** representative. They exist to build the runner against: language spread (Go ×2, TypeScript, Node, Python), size spread (3 → 783 lines), one known-clean PR, one with two documented defects, and both merge strategies.

Every entry records `base_sha` and `head_sha` explicitly rather than a URL, because reconstructing a merged PR's diff is not obvious:

```bash
# merge-commit: two parents — ^1 is the base branch at merge time, ^2 is the PR head
git diff <merge_sha>^1..<merge_sha>^2

# squash: one parent — the squash commit IS the head
git diff <merge_sha>^1..<merge_sha>
```

**Branch on parent count, never on a fallback.** Deriving head as "second parent, else the merge commit" yields `base == head` on a squash and produces an **empty diff with no error** — which scores as a clean review. This was hit for real while selecting `node-skeleton#2`.

```python
parents = commit["parents"]
if len(parents) == 2:
    base, head = parents[0], parents[1]      # merge-commit
else:
    base, head = parents[0], merge_sha       # squash (or rebase)
```

The same failure family: `git diff <base_branch>...<pr_head>` on a merged PR also returns empty, because the head is now an ancestor of the base branch.

**Requirement for the runner:** fail loudly on an empty diff. Two independent code paths produce a silent no-op review, and both look identical to a genuinely clean PR.

## Verifying an entry without cloning

```bash
gh api repos/<owner>/<repo>/compare/<base_sha>...<head_sha> --jq '.files | length'
```

All five entries were verified this way on 2026-08-06: 1 / 17 / 21 / 18 / 8 files.
