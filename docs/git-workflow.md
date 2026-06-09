# Git Workflow (YOLO)

## Hard Rules

### RULE git-workflow/never-direct-commit-to-master (MUST)

**Owner**: agent-auditor
**Applies when**: a git commit lands directly on `master` / `main` without going through a feature branch + PR — typically caught by `pre-push` hook rejecting cross-name pushes to the default branch, or by GitHub's `master-protection` ruleset.
**Enforcement**: judgment + tooling (`~/.git-hooks/pre-push` rejects feature-branch-to-master pushes; GitHub ruleset enforces required PR). Release commits (`release vX.Y.Z`) are the documented exception.
**Why**: Direct-to-master commits skip review, skip CI, skip the audit trail. The 14-commits-on-origin-master trap (PR #1) happened this way: `git worktree add -b feat/foo origin/master` left upstream pointing at master so `git push` shipped to the wrong place. Hook + ruleset catch it before it happens.

#### Bad

```bash
git checkout master && git commit -m "quick fix" && git push   # no PR, no review
```

#### Good

```bash
wt-feat coding fix/payment-bug   # feature worktree + branch + push -u in one shot
git commit -m "fix: payment bug" && git push
gh pr create                      # PR triggers review + CI
```

### RULE git-workflow/no-ai-attribution-in-commits (MUST)

**Owner**: agent-auditor
**Applies when**: a git commit message body or trailer contains "Co-Authored-By: Claude", "Generated with Claude Code", "Co-Authored-By: GitHub Copilot", or any other AI-attribution line.
**Enforcement**: `scripts/rule-checks.sh` (greps `git log --format=%B HEAD~10..HEAD` for AI-attribution patterns when `.git` present)
**Why**: AI attribution inflates commit metadata noise, signals tool use rather than authorship, and makes commits look "automated" even when the human did substantive design + review work. The human + commit message together constitute the canonical history. AI is a tool; tools don't get authorship credit any more than the editor or compiler does.

#### Bad

```
add login endpoint

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Good

```
add login endpoint

Validates the OAuth token against the configured issuer, returns
the corresponding user record or 401.
```

- **NEVER commit directly to master/main**
- **NEVER add AI attribution** to commits (no "Co-Authored-By: Claude", no "Generated with Claude Code")
- **NEVER use `git -C /path`** — always `cd /path && git ...`
- **NEVER merge PRs** — YOLO creates PRs, the human merges them. Stop after `gh pr create`.
- **NEVER commit secrets**, API keys, credentials, or `.env` files
- **NEVER auto-approve or self-merge** a PR you created

## Dark Factory Projects

If `/workspace` contains `prompts/` directory (dark-factory project):

- **NEVER commit, tag, or push** — dark-factory handles all git operations after you exit
- **NEVER run `git commit`, `git tag`, `git push`**
- `make precommit` is allowed for **validation only** — it must pass, but do not commit afterward
- Just implement the changes, verify with `make test` and `make precommit`, then exit
- Dark-factory will: stage all changes, move prompt to `completed/`, commit, tag, and push

**CHANGELOG in dark-factory mode:**
- If CHANGELOG.md exists, **YOU must add entries under `## Unreleased`**
- Write meaningful descriptions of what changed (not prompt filenames)
- Dark-factory will rename `## Unreleased` → `## vX.Y.Z` at release time
- If `## Unreleased` section doesn't exist yet, create it at the top (before first `## v`)
- Example:
  ```markdown
  ## Unreleased

  - Add TextMarshaler/TextUnmarshaler to DateTime, UnixTime, Duration, TimeOfDay
  - Add comprehensive JSON and YAML struct regression tests
  ```

## Mono-Repo Warning

If the project is a **mono-repo** (multiple services under one root):

```bash
# ❌ NEVER - runs ALL subdirs, takes 10+ minutes
cd /workspace && make test
cd /workspace && make precommit

# ✅ ALWAYS - only in the changed subdir
cd /workspace/core/myservice && make test
cd /workspace/lib && make precommit
```

Detect mono-repo: multiple `go.mod` files at different levels, or `Makefile` at root with recursive targets.

## Workflow

```bash
# 1. Create branch from master
git checkout master && git pull
git checkout -b feat/<name>   # or fix/, refactor/, chore/, docs/, test/

# 2. Make changes, verify in correct directory
make precommit   # only in changed subdir if mono-repo

# 3. Review staged files before committing
git status       # check what will be added
git diff --staged  # review actual changes

# 4. Update CHANGELOG.md under ## Unreleased, then commit
git add CHANGELOG.md <specific-files>  # prefer explicit over git add .
git commit -m "add descriptive summary"

# 5. Push + PR (STOP HERE — do not merge)
git push origin feat/<name>
gh pr create --title "short title" --body "$(cat <<'EOF'
## Summary
- What changed
- Why it was needed

## Test plan
- [ ] make test passes
- [ ] manual verification done
EOF
)"
```

## Commit Message Format

```
<imperative verb> <description under 50 chars>

Optional body: explain WHAT changed and WHY (not HOW).
Wrap body at 72 chars.
```

Good verbs: `add`, `fix`, `update`, `remove`, `refactor`, `improve`

Examples:
- `add configurable vault paths per vault`
- `fix storage path for daily notes`
- `refactor list command to support all vaults`

## CHANGELOG Format

Feature branches always use `## Unreleased` — never add version numbers:

```markdown
## Unreleased

- Add configurable folder paths per vault config
- Fix daily note path resolution
```

Version numbers are assigned by the maintainer when merging to master.

**Entry style:** `- <prefix>: <What> [context]`

See `changelog-guide.md` for full format rules, prefixes (`feat:`, `fix:`, `chore:`, etc.), and examples. dark-factory reads prefixes to determine version bumps automatically.

## Branch Naming

| Prefix | Use for |
|--------|---------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `hotfix/` | Critical urgent fixes |
| `refactor/` | Code improvements |
| `docs/` | Documentation only |
| `test/` | Test additions |
| `chore/` | Maintenance |
