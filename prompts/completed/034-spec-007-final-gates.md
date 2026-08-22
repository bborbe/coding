---
status: completed
spec: [007-security-rule-base]
summary: 'Verified the shipped 5-rule security base end-to-end: citation gate accepts all 5 ids, index holds exactly 5 mechanical go-security-specialist rules byte-identical to the regenerated one, all per-detector and full rule-test gates pass (51/51), scope-lock negatives hold, CHANGELOG Unreleased entry appended, and make precommit exits 0'
execution_id: coding-security-rule-base-exec-034-spec-007-final-gates
dark-factory-version: dev
created: "2026-08-22T23:25:00Z"
queued: "2026-08-22T21:36:42Z"
started: "2026-08-22T21:42:46Z"
completed: "2026-08-22T21:43:54Z"
branch: dark-factory/security-rule-base
---

<summary>
- Runs the cross-cutting acceptance gates for the whole security rule base: the citation checker accepts a findings list that cites all 5 new security rules by id (AC5)
- Verifies the rule index contains exactly the 5 new rules, all machine-enforced under the security-specialist owner, and that the stored index matches the regenerated one byte-for-byte (the git-based proof runs on the operator side)
- Verifies scope-lock: no `agents/security-verifier.md`, no `commands/*.md` change, exactly 5 files in `rules/security/` (AC8, via filesystem checks — the git-based `git status` evidence is moved to the operator ladder)
- Re-runs every per-detector rule-test and the full `ast-grep test -c sgconfig.yml` gate (AC1-AC3)
- Adds the `## Unreleased` CHANGELOG entry summarizing the shipped feature (repo precedent: spec-006's final prompt 030 did the same; `docs/changelog-guide.md` governs format)
- `make precommit` exits 0 at the end — this is the final prompt; after it all Acceptance Criteria except the operator-side ones are met
</summary>

<objective>
Run the final cross-cutting verification of the shipped 5-rule security base: citation-gate acceptance, index exactly-5 evidence, scope-lock negatives, the full rule-test harness, and the changelog entry — leaving `make precommit` green. This is prompt 4 of 4 and depends on prompts 1-3 (all 5 detectors + tests + snapshots, the 5-block guide, and the README/llms.txt/agent integration all exist).
</objective>

<context>
Read `CLAUDE.md` (repo root) for conventions, and `docs/changelog-guide.md` for the `## Unreleased` entry format (required `<prefix>: <what>` bullets; `feat:` for new features).
Read `scripts/validate-citations.sh` (full) — it reads a JSON file of findings (flat list or owner-grouped) whose dicts carry a `rule_id`, resolves each against `rules/index.json`, exits 0 only when every id resolves. Input via file arg or stdin.
Read `scripts/check-coverage.sh` and the `check-index` Makefile target — they are the repo's drift guards that this prompt's index/coverage verification relies on.
Read `rules/index.json` (head) and `docs/security/security-review-guide.md` (full) to confirm the end state before verifying.
Confirm the environment: `ast-grep --version` is 0.45.1, `jq` and `python3` are present.
</context>

<requirements>
1. Run the citation-gate acceptance (AC5). Create a temp fixture `/tmp/findings-security.json` citing all 5 new rule ids (flat list — the validator's walk() handles flat lists):
   ```json
   [
     {"rule_id": "go-security/tls-insecure-skip-verify", "message": "tls.Config{InsecureSkipVerify: true}"},
     {"rule_id": "go-security/crypto-insecure-random", "message": "import \"math/rand\""},
     {"rule_id": "go-security/crypto-weak-algorithm", "message": "md5.Sum"},
     {"rule_id": "go-security/sql-string-interpolation", "message": "db.Query(\"...\" + x)"},
     {"rule_id": "go-security/hardcoded-secret", "message": "token := \"sk-live-1234567890\""}
   ]
   ```
   Run `bash scripts/validate-citations.sh /tmp/findings-security.json` — must exit 0 (all 5 ids resolve against the regenerated `rules/index.json`). If it exits 1, an id is missing from the index — the index and guide are out of sync; do not weaken the fixture, fix the index (re-run `make build-index` only if the guide genuinely changed, then verify again).

2. Verify the index lists exactly the 5 new rules as mechanical, owner `go-security-specialist` (AC4, container form):
   - `python3 scripts/build-index.py | jq '[.[] | select(.id | test("go-security/(tls-insecure-skip-verify|crypto-insecure-random|crypto-weak-algorithm|sql-string-interpolation|hardcoded-secret)"))] | length'` returns 5.
   - Each of those 5 has `enforcement_type == "mechanical"` and `owner == "go-security-specialist"` (check with jq: `... | .[] | {id, owner, enforcement_type}`).
   - `make check-index` exits 0 — this is the byte-identical-committed-index guard (the non-git equivalent of AC4's `git diff rules/index.json` empty check; `.git` is masked in this container so the git form runs on the operator side of the spec's Verification ladder).

3. Verify per-detector and full rule-test gates (AC1-AC3):
   - For each of the 5 detectors: `ast-grep test -c sgconfig.yml -f <detector>` exits 0 with a PASS line naming the rule.
   - `ast-grep test -c sgconfig.yml` exits 0 with 51 passed; 0 failed.
   - `grep -n 'check-rule-tests' Makefile` returns the `precommit:` line containing `check-rule-tests` (AC3).

4. Verify scope-lock negatives (AC8, container form — filesystem checks, not git):
   - `test ! -f agents/security-verifier.md` — no new agent file.
   - `ls rules/security/*.yml | wc -l` returns 5 — no extra or missing detectors.
   - `grep -L 'security-review-guide\|go-security/' commands/code-review.md` — `commands/code-review.md` must contain none of this feature's content, proving it was not modified (dark-factory commits only the files this prompt touched; the git-based `git status --short` evidence for AC8 runs on the operator side of the spec's Verification ladder).
   - `grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md` returns 0 lines and `grep -c '^### RULE go-security/' docs/security/security-review-guide.md` returns 5 (AC6 re-confirmation).

5. Add the `## Unreleased` CHANGELOG entry. Read `CHANGELOG.md`'s head: resolve the topmost released version at execution time (do NOT hardcode it — it is currently `## v0.45.6` but moves with every release). Insert immediately below the header block (before the topmost `## v...` section), exactly these bullets:
   ```
   ## Unreleased

   - feat: Ship the 5-rule mechanical security rule base in rules/security/ (tls-insecure-skip-verify, crypto-insecure-random, crypto-weak-algorithm, sql-string-interpolation, hardcoded-secret), each with a rule-tests/security fixture proving it fires
   - fix: Repair tls-insecure-skip-verify's silent-zero (value scoping now via keyed_element node-text regex, pinned to ast-grep 0.45.1)
   - feat: Add docs/security/security-review-guide.md (5 RULE blocks, owner go-security-specialist) and register it in README.md, llms.txt, and agents/go-security-specialist.md
   - feat: Wire ast-grep test -c sgconfig.yml into make precommit as check-rule-tests (CI gate over the native rule-test harness); build-index.py now walks docs/security/*.md
   ```
   Follow `docs/changelog-guide.md` formatting rules. If `## Unreleased` already exists, append to it instead of creating a second one (do not duplicate the header).

6. Run `make precommit` — must exit 0. This is the final gate; a non-zero exit means the task is not done. Fix any failing check and re-run (per the CLAUDE.md fix-loop: re-run only the failing target first, then full precommit once).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. `.git` is a worktree pointer file, unusable inside the container; do NOT run `git` commands. Git-based evidence (AC4 `git diff rules/index.json` empty, AC8 `git status --short` scope-lock) is covered by the operator-executable rung of the spec's Verification ladder (`make release-check` before tagging; `/coding:pr-review` fixture run after merge).
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt.
- No new agent file, no command change: do not create `agents/security-verifier.md`, do not modify `commands/code-review.md` or any `commands/*.md`.
- Do NOT weaken or re-scope any detector, rule-test, guide block, or index entry — this prompt verifies and records, it does not redesign. The only file this prompt writes besides verification artifacts is `CHANGELOG.md`.
- `scripts/build-index.py` stays Python stdlib only. `scripts/validate-citations.sh` is unchanged (AC non-goal: no `invariant_id` support in this task).
- `rules/index.json` must not be hand-edited — it is a derived artifact; if it drifts, regenerate via `make build-index`.
- No config knobs, opt-out flags, or tunable thresholds added anywhere.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — `.git` is masked).
```bash
# --- Requirement 1: citation gate accepts all 5 rule ids (AC5) ---
bash scripts/validate-citations.sh /tmp/findings-security.json > /dev/null && echo "validate-citations: ok (exit 0)"

# --- Requirement 2: index exactly 5 new rules, mechanical, correct owner (AC4) ---
python3 scripts/build-index.py | jq '[.[] | select(.id | test("go-security/(tls-insecure-skip-verify|crypto-insecure-random|crypto-weak-algorithm|sql-string-interpolation|hardcoded-secret)"))] | length'
# must print 5
python3 scripts/build-index.py | jq '.[] | select(.id | test("go-security/(tls-insecure-skip-verify|crypto-insecure-random|crypto-weak-algorithm|sql-string-interpolation|hardcoded-secret)")) | {id, owner, enforcement_type}'
# must show owner=go-security-specialist and enforcement_type=mechanical on all 5
make check-index   # must exit 0 (regenerated index == committed index)

# --- Requirement 3: per-detector + full rule-test gates (AC1-AC3) ---
for f in tls-insecure-skip-verify crypto-insecure-random crypto-weak-algorithm sql-string-interpolation hardcoded-secret; do
  ast-grep test -c sgconfig.yml -f "$f" 2>&1 | grep -q "PASS go-security/$f" && echo "$f PASS: ok"
done
ast-grep test -c sgconfig.yml 2>&1 | tail -1   # must show 51 passed; 0 failed
grep -n 'check-rule-tests' Makefile            # must hit the precommit: phony line

# --- Requirement 4: scope-lock negatives (AC8, filesystem form) ---
test ! -f agents/security-verifier.md && echo "no new agent: ok"
ls rules/security/*.yml | wc -l                # must return 5
grep -L 'security-review-guide\|go-security/' commands/code-review.md && echo "commands/code-review.md untouched: ok"
grep -c '^### RULE go-security/' docs/security/security-review-guide.md   # must return 5
grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md   # must return 0 lines

# --- Requirement 5: changelog present ---
grep -n -m1 '^## Unreleased' CHANGELOG.md      # must return a line
grep -n '5-rule mechanical security rule base' CHANGELOG.md   # must return >= 1 line

# --- Requirement 6: full precommit green ---
make precommit   # must exit 0
```
</verification>
