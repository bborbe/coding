# Git Commit Workflow

**IMPORTANT**: When committing changes, follow these steps in order:

1. **Run pre-commit checks**: `make precommit` - ALWAYS run this first
2. **Update changelog**: Add changes to `CHANGELOG.md` with new version number - REQUIRED for all commits
3. **Stage and commit**: `git add . && git commit -m "commit message"`
4. **Tag version**: `git tag v1.x.x` (follow semantic versioning) - REQUIRED, use exact version from changelog

**Critical Notes**:
- Never commit without first updating the changelog
- ALWAYS tag the commit with the version number from the changelog
- The tag version MUST match the version in CHANGELOG.md exactly
