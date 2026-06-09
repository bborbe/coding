---
tags:
  - guide
  - git
  - documentation
---

Guide for writing consistent, useful CHANGELOG.md entries in dark-factory projects.

## Goal

Produce changelog entries with conventional prefixes so dark-factory can determine the version bump automatically — no guessing from prose.

## File Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## Unreleased

- feat: Add SpecWatcher to monitor specs/ for approved status changes
- fix: Remove stale Docker container before starting a new executor run

## v1.5.0

- feat: Add FuncRunner interface for executing functions with custom behavior
- fix: Fix WaiterUntil to handle equal times correctly
```

### RULE changelog/preamble-frozen (MUST)

**Owner**: agent-auditor
**Applies when**: a CHANGELOG.md edit inserts content above the `# Changelog` title, modifies the SemVer preamble bullets (MAJOR/MINOR/PATCH), or places a `## Unreleased` / `## vX.Y.Z` section inside (rather than after) the preamble block.
**Enforcement**: `scripts/rule-checks.sh` (checks `# Changelog` is first content; flags any `## Unreleased`/`## vX.Y.Z` before the preamble block)
**Why**: The preamble is the API contract between the changelog and every tool that parses it (dark-factory's version-bump detector, /coding:commit's CHANGELOG validator, downstream release-notes generators). Moving / deleting / shifting it breaks the parsers silently — the next release attempt either bumps the wrong version or misses entries entirely. Restoring is cheap; preventing the edit is cheaper.

#### Bad

```markdown
## Unreleased
- feat: new thing

# Changelog                          ← preamble shoved below
All notable changes...
```

#### Good

```markdown
# Changelog
All notable changes to this project will be documented in this file.
Please choose versions by [Semantic Versioning](http://semver.org/).
* MAJOR / MINOR / PATCH bullets here

## Unreleased
- feat: new thing
```

**Rules:**
- Preamble with SemVer explanation always present
- **Header is frozen**: everything from the start of the file to the FIRST `##` heading (the `# Changelog` title, the "All notable changes..." line, the SemVer link, and the MAJOR/MINOR/PATCH bullets) MUST NOT be moved, deleted, or have anything inserted above or inside it. Insert `## Unreleased` (or any version section) immediately AFTER the last header line — never before any header line. If the header is incomplete, restore it; never leave it partial.
- `## Unreleased` on feature branches — never a version number
- `## vX.Y.Z` on master — no date suffix
- Newest version first — `## Unreleased` goes directly above the highest `## vX.Y.Z`
- Flat list — no `### Added` / `### Fixed` categories

## Conventional Prefixes (REQUIRED)

### RULE changelog/conventional-prefix-required (MUST)

**Owner**: agent-auditor
**Applies when**: a bullet under `## Unreleased` in CHANGELOG.md does not start with one of the recognised conventional prefixes (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `perf:`).
**Enforcement**: judgment (regex over `## Unreleased` bullets: `^- ([a-z]+:)` first token must be in the allowed prefix set)
**Why**: dark-factory and `/coding:commit` parse the prefix to decide the version bump automatically — any `feat:` entry triggers a minor bump, everything else triggers a patch. Missing or wrong prefix means the version-bump detection fails: the release may patch-bump a feature commit (downstream consumers miss the new functionality in their range queries) or minor-bump a chore. Standardising the prefix is the cheapest possible structure for unambiguous machine parsing.

#### Bad

```markdown
## Unreleased
- Add SpecWatcher                    ← no prefix
- update go and deps                 ← no prefix
- fix and refactor                   ← ambiguous; multiple prefixes
```

#### Good

```markdown
## Unreleased
- feat: Add SpecWatcher to monitor specs/ for approved status changes
- chore: Update Go from 1.25.5 to 1.26.0
- refactor: Extract worktree cleanup to reduce cognitive complexity
```

Every `## Unreleased` entry must start with a conventional prefix:

| Prefix | Meaning | Version bump |
|--------|---------|-------------|
| `feat:` | New feature or capability | **Minor** (`vX.Y+1.0`) |
| `fix:` | Bug fix | Patch |
| `refactor:` | Code restructure, no behavior change | Patch |
| `test:` | Test additions or improvements | Patch |
| `docs:` | Documentation only | Patch |
| `chore:` | Dependency updates, build, tooling | Patch |
| `perf:` | Performance improvement | Patch |

dark-factory reads these prefixes to determine the version bump automatically. Any `feat:` entry → minor bump; everything else → patch bump.

## Entry Style

**Format:** `- <prefix>: <what> [context]`

**Be specific:**
- Name the exact type, function, command, or package touched
- Include versions for dependency updates
- Add brief context for non-obvious changes

## Anti-Patterns

❌ `- Add SpecWatcher` — missing prefix, bump detection fails
✅ `- feat: Add SpecWatcher to monitor specs/ for approved status changes`

❌ `- feat: update go and deps` — wrong prefix (chore), and too vague
✅ `- chore: Update Go from 1.25.5 to 1.26.0`
✅ `- chore: Update github.com/bborbe/errors to v1.5.2`

❌ `- fix: refactor` — what was refactored?
✅ `- refactor: Extract worktree cleanup to reduce cognitive complexity`

❌ `- test: add tests` — for what?
✅ `- test: Add processor test suite covering retry and failure paths (12 tests)`

❌ `- fix: fix bug` — which bug?
✅ `- fix: Fix NormalizeFilenames number conflict on non-standard filename format`

## Merge Conflicts in Unreleased

Multiple feature branches writing to `## Unreleased` will conflict. Resolution: keep both bullet lists, remove conflict markers.

```markdown
## Unreleased
- feat: Add SpecWatcher
- fix: Remove stale container before run
```

## Validation

- [ ] Every `## Unreleased` entry has a conventional prefix (`feat:`, `fix:`, etc.)
- [ ] `feat:` used only for genuine new features/capabilities
- [ ] Descriptions are specific — name types, functions, commands
- [ ] Dependency updates use `chore:` and include version numbers
- [ ] No vague entries (`fix: fix bug`, `chore: update deps`)
- [ ] Preamble present with SemVer link
- [ ] Newest version at top
