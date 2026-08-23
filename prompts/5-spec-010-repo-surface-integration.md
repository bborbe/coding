---
status: draft
spec: [010-security-review-command-wiring]
created: "2026-08-23T17:19:00Z"
branch: dark-factory/security-review-command-wiring
---

# Repo-surface integration: README, llms.txt alignment, agent tables, changelog

<summary>
- The README commands table and Quick Start document the new `--security` flag on all three review commands, so operators discover the mode from the plugin's front page
- The README Acceptance Scenarios table gains the four security scenario rows (007–010), linking to the scenario files landed by prompt 4
- The llms.txt index is verified to still reference both the security pipeline guide and the verifier agent — no new llms entry is required because the mode adds no new guide or agent
- The agent tables are verified unchanged: `security-verifier` stays registered, and no new agent file appears under the agents directory
- A changelog entry records the `--security` wiring under `## Unreleased`, placed above whichever version is currently the topmost released section
- The four plugin version strings stay untouched, and the full precommit (link + JSON + index + rule-test gates) stays green
</summary>

<objective>
Finish the spec's repo-surface integration: update `README.md` (commands table, Quick Start, Acceptance Scenarios rows 007–010), verify `llms.txt` and the agent tables stay aligned (the mode adds no new guide or agent), and add the `## Unreleased` changelog entry — with the plugin version strings untouched and `make precommit` green.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "Adding a new guide"/"Adding a new agent" checklists (this prompt adds neither), the "When Changing Files" cross-reference rules for README/llms/CHANGELOG, the generic-content rule, and the "Dark Factory Workflow" note that this repo's releases are manual (autoRelease false; the four version strings are touched only at release, never by prompts).

Read `README.md` (full) — the `## Quick Start` block (~lines 30–63), the `## Commands` table (~lines 65–86, rows for `/coding:pr-review`, `/coding:local-review`, `/coding:code-review`), the `## Agents` section with the `<details><summary><b>Other agents</b></summary>` table (which already contains the `security-verifier` row at ~line 273), and the `## Acceptance Scenarios` table (~lines 277–287, currently rows 001–004 only — rows 005/006 exist on disk but are intentionally not listed; do NOT backfill them, per the spec Non-goal).

Read `llms.txt` (full) — the `## Go — Testing & Quality` section currently has the Security Review Guide bullet (~line 28), the Security Review Pipeline bullet (~line 29), and the `security-verifier` bullet (~line 30); the `## Acceptance Scenarios` section lists 001–004 only. The mode adds no new guide or agent, so no new llms entry is required — this is an alignment VERIFICATION, not an addition.

Read `CHANGELOG.md` (head only) — the topmost versioned section is resolved at execution time (do NOT hardcode it: it moves with every release). There is currently no `## Unreleased` section. Insert `## Unreleased` directly above the topmost `## vX.Y.Z` line, after the frozen preamble header block.

Verify the deliverable files exist before wiring the README links: `scenarios/007-security-idor-confirmed.md`, `scenarios/008-security-idor-rejected-by-verifier.md`, `scenarios/009-security-toolchain-fail-closed.md`, `scenarios/010-security-zero-findings.md` (prompt 4's deliverables — `check-links` fails on README links to missing files).

Read `docs/changelog-guide.md` — the `## Unreleased` entry format (conventional prefix required; one bullet per logical change; the `## Unreleased` section goes directly above the highest `## vX.Y.Z`; never insert above or inside the frozen preamble).
</context>

<requirements>
1. **Record baselines FIRST.** Before making any edit, run:
   - `ls agents | sort > /tmp/df010-agents-baseline.txt` (the agent-file inventory — AC8: no new agent file)
   - `sha256sum agents/security-verifier.md agents/go-security-specialist.md > /tmp/df010-agents-frozen.sha256` (the two security agents stay byte-unchanged)
   - `sha256sum docs/selector-mode-guide.md scripts/validate-citations.sh docs/security/security-review-pipeline.md docs/security/security-review-guide.md > /tmp/df010-frozen.sha256` (the remaining frozen contract paths stay byte-unchanged — AC6/AC8 container backstop; the git diff/status guards run operator-side)
   Keep all three for the AC8 checks in `<verification>`.

2. **README commands table (AC8).** In the `## Commands` table, add the `--security` flag to the three review-command rows so the flag is discoverable:
   - `/coding:pr-review` row: append `— add \`--security\` to run the security review pipeline` (or equivalent wording naming `--security`).
   - `/coding:local-review [short\|selector\|full]` row: append `; add \`--security\` for the security review pipeline`.
   - `/coding:code-review [...]` row: append `; add \`--security\` for the security review pipeline`.
   Match the existing row formatting exactly (same column shape, no trailing whitespace). At least one of these rows (or the Quick Start addition in requirement 3) must contain the literal `--security` token.

3. **README Quick Start (AC8).** In the `## Quick Start` block, add one example line showing the mode, e.g.:
   ```
   /coding:pr-review --security        # security review mode: derived model + six trait groups + verifier gate + Security Findings report
   ```
   The line must contain the literal `--security` token.

4. **README Acceptance Scenarios table (AC8).** Add four rows to the `## Acceptance Scenarios` table, after the existing 004 row, following the exact existing row shape (`| NNN | [name](scenarios/NNN-name.md) | <one-line what-it-validates> |`):
   - 007 — `[security-idor-confirmed](scenarios/007-security-idor-confirmed.md)` — `\`--security\` review of an order app with a seeded ownership-check bypass: verifier confirms the invariant IDOR finding (counterevidence_checked populated) and blocking holds`
   - 008 — `[security-idor-rejected-by-verifier](scenarios/008-security-idor-rejected-by-verifier.md)` — `\`--security\` review of an order app guarded by a service-layer ownership check: verifier rejects the naive IDOR claim (reject_reason recorded), no finding, no blocking`
   - 009 — `[security-toolchain-fail-closed](scenarios/009-security-toolchain-fail-closed.md)` — `toolchain findings pass citation validation; invariant findings fail closed without a model; a \`--security\` deps pass surfaces a vulnerable dependency as Must-Fix, never a silent skip`
   - 010 — `[security-zero-findings](scenarios/010-security-zero-findings.md)` — `\`--security\` review of a clean generic Go app: Security Findings section with zero findings + Security Model provenance block, no blocking`
   The row for 010 must make the link target `scenarios/010-security-zero-findings.md` resolvable (check-links). Do NOT backfill rows for 005/006 (spec Non-goal: pre-existing staleness).

5. **llms.txt alignment check (AC8).** Verify (do not add): `grep -c 'security-review-pipeline' llms.txt` ≥ 1 AND `grep -c 'security-verifier' llms.txt` ≥ 1. Both are expected to already be present (the Security Review Pipeline and `security-verifier` bullets in the `## Go — Testing & Quality` section). If either is missing, restore the corresponding bullet from the current `docs/`/`agents/` content. The mode adds no new guide and no new agent, so no new llms entry is added. Do NOT edit the llms `## Acceptance Scenarios` section (prompt 4's scenarios are not listed there, matching the 005/006 precedent).

6. **Agent-table verification (AC8).** Verify (do not add): `grep -n 'security-verifier' README.md` ≥ 1 (the `Other agents` table row stays registered — it is NOT added to any Go Quality dispatch table and no command dispatch list references it). No new agent file appears under `agents/` (diff `/tmp/df010-agents-baseline.txt` against the current `ls agents` output — must be empty). The two security agent files stay byte-unchanged (`sha256sum -c /tmp/df010-agents-frozen.sha256`).

7. **CHANGELOG (repo convention).** Resolve the topmost released version at execution time — never hardcode it:
   ```bash
   grep -n -m1 '^## v' CHANGELOG.md        # the first released section, whatever it is
   grep -n -m1 '^## Unreleased' CHANGELOG.md ; echo "unreleased-exit=$?"
   ```
   If `## Unreleased` already exists (verify first; do not expect it), append the bullet to it — never create a second section. If it does not, insert `## Unreleased` immediately above the line the first `grep` reported (directly above the highest `## vX.Y.Z`, below the frozen preamble — never above or inside the preamble). Add exactly one `feat:` bullet (per `docs/changelog-guide.md`), naming the `--security` wiring, e.g.:
   ```
   ## Unreleased

   - feat: Wire the --security flag into commands/pr-review.md, commands/code-review.md, and commands/local-review.md — activating the dormant security review mode (session-derived /tmp/security-model.json, six trait groups with non-negotiable authz over-selection and deterministic invariant selection, verifier-gated emission, derived blocking, diff anchoring in PR mode / whole-repo scope in audit mode, fail-closed dependency toolchain pass, Security Findings + Security Model report sections); register the mode in README.md and finalize acceptance scenarios 007-010
   ```
   Do NOT touch the four version strings (the top `## vX.Y.Z` entry, `.claude-plugin/plugin.json` `version`, both `.claude-plugin/marketplace.json` fields).

8. **Do NOT touch** (beyond the files named above): any `commands/*.md` (wired by prompts 1–3), any `docs/*` (frozen contract + guides), `scripts/*`, `agents/*` (verification only, no edits), `rules/*`, `specs/*`, `scenarios/*` (landed by prompt 4), `CLAUDE.md`. No `### RULE` heading anywhere in your edit. Generic content only; no personal paths.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; the git-based negative guards (AC8 `git diff origin/master --stat -- agents/` and `git status --porcelain -- agents/`) run on the operator side of the spec's Verification ladder — the container forms are the baseline diff and checksum checks in requirements 1 and 6.
- Repo surfaces only: README.md, llms.txt (verification), CHANGELOG.md. No command, guide, agent, script, rule, or scenario edits.
- Acceptance Scenarios table rows: 007–010 only; do NOT backfill 005/006 (spec Non-goal — pre-existing staleness, not part of this mode).
- No new agent and no new guide: the `security-verifier` row stays in the README `Other agents` table only; llms.txt gains no new entry.
- CHANGELOG: `## Unreleased` entry with a `feat:` prefix, placed directly above the highest `## vX.Y.Z` resolved at execution time (create the section if absent); the four version strings are NOT touched (releases are manual, handled by maintainer-agent-releaser).
- Generic content only (User, Order, Product, Customer); never trading/project-specific content; no personal paths. No version-existence claims.
- Existing tests must still pass: `make precommit` (incl. `check-links`, which validates every README/llms link against an existing file) exits 0.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- AC1: repo integrity ---
make precommit    # must exit 0 (check-links validates the new scenario links against existing files)

# --- AC8: --security documented in README (commands table and/or Quick Start) ---
grep -n -- '--security' README.md                        # >= 1

# --- AC8: Acceptance Scenarios table gains the 4 security rows ---
grep -n '010-security-zero-findings' README.md           # >= 1
grep -n '007-security-idor-confirmed' README.md          # >= 1
grep -n '008-security-idor-rejected-by-verifier' README.md   # >= 1
grep -n '009-security-toolchain-fail-closed' README.md   # >= 1

# --- AC8: llms.txt stays aligned (no new entry required; both already present) ---
grep -c 'security-review-pipeline' llms.txt              # >= 1
grep -c 'security-verifier' llms.txt                     # >= 1

# --- AC8: agent tables unchanged, no new agent file ---
grep -n 'security-verifier' README.md                    # >= 1 (Other agents table)
ls agents | sort > /tmp/df010-agents-after.txt
diff -q /tmp/df010-agents-baseline.txt /tmp/df010-agents-after.txt   # must be identical (no new agent)
sha256sum -c /tmp/df010-agents-frozen.sha256             # both agents OK
sha256sum -c /tmp/df010-frozen.sha256                    # frozen contract paths unchanged

# --- Changelog ---
grep -n -m1 '^## Unreleased' CHANGELOG.md                # must return a line
grep -n -- '--security' CHANGELOG.md                     # >= 1

# --- version strings untouched (check-versions is container-safe: pure file reads, no git) ---
make check-versions                                      # must exit 0
```
</verification>

<!-- Confirmed 2026-08-23: requirement 7 (CHANGELOG `## Unreleased` `feat:` entry) is KEPT — sibling prompts 1-4 all defer the changelog to this prompt, the repo release flow expects an entry, and the four version strings stay untouched. The topmost released version is resolved at execution time (never hardcoded), following the completed-prompt 030 precedent for this repo — do not reference `v0.48.0` by name. -->
