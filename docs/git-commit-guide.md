# Git Commit Guide

Comprehensive guide for git commit workflow covering feature branch development, main branch releases, commit message conventions, repository-specific requirements, and branch naming patterns.

## Rules

### RULE git-commit/imperative-mood (MUST)

**Owner**: agent-auditor
**Applies when**: a git commit message's subject line starts with a non-imperative verb form — past tense (`added`, `fixed`, `updated`), gerund (`adding`, `fixing`), or 3rd-person singular (`adds`, `fixes`, `updates`) — instead of the bare imperative form (`add`, `fix`, `update`).
**Enforcement**: judgment (PR/commit-message check; the agent reads commit subjects via `git log --format=%s` and flags non-imperative verbs against the prose `Common Imperative Verbs` table below)
**Why**: Imperative mood matches Git's own convention (every internal `git` command produces an imperative message: "Merge branch X", "Revert commit Y") so the project history reads as one consistent voice. Past-tense and gerund forms also make `git log --grep "^add"` lossy — searching for added features finds 30% of them. The bare-imperative form is one fewer keystroke, one shorter subject line, and grep-friendly.

#### Bad

```
Added user authentication endpoint
Fixing the payment processor crash
Updates README with installation steps
```

#### Good

```
add user authentication endpoint
fix payment processor crash
update README with installation steps
```

**No-AI-attribution rule lives in [git-workflow.md](git-workflow.md)** as `git-workflow/no-ai-attribution-in-commits` (canonical). This guide intentionally does not duplicate it — both would produce double-findings at PR review time, same owner (`agent-auditor`), same trigger surface. Treat the git-workflow rule as the single source of truth for AI-attribution enforcement on commits.

### RULE git-commit/subject-under-50-chars (SHOULD)

**Owner**: agent-auditor
**Applies when**: a git commit subject line exceeds 50 characters. Body lines may be longer (wrap at 72 per the broader convention) but the subject is the single line that has to fit GitHub's PR list view, `git log --oneline`, and 80-column terminals without wrapping.
**Enforcement**: `scripts/rule-checks.sh` (`git log --format=%s HEAD~10..HEAD | awk` over recent commits when `.git` present)
**Why**: GitHub truncates PR subject lines around 70 characters; terminals at 80 columns wrap awkwardly around 60+ char subjects after the SHA prefix; `git log --oneline` becomes hard to scan when every line wraps to 2-3 rows. The 50-char convention is a soft cap with operational payoff: every history-reading surface stays one line per commit.

#### Bad

```
add comprehensive user authentication endpoint with OAuth2 PKCE flow support
```

#### Good

```
add OAuth2 PKCE auth endpoint
```

### RULE git-commit/feature-branch-no-tag (MUST)

**Owner**: agent-auditor
**Applies when**: a `git tag vX.Y.Z` command runs on a feature branch (any branch that is not `master` / `main`). Tags landing on a feature branch attach to a non-canonical commit; after PR merge the master-branch merge commit lacks the tag, and `git describe` returns a misleading version.
**Enforcement**: judgment (PR/CI check; `git for-each-ref --contains <feature-branch-tip> 'refs/tags/*'` returning any tag = violation. The agent verifies the tagged commit is reachable from master, not just from the feature branch)
**Why**: Tags represent **released versions** that users consume via `git checkout vX.Y.Z` or `claude plugin install pkg@vX.Y.Z`. A tag on a feature branch points at a commit that may differ from what landed on master (rebase, squash, amendment during review), so users who fetch the tag get pre-merge code that nobody actually reviewed. Only master-branch commits — the merge commits CI tested and reviewers approved — should carry release tags. The release procedure: merge first, tag second. See [releasing-coding.md](releasing-coding.md) for the canonical [autoRelease workflow](releasing-coding.md) when `.maintainer.yaml` has `release.autoRelease: true`.

#### Bad

```bash
# On branch feature/oauth-endpoint
git add . && git commit -m "release v1.5.0" && git tag v1.5.0 && git push --tags  # WRONG: tag lives on feature commit; master will lack v1.5.0 after merge
```

#### Good

```bash
# On feature branch: just push, no tag
git push -u origin feature/oauth-endpoint
gh pr create
# After merge to master, on master:
git checkout master && git pull && git tag v1.5.0 && git push origin v1.5.0
# Or use autoRelease bot per .maintainer.yaml (preferred for bborbe repos)
```

## Commit Message Format

**Structure:**
```
<imperative verb> <description under 50 chars>

[Optional body with details]
[Reference issues: #123]
```

**Rules:**
- **Use imperative mood**: "Add feature" not "Added feature" or "Adds feature"
- **Keep first line under 50 characters**: Subject line should be concise
- **Separate subject from body**: Use blank line between subject and body
- **Reference issues/PRs when relevant**: Link to tracking issues
- **NEVER add AI attribution**: No "Generated with Claude" or similar

**Examples:**
```bash
# ✅ Good
git commit -m "add user authentication endpoint"
git commit -m "fix null pointer in payment processor"
git commit -m "update README with installation steps"

# ❌ Bad
git commit -m "Added user authentication endpoint"  # Not imperative
git commit -m "fixes"  # Not descriptive
git commit -m "Generated with Claude: add authentication"  # AI attribution
```

**Common Imperative Verbs:**
- `add` - New feature or file
- `fix` - Bug fix
- `update` - Modification to existing feature
- `remove` - Delete feature or file
- `refactor` - Code restructuring without behavior change
- `docs` - Documentation only changes
- `test` - Test additions or modifications

## Feature Branch Development

**For commits in feature branches** (non-main branches):

1. **Run pre-commit checks**: `make precommit` - ALWAYS run this first
2. **Update changelog**: Add changes to `CHANGELOG.md` with new version number - REQUIRED for all commits  
3. **Stage and commit**: `git add . && git commit -m "commit message"`
4. **NO TAGGING**: Do not tag commits in feature branches

**Critical Notes for Feature Branches**:
- Never commit without first updating the changelog
- Update CHANGELOG.md with the planned version number for tracking
- **DO NOT TAG** feature branch commits - tags should only point to main branch commits
- Version numbers in CHANGELOG.md represent planned releases, not actual releases

## Main Branch Releases

**For commits merged to main branch** (actual releases):

1. **After PR merge**: Ensure the commit is in the main or master branch
2. **Verify changelog**: Confirm CHANGELOG.md has the correct version for this release
3. **Tag the release**: `git tag v1.x.x` (use exact version from CHANGELOG.md)
4. **Push tag**: `git push origin v1.x.x`

**Critical Notes for Main Branch**:
- Only tag commits that are in the main or master branch
- Tags represent actual releases available to users
- The tag version MUST match the version in CHANGELOG.md exactly
- Tags should point to merge commits or squashed commits in main

## Workflow Summary

### Development Phase (Feature Branches)
```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes and follow feature branch workflow
make precommit
# Update CHANGELOG.md with planned version
git add .
git commit -m "implement feature X"
# NO TAGGING

# 3. Push and create PR
git push origin feature/my-feature
gh pr create
```

### Release Phase (Main Branch)
```bash
# 1. After PR is merged, checkout main
git checkout main
git pull origin main

# 2. Tag the release (only if you're the maintainer)
git tag v1.x.x  # Use version from CHANGELOG.md
git push origin v1.x.x
```

## Repository-Specific Configuration

Configuration (email, GPG key, branch naming) varies by repository context to ensure proper attribution and signing.

### Company/Organization Repositories

**Detection Patterns:**
- Internal git hosting: `git.company.com`
- Organization GitHub: `github.com/company-name`
- Enterprise Bitbucket: `bitbucket.company.com`

**Required Configuration:**
```bash
git config user.email your.name@company.com
git config user.signingkey YOUR_GPG_KEY_ID
git config commit.gpgsign true
```

**Branch Naming Pattern:** `PROJECT-12345-description`
- `PROJECT`: Issue tracker project key (e.g., `API`, `WEB`, `DB`)
- `12345`: Issue number
- `description`: Short descriptive name (lowercase, hyphens)

**Examples:**
- `API-1234-add-authentication`
- `WEB-5678-user-dashboard`
- `DB-9012-migration-script`

**Branch Ancestry Requirement:**
- Feature branches MUST be created from `origin/master`, not local `master`
- Ensures branch is based on latest remote state
- Prevents merge conflicts and outdated base branches

**Correct workflow:**
```bash
git fetch
git checkout -b API-1234-new-feature origin/master
```

**Wrong workflow:**
```bash
# ❌ DON'T DO THIS
git checkout master
git checkout -b API-1234-new-feature  # based on local master
```

**Protected Branches** (skip branch naming/ancestry validation):
- `master`
- `main`
- `staging`
- `dev`

### Personal/Open Source Repositories

**Detection Pattern:**
- Personal GitHub: `github.com/username`
- Personal GitLab: `gitlab.com/username`

**Required Configuration:**
```bash
git config user.email your.email@example.com
git config user.signingkey YOUR_GPG_KEY_ID
git config commit.gpgsign true
```

**Branch Naming:**
- No specific requirements
- Use descriptive names (e.g., `feature/user-auth`, `fix/null-pointer`)

**Branch Ancestry:**
- No specific requirements
- Can branch from local `main` or `origin/main`

## Common Validation Warnings & Troubleshooting

### Email Mismatch

**Warning:**
```
⚠️  Email: personal@gmail.com (should end with @company.com)
```

**Fix:**
```bash
git config user.email your.name@company.com
```

### GPG Key Mismatch

**Warning:**
```
⚠️  Missing or incorrect GPG signing key
    Current: PERSONAL_KEY_ID
    Expected: COMPANY_KEY_ID
```

**Fix:**
```bash
git config user.signingkey COMPANY_KEY_ID
```

### GPG Signing Not Enabled

**Warning:**
```
⚠️  GPG signing not enabled
```

**Fix:**
```bash
git config commit.gpgsign true
```

### Branch Naming Violation (Organization Repos)

**Warning:**
```
⚠️  Branch: fix-typo (should be PROJECT-12345-description)
    Example: API-1234-fix-authentication
```

**Fix:**
- Rename branch: `git branch -m API-1234-description`
- Or create new branch with correct name: `git checkout -b API-1234-fix-typo origin/master`

### Branch Ancestry Violation (Organization Repos)

**Warning:**
```
⚠️  origin/master not in branch history
    Fix: git fetch && git rebase origin/master
```

**Fix Option 1 - Rebase:**
```bash
git fetch && git rebase origin/master
```

**Fix Option 2 - Create new branch:**
```bash
git fetch && \
git checkout -b API-1234-new-branch origin/master && \
git cherry-pick <commit-range>
```

### AI Attribution in Commit Message

**Problem:**
```bash
git commit -m "add authentication \n\nGenerated with Claude"
```

**Fix:**
```bash
# Amend the last commit (if not pushed)
git commit --amend -m "add authentication"

# Or create new commit with correct message
git reset --soft HEAD~1
git commit -m "add authentication"
```

**Prevention:**
Always follow commit message format without any AI attribution.

## Quick Reference

**Feature Branch Workflow:**
```bash
# Company/organization repos
git fetch && \
git checkout -b API-1234-feature origin/master && \
make precommit && \
git add . && \
git commit -m "add new feature" && \
git push origin API-1234-feature && \
gh pr create

# Personal/open source repos
git checkout -b feature/new-feature && \
make precommit && \
git add . && \
git commit -m "add new feature" && \
git push origin feature/new-feature && \
gh pr create
```

**Main Branch Release:**
```bash
git checkout main && \
git pull origin main && \
git tag v1.x.x && \
git push origin v1.x.x
```

**Commit Message Template:**
```
<verb> <description under 50 chars>

[Optional detailed explanation]
[References: #123]
```
