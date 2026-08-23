---
status: completed
spec: [008-security-review-pipeline]
summary: 'Verified the security review pipeline scope-lock and integrity gates: no agent/command/validator/CLAUDE.md changes, rule base intact at exactly 5 rules / 5 detectors / 171 index entries, all AC1-AC8 evidence greps pass, changelog + 4-version alignment intact, and make precommit exits 0'
execution_id: coding-security-review-pipeline-exec-037-spec-008-scope-lock-gates
dark-factory-version: dev
created: "2026-08-23T10:30:00Z"
queued: "2026-08-23T08:26:14Z"
started: "2026-08-23T08:29:48Z"
completed: "2026-08-23T08:30:44Z"
branch: dark-factory/security-review-pipeline
---

# Verify the security review pipeline scope-lock and integrity gates

<summary>
- Runs the final scope-lock verification that this docs-layer task touched nothing outside the docs layer: no command file, no validator script, no agent file, and no CLAUDE.md Doc↔Agent row
- Confirms the rule base is byte-intact: the sibling security guide still has exactly 5 rule blocks, the detector directory still has exactly 5 files, and the regenerated rule index stays at exactly 171 entries
- Confirms neither the new pipeline guide nor the extended selector guide gained any rule heading
- Re-runs every container-executable acceptance-criterion evidence grep from the spec as a final sweep (pipeline guide, selector extension, README/llms registration)
- Confirms the `## Unreleased` changelog entry exists and `make precommit` exits 0
- Leaves the git-based evidence (scope-lock via `git status --short`, the operator end-to-end walk) to the operator-side verification rung
</summary>

<objective>
Prove the scope-lock and integrity gates of the security review pipeline spec: nothing outside the docs layer was changed, the rule base is untouched at exactly 5 rules / 171 index entries, no stray rule headings were introduced, and `make precommit` is green. This is the final prompt of the spec and depends on prompts 1-2 having shipped the pipeline guide and the selector extension.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the Doc ↔ Agent alignment rule and the "When Changing Files / Adding a new guide" checklist. This feature must NOT add a Doc↔Agent row for the pipeline guide (it is a procedure contract, not an enforceable rule guide).

Read `scripts/build-index.py` and `Makefile` — the walker and targets behind the integrity gates this prompt runs: `check-index` (regenerated index byte-equal to the committed one), `check-coverage` (enforcement paths resolve / no orphan YAMLs), `check-acceptance` (selector-mode guide + command contracts), `check-links` (README/llms links resolve).

Read `scripts/check-coverage.sh` and `scripts/acceptance.sh` (skim) — the assertions these gates make, so a failure can be interpreted, not guessed at.

Re-read the artifacts this prompt verifies (full): `docs/security/security-review-pipeline.md`, `docs/selector-mode-guide.md`, `docs/security/security-review-guide.md`, `README.md`, `llms.txt`, `CHANGELOG.md` (head).

Confirm the environment: `jq`, `python3`, `ast-grep` are present (the `check-acceptance` preflight requires them).
</context>

<requirements>
1. **Scope-lock negatives (container form).** The git-based `git status --short` evidence for AC9 runs on the operator side of the spec's Verification ladder; here use filesystem checks:
   - `test ! -f agents/security-verifier.md` — no new agent file.
   - `grep -rn 'security-review-pipeline' agents/*.md` returns 0 matches — no agent file was touched by this feature.
   - `grep -rn 'security-review-pipeline' commands/*.md scripts/validate-citations.sh` returns 0 matches — no command and no validator content was added.
   - `grep -n 'security-review-pipeline' CLAUDE.md` returns 0 lines — no Doc↔Agent row was added for the pipeline guide.
2. **Rule-base integrity.**
   - `grep -c '^### RULE go-security/' docs/security/security-review-guide.md` returns 5 — the sibling guide kept its exactly-5 rule base.
   - `grep -c '^### RULE ' docs/security/security-review-pipeline.md` returns 0 — the new guide is a procedure contract with no rule headings.
   - `grep -c '^### RULE ' docs/selector-mode-guide.md` returns 0 — the extension added no rule headings.
   - `ls rules/security/*.yml | wc -l` returns 5 — no detector added or removed.
   - `python3 scripts/build-index.py | jq length` returns 171 — no index entries added (this is AC9's explicit evidence).
   - `make check-index` exits 0 — the committed `rules/index.json` equals the freshly regenerated one.
3. **Full acceptance-criterion evidence sweep (AC1-AC8, container form).** Run every grep from the spec's Container-executable Verification rung and confirm each expectation. If any check fails, fix the underlying doc that prompts 1-2 shipped (a missing evidence string, a stray heading) and re-run; NEVER weaken a check to force a pass:
   - AC1: `grep -c 'entry_points' docs/security/security-review-pipeline.md` ≥1; `grep -c 'never committed' docs/security/security-review-pipeline.md` ≥1; `grep -c '```json' docs/security/security-review-pipeline.md` ≥1.
   - AC2: `grep -n 'file:line' docs/security/security-review-pipeline.md` ≥1; `grep -nE 'touched package|blind spot' docs/security/security-review-pipeline.md` ≥1.
   - AC3: `grep -n 'carry forward' docs/security/security-review-pipeline.md` ≥1; `grep -n 'model refresh' docs/security/security-review-pipeline.md` ≥1; `grep -n 'diff-relevant' docs/security/security-review-pipeline.md` ≥1.
   - AC4: `grep -n 'attack-surface inventory' docs/security/security-review-pipeline.md` ≥1; `grep -n 'drift' docs/security/security-review-pipeline.md` ≥1.
   - AC5: each of `authz`, `input-origin`, `data-to-sink`, `external-io`, `crypto`, `secrets` has `grep -c <group> docs/selector-mode-guide.md` ≥1; `grep -n 'over-select' docs/selector-mode-guide.md` ≥1.
   - AC6: `grep -n 'attack_surfaces' docs/selector-mode-guide.md` ≥1; `grep -n 'invariant_id' docs/selector-mode-guide.md` ≥1.
   - AC7: `grep -c 'invariant' docs/selector-mode-guide.md` ≥2; `grep -n 'attack-surface inventory' docs/selector-mode-guide.md` ≥1.
   - AC8: `grep -n 'security-review-pipeline' README.md llms.txt` ≥1 line per file.
4. **Changelog + version integrity.** `grep -n -m1 '^## Unreleased' CHANGELOG.md` returns a line; `grep -n 'security-review-pipeline' CHANGELOG.md` returns ≥1 line (the hyphenated form, matching the prompt-1 bullet text). Run `make check-versions` and confirm it exits 0 — the four version strings (top `## vX.Y.Z` CHANGELOG section, `.claude-plugin/plugin.json .version`, `.claude-plugin/marketplace.json .metadata.version` and `.plugins[0].version`) were NOT touched by this task. A non-zero exit indicates a scope breach from prompts 1-2 — do NOT fix the versions (releases are manual); record the failure and stop.
5. **Final gate.** Run `make precommit` — must exit 0. This is the last prompt of the spec; a non-zero exit means the task is not complete. Fix any failing check and re-run (per the repo's fix-loop: re-run only the failing target first, then full precommit once).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git; do NOT run `git` commands (the container's git is not authoritative). Git-based evidence (AC9 `git status --short` scope-lock, AC10 operator DoD walk) is covered by the operator-executable rung of the spec's Verification ladder.
- Precommit stays green — `make precommit` must exit 0 at the end of this prompt.
- This prompt verifies and records; it does not redesign. Do NOT weaken any check to force a pass. The only corrective edits allowed are fixing a doc that prompts 1-2 shipped (missing evidence string, stray heading, broken link) — never a rule, detector, index entry, or command.
- Do NOT touch: `commands/*.md`, `scripts/validate-citations.sh`, `agents/*.md`, `CLAUDE.md`, `rules/security/*.yml`, `rules/index.json`, `scripts/build-index.py`, `scenarios/*`.
- No version strings touched (releases are manual, handled by maintainer-agent-releaser).
- Generic examples only (User, Order, Product, Customer); no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin.
</constraints>

<verification>
Run from repo root. All commands are container-executable (dark-factory handles git; the container's git is not authoritative).
```bash
# --- Requirement 1: scope-lock negatives (AC9, container form) ---
test ! -f agents/security-verifier.md && echo "no new agent: ok"
grep -rn 'security-review-pipeline' agents/*.md || echo "no agent content: ok"                    # must return 0 matches
grep -rn 'security-review-pipeline' commands/*.md scripts/validate-citations.sh || echo "no command/validator content: ok"   # must return 0 matches
grep -n 'security-review-pipeline' CLAUDE.md || echo "no Doc<->Agent row: ok"                     # must return 0 lines

# --- Requirement 2: rule-base integrity (AC9) ---
grep -c '^### RULE go-security/' docs/security/security-review-guide.md      # must return 5
grep -c '^### RULE ' docs/security/security-review-pipeline.md               # must return 0
grep -c '^### RULE ' docs/selector-mode-guide.md                             # must return 0
ls rules/security/*.yml | wc -l                                              # must return 5
python3 scripts/build-index.py | jq length                                   # must return 171
make check-index                                                             # must exit 0

# --- Requirement 3: full AC evidence sweep (AC1-AC8) ---
grep -c 'entry_points' docs/security/security-review-pipeline.md             # >= 1
grep -c 'never committed' docs/security/security-review-pipeline.md          # >= 1
grep -c '```json' docs/security/security-review-pipeline.md                  # >= 1
grep -n 'file:line' docs/security/security-review-pipeline.md                # >= 1
grep -nE 'touched package|blind spot' docs/security/security-review-pipeline.md   # >= 1
grep -n 'carry forward' docs/security/security-review-pipeline.md            # >= 1
grep -n 'model refresh' docs/security/security-review-pipeline.md            # >= 1
grep -n 'diff-relevant' docs/security/security-review-pipeline.md            # >= 1
grep -n 'attack-surface inventory' docs/security/security-review-pipeline.md # >= 1
grep -n 'drift' docs/security/security-review-pipeline.md                    # >= 1
for g in authz input-origin data-to-sink external-io crypto secrets; do
  n=$(grep -c "$g" docs/selector-mode-guide.md); echo "$g: $n"; [ "$n" -ge 1 ]
done
grep -n 'over-select' docs/selector-mode-guide.md                            # >= 1
grep -n 'attack_surfaces' docs/selector-mode-guide.md                        # >= 1
grep -n 'invariant_id' docs/selector-mode-guide.md                           # >= 1
n=$(grep -c 'invariant' docs/selector-mode-guide.md); echo "invariant: $n"; [ "$n" -ge 2 ]
grep -n 'attack-surface inventory' docs/selector-mode-guide.md               # >= 1
grep -n 'security-review-pipeline' README.md                                 # >= 1
grep -n 'security-review-pipeline' llms.txt                                  # >= 1

# --- Requirement 4: changelog + version integrity ---
grep -n -m1 '^## Unreleased' CHANGELOG.md                                    # must return a line
grep -n 'security-review-pipeline' CHANGELOG.md                              # must return >= 1 line (hyphenated form — matches the prompt-1 bullet text)
make check-versions                                                          # must exit 0 (four version strings untouched)

# --- Requirement 5: final gate ---
make precommit                                                               # must exit 0
```
</verification>
