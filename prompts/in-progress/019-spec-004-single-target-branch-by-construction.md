---
status: approved
spec: [004-bench-review-environment-control]
created: "2026-08-08T08:06:00Z"
queued: "2026-08-08T08:19:41Z"
---

<summary>
- The working copy the reviewer runs in now carries exactly one branch it could review and one branch to compare against — nothing else
- Every branch the upstream repository happened to have, every tag, and the pointer naming a default branch are removed before the review starts
- The reviewer can no longer ask which of several branches to compare against, because there is no longer more than one
- The removal happens on every run, so the caches every operator already has get the same treatment as a fresh one
- Running the same pull request twice leaves the working copy in the identical state and needs no network on the second pass
- The commits the frozen pull-request list names stay reachable, so repeated runs still resolve their comparison range offline
- Removing references is destructive, so every removal goes through the existing guard that refuses to touch anything outside the benchmark's own cache
- A guard test proves the removal refuses to run against a directory outside that cache
- The determinism comes from removing the choice, not from asking the reviewer more firmly — nothing the review reads is reworded
- The test suite grows; no existing test loses an assertion
</summary>

<objective>
Make the working copy handed to the review offer exactly one target branch by construction: after a PR is prepared, its repository holds only the checked-out head branch and the two synthetic remote-tracking refs the runner published for that PR — no upstream branches, no tags, no `refs/remotes/origin/HEAD` symref. This removes the observed non-determinism where the same inputs sometimes produced a review and sometimes a clarifying question ("Target branch options: 1. `main` … Which should I use as the target for comparison?"), because the alternatives the question enumerated no longer exist.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, never commit — dark-factory handles git).

Read `specs/in-progress/004-bench-review-environment-control.md`. This prompt implements **Desired Behavior 3** and **Acceptance Criteria AC8 and AC9**. Load-bearing sections:

- **Reference: observed evidence → D5** — the verbatim `git branch -a` output from the failing live run (`bench-pr-20`, `origin/HEAD -> origin/main`, `origin/bench-base-20`, `origin/bench-pr-20`, `origin/feature/streaming-playback`, `origin/fix/lead-silence-startup-clipping`, `origin/main`) and the reviewer's verbatim reply. An *earlier* run with identical inputs reviewed correctly — this is non-determinism, not a stable bug.
- **Failure Modes** rows: "Working clone still carries the upstream repository's branches (every operator's existing cache)"; "Manifest commits become unreachable after pruning" (must be impossible); "Process killed mid-prune, leaving a partially-pruned ref set" (the next run re-prunes to the same two synthetic refs before any review is invoked).
- **Security / Abuse Cases → "Destructive operation under a path guard"**: ref pruning deletes refs; every git invocation that performs it is subject to the existing safety invariant that the target repository lies under `bench/.cache/repos/`. The spec calls this "the highest-risk change in the spec and the one whose blast radius is bounded by an assertion rather than by care."
- **Do-Nothing Option → alternative (b)**: instructing the reviewer more firmly instead of pruning "leaves the choice present and makes determinism a property of the model's disposition". Do not implement this as prompt wording.
- **Assumptions**: "`git branch -a` in the prepared working copy is what the reviewer's own branch enumeration sees; refs kept outside `refs/heads/` and `refs/remotes/` are not offered as target-branch candidates."

Read `bench/run.py`. The parts you touch and the parts you must not:

- `git(args, *, repo_dir, cache_root, check=True, timeout=600)` — the single git subprocess chokepoint. It calls `assert_under(repo_dir, repos_root(cache_root))` **before** the subprocess, always uses `-C <target>`, never a shell string, and raises `BenchError` when `check` is true and the exit code is non-zero. **Every git invocation this prompt adds goes through this function.** Never call `subprocess.run(["git", ...])` from production code.
- `assert_under(path, root)` — resolves both paths and raises `BenchError` when `path` equals `root` or is not strictly under it.
- `repos_root(cache_root)`, `repo_cache_dir(cache_root, owner, repo)`, `worktree_dir(cache_root, owner, repo, number)` — the path helpers.
- `ensure_refs(cache_root, entry)` — creates the repo cache dir, `git init`s it when needed, then runs an **offline short-circuit**: it `git cat-file -e <sha>^{commit}`s each of `merge_sha`, `base_sha`, `head_sha` and returns without fetching when all three resolve. Only when one fails does it `git fetch --no-tags --force <url> +pull/<n>/head:refs/bench/pr<n>/head +refs/heads/*:refs/remotes/origin/*`. **That refspec is where the upstream branches come from.** Do not change `ensure_refs`.
- `prepare_worktree(cache_root, repo_dir, entry, base_endpoint, head_endpoint)` — resolves the two endpoints to SHAs, publishes `refs/remotes/origin/bench-base-<n>` and `refs/remotes/origin/bench-pr-<n>` with `git update-ref`, tears down any stale worktree, then `git worktree add --force -b bench-pr-<n> <wt> <head_sha>` and returns a `PrCheckout`. **This is where the new pruning is wired in.**
- `resolve_pr(cache_root, entry)` — `ensure_refs` → `resolve_diff_range` → `changed_files` → empty-diff gate → `prepare_worktree`. Unchanged by this prompt.
- `BenchError` — `main()` prints `str(err)` to stderr and exits 2, so asserting on the message is equivalent to asserting on stderr.

Read `bench/testsupport.py` for the temp-repo helpers this prompt builds on: `init_git_repo`, `commit_file`, `make_merge_repo` (returns `{"repo", "merge_sha", "base_sha", "head_sha"}` for a real two-parent merge), `seed_cached_repo`, `make_manifest`, `build_coding_repo`, `build_verify_config_dir`, `stub_claude`, `with_path`.

Read `bench/test_resolve.py` — this is where the new tests go and it is the established style for git-backed unit tests: build throwaway repositories under `<td>/cache/repos/<owner>/<repo>` with `tempfile.TemporaryDirectory()`, call the real `run.*` function, then inspect with a direct `subprocess.run(["git", "-C", …])` from the test. `TestWorktreeCreatedUnderReposRoot.test_worktree_under_repos_root_head_at_sha` is the closest existing shape: it calls `run.resolve_pr` and then asserts on `git rev-parse HEAD`, the checked-out branch name, and `refs/remotes/origin/bench-base-<n>`. `TestEveryGitStaysUnderCacheRepos.test_git_invocation_confined_to_cache_repos` is the existing safety-invariant test.

Read `scripts/build-index.py` for the repo's stdlib-Python precedent.

Read `docs/dod.md` — no personal paths, `## Unreleased` CHANGELOG entry (the CHANGELOG belongs to prompt 4 of this spec; do not touch it here).

**Verified git behaviour** (measured on git 2.55 against a throwaway repo built exactly like the tests build one — use these forms, they are load-bearing):

| Command | Observed |
|---|---|
| `git update-ref -d refs/heads/<name>` on the branch the repository has checked out | exits 0 and deletes it (unlike `git branch -D`, which refuses); the repository is left with an unborn HEAD, which is the same state `git init` leaves and which `git worktree add` still works from |
| `git update-ref -d <ref>` on a branch checked out in a *linked* worktree | exits 0 |
| `git update-ref -d <ref>` on a ref that does not exist | exits 0 — deletion is idempotent |
| `git update-ref -d refs/tags/<name>` | exits 0; `git tag` then prints nothing |
| `git symbolic-ref -d refs/remotes/origin/HEAD` when it is a symref | exits 0 |
| `git symbolic-ref -d refs/remotes/origin/HEAD` when it is absent | exits **128** — must be invoked with `check=False` |
| `git symbolic-ref refs/remotes/origin/HEAD` after deletion | exits 128 (this is what AC8 asserts) |
| `git for-each-ref --format=%(refname) refs/heads refs/remotes refs/tags` | lists heads, remote-tracking refs (including a `refs/remotes/origin/HEAD` symref) and tags, and lists **nothing** under `refs/bench/` |
| `git branch -a` | lists only `refs/heads/*` and `refs/remotes/*`; a ref under `refs/bench/` is never shown |
| `git cat-file -e <sha>^{commit}` after the deletions, with the sha held by a `refs/bench/…` ref | exits 0 |
</context>

<requirements>

## 1. Ref-name constants and helpers in `bench/run.py`

Add next to the existing module constants:

```python
# Ref pruning (frozen invariant — the prepared working copy offers one target branch)
KEEP_REF_NAMESPACE = "refs/bench/keep"
PRUNED_REF_NAMESPACES = ("refs/heads", "refs/remotes", "refs/tags")
DEFAULT_BRANCH_SYMREF = "refs/remotes/origin/HEAD"
```

Add pure helpers next to the existing path helpers:

```python
def keep_ref_name(number: int, label: str) -> str:
    """Full refname under KEEP_REF_NAMESPACE holding one manifest SHA for this PR.

    label is one of "merge", "base", "head".  These refs live outside refs/heads/
    and refs/remotes/, so they keep the manifest's commits reachable without
    appearing in `git branch -a` and without becoming a target-branch candidate.
    """


def synthetic_ref_names(number: int) -> tuple[str, str, str]:
    """The exact three refs a prepared working copy is allowed to carry.

    Returns (refs/heads/bench-pr-<n>, refs/remotes/origin/bench-base-<n>,
    refs/remotes/origin/bench-pr-<n>) — the checked-out head branch and the two
    synthetic remote-tracking refs prepare_worktree publishes.  The branch names
    must stay byte-identical to the f-strings prepare_worktree already builds
    (`bench-base-{number}`, `bench-pr-{number}`); derive them from one place so
    they cannot drift.
    """
```

## 2. `publish_keep_refs(cache_root, repo_dir, entry)`

```python
def publish_keep_refs(cache_root: pathlib.Path, repo_dir: pathlib.Path,
                      entry: dict) -> None:
    """Anchor the manifest's three SHAs under refs/bench/keep/<number>/ before pruning.

    Without these the merge commit becomes unreachable the moment the upstream
    branches are deleted, and a later git gc could discard it — which would break
    ensure_refs' offline short-circuit and force a network fetch on every run.
    """
```

- One `git update-ref <keep_ref_name(number, label)> <sha>` per label for `merge_sha`, `base_sha`, `head_sha`, through the `git()` chokepoint.
- Use `check=False`: a SHA a fetch never delivered must not turn a run that would otherwise work into a hard failure. The subsequent resolution steps already fail loudly on a genuinely missing commit.
- Called **before** pruning, never after — a process killed between the two steps must leave the commits reachable, not unreachable.

## 3. `prune_refs(cache_root, repo_dir, number)`

```python
def prune_refs(cache_root: pathlib.Path, repo_dir: pathlib.Path,
               number: int) -> list[str]:
    """Reduce repo_dir to exactly the three synthetic refs for this PR.

    Deletes every ref under refs/heads/, refs/remotes/ and refs/tags/ that is not
    one of synthetic_ref_names(number), and unsets the default-branch symref, so
    `git branch -a` in the prepared working copy enumerates exactly one head branch
    and two remote-tracking refs and the reviewer has no alternative target to ask
    about.  Returns the refnames deleted, sorted, for logging and assertions.

    Idempotent: a second call over an already-pruned repository deletes nothing and
    returns [].  Every git invocation goes through git(), so the destructive step
    inherits the safety invariant that repo_dir lies under bench/.cache/repos/.
    """
```

Sequence:

1. `git(["symbolic-ref", "-d", DEFAULT_BRANCH_SYMREF], repo_dir=..., cache_root=..., check=False)` — exits 128 when the symref is absent, which is the normal state on every run after the first.
2. Enumerate: `git(["for-each-ref", "--format=%(refname)", *PRUNED_REF_NAMESPACES], …)` and split `stdout` into non-empty lines.
3. For every enumerated refname not in `synthetic_ref_names(number)`: `git(["update-ref", "-d", refname], …, check=False)`. `check=False` because a ref can vanish between enumeration and deletion (a concurrent `git gc --auto`, a partially-pruned state from a killed process) and that is not a failure — the next run re-prunes to the same end state.
4. Return the sorted list of refnames it attempted to delete.

Do not delete anything outside `PRUNED_REF_NAMESPACES`. `refs/bench/pr<n>/head` (written by `ensure_refs`' fetch) and the keep refs from requirement 2 stay — they hold reachability and are not target-branch candidates.

Do not add a flag, an environment variable or a config field that skips pruning. Do not make the ref namespaces configurable.

## 4. Wire it into `prepare_worktree`

In `prepare_worktree`, after the existing `git(["worktree", "add", "--force", "-b", head_branch, str(wt), head_sha], …)` call and before the `return PrCheckout(...)`:

```python
    publish_keep_refs(cache_root, repo_dir, entry)
    prune_refs(cache_root, repo_dir, entry["number"])
```

That placement satisfies three requirements at once: pruning runs on **every** preparation (so an operator's pre-existing cache is pruned the first time the new runner touches it, not only a freshly created one); it runs **before any review subprocess is started**, because `resolve_pr` returns to `process_pr` which only then builds the argv and invokes the review; and the head branch already exists, so it is in the keep set rather than a casualty.

Nothing else in `prepare_worktree` changes: not the endpoint resolution, not the two `update-ref` publishes, not the stale-worktree teardown, not the `assert_under` calls, not the returned `PrCheckout`. Do not change `ensure_refs`, `resolve_diff_range`, `changed_files`, `resolve_pr`, `process_pr`, `run_bench`, `invoke_review`, `review_env`, the harvest functions, the non-review gate, or the CLI parser.

## 5. Test helper in `bench/testsupport.py`

Add one helper; do not modify any existing helper.

```python
def make_upstream_shaped_repo(path: pathlib.Path) -> dict:
    """Build a merge repo that also carries the refs a real upstream clone carries.

    Calls make_merge_repo(path), then adds, all pointing at the merge commit:
      refs/remotes/origin/main
      refs/remotes/origin/feature/streaming-playback
      refs/remotes/origin/fix/lead-silence-startup-clipping
      refs/remotes/origin/HEAD  (a symbolic ref to refs/remotes/origin/main)
      refs/heads/upstream-extra
      refs/tags/v1.0
    This reproduces the ref set observed in the failing live run recorded in
    spec 004 (Reference: observed evidence, D5).  Returns make_merge_repo's dict.
    """
```

Build the extra refs with direct `subprocess.run(["git", "-C", str(path), …])` calls the way `init_git_repo` and `commit_file` already do — `testsupport.py` is test scaffolding and does not go through the runner's chokepoint. Use `git update-ref <name> <sha>` for the five direct refs and `git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main` for the symref.

## 6. New tests in `bench/test_resolve.py`

Add a class `TestPreparedWorkingCopyOffersOneTargetBranch(unittest.TestCase)`. Every test builds throwaway repositories in a `tempfile.TemporaryDirectory()`, runs offline, and needs no network, no real `claude` binary and no GitHub access. Import `from unittest import mock` at the top of the file if it is not already imported.

Add a module-level helper in the test file (not in `testsupport.py`) that reads the prepared working copy the way the reviewer's own enumeration does:

```python
def observed_branches(worktree: pathlib.Path) -> list[str]:
    """Sorted `git branch -a` names with the checkout markers stripped.

    Strips the leading two characters git uses for the current-branch marker
    ("* ", "+ " or "  ") so the comparison is over ref names, not decoration.
    """
```

1. **`test_prepared_working_copy_offers_exactly_one_target_branch`** (AC8).
   Seed `<td>/cache/repos/testowner/testrepo` with `testsupport.make_upstream_shaped_repo`, build the manifest entry from its three SHAs with `number=42`, call `run.resolve_pr(cache_root, entry)`, then assert against the returned `checkout.worktree`:
   - `observed_branches(checkout.worktree)` equals exactly
     `["bench-pr-42", "remotes/origin/bench-base-42", "remotes/origin/bench-pr-42"]` — assert with the **full observed list interpolated into the assertion message**, which AC8 requires by name.
   - The checked-out branch is `bench-pr-42`: `git -C <worktree> rev-parse --abbrev-ref HEAD` prints it.
   - `git -C <worktree> symbolic-ref refs/remotes/origin/HEAD` exits **non-zero**.
   - `git -C <worktree> tag` prints nothing (empty after `strip()`).
   - The two upstream branch names from the observed live failure (`feature/streaming-playback`, `fix/lead-silence-startup-clipping`) and `main` do not appear anywhere in the `git branch -a` output.

2. **`test_ref_pruning_is_idempotent_and_keeps_manifest_commits_reachable`** (AC9).
   Same seeding. Call `run.resolve_pr` twice against the same `cache_root`. Assert:
   - `observed_branches(...)` after the second preparation equals the list from the first, and equals the three-name list above.
   - After both preparations, run `git -C <repo_dir> gc --prune=now --quiet` **before** asserting, then `git -C <repo_dir> cat-file -e <sha>^{commit}` exits 0 for each of the manifest's `merge_sha`, `base_sha` and `head_sha`. The `gc` is load-bearing: `cat-file -e` tests object *existence*, not reachability, so a loose object survives it even when no ref points at the commit. Without forcing a prune first, an implementation that dropped `publish_keep_refs` entirely would still pass this assertion — the very regression the keep-refs exist to prevent. `merge_sha` is the one at risk: it is not an ancestor of either synthetic ref, so once `origin/main` is deleted only a `refs/bench/keep/…` ref holds it.
   - The second preparation issues **no network fetch**. Prove it by recording every git invocation for the duration of the second call:
     ```python
     calls: list[list[str]] = []
     real_git = run.git

     def recording_git(args, **kwargs):
         calls.append(list(args))
         return real_git(args, **kwargs)

     with mock.patch.object(run, "git", recording_git):
         run.resolve_pr(cache_root, entry)
     ```
     Then assert no recorded invocation has `"fetch"` as its first element, with the full recorded call list in the assertion message. (A fetch would also fail outright — the manifest URL points at a repository that does not exist for `testowner` — so this assertion is the precise form of a failure that would otherwise surface as a confusing network error.)

3. **`test_prune_refs_refuses_a_repo_outside_the_cache`** (spec Security / Abuse Cases — "Destructive operation under a path guard").
   Build a real git repository at `<td>/outside-the-cache` (with `testsupport.init_git_repo` and one commit), then call `run.prune_refs(cache_root, td / "outside-the-cache", 1)` and assert it raises `run.BenchError` whose message names both the outside path and `str(run.repos_root(cache_root))`. Then assert the outside repository still has its branch — `git -C <outside> for-each-ref --format=%(refname) refs/heads` is non-empty — so the test proves nothing was deleted, not merely that an exception was raised.

4. **`test_prune_refs_is_a_no_op_on_an_already_pruned_repo`**.
   After one `run.resolve_pr`, call `run.prune_refs(cache_root, checkout.repo_dir, entry["number"])` directly and assert it returns `[]` and that `observed_branches` is unchanged. This is the "process killed mid-prune" recovery property from the spec's Failure Modes table stated as a unit test.

Do not delete, rename, weaken or relax any existing test in `bench/test_resolve.py`, `bench/test_config.py` or `bench/test_review.py`. The existing `test_worktree_under_repos_root_head_at_sha` asserts `refs/remotes/origin/bench-base-42` still resolves after `resolve_pr` — that ref is in the keep set and the assertion must keep passing untouched.

## 7. Config-dir calls in new tests

Any new test that needs an isolated config directory calls `testsupport.build_verify_config_dir(<dir>, plugin_src)` with **exactly two positional arguments** and no keyword arguments. Prompt 1 of this spec rewrites that helper's internals and removes its `use_known_marketplaces` parameter; the two-argument form is correct both before and after that change. Do not pass `use_known_marketplaces` in any code you add.

The tests in this prompt exercise `run.resolve_pr` and `run.prune_refs` directly and do not need `run_bench`, so most of them need no config directory at all.

## 8. Do not modify

`bench/prs.json`, `bench/testdata/`, `bench/README.md`, `CHANGELOG.md`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`.

`bench/README.md` and the CHANGELOG entry are prompt 4 of this spec. The plugin load-path preflight is prompt 1. The both-stream failure artifacts are prompt 3. Do not implement any of them here.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no third-party imports, no new top-level files outside `bench/`
- Changes land only in `bench/run.py`, `bench/testsupport.py` and `bench/test_resolve.py`
- The existing tests keep passing and their assertions are not weakened. Deleting a test, removing an assertion, or relaxing an assertion to accommodate pruning is not permitted. The suite's test count after this prompt is strictly greater than 55
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access — ref-pruning behaviour is proven against throwaway git repositories built in a temp directory, the way the existing parent-count tests already are
- **Every git invocation stays under `bench/.cache/repos/`.** The safety invariant from spec 002 is unchanged and the new pruning is subject to it: deleting refs is destructive, and a pruning step that could run against a path outside that prefix would be strictly worse than the defect it fixes. Every git call this prompt adds goes through the existing `git()` chokepoint, which runs `assert_under` before the subprocess. No `subprocess.run(["git", ...])` in production code
- Subprocesses are invoked with argument lists, never shell strings; no manifest value is interpolated into a shell command
- The commits the manifest names stay reachable after pruning, so range resolution and the offline short-circuit are unaffected and a second run over the same PR needs no fetch
- Pruning is idempotent and is applied on **every** run, including against a cache directory populated by an earlier version of the runner — which every operator already has
- Do NOT implement this as firmer wording in the prompt handed to the reviewer. No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`. The measured configuration stays fixed while the instrument is repaired
- Do NOT make any of this configurable: no flag, no environment variable, no config field for the ref namespaces, the branch names, or a skip-pruning escape hatch
- Do NOT add a field to the result row. Do NOT change the harvest contract or the non-review sanity gate shipped in v0.35.2
- Do NOT make `review_env()` supply an authentication token, and do NOT add environment scrubbing or an inherited-variable allowlist
- Frozen invariants: the isolated config directory `$HOME/.claude-verify`; the 45-minute review timeout; the cache, results and failure-artifact locations; the three required section names; the `--golden` exit-2 rejection
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file including test data (`docs/dod.md`)
- Do NOT re-harvest, migrate or re-validate anything already under `bench/.cache/` or `bench/results/`
- Do NOT add a scenario file — the spec's **Scenario coverage** section is explicit that ref pruning is assertable against throwaway git repositories
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# The pruning surface exists and is anchored on the chokepoint
grep -n 'def keep_ref_name\|def synthetic_ref_names\|def publish_keep_refs\|def prune_refs' bench/run.py
grep -n 'KEEP_REF_NAMESPACE\|PRUNED_REF_NAMESPACES\|DEFAULT_BRANCH_SYMREF' bench/run.py
grep -n 'publish_keep_refs\|prune_refs' bench/run.py | grep -n 'prepare_worktree' ; sed -n '/def prepare_worktree/,/^def resolve_pr/p' bench/run.py | grep -n 'publish_keep_refs\|prune_refs\|worktree add'

# No production git call bypasses the chokepoint
grep -n 'subprocess.run' bench/run.py
grep -n 'subprocess.run(\["git"' bench/run.py ; echo "raw-git grep exit=$?  (expect 1)"

# No escape hatch was invented
grep -niE 'skip_prune|no_prune|disable_prun|PRUNE_ENABLED' bench/run.py ; echo "escape-hatch grep exit=$?  (expect 1)"

# New tests present by name
grep -n 'def test_prepared_working_copy_offers_exactly_one_target_branch\|def test_ref_pruning_is_idempotent_and_keeps_manifest_commits_reachable\|def test_prune_refs_refuses_a_repo_outside_the_cache\|def test_prune_refs_is_a_no_op_on_an_already_pruned_repo' bench/test_resolve.py
grep -n 'def make_upstream_shaped_repo' bench/testsupport.py

# No call site passes the parameter prompt 1 removes
grep -rn 'use_known_marketplaces' bench/test_resolve.py ; echo "param grep exit=$?  (expect 1)"

# Full suite
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -40
python3 -m unittest discover -s bench -p 'test_*.py' 2>&1 | grep -E '^Ran |^OK|^FAILED'

# Nothing disappeared from the existing resolve suite
for t in test_parent_count_drives_merge_range test_single_parent_uses_manifest_base_not_parent_derived \
         test_mismatch_is_noted_not_obeyed test_empty_diff_raises_empty_diff_error \
         test_git_invocation_confined_to_cache_repos test_second_pr_runs_after_first_fails \
         test_worktree_under_repos_root_head_at_sha test_assert_under_rejects_absolute_outside \
         test_assert_under_rejects_root_itself test_fetch_url_exact_format; do
  grep -q "def $t" bench/test_resolve.py || echo "MISSING TEST: $t"
done

# The end state, exercised directly against a throwaway upstream-shaped repo
python3 -c "
import subprocess, sys, pathlib, tempfile; sys.path.insert(0, 'bench')
import run, testsupport
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    cache_root = td / 'cache'
    repo = cache_root / 'repos' / 'testowner' / 'testrepo'
    repo.mkdir(parents=True)
    info = testsupport.make_upstream_shaped_repo(repo)
    entry = {
        'id': 'test#42', 'owner': 'testowner', 'repo': 'testrepo', 'number': 42,
        'merge_strategy': 'merge-commit', 'merge_sha': info['merge_sha'],
        'base_sha': info['base_sha'], 'head_sha': info['head_sha'], 'changed_files': 1,
    }
    before = subprocess.run(['git','-C',str(repo),'branch','-a'], capture_output=True, text=True).stdout
    print('--- before ---'); print(before)
    checkout = run.resolve_pr(cache_root, entry)
    after = subprocess.run(['git','-C',str(checkout.worktree),'branch','-a'], capture_output=True, text=True).stdout
    print('--- after ---'); print(after)
    names = sorted(ln[2:] for ln in after.splitlines() if ln.strip())
    assert names == ['bench-pr-42','remotes/origin/bench-base-42','remotes/origin/bench-pr-42'], names
    sym = subprocess.run(['git','-C',str(checkout.worktree),'symbolic-ref','refs/remotes/origin/HEAD'], capture_output=True, text=True)
    assert sym.returncode != 0, sym
    tags = subprocess.run(['git','-C',str(repo),'tag'], capture_output=True, text=True).stdout.strip()
    assert tags == '', tags
    for f in ('merge_sha','base_sha','head_sha'):
        rc = subprocess.run(['git','-C',str(repo),'cat-file','-e', entry[f] + '^{commit}']).returncode
        assert rc == 0, f
    # idempotent: a second preparation lands on the identical ref set
    checkout2 = run.resolve_pr(cache_root, entry)
    after2 = subprocess.run(['git','-C',str(checkout2.worktree),'branch','-a'], capture_output=True, text=True).stdout
    assert sorted(ln[2:] for ln in after2.splitlines() if ln.strip()) == names
    assert run.prune_refs(cache_root, checkout2.repo_dir, 42) == []
    print('OK')
"

# The destructive step is under the path guard
python3 -c "
import sys, pathlib, tempfile; sys.path.insert(0, 'bench')
import run, testsupport
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    outside = testsupport.init_git_repo(td / 'outside-the-cache')
    testsupport.commit_file(outside, 'f.txt', 'c\n', 'f')
    try:
        run.prune_refs(td / 'cache', outside, 1)
    except run.BenchError as err:
        print('refused:', err)
    else:
        raise SystemExit('FAIL: prune_refs did not refuse a repo outside the cache')
    print('OK')
"

# No personal paths, stdlib-only imports
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_resolve.py

# CLI contract unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; the unittest run reports `OK` with `Ran N tests`, `N > 55`; the `MISSING TEST:` loop prints nothing; the raw-git and escape-hatch greps exit 1 with no output; the first inline Python prints a "before" list carrying `origin/main`, `origin/HEAD`, both upstream feature branches and `upstream-extra`, an "after" list of exactly three names, and `OK`; the second inline Python prints `refused: …` naming both paths and then `OK`; the personal-path grep exits 1 with no output; both `run.py` invocations exit 2.

Operator-executed after merge, in the spec-verification phase (real tokens, live review command, not runnable here): **AC18** — three consecutive runs over a one-PR manifest, deleting `bench/.cache/reviews/` and `bench/results/` before each, every run exiting 0 with `0 failed` and no raw output containing "which should I use" or "target branch options" — and **AC19**, `git branch -a` in a live prepared working copy printing exactly the three lines with `git symbolic-ref refs/remotes/origin/HEAD` exiting non-zero.
</verification>
