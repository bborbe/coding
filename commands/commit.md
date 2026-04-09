---
description: Intelligent Git commit with automatic changelog/tagging detection
argument-hint: [directory]
allowed-tools:
  - Read
  - Edit
  - MultiEdit
  - Glob
  - LS
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
- **Master/main + CHANGELOG.md + Unreleased**: Converts `## Unreleased` to `## vX.Y.Z`, creates tag
- **Master/main + CHANGELOG.md (no Unreleased)**: Legacy workflow - creates version section + tag
- **No CHANGELOG.md**: Simple commit without versioning

Tags are ONLY created on master/main branch. Feature branches never create tags.

## Workflow

### Automatic Detection
1. Determine working directory
2. **Read project `CLAUDE.md`** (if present at repo root) — scan for release/commit checklists, extra files to bump, and project-specific rules. Common sections: "Release Checklist", "Plugin Release Checklist", "Publishing", "Version Bump". If a checklist lists extra files (e.g. `.claude-plugin/plugin.json`, `package.json`, `pyproject.toml`, `Cargo.toml`), treat them as mandatory parts of any release commit and bump their version string to match the new `vX.Y.Z`.
3. Detect current branch (master/main vs feature)
4. Check if `CHANGELOG.md` exists
5. Check for `## Unreleased` section
6. **Detect pipeline-only changes** (only prompts/, specs/, scenarios/)
7. **Detect trivial changes** (comments, whitespace, TODOs only)
8. Route to appropriate workflow

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
3. Analyze Unreleased changes to determine increment (patch/minor)
4. Calculate new version
5. Rename `## Unreleased` to `## vX.Y.Z` in CHANGELOG.md
6. Commit with "release vX.Y.Z" message
7. Create tag and push both commits and tag

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

### 3. Detect Pipeline-Only Changes

A change is **pipeline-only** if ALL changed/added/deleted files (committed since last tag + uncommitted) are inside these directories:
- `prompts/` (including `prompts/in-progress/`, `prompts/completed/`, `prompts/log/`)
- `specs/` (including `specs/in-progress/`, `specs/completed/`, `specs/log/`)
- `scenarios/`

```bash
# Check uncommitted changes
git status --porcelain | awk '{print $2}'
# Check committed changes since last tag
git diff --name-only $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~100")..HEAD
```

If EVERY file path starts with `prompts/`, `specs/`, or `scenarios/`, this is pipeline-only → route to Workflow E.

**Rationale:** Prompts, specs, and scenarios are pipeline metadata, not code. They don't warrant a version bump or changelog entry.

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
  IF IS_MASTER = false:
    → Workflow A (Feature Branch with CHANGELOG)
  ELSE IF IS_MASTER = true AND "## Unreleased" section exists:
    → Workflow B (Master with Unreleased)
  ELSE IF IS_MASTER = true:
    → Workflow C (Master without Unreleased - legacy)
ELSE:
  → Workflow D (No CHANGELOG - simple commit)
```

---

#### Workflow A: Feature Branch WITH CHANGELOG.md

Feature branches add changes to `## Unreleased` section. No version increment, no tag.

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
```bash
# Always cd to project dir first (never use git -C)
cd $PROJECT_DIR && git add CHANGELOG.md && git add . && git commit -m "descriptive message" && git push
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

**Step B.3: Analyze Unreleased changes**

Read the content between `## Unreleased` and the next `## v` section to understand what changed.
Use these entries to determine version increment type.

**Step B.4: Determine version increment**

Analyze the Unreleased entries to determine increment type (see "Version Increment Rules" section below).

Calculate new version:
- From `v0.3.3`: patch -> `v0.3.4`, minor -> `v0.4.0`
- If no previous version: start with `v0.1.0`

**Step B.5: Rename Unreleased to version**

Replace `## Unreleased` with `## vX.Y.Z` in CHANGELOG.md:
```bash
# Example: sed 's/^## Unreleased$/## v0.14.8/' CHANGELOG.md
```

Use the Edit tool to replace `## Unreleased` with `## vX.Y.Z` (preferred over sed).

**Step B.6: Generate commit message**

Format: `release vX.Y.Z` (this IS a release commit on master).

**Step B.6a: Safety check for Claude/MCP files**
```bash
UNSAFE_FILES=$(git status --porcelain | grep -E '^\?\? .*/?(\.mcp|\.claude|CLAUDE\.md)' || true)

if [ -n "$UNSAFE_FILES" ]; then
  # Use AskUserQuestion to confirm
fi
```

**Step B.7: Commit, tag, and push**
```bash
cd $PROJECT_DIR && git add CHANGELOG.md && git add . && git commit -m "release vX.Y.Z" && git tag vX.Y.Z && git push && git push origin vX.Y.Z
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
```bash
cd $PROJECT_DIR && git add CHANGELOG.md && git add . && git commit -m "descriptive message" && git tag vX.Y.Z && git push && git push origin vX.Y.Z
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
```bash
cd $PROJECT_DIR && git add . && git commit -m "descriptive message" && git push
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
```bash
cd $PROJECT_DIR && git add . && git commit -m "descriptive message" && git push
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
