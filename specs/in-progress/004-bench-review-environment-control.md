---
status: verifying
tags:
    - dark-factory
    - spec
approved: "2026-08-08T07:45:32Z"
generating: "2026-08-08T07:45:58Z"
prompted: "2026-08-08T07:56:15Z"
verifying: "2026-08-08T08:48:08Z"
branch: dark-factory/bench-review-environment-control
---

## Summary

- The bench runner decides what the review subprocess sees. Three live runs of `bench/run.py` proved it does not actually control that environment — and none of the three defects is reachable by the 55 unit tests, because every one of them stubs the `claude` binary.
- **The plugin-hash preflight verifies a directory nothing loads from.** It resolves the marketplace path while Claude Code loads from a per-version cache directory. On 2026-08-08 the preflight reported MATCH across a thirteen-minor-version gap. The one guard that exists to prove "the rules I am about to hash are the rules that will run" cannot detect the mismatch it exists for.
- **The runner does not control the branch set the reviewer sees.** The working clone retains the upstream repository's real branches plus a default-branch symref, so the reviewer is handed one target branch and offered three alternatives. One run reviewed; an identical earlier run asked a clarifying question instead. Same inputs, different behaviour.
- **Failure logs preserve stderr only, and Claude Code writes its real errors to stdout.** The preserved artifact from the failing run contained a harmless model-name warning while the actual cause — an expired OAuth session — was discarded. That caused a wrong root-cause diagnosis.
- The branch fix removes the choice rather than handling it: the clone the review sees carries only the two synthetic refs, so the clarifying question is unaskable. Determinism by construction, not by the model declining to second-guess.

## Problem

A benchmark exists to make two configurations comparable. That requires the instrument to control, and to be able to prove, what the measured subprocess actually saw — which rules it loaded, which branches it could choose between, and what it printed when it failed. The runner controls none of the three. It records a content hash taken from a directory the review never reads, so a result row can attribute findings to a rule set that did not run; that corrupts cross-configuration comparison specifically, which is the entire purpose of the benchmark. It hands the reviewer a target branch while leaving three plausible alternatives and a symref naming a different branch as canonical, so the same inputs sometimes produce a review and sometimes produce a question — a measurement instrument that is only sometimes a measurement instrument. And when a run fails, it throws away the stream the failure was actually written on, so the operator debugs the wrong thing. All three were found by running the thing; none was findable from inside the test suite, because the tests stub away exactly the boundary where all three live.

## Goal

The environment the review executes in is controlled by the runner and provable from its output. The preflight hashes the directory Claude Code will really load the plugin from, and any condition that would stop the plugin loading at all — no install record, a recorded install path that is not on disk, a record scoped to a different working directory — aborts the whole run by name before the first review starts. The working copy handed to the reviewer contains exactly two branches and no default-branch symref, so there is no alternative target to ask about and repeated runs over the same input produce reviews rather than questions. Every failed review leaves behind both of the subprocess's output streams, each labelled, so the preserved artifact names the real cause instead of the harmless one.

## Non-goals

- Do NOT build scoring, a golden set, or any precision/recall semantics. `--golden` stays reserved-and-rejected with exit 2, exactly as it is today.
- Do NOT change any rule, agent, command, or doc that participates in a review, including `commands/pr-review.md`. The measured configuration stays fixed while the instrument is repaired.
- Do NOT change the harvest contract or the non-review sanity gate shipped in v0.35.2 — this work adds a failure artifact to the gate's rejection path and changes nothing about what the gate accepts, what a section boundary is, or what opens a finding.
- Do NOT make `review_env()` supply an authentication token. Any value of `ANTHROPIC_AUTH_TOKEN` switches Claude Code into API-key mode and bypasses the OAuth path entirely — for every operator, including those whose OAuth works. Silently changing the authentication path of a measurement instrument to save one `export` is a worse trade than documenting the `export`. Desired Behavior 4 makes the OAuth failure self-diagnosing, which is the harm that was actually observed.
- Do NOT add environment scrubbing, an inherited-variable allowlist, or any other change to what the review subprocess inherits beyond the two variables set today. No observed defect names one.
- Do NOT add fields to the result row (a plugin version, a load path). The content hash already pins what ran; a second identifier for the same fact is an extra thing to keep consistent.
- Do NOT make the fixed invariants configurable: the cache and results locations, the failure-artifact location, the 45-minute review timeout, and the isolated config directory stay as they are. If a future consumer demands variation, that is a separate spec.
- Do NOT change `bench/prs.json` — schema, entries, and `dev-1` version are frozen inputs.
- Do NOT re-harvest, migrate, or re-validate raw outputs and ledger rows already written. Rows recorded before this change carry an unproven hash; the recovery is to delete the cache and re-run, which the README states.

## Desired Behavior

1. **The preflight hashes the directory the review will load from.** The plugin's load path is read from the install record the isolated config directory keeps for it, and that path is what gets hashed and compared against `--coding-repo`. The marketplace / `installLocation` path is never hashed and never used as a fallback: if the load path cannot be determined from the install record, the run aborts rather than falling back to a directory that agrees with nothing. Where several versions of the plugin are present on disk, the one named by the install record is the one hashed — never the newest, the highest-numbered, or the first one found. A resolved and matching preflight prints one line naming the resolved load path, the recorded version, and the hash, so the operator can cross-check the runner's claim against the filesystem without reading the code.

2. **Conditions that stop the plugin loading at all are named before the first review.** Three states were observed or are reachable on a real host, and each aborts the whole run — before any PR is resolved, before any review subprocess starts — with a message naming what was found: (a) the config directory holds no install record for the plugin; (b) the record names an install path that is not on disk (observed: a record pointing at a `0.16.0` directory that did not exist, which made every slash command unknown); (c) the record applies only to a working directory other than the one the review will be invoked from (observed: a project-scoped install pinned to a path the runner never runs in). Today each of these surfaces as an unexplained review failure many minutes later, or — for (a) and (b) — as a green preflight followed by reviews with no rules loaded. A record whose install path lies outside the isolated config directory's own plugin tree is refused for the same reason: the runner is turning file content into a filesystem path it will read.

3. **The reviewer is offered exactly one target branch, by construction.** Before a review is invoked, the working copy it will run in contains exactly the head branch checked out plus the two synthetic remote-tracking refs the runner published for that PR. Every other branch, every other remote-tracking ref, every tag, and the default-branch symref are gone. The upstream repository's real branches are what made the reviewer ask which target to compare against instead of reviewing; removing them removes the question rather than relying on the model to decline it, which is the only version of this that is deterministic. The commits the manifest names stay reachable so range resolution and the offline short-circuit are unaffected, and the pruning is applied on every run — including against a cache directory populated by an earlier version of the runner, which every operator already has.

4. **A failed review preserves both of the subprocess's output streams.** Timeout, non-zero exit, and rejection as a non-review all leave one artifact carrying the subprocess's stdout and its stderr, each under a label naming which stream it is, with an empty stream explicitly marked empty rather than omitted. Claude Code writes its real errors to stdout — an expired OAuth session, an unknown command — while stderr carries incidental warnings, so an artifact that holds only stderr systematically preserves the wrong half. Retry semantics are unchanged: a failed PR still produces no ledger row and no review cache entry, and is still retried naturally on the next invocation. The artifact is a diagnostic, not a cache entry.

5. **Authentication is an operator precondition, stated where the operator reads.** `bench/README.md` states which environment variable must be exported before a run, that the runner deliberately does not set it, and why — setting it would switch every run into API-key mode. The same document states the plugin load-path shape the preflight resolves and the three abort conditions from Desired Behavior 2, so an operator hitting one of them can act on the message without reading `bench/run.py`.

## Constraints

- **Language and dependencies:** Python 3 standard library only. Changes land in `bench/run.py`, `bench/test_*.py`, `bench/testsupport.py`, `bench/testdata/`, `bench/README.md`, and `CHANGELOG.md`. No packaging, no third-party imports, no new top-level files outside `bench/`.
- **The 55 existing tests keep passing, and their assertions are not weakened.** The shared test harness builds marketplace-shaped config directories, so it gains a load-path shape and most plugin-preflight tests are rewritten against it — that is expected. Deleting a test, removing an assertion, or relaxing an assertion to accommodate the new preflight is not. The only test functions that may disappear are the ones whose entire subject is marketplace-path resolution (names containing `marketplace` or `install_location`); each is replaced by a load-path equivalent asserting the same or stronger behaviour. The suite's test count after this work is strictly greater than 55.
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access. Ref-pruning behaviour is proven against throwaway git repositories built in a temp directory, the way the existing parent-count tests already are.
- **Every git invocation stays under `bench/.cache/repos/`** — the safety invariant from spec 002 is unchanged and the new pruning is subject to it. Deleting refs is a destructive operation; a pruning step that could run against a path outside that prefix would be strictly worse than the defect it fixes.
- **The failure artifact is a diagnostic, not a cache entry.** Writing it does not create a review cache entry, does not append a ledger row, and does not make a failed PR look cached on the next run. The v0.35.2 invariant that a rejected non-review leaves nothing under `bench/.cache/reviews/` holds unchanged.
- **Frozen invariants** (not configurable, not flagged): the isolated config directory `$HOME/.claude-verify`; the 45-minute review timeout; the cache, results, and failure-artifact locations; the three required section names and the `--golden` exit-2 rejection inherited from earlier specs.
- **Repo conventions that must not regress** (`docs/dod.md`): no personal paths (`/Users/`, `~/Documents/`) in any shipped file including test data and the README, and a `## Unreleased` CHANGELOG entry.
- **CHANGELOG entries use conventional prefixes** (`fix:` / `feat:` / `docs:`) per `docs/changelog-guide.md` — the non-conforming `bench:` style used in v0.35.1 is not repeated, because dark-factory's version-bump detector reads the prefix. **The entry describes the whole change, not the last prompt's slice:** spec 002 shipped a 1,075-line runner with no bullet describing it and drew a patch bump instead of a minor.

## Assumptions

- The isolated config directory records, per installed plugin, at least a scope, an install path, and a version; the observed record additionally carries a project path for project-scoped installs. The runner reads the recorded install path rather than reconstructing it from the `plugins/cache/<marketplace>/<plugin>/<version>/` naming convention, so a convention change surfaces as a changed record rather than as a silently wrong hash.
- A project-scoped install applies only when the review is invoked from the recorded project path. The runner treats a project-scoped record that does not match the review's working directory as not-loading and aborts. If that reading is stricter than Claude Code's actual behaviour, the cost is a loud abort naming the record, which the operator resolves by installing the plugin at user scope — fail-closed, and cheaper than a silent wrong measurement.
- `git branch -a` in the prepared working copy is what the reviewer's own branch enumeration sees; refs kept outside `refs/heads/` and `refs/remotes/` are not offered as target-branch candidates.
- A stub executable on `PATH` that writes chosen payloads to stdout and stderr and exits with a chosen code is sufficient to reproduce the failure-artifact defects; `bench/testsupport.py` already provides that harness. No live `claude` binary is needed for any container-verifiable criterion.
- The five fixture PRs stay merged, their recorded SHAs stay reachable, and `tts-mcp#20` remains the known-clean entry whose correct answer is zero findings.

## Failure Modes

| Trigger | Expected behavior | Recovery | Detection | Reversibility | Concurrency |
|---|---|---|---|---|---|
| Load path and `--coding-repo` hold different plugin content (the observed thirteen-version gap) | Whole run aborts before the first review; no PR is resolved, no subprocess starts | Operator reinstalls or repoints the plugin in the isolated config directory and re-runs | Non-zero exit; stderr carries the mismatch marker, the resolved load path, the recorded version, and both hashes | Fully reversible — nothing written | Nothing written, so no partial ledger |
| No install record for the plugin in the isolated config directory | Whole run aborts naming the record file and the plugin; the marketplace path is not used as a fallback | Operator installs the plugin into the isolated config directory and re-runs | Non-zero exit; stderr names the missing record, and does not name the marketplace path as a resolution | Fully reversible | Nothing written |
| Install record names a path that is not on disk (observed stale `0.16.0` entry) | Whole run aborts naming the recorded path and version | Operator reinstalls the plugin, which rewrites the record, and re-runs | Non-zero exit; stderr carries the stale-install marker plus the path and version it read | Fully reversible | Nothing written |
| Install record is project-scoped for a project path the review will not run in | Whole run aborts naming the record's scope, its project path, and the directory the review would have run in | Operator installs the plugin at user scope in the isolated config directory and re-runs | Non-zero exit; stderr names both paths | Fully reversible | Nothing written |
| Install record is unreadable or malformed | Whole run aborts naming the record file and the parse error; no fallback path is hashed | Operator repairs or reinstalls and re-runs | Non-zero exit; stderr names the file | Fully reversible | Nothing written |
| Working clone still carries the upstream repository's branches (every operator's existing cache) | They are removed before the review is invoked, on every run, not only on a freshly created cache | None needed | The prepared working copy enumerates exactly three refs | Irreversible for those refs by design — they are re-fetchable from the manifest and hold nothing the runner needs | Two PRs of the same repository are prepared sequentially; each preparation re-establishes the exact ref set for its own PR |
| Manifest commits become unreachable after pruning | Cannot occur: the commits the manifest names stay reachable, so range resolution and the offline short-circuit still work on the next run | None needed | A second run over the same PR resolves its range without re-fetching | n/a | n/a |
| Review subprocess exits non-zero after writing its real error to stdout (observed: expired OAuth session) | The PR fails; the preserved artifact carries both streams, labelled | Operator reads the artifact, fixes the named cause, re-runs — the uncached PR is retried | Summary lists the PR as failed; the artifact contains the stdout error text under a stdout label | Fully reversible — no row, no review cache entry | Rows and cache entries for other PRs untouched |
| Review subprocess exceeds the 45-minute timeout | Subprocess terminated; the artifact carries whatever both streams produced before termination, labelled, including the case where one of them is empty | Re-run; completed PRs are cache-served | Summary lists `failed: timeout`; the artifact exists and names both streams | Fully reversible | Partial cache from earlier PRs stays valid |
| Review subprocess exits 0 but prints a non-review (the v0.35.2 gate fires) | Unchanged rejection semantics — no ledger row, no review cache entry — plus an artifact carrying both streams so the full rejected output is recoverable after the bounded stderr excerpt scrolls away | Operator reads the artifact and re-runs | Non-zero exit; the gate's marker on stderr; the artifact present | Fully reversible | Append-only ledger unaffected |
| Failed subprocess produced megabytes of output | The artifact holds it; the bounded stderr excerpt printed by the v0.35.2 gate is unchanged and stays bounded | Operator deletes `bench/.cache/` | Artifact file size | Fully reversible | Disk growth is confined to the failures directory, which the README names as deletable |
| Two runners started against the same output directory | Unchanged: the second exits immediately without touching the ledger, cache, or failure artifacts | Operator waits and re-runs | Non-zero exit; stderr states a run is in progress | Fully reversible | Single-instance lock, unchanged from spec 002 |
| Process killed mid-prune, leaving a partially-pruned ref set | The clone is left in an indeterminate ref state; the next run re-prunes to the same two synthetic refs before any review is invoked, so no review ever observes the partial state | Re-run — pruning is idempotent and runs before invocation, so no manual cleanup is needed | The next run's own ref assertion; a partial state is indistinguishable from a fresh clone at that point | Fully reversible — the refs are reconstructed from the recorded SHAs, never from network state | Prune happens inside the per-PR path already serialized by the single-instance lock |

## Security / Abuse Cases

- **Attacker-controlled surface:** two files the runner reads and turns into filesystem paths (the isolated config directory's plugin install record, and the PR manifest), plus the third-party repository content that gets checked out and the review subprocess's own output.
- **File content becoming a read path:** the install record's install path is validated to lie under the isolated config directory's own plugin tree before anything is read or hashed from it. A record naming a path outside that tree is refused, so a tampered or corrupted record cannot redirect the preflight at arbitrary directories on the host.
- **Destructive operation under a path guard:** ref pruning deletes refs. Every git invocation that performs it is subject to the existing safety invariant that the target repository lies under `bench/.cache/repos/`, so no operator clone can be pruned. This is the highest-risk change in the spec and the one whose blast radius is bounded by an assertion rather than by care.
- **Command injection:** subprocesses continue to be invoked with argument lists, never shell strings; no manifest value, record value, or review-output value is interpolated into a shell command.
- **Secret leakage:** the failure artifact reproduces the subprocess's own two streams and nothing else — no environment variables, no tokens, no credential material is copied into it. Authentication material is never read, logged, or written by the runner; the README states the variable name only.
- **Fail-closed, not fail-open:** every ambiguity in plugin resolution aborts. A false abort costs one operator fix and a re-run; a false pass writes a hash that did not run into an append-only ledger, which is the failure this spec exists to prevent.

## Acceptance Criteria

Each AC is tagged **[container]** (verifiable at prompt time with no network, no tokens, and no real `claude` binary) or **[operator]** (only observable on the host, because it spends real tokens against the live review command). The convention follows specs 002 and 003 — whose operator criteria found all three of these defects while 55 container tests found none.

- [ ] **AC1 [container]** `make precommit` exits 0 and the bench suite grew — evidence: exit code 0; `python3 -m unittest discover -s bench -p 'test_*.py'` stderr contains `OK` and a `Ran N tests` line with `N > 55`.
- [ ] **AC2 [container]** The preflight hashes the load path, not the marketplace path, in **both** directions — evidence, two cases, each: process exit code as stated and the stub-`claude` counter file has 0 lines in the failing case.
  - Case A: config dir whose marketplace path holds content byte-identical to `--coding-repo` while the recorded load path holds one mutated byte → exit non-zero, stderr contains `PLUGIN RESOLUTION MISMATCH` and the load path.
  - Case B: the reverse — load path identical to `--coding-repo`, marketplace path mutated → the run proceeds past the preflight (stub-`claude` counter file has 1 line for a one-PR manifest).

  Case B exists because hashing both paths and requiring both to match passes Case A while breaking every legitimate host.
- [ ] **AC3 [container]** The version hashed is the one the record names, not the newest on disk: a config dir with two version directories holding different content, the record naming the lower version — evidence: with `--coding-repo` matching the lower version's content the run proceeds (counter file 1 line); with `--coding-repo` matching the higher version's content it exits non-zero and stderr names the lower version string. (Without this, globbing the cache directory and taking the maximum passes AC2.)
- [ ] **AC4 [container]** A record naming an install path that is not on disk aborts before any review — evidence: exit non-zero; stderr contains the stale-install marker literal, the recorded path, and the recorded version; stub-`claude` counter file has 0 lines; results file gains 0 lines.
- [ ] **AC5 [container]** Scope is evaluated, not merely mentioned, across **two** cases — evidence, both: stated exit code, and results file line count unchanged in the failing case.
  - Case A: the only record for the plugin is project-scoped with a project path that is not the directory the review runs in → exit non-zero; stderr names the record's project path and the review's working directory; stub-`claude` counter file has 0 lines.
  - Case B: the same file additionally carries a user-scoped record with a valid install path → the run proceeds (counter file 1 line for a one-PR manifest).

  Case B exists because aborting whenever a project-scoped record appears passes Case A.
- [ ] **AC6 [container]** No record, malformed record, and out-of-tree install path each abort with no fallback — evidence, three cases: exit non-zero each; stderr names the record file; stderr does **not** contain the substring `marketplaces` in any of the three (proving the marketplace path was not resolved as a fallback); stub-`claude` counter file has 0 lines in all three.
- [ ] **AC7 [container]** A passing preflight states what it resolved: a successful one-PR run's stdout contains exactly one line carrying all three of the resolved load path, the recorded version string, and the content hash — evidence: `grep -c` on captured stdout for a line matching all three returns 1.
- [ ] **AC8 [container]** The prepared working copy offers exactly one target branch: a unit test builds a throwaway git repository in a temp dir pre-populated with upstream-shaped refs (`refs/remotes/origin/main`, two `refs/remotes/origin/feature/*`, a `refs/remotes/origin/HEAD` symref, an extra `refs/heads/*`, and a tag), runs PR preparation, then inspects the prepared working copy — evidence: `git branch -a` output, sorted, equals exactly the three lines for the checked-out `bench-pr-<N>`, `remotes/origin/bench-base-<N>`, and `remotes/origin/bench-pr-<N>`; `git symbolic-ref refs/remotes/origin/HEAD` exits non-zero; `git tag` prints nothing; the assertion failure message prints the full observed ref list.
- [ ] **AC9 [container]** Pruning is idempotent and non-destructive to the objects the runner needs: preparing the same PR a second time in the same cache directory yields the identical three-line `git branch -a` output, and after both preparations `git cat-file -e <sha>^{commit}` exits 0 for the manifest's `merge_sha`, `base_sha`, and `head_sha` — evidence: exit codes; the second preparation issues no network fetch (a stub `git` log, or the absence of a fetch invocation, asserted the way spec 002's git-path test already logs invocations).
- [ ] **AC10 [container]** A non-zero-exit failure preserves both streams, labelled, across **two** cases — evidence, both: the artifact file exists under `bench/.cache/failures/`; `grep -c` for the stdout sentinel returns ≥1; `grep -c` for each of the two stream labels returns ≥1.
  - Case A: stub `claude` writes distinct sentinels to stdout and stderr and exits 3 → both sentinels present.
  - Case B: stub `claude` writes a stdout sentinel only, stderr empty, exits 3 → the stdout sentinel is present and the stderr section is present and explicitly marked empty.

  Case B exists because appending stdout after stderr with no labels, or omitting an empty stream, passes Case A.
- [ ] **AC11 [container]** The timeout path preserves both streams: a unit test drives the artifact writer with a timeout-shaped failure carrying both streams, including the mixed `bytes`/`str` combination the timeout exception actually produces — evidence: test exits 0; the assertion compares the artifact's full text against both sentinels and both labels; the test name contains `timeout`.
- [ ] **AC12 [container]** The non-review rejection preserves both streams without changing its own semantics: stub `claude` prints exactly `Unknown command: /coding:pr-review` to stdout plus a benign warning to stderr and exits 0 — evidence: exit non-zero; the artifact contains both sentinels and both labels; the results file gains 0 lines; `ls bench/.cache/reviews/` shows no new file for that (PR, configuration) pair; stdout summary reports `1 failed`.
- [ ] **AC13 [container]** No test was deleted to make the new preflight fit: `git diff origin/master -- bench/test_*.py | grep '^-.*def test_'` lists only test names containing `marketplace` or `install_location`, and at most three of them — evidence: the grep output inspected line by line; combined with AC1's `N > 55`.
- [ ] **AC14 [container]** The README states the operator preconditions and the abort conditions — evidence: `grep -c 'ANTHROPIC_AUTH_TOKEN' bench/README.md` returns ≥1; `grep -ciE 'API.key mode|does not set it' bench/README.md` returns ≥1; `grep -ciE 'installed_plugins|install record' bench/README.md` returns ≥1; `grep -ciE 'plugins/cache' bench/README.md` returns ≥1; `grep -ciE 'bench-base-|two synthetic' bench/README.md` returns ≥1.

  **Anti-keyword-stuffing**: the five patterns above must match on **at least four distinct line numbers** — evidence: the union of `grep -n` line numbers across the five patterns has ≥4 unique values. Additionally each of the three topics (authentication precondition, plugin load path + abort conditions, two-ref guarantee) must be its own prose block of ≥3 non-empty lines under its own heading. Without this, one keyword-dense line satisfies every grep while documenting nothing.
- [ ] **AC15 [container]** The runner still carries no personal paths and no third-party dependencies — evidence: `grep -rn '/Users/\|~/Documents/' bench/` returns 0 lines (exit 1); every `import` / `from` line in `bench/run.py` names a Python 3 standard-library module only.
- [ ] **AC16 [container]** The CHANGELOG entry uses conventional prefixes and describes all three defects — evidence: the section extracted from `## Unreleased` up to the next `## ` line is non-empty; every bullet line in it matches `^- (fix|feat|docs): `; `grep -c '^- bench: '` over that section returns 0; within it, `grep -ciE 'plugin|load path'` ≥1, `grep -ciE 'branch|ref'` ≥1, and `grep -ciE 'stdout'` ≥1.

  **Anti-keyword-stuffing**: the three topic patterns must match on **three distinct bullet lines**, and the section must contain **≥3 bullets** — evidence: the union of `grep -n` line numbers across the three topic patterns has exactly 3 unique values, and `grep -c '^- '` over the section returns ≥3. One bullet naming all three defects passes the loose form while under-describing the change, which is precisely the failure that drew a patch bump on v0.35.1.
- [ ] **AC17 [operator]** The path the preflight names is the path the host really loads from — evidence: the resolution line from AC7 in a real `make bench` run names a directory that exists; its version segment equals the `version` recorded for the `coding` plugin in `~/.claude-verify`'s install record; `diff -r <that directory>/rules <coding-repo>/rules` and the same for `commands/` both report no differences and exit 0.
- [ ] **AC18 [operator]** The reviewer never asks which branch to compare: three consecutive runs over a one-PR manifest, deleting `bench/.cache/reviews/` and `bench/results/` before each — evidence: each run exits 0 with a summary line reporting `0 failed`; `jq -s 'length' bench/results/results.jsonl` prints 1 after each; `grep -ciE 'which should I use|target branch options' <each raw output file>` prints 0 for all three. (Under the v0.35.2 gate a clarifying question is a rejected non-review, so `0 failed` three times in a row is the determinism evidence.)
- [ ] **AC19 [operator]** The live working copy carries exactly the two synthetic refs — evidence: after a run, `git branch -a` in the prepared working copy under `bench/.cache/repos/` prints exactly the three lines from AC8, and `git symbolic-ref refs/remotes/origin/HEAD` exits non-zero.
- [ ] **AC20 [operator]** A real failure names its real cause: the operator induces a genuine subprocess failure (for example by pointing the run at an isolated config directory with no valid credentials) — evidence: the run exits non-zero; the artifact under `bench/.cache/failures/` contains both stream labels and the underlying error text appears under the stdout label, not the stderr one.
- [ ] **AC21 [operator]** The full five-PR fixture is unregressed — evidence: after deleting `bench/.cache/reviews/` and `bench/results/`, `make bench BENCH_ARGS="--model <m> --effort <e> --mode <mode>"` exits 0; `jq -s 'length' bench/results/results.jsonl` prints 5; `jq -r 'select(.pr_id=="tts-mcp#20") | .findings | length'` prints 0; `jq -r .rules_commands_hash bench/results/results.jsonl | sort -u | wc -l` prints 1.

**Scenario coverage — NO new scenario.** Plugin resolution is a pure function over a temp-directory config tree, ref pruning is assertable against throwaway git repositories, and both failure-artifact paths are reachable with a stub executable — all three defect classes are unit-testable at the boundary the current tests stub away. The remaining evidence needs real tokens against a live review, which the scenario harness cannot supply either; AC17-AC21 are operator-executed after merge, exactly as specs 002 and 003 did.

## Verification

### Container-executable (runs inside the YOLO container at prompt time)

```
make precommit
python3 -m unittest discover -s bench -p 'test_*.py' -v
git diff origin/master -- bench/test_config.py bench/test_resolve.py bench/test_review.py | grep '^-.*def test_'
grep -rn '/Users/\|~/Documents/' bench/
grep -n 'ANTHROPIC_AUTH_TOKEN' bench/README.md
grep -niE 'installed_plugins|install record|plugins/cache' bench/README.md
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md
```

Expected: `make precommit` exits 0; the verbose unittest run reports `OK` with `Ran N tests`, `N > 55`, and shows the load-path resolution, stale-install, scope, ref-pruning, idempotence, and both failure-artifact tests by name; the deleted-test grep lists at most three names, all containing `marketplace` or `install_location`; the personal-path grep returns nothing (exit 1); both README greps return ≥1 line; the extracted Unreleased section contains only `fix:` / `feat:` / `docs:` bullets and names the plugin load path, the branch set, and the stdout preservation.

### Operator-executable (runs on the host, spends real tokens)

```
rm -rf bench/.cache/reviews bench/results
make bench BENCH_ARGS="--model <model> --effort <effort> --mode <mode>"
diff -r <resolved-load-path>/rules ./rules && diff -r <resolved-load-path>/commands ./commands
git -C bench/.cache/repos/<owner>/<repo>/<worktree> branch -a
git -C bench/.cache/repos/<owner>/<repo>/<worktree> symbolic-ref refs/remotes/origin/HEAD
jq -s 'length' bench/results/results.jsonl
jq -r 'select(.pr_id=="tts-mcp#20") | .findings | length' bench/results/results.jsonl
```

`<resolved-load-path>` is the directory named on the preflight's resolution line; `<owner>/<repo>/<worktree>` is a prepared working copy from the run. Neither is a personal path baked into this spec.

Expected: the run exits 0 and writes five rows; both `diff -r` invocations report no differences; `git branch -a` prints exactly three lines; the `symbolic-ref` lookup exits non-zero; `tts-mcp#20` reports 0 findings. The three-run determinism check of AC18 and the induced-failure check of AC20 are run separately.

## Reference: observed evidence

**D1, 2026-08-08.** The preflight reported MATCH while the marketplace path held `v0.35.1` (content hash prefix `05f95877…`) and the real load path held `v0.22.0` (`59a47cc8…`) — thirteen minor versions apart. Separately observed in the same install record: an entry pointing at a `…/cache/coding/coding/0.16.0` directory that was not present on disk, which made the plugin fail to load entirely and every slash command unknown; and a `scope: project` entry pinned to a project path the runner never invokes from.

**D5, same run.** `git branch -a` in the working copy handed to the reviewer:

```text
* bench-pr-20
  remotes/origin/HEAD -> origin/main
  remotes/origin/bench-base-20
  remotes/origin/bench-pr-20
  remotes/origin/feature/streaming-playback
  remotes/origin/fix/lead-silence-startup-clipping
  remotes/origin/main
```

The reviewer replied, verbatim: "**Target branch options:** 1. `main` — the default release branch 2. `feature/streaming-playback` 3. `fix/lead-silence-startup-clipping` — Which should I use as the target for comparison?" The v0.35.2 sanity gate correctly rejected it as a non-review. An earlier run with identical inputs reviewed correctly.

**D3, same run.** `bench/.cache/failures/*.stderr.txt` contained only a model-name warning. The actual cause — `Failed to authenticate: OAuth session expired and could not be refreshed` — was on stdout and discarded, and the run was misdiagnosed on the strength of the preserved half.

## Suggested Decomposition

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Plugin load-path resolution from the install record, the four abort conditions (no record, stale path, non-applicable scope, out-of-tree path), the resolution line on stdout, no marketplace fallback. Rebuild the config-dir test harness around the load-path shape and rewrite the marketplace-path tests against it. | 1, 2 | AC2, AC3, AC4, AC5, AC6, AC7, AC13 | — |
| 2 | Ref pruning in the prepared working copy: exactly the two synthetic refs plus the checked-out head branch, no default-branch symref, no tags, manifest commits still reachable, idempotent and applied to pre-existing caches, all under the existing cache-path safety guard. | 3 | AC8, AC9 | — |
| 3 | Both-stream failure artifacts for the timeout, non-zero-exit, and non-review-rejection paths, with stream labels and explicit empty-stream marking; v0.35.2 rejection semantics unchanged. | 4 | AC10, AC11, AC12 | — |
| 4 | `bench/README.md` sections for the authentication precondition, the load-path shape and abort conditions, and the two-ref guarantee; CHANGELOG `## Unreleased` entry with conventional prefixes covering all three defects; personal-path and stdlib-only sweep; full precommit. | 5 | AC1, AC14, AC15, AC16 | prompts 1-3 |

Rationale: prompts 1, 2 and 3 touch disjoint code paths (preflight, PR preparation, failure handling) and share no fixtures, so they carry no ordering dependency between them and can be worked in any order or in parallel. Prompt 1 is by far the largest because it rewrites the shared config-dir test harness that most existing tests build on; isolating that churn in one prompt keeps the other two reviewable. Prompt 4 is docs and packaging, deliberately last so the CHANGELOG bullets describe what all three actually shipped — the specific failure from spec 002, where the final prompt described only its own slice and the release classifier cut a patch instead of a minor. AC17-AC21 are operator-executed after merge in the spec-verification phase.

## Do-Nothing Option

Doing nothing leaves an instrument whose readings cannot be attributed. The hash on every row is unproven — the one guard that exists to prove it verifies a directory the review never reads, and it has already reported MATCH across a thirteen-version gap on a real host. Rows from different configurations therefore cannot be compared, which is the only thing the benchmark is for. Meanwhile the same inputs sometimes produce a review and sometimes a question, so even run-to-run repeatability of a single configuration is not established; the noise-floor and model-comparison work that everything downstream depends on cannot start on an instrument that is not repeatable. And each failure costs an unbounded debugging detour, because the preserved artifact reliably contains the wrong stream — that already happened once and produced a confident wrong diagnosis. The alternatives considered: (a) have the operator hand-verify the load path before every run — restores correctness for one careful operator and silently reverts the moment anyone forgets, which is what a preflight exists to prevent; (b) handle the branch ambiguity by instructing the reviewer more firmly rather than pruning refs — leaves the choice present and makes determinism a property of the model's disposition, exactly the failure being fixed; (c) fix only the plugin path and defer the rest — the hash would become trustworthy while the runs producing it stayed non-deterministic, so the numbers would be precisely attributed and still not comparable. All three defects came out of one live run, all three sit at the same boundary the test suite stubs away, and the benchmark is not usable as a measurement instrument until all three are closed.
