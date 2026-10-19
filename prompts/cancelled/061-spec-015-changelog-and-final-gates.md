---
status: cancelled
spec: [015-language-agnostic-maintainability-rules]
created: "2026-10-18T15:58:21Z"
queued: "2026-10-18T16:35:23Z"
branch: dark-factory/language-agnostic-maintainability-rules
cancelled: "2026-10-18T16:41:03Z"
---

# Changelog entry and cross-cutting release gates

<summary>
- The changelog records the maintainability rule family as one user-visible feature under the unreleased section
- The release tail is verified: the index holds 199 entries (5 new, 194 pre-existing), the coverage check reports no drift, and the owner-agent assertion passes
- Every new rule id is proven to resolve through the citation validator, so an invented id cannot survive review
- The negative scope lock is checked: no frozen file (command, security doc, selector guide, scenario, maintainer config, or the two frozen scripts) references the new rule family
- The guide is proven language-neutral inside every rule block
- The gates the container can run all pass: changelog, index, coverage, citation and acceptance checks are green, with the git-dependent precommit step reported as an environment gap
</summary>

<objective>
Close spec 015: ensure the changelog carries exactly one `feat:` bullet for the maintainability rule family, then run the cross-cutting gates that prove the change is release-ready and scope-locked. This is prompt **3 of 3** and depends on prompts 1 and 2.
</objective>

<context>
Read fully before writing:

- `CHANGELOG.md` — the top of the file. An `## Unreleased` section already exists with this bullet:
  `- feat: add language-agnostic maintainability rules for files outside Go/Python/Node — comments restating code, dead code, bandaids, speculative abstraction / over-configuration, and naming/size drift`
- `docs/changelog-guide.md` — entry format `- <prefix>: <what> [context]`, prefix required, one bullet per logical change, append to an existing `## Unreleased` rather than replacing it.
- `specs/in-progress/015-language-agnostic-maintainability-rules.md` — AC7, AC8, AC9, AC10, AC12 and the Verification section.
- `scripts/check-coverage.sh` — prints `check-coverage: OK (<N> rules, <M> mechanical YAMLs, no drift)` and fails on a missing cited YAML, an orphan YAML, or an id mismatch.
- `scripts/validate-citations.sh` — takes a JSON file of findings and exits 0 when every `rule_id` resolves against `rules/index.json`, 1 when any is dropped, 2 when the index is missing.
- `Makefile` — the `precommit` target chain and the git-free subset used below.

**Verified repo facts this prompt relies on**

- The pre-change rule count is 194; after prompts 1 and 2 it is 199 (194 + the 5 maintainability rules). Prompt 2 adds no rule.
- The five ids are `maintainability/bandaid-fix`, `maintainability/comment-restates-code`, `maintainability/dead-code`, `maintainability/naming-size-drift` and `maintainability/speculative-abstraction`.
- The container's `.git` is masked for this run (`.dark-factory.log` records `hideGit=true`). `make precommit` therefore fails on `check-changelog-fold` with `not a git repository`; the git-based `git diff --stat` scope lock in AC12 runs on the operator side of the spec's Verification ladder, not here.
</context>

<requirements>

### 1. Ensure the changelog entry

Open `CHANGELOG.md` and locate the `## Unreleased` section.

- If it already contains the bullet quoted in `<context>`, change nothing. Do not add a second bullet and do not reword it.
- If the bullet is missing, add exactly that one line under `## Unreleased`, preserving the section's existing bullets.
- If `## Unreleased` itself is missing, add it immediately after the introductory paragraphs and before the most recent `## vX.Y.Z` heading, with the single bullet beneath it.

Do not rename `## Unreleased` to a version, do not bump any version string in `.claude-plugin/plugin.json` or `.claude-plugin/marketplace.json`, and do not touch any other changelog section.

### 2. Run the cross-cutting gates

Run every check in `<verification>` and confirm each expectation. The negative checks matter as much as the positive ones: a scope-lock failure means a prompt reached outside its assigned files.

### 3. Report the environment limitation honestly

If `make precommit` fails only on `check-changelog-fold` with `not a git repository`, that is the masked-`.git` environment, not this change. Run the git-free target subset, require it green, record the gap in `## Improvements` (category: GLOBAL), and report `status: partial` with the real exit code. Never report `success` for a non-zero `make precommit`.
</requirements>

<constraints>
- **One changelog bullet.** Exactly one `feat:` bullet describes this change. The existing bullet is authoritative; do not duplicate or reword it.
- **No version bump.** `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are untouched; `.dark-factory.yaml` keeps `autoRelease: false` and the release is cut out of band by the maintainer-agent-releaser.
- **No rule, guide, agent or script edit.** This prompt is the release tail; `docs/maintainability-review-guide.md`, `agents/maintainability-assistant.md`, `rules/index.json`, `scripts/acceptance.sh` and `specs/fixtures/maintainability/**` are already final.
- **Do NOT modify** `commands/**`, `docs/selector-mode-guide.md`, `docs/security/**`, `scripts/rule-checks.sh`, `scripts/validate-citations.sh`, `scripts/build-index.py`, `.maintainer.yaml`, `scenarios/**`, or `README.md` / `llms.txt` / `CLAUDE.md`.
- **No mechanical layer:** this prompt makes no `rules/` change — prompt 1 already regenerated `rules/index.json`; there is no `rules/maintainability/` directory and no new ast-grep YAML.
- **Do NOT commit and do NOT run any `git` command.** The container's `.git` is masked (`hideGit=true`); the daemon commits on completion. The `git diff --stat` scope lock in AC12 is operator-side.
- **Generic content only:** any text added to the changelog stays general-purpose — no trading or project-specific domains.
</constraints>

<verification>
All commands are container-executable from the repo root. This container's `.git` is masked (`hideGit=true`) — no check below needs git.

```bash
# 1. Changelog: one unreleased feat bullet, present exactly once
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'          # expect: >= 1
grep -c 'language-agnostic maintainability rules' CHANGELOG.md                            # expect: 1
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c 'maintainability'    # expect: 1

# 2. Index shape: 199 total, 5 new, 194 pre-existing
jq 'length' rules/index.json                                                              # expect: 199
jq '[.[] | select(.id|startswith("maintainability/"))] | length' rules/index.json          # expect: 5
jq '[.[] | select(.id|startswith("maintainability/")|not)] | length' rules/index.json      # expect: 194
python3 scripts/build-index.py | jq 'length'                                              # expect: 199
make check-index                                                                          # expect: exit 0

# 3. Every new id resolves through the citation validator
cat > /tmp/df014-citations.json <<'EOF'
[
  {"rule_id": "maintainability/bandaid-fix", "file": "infra/main.tf", "line": 1},
  {"rule_id": "maintainability/comment-restates-code", "file": "infra/main.tf", "line": 1},
  {"rule_id": "maintainability/dead-code", "file": "infra/main.tf", "line": 6},
  {"rule_id": "maintainability/naming-size-drift", "file": "infra/main.tf", "line": 1},
  {"rule_id": "maintainability/speculative-abstraction", "file": "infra/main.tf", "line": 1}
]
EOF
bash scripts/validate-citations.sh /tmp/df014-citations.json > /dev/null      # expect: exit 0

# 4. No mechanical layer, coverage clean
find rules -path '*maintainability*'                                                       # expect: no output
test ! -d rules/maintainability && echo "OK: no maintainability YAML directory"
make check-coverage                                                                        # expect: exit 0, "199 rules", "no drift"

# 5. Owner agent, trigger boundary and acceptance suite
test -f agents/maintainability-assistant.md && echo "OK: owner agent exists"
make check-acceptance                                                                      # expect: exit 0
bash scripts/acceptance.sh 2>&1 | grep -c 'non-owned diff selects maintainability/'        # expect: 5
bash scripts/acceptance.sh 2>&1 | grep -c 'owned-source diff selects zero maintainability rules'   # expect: 1

# 6. The guide stays language-neutral after the first RULE heading
! awk '/^### RULE/{inrule=1} inrule' docs/maintainability-review-guide.md \
  | grep -qE '(^|[^A-Za-z])(Go|Python|Node|TypeScript|JavaScript)([^A-Za-z]|$)'
# expect: exit 0 — no language name at or after the first RULE heading

# 7. Trigger boundary: exactly 22 globs, none on an owned extension
python3 scripts/build-index.py | jq -r '[.[] | select(.owner=="maintainability-assistant") | .trigger[]] | unique | .[]' > /tmp/df014-triggers.txt
wc -l < /tmp/df014-triggers.txt                                                            # expect: 22
grep -E '\.(go|py|ts|tsx|js|jsx|md|yaml|yml)$' /tmp/df014-triggers.txt                     # expect: no output

# 8. Scope lock (git-free): no forbidden file mentions the new family, and the
#    only script carrying it is the acceptance suite
grep -rl 'maintainability' commands/ docs/security/ docs/selector-mode-guide.md \
  scripts/rule-checks.sh scripts/validate-citations.sh scenarios/ .maintainer.yaml
# expect: no output
grep -c 'maintainability' scripts/acceptance.sh                                            # expect: >= 3
grep -c 'maintainability' docs/maintainability-review-guide.md                             # expect: >= 5
grep -c 'maintainability' agents/maintainability-assistant.md                              # expect: >= 5

# 9. The git-free precommit targets
make check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test   # expect: exit 0

# 10. Full gate is NOT a pass condition here: `make precommit` cannot pass with a
#     masked `.git` (check-changelog-fold exits 1 on `not a git repository`).
#     Step 9 is the in-container gate; the daemon's validationCommand still runs
#     `make precommit` afterwards, and requirement 3 defines the report.
```

Note on `make precommit`: under this run's masked `.git`, `check-changelog-fold` exits non-zero with `not a git repository`. That single failure is an environment limitation. If it is the only failure, the git-free target list in step 9 is the real in-container gate; report the gap and `status: partial` with the actual exit code.
</verification>

<notes>
- **The changelog bullet already exists.** It was added before prompt generation; this prompt verifies it rather than adding a second copy. `grep -c 'language-agnostic maintainability rules'` must stay at 1.
- **Why the citation check is here.** `validate-citations.sh` resolves every emitted `rule_id` against `rules/index.json`, so it is the cheapest proof that the five ids are real and discoverable — the same gate a live review applies to a finding.
- **Why the scope lock is grep-based.** The container's `.git` is masked, so `git diff --stat origin/master...HEAD` (AC12) cannot run here. The grep set covers the files the spec names as frozen; the git-based diff stat remains an operator-side check in the spec's Verification ladder.
- **Operator-side, not this prompt:** AC4, AC5, AC6 (fixture reviews against the released plugin) and AC11 (bench re-run and precision comparison). They need a released plugin and the bench harness, so they run after merge per the spec's operator rung.
</notes>
