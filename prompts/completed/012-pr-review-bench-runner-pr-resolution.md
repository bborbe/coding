---
status: completed
spec: [002-pr-review-bench-runner]
summary: Extended bench/run.py with PR resolution (git chokepoint, ensure_refs, resolve_diff_range, changed_files, prepare_worktree, resolve_pr), path helpers, fetch_url; rewrote process_pr stub; added bench/test_resolve.py with 12 unit tests covering AC2/AC3/AC7/AC8; extended bench/testsupport.py with git-repo helpers
execution_id: coding-bench-runner-exec-012-pr-review-bench-runner-pr-resolution
dark-factory-version: v0.192.9
created: "2026-08-06T21:06:00Z"
queued: "2026-08-06T21:40:07Z"
started: "2026-08-06T21:45:57Z"
completed: "2026-08-06T22:08:44Z"
---

<summary>
- Teaches the benchmark runner to reconstruct each merged pull request's diff on its own, without any GitHub CLI
- All repository work happens inside the runner's private cache — the operator's real clones are never touched, opened or mutated
- Pull requests are fetched from the repository the manifest names, not from whatever remote happens to be called `origin` (one fixture PR lives on a fork, so an `origin` assumption fails outright)
- The diff range is chosen by counting the merge commit's actual parents, so a squashed pull request is never silently reduced to an empty diff
- A resolved range that touches zero files aborts that pull request loudly instead of being recorded as a clean review
- A failing pull request is isolated: the remaining ones still run, and the overall run reports failure
- Re-runs are offline-friendly: if the needed commits are already in the cache, no network fetch is attempted
- Review invocation itself still reports a loud "not yet implemented" failure — it lands in the next prompt
</summary>

<objective>
Extend `bench/run.py` so it resolves each manifest pull request into a checked-out working copy and a correct diff range, entirely inside `bench/.cache/repos/`. Diff-range selection branches on the merge commit's actual parent count; an empty diff aborts that PR loudly; every `git` invocation is structurally confined to the runner's own cache. Review invocation remains a loud stub.
</objective>

<context>
Read `CLAUDE.md` for project conventions.
Read `specs/in-progress/002-pr-review-bench-runner.md` — this prompt implements Desired Behaviors 4, 5 and 6 and Acceptance Criteria AC2, AC3, AC7, AC8.
Read `bench/run.py` (created by prompt 1) — you are extending it. Reuse `BenchError`, `load_manifest`, `safe_pr_key`, `run_bench` and the `process_pr` stub; do not restructure them.
Read `bench/testsupport.py` (created by prompt 1) — you are extending it with git-repo and stub-`git` helpers.
Read `bench/prs.json` — note `node-skeleton#2` is the only `squash` entry and its `head_sha` equals its `merge_sha`; the other four are `merge-commit`.
Read `bench/README.md` — its current squash snippet is superseded by the spec (see the Constraints section of the spec: *"This spec is the binding contract for diff-range mechanics, superseding `bench/README.md` where the two disagree"*). Prompt 4 rewrites the README; this prompt implements the spec's rule, not the README's.
Read `commands/pr-review.md` Step 0a-pre through Step 0c — this is the consumer of the working copy you are preparing. Step 0c resolves the diff as `git diff origin/<TARGET_BRANCH>...HEAD`, which resolves through the ref namespace and is why the runner must create `refs/remotes/origin/<branch>` refs locally.

Known and accepted: Step 0a-pre's fast-path short-circuit begins with `git fetch origin <SOURCE_BRANCH>`, which needs an actual `[remote "origin"]` config entry. `ensure_refs` fetches from an anonymous manifest-derived URL and never creates one, so that fetch fails and the short-circuit does not fire — execution falls through to Step 0b, which creates its own `/tmp` worktree. That is slower but still correct, because the refs Step 0b and 0c need already exist locally. **Do not "fix" this by adding a `git remote add origin …`**: the fixture PRs live on repositories where `origin` is the wrong remote (`tts-mcp`'s `origin` is upstream `florianbuetow/tts-mcp` while the PR is on the fork), and creating a remote literally named `origin` is how that class of bug returns. The extra worktree hop is the accepted cost of never depending on a remote name.
</context>

<requirements>

## 1. New imports

Add `dataclasses`, `shutil` and `subprocess` to `bench/run.py`'s stdlib import list. No third-party imports.

## 2. Path helpers

```python
def repos_root(cache_root: pathlib.Path) -> pathlib.Path:
    return cache_root / "repos"

def repo_cache_dir(cache_root, owner, repo) -> pathlib.Path:
    return repos_root(cache_root) / owner / repo

def worktree_dir(cache_root, owner, repo, number) -> pathlib.Path:
    return repos_root(cache_root) / owner / f"{repo}__pr{number}"
```

The worktree lives beside the bare-ish clone and **under `repos/`**, not in a sibling directory, so it is covered by the same containment invariant.

```python
def assert_under(path: pathlib.Path, root: pathlib.Path) -> pathlib.Path
```
Resolve both; raise `BenchError` unless `resolved != root_resolved` and `resolved.is_relative_to(root_resolved)`. The message must name both `path` and `root` and state that the runner only ever touches its own cache. Return the resolved path.

## 3. `def fetch_url(owner: str, repo: str) -> str`

```python
return f"https://github.com/{owner}/{repo}"
```

Derived purely from the manifest's `owner`/`repo`. The runner must never read, query or depend on a remote named `origin` to decide where to fetch from — `bborbe/tts-mcp#20`'s PR lives on the fork while that repo's `origin` is upstream `florianbuetow/tts-mcp`, so `git fetch origin pull/20/head` fails there with "couldn't find remote ref".

## 4. `def git(args, *, repo_dir, cache_root, check=True, timeout=600)` — the single git chokepoint

Every `git` invocation the runner ever issues goes through this function. No other function may call `subprocess` with `git`.

```python
def git(args, *, repo_dir, cache_root, check=True, timeout=600):
    target = assert_under(repo_dir, repos_root(cache_root))
    cmd = ["git", "-C", str(target), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise BenchError(f"git {' '.join(args)} failed in {target} (exit {proc.returncode}): {proc.stderr.strip()}")
    return proc
```

- Always `-C <repo_dir>`; never pass `cwd=`, never build a shell string, never interpolate a manifest value into one argument. Manifest values are passed as separate list elements.
- `repo_dir` must already exist (create it with `mkdir(parents=True, exist_ok=True)` before the first call). `git -C <existing-empty-dir> init` works, which is why the runner never needs `git clone` and therefore never needs a cwd-based invocation.
- `assert_under` runs before the subprocess, so a manifest value that somehow escaped validation still cannot target a path outside `bench/.cache/repos/`.
- `subprocess.TimeoutExpired` propagates; `process_pr` converts it into a per-PR failure.

## 5. `def ensure_refs(cache_root, entry) -> pathlib.Path`

Prepare `repo_cache_dir(...)` so the entry's three SHAs are locally reachable. Returns the repo directory.

1. `repo_dir.mkdir(parents=True, exist_ok=True)`.
2. If `repo_dir/".git"` does not exist, `git(["init", "--quiet"], ...)`.
3. **Offline short-circuit** — if all three of `merge_sha`, `base_sha`, `head_sha` already resolve locally, skip the fetch entirely. Test each with `git(["cat-file", "-e", f"{sha}^{{commit}}"], check=False)` and treat `returncode == 0` as resolved. This makes re-runs cheap and is the mechanism that lets the unit tests exercise the whole resolution path with no network.
4. Otherwise fetch once, from the manifest URL:
   ```python
   url = fetch_url(entry["owner"], entry["repo"])
   git(["fetch", "--no-tags", "--force", url,
        f"+pull/{entry['number']}/head:refs/bench/pr{entry['number']}/head",
        "+refs/heads/*:refs/remotes/origin/*"],
       repo_dir=repo_dir, cache_root=cache_root)
   ```
   The first positional argument after the flags is the URL string — never the token `origin`. The `refs/remotes/origin/*` destination is a *local ref namespace* (needed so `/coding:pr-review` can resolve `origin/<branch>` in the prepared working copy), not a remote name, and must not be confused with one.
5. If the fetch fails, `BenchError` from `git()` propagates and `process_pr` records the PR as failed with the underlying git stderr. The outcome string is the generic `failed: <message first line>` form defined in requirement 10 — do NOT introduce a separate `failed: fetch` literal. A fetch failure's first line already begins with `git fetch …`, which identifies the phase; a second, phase-specific literal would be a classification the generic handler cannot produce and no test asserts.

## 6. `def resolve_diff_range(cache_root, repo_dir, entry) -> tuple[str, str, str, int]`

Returns `(diff_range, base_endpoint, head_endpoint, parent_count)`.

```python
out = git(["rev-list", "--parents", "-n", "1", entry["merge_sha"]],
          repo_dir=repo_dir, cache_root=cache_root).stdout.split()
if not out:
    raise BenchError(f"{entry['id']}: cannot resolve merge commit {entry['merge_sha']}")
n_parents = len(out) - 1
if n_parents >= 2:
    base = f"{entry['merge_sha']}^1"
    head = f"{entry['merge_sha']}^2"
elif n_parents == 1:
    base = entry["base_sha"]
    head = entry["head_sha"]
else:
    raise BenchError(f"{entry['id']}: merge commit {entry['merge_sha']} has no parents; cannot reconstruct a diff range")
return f"{base}..{head}", base, head, n_parents
```

This is the whole rule. There is **no fallback branch** — no "second parent, else the merge commit itself" heuristic, and the manifest's `merge_strategy` label never selects the range. A single-parent commit always uses the manifest's recorded `base_sha..head_sha`, never a parent-derived range.

**Strategy-label mismatch is reported, never obeyed.** If `entry["merge_strategy"] == "merge-commit"` and `n_parents == 1`, or `entry["merge_strategy"] == "squash"` and `n_parents >= 2`, append the note `strategy mismatch (manifest={label}, parents={n})` to the PR's notes list. It is cosmetic — the run already used the correct range — and must not fail the PR.

## 7. `def changed_files(cache_root, repo_dir, diff_range) -> list[str]`

```python
proc = git(["diff", "--name-only", diff_range], repo_dir=repo_dir, cache_root=cache_root)
return [ln for ln in proc.stdout.splitlines() if ln.strip()]
```

Pass the same `diff_range` string that gets recorded in the result row, so the executed range and the recorded range can never drift. Apply **no** path exclusions — the manifest's `changed_files` counts came from `gh api repos/<owner>/<repo>/compare/...` with no exclusions, and the recorded count must be comparable to them.

## 8. `def prepare_worktree(cache_root, repo_dir, entry, base_endpoint, head_endpoint) -> PrCheckout`

Resolve both endpoints to full SHAs, publish the two remote-tracking refs `/coding:pr-review` needs, and create the working copy.

```python
base_branch = f"bench-base-{entry['number']}"
head_branch = f"bench-pr-{entry['number']}"
```

1. `base_sha = git(["rev-parse", f"{base_endpoint}^{{commit}}"], ...).stdout.strip()` and likewise `head_sha` from `head_endpoint`.
2. `git(["update-ref", f"refs/remotes/origin/{base_branch}", base_sha], ...)` and the same for `refs/remotes/origin/{head_branch}` → `head_sha`. These make `origin/bench-base-<n>` resolvable in the working copy, which is what `commands/pr-review.md` Step 0c diffs against.
3. Tear down any stale copy from a previous run, ignoring failures:
   - `git(["worktree", "remove", "--force", str(wt)], ..., check=False)`
   - `shutil.rmtree(wt, ignore_errors=True)` after `assert_under(wt, repos_root(cache_root))` — the `assert_under` call is mandatory before any `rmtree`
   - `git(["branch", "-D", head_branch], ..., check=False)`
   - `git(["worktree", "prune"], ..., check=False)`
4. `assert_under(wt, repos_root(cache_root))` again, then `git(["worktree", "add", "--force", "-b", head_branch, str(wt), head_sha], ...)`. The `git()` chokepoint only validates the `-C` repository argument, so `wt` — which is passed as a positional path and is where `--force` will overwrite — must be validated explicitly. Same defense-in-depth rule as step 3's `rmtree`: every path this function hands to a destructive operation is asserted at the call site, never trusted because of where it came from.
5. Return the checkout record.

```python
@dataclasses.dataclass
class PrCheckout:
    pr_id: str
    repo_dir: pathlib.Path
    worktree: pathlib.Path
    base_branch: str
    head_branch: str
    diff_range: str
    base_sha: str
    head_sha: str
    changed_files: int
    parent_count: int
    notes: list
```

## 9. `def resolve_pr(cache_root, entry) -> PrCheckout`

Ties steps 5–8 together in order: `ensure_refs` → `resolve_diff_range` → `changed_files` → **empty-diff gate** → `prepare_worktree`.

The empty-diff gate runs **before** the worktree is created and before any review could be invoked:

```python
files = changed_files(cache_root, repo_dir, diff_range)
if not files:
    raise BenchError(
        f"EMPTY DIFF: {entry['id']} resolved range {diff_range} contains zero changed files. "
        f"This is never recorded as a zero-finding review — two independent code paths produce "
        f"this state and both look identical to a genuinely clean PR. "
        f"Re-verify the SHAs with: gh api repos/{entry['owner']}/{entry['repo']}/compare/{entry['base_sha']}...{entry['head_sha']} --jq '.files | length'"
    )
```

The message must contain the literal `EMPTY DIFF`, the PR id, and the resolved range.

## 10. Rewrite `process_pr` — resolution now real, review still stubbed

```
1. checkout = resolve_pr(cache_root, entry)          # may raise BenchError
2. return ("failed", "review invocation not yet implemented (prompt 3 of spec 002)")
```

Do NOT append a result row, do NOT create a cache entry, do NOT return a success outcome. Prompt 3 replaces step 2.

`run_bench` must catch, per PR and without aborting the loop:
- `BenchError` → outcome `failed: <message first line>`
- `subprocess.TimeoutExpired` → outcome `failed: timeout`
- `OSError` → outcome `failed: <errno message>` (this is the disk-exhaustion path)

Each failing PR prints its full error to stderr, contributes no row and no cache entry, and the process exit code becomes 1. Any note collected on a checkout (e.g. `strategy mismatch (...)`) is appended to that PR's summary line.

## 11. Extend `bench/testsupport.py`

```python
def init_git_repo(path) -> pathlib.Path
```
`git init` a directory and configure `user.email`/`user.name` locally so commits work in a bare container. Return the path.

```python
def commit_file(repo, relpath, text, message) -> str
```
Write the file, `git add`, `git commit`, return the resulting full SHA.

```python
def make_merge_repo(path) -> dict
```
Build a repo with a real two-parent merge commit: commit `base` on the default branch, branch off, commit a change on the branch, return to the default branch, commit a second change, then `git merge --no-ff <branch>`. Return `{"repo": path, "merge_sha": ..., "base_sha": ..., "head_sha": ...}` where `base_sha`/`head_sha` are the merge's first and second parents. Ensure the branch's change touches at least one file the default branch did not, so both endpoints differ.

```python
def make_squash_repo(path) -> dict
```
Build a repo whose final commit has exactly one parent and differs from its parent in ≥1 file. Return `{"repo": path, "merge_sha": <final>, "base_sha": <parent>, "head_sha": <final>}` — mirroring `node-skeleton#2`, where `head_sha == merge_sha`.

```python
def make_empty_diff_repo(path) -> dict
```
Build a single-parent repo and return an entry whose `base_sha` and `head_sha` are **the same commit**, so the resolved range yields zero changed files.

```python
def stub_git(bin_dir, log_file) -> pathlib.Path
```
Install a stub `git` on `PATH` that appends one line per invocation to `log_file` recording the process cwd and the full argument list, then exits 0 with empty stdout. Body shape:
```sh
printf 'cwd=%s args=%s\n' "$(pwd)" "$*" >> "<log_file>"
exit 0
```

```python
def make_manifest(path, entries, version="test-1") -> pathlib.Path
```
Write a minimal valid manifest JSON to `path` and return it.

## 12. Extend `bench/test_resolve.py` (new file)

`import unittest`, `import run`, `import testsupport`. All tests must run offline with no `claude` binary and no GitHub access.

1. **`test_diff_range_branches_on_parent_count`** (AC2) — build a merge repo and a squash repo in one temp dir (both placed under a temp `cache_root/repos/...` so `assert_under` is satisfied). Assert:
   - merge repo → `resolve_diff_range` returns range `f"{merge_sha}^1..{merge_sha}^2"` and `parent_count == 2`
   - squash repo → returns exactly `f"{base_sha}..{head_sha}"` from the manifest entry and `parent_count == 1`
   - `changed_files(...)` for each range has length ≥ 1
   Use an assertion message that names both ranges, e.g. `msg=f"merge_range={merge_range!r} squash_range={squash_range!r}"`. The test name must contain `parent_count`.
2. **`test_squash_range_is_manifest_derived_not_parent_derived`** — for the squash repo, construct an entry whose `base_sha` is deliberately an *older* commit than the merge commit's parent, and assert the returned range uses the manifest's `base_sha`, proving parent traversal is not consulted for single-parent commits.
3. **`test_strategy_label_mismatch_is_noted_not_obeyed`** — a two-parent repo whose entry claims `merge_strategy: "squash"` still yields the `^1..^2` range, and the note list contains `strategy mismatch`.
4. **`test_empty_diff_aborts_loudly`** (AC3) — pre-seed `cache_root/repos/<owner>/<repo>` with `make_empty_diff_repo` so no fetch is attempted, plus a matching `.claude-verify` config dir so the preflight passes, plus `stub_claude` with a counter file on `PATH`. Call `run.run_bench(...)`. Assert: return code is non-zero; the captured stderr contains `EMPTY DIFF`, the PR id and the range; `results_dir/"results.jsonl"` either does not exist or has the same line count as before the call (0); `cache_root/"reviews"` does not exist or contains no files; the stub-`claude` counter file has 0 lines.
5. **`test_fetch_url_is_built_from_manifest_owner_repo`** (AC8) — assert `run.fetch_url("bborbe", "tts-mcp") == "https://github.com/bborbe/tts-mcp"`. Then, with `stub_git` on `PATH`, drive `ensure_refs` for an entry whose `owner`/`repo` is `bborbe/tts-mcp` in a repo dir that has a remote literally named `origin` pointing at `https://github.com/florianbuetow/tts-mcp`, and assert the logged `fetch` invocation's first positional argument after the flags is exactly `https://github.com/bborbe/tts-mcp` and that the token `origin` never appears as that positional argument.
6. **`test_fetch_url_used_when_no_origin_remote_exists`** (AC8, second case) — same assertion in a repo dir with no remotes configured at all; the constructed URL is unchanged, proving `origin` is never consulted.
7. **`test_every_git_invocation_stays_under_cache_repos`** (AC7) — with `stub_git` logging to a file and a two-PR temp manifest (and a passing plugin preflight), call `run.run_bench(...)`. Then:
   - assert the log file has **at least one line per manifest PR** (≥2), so the check cannot pass vacuously through an early abort with zero git invocations
   - for each logged line, take the value following `-C` if present, otherwise the recorded `cwd`
   - assert each such target path is a strict prefix-match of `<cache_root>/repos/`, with a failure message naming the offending path verbatim
8. **`test_assert_under_rejects_outside_path`** — `assert_under(pathlib.Path("/tmp"), repos_root(cache))` raises `BenchError`, and `assert_under(repos_root(cache), repos_root(cache))` also raises (the root itself is not a strict prefix match).
9. **`test_failing_pr_does_not_abort_remaining_prs`** — a two-PR manifest where the first entry's `merge_sha` is unresolvable and the second resolves cleanly; assert both PRs appear in the summary, the first as `failed`, and `run_bench` returns 1.
10. **`test_worktree_is_created_under_repos_root`** — after `resolve_pr` on a seeded merge repo, the returned `worktree` exists, is a directory under `<cache_root>/repos/`, has `HEAD` at the resolved head SHA, and `git -C <worktree> rev-parse --abbrev-ref HEAD` prints `bench-pr-<number>`. Also assert `git -C <repo_dir> rev-parse refs/remotes/origin/bench-base-<number>` resolves to the base SHA — this is the boundary the `/coding:pr-review` command crosses in its Step 0c `git diff origin/<TARGET_BRANCH>...HEAD`.

## 13. Do not modify

Do not touch `Makefile`, `bench/README.md`, `CHANGELOG.md`, `bench/prs.json`, `rules/`, `commands/`, `agents/` or `docs/`.
</requirements>

<constraints>
- Python 3 standard library only — no `pip`, no `requirements.txt`, no third-party imports
- **Every `git` invocation goes through the single `git()` chokepoint, always with `-C <path under bench/.cache/repos/>`.** No `cwd=` argument, no `git clone`, no shell string, no invocation targeting a path outside that prefix. `/coding:pr-review` holds `git worktree`, `git fetch`, `git branch` and `rm -rf` permissions, so a runner that reused an operator's real clone could destructively mutate it
- Every subprocess is invoked with an argument list; no manifest value is ever interpolated into a shell command
- No `shutil.rmtree` without a preceding `assert_under(..., repos_root(cache_root))`
- Fetch targets the URL built from the manifest's `owner`/`repo`; the runner never depends on a remote named `origin`
- Diff-range selection branches on actual parent count only. No fallback branch, no reliance on the manifest's `merge_strategy` label
- Zero changed files aborts that PR loudly with the literal `EMPTY DIFF` — never recorded as a zero-finding review
- A failed PR produces no row and no cache entry; remaining PRs still run; process exits non-zero
- Fixed invariants, not configurable: 45-minute review timeout, cache under `bench/.cache/`, results under `bench/results/`, config dir `$HOME/.claude-verify`. Do NOT add flags or env vars for any of them
- Do NOT add a retry loop around a failed fetch or review
- No personal paths anywhere (`/Users/`, `~/Documents/`)
- `bench/prs.json` is a frozen input
- Do NOT commit — dark-factory handles git
- All new tests must run offline: no network, no real `claude` binary, no GitHub access
</constraints>

<verification>
```
# Stdlib-only imports
grep -nE '^(import |from )' bench/run.py

# No personal paths
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"

# Single git chokepoint: every subprocess git call is inside git()
grep -n 'subprocess.run' bench/run.py
grep -n '"git"' bench/run.py
# Expect exactly one subprocess.run building a git command, inside def git(...)

# No cwd-based subprocess invocation
grep -n 'cwd=' bench/run.py ; echo "cwd grep exit=$?  (expect 1 for this prompt)"

# Unit tests pass, including the four AC tests
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tee /tmp/bench-tests.log
grep -c 'parent_count' /tmp/bench-tests.log
grep -c 'empty_diff' /tmp/bench-tests.log
grep -c 'stays_under_cache_repos' /tmp/bench-tests.log
grep -c 'fetch_url' /tmp/bench-tests.log

# The empty-diff message really carries the literal
grep -n 'EMPTY DIFF' bench/run.py

# Reserved flag and mandatory flags unchanged from prompt 1
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"

# Frozen manifest still validates
python3 -c "
import sys, pathlib
sys.path.insert(0, 'bench')
import run
m = run.load_manifest(pathlib.Path('bench/prs.json'))
print('manifest ok:', m['version'], len(m['prs']), 'entries')
for e in m['prs']:
    print(' ', e['id'], run.fetch_url(e['owner'], e['repo']))
"

# Repo checks unchanged
make precommit
```
</verification>
