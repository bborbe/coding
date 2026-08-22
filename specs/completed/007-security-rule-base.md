---
status: completed
tags:
    - dark-factory
    - spec
approved: "2026-08-22T21:17:17Z"
generating: "2026-08-22T21:18:00Z"
prompted: "2026-08-22T21:33:08Z"
verifying: "2026-08-22T21:48:55Z"
completed: "2026-08-22T21:49:03Z"
branch: dark-factory/security-rule-base
---

## Summary

- Ship the foundational security rule base for Security Review Mode: 5 mechanical (`MUST`) detectors in `rules/security/*.yml`, each proven to fire on a bad sample and stay silent on a good sample.
- Fix the one broken detector (`tls-insecure-skip-verify.yml`) whose value scoping currently matches zero findings — the repo's documented "silent zero" failure class.
- Clean and ship `docs/security/security-review-guide.md` with exactly 5 `### RULE` blocks (owner `go-security-specialist`, IDs `go-security/<slug>`), dropping the judgment/invariant tiers to a follow-up task.
- Add per-rule acceptance tests using the repo's native `ast-grep test` mechanism (`rule-tests/security/*-test.yml` valid/invalid snippets) and wire `ast-grep test -c sgconfig.yml` into `make precommit` (new `check-rule-tests` target), so a detector that silently emits zero findings fails CI instead of shipping quietly.
- Register the guide in the repo's "Adding a new guide" integration points (README.md, llms.txt, `agents/go-security-specialist.md`) and extend `scripts/build-index.py` to walk `docs/security/*.md`, regenerating `rules/index.json`.

## Problem

The `rules/security/tls-insecure-skip-verify.yml` detector ships but matches zero findings: the Go composite-literal value-scoping form it uses is not valid for the installed ast-grep grammar, and the repo has a documented history of exactly this failure (`rules/go/no-fmt-errorf.yml` was mis-parsed the same way). A detector that never fires is worse than no detector — it creates the illusion of coverage. Security Review Mode cannot start from a rule base whose flagship detector is dead code, and there is currently no automated guard that would catch a new detector silently matching nothing. The repo already has a native rule-test harness (`rule-tests/` + `ast-grep test -c sgconfig.yml`, 46 tests passing) but it is NOT wired into `make precommit` or CI, so nothing today fails a detector that stops firing. Task 1 of Security Review Mode must deliver a trustworthy, mechanically-enforced rule base with a CI gate that proves every detector actually fires.

## Goal

After this work, the repo ships a 5-rule mechanical security rule base. Each detector in `rules/security/*.yml` fires on its own invalid snippet and stays silent on its own valid snippet in the repo's native rule-test harness, and a new `make precommit` gate (`check-rule-tests`, running `ast-grep test -c sgconfig.yml`) fails CI whenever any detector violates that contract. `rules/index.json` lists all 5 rules as `mechanical`, owned by `go-security-specialist`, sourced from a clean `docs/security/security-review-guide.md` that contains exactly the 5 RULE blocks and no judgment/invariant-tier blocks. The guide is registered in README.md, llms.txt, and the `go-security-specialist` agent's source-of-truth reference. The end state is a rule base that any downstream review funnel can trust: a finding means a real violation, and a missing finding means the detector's fixture contract was validated.

## Non-goals

- Do NOT ship judgment-tier or invariant-tier RULE blocks (SSRF, authz/IDOR, invariant-preservation) — they are a later task of the Security Review Mode goal.
- Do NOT ship the remaining `rules/security` mechanical detectors from the design (`subprocess`, `debug-endpoints`, `http-timeouts`, `deps`/toolchain) — separate later tasks.
- Do NOT split detectors per language (`rules/security/{go,python,node}/`) or add a runner special-case like the node/frontend one — a later task; v1 ships flat under `rules/security/`.
- Do NOT change `scripts/validate-citations.sh` (`invariant_id` support) — a later task.
- Do NOT change any command (`--security` flag on pr-review / code-review / local-review) — a later task.
- Do NOT create `agents/security-verifier.md` or change `commands/code-review.md` — no new agent in this task.
- Do NOT commit or touch `security-spike-notes.md` — internal design notes, stays untracked in the source `coding/` repo and is absent from this worktree.
- Do NOT add any config knob, opt-out flag, or tunable threshold to the detectors or the harness — the fixture contract (bad ≥ 1, good = 0) is the only acceptance surface; a future consumer demanding variation is a separate spec.
- Do NOT change the Go agent repo — separate.

## Acceptance Criteria

**Scenario coverage: NO new scenario.** The behavior is fully reachable by scripted integration checks running real `ast-grep` against real fixture files — the same tier as the existing `scripts/acceptance.sh` and `rule-tests/`. A slow E2E scenario adds no signal here.

- [ ] **AC1 — tls detector fixed and tested:** `rule-tests/security/tls-insecure-skip-verify-test.yml` exists with valid (good) and invalid (bad) Go snippets; `ast-grep test -c sgconfig.yml -f tls-insecure-skip-verify` passes (invalid snippet yields a finding, valid snippet yields none) — evidence: test exit 0 + per-case PASS output.
- [ ] **AC2 — 4 new detectors fire and are tested:** for each of `crypto-insecure-random`, `crypto-weak-algorithm`, `sql-string-interpolation`, `hardcoded-secret`, a `rule-tests/security/<detector>-test.yml` exists with valid/invalid Go snippets and `ast-grep test -c sgconfig.yml -f <detector>` passes (invalid → finding, valid → none) — evidence: per-detector test exit 0 + per-case PASS output.
- [ ] **AC3 — rule-test gate green and wired:** `ast-grep test -c sgconfig.yml` exits 0 (all existing 46 tests + new security tests), `grep -n 'check-rule-tests' Makefile` returns line ≥1 inside the `precommit` phony list, and `make precommit` exits 0 after all changes — evidence: exit codes + grep hit.
- [ ] **AC4 — index lists exactly the 5 new rules as mechanical:** `python3 scripts/build-index.py | jq '.[] | select(.id | test("go-security/(tls-insecure-skip-verify|crypto-insecure-random|crypto-weak-algorithm|sql-string-interpolation|hardcoded-secret)"))'` lists exactly 5 entries, each with `owner: go-security-specialist` and `enforcement_type: mechanical`, and `git diff rules/index.json` is empty after `make build-index` and commit — evidence: stdout JSON content (exactly 5 rows) + empty diff (negative).
- [ ] **AC5 — citation validation accepts the new rules:** `bash scripts/validate-citations.sh` on a JSON fixture citing all 5 new `rule_id`s exits 0 — evidence: exit code.
- [ ] **AC6 — guide is clean and exactly scoped:** `docs/security/security-review-guide.md` exists; `grep -c '^### RULE go-security/'` returns 5; `grep -nE 'DRAFT|~/Downloads|security-spike-notes'` returns 0 lines; `grep -cE 'RULE go-security/(ssrf|authz|invariant)'` returns 0 — evidence: file presence + grep counts.
- [ ] **AC7 — integration references registered:** `grep -n 'security-review-guide' README.md`, `llms.txt`, and `agents/go-security-specialist.md` each return line ≥1 — evidence: grep hits per file.
- [ ] **AC8 — no scope leak (negative):** `git status --short` lists no modification to `commands/code-review.md`, no file `agents/security-verifier.md`, and `ls rules/security/*.yml` yields exactly 5 files — evidence: git status + file listing count.

## Verification

## Container-executable (runs inside the YOLO container at prompt time)

- `make precommit` — exits 0 (includes `check-links`, `check-json`, `check-index`, `check-coverage`, `check-acceptance`, new `check-rule-tests`, `bench-test`).
- `ast-grep test -c sgconfig.yml` — exits 0 (all existing + new security rule-tests).
- Per-detector (x5): `ast-grep test -c sgconfig.yml -f <detector>` — reports the test passing (invalid snippet → ≥1 finding, valid snippet → 0). (`ast-grep` 0.45.1, `jq`, `python3` are present in the container — the existing `check-acceptance` already requires them.)
- `python3 scripts/build-index.py | jq '.[] | select(.id | startswith("go-security/"))'` — lists the 5 new rules, no network required.
- `grep -c '^### RULE go-security/' docs/security/security-review-guide.md` returns 5; `grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md` returns 0.
- `grep -n 'security-review-guide' README.md llms.txt agents/go-security-specialist.md` returns ≥1 hit per file.
- `bash scripts/validate-citations.sh <fixture-with-5-rule-ids>` exits 0.

## Operator-executable (runs on the host after PR merge, spec verification ladder)

- `make release-check` — precommit + `check-versions` clean, run before tagging.
- `/coding:pr-review` local run on a fixture repo — must report the new rules resolving (owner `go-security-specialist` findings cite the new `rule_id`s); run by the operator or this repo's own review pipeline.

## Desired Behavior

1. **Working tls detector.** `rules/security/tls-insecure-skip-verify.yml` is authored fresh (the file is untracked in the source repo and absent from the worktree) using the pinned pattern in Constraints item 1; it matches `tls.Config{InsecureSkipVerify: true}` composite literals and nothing else: ≥1 finding on the tls `invalid:` snippet, 0 on the `valid:` snippet (which sets `MinVersion` instead). The authored YAML carries no `DRAFT` header and no debug trail.
2. **Four new mechanical detectors.** `rules/security/crypto-insecure-random.yml` (flags the `math/rand` import), `crypto-weak-algorithm.yml` (flags `md5`/`sha1`/`des` `Sum`/`New`/`NewCipher`/`NewTripleDESCipher` calls), `sql-string-interpolation.yml` (flags `$DB.QueryContext`/`$DB.Query`/`$DB.ExecContext`/`$DB.Exec` called with a `$A + $B` statement argument), and `hardcoded-secret.yml` (flags short-declaration, assignment, `const`, and `var` forms where the variable name matches a secret identifier and the value is a quoted literal ≥12 characters). Each fires ≥1 on its bad fixture and 0 on its good fixture.
3. **Security review guide.** `docs/security/security-review-guide.md` is authored fresh (the draft is untracked in the source repo and absent from the worktree) and contains exactly 5 `### RULE go-security/<slug>` blocks conforming to `docs/rule-block-schema.md` (Owner → Applies when → Enforcement field order, Bad/Good examples, no `**Trigger**:` on mechanical rules), owner `go-security-specialist` throughout. It must NOT contain a DRAFT banner, any `~/Downloads/` references, any reference to `security-spike-notes.md`, or any judgment/invariant-tier RULE blocks. The three-tier framing (mechanical / judgment / invariant) remains as prose, with a sentence stating the judgment and invariant tiers ship in a follow-up task. Bad/Good examples use generic domains (User, Order, Product), never trading terms.
4. **Guide integration.** README.md gains a table entry linking `docs/security/security-review-guide.md`; llms.txt gains a matching bullet; `agents/go-security-specialist.md` names the new guide alongside `go-security-linting.md` and `teamvault-conventions.md` as source of truth for its owned rules. No new agent file and no `commands/code-review.md` change.
5. **Index walker extension.** `scripts/build-index.py` emits RULE blocks from both `docs/*.md` and `docs/security/*.md` (keeping the `rule-block-schema.md` skip and duplicate-ID detection across both sets), and `rules/index.json` is regenerated via `make build-index` so all 5 new rules appear with `enforcement_type: mechanical` and repo-relative `doc_path: docs/security/security-review-guide.md`.
6. **Per-rule acceptance tests (native harness).** New `rule-tests/security/*-test.yml` files — one per detector (`tls-insecure-skip-verify`, `crypto-insecure-random`, `crypto-weak-algorithm`, `sql-string-interpolation`, `hardcoded-secret`) — each with `id:` matching the rule, `valid:` snippets (expect 0 findings) and `invalid:` snippets (expect ≥1 findings) in Go, following the existing convention in `rule-tests/admin-port-9090-test.yml`. Snapshots are generated once via `ast-grep test -c sgconfig.yml -U` (with `rule-tests/__snapshots__/go-security/` pre-created) and committed. A new `check-rule-tests` Makefile target running `ast-grep test -c sgconfig.yml` joins the `precommit` phony list — the repo's first CI enforcement of its native rule-test harness.
7. **Silent-zero regression guard.** The `check-rule-tests` precommit gate fails CI whenever a security detector stops firing (its invalid snippet no longer matches) or over-fires (its valid snippet matches). Detectors keep the standard `ignores:` (`**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`); no committed bad-fixture dir is needed — test snippets live in `rule-tests/` which the runner never scans, so there is no self-flagging concern.

## Constraints

- **Rule identity:** all new rule IDs use the two-component `go-security/<slug>` form (per spike Finding 1 — the repo's existing security family), NOT the design's three-component `security/<topic>/<slug>` form. Owner is `go-security-specialist` in every block and every index entry.
- **Approval discipline:** never edit frontmatter status manually — approval goes through `dark-factory spec approve` with explicit user confirmation (repo rule). This spec lives in `specs/` until approved.
- **Run flags:** `hideGit: true`, `autoRelease: false`, `worktree: false`, `pr: false` for this run; PRs are created manually. `security-spike-notes.md` is not present in this worktree and must never be committed from the source repo either.
- **No new agent, no command change:** do not create `agents/security-verifier.md`, do not modify `commands/code-review.md` or any `commands/*.md`.
- **Precommit stays green after every prompt:** each of the 4 prompts is atomic and independently verifiable; `make precommit` exits 0 at the end of each.
- **Rule-test discipline:** new `rule-tests/security/*-test.yml` files follow the existing convention (`id:` + `valid:`/`invalid:` snippet blocks — see `rule-tests/admin-port-9090-test.yml`); snapshots are generated via `ast-grep test -c sgconfig.yml -U` with `rule-tests/__snapshots__/go-security/` pre-created, then committed; the plain `ast-grep test -c sgconfig.yml` must pass in CI. `scripts/build-index.py` stays Python stdlib only.
- **Author-fresh files:** `rules/security/tls-insecure-skip-verify.yml` and `docs/security/security-review-guide.md` are untracked in the source repo and ABSENT from the worktree (not in git). Prompt 1 AUTHORS the tls detector fresh from the pinned pattern in reference-implementation note 1 AND authors the guide skeleton (three-tier prose + tls RULE block); prompt 2 appends the other four RULE blocks; prompt 3 does integration only and does not edit the guide unless a verification check fails. The `check-coverage.sh` orphan-YAML rule requires each `rules/security/*.yml` to be index-referenced in the same prompt that creates it — which is why guide authoring, the `build-index.py` walk extension, and the index regen are pulled forward into prompts 1-2.
- **Reference implementation notes (ast-grep 0.45.1, empirically validated — do NOT re-derive):** the prompt-creator must encode these exact proven forms; the rule-test snippets (valid/invalid) are the final gate.
  1. `tls-insecure-skip-verify`: root `keyed_element` whose node text matches `^InsecureSkipVerify:\s*true$`, constrained by `inside: literal_value inside: composite_literal has: field type, kind qualified_type, all [has kind package_identifier regex ^tls$, has field name kind type_identifier regex ^Config$]`. Grammar notes: in type position `tls.Config` is a `qualified_type` with a fieldless `package_identifier` child plus a `name` field — NOT a `selector_expression`; `true` is its own node kind named `true` (quote it `'true'` in YAML); `keyed_element` has no named `key`/`value` fields in this grammar, so value scoping goes through the node-text regex.
  2. `crypto-insecure-random`: `kind: import_spec` with `has: {field: path, regex: '^"math/rand"$'}` — flags the import; the guide states judgment-tier LLM adjudication decides whether the usage is security-relevant (this keeps `enforcement_type: mechanical` because the enforcement field cites the YAML path).
  3. `crypto-weak-algorithm`: `kind: call_expression` with `has: {kind: selector_expression, all: [has {kind: identifier, regex: '^(md5|sha1|des)$'}, has {field: field, kind: field_identifier, regex: '^(Sum|New|NewCipher|NewTripleDESCipher)$'}]}`.
  4. `sql-string-interpolation`: use the structural form — `kind: call_expression` whose `function` is a `selector_expression` on `QueryContext|Query|ExecContext|Exec` (operand any expression `$DB`) and whose `arguments` is an `argument_list` containing a `binary_expression` with an `interpreted_string_literal` child. (The originally-pinned `any:` of `$DB.QueryContext($CTX, $A + $B)`, `$DB.Query($A + $B)`, etc. silently misses the bare `Query`/`Exec` shapes — a bare `$DB.Query($A + $B)` parses as a Go `type_conversion_expression` in ast-grep 0.45.1, the same silent-zero class as `rules/go/no-fmt-errorf.yml`. The structural form is verified to fire on all four call shapes and stay silent on parameterized queries — updated 2026-08-22.)
  5. `hardcoded-secret`: `rule: {any: [pattern $NAME := $VALUE, pattern $NAME = $VALUE, pattern const $NAME = $VALUE, pattern var $NAME = $VALUE]}` with TOP-LEVEL `constraints:` (a sibling of `rule`, NOT nested — ast-grep rejects nested constraints). NAME regex `(?i)(token|secret|password|credential|apikey|api_key|api-key|auth_key|auth-token)`, VALUE regex `^".{12,}"$`.
- **Snippet contract:** in each `rule-tests/security/*-test.yml`, every `valid:` snippet must be clean against its own rule (0 findings) and every `invalid:` snippet must trip its own rule (≥1 finding); snippets are repo-controlled Go files, never generated at runtime. Valid snippets must avoid the trigger shapes of their own rule (e.g. the tls valid snippet sets `MinVersion`, not `InsecureSkipVerify`; the rand valid snippet imports `crypto/rand`, not `math/rand`; the secrets valid snippet reads via `os.Getenv`, not a literal).
- **Index walker invariants:** keep walking `docs/*.md`, keep skipping `rule-block-schema.md`, keep duplicate-ID detection across the union of both walked sets, keep byte-stable sorted output so `check-index` stays deterministic.

## Failure Modes

| Trigger | Expected behavior | Recovery | Detection | Reversibility |
|---------|-------------------|----------|-----------|---------------|
| A detector silently emits zero findings (ast-grep grammar drift — the installed ast-grep version differs from 0.45.1, or a pattern regresses) | `check-rule-tests` fails precommit: the detector's `invalid:` snippet no longer produces a finding | Fix the pattern, re-run `ast-grep test -c sgconfig.yml -f <detector>` until the invalid snippet matches, re-run `make precommit` until green | `ast-grep test` FAIL line naming the rule; `make precommit` exits non-zero | Reversible — repo-local, no external state |
| A detector over-matches and fires on its `valid:` snippet (e.g. tls also matches `InsecureSkipVerify: false`) | `check-rule-tests` fails precommit: the `valid:` snippet yields a finding | Tighten the pattern (e.g. the node-text regex `^InsecureSkipVerify:\s*true$`), re-verify against the snippet contract | `ast-grep test` FAIL line naming the rule + snippet | Reversible |
| Guide edited without regenerating the index | `check-index` fails precommit ("rules/index.json is stale") | Run `make build-index`, commit the regenerated `rules/index.json` | `make precommit` exits non-zero on `check-index` | Reversible |
| `build-index.py` walk extension breaks existing `docs/*.md` extraction | `make precommit` `check-index` fails, or duplicate-ID/field errors surface | Revert the walk change; verify the existing rules still derive identically; re-apply the extension | build-index exit 1 with a named doc/rule on stderr | Reversible |
| `ast-grep`/`jq` missing in the container or on a contributor host | `check-rule-tests` (and the existing `check-acceptance`) fails with `ast-grep: command not found` — fail-closed, no silent PASS | Install `ast-grep` (the existing `check-acceptance` preflight already names the install command) | `make precommit` exits non-zero on `check-rule-tests` / `check-acceptance` | Reversible |
| Two prompts run concurrently and both regenerate `rules/index.json` or edit the guide | Last writer wins; a stale or partial index can result | Dark-factory executes prompts in filename order (`1-`…`4-`); each prompt runs `make precommit` as its gate, catching any cross-prompt drift | `check-index` failure at the next prompt's precommit | Partial — index is a derived artifact, regenerable via `make build-index` |
| Go detectors in `rules/security/*` run against non-Go files in a consumer repo (no per-language gating in the runner) | `ast-grep` with a Go grammar on a `.py` file no-ops or errors; errors are tolerated by the funnel, no-ops cost nothing | Deferred — the per-language split is a later task; v1 ships flat with `ignores:` scoping | Not visible at build time; observed in consumer-project reviews | Reversible (no consumer-side state written) |

## Security / Abuse Cases

The feature touches files (detectors, fixtures, guide, index) and adds detectors that later scan untrusted consumer code.

- **Attacker-controlled input:** the detectors will run against consumer PR changed-files — untrusted source code. The rule patterns are repo-controlled constants, not derived from scanned code, so no code-path injection into the rules.
- **Regex safety:** all detector regexes are anchored and bounded (`^…$` on short node texts; the hardcoded-secret VALUE regex is `^".{12,}"$`) — no unbounded backtracking on attacker-supplied source, no ReDoS surface worth defending.
- **Trust boundary:** rule-test snippets and snapshots are committed repo files, never runtime-generated; `ast-grep test -c sgconfig.yml` reads only `rule-tests/` and needs no network, no credentials, no secrets.
- **Self-scan contamination:** test snippets live in `rule-tests/`, which the review runner never scans, so the repo's own review funnel cannot self-flag them; no `rules/security/samples/**`-style ignores are needed.
- **Provenance integrity:** the citation gate (`validate-citations.sh`) rejects invented `rule_id`s against `rules/index.json` — unchanged in this task; the 5 new rules resolve only after prompt 4 regenerates the index.
- **Hang/retry:** harness runs are bounded single-shot commands over fixed fixture files; there is no retry loop and no unbounded scan.
- **Scope-lock:** a `hardcoded-secret` detector that over-fires on ordinary assignments is the highest false-positive risk in the set; the fixture contract (good samples clean against all 5 detectors, anchored regexes) is the guard, and any finding the detector raises remains a MUST-level review item.

## Suggested Decomposition

Prompts generated in this order — each row is one prompt with an auditable scope. The ordering guarantees `make precommit` stays green after every prompt.

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Author `rules/security/tls-insecure-skip-verify.yml` fresh (pinned pattern) + `rule-tests/security/tls-insecure-skip-verify-test.yml` + wire `check-rule-tests` into Makefile `precommit` + author the guide SKELETON (three-tier prose + tls RULE block) + extend `scripts/build-index.py` walk to `docs/security/*.md` + `make build-index` regen (167 entries) | 1, 3, 5, 6, 7 | 1, 3 | — |
| 2 | Ship the 4 new detectors + their `rule-tests/security/*-test.yml` + snapshots + append the 4 remaining RULE blocks to the guide (5 total) + `make build-index` regen (171 entries) | 2, 3, 6, 7 | 2, 3 | prompt 1 (rule-test gate, snapshot dir, guide file, walk extension all exist) |
| 3 | Integration only: README.md row + llms.txt bullet + `agents/go-security-specialist.md` companion-guides list + CLAUDE.md Doc↔Agent alignment row; verify the guide is clean and exactly scoped | 3, 4 | 6, 7 | prompts 1-2 (guide exists with 5 blocks) |
| 4 | Final cross-cutting gates: citation validation (5 rule_ids resolve), index exactly-5 mechanical (`make check-index`), scope-lock negatives, full rule-test harness, CHANGELOG `## Unreleased`, `make precommit` green | 5 | 1, 2, 3, 4, 5, 8 | prompts 1-3 |

Rationale (revised 2026-08-22 to record the executed re-sequencing): the original decomposition (guide in prompt 3, build-index walk + regen in prompt 4) broke `make precommit` between prompts because `scripts/check-coverage.sh` fails on a `rules/security/*.yml` that has no `rules/index.json` reference (orphan-YAML check) — a detector cannot land before the guide block that feeds its index entry exists. Guide authoring (skeleton in prompt 1, grown to 5 blocks in prompt 2), the `build-index.py` walk extension, and the index regen are therefore pulled forward into prompts 1-2 so each prompt that creates detector YAMLs also lands their index references. Prompt 1 is foundational — the tls detector, its rule-test, and the `check-rule-tests` gate (which also starts CI-enforcing the existing 46 rule-tests) land together. Prompt 2 rides prompt 1's gate. Prompt 3 is integration-only (no index impact — the index is byte-stable unless a RULE-block fix forces a regen). Prompt 4 is the final gate: it re-runs every AC check, records the CHANGELOG entry, and must leave `make precommit` green. Prompts 1–2 reference `docs/security/security-review-guide.md` in their detector `message:` text as a forward reference — benign, since `check-links` validates markdown links, not YAML message strings.

## Do-Nothing Option

If this task does not ship, the repo keeps a flagship security detector that provably never fires, no second detector exists, and Security Review Mode starts with no trustworthy mechanical rule base and no CI guard against silent-zero regressions. The gosec-only coverage in `docs/go-security-linting.md` remains the only security guidance; the spike remains untracked design notes. The current approach is not acceptable: a dead detector is actively misleading and the foundation task of the goal is undone.
