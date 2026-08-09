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

The runner drives the real `/coding:pr-review` slash command over the pinned PR manifest (`bench/prs.json`) and writes one machine-readable row per PR. A scoring layer turns a ledger plus `bench/golden.json` into per-run precision and recall, and a committed report page per configuration. The scoring layer invokes no review, spends no tokens, and needs no network — it is a pure function over data already on disk.

Two entry points exist: `--golden` on a live run scores that run's configuration after the last PR completes; `--score` over an existing ledger scores every configuration in it. `--reports-dir` defaults to `bench/reports`.

## `prs.json`

Five already-merged PRs, deliberately **not** representative. They exist to build the runner against: language spread (Go ×2, TypeScript, Node, Python), size spread (3 → 783 lines), one known-clean PR, one with two documented defects, and both merge strategies.

Every entry records `base_sha` and `head_sha` explicitly because reconstructing a merged PR's diff requires knowing the merge strategy.

## Running it

```bash
make bench BENCH_ARGS="--model <model> --effort <effort> --mode <short|full|selector> --golden bench/golden.json"
make bench-test
python3 bench/run.py --score --golden bench/golden.json
```

`--model`, `--effort`, and `--mode` are mandatory for a live run: they are recorded as the configuration identity in every result row and have no safe default. Results land in `bench/results/results.jsonl`. `make bench-test` is also wired into `make precommit` so the unit tests gate every later change to the repo.

`python3 bench/run.py --print-config-hash` prints the content hash of `rules/` + `commands/` from the current `--coding-repo` and exits immediately.

`--golden <path>` scores the run after the last PR completes and requires `--model`, `--effort`, `--mode` to be supplied; the scored ledger is then available for the score-only mode. `--score` mode reads an existing ledger, scores every distinct `config_hash` in it, and writes one report page per configuration — it invokes no review and needs no model/effort/mode. `--reports-dir` defaults to `bench/reports`.

**Exit codes:** 0 when every PR produced a row (ok or cache hit); 1 when one or more PRs failed; 2 for a usage, manifest, preflight failure, missing or invalid golden set, empty or absent ledger, corrupt ledger line, or a live-run `prs_version` disagreement with the golden set.

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

The four ledger slices under `bench/testdata/` are verbatim extracts of real ledger rows, installed by the operator before approval. The slice `bench/testdata/ledger-baseline-opus-xhigh-full.jsonl` is the run the golden set was derived from; it produces a perfect self-match (42/42/0/0). No test may author a ledger row in place of any of these slices — five defects reached production because fixtures were written from the same template as the parser consuming them.

## Scoring

**Matching and the three golden states.** The match rule is exact and deterministic. For a `(golden entry, finding)` pair within the same `pr_id`: if both sides carry a non-null `rule_id`, they match when those ids are equal and do not match otherwise — a rule-id disagreement is decisive and no fallback is attempted. Otherwise they match when the `path` field is string-equal and **every** keyword in the entry's `signature` appears as a case-insensitive substring of the finding's `body`. Otherwise they do not match. `line` is never used for identity — it is display data only. Path comparison is whole-string equality with no extension requirement, so an extensionless path such as `Dockerfile` compares like any other.

Every golden entry carries one of three states, and the state governs what a hit or miss costs. An `accepted` entry — one the reviewer should produce — costs recall when unmatched and costs nothing when matched. A `rejected` entry — a known false positive — costs precision when matched and costs nothing when unmatched. An `unreviewed` entry — not yet adjudicated — is excluded from both numerator and denominator of both ratios, and a finding matching one is neither a penalty nor a candidate.

**Gap-triage candidates.** A finding matching no golden entry at all is a **gap-triage candidate**. It is quoted verbatim on the report page under its own heading, with its `pr_id`, `path`, `line` and `body`, and it is counted against nothing. It is **not a precision failure**. The golden set is bootstrapped from a single strong-model run, not hand-curated ground truth, and the reason this classification matters is load-bearing: when several independent configurations agree on a finding the baseline missed, that is evidence the golden set is incomplete and the entry is a candidate for promotion to `accepted`. When nothing ever reproduces a baseline finding, it is a candidate for demotion to `rejected`. The recorded case is `tts-mcp#20`, which was annotated "clean — correct answer is zero findings" on the strength of six zero-finding runs from a weaker model; the strong model then found a real, hand-verified defect in it.

**What precision currently measures.** `golden-dev-1` carries zero `rejected` entries, so precision cannot be lost by any configuration. A precision of `1.000` is a property of the golden set's adjudication state and is **not yet a result**.

**What recall currently measures.** 36 of the 42 signatures embed a line reference, so a re-report of the same issue at a different line does not match and surfaces as a gap-triage candidate rather than a hit. On this golden set, `recall` measures whether a configuration cited the same line, not whether it found the issue. Across the four runs of config `9ce66e05…` only 5 of 16 findings hit an entry, and the `apt-key` issue in `.github/workflows/ci.yml` is reported in all four runs at lines 13, 29, 9 and 27 and is a gap candidate every time.

**Runs are an occurrence index, never a timestamp cluster.** Within one `config_hash`, the k-th ledger row for a given `pr_id`, in ledger file order, belongs to run k. Run boundaries need no clock, no threshold, and no tuning, and they survive clock skew, a slow PR, and an operator pausing between PRs. The boundary between run 2 and run 3 of config `9ce66e05…` is 48 seconds while gaps *within* runs 1, 2 and 4 reach 140, 128 and 110 seconds — no time threshold separates them in either direction. A run that does not cover every PR in the manifest is labelled **partial** on the report page, and a partial run is scored over the PRs it actually covers: the missing PRs' golden entries are **out of scope for that run, not misses**, so a 3-PR run scores against 24 entries and a 1-PR run against 1.

**Rows recorded against another PR manifest.** Every ledger row whose own `prs_version` differs from the golden set's is skipped **before scoring**, named on stderr with the literal `PRS VERSION SKIP` together with its `config_hash` and both version strings. A configuration with no surviving rows gets **no page at all**. A configuration with some survivors gets a page whose Configuration block records how many rows were skipped. On the ledger as of 2026-08-09, 4 of the 66 rows carry `empty-diff-probe`, `mode-full-probe` or `ruleid-probe` and are skipped; they belong to 3 of the 7 configurations. Scoring produces no new ledger rows and mutates none that exist. A scorer change requires **no cache clear** — the config hash covers `rules/` + `commands/` but not `bench/run.py`, and scoring consumes already-normalised findings. The cache-clearing rule continues to apply to **harvest** changes alone.

**Report page.** Each scored configuration gets one page at `bench/reports/<config_hash>.md` — the full 64-character lowercase-hex hash, because a truncated filename reintroduces the identity ambiguity the hash exists to remove. The page is tracked in git and carries no generation timestamp, so re-scoring an unchanged ledger produces a byte-identical file. The page has four sections in order: **Configuration** (model, effort, mode, config_hash, rules_commands_hash, prs_version, coding version, golden version, runner_version, rows skipped, cost-not-recorded note, and both ratio caveats), **Runs** (one row per run with span, PR coverage, complete/partial label, golden entries in scope, findings, hits, misses, matched rejected, gap candidates, recall, precision, wall time), **Per-PR** (per run and PR: golden entries in scope, hits, misses, findings, gap candidates, duration), and **Gap-triage candidates** (every unmatched finding, quoted verbatim, under its own heading). Cost is not recorded because the ledger carries no cost field.

## Verifying an entry without cloning

```bash
gh api repos/<owner>/<repo>/compare/<base_sha>...<head_sha> --jq '.files | length'
```

All five entries were verified this way on 2026-08-06: 1 / 17 / 21 / 18 / 8 files.

### Ledger slices

| File | Contents | Lines | `sha256` |
|---|---|---|---|
| `bench/testdata/ledger-baseline-opus-xhigh-full.jsonl` | 5 rows — one complete run of the config the golden set was bootstrapped from | 5 | `af8f684b95e82577af4ac6b4a04392559ef04865ee95e7f8afdcc8f1756e86fb` |
| `bench/testdata/ledger-sonnet-medium-short-4runs.jsonl` | 20 rows — four complete runs of a weaker configuration | 20 | `f25b759a09d6fbedcf3f755977492324369ce19db40933fc77d17497d8596d02` |
| `bench/testdata/ledger-sonnet-medium-short-partial.jsonl` | 32 rows — eight runs of a third configuration, three of them partial and one covering a single PR | 32 | `165320f9edcd45bcbe3938685e0bc052c4adf56545c7317a87f5aff7945c24a7` |
| `bench/testdata/ledger-probe-configs-mixed-prs-version.jsonl` | 4 rows whose `prs_version` is not `dev-1` — three probe configurations run against different PR manifests | 4 | `f19cb4e9824f078b498a82c0ce2c55a884a28ca16ac0a33c9c3bd48dd478e209` |

## Fixed invariants

These are deliberately not configurable:

- **Review timeout:** 45 minutes per PR (`REVIEW_TIMEOUT_SECONDS = 45 * 60`)
- **Cache:** lives under `bench/.cache/` (gitignored — no benchmark output is ever committed; the two named exceptions are report pages under `bench/reports/` and the four frozen ledger slices under `bench/testdata/`)
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
- **Match rule:** `rule_id` exact when both sides carry one; otherwise `path` string equality plus every signature keyword present case-insensitively in body; `line` is never used for identity; path comparison is whole-string with no extension requirement
- **Golden states:** `accepted` (recall miss on no-match), `rejected` (precision penalty on match), `unreviewed` (excluded from both ratios); a finding matching no entry is a gap-triage candidate, **not a precision failure**
- **Run chunking:** per-PR occurrence index in ledger file order; the k-th row for a given `pr_id` belongs to run k; no clock, no threshold
- **Report location:** `bench/reports/<64-lowercase-hex>.md`; full hash, no truncation; tracked in git
- **Ratio rendering:** three decimals via `format(value, '.3f')`; `n/a` when denominator is zero; no `0.000` for a zero denominator
- **Report generation:** no timestamp written; re-scoring unchanged data yields byte-identical file
- **Precondition literals:** `GOLDEN SET NOT FOUND`, `INVALID GOLDEN SET`, `GOLDEN VERSION MISMATCH`, `PRS VERSION SKIP`, `EMPTY LEDGER`, `CORRUPT LEDGER`, `INVALID CONFIG HASH`

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
