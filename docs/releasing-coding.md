# Releasing coding

How to ship a new version of the `coding` plugin. Mandatory reading before tagging or bumping plugin JSONs.

## One surface, one version stream

Unlike `vault-cli` / `dark-factory` / `semantic-search` which ship both a binary and a plugin, `coding` is **plugin-only**: docs + commands + agents + skills, distributed via the Claude Code marketplace. There is no Go or Python binary.

| Surface | Versioned by | Consumed by | Bumped how |
|---------|--------------|-------------|------------|
| **Plugin** | `CHANGELOG.md` top entry + `.claude-plugin/plugin.json` `version` + `.claude-plugin/marketplace.json` (`metadata.version` AND `plugins[0].version`) | Claude Code via the marketplace | Manual — operator bumps the four fields together |

## 🚨 Version alignment — locked at release time only

All four version strings MUST equal each other **at release time**:

1. `CHANGELOG.md` — top `## vX.Y.Z` entry
2. `.claude-plugin/plugin.json` — `"version"`
3. `.claude-plugin/marketplace.json` — `metadata.version`
4. `.claude-plugin/marketplace.json` — `plugins[0].version`

The check is **release-time only** — `make precommit` does NOT run it.

**Why not in `precommit`**: every refactor commit would otherwise have to bump plugin JSONs in lockstep, burning release numbers on internal work. Drift during development is fine; alignment is enforced when versions are bumped for a release. (Same lesson `dark-factory`, `vault-cli`, and `semantic-search` apply.)

## The release gate (run BEFORE every plugin bump)

`make precommit` is the development gate (link check + JSON syntax). It does NOT cover real Claude Code load, slash-command surfaces, or marketplace ingestion.

Until a `scenarios/` regression suite exists, the operator must manually exercise:

- Reload Claude Code with the plugin source mounted; verify `commands/`, `agents/`, `skills/` load without errors
- Smoke-test at least one slash command (e.g. `/coding:local-review`) end-to-end
- Inspect any new docs added under `docs/` for broken cross-references not caught by `check-links`

If any check fails, fix before tagging.

## Version alignment check (release-time)

`scripts/check-versions.sh` enforces the locked model. Run via `make check-versions`, or via `make release-check` (which adds `make precommit` first).

```bash
make release-check          # full gate: precommit + check-versions
# or, just the version check:
make check-versions
# or directly:
bash scripts/check-versions.sh
```

**NOT wired into `make precommit`** — see "Version alignment" above for why.

## Release procedure

1. **Land all changes** for the release on `master`.
2. **Pick the next version.** Increment per SemVer based on what changed (patch for fixes, minor for new commands/agents/skills, major for breaking).
3. **Update all four version fields** to the new value (no `v` prefix in JSON):
   - `.claude-plugin/plugin.json` `"version"`
   - `.claude-plugin/marketplace.json` `metadata.version`
   - `.claude-plugin/marketplace.json` `plugins[0].version`
   - Add a `## vX.Y.Z` section at the top of `CHANGELOG.md` summarising every change since the previous tag
4. **Run `make release-check`** — must pass `precommit` AND `check-versions`.
5. **Commit:** `git commit -am "release vX.Y.Z: <summary>"`.
6. **Tag and push:**

   ```bash
   git tag vX.Y.Z
   git push && git push --tags
   ```

7. **Verify:** the marketplace re-checks periodically; new sessions load the bumped plugin automatically.

### Common release mistakes

- Forgetting one of the three `.claude-plugin/` JSON fields. The marketplace rejects mismatches silently and refuses to load the plugin.
- Creating a separate "Plugin vX" CHANGELOG section. Wrong — there is one CHANGELOG.
- Bumping versions BEFORE running the release gate. Surface changes that ship in the same release escape the manual smoke check.

## See also

- `CLAUDE.md` § "Version Alignment — MANDATORY"
- `CHANGELOG.md` — historical record + top entry as the version source-of-truth
- `scripts/check-versions.sh` — script behind `make check-versions`
