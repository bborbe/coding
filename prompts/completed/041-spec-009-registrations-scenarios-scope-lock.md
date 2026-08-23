---
status: completed
spec: [009-security-verifier-citations]
summary: 'Registered the security-verifier agent in README.md (Other agents) and llms.txt, landed three draft scenario fixtures (007 confirmed IDOR / 008 rejected-by-verifier / 009 toolchain-fail-closed) under scenarios/, added the ## Unreleased changelog entry naming the verifier gate and polymorphic citation validation, and proved the scope-lock negatives (step headings byte-unchanged, rule base 5/5/171, no command/index/CLAUDE.md leakage, version strings untouched) with make precommit green.'
execution_id: coding-security-verifier-exec-041-spec-009-registrations-scenarios-scope-lock
dark-factory-version: dev
created: "2026-08-23T10:01:50Z"
queued: "2026-08-23T10:28:26Z"
started: "2026-08-23T10:28:28Z"
completed: "2026-08-23T10:30:18Z"
branch: dark-factory/security-verifier-citations
---

# Register the verifier, land the scenario fixtures, and lock the scope

<summary>
- The verifier agent is registered in the plugin's README "Other agents" table and in the llms.txt index, with no entry in any command dispatch list
- Three draft scenario fixtures land under the scenarios directory locking the verifier's confirmed/rejected verdicts and the validator's fail-closed behavior as E2E acceptance contracts
- Each new scenario is a draft fixture in the standard scenario format with a Test PR marker that stays TBD until the security signal is wired, and none is promoted to active
- The changelog gains an Unreleased section naming the verifier gate and the polymorphic citation validation, with the four version strings untouched
- A final scope-lock sweep proves the frozen step headings are byte-unchanged, the rule base is intact at exactly 5 detectors / 5 rules / 171 index entries, no command or index script changed, and precommit is green
- The README and llms scenario tables are intentionally not extended for the new draft fixtures, matching the existing precedent that not every on-disk scenario is listed there
</summary>

<objective>
Complete the integration pass for the security-verifier-citations spec: register the verifier agent in README.md and llms.txt, land the three draft scenario fixtures, add the `## Unreleased` changelog entry, and run the scope-lock gate proving prompts 1–3 held the task-3/4/6 boundaries with `make precommit` green.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "When Changing Files / Adding a new agent" checklist (create agent file, register in README + llms; this task deliberately registers the verifier in the README "Other agents" table only, NOT in any dispatch list and NOT in the CLAUDE.md Doc↔Agent table — recorded decision) and the "Adding a new guide" checklist for the `## Unreleased` rule (CHANGELOG entry required; four version strings NOT touched).

Read `README.md` — the `<details><summary><b>Other agents</b></summary>` table (~lines 250–274) is where the `security-verifier` row goes; it is NOT one of the Go Quality dispatch tables (the `<details><summary><b>Go Quality (standard mode, 7 agents)</b></summary>` and `<details><summary><b>Go Quality (full mode adds 8 more)</b></summary>` blocks). Note the "Acceptance Scenarios" table (~lines 280–285) lists scenarios 001–004 only — scenarios 005/006 exist on disk but are not listed, so the new draft fixtures are likewise NOT added to that table.

Read `llms.txt` — the "## Go — Testing & Quality" section (~lines 21–29) ends with the two security bullets: `- [Security Review Guide](...)` and `- [Security Review Pipeline](...)`. The verifier bullet goes immediately after the Security Review Pipeline bullet. Note the "## Acceptance Scenarios" section (~lines 99–104) lists scenarios 001–004 only — same precedent: do not extend it for the new fixtures.

Read `CHANGELOG.md` (head only) — the topmost versioned section is `## v0.47.0`; there is currently no `## Unreleased` section. Insert `## Unreleased` directly above `## v0.47.0`.

Read `scenarios/005-selector-clean-short-circuit.md` (full) — the scenario format precedent (frontmatter, `# Scenario NNN:` H1, "Validates that ..." sentence, `## Setup` / `## Action` / `## Expected` / `## Cleanup` checkbox sections, closing walk-status note). The new fixtures follow the spec's AC10 format which additionally requires a `## Test PR` section (so `grep -c '^## '` ≥ 5 per file). Read `scenarios/006-selector-findings-path.md` (full) — the format precedent for the `## Test PR` section the new fixtures must carry (005 has no Test PR section).

Re-read the deliverables this prompt integrates (full): `scripts/validate-citations.sh` and the fixture set under `scripts/testdata/validate-citations/` (prompt 1), `agents/security-verifier.md` (prompt 2), `docs/selector-mode-guide.md` (prompt 3).

Read `docs/security/security-review-pipeline.md` (the model schema) and `docs/security/security-review-guide.md` (the rule ids) — the concrete fixture details the scenario "Expected" sections cite.
</context>

<requirements>
1. **Hard dependency guards.** Verify all prompts 1–3 deliverables are present before doing anything else; if any is missing, STOP and report which prompt must execute first:
   - `grep -q 'SECURITY_MODEL_FILE' scripts/validate-citations.sh` (prompt 1)
   - `test -f scripts/testdata/validate-citations/rule-valid.json` (prompt 1)
   - `test -f agents/security-verifier.md` (prompt 2)
   - `grep -q 'Verifier gate' docs/selector-mode-guide.md` (prompt 3)

2. **README registration (AC11).** In `README.md`, add a row to the `<details><summary><b>Other agents</b></summary>` table (not in any Go Quality dispatch table):
   ```
   | `security-verifier` | Security-mode post-adjudication falsification gate — attempts to falsify high-severity findings before they emit (precision vs the judge's recall) |
   ```
   Description wording is at your discretion but must convey "security-mode post-adjudication falsification gate" and must NOT imply dispatch from `/coding:local-review` or `/coding:pr-review`. Match the exact surrounding table formatting (same `| Agent | Description |` column shape, no trailing whitespace). Do NOT edit any other README section or row.

3. **llms.txt registration (AC11).** Add a bullet to `llms.txt` immediately after the Security Review Pipeline bullet in the `## Go — Testing & Quality` section (or, if that placement is structurally unsuitable, anywhere near the security guides):
   ```
   - [security-verifier](agents/security-verifier.md): Security-mode post-adjudication falsification gate — verdicts confirmed|plausible|rejected, counterevidence_checked on survivors (not in any command dispatch list)
   ```
   Match the existing bullet formatting (dash, space, `[Title](path): description`). Do NOT edit any other section or bullet.

4. **Scenario fixtures (AC10).** Create three files in `scenarios/` — `007-security-idor-confirmed.md`, `008-security-idor-rejected-by-verifier.md`, `009-security-toolchain-fail-closed.md`. Each follows the standard scenario format with EXACTLY these five `## ` sections in this order: `## Test PR`, `## Setup`, `## Action`, `## Expected`, `## Cleanup` (so `grep -c '^## '` ≥ 5 per file). Each carries frontmatter `status: draft` and an H1 `# Scenario NNN: <what this proves in one line>`, followed by a one-sentence "Validates that ..." description. Each `## Test PR` section marks the fixture as TBD (a public fixture shape — e.g. "TBD — task 4 names the security-mode fixture PR; expected shape: a repo whose `order` resource handler lacks an ownership authorization check"), never a personal path. Do NOT walk or promote any of the three to `active` — they are draft fixtures, walkable only after task 4 wires the security-review signal.
   - `007-security-idor-confirmed.md` — the verifier CONFIRMS an IDOR finding on a generic order-resource handler (severity critical, kind invariant, `invariant_id` resolving in the model). Expected: verdict `confirmed`, a concrete attacker scenario, populated `counterevidence_checked`, the finding survives with severity=critical, and per the blocking model it blocks merge (`confidence==confirmed ∧ exploitability==high ∧ impact≥medium`).
   - `008-security-idor-rejected-by-verifier.md` — the verifier REJECTS an IDOR claim because middleware/service-layer authorization is found. Expected: verdict `rejected`, `reject_reason` recorded, the finding does NOT emit, and no merge block.
   - `009-security-toolchain-fail-closed.md` — a `kind: toolchain` finding (e.g. osv-scanner/trivy output) passes citation validation with no `rule_id` (exit 0, kept), while a `kind: invariant` finding run without `SECURITY_MODEL_FILE` drops fail-closed (exit 1, `WARN: dropped` on stderr naming the `invariant_id`). Expected: both validator behaviors observed per the spec's fixture matrix.

5. **CHANGELOG (AC12).** Add a `## Unreleased` section to `CHANGELOG.md` directly above `## v0.47.0` (the topmost versioned section), after the frozen preamble header block, with exactly one bullet (follow `docs/changelog-guide.md`; conventional prefix required):
   ```
   ## Unreleased

   - feat: Add agents/security-verifier.md — post-adjudication falsification gate (7-item checklist, verdict confirmed|plausible|rejected, counterevidence_checked on survivors) — and extend scripts/validate-citations.sh to the polymorphic citation contract (kind rule/invariant/toolchain, SECURITY_MODEL_FILE, fail-closed on absent model); register the agent and land three draft security-mode scenario fixtures
   ```
   If `## Unreleased` already exists (do not expect it — verify first), append the bullet to it instead of creating a second section. Do NOT touch the four version strings (`CHANGELOG.md` top versioned entry, `.claude-plugin/plugin.json` `version`, both `.claude-plugin/marketplace.json` fields).

6. **Scope-lock negatives (AC13, container form).** The git-based `git status --short` evidence runs on the operator side of the spec's Verification ladder; here use filesystem checks:
   - `grep -n '^## Step 4c-sel' docs/selector-mode-guide.md` returns the exact baseline heading `## Step 4c-sel: CLASSIFY (in-session, no Task spawn)` and `grep -n '^## Step 4d-sel' docs/selector-mode-guide.md` returns `## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)` — no renumbering.
   - `grep -rn 'security-verifier\|SECURITY_MODEL_FILE\|counterevidence_checked\|verifier gate' commands/*.md scripts/build-index.py scripts/ast-grep-runner.sh CLAUDE.md` returns 0 matches — no command, index script, runner, or Doc↔Agent row was touched.
   - `ls rules/security/*.yml | wc -l` returns 5; `grep -c '^### RULE go-security/' docs/security/security-review-guide.md` returns 5; `python3 scripts/build-index.py | jq length` returns 171 — rule base byte-intact.
   - `make check-index` exits 0 — `rules/index.json` equals the freshly regenerated index.
   - `make check-versions` exits 0 — the four version strings were not touched.
   - The full allowed-change set for this spec is exactly: `scripts/validate-citations.sh`, `scripts/testdata/`, `agents/security-verifier.md`, `docs/selector-mode-guide.md`, `scenarios/007-009`, `README.md`, `llms.txt`, `CHANGELOG.md`. Nothing else.

7. **Do NOT touch** (beyond the files named above): `docs/security/*.md`, any other `docs/*.md`, any other `agents/*.md`, any other `scripts/*`, `rules/*`, `specs/*`, `CLAUDE.md`, `commands/*.md`. Do NOT add the three new scenario files to the README "Acceptance Scenarios" table or the llms.txt scenarios section (precedent: scenarios 005/006 exist on disk but are not listed there; the spec registers only the verifier agent). Do NOT promote any scenario to `active`.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; git-based evidence (AC13 `git status --short` scope-lock) runs on the operator side of the spec's Verification ladder.
- Precommit stays green — `make precommit` must exit 0 at the end of this prompt. This is the last prompt of the spec; a non-zero exit means the task is not complete. Fix any failing check (a missing evidence string, a broken link, a malformed scenario heading) and re-run per the repo's fix-loop (re-run only the failing target first, then full precommit once). Do NOT weaken a check to force a pass.
- Do NOT promote the three scenarios to `active` (frozen): they are draft fixtures; the `--security` command (task 4) must exist before they can be walked.
- Agent registration scope (frozen): `security-verifier` registers in README "Other agents" and llms.txt only; it is NOT added to the standard/full-mode Go Quality dispatch lists in any command, and no CLAUDE.md Doc↔Agent row is added.
- No renumbering (frozen): `## Step 4c-sel` / `## Step 4d-sel` headings and their step bodies in `docs/selector-mode-guide.md` are byte-unchanged.
- Rule base frozen: no new `### RULE` blocks, `rules/security/*.yml` stays at exactly 5 files, `rules/index.json` byte-unchanged, no `scripts/build-index.py` change. `docs/security/security-review-guide.md` stays at exactly 5 RULE blocks.
- CHANGELOG: `## Unreleased` entry with a conventional prefix, placed directly above the highest `## vX.Y.Z` (create the section if absent); the four version strings are NOT touched (releases are manual, handled by maintainer-agent-releaser).
- Generic examples only (User, Order, Product, Customer) — never trading terms; no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin. The scenario `Test PR` TBD marker names a public fixture shape, never a personal path. No version-existence claims.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- Hard dependency guards ---
grep -q 'SECURITY_MODEL_FILE' scripts/validate-citations.sh && test -f scripts/testdata/validate-citations/rule-valid.json && test -f agents/security-verifier.md && grep -q 'Verifier gate' docs/selector-mode-guide.md && echo "prompts 1-3 deliverables present: ok"

# --- AC11: registrations ---
grep -n 'security-verifier' README.md          # must return >= 1
grep -n 'security-verifier' llms.txt           # must return >= 1

# --- AC10: three draft scenario fixtures ---
ls scenarios/                                  # must list 007-security-idor-confirmed.md, 008-security-idor-rejected-by-verifier.md, 009-security-toolchain-fail-closed.md
for f in 007-security-idor-confirmed 008-security-idor-rejected-by-verifier 009-security-toolchain-fail-closed; do
  grep -c '^status: draft' "scenarios/$f.md"    # must return 1 per file
  grep -c '^## ' "scenarios/$f.md"              # must return >= 5 per file
  grep -c '^## Test PR' "scenarios/$f.md"       # must return 1 per file
done

# --- AC12: changelog ---
grep -n -m1 '^## Unreleased' CHANGELOG.md        # must return a line
grep -n 'security-verifier' CHANGELOG.md         # must return >= 1
grep -n 'validate-citations' CHANGELOG.md        # must return >= 1

# --- AC13 negatives (container form; git status --short is operator-side) ---
grep -n '^## Step 4c-sel: CLASSIFY (in-session, no Task spawn)' docs/selector-mode-guide.md   # exact baseline heading
grep -n '^## Step 4d-sel: ADJUDICATE (in-session, no Task spawn)' docs/selector-mode-guide.md # exact baseline heading
if grep -rnE 'security-verifier|SECURITY_MODEL_FILE|counterevidence_checked|verifier gate' commands/ scripts/build-index.py scripts/ast-grep-runner.sh CLAUDE.md; then echo "LEAK DETECTED — scope-lock violated"; exit 1; else echo "no command/index-script/CLAUDE.md leakage: ok"; fi
ls rules/security/*.yml | wc -l                  # must return 5
grep -c '^### RULE go-security/' docs/security/security-review-guide.md    # must return 5
python3 scripts/build-index.py | jq length        # must return 171
make check-index                                  # must exit 0
make check-versions                               # must exit 0 (four version strings untouched)

# --- Full precommit ---
make precommit                                    # must exit 0
```
</verification>
