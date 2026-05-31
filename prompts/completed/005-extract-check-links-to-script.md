---
status: completed
summary: Extracted check-links shell logic from Makefile into scripts/check-links.sh; reduced Makefile target to one-liner
container: coding-rule-base-pilot-exec-005-extract-check-links-to-script
dark-factory-version: v0.173.0
created: "2026-05-31T20:13:44Z"
queued: "2026-05-31T20:16:15Z"
started: "2026-05-31T20:16:16Z"
completed: "2026-05-31T20:17:14Z"
---

<summary>
- Extract the multi-line shell logic embedded in the Makefile's `check-links` target into a standalone `scripts/check-links.sh`
- Mirror the conventions of the existing `scripts/check-versions.sh` (header block, `set -euo pipefail`, repo-root compute, exit 0/1)
- Reduce the Makefile's `check-links` target to a one-line `@bash scripts/check-links.sh` invocation
- Same behavior end-to-end — no functional change, only a refactor
- Enables `shellcheck` to lint the link-check logic (Makefile-embedded shell is not linted)
</summary>

<objective>
Move the inline shell logic from the Makefile's `check-links` target into a standalone executable script `scripts/check-links.sh`, following the convention already established by `scripts/check-versions.sh`. The Makefile target then becomes a one-liner that invokes the script. No behavioral change.
</objective>

<context>
Read `CLAUDE.md` for project conventions.
Read `Makefile` — focus on the `check-links` target (lines 10–25). Note the existing `check-versions` target (lines 34–36) which already follows the pattern this prompt extends to `check-links`.
Read `scripts/check-versions.sh` — the conventions reference. Match its header-block style (purpose, exit semantics, repo-root compute from script location, `set -euo pipefail`, sectioned bash with `report` helper).
Note: `make precommit` chains `check-links check-json` (line 4). Behavior of `make precommit` and `make check-links` must be unchanged by this prompt.
</context>

<requirements>
1. Create the file `scripts/check-links.sh` as an executable bash script.
2. Begin with a header comment block (≥6 lines) in the style of `scripts/check-versions.sh`. Include:
   - Purpose (validates markdown links in README.md and llms.txt point to files that exist)
   - Exit semantics (0 on all links OK, 1 on any broken link)
   - Files checked (`README.md`, `llms.txt`)
   - How repo root is computed (from script's own location via `dirname "$0"`)
   - Note that it is invoked from the Makefile `check-links` target
3. Use `#!/usr/bin/env bash` shebang and `set -euo pipefail` immediately after the header (mirrors `check-versions.sh`).
4. Compute repo root as `ROOT=$(cd "$(dirname "$0")/.." && pwd)` and `cd "$ROOT"` (same pattern as `check-versions.sh`).
5. Port the existing Makefile `check-links` shell logic verbatim — same files scanned, same `grep -oP '\]\(\K[^)]+'` extraction, same `http`/`mailto:` exclusions, same `${link%%#*}` anchor stripping, same `[ -z ... ] && continue` empty-target skip, same `BROKEN: <file> -> <link>` output format, same `All links OK` success message, same exit code semantics. The behavior must be byte-identical to the current Makefile.
6. Make the script executable (`chmod +x scripts/check-links.sh` — set by the agent before completion).
7. Edit `Makefile`: replace the entire body of the `check-links` target (lines 10–25, everything from `.PHONY: check-links` is unchanged, but the recipe lines `@echo ...; @EXIT=0; ...; echo "All links OK"`) with a single recipe line `@bash scripts/check-links.sh`. The `.PHONY: check-links` declaration stays. The new shape mirrors `check-versions`:
   ```makefile
   .PHONY: check-links
   check-links:
   	@bash scripts/check-links.sh
   ```
8. Do NOT modify any other Makefile target — `precommit`, `release-check`, `check-json`, `check-versions`, `build-index` stay exactly as they are.
9. Do NOT modify any other file outside `Makefile` and `scripts/check-links.sh`.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git
- Do NOT change the behavior of `make precommit` or `make check-links` (verified by re-running both)
- Do NOT touch `check-json`, `check-versions`, or `build-index` targets
- Do NOT touch any markdown link or any README/llms.txt content
- No personal paths anywhere (`~/Documents/`, `/Users/`)
- Preserve existing Makefile formatting (tabs, comment style)
</constraints>

<verification>
Run the following from the repo root:
```
# Script exists and is executable
test -x scripts/check-links.sh && echo "executable: ok"

# Header has shebang + set -euo pipefail
head -2 scripts/check-links.sh | grep -q '^#!/usr/bin/env bash' && echo "shebang: ok"
grep -q 'set -euo pipefail' scripts/check-links.sh && echo "strict mode: ok"

# Lints clean
shellcheck scripts/check-links.sh && echo "shellcheck: ok"

# Makefile target reduced to one-liner
grep -A2 '^check-links:' Makefile
# Recipe should be: @bash scripts/check-links.sh   (single line, nothing else)

# Behavior unchanged
make check-links
# Must print "All links OK" (or list broken links) — same output as before the refactor

# Full precommit still passes
make precommit
```
</verification>
