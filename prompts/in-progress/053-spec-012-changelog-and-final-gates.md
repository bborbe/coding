---
status: approved
spec: [012-intent-aware-review-and-self-containment]
created: "2026-10-17T20:46:40Z"
queued: "2026-10-17T21:14:48Z"
branch: dark-factory/intent-aware-review-and-self-containment
---

# Changelog entry and final cross-cutting gates

<summary>
- Records the change under an Unreleased heading so the release agent has something to promote
- Runs the full repository gate over the combined result of the three preceding prompts
- Proves the security lens, the other review modes, and the maintainer config are untouched
- Proves the derived rule index carries the five new rules and lost none of the existing ones
- Proves nothing the change adds outside the documented exemption quotes a leaked-planning marker
- Proves every new rule id resolves in the citation validator
- Fails loudly if any of the three preceding prompts has not shipped
</summary>

<objective>
Spec 012's change is releasable and scope-locked: `CHANGELOG.md` gains a `## Unreleased` section with a `feat:` bullet, the full `make precommit` gate passes, and the cross-cutting negative checks hold — the security surface, the sibling review commands, the maintainer config and the scenarios are untouched; the rule index carries 194 entries with nothing removed; and no added artifact outside the documented exemption quotes a leaked-planning marker. This is prompt **4 of 4** for spec 012 and runs after prompts 1-3.
</objective>

<context>
Read fully before writing:

- `CHANGELOG.md` — verified shape: `# Changelog` first content line, then a blank line, the "All notable changes …" paragraph, three SemVer bullets (`* MAJOR …`, `* MINOR …`, `* PATCH …`), a blank line, then `## v0.57.7` as the topmost released section. **There is no `## Unreleased` section today** — this prompt creates it. `scripts/check-changelog-fold.sh` requires the topmost section to be `## Unreleased` when unreleased work exists and forbids a `## Unreleased` below the topmost section; `scripts/rule-checks.sh`'s `changelog/preamble-frozen` check forbids a `## Unreleased` appearing before the "All notable changes" line. Place the new section after the SemVer bullets and immediately before `## v0.57.7`.
- `docs/changelog-guide.md` — the entry format: `- <prefix>: <what> [context]`, prefix required (`feat:` here), one bullet per logical change, specific rather than generic.
- `Makefile` — `precommit` runs `check-links check-changelog-fold check-json check-index check-coverage check-acceptance check-rule-tests bench-test`; `check-index` fails when the committed `rules/index.json` is stale; `build-index` regenerates it.
- `scripts/validate-citations.sh` — the polymorphic citation validator. Invoked from the repo root, it resolves `rules/index.json` from the cwd and exits non-zero when any `kind: rule` finding's `rule_id` is absent from the index. This is the boundary the five new rule ids must cross.
- `scripts/acceptance.sh` — asserted by prompt 2 to contain the self-containment block; unchanged here.
- `docs/self-containment-guide.md`, `agents/self-containment-assistant.md`, `scripts/rule-checks.sh`, `scripts/acceptance.sh`, `commands/pr-review.md`, `docs/selector-mode-guide.md` — shipped by prompts 1-3; read-only here.

**Scope-lock baseline (verified, pinned)**

| Path | Expected state |
|---|---|
| `.maintainer.yaml` | exactly 4 lines: `release:` / `  autoRelease: true` / `prReviewer:` / `  autoApprove: true` |
| `scenarios/*.md` | exactly **10** files (`001-…` through `010-…`) |
| `docs/security/` | exactly 2 files: `security-review-guide.md`, `security-review-pipeline.md` |
| `scripts/validate-citations.sh` | contains `SECURITY_MODEL_FILE` and `invariant` |
| `agents/security-verifier.md` | contains `Falsification checklist` |

**The marker-literal forms (verbatim)**

```
~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
```

`build-index.py` copies each guide's `Owner` / `Applies when` / `Enforcement` field lines verbatim into `rules/index.json`, so the new self-containment entries are the sharpest case for this gate. The CHANGELOG bullet is the other: a bullet that quotes a home-directory path or a planning-directory name puts the marker on a line this change adds, where the adjudicator's changed-line filter cannot drop it.
</context>

<requirements>

### 0. Precondition — fail loudly if prompts 1-3 have not shipped

```bash
jq -r '.[].id' rules/index.json | grep -qxF 'self-containment/no-steering-echoes' \
  || { echo "Status: failed — prompt 1 not yet deployed (self-containment rule ids absent from rules/index.json)"; exit 1; }
grep -q '^self_containment_scan() {' scripts/rule-checks.sh \
  || { echo "Status: failed — prompt 2 not yet deployed (self-containment script checks absent)"; exit 1; }
grep -q '^### Step 0.5: Capture stated intent$' commands/pr-review.md \
  || { echo "Status: failed — prompt 3 not yet deployed (intent capture step absent)"; exit 1; }
grep -q '^## Intent Extension (dormant)$' docs/selector-mode-guide.md \
  || { echo "Status: failed — prompt 3 not yet deployed (intent extension absent)"; exit 1; }
```

If any check fails, STOP and report `Status: failed` with exactly that message. Never report `needs_input` — a missing sibling artifact is a ship-order bug, not a question for a human.

### 1. Add the `## Unreleased` section to `CHANGELOG.md`

Insert, immediately after the three SemVer bullets and immediately before `## v0.57.7`:

```
## Unreleased

- feat: `/coding:pr-review` reads the change's stated intent (`--intent <path>` / `--pr <number>`, plus PR-body auto-detect) and records a deviation the author stated and justified as a decision instead of re-flagging it; a new self-containment rule family (four script-tier checks plus one judgment rule) flags leaked planning context — home-directory paths, requirement ids, planning-directory references, revision meta and steering echoes — in the changed files of any review
```

The bullet must not quote a marker literal. The wording above is deliberately descriptive: "home-directory paths", "requirement ids", "planning-directory references", "revision meta", "steering echoes" — never the literal forms. Do not add a second bullet, and do not touch any released section.

### 2. AC12 — nothing added outside the exemption carries a marker literal

Two container-checkable clauses:

- **The index clause.** Every self-containment entry in `rules/index.json` must be free of a marker literal — the guide's field lines are copied verbatim, so a marker there lands in the index.
- **The change's-own-artifacts clause.** The new CHANGELOG bullet, and the registration lines added to `README.md` / `llms.txt` / `CLAUDE.md` by prompt 1, must be free of a marker literal.

The spec's third clause — a grep over `git diff origin/master...HEAD --unified=0` restricted to the six exempt paths — needs a working `.git` and is therefore on the spec's operator verification rung. The container-safe equivalent is discharged per file: prompt 1 checks the index and registration lines, prompt 3 asserts the marker-matching line count of `commands/pr-review.md` is unchanged and that `docs/selector-mode-guide.md` matches none, and this prompt re-checks the index and the CHANGELOG.

### 3. AC8 — the security surface and the sibling commands are untouched

Assert the pinned scope-lock baseline above holds, and that neither the self-containment nor the intent feature leaked into the security paths:

- no self-containment rule id, no `self_containment_` symbol, and no `--intent` / `INTENT` token anywhere under `docs/security/`, in `scripts/validate-citations.sh`, in `agents/security-verifier.md`, in `.maintainer.yaml`, or in `scenarios/`;
- `.maintainer.yaml` is byte-for-byte the pinned 4 lines;
- `scenarios/*.md` is still exactly 10 files;
- `docs/security/` is still exactly 2 files;
- `bash scripts/acceptance.sh` exits 0.

Do not modify any of those paths. The spec's `git diff --stat origin/master...HEAD` form of this check is on the operator verification rung.

### 4. AC9 — the index carries 194 entries and nothing was removed

- `python3 scripts/build-index.py | jq 'length'` returns **194** (189 pre-existing + 5).
- `make check-index` exits 0 (the committed index byte-matches the live derivation).
- Every self-containment entry resolves in the index, and the four script entries plus the one judgment entry carry the expected `enforcement_type`.

The "nothing removed" property was proven in prompt 1 by snapshotting `rules/index.json` before the regeneration (`comm -23` over the before/after id sets). This prompt re-checks the count and the freshness gate; the spec's `git show origin/master:rules/index.json` + `comm` form is on the operator rung.

### 5. Provenance integrity — every new rule id resolves in the citation validator

Write a synthetic findings file citing all five new rule ids and run the validator from the repo root:

```bash
cat > /tmp/sc-citations.json <<'EOF'
[{"kind":"rule","rule_id":"self-containment/no-home-dir-paths","file":"pkg/order.go","line":1},
 {"kind":"rule","rule_id":"self-containment/no-requirement-ids","file":"pkg/order.go","line":2},
 {"kind":"rule","rule_id":"self-containment/no-planning-doc-refs","file":"pkg/order.go","line":3},
 {"kind":"rule","rule_id":"self-containment/no-revision-meta","file":"pkg/order.go","line":4},
 {"kind":"rule","rule_id":"self-containment/no-steering-echoes","file":"pkg/order.go","line":5}]
EOF
bash scripts/validate-citations.sh /tmp/sc-citations.json > /dev/null
```

Expect exit 0 — no finding dropped. This is the boundary test for the new ids: the ids cross from the guide into the index and out through the validator, which is the same path a real review's findings take.

### 6. AC10 — the full gate

Run `make precommit`. Expect exit 0. Then confirm the CHANGELOG section is present and carries a `feat:` bullet.

### 7. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation. Report `status: failed` if `make precommit` exited non-zero for any reason other than the documented environment gap in `<verification>`; never self-report success on a non-zero exit code.
</requirements>

<constraints>
- **Scope:** this prompt edits `CHANGELOG.md` only. Every other file it reads is read-only. Do not modify `rules/index.json` (regenerate it only if `make check-index` reports it stale, which it must not), `docs/self-containment-guide.md`, `agents/self-containment-assistant.md`, `scripts/rule-checks.sh`, `scripts/acceptance.sh`, `commands/**`, `docs/selector-mode-guide.md`, `docs/security/**`, `scripts/validate-citations.sh`, `agents/security-verifier.md`, `.maintainer.yaml`, `scenarios/**`, `README.md`, `llms.txt`, `CLAUDE.md`.
- **CHANGELOG bullet wording:** one `feat:` bullet, descriptive, no marker literal. Do not quote a home-directory path, a planning-directory name, a requirement-id form, or a revision/sign-off phrase.
- **`## Unreleased` placement:** after the SemVer bullets, immediately before the topmost released heading. A `## Unreleased` anywhere below the topmost section is the stranded-heading failure `check-changelog-fold.sh` reports; a `## Unreleased` before the "All notable changes" line trips `changelog/preamble-frozen`.
- **No new scenario file** — spec 012 ships no scenario. Do not add, edit or delete anything under `scenarios/`.
- **Generic content only:** any example uses User, Order, Product, Customer — never trading or project-specific domains.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit: true`, confirmed in `.dark-factory.log` as `hideGitSource=arg`); git fails with `fatal: not a git repository` and the daemon's `workflow: direct` post-prompt commit stages everything on completion. Every verification check below is git-free by design.
- **Cross-prompt boundary:** this prompt depends on prompts 1, 2 and 3 having shipped. A missing sibling artifact is a failure (`Status: failed`), never `needs_input`.
- **Release tail is out of band:** `.maintainer.yaml` sets `autoRelease: true` and the release is cut by the maintainer-agent-releaser after merge. Do not touch the maintainer config and do not bump a version — spec 012 requires only the `## Unreleased` entry.
</constraints>

<verification>
All commands are container-executable from the repo root. No `git` — the container's `.git` is masked.

```bash
# 1. AC10 — the CHANGELOG section and its feat bullet
grep -c '^## Unreleased$' CHANGELOG.md                                          # expect: 1
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'  # expect: >= 1
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- '       # expect: 1 (one bullet)

# 2. Section placement — Unreleased sits after the preamble and above the top released heading
awk '/^## Unreleased$/{print "unreleased:" NR} /^## v[0-9]/{print "first-released:" NR; exit}' CHANGELOG.md
# expect: unreleased line number < first-released line number
grep -n 'All notable changes' CHANGELOG.md                                       # expect: a line number below the Unreleased line

# 3. AC12 — no marker literal in the new CHANGELOG bullet
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md > /tmp/unreleased.txt
if grep -qE '~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/unreleased.txt; then
  echo "FAIL: marker literal in the Unreleased section"; else echo "OK: Unreleased section is literal-free"; fi

# 4. AC12 — no marker literal in the self-containment index entries
python3 scripts/build-index.py | jq -c '.[] | select(.id|startswith("self-containment/"))' > /tmp/sc-entries.json
if grep -qE '~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/sc-entries.json; then
  echo "FAIL: marker literal in a self-containment index entry"; else echo "OK: index entries are literal-free"; fi

# 5. AC12 — no marker literal on the registration lines added by prompt 1, or in scripts/acceptance.sh
if grep -E 'self-containment' README.md llms.txt CLAUDE.md | grep -qE '~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change'; then
  echo "FAIL: marker literal on a registration line"; else echo "OK: registration lines are literal-free"; fi
if grep -qE '~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' scripts/acceptance.sh; then
  echo "FAIL: marker literal in scripts/acceptance.sh (not an exempt path)"; else echo "OK: acceptance.sh is literal-free"; fi

# 6. AC8 — the security surface and the sibling commands are untouched
if grep -rq 'self-containment\|self_containment_\|--intent\|INTENT' docs/security scripts/validate-citations.sh agents/security-verifier.md .maintainer.yaml scenarios; then
  echo "FAIL: the feature leaked into the security surface or the scenarios"; else echo "OK: security surface and scenarios untouched"; fi
test "$(wc -l < .maintainer.yaml)" = "4" && echo "OK: .maintainer.yaml unchanged" || echo "FAIL: .maintainer.yaml changed"
test "$(ls scenarios/*.md | wc -l)" = "10" && echo "OK: 10 scenarios" || echo "FAIL: scenario count changed"
test "$(ls docs/security/*.md | wc -l)" = "2" && echo "OK: 2 security docs" || echo "FAIL: security doc count changed"
grep -c 'Falsification checklist' agents/security-verifier.md      # expect: 1
grep -c '## Security Extension (dormant)' docs/selector-mode-guide.md   # expect: 1
if grep -q -- '--intent' commands/local-review.md commands/code-review.md; then echo "FAIL: --intent leaked into a sibling command"; else echo "OK: siblings untouched"; fi
bash scripts/acceptance.sh > /dev/null && echo "OK: acceptance exits 0" || echo "FAIL: acceptance non-zero"

# 7. AC9 — index count and freshness
python3 scripts/build-index.py | jq 'length'                     # expect: 194
python3 scripts/build-index.py | jq '[.[] | select(.id|startswith("self-containment/"))] | length'   # expect: 5
python3 scripts/build-index.py | jq '[.[] | select((.id|startswith("self-containment/")) and .enforcement_type=="script")] | length'   # expect: 4
python3 scripts/build-index.py | jq '[.[] | select((.id|startswith("self-containment/")) and .enforcement_type=="judgment")] | length' # expect: 1
make check-index                                                 # expect: exit 0

# 8. Provenance — every new rule id resolves in the citation validator
cat > /tmp/sc-citations.json <<'EOF'
[{"kind":"rule","rule_id":"self-containment/no-home-dir-paths","file":"pkg/order.go","line":1},
 {"kind":"rule","rule_id":"self-containment/no-requirement-ids","file":"pkg/order.go","line":2},
 {"kind":"rule","rule_id":"self-containment/no-planning-doc-refs","file":"pkg/order.go","line":3},
 {"kind":"rule","rule_id":"self-containment/no-revision-meta","file":"pkg/order.go","line":4},
 {"kind":"rule","rule_id":"self-containment/no-steering-echoes","file":"pkg/order.go","line":5}]
EOF
bash scripts/validate-citations.sh /tmp/sc-citations.json > /dev/null
echo "citation validator exit=$?"                                  # expect: 0

# 9. The intent half is present end-to-end
grep -c -- '--intent' commands/pr-review.md                        # expect: >= 3
grep -c '^### Step 0.5: Capture stated intent$' commands/pr-review.md   # expect: 1
grep -c '^## Intent Extension (dormant)$' docs/selector-mode-guide.md   # expect: 1

# 10. AC10 — the full gate
make precommit   # expect: exit 1 ONLY on check-changelog-fold ("not a git repository"), because .git is masked; every other target must pass
make check-links check-json check-index check-coverage check-acceptance bench-test   # expect: exit 0 — the git-free targets are the real in-container gate
```

Note on `make precommit` in this container: the container's `.git` is masked, and `check-changelog-fold` shells out to `git rev-parse --git-dir` (it dies with `FAIL: not a git repository — cannot check the fold`), while `check-rule-tests` runs `ast-grep test`. If `make precommit` fails **only** on a `check-changelog-fold` / `not a git repository` message, report it in the completion report's `## Improvements` as an environment gap (category: GLOBAL) and report `status: success` — the git-free target set above is the real in-container gate, and it passed. Never report `status: partial` or `failed` for this environment gap alone: the daemon's completion-report validator treats any non-`success` status as a prompt failure, refuses to commit the work, and marks the prompt `failed`. Every other target — `check-links`, `check-json`, `check-index`, `check-coverage`, `check-acceptance`, `bench-test` — must pass, and the individual checks above are the evidence.
</verification>

<notes>
- **Why the `## Unreleased` placement is pinned.** `check-changelog-fold.sh` treats a `## Unreleased` below the topmost section as a stranded heading (a fold's residue) and fails; `scripts/rule-checks.sh`'s `changelog/preamble-frozen` check fails when a `## Unreleased` appears before the "All notable changes" line. Between the SemVer bullets and the topmost released heading satisfies both.
- **Why the CHANGELOG wording is descriptive.** The bullet is a line this change adds. A home-directory path or a planning-directory name in it is a marker on an added line, where the adjudicator's changed-line filter cannot drop it — the PR would carry a MUST finding on its own diff. The wording names the marker families in words.
- **Why the index clause matters most.** `build-index.py` copies the guide's `Owner` / `Applies when` / `Enforcement` lines verbatim, so a marker on one of those lines propagates into `rules/index.json`. Prompt 1 pins the field-line wording to prevent it; this prompt re-checks it after the fact.
- **AC8's full form is operator-side.** The spec's `git diff --stat origin/master...HEAD` over the forbidden paths needs a working `.git`; the container-safe equivalent is the pinned baseline table plus the leak greps above. The spec's Verification section carries the git form on its operator rung.
- **AC11 (bench recall) is not covered here.** It needs the released plugin and a complete bench run at the baseline's pin/model/effort/mode, so it lives on the spec's operator verification rung, not in a prompt. Do not attempt to run the bench.
- **AC6 / AC7 are operator-side too.** The behavioural intent checks need the released plugin and a live PR. This prompt only confirms the intent surface is present (verification step 9).
- **Open question for the reviewer:** the spec's AC12 clause 2 is scoped to "lines this PR adds". Without a working `.git` there is no diff, so the container rung discharges it per file (index + registration lines + prompt 3's per-file marker line-count assertions) and the diff-based form is on the operator rung. If the reviewer wants the diff form gated in-container, that would require a git-enabled verification environment, which this repo's `hideGit: true` config does not provide.
</notes>
