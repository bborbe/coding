---
status: verifying
approved: "2026-11-04T14:11:27Z"
generating: "2026-11-04T15:20:03Z"
prompted: "2026-11-04T15:42:48Z"
verifying: "2026-11-04T15:55:17Z"
branch: dark-factory/bug-review-scripts-argv-e2big
---

## Summary

- Two scripts build each finding by handing its text to a JSON tool as a command-line argument.
- The operating system refuses a single argument of 128 KiB or more, so the script aborts instead of reporting.
- The abort is silent: no findings are printed, so the consumer treats the whole mechanical pass as "did not run".
- One of the two scripts also passes its entire findings collection as a single argument, which an ordinary large PR reaches.
- Fix: no finding payload travels as a command-line argument, and emitted text is bounded with a visible marker.

## Problem

The runner is the reviewer's mechanical MUST-tier pass. When it dies, `github-pr-review-agent`'s `FunnelResult.Ran` is false and its fail-closed gate demotes every `approve` verdict to `CHANGES_REQUESTED` — the PR cannot merge on its own approval. Because the abort is silent (no JSON, no findings), the reviewer still produces a complete review, so the failure surfaces only as an unexplained blocked merge.

Two files carry the defect:

- `scripts/ast-grep-runner.sh` — each finding is assembled by passing its matched text and message as arguments to `jq -n --arg`.
- `scripts/rule-checks.sh` — the same construction in `emit_finding`, plus two aggregate sites: `--argjson f "$clean_finding"` per finding and `--argjson findings_by_owner "$FBO_JSON"` for the whole map. The aggregate path makes this reachable on an ordinary PR (200 findings × ~1 KB > 128 KiB), not only on exotic minified content. When it fires, the runner merges its output and silently drops every script-tier finding behind `append_error "rule-checks-error"`.

Reproduced in the deployed image `bborbe/github-pr-review-agent:v0.15.5` (jq 1.8.2, `coding@v0.51.0`) on 2026-11-04: a 131000-byte argument succeeds, while 131072 and 131073 bytes fail with `jq: Argument list too long`; under the script's own `set -euo pipefail` the run exits 126 with empty stdout.

## Goal

Both scripts complete and emit valid findings JSON regardless of how large any matched text or message is. A finding whose match is megabytes long is carried, bounded and visibly marked, rather than killing the run — and the emitted payload stays small enough that the consumer's review prompt remains a sane size.

## Non-goals

- `.reviewignore` handling — it lives in `commands/pr-review.md`, not in these scripts.
- Any change in `bborbe/github-pr-review-agent`. The consumer's `filterFindings` unmarshals into a fixed seven-field struct and re-marshals it, so a new JSON field would be stripped. That is why the truncation marker is carried **inside** the text rather than as a new field: it survives any consumer that passes the string through.
- Capping or validating the total number of findings; only per-field size is bounded.
- Changing what the rules detect, or the `.git/` path filters.
- Adding a configurable cap — the bounds are fixed values, not knobs.

## Assumptions

- The consumer re-marshals a fixed seven-field struct (`pkg/funnel.go` in `bborbe/github-pr-review-agent`), so a new JSON field would be dropped — this is why the truncation marker is an in-string suffix.
- The JSON tool supports `--slurpfile`/`--rawfile`, so a payload can be read from a file rather than an argument.
- `ast-grep` is already a `make precommit` prerequisite via `check-rule-tests`, so the fixtures can invoke the real scanner.
- Both scripts run under `set -euo pipefail`, so a failing command substitution aborts the whole run.

## Acceptance Criteria

- [ ] AC1: `ast-grep-runner.sh` emits a finding whose `matched_text` was 131072 bytes, bounded and marked. Note the fixture can only plant **source files**, not its own rule: the runner resolves rules from the repo's `rules/index.json`, not from the target dir. Feasible via an existing call-expression rule — `return fmt.Errorf("%s", "<131072 bytes>")` makes the whole call node the matched text. Evidence: a fixture plants a rule match over a node of exactly 131072 bytes; the test asserts `stats.findings_count >= 1`, the finding's `rule_id` equals the planted rule, `matched_text` is at most 8192 bytes plus the marker suffix, and `matched_text` ends with `[truncated, original 131072 bytes]`.
- [ ] AC2: `ast-grep-runner.sh` exits 0 on that same input, with findings present. Evidence: exit status 0 **and** `stats.findings_count >= 1`; the pre-fix behaviour is exit 126 with `findings_count` absent.
- [ ] AC3: `rule-checks.sh` survives an ordinary large run. Evidence: a fixture produces ≥ 200 findings **whose combined `findings_by_owner` JSON exceeds 131072 bytes** (the test asserts the byte size, not just the count — 200 small findings sum to ~50 KB and would pass against the unfixed script); the script exits 0 and emits `stats.findings_count >= 200`. The pre-fix behaviour on that same fixture is exit 126. This is the behavioral proof for the aggregate conversion — AC6's greps alone cannot distinguish a renamed variable from a fixed one.
- [ ] AC4: An ordinary small match is emitted byte-identically to pre-fix output. Evidence: a fixture scans a known small file and `diff`s the emitted finding against a capture produced at test time by running `git show origin/master:scripts/ast-grep-runner.sh` over the same fixture (deriving the golden at test time, not committing one, so a fabricated golden cannot pass); an untruncated `matched_text` carries no marker suffix.
- [ ] AC5: A `message` over 1024 bytes is bounded the same way. A rule message can interpolate metavariables (`$$$`) and therefore carry matched content, so it is reachable by the same path as `matched_text`, not only repo-authored text. Evidence: a fixture plants a rule whose message exceeds the bound; the test asserts `message` is at most 1024 bytes plus its marker and ends with `[truncated, original <N> bytes]`.
- [ ] AC6: No payload field is passed as a command-line argument, in either script. Evidence: two greps, both keyed on the **jq parameter name** rather than the shell variable (so renaming `$text` to `$t` cannot defeat them): `grep -nE -- '--arg(json)? (matched_text|message)' scripts/ast-grep-runner.sh scripts/rule-checks.sh` reports a count of 0, and `grep -n -- '--argjson findings_by_owner' scripts/rule-checks.sh` reports a count of 0. Both are non-zero on the current tree (2 in the runner, 4 in rule-checks), so the AC is meaningful today.
- [ ] AC7: The emitted finding keeps its existing key set and types — no new field. Evidence: the fixture asserts the object carries exactly `rule_id`, `rule_level`, `file`, `line`, `column`, `matched_text`, `message`, with `matched_text` and `message` as strings.
- [ ] AC8: The aggregate `--slurpfile` path and the `.git/` path filters are untouched. Evidence: `git diff` shows no change to the `--slurpfile` block in `ast-grep-runner.sh` and no change to either `.git/` case arm.
- [ ] AC9: The in-repo schema doc and the release convention are updated. Evidence: `grep -c 'truncated' agents/ast-grep-runner.md` returns ≥ 1 (the word does not occur today), and `awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- fix:'` returns ≥ 1.
- [ ] AC10: `make precommit` exits 0, and `shellcheck scripts/ast-grep-runner.sh scripts/rule-checks.sh` exits 0.

## Verification

### Container-executable (runs inside the YOLO container at prompt time)

- `make precommit` — the repo's full check chain exits 0
- `shellcheck scripts/ast-grep-runner.sh scripts/rule-checks.sh` — exits 0
- `bash scripts/ast-grep-runner.sh <fixture-dir>` over the 131072-byte fixture — exits 0 and prints JSON with `findings_count >= 1`
- `bash scripts/rule-checks.sh <fixture-dir>` over a ≥ 200-finding fixture — exits 0 and prints JSON with `findings_count >= 200`
- `grep -cE -- '--arg[a-z]* [A-Za-z_]+ "\$(matched_text|message|text|msg|clean_finding|FBO_JSON|findings_by_owner)"' scripts/ast-grep-runner.sh scripts/rule-checks.sh` — the reported count is 0 (the command exits 1 at zero matches; assert the count, not the exit status)

### Operator-executable (runs on the host after PR merge and release)

- `docker run --rm --entrypoint sh bborbe/github-pr-review-agent:<released-tag> -c 'set -euo pipefail; x=$(jq -n --arg m "$(head -c 131072 /dev/zero | tr "\0" a)" "{m:\$m}"); echo NOT_REACHED'` — still exits 126, proving the kernel limit is unchanged; the fix is that no code path feeds it
- `kubectlnukedev -n development-sandbox logs job/<reviewer-job> | grep 'ast-grep-runner exit='` — the newest reviewer Job logs `exit=0`
- `kubectlnukedev -n development-sandbox logs job/<reviewer-job> | grep -c 'rule-checks-error'` — 0

## Desired Behavior

1. Each finding is assembled without passing its `matched_text` or `message` as a command-line argument, in both scripts.
2. `rule-checks.sh` assembles its aggregate without passing the findings map or any individual finding as a command-line argument.
3. `matched_text` is emitted at most 8192 bytes, cut on a UTF-8 rune boundary; `message` at most 1024 bytes, cut the same way.
4. A field that was cut ends with a visible suffix naming the cut: `…[truncated, original <N> bytes]`, where `<N>` is the pre-cut byte length. The suffix is part of the string, so it survives any consumer that passes the string through.
5. A `matched_text` or `message` under its bound is emitted byte-identically to pre-fix output, with no suffix.
6. The scripts' exit status reflects only genuine tooling failure (missing `sg`/`ast-grep`, malformed rules), never payload size.
7. The emitted object keeps its existing key set and types; downstream `filterFindings` parses it unchanged.
8. The existing aggregate `--slurpfile` path in `ast-grep-runner.sh` and its two `.git/` path-filter arms are unchanged. (`rule-checks.sh` has no `.git/` filter — it emits a finding whose file is `$TARGET_DIR/.git/COMMIT_EDITMSG`; that behaviour is unchanged too.)
9. `agents/ast-grep-runner.md` documents the two bounds and the suffix, and `CHANGELOG.md` carries the change under `## Unreleased`.

## Reproduction

In the deployed image (`bborbe/github-pr-review-agent:v0.15.5`, which carries `coding@v0.51.0`):

```
docker run --rm --entrypoint sh bborbe/github-pr-review-agent:v0.15.5 -c '
  for n in 131000 131072 131073; do
    BIG=$(head -c $n /dev/zero | tr "\0" a)
    jq -n --arg m "$BIG" "{m:\$m}" >/dev/null 2>/tmp/e; echo "n=$n exit=$? err=$(head -1 /tmp/e)"
  done'
```

Observed:

```
n=131000 exit=0 err=
n=131072 exit=126 err=jq: Argument list too long
n=131073 exit=126 err=jq: Argument list too long
```

And the abort path, under the script's own `set -euo pipefail` (anchor on the content, not a line number — the directive sits at line 27 in `v0.51.0` and line 31 in the tree being edited):

```
docker run --rm --entrypoint sh bborbe/github-pr-review-agent:v0.15.5 -c '
  set -euo pipefail
  x=$(jq -n --arg m "$(head -c 131072 /dev/zero | tr "\0" a)" "{m:\$m}")
  echo NOT_REACHED'
```

Observed: exit 126, stdout empty, stderr `jq: Argument list too long` — `NOT_REACHED` never printed.

The `rule-checks.sh` aggregate path is reachable without any oversized text: 200 findings of ~1 KB each exceed the per-argument limit in the single `--argjson findings_by_owner "$FBO_JSON"` call.

## Expected vs Actual

**Expected** (`scripts/ast-grep-runner.sh` documents the aggregate surface at its `--slurpfile` comment: passing the whole payload through argv dies with "Argument list too long" past ARG_MAX, while `--slurpfile` makes the tool read the file itself, so payload size is irrelevant): the same reasoning applies to every payload — including one finding's text and rule-checks' aggregate.

**Actual:** the per-finding constructions were never converted in either script, and `rule-checks.sh` still routes its whole map through argv. One large match, or enough ordinary findings, kills the run.

## Workaround

Operators re-run the review on a PR with the offending file excluded, or read the review's judgment-only output and treat the missing mechanical pass as a manual step.

## Why this is a bug

The runner already names this exact failure class and fixes it at one surface. The remaining sites are the same defect at smaller and larger scopes, and both are reachable from ordinary PR content. The consumer's contract (`bborbe/github-pr-review-agent/pkg/funnel.go`) treats any non-zero exit as "funnel did not run" and fail-closes, so a silent abort becomes a blocked merge.

## Constraints

- The emitted JSON schema, key names and types do not change — `filterFindings` in `bborbe/github-pr-review-agent/pkg/funnel.go` parses it, and it re-marshals a fixed field set, so the truncation marker must live inside the string.
- The schema is documented in-repo at `agents/ast-grep-runner.md`; update that doc with the bounds and the suffix.
- Exit codes for genuine tooling failure keep their meaning (the consumer distinguishes exit 2 = ast-grep missing).
- `rule-checks.sh` keeps its documented "always exit 0" contract on non-fatal tooling problems.
- No new runtime dependency; the JSON tool and coreutils are already required.
- Both scripts must keep working under `set -euo pipefail`.
- `.reviewignore` handling is not in these scripts and is out of scope.

## Failure Modes

| Trigger | Expected behavior | Recovery |
|---|---|---|
| Match text is 100 MiB | Emitted cut to 8192 bytes with the suffix naming the original size; run exits 0 | None needed — the bound is the recovery |
| 500 findings in one rule-checks run | Aggregate assembled without argv; run exits 0 | AC3's 200-finding fixture fails in CI |
| A field exactly at its bound | Not truncated, no suffix | Boundary case asserted in the fixture |
| Truncation splits a multi-byte rune | Cut moves back to the previous rune boundary | Fixture includes a multi-byte character straddling the bound |
| The scratch space is unwritable | Script exits non-zero with a named error | Operator sees a real tooling failure rather than an empty result |
| Two matches in one scan stream | Both emitted; no interleaving corruption | `findings_count` equals the number of stream lines |

## Security / Abuse

A PR author controls file content, so an oversized match is a *deliberate* way to suppress the mechanical MUST-tier pass — and the `rule-checks.sh` aggregate silently drops every script-tier finding while the reviewer still emits a clean-looking review. That is an attacker-triggerable false green on a merge gate, not only an accidental crash.

| Trigger | Expected behavior | Recovery |
|---|---|---|
| Crafted ≥128 KiB content in a PR file | The mechanical pass completes and reports its findings; size cannot suppress it | None needed — the bound is the mitigation |
| Crafted content aimed at the prompt instead | The bound also caps how much PR-authored text reaches the review prompt | — |

## Suggested Decomposition

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Bounded, argv-free finding construction in `ast-grep-runner.sh` | 1, 3, 4, 5, 6, 7, 8 | 1, 2, 4, 5, 7 | — |
| 2 | Same in `rule-checks.sh`, including its aggregate | 2, 3, 4, 5, 6, 8 | 3, 6, 8 | prompt 1 (shares the helper and the bounds) |
| 3 | Doc + CHANGELOG for the bounds and the suffix | 9 | 9, 10 | prompts 1, 2 |

Rationale: prompt 2 reuses whatever construction prompt 1 introduces, so it lands second; the doc and changelog update describes the settled behavior. AC10 rides on all three. Every DB 1-9 is covered by a row.

## Do-Nothing Option

Leave it. The cost is concrete and recurring: every PR whose content trips the limit gets a `CHANGES_REQUESTED` it did not earn, blocking merge on its own approval, and every PR large enough to trip `rule-checks.sh`'s aggregate silently loses its entire script-tier findings set behind `append_error` — so the reviewer reports a cleaner diff than it actually examined. The first costs an operator interrupt and an admin-merge; the second is a false green on the mechanical gate, and a PR author can trigger it deliberately. Two focused script changes fix both.
