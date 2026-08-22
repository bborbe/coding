---
status: approved
spec: [007-security-rule-base]
created: "2026-08-22T23:25:00Z"
queued: "2026-08-22T21:36:42Z"
branch: dark-factory/security-rule-base
---

<summary>
- Registers `docs/security/security-review-guide.md` in the repo's "Adding a new guide" integration points: a table row in `README.md`, a bullet in `llms.txt`, and a source-of-truth companion-guide mention in `agents/go-security-specialist.md`
- Adds the guide to the security-specialist agent's Source of truth list alongside `go-security-linting.md` and `teamvault-conventions.md`, so the owner agent resolves its 5 new `go-security/*` rules from this guide
- Verifies the guide contains exactly the five mechanical detectors, with no draft markers, no personal file paths, and none of the deferred judgment/invariant-tier rules
- `make precommit` exits 0 at the end — the new README/llms.txt links resolve to the (existing) guide file, so `check-links` stays green
- No new agent file and no `commands/*.md` change — integration is reference-only
</summary>

<objective>
Register the authored security review guide in the repo's three integration points (README.md, llms.txt, agents/go-security-specialist.md) and verify the guide is clean, exactly scoped, and fully indexed. This is prompt 3 of 4; it depends on prompts 1-2 (the guide file and all 5 RULE blocks exist, the index has all 5 entries).
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "When Changing Files / Adding a new guide" checklist: create the guide (done in prompts 1-2), add to `README.md` table, update `llms.txt`, add the matching agent reference if enforceable. The agent already exists (`agents/go-security-specialist.md`) — this prompt only adds the guide to its source-of-truth references.
Read `README.md` around the "### Go — Infrastructure" table (the row `| [Security Linting](docs/go-security-linting.md) | Security analysis |` at ~line 147). The new row goes immediately after it in the same table.
Read `llms.txt` — the bullet `- [Security Linting](docs/go-security-linting.md): Security-focused static analysis` sits at ~line 27 as the last bullet of the "## Go — Testing & Quality" section (that heading is at line 21; the "## Go — Infrastructure & Tools" heading is at line 29). The new bullet goes immediately after the Security Linting bullet.
Read `agents/go-security-specialist.md` — the line to edit is the "Source of truth (rule definitions):" paragraph in the `# Purpose` section: `Companion guides: go-security-linting.md, teamvault-conventions.md, go-k8s-binary-conventions.md (secret-handling subset).`
Read `docs/security/security-review-guide.md` (full) — you are verifying it, not editing it (unless the verification below fails).
Read `scripts/check-links.sh` — it validates that `](...)` links in README.md and llms.txt resolve to existing files; the new links must point at the existing `docs/security/security-review-guide.md`.
</context>

<requirements>
1. Add a table row to `README.md` in the "### Go — Infrastructure" table, immediately after the existing Security Linting row:
   ```
   | [Security Review Guide](docs/security/security-review-guide.md) | Mechanical security rule base |
   ```
   Match the exact surrounding table formatting (same `| Guide | Description |` column shape, no trailing whitespace). Do NOT edit any other README section or row.

2. Add a bullet to `llms.txt` immediately after the existing Security Linting bullet (which is the last bullet of the "## Go — Testing & Quality" section):
   ```
   - [Security Review Guide](docs/security/security-review-guide.md): Mechanical security rule base (5 detectors) for Security Review Mode
   ```
   Match the existing bullet formatting (dash, space, `[Title](path): description`). Do NOT edit any other section or bullet.

3. Edit `agents/go-security-specialist.md`: in the `# Purpose` section, change the "Companion guides:" list to name the new guide first:
   - Before: `Companion guides: `go-security-linting.md`, `teamvault-conventions.md`, `go-k8s-binary-conventions.md` (secret-handling subset).`
   - After: `Companion guides: `security-review-guide.md`, `go-security-linting.md`, `teamvault-conventions.md`, `go-k8s-binary-conventions.md` (secret-handling subset).`
   Make ONLY this one edit. Do not restructure the agent, do not touch its checklists or tool sections.

4. Add a row to the Doc ↔ Agent alignment table in `CLAUDE.md` (the table spans lines ~22-82, listing every enforceable guide with its owner agent — per `docs/dod.md` this repo's validationPrompt requires the table updated when a new enforceable guide ships). Insert immediately after the go-security-linting.md row:
   ```
   | `security-review-guide.md` | `go-security-specialist` |
   ```
   Match the surrounding table's column style exactly. Make ONLY this one row addition — no other CLAUDE.md edits.

5. Verify the guide is clean and exactly scoped (these are AC6 checks — if any fails, fix the guide, do not weaken the check):
   - `grep -c '^### RULE go-security/' docs/security/security-review-guide.md` returns 5.
   - `grep -cE '^### RULE go-security/(tls-insecure-skip-verify|crypto-insecure-random|crypto-weak-algorithm|sql-string-interpolation|hardcoded-secret) ' docs/security/security-review-guide.md` returns 5 (the exact five slugs — a duplicate or wrong slug must not pass).
   - `grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md` returns 0 lines.
   - `grep -cE 'RULE go-security/(ssrf|authz|invariant)' docs/security/security-review-guide.md` returns 0.
   - The guide's `## Tiers` prose states (in prose, not as RULE blocks) that the judgment and invariant tiers ship in a follow-up task.
   - If a guide fix changes any RULE block, re-run `make build-index` and commit the regenerated `rules/index.json` (this overrides the byte-stable rule only in that case); otherwise leave the index untouched (prompt 4 owns the final regen).

6. Run `make precommit` — must exit 0. If `check-links` reports a broken link, the new README/llms.txt entry points at a path that does not exist or has a typo — fix the link text, not the file.

7. Do NOT touch: `docs/security/security-review-guide.md`'s RULE blocks (prompts 1-2 own them), `rules/security/*.yml`, `rule-tests/`, `scripts/build-index.py`, `rules/index.json` (must remain byte-stable unless a RULE block was fixed per requirement 5), `commands/*.md`, `scripts/validate-citations.sh`, `CHANGELOG.md`. Do NOT create `agents/security-verifier.md`.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. `.git` is a worktree pointer file, unusable inside the container; do NOT run `git` commands.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt.
- No new agent file, no command change: do not create `agents/security-verifier.md`, do not modify `commands/code-review.md` or any `commands/*.md`.
- The guide's RULE blocks stay exactly as authored in prompts 1-2 (5 blocks, all `go-security/<slug>`, owner `go-security-specialist`). No judgment/invariant-tier blocks.
- Generic examples only — no trading terms anywhere in the guide or edits.
- No personal paths (no `~/Downloads`, no `~/...` references) in any edited file.
- `rules/index.json` is byte-stable this prompt — do not regenerate it.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — `.git` is a worktree pointer file).
```bash
# --- Requirements 1-4: integration references registered (AC7) ---
grep -n 'security-review-guide' README.md                 # must return >= 1 line
grep -n 'security-review-guide' llms.txt                  # must return >= 1 line
grep -n 'security-review-guide' agents/go-security-specialist.md   # must return >= 1 line
grep -n 'security-review-guide.md' CLAUDE.md              # must return >= 1 line (Doc<->Agent alignment row)

# The agent edit names it alongside the two existing source-of-truth guides
grep -n 'Companion guides:.*security-review-guide.md.*go-security-linting.md.*teamvault-conventions.md' \
  agents/go-security-specialist.md && echo "agent companion list: ok"

# --- Requirement 5: guide clean and exactly scoped (AC6) ---
grep -c '^### RULE go-security/' docs/security/security-review-guide.md   # must return 5
grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md   # must return 0 lines
grep -cE 'RULE go-security/(ssrf|authz|invariant)' docs/security/security-review-guide.md   # must return 0

# --- Requirement 6: full precommit green ---
make precommit   # must exit 0
```
</verification>
