---
status: approved
spec: [011-security-comprehensive-rules]
summary: Record the cross-language detector layout decision in docs/security/security-review-guide.md, perform the final guide reconciliation (three-tier framing now fully shipped), add the
execution_id: pending
dark-factory-version: dev
created: "2026-08-23T20:30:00Z"
queued: "2026-08-23T20:53:15Z"
branch: dark-factory/security-comprehensive-rules
---

# Cross-language layout decision + CHANGELOG + final gates

<summary>
- Record the cross-language detector layout decision (spike Finding 2) as a new `## Cross-language detector layout` prose section in `docs/security/security-review-guide.md` — per-language `rules/security/{go,python,node}/` split with a runner case mirroring the `node/frontend` special-case in `scripts/ast-grep-runner.sh`, go-first v1 stays flat, documentation only
- Perform the final guide reconciliation: any remaining tier-deferral phrasing is rewritten to the shipped state (all three tiers live in this guide)
- Insert a `## Unreleased` section above `## v0.49.0` in `CHANGELOG.md` with a single `feat:` bullet describing the comprehensive security v1 rule base (no `## vX.Y.Z` bump — the release tail is `.maintainer.yaml` autoRelease)
- Re-run the cross-cutting gates: `make precommit`, `make check-index`, index length 180, `class` count 2, no three-component IDs, non-vacuous AC5 citation fixture, `ast-grep test` green
- No new RULE blocks, no walker, no schema, no detector changes — prompts 1/2 shipped those
- Working-tree changes are left for the daemon's `workflow: direct` post-prompt commit; no git is run inside the container
</summary>

<objective>
The comprehensive security v1 rule base is closed out: the guide records the cross-language detector layout decision and carries no deferral phrasing, `CHANGELOG.md` has a `## Unreleased` section with one `feat:` bullet for the whole feature, every cross-cutting gate is green (`make precommit`, `make check-index`, index at 180, `class` count 2, AC5 citations resolve non-vacuously), and the only modified files are `docs/security/security-review-guide.md` and `CHANGELOG.md`.
</objective>

<context>
Spec 011 prompt **3 of 3**. Depends on prompts 1 and 2 having shipped the 7 judgment rules + prose reconcile and the 2 invariant rules + walker `Class` field + schema doc. This prompt is the documentation + CHANGELOG + final-gates closer. No new RULE blocks land here.

Read fully before writing:

- `/workspace/CLAUDE.md` — project conventions, generic content only.
- `/workspace/docs/security/security-review-guide.md` — current state after prompts 1 + 2: 14 RULE blocks total (5 mechanical + 7 judgment + 2 invariant), tier-deferral prose already reconciled by prompt 1, `Class` field documented in the schema (prompt 2).
- `/workspace/docs/security/security-review-pipeline.md` — the derived security-model procedure contract (referenced, not edited).
- `/workspace/CHANGELOG.md` — convention from `docs/changelog-guide.md`. The top section today is `## v0.49.0` (the `--security` wiring release). This prompt inserts a `## Unreleased` section above `## v0.49.0` (after the SemVer preamble).
- `/workspace/docs/changelog-guide.md` (skim) — `## Unreleased` lives directly above the most-recent versioned section; conventional prefixes `feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:` / `perf:` required for every bullet; `-` / `*` bullet markers.
- `/workspace/specs/in-progress/011-security-comprehensive-rules.md` — the spec this prompt closes. Spike Finding 2 names the cross-language layout decision: per-language `rules/security/{go,python,node}/` split with a runner case for cross-language rules, while go-first v1 keeps single-language (Go) rules flat under `rules/security/`.
- `/workspace/scripts/ast-grep-runner.sh` — the runner that special-cases `rules/node/*` (skipped on frontend projects). The layout prose's "runner case" mirrors THIS file, not `bench/`.
- `/workspace/rules/index.json` — currently 180 entries after prompts 1 + 2.
- `/workspace/scripts/validate-citations.sh` — citation gate. Test a non-vacuous fixture to prove the gate keeps the new rule_ids (spec AC5).
- `/workspace/Makefile` — `make precommit` runs check-links/check-json/check-index/check-coverage/check-acceptance/check-rule-tests/bench-test.

This prompt touches only:

1. `docs/security/security-review-guide.md` — append a "Cross-language detector layout" prose section (spike Finding 2 record) and a final reconciliation touch-up if any tier-deferral phrase remains.
2. `CHANGELOG.md` — insert `## Unreleased` with a single `feat:` bullet.
</context>

<requirements>

### 1. Record the cross-language detector layout decision in `docs/security/security-review-guide.md`

Append a new section at the end of the guide (after the `## Anti-patterns to refuse` section). Title: `## Cross-language detector layout`. Content (target wording, adjust to match the doc's prose style):

```markdown
## Cross-language detector layout

When security rules grow beyond a single language, the detector tree splits per-language under `rules/security/{go,python,node}/` (one subdir per language the rule base covers). The runner that scans a multi-language repo gains a per-language case mirroring the existing `node/frontend` special-case in `scripts/ast-grep-runner.sh` (node rules are skipped on frontend projects), dispatching each language's detectors to the matching `ast-grep scan --lang <lang>` invocation.

For the v1 release, security rules are go-first: every detector lives flat under `rules/security/` (no per-language subdirectories). This matches the rule base's actual coverage today — five mechanical detectors plus nine judgment / invariant rules, all Go-targeted. The split documented above is the target layout for the cross-language expansion (the python and node language cases), deferred until non-Go rules ship.

The decision is recorded here as a spike outcome (no structural reorganization ships with this version): the cross-language split is the chosen shape; the go-first v1 stays flat because no non-Go detectors exist yet.
```

**Do NOT** create `rules/security/{go,python,node}/` directories or any new YAMLs. **Do NOT** modify `scripts/ast-grep-runner.sh` or any runner script. The decision is documentation only.

### 2. Final guide reconciliation

After the new section lands, re-grep `docs/security/security-review-guide.md` for any remaining deferral phrasing. The `grep -cE 'follow-up task|ships in a follow-up|ship.*follow-up'` and `grep -c 'until then'` counts must remain 0 — prompts 1 already removed the original deferrals, but a stray phrase from prior prose may surface. Fix any remaining hits by re-writing the surrounding sentence to describe the shipped state (all three tiers live in this guide; judgment / invariant rules are present, scoped, and emitted by the review pipeline).

Also confirm the three-tier framing at the top of `## Tiers` lists all three tiers as live, not deferred. Do not modify paragraphs 1-3 of `## Tiers`; the fourth (the sentence prompt 1 already rewrote) may be touched only if it still reads as deferred.

### 3. Add `## Unreleased` to `CHANGELOG.md`

Insert a `## Unreleased` section directly above `## v0.49.0` (after the SemVer preamble block — the `* MAJOR / MINOR / PATCH` bullets). The section contains a single `feat:` bullet that summarizes the comprehensive rule base. Do not summarize each prompt — write one bullet covering the whole feature.

Suggested bullet (target wording, adjust to the changelog's existing voice):

```markdown
## Unreleased

- feat: Ship the comprehensive security v1 rule base in `docs/security/security-review-guide.md` — 7 judgment-tier rules (SSRF, XSS, deserialization, open redirect, webhook verification MUST; mass assignment, insecure defaults SHOULD) and 2 invariant-linked authz rules (resource ownership, tenant isolation MUST) with `**Class**: security-invariant` and `@commits` triggers; extend `scripts/build-index.py` to emit a `class` index key and document the new field in `docs/rule-block-schema.md`; regenerate `rules/index.json` from 171 to 180 entries; record the cross-language detector layout decision (per-language `rules/security/{go,python,node}/` target, go-first v1 stays flat)
```

**Do NOT** include multiple bullets. One feature, one bullet — the changelog convention is one bullet per logical change, and this is one feature.

**Do NOT** add a `## vX.Y.Z` section. The release tail is out of band (`.maintainer.yaml` `autoRelease: true` cuts v0.50.0 via the maintainer-agent-releaser after merge). This prompt ships only the `## Unreleased` entry.

**Do NOT** include verification commands or test instructions in the bullet — those are release-check noise, not changelog content.

### 4. Re-run the cross-cutting gates

Run each of these from repo root and confirm exit 0 + expected output:

```bash
# (a) make precommit — all gates green
make precommit

# (b) make check-index — index byte-stable
make check-index

# (c) Index length is 180
python3 scripts/build-index.py | jq 'length'

# (d) Exactly 2 entries carry a class key
python3 scripts/build-index.py | jq '[.[] | select(has("class"))] | length'

# (e) No three-component security/... IDs; go-security count stays 18
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("security/"))] | length'
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("go-security/"))] | length'

# (f) New rule_ids resolve against the citation gate (non-vacuous AC5, 3 IDs per spec AC5)
jq -n '[{kind:"rule",rule_id:"go-security/ssrf-user-controlled-url"},{kind:"rule",rule_id:"go-security/xss-untrusted-html"},{kind:"rule",rule_id:"go-security/resource-ownership"}]' > /tmp/security-findings.json
bash scripts/validate-citations.sh /tmp/security-findings.json > /tmp/security-validated.json
jq '.findings | length' /tmp/security-validated.json  # expect: 3
jq '.dropped_count' /tmp/security-validated.json       # expect: 0

# (g) ast-grep rule-test harness still green (no detector added, no fixture changed)
ast-grep test -c sgconfig.yml
```

### 5. Scope-lock negatives (AC7)

Run these and confirm each prints the expected value (grep/ls based — no git, `.git` is masked):

```bash
ls rules/security/*.yml | wc -l                          # expect: 5 (detector count unchanged)
grep -c '"Class"' scripts/build-index.py                  # expect: >=1 (unchanged from prompt 2 — walker Class support present, not removed)
grep -c '^### RULE go-security/' docs/security/security-review-guide.md   # expect: 9 (7 judgment + 2 invariant, unchanged)
```

The out-of-scope files (`scripts/validate-citations.sh`, `commands/*.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, `.maintainer.yaml`, `scenarios/`) carry no RULE-block or class content and are not touched by any requirement in this prompt — do not modify them.

### 6. Do NOT commit

Do NOT run `git` of any kind — the container's `.git` is masked (`hideGit: true`) and dark-factory's `workflow: direct` post-prompt commit stages and commits all dirty files on completion (repo convention: "Do NOT commit — dark-factory handles git"). Touched paths expected in the daemon's commit: `docs/security/security-review-guide.md`, `CHANGELOG.md`.

</requirements>

<constraints>
- **Documentation only:** this prompt records the layout decision and the CHANGELOG entry; no directories, runner cases, detectors, or walker/schema edits ship.
- **Layout decision scope:** the recorded decision is exactly spike Finding 2 — per-language `rules/security/{go,python,node}/` split + a runner case mirroring the `node/frontend` special-case in `scripts/ast-grep-runner.sh`; go-first v1 stays flat. No `_shared/` or other invented layout convention.
- **No changes to:** `scripts/validate-citations.sh`, `commands/*.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, `.maintainer.yaml`, `scenarios/`, `rules/security/`, `scripts/build-index.py`, `docs/rule-block-schema.md` (all shipped/locked in prompts 1/2 or out of scope).
- **CHANGELOG:** single `## Unreleased` section above `## v0.49.0` with exactly one `feat:` bullet; no `## vX.Y.Z` bump; no verification noise in the bullet.
- **Guide reconciliation:** deferral phrasing (`follow-up task`, `ships in a follow-up`, `ship.*follow-up`, `until then`) returns 0; the `## Tiers` first three paragraphs are not modified.
- **Index gates:** `make check-index` and `make precommit` exit 0; index stays 180 entries; `class` count stays 2.
- **Git discipline:** no git inside the container (hideGit masks `.git`); the daemon owns the post-prompt commit.
- **Generic content only:** the layout prose and changelog bullet use no trading or project-specific domains.
</constraints>

<verification>
All commands are container-executable (repo root). No git — `.git` is masked.

```bash
# 1. Cross-language layout decision recorded
grep -n 'rules/security/{go,python,node}' docs/security/security-review-guide.md
# expect: >=1 line

# 2. Detector count unchanged (negative)
ls rules/security/*.yml | wc -l
# expect: 5

# 3. Precommit green
make precommit   # expect: exit 0

# 4. Index gate green
make check-index
python3 scripts/build-index.py | jq 'length'                               # expect: 180
python3 scripts/build-index.py | jq '[.[] | select(has("class"))] | length' # expect: 2
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("security/"))] | length'   # expect: 0
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("go-security/"))] | length'  # expect: 18

# 5. AC5 non-vacuous: 3 new rule_ids resolve via the citation gate (per spec AC5)
jq -n '[{kind:"rule",rule_id:"go-security/ssrf-user-controlled-url"},{kind:"rule",rule_id:"go-security/xss-untrusted-html"},{kind:"rule",rule_id:"go-security/resource-ownership"}]' > /tmp/security-findings.json
bash scripts/validate-citations.sh /tmp/security-findings.json > /tmp/security-validated.json
echo "exit=$?"
jq '.findings | length' /tmp/security-validated.json    # expect: 3
jq '.dropped_count' /tmp/security-validated.json        # expect: 0

# 6. ast-grep rule-test harness still green
ast-grep test -c sgconfig.yml   # expect: exit 0

# 7. CHANGELOG entry present
grep -c '^## Unreleased' CHANGELOG.md                    # expect: >=1
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'   # expect: >=1

# 8. Final guide reconciliation — no deferral phrasing
grep -cE 'follow-up task|ships in a follow-up|ship.*follow-up' docs/security/security-review-guide.md   # expect: 0
grep -c 'Judgment/invariant-tier RULE blocks in this guide' docs/security/security-review-guide.md     # expect: 0
grep -c 'until then' docs/security/security-review-guide.md                                            # expect: 0

# 9. Final state — only the two intended files carry changes (do NOT commit)
grep -c 'Cross-language detector layout' docs/security/security-review-guide.md   # sanity: guide edited
grep -c '^## Unreleased' CHANGELOG.md                                              # sanity: changelog edited
```

</verification>

<notes>
- **No new RULE blocks in this prompt.** All 9 new blocks ship in prompts 1 and 2. Prompt 3 is documentation + CHANGELOG + gates only. If a regression surfaces in the index, that's a bug in prompts 1 or 2 — fix in those prompts, not here.
- **AC10 (operator rung) is out of scope for this prompt.** Scenario 007 / 008 walks and the new SSRF inline fixture run on the merged plugin at spec-verification time. The management session handles the verification ladder; this prompt only commits the documentation closer.
- **The cross-language layout decision is documentation only.** Spike Finding 2 records the chosen shape but no directories ship now. Future cross-language expansion creates the directories and runner cases — separate spec.
- **CHANGELOG bullet wording.** One bullet, one feature, one `feat:` prefix. Do not list prompts 1/2/3 separately; the changelog reader cares about the feature, not the prompt sequence that built it.
- **Field order is frozen from prompts 1/2** (schema + spec 011 constraint): `**Trigger**:` after `**Enforcement**:`, `**Class**:` after `**Trigger**:`. This prompt must not re-order any block.
- **The `## Cross-language detector layout` section lives at the end of the guide.** It is a forward-looking design note, not a current-state description. Future readers hitting the spec at v0.50.0+ will read it as "this is where we're going"; readers today read it as "this is the recorded decision, not yet executed".
- **Do NOT bump the CHANGELOG to a `## vX.Y.Z` section.** Release tail is the maintainer-agent-releaser per `.maintainer.yaml` `autoRelease: true` after merge. This prompt ships only `## Unreleased`.
</notes>
