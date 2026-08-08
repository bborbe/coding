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

## Authentication precondition

The benchmark calls the real `/coding:pr-review` command, which itself invokes the real `claude` binary. The `claude` binary must be able to authenticate — the runner does not set `ANTHROPIC_AUTH_TOKEN` and never will: any value of that variable switches Claude Code into API-key mode and bypasses the OAuth path entirely, for every operator, including those whose OAuth is already working. Setting it to save one `export` would silently change the authentication path of a measurement instrument.

A failed run leaves one artifact per failed `(PR, configuration)` pair under `bench/.cache/failures/`. Each artifact records both of the subprocess's output streams, each labelled with its stream name; an empty stream is marked explicitly rather than omitted.

> **Why the runner labels both streams.** Claude Code writes its real errors to stdout — an expired OAuth session, an unknown command — while stderr carries incidental warnings. An artifact that holds only stderr therefore systematically preserves the wrong half. The `bench-pr-20` failure on 2026-08-08 was diagnosed as a model-name warning until the stdout half was recovered.

## Plugin load path and start-up abort conditions

Before any PR is resolved, the runner checks that the isolated config directory (`$HOME/.claude-verify`) will load the `coding` plugin from the path its install record names — not from the marketplace directory, and not from a version inferred from directory names.

The check reads `<config dir>/plugins/installed_plugins.json`. That record's entry for the `coding` plugin names an `installPath` under `<config dir>/plugins/cache/`. That recorded path — the directory Claude Code really loads from — is what gets hashed and compared against `--coding-repo`. There is no fallback: a resolution that agrees with nothing produces a measurement that cannot be attributed, so the run aborts instead.

A passing check prints one line naming the resolved load path, the recorded version, and the content hash, so the claim can be cross-checked against the filesystem without reading the source.

Every condition below aborts the whole run before the first review starts, with a message naming what was found:

| Condition | What the operator does |
|---|---|
| no install record for the `coding` plugin in `installed_plugins.json` | install the plugin into the isolated config directory |
| the record cannot be read or parsed | repair or reinstall |
| the recorded install path is not on disk | reinstall, which rewrites the record |
| the recorded install path lies outside the config directory's own plugin tree | reinstall so the record names a path inside it |
| the record applies only to a different working directory | install at user scope |
| the resolved content hash differs from `--coding-repo` | reinstall or repoint the plugin |

## Two-ref guarantee

Before any review is invoked, the prepared working copy under `bench/.cache/repos/` contains exactly the checked-out head branch `bench-pr-<N>` plus the two synthetic remote-tracking refs `origin/bench-base-<N>` and `origin/bench-pr-<N>`, and nothing else. Every other branch, every other remote-tracking ref, every tag, and the default-branch symref are removed on every run — including against a cache directory an earlier version of the runner populated. The commits the manifest names stay reachable, so range resolution and the offline short-circuit still work on a repeat run.

> **Why this was necessary.** The `bench-pr-20` run on 2026-08-08 handed the reviewer a working copy that also carried `origin/main`, `origin/feature/streaming-playback`, and `origin/fix/lead-silence-startup-clipping`. The reviewer replied: "Target branch options: 1. `main` 2. `feature/streaming-playback` 3. `fix/lead-silence-startup-clipping` — Which should I use as the target for comparison?" The v0.35.2 sanity gate correctly rejected it as a non-review. An earlier run with identical inputs had reviewed correctly. Removing the alternatives removes the question; instructing the reviewer more firmly would leave the choice present and make determinism a property of the model's disposition.

## Diff-range rule

The correct range depends on the merge strategy, **not** on a fallback from parent count:

- **merge-commit** (two or more parents): `<merge_sha>^1..<merge_sha>^2`
- **squash or rebase** (exactly one parent): the manifest's recorded `base_sha..head_sha`

The manifest's recorded `base_sha..head_sha` is the single authoritative source for single-parent commits. It is derived from the manifest and **never** reconstructed by walking the merge commit's parents.

> **Why the parent-derived form looked right on the fixture.** The only squash entry in `bench/prs.json` (`node-skeleton#2`) has `head_sha` equal to its `merge_sha`, so `git diff <merge_sha>^1..<merge_sha>` produced the correct diff by coincidence. A coincidence on one fixture entry is not a rule. Deriving head as "second parent, else the merge commit" yields `base == head` on any squash whose head is not the merge commit — an empty diff with no error, which scores as a clean review.

The runner aborts loudly on an empty diff (`EMPTY DIFF`) — a resolved range with zero changed files is never recorded as a zero-finding review and produces no row and no cache entry.

## Reading review output

### The three required sections

`commands/pr-review.md` Step 5 marks **Must Fix**, **Should Fix** and **Nice to Have** as mandatory sections and mandates the literal `None.` when a section has no findings. A report is a review only when all three appear as markdown headings; output missing any of them is **rejected before the raw output is cached** and before it is harvested. A rejected PR leaves no ledger row and no cache entry, the remaining PRs still run, and the process exits non-zero — the same treatment an `EMPTY DIFF` gets, for the same reason.

The rejection names the PR, names each missing section on its own `missing sections: ` line, and carries a bounded verbatim excerpt on stderr.

> **Why the gate is necessary.** A subprocess that exits 0 after printing `Unknown command: /coding:pr-review` is otherwise indistinguishable from a genuinely clean review. A fabricated clean row is byte-for-byte identical to a real one.

### What ends a findings section

A findings section's content ends at the **next markdown heading of any level**, at a **thematic break**, at a **bold-run line outside a fenced code block** (`**` as the first non-whitespace content of a line), or at **end of input** — whichever comes first. Section names are matched as headings at any level; a mention in prose, in a bold run, or inside a fenced code block is not a heading. The terminating heading's level carries no information and is not used: level varies run to run inside a single mode, so relying on it would make boundary determination a property of the template rather than of the output.

The two bold-label shapes observed defeating the old boundary were `**Notes:**` and `**Summary**:` — housekeeping blocks appended after a clean review whose trailing bullets were then harvested as findings.

> **Why a bold label ends a section.** A review whose three severity sections all read `None.` — the correct answer, zero — was harvested as three findings, verbatim the three bullets of a trailing `**Notes:**` block. A bold label introduces a new block, and everything under it belongs to that block.

### What opens a finding

Both list styles open a finding: an **unordered item** (`-` or `*` followed by whitespace) and an **ordered/numbered item** (a run of digits followed by `.` and whitespace). Numbered items need not start at 1 and are not limited to one digit. Subsequent non-list lines extend the item already open. A line inside a fenced code block is ordinary text and opens nothing. Prose appearing in a section **before** the first list item — most importantly the mandated `None.` sentinel — contributes no finding and cannot be extended by anything that follows. Only the list marker is stripped from the body; the item's leading bold run survives intact.

> **Why numbered items matter most.** The reviewer writes its more severe tiers as numbered lists. A capture carrying five numbered Should Fix items harvested to two — the two Nice to Have bullets — so the parser lost precisely the findings that matter most, and left no trace of the loss.

### Where attribution comes from

`path` and `line` are read from the **bold run at the head of the item**, in the shapes the reviewer writes. A path or line appearing only in the item's trailing prose is not used when the leading bold run supplies one; no path is ever inferred by searching the repository and no line is guessed from surrounding text.

`rule_id` has **two sources, in strict priority order**:

1. The item's own inline `*(rule: \`<id>\`)*` marker. When present it always wins and is recorded as the literal string the reviewer wrote, **whether or not that id appears in `rules/index.json`**.
2. Only when no inline marker is present, a backticked token at the very head of the item that **is a member of `rules/index.json`**. This legacy shape is what three findings in `bench/testdata/sample-report.md` depend on. It stays index-gated: at the head of an item, an unknown backticked token is far more likely to be a file path or symbol than a rule name.

Under either source, an id named in the item's prose, in the item's tail, in a traceability table, or anywhere outside the item is never attributed to it.

The four observed bold-reference shapes and their resulting `path` and `line` values:

| Bold reference shape | `path` | `line` |
|---|---|---|
| `**bench/run.py:1037**` | `bench/run.py` | `1037` |
| `**README.md**` | `README.md` | `None` |
| `**src/server.go:42**` | `src/server.go` | `42` |
| `**pkg/config.ts:18-24**` | `pkg/config.ts` | `18` |

> **Why the inline marker is not validated against the rule index.** A tag naming a renamed rule, a rule added since the index was written, or a review run against a different rules revision would otherwise yield `null` — attribution would become a property of the runner's bookkeeping rather than of the reviewer's output. The instrument records what the reviewer claimed; reconciling that against the shipped rule set is the scorer's job, and coupling the two hides rule drift instead of surfacing it. The head-anchored legacy source keeps its index gate because it has no explicit marker to trust: there, membership is the only signal that a backticked token is a rule name at all.

### When a finding cannot be attributed

An item inside a severity section that yields neither a `path` nor a `rule_id` cannot be keyed, cannot be matched against a golden set, and is never written as a body-only finding. Such a PR fails with `UNATTRIBUTABLE FINDING` — in the same class as the existing `NOT A REVIEW` gate: no ledger row, no `<key>.json` row marker, the PR listed as failed, remaining PRs still processed, process exits non-zero.

The two gates differ in what they leave behind. `NOT A REVIEW` fires before the raw-output write and leaves nothing; `UNATTRIBUTABLE FINDING` fires after it, so the `<key>.stdout.txt` stays on disk and the review is re-harvestable after a parser fix without spending tokens again. A both-stream failure artifact is written under `bench/.cache/failures/`. There is no opt-out.

> **Why a body-only finding is refused.** A finding with no path and no rule id is an unmatchable measurement dressed as a data point. A false rejection costs one operator decision and a re-run; a false acceptance writes an unscoreable row into an append-only ledger.

### Fixtures

| Fixture | Origin | `sha256` | Harvests to |
|---|---|---|---|
| `bench/testdata/capture-notes-block-h2.md` | verbatim capture, `node-skeleton#2` short mode, `##` headings, all three sections `None.` with a trailing `**Notes:**` block | `6427028bef301ff822cca6dbf9308896f1899ac5a972ed3fddc276f2216552b9` | 0 findings, 0 unattributable |
| `bench/testdata/capture-numbered-findings-h3.md` | verbatim capture, `python-skeleton#3` full mode, `###` headings, five numbered Should Fix items with inline rule tags plus a positive-notes list | `5530049fa4d116dc5762b69c9c9498ff0865c0ae0c6b1de7b3ae4cc846643e93` | 5 findings, 2 unattributable |
| `bench/testdata/capture-traceability-h4.md` | verbatim capture, `node-skeleton#2` full mode, `####` headings, one bold-headed finding plus a 22-row traceability table | `2922746bb95bdb3a67a683942531362271d8f3ccd558067d910146e054bcfe7c` | 1 finding, 0 unattributable |
| `bench/testdata/capture-summary-trailer-h4.md` | verbatim capture, `github-pr-review-agent#11` short mode, `####` headings, all three sections `None.` with a `**Summary:**` trailer | `36e15eca61133033d81687f87a82b044333c6a7465508d1757f8493361137e79` | 0 findings, 0 unattributable |
| `bench/testdata/sample-report.md` | derived from the review command's Step 5 template, `####` headings | `de40c00e7d3c452fa7475be9fa6541426058a96dba91487460aa53be0bd186ae` | 3 findings |
| `bench/testdata/real-capture-report.md` | verbatim capture of live review output, `##` headings, all three sections `None.`, trailing prose | `be1400f065d6b856910e7ac91c7f4801598b57afb444f55cf2e257a43619f4db` | 0 findings |

Both defects this section documents survived 42 green unit tests because the tests were built from the same template the parser was built from. Every capture checked in before this change carried zero findings — no fixture had ever exercised the parser against a real finding, which is how this defect family reached five occurrences. A fixture for a new defect must be a **capture of real output**, not a transcription of the template.

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
- **Failure artifacts:** one file per failed `(PR, configuration)` pair under `bench/.cache/failures/`, each containing both subprocess streams labelled with their stream name; empty streams marked explicitly
- **Isolated config:** `$HOME/.claude-verify` with `DISABLE_AUTOUPDATER=1`; the runner aborts the whole run before the first review when the install record names a path whose content hash differs from `--coding-repo`'s, or when any of the abort conditions in the Plugin load path section applies
- **Plugin load path:** the runner hashes the directory named by the isolated config directory's `installed_plugins.json` record (the directory Claude Code really loads from), not the marketplace path; there is no fallback when the record is absent, unreadable, stale, out-of-tree, scope-mismatched, or hash-mismatched
- **Two-ref guarantee:** the prepared working copy carries exactly the checked-out head branch and the two synthetic remote-tracking refs for that PR; every other branch, tag and the default-branch symref are removed on every run
- **Required section names:** `Must Fix`, `Should Fix`, `Nice to Have` — all three mandatory in every review report; output missing any one is rejected before cache write
- **List-item markers:** both `-` and `*` unordered items and digit-run ordered items open a finding; prose before the first list item cannot form one; a list item inside a fenced code block opens nothing
- **Section terminators:** next heading of any level, thematic break, bold-run line outside a fence, end of input
- **Inline rule tag:** `*(rule: \`<id>\`)*` is read positionally from the item and recorded verbatim; it is **not** validated against `rules/index.json`; the head-anchored backtick fallback is **index-gated** (only used when no inline tag is present and the token is a known rule id)
- **Unattributable-item rejection:** `UNATTRIBUTABLE FINDING` fires when an item inside a severity section yields neither `path` nor `rule_id`; no ledger row, no row marker, no opt-out
- **Stderr excerpt bound:** at most 2,000 bytes of rejected output are printed to stderr (truncation is marked)

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
