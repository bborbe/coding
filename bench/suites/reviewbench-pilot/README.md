# reviewbench-pilot — signature-viability pilot

A one-PR suite, converted by hand from [ReviewBench](https://github.com/review-bench/ReviewBench)'s golden format into this bench's schema. Its purpose is **not** to score a configuration. It exists to answer one question before the remaining 218 ReviewBench PRs are converted:

> Do keyword-substring signatures survive ReviewBench's finding density?

**Verdict: no. Do not convert the remaining 218 PRs with the current matcher.**

## The PR

`k1LoW/gh-copilot-review#9` — 68 changed lines, 2 files, in ReviewBench's 25-PR test set. Smallest Go PR in the corpus.

ReviewBench freezes `base`/`head` at capture time. The PR's live `refs/pull/9/head` has since moved to `395fb812…`, so `head_sha` here is the **frozen** commit, not the current PR head. Both frozen SHAs were verified reachable from upstream on 2026-10-07.

12 golden entries: 7 `tp` → `accepted`, 5 `fp` → `rejected`. Signatures are **hand-authored, not derived** — all 12 findings sit in two files and share vocabulary (`fetch` / `page` / `commits` / `reviews` / `freshness`), so derived keywords would cross-match, and measuring that risk is the point.

## Result

Run: `--model MiniMax-M3 --effort high --mode short`, `--coding-repo` pinned to the installed v0.38.0 baseline. 84s.

| metric | value |
|---|---|
| findings harvested | 4 |
| hits | **0** |
| misses | 7 |
| matched `rejected` | 0 |
| gap-triage candidates | 4 |
| recall | **0.000** |
| precision | n/a |

A recall of 0.000 reads like the reviewer found nothing. It didn't. The next section is why that reading is wrong, and it is the actual finding.

## The decisive evidence — paraphrase, not density

Each of the 4 harvested findings, scored against every golden entry by keyword coverage:

| finding | closest golden entry | coverage |
|---|---|---|
| `internal/github/github.go` (commits pagination) | #0 `accepted` `["first page","commits"]` | **1 of 2** |
| `internal/github/github.go` (reviews pagination) | #1 `accepted` `["first page","reviews"]` | **1 of 2** |
| `internal/github/github.go` (missing tests / doc comment) | — | no overlap |
| `cmd/root.go` (helper extraction) | — | no overlap |

Findings 1 and 2 are **correct detections of accepted golden entries #0 and #1**. Both were scored as misses because the reviewer wrote:

> "`GET /repos/{owner}/{repo}/pulls/{number}/commits` is **paginated** (default 30 per page, oldest first)"

The signature requires the literal phrase `first page`. The reviewer said `paginated`. The conjunction failed on a synonym while describing the same defect at the same lines.

So the real detection rate on this PR is roughly **2 of 7 accepted entries**, not 0 — and every one of those two was lost to wording, not to density.

Two further problems are visible in the same table:

- **Finding 2 is 1-of-2 against two different entries at once** (#0 and #1). Both accepted entries share the keyword `first page`, so a reviewer that wrote that phrase would match *both* — one detection double-counted as two hits.
- **The circular local check is worthless as a gate.** Matching each hand-authored signature against the 12 source messages gives 12/12 unique. That number was always going to be 12/12: the signatures were written from those messages. It measures mutual discriminability, nothing more. Only the live run was informative.

## Why this is a matcher problem, not a corpus problem

The bench's match rule is `all(keyword.lower() in finding_body.lower() for keyword in signature)` — a conjunction of literal substrings. It was designed for a 31-PR, 158-entry suite where the golden was bootstrapped from one strong-model run and most signatures carry two or three distinctive tokens.

At ReviewBench's scale the same rule meets text written independently, and a conjunction is unforgiving: one synonym anywhere in the signature and the whole entry is a miss. Density makes it worse — the more findings per PR, the more likely a shared token is doing the matching — but paraphrase alone is sufficient to break it, and this pilot is one PR with two losses from paraphrase alone.

## What would change the verdict

Before converting 218 more PRs, the matching key needs to stop depending on exact wording. In rough order of cost:

1. **Semantic matching** — what ReviewBench itself uses. Its judge is LLM-based precisely because substring matching does not hold at this scale. Costs an LLM call per (entry, finding) pair, and needs a provider key.
2. **`rule_id`-primary matching** — strongest where the reviewer cites a rule, but ReviewBench's entries carry no `rule_id` at all, so it cannot be the primary key against this corpus.
3. **Normalized-title or anchor matching** — hash a normalized form of the issue, or match on `(path, line-range)` overlap. Cheaper than (1), and `path`/`line` are already harvested; but the bench deliberately excludes them from identity today, because the same defect is legitimately anchored at different lines.

## Reproducing

```bash
make bench BENCH_ARGS="--suite reviewbench-pilot --coding-repo ../coding-v0380 \
  --model MiniMax-M3 --effort high --mode short"
```

`--coding-repo` is not optional: it must be pinned to the version installed in `~/.claude-verify` (currently v0.38.0, hash `ecc80333…`), or the runner aborts on preflight. See `[[Run the PR Review Bench]]`.

The scored report page is committed at `reports/<config_hash>.md`. The ledger and cache are not — see `.gitignore`.
