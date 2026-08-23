---
description: Intelligent Git commit with automatic changelog/tagging detection
argument-hint: [directory]
allowed-tools:
  - Read
  - Edit
  - MultiEdit
  - Glob
  - LS
  - Task
  - Bash(git describe:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git rev-list:*)
  - Bash(git rev-parse:*)
  - Bash(git status:*)
  - Bash(make precommit:*)
---

# Commit

Intelligent Git commit command that automatically detects project structure and branch context:

- **Pipeline-only (prompts/specs/scenarios)**: Commit and push, no changelog/version/tag
- **Feature branch + CHANGELOG.md**: Adds changes to `## Unreleased` section, no tag
- **Master/main + `.maintainer.yaml: release.autoRelease: true`**: Adds to `## Unreleased`, NO tag — `github-releaser-agent` handles the release within ~10 min
- **Master/main + CHANGELOG.md + Unreleased (manual release)**: Converts `## Unreleased` to `## vX.Y.Z`, creates tag
- **Master/main + CHANGELOG.md (no Unreleased)**: Legacy workflow - creates version section + tag
- **No CHANGELOG.md**: Simple commit without versioning

Tags are ONLY created on master/main branch AND only when `.maintainer.yaml` does not opt into bot auto-release. Feature branches never create tags.

## Workflow

### Automatic Detection
1. Determine working directory
2. **Read project `CLAUDE.md`** (if present at repo root) — scan for release/commit checklists, extra files to bump, and project-specific rules. Common sections: "Release Checklist", "Plugin Release Checklist", "Publishing", "Version Bump". If a checklist lists extra files (e.g. `.claude-plugin/plugin.json`, `package.json`, `pyproject.toml`, `Cargo.toml`), treat them as mandatory parts of any release commit and bump their version string to match the new `vX.Y.Z`.
3. Detect current branch (master/main vs feature)
4. Check if `CHANGELOG.md` exists
5. Check for `## Unreleased` section
6. **Detect maintainer-bot auto-release opt-in** (`.maintainer.yaml: release.autoRelease: true`)
7. **Detect pipeline-only changes** (only prompts/, specs/, scenarios/)
8. **Detect trivial changes** (comments, whitespace, TODOs only)
9. Route to appropriate workflow

### CRITICAL: "No changes" check

When `CHANGELOG.md` exists, NEVER abort based on `git status --porcelain` alone. A clean working tree can still have **unreleased commits since the last tag** that need to be released.

**Always run both checks:**
```bash
cd $PROJECT_DIR && git status --porcelain                                  # uncommitted
cd $PROJECT_DIR && git log --oneline $(git describe --tags --abbrev=0)..HEAD  # unreleased commits
```

Abort with "No changes to commit" only if **both** are empty. If there are unreleased commits on master/main, proceed with Workflow B or C to create the release (changelog + tag), even with a clean working tree.

### Workflow A: Feature Branch WITH CHANGELOG.md
1. Run `make precommit` (if available)
2. Ensure `## Unreleased` section exists (create if missing)
3. Add change descriptions to Unreleased section
4. Commit with descriptive message (NOT "release vX.Y.Z")
5. Push WITHOUT creating any tag

### Workflow B: Master Branch + CHANGELOG.md + Unreleased Section
1. Run `make precommit` (if available)
2. Get current version from latest git tag
3. Invoke `release-changelog-assistant` (flags: `majorBumpAllowed=false`, `rewriteChangelogEntries=false`) → classified `bump` → calculate new version
4. Rename `## Unreleased` to `## vX.Y.Z` in CHANGELOG.md
5. Commit with "release vX.Y.Z" message
6. Create tag and push both commits and tag

### Workflow C: Master Branch + CHANGELOG.md (No Unreleased)
1. Legacy workflow: create new version section, tag, push
2. Same as previous behavior for backward compatibility

### Workflow D: No CHANGELOG.md
1. Simple commit without versioning (unchanged)

### Workflow E: Trivial or Pipeline-Only Change (any branch, any project)
1. Run `make precommit` (if available)
2. Commit with descriptive message
3. Push — no CHANGELOG update, no version bump, no tag
4. Pipeline-only = all files in `prompts/`, `specs/`, or `scenarios/`

## Implementation

Execute the following steps:

### 1. Determine Working Directory and Branch
```bash
# If $ARGUMENTS is provided, use it as PROJECT_DIR
# Otherwise, use current working directory
PROJECT_DIR="${ARGUMENTS:-.}"
```

```bash
# Detect current branch
CURRENT_BRANCH=$(cd $PROJECT_DIR && git rev-parse --abbrev-ref HEAD)
case "$CURRENT_BRANCH" in
  master|main) IS_MASTER=true ;;
  *) IS_MASTER=false ;;
esac
```

### 2. Detect Project Structure
```bash
# Check if CHANGELOG.md exists
ls "$PROJECT_DIR/CHANGELOG.md" 2>/dev/null

# If CHANGELOG.md exists, check for Unreleased section
grep -q "^## Unreleased" "$PROJECT_DIR/CHANGELOG.md" 2>/dev/null
```

### 2b. Detect maintainer-bot Auto-Release Opt-in

If `.maintainer.yaml` exists at repo root and declares `release.autoRelease: true`, the maintainer's `github-releaser-agent` owns the release: it picks up non-empty `## Unreleased` blocks via its watcher (~10 min poll), rewrites the header to `## vX.Y.Z`, commits, tags, pushes.

When this opt-in is detected, this skill MUST NOT:
- Rename `## Unreleased` → `## vX.Y.Z` itself
- Run `git tag`

…even on master/main. Route to Workflow A (add to Unreleased, push) regardless of branch.

```bash
AUTORELEASE_BOT=false
if [ -f "$PROJECT_DIR/.maintainer.yaml" ]; then
  # Look for `release:` block with `autoRelease: true` on the next non-empty line.
  if awk '/^release:/{flag=1; next} flag && /autoRelease:[[:space:]]*true/{print; exit} flag && /^[^[:space:]]/{flag=0}' "$PROJECT_DIR/.maintainer.yaml" | grep -q .; then
    AUTORELEASE_BOT=true
  fi
fi
```

See [[GitHub Auto-Release Guide]] for the full bot release flow, opt-in config, and manual fallback (`/github-release-repo`).

### 2c. Detect branch protection (master/main only)

A protected branch is the repo saying *changes go through a PR*. Pushing straight to it does not fail loudly when the operator holds admin rights — GitHub accepts the push and prints `Bypassed rule violations`, so the required status checks simply never run. That is a silent CI skip, and the operator usually only sees it scroll past.

**Resolve the repo from the push remote — never let `gh` infer it.** `{owner}/{repo}` is `gh`'s own guess from the remote set, and on a fork it resolves to the **upstream parent**, not the repo you are pushing to. Observed 2026-08-22 on `bborbe/tts-mcp` (a fork of `florianbuetow/tts-mcp`, whose only remote is named `fork`): the check queried florianbuetow's repo, which has no rulesets, returned empty, and reported the branch unprotected. The push then bypassed a required PR *and* a required `test` check. Any repo whose remote is not named `origin`, or which has an upstream parent, hits this.

**And let a failed query be loud.** With `2>/dev/null`, "this repo has no rules" and "the query failed / hit the wrong repo" produce identical empty output — so the failure mode is a silent pass, exactly the case the check exists to prevent. See [[Checks That Report False Green]].

Run this whenever `IS_MASTER=true`, before any push:

```bash
PROTECTED=""
if command -v gh >/dev/null 2>&1; then
  # Derive owner/repo from the remote we actually push to, not from gh's inference.
  PUSH_REMOTE=$(cd $PROJECT_DIR && git rev-parse --abbrev-ref --symbolic-full-name @{push} 2>/dev/null | cut -d/ -f1)
  PUSH_REMOTE=${PUSH_REMOTE:-origin}
  REPO_SLUG=$(cd $PROJECT_DIR && git remote get-url "$PUSH_REMOTE" \
    | sed -E 's#^(git@github\.com:|https://github\.com/)##; s#\.git$##')

  if [ -z "$REPO_SLUG" ]; then
    echo "⚠️ Could not resolve owner/repo from remote '$PUSH_REMOTE' — cannot verify branch protection." >&2
    exit 1
  fi

  # Capture stderr so a failed query is distinguishable from "no rules".
  RULES_ERR=$(mktemp)
  RULES=$(gh api "repos/$REPO_SLUG/rules/branches/$CURRENT_BRANCH" --jq '.[].type' 2>"$RULES_ERR")
  RULES_EXIT=$?
  if [ $RULES_EXIT -ne 0 ]; then
    echo "⚠️ Branch-protection query failed for $REPO_SLUG ($(head -1 "$RULES_ERR"))." >&2
    echo "   Treating as UNVERIFIED, not as unprotected. Do not push until this is resolved." >&2
    rm -f "$RULES_ERR"; exit 1
  fi
  rm -f "$RULES_ERR"

  PROTECTED=$(printf '%s\n' "$RULES" | grep -E '^(pull_request|required_status_checks)$' | tr '\n' ' ')
fi
```

Sanity-check the slug before trusting an empty result: `echo "$REPO_SLUG"` must name the repo you believe you are pushing to. An empty `PROTECTED` from the wrong repo looks exactly like an empty one from the right repo.

`PROTECTED` non-empty means a direct push would bypass a rule. **Stop and surface it** — do not push, and do not silently rely on admin bypass:

```
⚠️ $CURRENT_BRANCH is protected: $PROTECTED
A direct push bypasses it and skips required checks.
  1. Branch + PR instead (recommended)
  2. Push directly anyway (admin bypass, checks will not run)
```

Proceed with the direct push only on explicit confirmation. If `gh` is absent, the check is skipped and every workflow continues unchanged. If the repo genuinely has no ruleset, `PROTECTED` is empty and nothing blocks — but a *failed* query now aborts rather than passing silently, because an unverifiable protection state is not the same as an absent one.

**Verify against the push output, too.** The pre-check can still be wrong; the remote is the authority. If a push prints `Bypassed rule violations`, a protected branch was written to regardless of what the check said — surface it to the operator immediately rather than letting it scroll past.

This mirrors the git workflow the [[Development Guide]] already mandates (worktree → branch → PR → merge). The rule was never missing; this command simply had no way to notice it was breaking it.

### 2d. Scope the commit — explicit pathspec, never `git add .`

`git add .` stages **everything** dirty in the tree, not just the change you were asked to commit. Repos routinely carry unrelated work-in-progress — a half-edited sibling command, an untracked scratch dir, another session's files. Sweeping those into your commit is silent and hard to undo once pushed.

Before every commit, determine `$CHANGED_PATHS` — the paths belonging to THIS change:

```bash
cd $PROJECT_DIR && git status --porcelain
```

- Everything dirty is part of this change → `$CHANGED_PATHS` may be `.`, but write it deliberately, not by default.
- Anything dirty is unrelated → `$CHANGED_PATHS` lists **only** your paths. Directories are fine (`pkg/`, `commands/`); no need to enumerate every file.

Pathspec placement matters: `git commit -m "msg" -- <paths>` works, `git commit -- <paths> -m "msg"` fails with `did not match any file(s) known to git`.

`git add <paths>` alone is NOT sufficient — a later bare `git commit` still commits whatever was already staged. The `--` pathspec on the commit itself is what bounds it.

**Untracked files must be `git add`-ed first.** A commit pathspec matches only paths git already knows, so a brand-new file is rejected outright — `error: pathspec '<file>' did not match any file(s) known to git` — and the whole commit fails. This hits every commit that introduces a new file, which is most feature work. It reads like a contradiction of the line above; it is not. Both hold: `git add` is required to make a new path commit-able, and the `--` pathspec is required to bound what gets committed.

Sequence when any path is untracked:

```bash
git diff --cached --name-only          # must be empty, or only yours — abort if a sibling session pre-staged something
git add <new paths>
git diff --cached --name-only          # confirm only your paths are staged
git commit -m "msg" -- <all paths>     # pathspec still bounds the commit
```

**Exception — after `git rm --cached`:** do not use a pathspec (it commits working-tree state and silently re-adds files staged for deletion). Confirm `git diff --cached --name-only` lists only the intended deletions, then run a bare `git commit`.

### 3. Detect Pipeline-Only Changes

A change is **pipeline-only** if ALL changed/added/deleted files (committed since last tag + uncommitted) are inside these directories:
- `prompts/` (including `prompts/in-progress/`, `prompts/completed/`, `prompts/log/`)
- `specs/` (including `specs/in-progress/`, `specs/completed/`, `specs/log/`)

```bash
# Check uncommitted changes
git status --porcelain | awk '{print $2}'
# Check committed changes since last tag
git diff --name-only $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~100")..HEAD
```

If EVERY file path starts with `prompts/` or `specs/`, this is pipeline-only → route to Workflow E.

**Rationale:** Prompts and specs are dark-factory runtime state (queued work, daemon inboxes). They don't warrant a version bump or changelog entry. **Scenarios are NOT pipeline metadata** even when they live next to prompts/specs — they're shipped acceptance contracts that users (or operators) invoke via `/dark-factory:run-scenario` to validate behavior. A new scenario adds a new acceptance contract to the project's surface; that IS a versioned change and belongs in the changelog. Treat `scenarios/` the same as `docs/` or `rules/` — release-relevant content, not pipeline state.

### 4. Detect Trivial Changes

**IMPORTANT**: Check ALL changes since the last tag, not just uncommitted changes:

```bash
# Check all changes since last tag (commits + uncommitted)
git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~100")..HEAD
git diff HEAD  # or git diff --staged if changes are staged
```

A change is **trivial** if ALL modified lines (additions and deletions) match one or more of:
- Comment-only lines: lines where the non-whitespace content starts with `//`, `#`, `*`, `/*`, `*/`
- Blank/whitespace-only lines
- Lines containing only TODO, FIXME, HACK, NOTE, or XXX annotations (with or without surrounding comment syntax)

A change is **NOT trivial** if any modified line contains functional code (variable assignments, function calls, control flow, type definitions, imports, etc.).

**CRITICAL**: If there are commits since the last tag that contain functional code, the change is NOT trivial — even if the current uncommitted diff is trivial.

### 5. Route to Appropriate Workflow

```
IF changes are pipeline-only (only prompts/, specs/, scenarios/):
  → Workflow E (Pipeline-only — commit and push, skip changelog)
ELSE IF changes are trivial (comments/whitespace/TODOs only):
  → Workflow E (Trivial — commit and push, skip changelog)
ELSE IF CHANGELOG.md exists:
  IF AUTORELEASE_BOT = true:
    → Workflow A (Add to Unreleased, NO tag — github-releaser-agent handles release)
  ELSE IF IS_MASTER = false:
    → Workflow A (Feature Branch with CHANGELOG)
  ELSE IF IS_MASTER = true AND "## Unreleased" section exists:
    → Workflow B (Master with Unreleased — manual release path)
  ELSE IF IS_MASTER = true:
    → Workflow C (Master without Unreleased - legacy)
ELSE:
  → Workflow D (No CHANGELOG - simple commit)
```

**Key rule:** `AUTORELEASE_BOT = true` short-circuits the branch check. Even on master, never rename Unreleased or tag — the agent does both.

---

#### Workflow A: Unreleased Append (Feature Branch OR maintainer-bot Auto-Release)

Adds changes to `## Unreleased` section. No version increment, no tag.

Triggered for:
- Any feature branch with `CHANGELOG.md`
- **Any branch (including master) when `.maintainer.yaml: release.autoRelease: true`** — `github-releaser-agent` will rename `## Unreleased` → `## vX.Y.Z` and tag within ~10 min of push.

**Step A.1: Pre-commit validation**
```bash
make precommit  # Skip if target doesn't exist
```

**Step A.2: Analyze ALL changes (committed + uncommitted)**
```bash
# Committed changes since branch diverged from master/main
cd $PROJECT_DIR && git log --oneline $(git merge-base HEAD master 2>/dev/null || git merge-base HEAD main 2>/dev/null || echo "HEAD~100")..HEAD
# Uncommitted changes
cd $PROJECT_DIR && git status --short
cd $PROJECT_DIR && git diff --stat
```

**Step A.3: Ensure Unreleased section exists**

Check if `## Unreleased` already exists in CHANGELOG.md:
```bash
grep -q "^## Unreleased" "$PROJECT_DIR/CHANGELOG.md"
```

If NOT found, create it by inserting `## Unreleased` after the preamble, before the first version entry:
- Find the first line matching `^## v[0-9]`
- Insert `## Unreleased\n` immediately before it
- If no version entries exist, insert after all header/preamble text

**Step A.4: Add changes to Unreleased section**

Analyze the diff and add descriptive bullet points under `## Unreleased`:
```markdown
## Unreleased
- Description of change 1
- Description of change 2
```

If Unreleased already has entries, APPEND new entries (don't overwrite existing ones).

**Step A.5: Generate commit message**

Create descriptive message by analyzing git diff output. See "Commit Message Generation Guidelines" section below.
**IMPORTANT**: Do NOT use "release version vX.Y.Z" format. Use descriptive messages like "add feature X" or "fix bug Y".

**Step A.5a: Safety check for Claude/MCP files**
```bash
UNSAFE_FILES=$(git status --porcelain | grep -E '^\?\? .*/?(\.mcp|\.claude|CLAUDE\.md)' || true)

if [ -n "$UNSAFE_FILES" ]; then
  # Use AskUserQuestion to confirm
  # "About to commit Claude/MCP configuration files. Are you sure?"
  # Options: 1. Yes, commit them  2. No, exclude them
fi
```

**Step A.6: Commit and push (NO tag)**

If `IS_MASTER=true`, run the § 2c branch-protection check first — with `autoRelease: true` this workflow runs on master, which is exactly where a bypass can happen.
```bash
# Always cd to project dir first (never use git -C)
cd $PROJECT_DIR && git commit -m "descriptive message" -- CHANGELOG.md $CHANGED_PATHS && git push
```

**NOTE**: No `git tag` command. Feature branches NEVER create tags.

---

#### Workflow B: Master Branch + CHANGELOG.md + Unreleased Section

Master branch converts `## Unreleased` to a versioned section and creates a tag.

**Step B.1: Pre-commit validation**
```bash
make precommit  # Skip if target doesn't exist
```

**Step B.2: Get current version**

Priority: Git tags are the source of truth. Only parse CHANGELOG.md if no tags exist.

```bash
# Try to get latest tag (preferred source of truth)
LATEST_TAG=$(cd $PROJECT_DIR && git describe --tags --abbrev=0 2>/dev/null)

if [ -n "$LATEST_TAG" ]; then
  CURRENT_VERSION="$LATEST_TAG"
else
  # No tag exists - parse latest version from CHANGELOG.md
  CURRENT_VERSION=$(grep -E "^## v[0-9]+\.[0-9]+\.[0-9]+" "$PROJECT_DIR/CHANGELOG.md" 2>/dev/null | head -n 1 | awk '{print $2}')

  if [ -z "$CURRENT_VERSION" ]; then
    CURRENT_VERSION="v0.0.0"  # Will be incremented to v0.1.0
  fi
fi
```

**Step B.3: Invoke `release-changelog-assistant` for bump classification**

Make sure cwd is `$PROJECT_DIR` (the agent reads `CHANGELOG.md` from cwd and extracts the `## Unreleased` block itself — no inline body passing). Then use the Task tool with the Workflow B profile (`majorBumpAllowed=false`, `rewriteChangelogEntries=false`). This preserves Workflow B's historical contract: bump is capped at `minor` (the operator must manually bump major), and bullets are NOT rewritten (pure passthrough — Workflow B keeps the sed-rename behavior).

```
cd $PROJECT_DIR
Task(
  subagent_type="coding:release-changelog-assistant",
  prompt="""
    current_version: $CURRENT_VERSION
    majorBumpAllowed: false
    rewriteChangelogEntries: false
  """
)
```

Parse the returned JSON. Check for `error` field first; abort with the error message if present. Otherwise use the `bump` field to compute the next version:

- From `v0.3.3`: patch → `v0.3.4`, minor → `v0.4.0`
- If no previous version: start with `v0.1.0`

The `rewritten_unreleased` field will be empty (per the flag profile) — discard it. The `unreleased_body` and `reasoning` fields are informational for the operator log.

**Why these flags:** Workflow B is the operator's "I'm releasing manually right now" path. `majorBumpAllowed=false` matches the legacy "major requires manual edit" rule (preserved verbatim from the pre-agent Version Increment Rules below). `rewriteChangelogEntries=false` keeps Workflow B fast and offline — no rewrite call. For full AI rewrite + faithfulness review, use `/coding:github-release` instead (which sets both flags `true`).

**Step B.4: Rename Unreleased to version**

Replace `## Unreleased` with `## vX.Y.Z` in CHANGELOG.md:
```bash
# Example: sed 's/^## Unreleased$/## v0.14.8/' CHANGELOG.md
```

Use the Edit tool to replace `## Unreleased` with `## vX.Y.Z` (preferred over sed).

**Step B.5: Generate commit message**

Format: `release vX.Y.Z` (this IS a release commit on master).

**Step B.5a: Safety check for Claude/MCP files**
```bash
UNSAFE_FILES=$(git status --porcelain | grep -E '^\?\? .*/?(\.mcp|\.claude|CLAUDE\.md)' || true)

if [ -n "$UNSAFE_FILES" ]; then
  # Use AskUserQuestion to confirm
fi
```

**Step B.6: Commit, tag, and push**

Run the § 2c branch-protection check first — this workflow is master-only.
```bash
cd $PROJECT_DIR && git commit -m "release vX.Y.Z" -- CHANGELOG.md $CHANGED_PATHS && git tag vX.Y.Z && git push && git push origin vX.Y.Z
```

---

#### Workflow C: Master Branch + CHANGELOG.md (No Unreleased) - Legacy

Fallback for master branch when no `## Unreleased` section exists. Preserves backward compatibility.

**Step C.1: Pre-commit validation**
```bash
make precommit  # Skip if target doesn't exist
```

**Step C.2: Get current version**

Priority: Git tags are the source of truth. Only parse CHANGELOG.md if no tags exist.

```bash
LATEST_TAG=$(cd $PROJECT_DIR && git describe --tags --abbrev=0 2>/dev/null)

if [ -n "$LATEST_TAG" ]; then
  CURRENT_VERSION="$LATEST_TAG"
else
  CURRENT_VERSION=$(grep -E "^## v[0-9]+\.[0-9]+\.[0-9]+" "$PROJECT_DIR/CHANGELOG.md" 2>/dev/null | head -n 1 | awk '{print $2}')

  if [ -z "$CURRENT_VERSION" ]; then
    CURRENT_VERSION="v0.0.0"
  fi
fi
```

**Version Validation:**
```bash
if ! grep -qE "^## v[0-9]+\.[0-9]+\.[0-9]+" "$PROJECT_DIR/CHANGELOG.md" 2>/dev/null; then
  echo "Error: CHANGELOG.md exists but contains no valid version entries"
  echo "Expected format: ## vX.Y.Z (e.g., ## v0.3.3)"
  exit 1
fi
```

**Step C.3: Analyze ALL changes since last release**

IMPORTANT: Analyze both committed AND uncommitted changes since last tag. The changelog must cover everything since the last release, not just the current working directory diff.

```bash
# Always check committed changes since last tag (this is the PRIMARY source)
cd $PROJECT_DIR && git log --oneline $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~100")..HEAD
cd $PROJECT_DIR && git diff $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~100")..HEAD --stat

# Also check uncommitted changes
cd $PROJECT_DIR && git status --short
cd $PROJECT_DIR && git diff --stat
```

**The changelog entries come from `git log <last-tag>..HEAD`** — not from `git diff` of uncommitted changes. Uncommitted changes are included in the commit but the changelog describes all work since last release.

**Step C.4: Determine version increment**

Analyze changes to determine increment type (see "Version Increment Rules" section below).

Calculate new version:
- From `v0.3.3`: patch -> `v0.3.4`, minor -> `v0.4.0`
- If no previous version: start with `v0.1.0`

**Step C.5: Generate commit message**

Create descriptive message by analyzing git diff output (NOT "release version vX.Y.Z"). See "Commit Message Generation Guidelines" section below.

**Step C.6: Update CHANGELOG.md**

Insert new version section after the header, before existing versions:
```markdown
## vX.Y.Z
- Description of change 1
- Description of change 2
- Description of change 3
```

Maintain existing format:
- Version header: `## vX.Y.Z` (no date)
- Bullet points: `- Change description`
- Descending order (newest first)

**Step C.6a: Safety check for Claude/MCP files**
```bash
UNSAFE_FILES=$(git status --porcelain | grep -E '^\?\? .*/?(\.mcp|\.claude|CLAUDE\.md)' || true)

if [ -n "$UNSAFE_FILES" ]; then
  # Use AskUserQuestion to confirm
fi
```

**Step C.7: Commit, tag, and push**

Run the § 2c branch-protection check first — this workflow is master-only.
```bash
cd $PROJECT_DIR && git commit -m "descriptive message" -- CHANGELOG.md $CHANGED_PATHS && git tag vX.Y.Z && git push && git push origin vX.Y.Z
```

---

#### Workflow D: WITHOUT CHANGELOG.md

**Step D.1: Pre-commit validation**
```bash
make precommit  # Skip if target doesn't exist
```

**Step D.2: Analyze changes**
```bash
git status
git diff --staged
git diff --stat
```

**Step D.3: Generate commit message**

Create descriptive message by analyzing git diff output. See "Commit Message Generation Guidelines" section below.

**Step D.3a: Safety check for Claude/MCP files**
```bash
UNSAFE_FILES=$(git status --porcelain | grep -E '^\?\? .*/?(\.mcp|\.claude|CLAUDE\.md)' || true)

if [ -n "$UNSAFE_FILES" ]; then
  # Use AskUserQuestion to confirm
fi
```

**Step D.4: Commit and push**

If `IS_MASTER=true`, run the § 2c branch-protection check first.
```bash
cd $PROJECT_DIR && git commit -m "descriptive message" -- $CHANGED_PATHS && git push
```

#### Workflow E: Trivial or Pipeline-Only Change (any branch, any project)

For changes that are purely comments, whitespace, or TODO/FIXME annotations — OR changes that only touch `prompts/`, `specs/`, or `scenarios/` directories. No CHANGELOG update, no version bump, no tag.

**Step E.1: Pre-commit validation**
```bash
make precommit  # Skip if target doesn't exist
```

**Step E.2: Safety check for Claude/MCP files**
```bash
UNSAFE_FILES=$(git status --porcelain | grep -E '^\?\? .*/?(\.mcp|\.claude|CLAUDE\.md)' || true)

if [ -n "$UNSAFE_FILES" ]; then
  # Use AskUserQuestion to confirm
fi
```

**Step E.3: Commit and push (NO changelog update, NO tag)**

If `IS_MASTER=true`, run the § 2c branch-protection check first — a trivial change still bypasses required checks.
```bash
cd $PROJECT_DIR && git commit -m "descriptive message" -- $CHANGED_PATHS && git push
```

---

## Commit Message Generation Guidelines

Create descriptive commit messages by analyzing git diff output:

**Process:**
1. Analyze `git diff` and `git status` output
2. Identify primary type of changes:
   - New files -> "add [feature/component]"
   - Modified existing -> "improve/update/fix [component]"
   - Deleted files -> "remove [component]"
   - Documentation -> "update documentation for [topic]"
3. Generate 1-2 line summary in imperative mood
4. Template: `<action> <what> [optional: context]`

**Examples:**
- "add fluent API for metric configuration"
- "fix memory leak in connection pool"
- "improve error handling and add retry logic"
- "update documentation with usage examples"
- "refactor authentication flow for clarity"
- "add support for custom timeout configuration"
- "remove deprecated API endpoints"

**Key principles:**
- Use imperative mood (add/fix/improve, not added/fixed/improved)
- Focus on WHAT changed and WHY (not HOW it was implemented)
- Keep under 72 characters if possible
- Be specific but concise
- **NEVER** add Claude attribution (no "Generated with Claude Code", no "Co-Authored-By")

## Version Increment Rules

When CHANGELOG.md exists, use these rules to determine version increment:

- **Patch (x.y.Z)**:
  - Bug fixes
  - Documentation updates
  - Code cleanup/refactoring
  - Minor improvements
  - Performance optimizations (non-breaking)

- **Minor (x.Y.0)**:
  - New features
  - API additions (backward compatible)
  - Significant enhancements
  - New functionality

- **Major (X.0.0)**:
  - Breaking changes
  - API removals/modifications
  - Requires manual version specification (not auto-detected)

## CHANGELOG.md Format

The command maintains the user's changelog format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## Unreleased
- Changes not yet released
- Another pending change

## v0.3.4
- Add new feature description
- Fix bug description
- Improve something description

## v0.3.3
- Previous version changes...
```

## Error Handling

- **No make precommit target**: Continue without running pre-commit checks (not all projects have this)

- **No previous tags + CHANGELOG exists**: Parse latest version from CHANGELOG.md, or start with v0.1.0 if no versions found

- **Malformed CHANGELOG**: Report error and abort if:
  - CHANGELOG.md exists but contains no version entries matching `^## v[0-9]+\.[0-9]+\.[0-9]+` AND no `## Unreleased` section
  - Example error: "CHANGELOG.md exists but contains no valid version entries. Expected format: ## vX.Y.Z (e.g., ## v0.3.3)"
  - Exception: A CHANGELOG with only `## Unreleased` and no versions is valid (new project)

- **No changes to commit**:
  - Check `git status --porcelain` output
  - If empty: Report "No changes to commit" and abort
  - Don't create empty commits

- **Push fails**:
  - Report error with failure message
  - Note: Tags and commits already created locally
  - User can retry with `git push && git push origin <tag>`

- **Version increment ambiguous**:
  - If unable to determine patch vs minor, default to patch increment
  - Report: "Defaulting to patch increment (X.Y.Z+1). For minor increment, manually edit CHANGELOG.md first."

- **Unreleased section empty on master**:
  - If `## Unreleased` exists but has no entries, warn and abort
  - "Unreleased section is empty. Add change descriptions before releasing."

- **CHANGELOG insert location for Unreleased**:
  - Find first occurrence of `^## v[0-9]` pattern
  - Insert `## Unreleased` immediately before it
  - If no previous versions found, insert after all header/preamble text

## Examples

### Feature branch with CHANGELOG.md
```bash
# On branch feature/add-metrics
/commit ~/Documents/workspaces/metrics
```
Result: Adds changes to `## Unreleased` section, commits with "add metric configuration API", pushes. No tag created.

### Master branch with Unreleased section
```bash
# On master, after merging feature branches
/commit ~/Documents/workspaces/metrics
```
Result: Converts `## Unreleased` to `## v0.3.4`, commits with "release v0.3.4", creates tag v0.3.4, pushes both.

### Master branch with `.maintainer.yaml: release.autoRelease: true`
```bash
# On master, .maintainer.yaml opts into bot release
/commit ~/Documents/workspaces/vault-cli
```
Result: Adds changes under `## Unreleased`, commits with descriptive message, pushes. **No tag created** — `github-releaser-agent` watcher picks up the `## Unreleased` block within ~10 min and tags `vX.Y.Z` autonomously. See [[GitHub Auto-Release Guide]].

### Master branch without Unreleased (legacy)
```bash
# On master, direct changes without Unreleased workflow
/commit ~/Documents/workspaces/metrics
```
Result: Creates new version section `## v0.3.4`, commits with descriptive message, creates tag v0.3.4, pushes both.

### Project without CHANGELOG.md
```bash
/commit
```
Result: Analyzes changes, commits with descriptive message, pushes (no tag created).

### Pipeline-only change (prompts/specs/scenarios)
```bash
# Added or updated a dark-factory prompt
/commit ~/Documents/workspaces/dark-factory
```
Result: Detects all files in prompts/specs/scenarios only, commits with "add prompt for feature X", pushes. No CHANGELOG update, no version bump, no tag.

### Trivial change (comments/TODOs only)
```bash
/commit
```
Result: Detects only comment/whitespace changes, commits with descriptive message, pushes. CHANGELOG.md untouched, no version bump, no tag.

## Merge Conflict Resolution

### Unreleased Section Conflicts

When multiple feature branches add entries to `## Unreleased`, merge conflicts are expected and simple to resolve:

**Conflict pattern:**
```markdown
## Unreleased
<<<<<<< HEAD
- Feature A change
=======
- Feature B change
>>>>>>> feature-b
```

**Resolution:**
```markdown
## Unreleased
- Feature A change
- Feature B change
```

**Process:**
1. Keep both sets of changes (no deletions needed)
2. Maintain bullet list format (`- Description`)
3. Order doesn't matter (all will be versioned together on master)
4. Remove conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)

**Prevention**: Not needed - these conflicts are safe and part of normal workflow.

## Notes

- All git write operations are chained with `&&` for single approval
- Tags are ONLY created on master/main branch (never on feature branches)
- Feature branches use `## Unreleased` section to collect changes
- Multiple feature branches can safely add to `## Unreleased` (merge conflicts are simple to resolve)
- Version numbers are assigned only at release time on master/main
- Commit messages are always descriptive, never generic
- Automatically adapts to project structure and branch context
- For breaking changes (major version), manually edit CHANGELOG.md first
- **IMPORTANT**: Always use `cd $PROJECT_DIR && git ...` instead of `git -C $PROJECT_DIR ...` to avoid permission prompts
