---
description: Release a git repo — cwd, a directory path, or `owner/repo` / GitHub URL (clone to tmp). Classify bump from `## Unreleased`, rewrite header, commit, tag, push. PR + auto-merge fallback for branch-protected repos.
argument-hint: "[target] [--dry-run]"
allowed-tools:
  - Bash(git clone:*)
  - Bash(git status:*)
  - Bash(git rev-parse:*)
  - Bash(git symbolic-ref:*)
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(git fetch:*)
  - Bash(git pull:*)
  - Bash(git describe:*)
  - Bash(git tag:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push:*)
  - Bash(git checkout:*)
  - Bash(grep:*)
  - Bash(awk:*)
  - Bash(sed:*)
  - Bash(cat:*)
  - Bash(head:*)
  - Bash(mkdir -p /tmp/github-release:*)
  - Bash(mktemp:*)
  - Bash(mv CHANGELOG.md.new CHANGELOG.md)
  - Bash(rm -rf /tmp/github-release/tmp.*:*)
  - Bash(gh pr create:*)
  - Bash(gh pr view:*)
  - Bash(gh pr merge:*)
  - Bash(gh api:*)
  - Read
  - Edit
  - AskUserQuestion
---

Direct release command. Target = cwd, a local directory, or a remote repo (`owner/repo` or GitHub URL, cloned to tmp). No task file, no vault interaction — pure git + Claude bump classification, with a confirm step before any write.

Same release logic as the maintainer agent's `planning` + `execution` phases (`agent/github-releaser`), just operator-triggered on the current repo instead of vault-task-driven. Sibling tooling (a vault-task-driven release pipeline and a fleet scanner that emits release tasks) lives outside this plugin.

## When to use which

| Command | Trigger | State |
|---|---|---|
| `/coding:github-release [target]` | "release a repo NOW" — cwd, a worktree path, or a remote `owner/repo` | none — direct |
| `/github-release-task-agent <task>` | Task already emitted by watcher; release per-task with phase tracking | vault task file |
| `/github-release-repo-watcher [owner]` | Scan fleet, emit tasks for repos with `## Unreleased` | emits tasks |

## Arguments

- **`target`** (optional, positional) — *where* to release. Forms:
  - omitted → use cwd
  - directory path (starts with `/`, `~`, `./`, `../`, or exists as a dir) → `cd` into it, release in place
  - `owner/repo` (no slash before the slash, no scheme) → clone `git@github.com:owner/repo.git` to a tmp dir
  - `https://github.com/owner/repo[.git]` → same clone-to-tmp
- **`--dry-run`** — print the plan; no git writes, no remote calls (except read-only `gh api`), no commit, no tag, no push

Bump is always auto-classified from `## Unreleased`. No flag overrides — the major-bump confirm step (#6) gives you the downgrade choice when Claude over-classifies.

Examples:

```
/coding:github-release                                           # cwd
/coding:github-release ~/Documents/workspaces/maintainer         # dir
/coding:github-release bborbe/maintainer                         # owner/repo
/coding:github-release https://github.com/bborbe/maintainer      # URL
/coding:github-release bborbe/maintainer --dry-run               # preview
```

## Workflow

### 0. Resolve target

```bash
# Helpers used throughout the workflow:
die() { echo "ERROR: $*" >&2; exit 1; }
default_branch() {
  local b
  b=$(git symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||')
  if [ -z "$b" ]; then git show-ref --verify --quiet refs/remotes/origin/master && b=master; fi
  if [ -z "$b" ]; then git show-ref --verify --quiet refs/remotes/origin/main   && b=main;   fi
  [ -n "$b" ] || die "cannot determine default branch (origin/HEAD unset, no master/main)"
  echo "$b"
}
owner_repo() {
  # Parse owner/repo from origin URL. Supports git@github.com:owner/repo(.git)? and https://github.com/owner/repo(.git)?.
  # Uses shell parameter expansion only — portable across bash/zsh, no sed regex flavor issues.
  local url=$(git remote get-url origin 2>/dev/null) || die "no origin remote"
  local stripped="${url#*github.com[:/]}"   # strip everything up to and including 'github.com:' or 'github.com/'
  stripped="${stripped%.git}"                # drop trailing .git if present
  [[ "$stripped" == */* && "$stripped" != */*/* ]] || die "cannot parse owner/repo from origin: $url"
  printf '%s' "$stripped"
}

# Auto-cleanup of tmp clones on any exit path (success, error, Ctrl-C):
clone_path=""
trap '[ -n "$clone_path" ] && rm -rf "$clone_path"' EXIT

target="$1"   # may be empty

case "$target" in
  "")
    workdir="$PWD"; clone_path=""
    ;;
  /*|~*|./*|../*)
    workdir="${target/#\~/$HOME}"
    [ -d "$workdir" ] || die "directory does not exist: $workdir"
    clone_path=""
    ;;
  https://github.com/*|git@github.com:*)
    # URL form
    mkdir -p /tmp/github-release
    tmp=$(mktemp -d /tmp/github-release/tmp.XXXXXX)
    clone_url="$target"; clone_path="$tmp"
    git clone --quiet "$clone_url" "$tmp" || die "clone failed: $clone_url"
    workdir="$tmp"
    ;;
  */*)
    # owner/repo form (one slash, no scheme, no leading dot/slash/tilde)
    case "$target" in
      */*/*)   die "ambiguous target: $target" ;;
      *[:@]*)  die "invalid owner/repo target: $target (contains : or @ — refusing to construct git URL with embedded host)" ;;
    esac
    mkdir -p /tmp/github-release
    tmp=$(mktemp -d /tmp/github-release/tmp.XXXXXX)
    clone_url="git@github.com:${target}.git"; clone_path="$tmp"
    git clone --quiet "$clone_url" "$tmp" || die "clone failed: $clone_url"
    workdir="$tmp"
    ;;
  *)
    # Could be a relative dir without ./ prefix
    if [ -d "$target" ]; then
      workdir="$target"; clone_path=""
    else
      die "unrecognized target: $target (use cwd, a directory path, owner/repo, or a GitHub URL)"
    fi
    ;;
esac

cd "$workdir"
```

Cleanup happens automatically via the `trap '[ -n "$clone_path" ] && rm -rf "$clone_path"' EXIT` set above — runs on success, error, `die`, and Ctrl-C. No additional cleanup needed at exit paths.

For cloned targets, dirty-tree / non-default-branch checks are trivially satisfied — fresh clone, on default branch. They run anyway for uniform code path.

### 1. Preflight (repo state)

```bash
git rev-parse --is-inside-work-tree   # must be a git repo
git symbolic-ref --short HEAD          # current branch
git status --porcelain                 # must be clean (no uncommitted changes)
```

Fail-fast errors:
- Not a git repo → `not a git repository: $workdir`
- Dirty tree → `working tree not clean; commit or stash first` (skip for cloned targets — fresh clones are clean by construction)
- Not on default branch → `not on default branch (HEAD is X, default is master/main)`. Detect default via `git symbolic-ref refs/remotes/origin/HEAD` or fall back to `master` then `main`.
- No `CHANGELOG.md` → `no CHANGELOG.md in repo root`

For non-cloned targets: `git fetch && git pull --ff-only` to sync with remote. Abort on non-ff (`local diverged from origin; rebase first`). For cloned targets: clone is already at remote HEAD, skip.

### 2. CHANGELOG preconditions

Same rules as `/github-release-task-agent` planning phase:

**P1. `## Unreleased` MUST be the first `## ` heading.**

```bash
first=$(grep -nE '^## ' CHANGELOG.md | head -1)
echo "$first" | grep -q ': *## Unreleased$' || die "Unreleased is not the first ## section (found: $first). Move ## Unreleased above all release headings."
```

**P2. `## Unreleased` MUST have ≥1 `- ` bullet.**

```bash
bullets=$(awk '/^## Unreleased$/{flag=1;next}/^## /{flag=0}flag' CHANGELOG.md | grep -c '^- ')
[ "$bullets" -gt 0 ] || die "## Unreleased has no bullet entries; nothing to release."
```

### 3. Detect current version + header style

```bash
# Latest tag (matches v-prefixed or bare semver)
current=$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null \
  || git describe --tags --abbrev=0 --match '[0-9]*' 2>/dev/null \
  || echo "v0.0.0")

# Infer header prefix style from first historic release heading
sample=$(grep -E '^## [v0-9]' CHANGELOG.md | grep -v '^## Unreleased$' | head -1)
case "$sample" in
  '## v'*) prefix="v" ;;
  '## '[0-9]*) prefix="" ;;
  *) prefix="v" ;;   # first release defaults v-prefixed
esac
```

### 4. Classify bump + rewrite bullets via `release-changelog-agent`

Invoke the shared release agent via the Task tool with the `/coding:github-release` profile (`majorBumpAllowed=true`, `rewriteChangelogEntries=true`) — operator-facing path gets full classification and AI rewrite.

```
Task(
  subagent_type="release-changelog-agent",
  prompt="""
    current_version: $current
    majorBumpAllowed: true
    rewriteChangelogEntries: true

    unreleased_body:
    <verbatim Unreleased section captured in Step 3>
  """
)
```

Parse the returned JSON:
- `bump` → drives Step 5 (version arithmetic) and Step 6 (plan + confirm)
- `rewritten_unreleased` → if non-empty, replaces the Unreleased body in CHANGELOG.md at Step 8 (header rewrite happens at the same time). If empty, leave bullets as-is.
- `reasoning` → shown in Step 6 plan output

**Why these flags:** Direct operator release wants the full pipeline — major-bump classification (caller can downgrade at the confirm step) and AI rewrite for clean release notes. Matches the K8s `agent/github-releaser` planning-phase behavior, so a local dry-run can preview what autonomous release would do.

**Pre-1.0 cap (always-on)** still applies inside the agent — `current_version` starting with `0.` or `v0.` never returns `bump: major` even with `majorBumpAllowed=true`. The agent will downgrade to `minor` with a `pre-1.0` mention in `reasoning`.

Edge case: `current = v0.0.0` (no prior tag) → next is `v0.1.0` regardless of bump.

### 5. Compute next version + header

```bash
# Strip 'v' prefix from current for arithmetic
cur_n="${current#v}"
IFS=. read -r MAJ MIN PAT <<< "$cur_n"

case "$bump" in
  major) MAJ=$((MAJ+1)); MIN=0; PAT=0 ;;
  minor) MIN=$((MIN+1)); PAT=0 ;;
  patch) PAT=$((PAT+1)) ;;
esac

next="${prefix}${MAJ}.${MIN}.${PAT}"
header="## ${next}"
```

### 6. Show plan + confirm

Always print the plan first:

```
Release plan for <owner>/<repo>:
  current: v1.2.6
  next:    v1.2.7  (patch)
  reason:  internal refactor + dep bumps, no API changes
  header:  ## v1.2.7
  bullets (3):
    - bump go-deps
    - tidy
    - factor out helpers
```

If `--dry-run` → exit here. **No confirm, no writes.**

Otherwise the confirm depends on the proposed bump:

**Patch / Minor** — single y/n via `AskUserQuestion`:
- "Release v1.2.7?" → `Proceed` / `Cancel` (Recommended: Proceed)

**Major** — operator usually disagrees with Claude's "major" call. Force an explicit choice via `AskUserQuestion` with four options:
- `Confirm major (v2.0.0)` — proceed as classified
- `Downgrade to minor (v1.3.0)` (Recommended) — recompute next as minor, proceed
- `Downgrade to patch (v1.2.7)` — recompute next as patch, proceed
- `Cancel` — exit

On downgrade: recompute `next` (#5) with the chosen bump, re-print one-line "→ now releasing v1.3.0 (minor, operator override)", then proceed straight to step 7 (no second confirm).

On `Cancel` → exit, no writes.

### 7. Tag collision check

```bash
git rev-parse "$next" >/dev/null 2>&1 && die "tag $next already exists locally — pull or delete"
OR=$(owner_repo)
gh api "repos/${OR}/git/refs/tags/$next" --silent 2>/dev/null && die "tag $next already exists on remote"
```

### 8. Rewrite header (+ rewritten bullets) + commit

If the agent returned a non-empty `rewritten_unreleased`, the Edit tool is preferred over the awk pipeline below — it can replace the multi-line Unreleased block atomically in one operation:

```
Edit(CHANGELOG.md):
  old_string: "## Unreleased\n<verbatim original bullets>"
  new_string: "## ${next}\n<rewritten_unreleased>"
```

Otherwise (passthrough — agent returned empty `rewritten_unreleased`), header-only rewrite via awk:

```bash
awk -v n="$next" 'BEGIN{r=0} /^## Unreleased$/ && r==0 {print "## "n; r=1; next} {print}' CHANGELOG.md > CHANGELOG.md.new && mv CHANGELOG.md.new CHANGELOG.md
```

Then commit:

```bash
git add CHANGELOG.md
git commit -m "release ${next}"
COMMIT_SHA=$(git rev-parse HEAD)
```

### 9. Try direct push

```bash
git push origin "HEAD:$(default_branch)"
```

- Success → step 10 (tag + push)
- Branch-protection error (`GH006`, `Required status check`, `required pull request reviews`) → step 11 (PR fallback)
- Other error → fail, leave commit on local branch for operator to inspect

### 10. Tag + push tag

```bash
git tag "$next"
git push origin "$next"
```

Final report → step 12.

### 11. PR fallback (branch-protected)

```bash
branch="release/${next}"
git checkout -b "$branch"
git push -u origin "$branch"
gh pr create --base "$(default_branch)" --head "$branch" \
  --title "release ${next}" \
  --body "Auto-release via /coding:github-release. Bump: ${bump}. Reasoning: ${reasoning}."
gh pr merge --auto --squash --delete-branch
```

Polling loop (up to 5 min, 10s interval):

```bash
pr_num=$(gh pr view "$branch" --json number --jq '.number')
for _ in $(seq 1 30); do
  sleep 10
  merged_sha=$(gh pr view "$pr_num" --json state,mergeCommit --jq 'select(.state=="MERGED") | .mergeCommit.oid')
  [ -n "$merged_sha" ] && break
done
if [ -n "$merged_sha" ]; then
  git checkout "$(default_branch)" && git pull && git tag "$next" "$merged_sha" && git push origin "$next"
else
  echo "PR open, merge pending: https://github.com/$(owner_repo)/pull/$pr_num"
  echo "Re-run /coding:github-release after merge — Steps 1-8 will detect the released CHANGELOG and exit cleanly; only Step 10 (tag at merge SHA) needs to fire."
  exit 0
fi
```

### 12. Report

```
✓ Released <owner>/<repo> v1.2.7 (patch)
  commit:  abc1234 release v1.2.7
  tag:     https://github.com/<owner>/<repo>/releases/tag/v1.2.7
  path:    direct-push | pr-merge
  pr:      <url>           # if pr-merge
```

## Constraints

- **Target resolution before any work** — resolve `target` arg first; reject ambiguous forms early.
- **Default branch only** — refuse if HEAD is a feature branch. Releases happen on master/main.
- **Clean tree required** — no uncommitted changes for cwd / dir targets (cloned targets are clean by construction).
- **Confirm before write** — `AskUserQuestion` y/n on the plan unless `--dry-run`.
- **Dry-run safety** — zero git mutations, zero remote writes (read-only `gh api` GETs + `git clone` for URL targets are OK; cleanup still runs).
- **Cleanup clones** — every exit path `rm -rf` the tmp clone dir under `/tmp/github-release/`. Don't leak `$(mktemp -d ...)`.
- **Idempotency** — re-running after a successful release: tag collision check catches it; exit with `already released`.
- **No `--force`, no `--no-verify`** — respect hooks and branch protection. PR fallback handles protection cleanly.
- **No Claude attribution** in commit message or PR body.
- **No vault interaction** — this command is a pure local tool; the task-file machinery lives in `/github-release-task-agent`.

## Difference vs `/github-release-task-agent`

| Aspect | `/coding:github-release [target]` | `/github-release-task-agent <task>` |
|---|---|---|
| Input | cwd / dir / `owner/repo` / URL | vault task file |
| Output | release | release + `## Plan` / `## Result` / `## Review` JSON sections |
| Phases | none — one shot | planning → execution → ai_review |
| Resume after crash | no — re-run from start | yes — resumes at last-advanced `phase` |
| Clone | only for `owner/repo` / URL targets | always — clones repo at `ref` |
| Use case | "release a repo NOW" | "watcher emitted N tasks, batch through them" |

Both share the same release logic (preconditions, bump rules, header rewrite, push or PR-fallback). This command is the operator shortcut; the agent is the pipeline drone.
