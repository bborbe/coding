# Definition of Done

After completing your implementation, review your own changes against each criterion below. These are quality checks you perform by inspecting your work — not commands to run (linting and tests already ran via `validationCommand`). Report any unmet criterion as a blocker.

## Rule Base Structure

- Every changed `docs/*.md` MUST/SHOULD section has `### RULE <id> (MUST|SHOULD|MAY)` blocks
- Each rule block carries `Owner:` (single agent name from `agents/`), `Applies when:`, `Enforcement:` fields
- Every `Enforcement: rules/<lang>/<file>.yml` path resolves to an existing ast-grep file
- `make build-index` runs clean; `rules/index.json` reflects changes

## Plugin Conventions

- Generic examples only (User, Order, Product, Customer) — no trading-domain content
- No personal paths (`~/Documents/`, `/Users/bborbe/`) anywhere
- All agent references in commands use `coding:` prefix
- New doc or agent → README.md tables + llms.txt updated
- Doc ↔ Agent alignment table in CLAUDE.md updated if applicable

## Documentation

- CHANGELOG.md has an entry under `## Unreleased`
- 4-version alignment NOT touched (releases are manual, handled by maintainer-agent-releaser)
