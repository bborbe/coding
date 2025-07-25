# Git Commit Workflow

This document defines the git workflow for both feature branch development and main branch releases.

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
