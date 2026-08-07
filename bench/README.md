# bench — code-review outcome benchmark

The missing tier of this repo's test pyramid:

| Tier | Location | Answers |
|---|---|---|
| Unit | `rule-tests/` | does this rule match what I meant? |
| Contract | `scripts/acceptance.sh` | does the dispatcher route correctly? |
| E2E | `scenarios/` | does the pipeline walk end to end? |
| **Outcome** | **`bench/`** | **does the rule set actually catch bugs?** |

A *configuration* is the tuple `(rules + commands content, model, effort level, review mode)`. Mode is not cosmetic — `short` / `full` / `selector` route through materially different code paths in `/coding:pr-review`, so a result row that did not distinguish mode would conflate two different instruments under one key. The bench scores a configuration against a curated set of expected findings, so a rule, model, effort, or mode change carries a measured before/after instead of shipping blind.

Goal: `[[PR Review Bench]]` in the Personal vault.

## Current state

The runner drives the real `/coding:pr-review` slash command over the pinned PR manifest (`bench/prs.json`) and writes one machine-readable row per PR. The golden set and scoring semantics belong to a later spec; `--golden` is recognised and rejected with exit code 2 rather than silently ignored.

## `prs.json`

Five already-merged PRs, deliberately **not** representative. They exist to build the runner against: language spread (Go ×2, TypeScript, Node, Python), size spread (3 → 783 lines), one known-clean PR, one with two documented defects, and both merge strategies.

Every entry records `base_sha` and `head_sha` explicitly because reconstructing a merged PR's diff requires knowing the merge strategy.

## Running it

```bash
make bench BENCH_ARGS="--model <model> --effort <effort> --mode <short|full|selector>"
make bench-test
```

`--model`, `--effort`, and `--mode` are mandatory: they are recorded as the configuration identity in every result row and have no safe default. Results land in `bench/results/results.jsonl`. `make bench-test` is also wired into `make precommit` so the unit tests gate every later change to the repo.

`python3 bench/run.py --print-config-hash` prints the content hash of `rules/` + `commands/` from the current `--coding-repo` and exits immediately.

**Exit codes:** 0 when every PR produced a row (ok or cache hit); 1 when one or more PRs failed; 2 for a usage, manifest, or preflight failure.

## Diff-range rule

The correct range depends on the merge strategy, **not** on a fallback from parent count:

- **merge-commit** (two or more parents): `<merge_sha>^1..<merge_sha>^2`
- **squash or rebase** (exactly one parent): the manifest's recorded `base_sha..head_sha`

The manifest's recorded `base_sha..head_sha` is the single authoritative source for single-parent commits. It is derived from the manifest and **never** reconstructed by walking the merge commit's parents.

> **Why the parent-derived form looked right on the fixture.** The only squash entry in `bench/prs.json` (`node-skeleton#2`) has `head_sha` equal to its `merge_sha`, so `git diff <merge_sha>^1..<merge_sha>` produced the correct diff by coincidence. A coincidence on one fixture entry is not a rule. Deriving head as "second parent, else the merge commit" yields `base == head` on any squash whose head is not the merge commit — an empty diff with no error, which scores as a clean review.

The runner aborts loudly on an empty diff (`EMPTY DIFF`) — a resolved range with zero changed files is never recorded as a zero-finding review and produces no row and no cache entry.

## Verifying an entry without cloning

```bash
gh api repos/<owner>/<repo>/compare/<base_sha>...<head_sha> --jq '.files | length'
```

All five entries were verified this way on 2026-08-06: 1 / 17 / 21 / 18 / 8 files.

## Fixed invariants

These are deliberately not configurable:

- **Review timeout:** 45 minutes per PR (`REVIEW_TIMEOUT_SECONDS = 45 * 60`)
- **Cache:** lives under `bench/.cache/` (gitignored — no benchmark output is ever committed)
- **Results:** live under `bench/results/` (gitignored)
- **Isolated config:** `$HOME/.claude-verify` with `DISABLE_AUTOUPDATER=1`; the runner aborts the whole run before the first review if that directory would resolve the `coding` plugin to content whose hash differs from `--coding-repo`'s

## Safety invariant

Every `git` invocation the runner issues targets a path under `bench/.cache/repos/`. The runner never touches a clone the operator uses for real work. `/coding:pr-review` itself holds `git worktree`, `git fetch`, `git branch`, and `rm -rf` permissions once invoked, so reusing a real clone could destructively mutate it.

## Result row

Each row in `bench/results/results.jsonl` records:

| Field | Description |
|---|---|
| `config_hash` | SHA-256 of the full configuration identity |
| `rules_commands_hash` | SHA-256 of all files in `rules/` and `commands/` |
| `model` | Model name passed to `/coding:pr-review` |
| `effort` | Effort level passed to `/coding:pr-review` |
| `mode` | Mode (`short`, `full`, or `selector`) |
| `prs_version` | Manifest version string |
| `pr_id` | PR identifier (e.g. `owner/repo#123`) |
| `base_sha` | Resolved base SHA |
| `head_sha` | Resolved head SHA |
| `diff_range` | The diff range string used (e.g. `abc123^1..abc123^2`) |
| `changed_files` | Number of files in the diff |
| `parent_count` | Number of parents on the merge commit (1 = squash/rebase) |
| `notes` | Strategy-label mismatch warnings, if any |
| `review_command` | The full `claude … /coding:pr-review …` argv |
| `started_at` | ISO-8601 timestamp when the review started |
| `duration_seconds` | Wall-clock seconds for this review |
| `findings` | Normalised list of `{path, line, rule_id, body}` |
| `raw_output_ref` | Path to the raw stdout file |
| `runner_version` | Runner version string |

Repeating a configuration is free: completed `(PR, configuration)` pairs are served from cache and invoke no review. The cache key includes the mode, so changing only `--mode` re-runs the review.
