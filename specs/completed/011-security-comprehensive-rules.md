---
status: completed
tags:
    - dark-factory
    - spec
approved: "2026-08-23T20:25:32Z"
generating: "2026-08-23T19:58:53Z"
prompted: "2026-08-23T20:42:35Z"
verifying: "2026-08-23T20:58:55Z"
completed: "2026-08-23T21:22:40Z"
branch: dark-factory/security-comprehensive-rules
---

## Summary

- Ship the comprehensive security v1 rule base: 7 judgment-tier RULE blocks (SSRF, XSS/untrusted-html, deserialization, open redirect, webhook verification — MUST; mass assignment, insecure defaults — SHOULD) plus 2 invariant-linked authz rules (resource ownership, tenant isolation — MUST) in `docs/security/security-review-guide.md`, all owner `go-security-specialist`.
- Add a new optional `**Class**: security-invariant` field to the two authz rules; extend `scripts/build-index.py` to emit a `class` index key, and document the new field + key in `docs/rule-block-schema.md`.
- All 9 new rules use the two-component `go-security/<slug>` ID form (spike Finding 1); `rules/index.json` is regenerated (171 → 180 entries) and every citation still validates against the unchanged `validate-citations.sh` contract.
- Record the cross-language detector layout decision (spike Finding 2) in the guide — per-language `rules/security/{go,python,node}/` split + a runner case for cross-language rules, with go-first v1 staying flat — as documentation only, no structural reorganization.
- Definition of Done: an invariant-linked rule (existing IDOR scenarios 007/008) and a new judgment-tier SSRF fixture are each exercised at spec-verification time (finding produced, verified, or correctly rejected).

## Problem

The foundational mechanical security rule base (v0.46-0.49) ships 5 MUST-level ast-grep detectors and the guide states the judgment and invariant tiers "ship in a follow-up task" — this spec is that follow-up. Without it, security review mode can only emit findings on mechanical shapes (hardcoded secrets, TLS bypass, weak crypto, SQL interpolation). The judgment-tier rules (SSRF, XSS, deserialization, open redirect, webhook verification, mass assignment, insecure defaults) and especially the invariant-linked authz rules (resource ownership, tenant isolation) are what make security review deliver exploitable findings on real apps — authorization and business-logic gaps are the differentiator generic linters miss. The rule infrastructure also has no concept of an invariant-linked rule: the index schema and walker have no `class` field, so the two authz rules that "fire with the derived security model" cannot be marked as such.

## Goal

After this work, `docs/security/security-review-guide.md` is the complete v1 security rule base: the 5 mechanical rules, the 7 judgment-tier rules, and the 2 invariant-linked authz rules — every block owner `go-security-specialist`, every ID in the two-component `go-security/<slug>` form, every judgment-tier block carrying a `**Trigger**:` field, and both authz blocks carrying `**Class**: security-invariant`. `rules/index.json` holds 180 entries and passes `make check-index`; `scripts/build-index.py` emits a `class` key for invariant-linked rules; `docs/rule-block-schema.md` documents the new field and key. The guide records the cross-language detector layout decision. Every rule finding resolves against the regenerated index (invariant findings against the derived session model), so no invented security policy passes the citation gate. The Definition of Done holds: one invariant-linked rule and one judgment-tier rule are each proven on a fixture.

## Non-goals

- Do NOT ship new mechanical detectors — all 9 new rules are judgment-tier (LLM-adjudicated); `rules/security/` keeps exactly its 5 flat go-first YAML detectors.
- Do NOT structurally reorganize `rules/security/` into per-language subdirectories — the split decision is recorded in the guide only.
- Do NOT touch the `go-security-specialist` agent (task 5, parallel session), the verifier agent, `scripts/validate-citations.sh`, any `commands/*.md`, or `.maintainer.yaml`.
- Do NOT add runtime/network probing or new languages beyond go-first v1.
- Do NOT create a new guide — extending the already-registered `docs/security/security-review-guide.md` avoids the README/llms.txt/code-review.md "Adding a new guide" checklist.
- Do NOT add any config knob, opt-out flag, or tunable threshold to the rules or the walker — the schema fields (`level`, `trigger`, `class`) are the only acceptance surface; a future consumer demanding variation is a separate spec.

## Acceptance Criteria

**Scenario coverage: NO new scenario file.** The two invariant/IDOR fixtures already exist as scenarios 007 and 008 and are walkable (the `--security` wiring they depend on shipped in v0.49.0); the judgment-tier rule is exercised via an inline verification-time fixture in the operator rung, mirroring the scenario setup pattern — no new `scenarios/*.md` ships from this spec. A committed `scenarios/011` is deliberately not added: the judgment-tier SSRF path is exercised by the same in-place fixture pattern the operator rung runs, the invariant-kind path is already covered by committed walkable scenarios 007/008, AC7 locks `scenarios/` untouched for this spec, and the inline fixture is re-runnable at verification time producing identical evidence — a committed scenario adds no signal a walkable inline fixture cannot reproduce.

- [ ] **AC1 — Judgment-tier blocks schema-conformant:** `grep -Ec '^### RULE go-security/(ssrf-user-controlled-url|xss-untrusted-html|deserialization-unsafe|open-redirect|webhook-verification|mass-assignment|insecure-defaults)' docs/security/security-review-guide.md` returns 7; `python3 scripts/build-index.py | jq '[.[] | select(.id | test("go-security/(ssrf-user-controlled-url|xss-untrusted-html|deserialization-unsafe|open-redirect|webhook-verification|mass-assignment|insecure-defaults)")) | {id, level, enforcement_type, owner, trigger}]'` lists exactly 7 entries — `ssrf-user-controlled-url`, `xss-untrusted-html`, `deserialization-unsafe`, `open-redirect`, `webhook-verification` with `"level": "MUST"`; `mass-assignment`, `insecure-defaults` with `"level": "SHOULD"`; all with `"enforcement_type": "judgment"`, `"owner": "go-security-specialist"`, and a non-empty `trigger` array; `grep -c '^### RULE ' docs/security/security-review-guide.md` returns 14 (5 existing + 9 new) and `grep -c '\*\*Why\*\*' docs/security/security-review-guide.md` returns ≥14, `grep -c '^#### Bad' docs/security/security-review-guide.md` returns ≥14, `grep -c '^#### Good' docs/security/security-review-guide.md` returns ≥14 (prose blocks not fakeable). Evidence: grep count + stdout JSON content.
- [ ] **AC2 — Invariant-linked authz rules marked and gated:** `grep -Ec '^### RULE go-security/(resource-ownership|tenant-isolation)' docs/security/security-review-guide.md` returns 2; `grep -c '\*\*Class\*\*: security-invariant' docs/security/security-review-guide.md` returns 2; `python3 scripts/build-index.py | jq '.[] | select(.id=="go-security/resource-ownership" or .id=="go-security/tenant-isolation") | {id, level, enforcement_type, owner, class, trigger}'` returns 2 entries each with `"class": "security-invariant"`, `"level": "MUST"`, `"enforcement_type": "judgment"`, `"owner": "go-security-specialist"`, and `"trigger": ["@commits"]`; `grep -c 'security-review-pipeline.md' docs/security/security-review-guide.md` returns ≥1 (each block's enforcement cites the derived-model procedure). Evidence: grep counts + stdout JSON.
- [ ] **AC3 — Walker and schema learn the Class field:** `grep -n '"Class"' scripts/build-index.py` returns line ≥1 (the string literal in the field-parse key tuple — gates the generic parse, not a comment or a hardcoded two-ID special-case); `python3 scripts/build-index.py | jq '[.[] | select(has("class"))] | length'` returns exactly 2 (no other entry gains a `class` key); `grep -n '\*\*Class\*\*' docs/rule-block-schema.md` returns line ≥1 and `grep -n '"class"' docs/rule-block-schema.md` returns line ≥1 (schema documents the field and the index key). Evidence: grep hits + jq length.
- [ ] **AC4 — Index regenerated, IDs uniform, nothing removed:** `make check-index` exits 0; `python3 scripts/build-index.py | jq 'length'` returns 180; `python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("security/"))] | length'` returns 0 (negative: no three-component `security/...` ID anywhere); `git diff rules/index.json | grep -cE '^-.*"id": "go-security/'` returns 0 (negative: no existing security rule ID removed). Evidence: exit code + stdout counts + diff grep.
- [ ] **AC5 — New rule citations validate (non-vacuous):** `jq -n '[{kind:"rule",rule_id:"go-security/ssrf-user-controlled-url"},{kind:"rule",rule_id:"go-security/xss-untrusted-html"},{kind:"rule",rule_id:"go-security/resource-ownership"}]' > /tmp/security-findings.json && bash scripts/validate-citations.sh /tmp/security-findings.json > /tmp/security-validated.json` exits 0; `jq '.findings | length' /tmp/security-validated.json` returns 3 and `jq '.dropped_count' /tmp/security-validated.json` returns 0 — the 3 new rule_ids demonstrably resolve against the regenerated index (an empty findings fixture cannot pass). Evidence: exit code + jq counts.
- [ ] **AC6 — Cross-language layout decision recorded, no reorganization (negative):** `grep -n 'rules/security/{go,python,node}' docs/security/security-review-guide.md` returns line ≥1 (the per-language split + runner case is documented); `ls rules/security/*.yml | wc -l` returns 5 (negative: detector count unchanged); `git status --short -- rules/security/` prints nothing (negative: no tracked change to `rules/security/`). Evidence: grep hit + counts + git status.
- [ ] **AC7 — Out-of-scope files untouched (negative):** `git status --short` lists no modification to `scripts/validate-citations.sh`, no `commands/*.md`, no `agents/security-verifier.md`, no `agents/go-security-specialist.md`, no `.maintainer.yaml`, and no `scenarios/`. Evidence: git status output empty for those paths.
- [ ] **AC8 — Precommit green, CHANGELOG entry present:** `make precommit` exits 0; `grep -c '^## Unreleased' CHANGELOG.md` returns ≥1; `awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- feat:'` returns ≥1. Evidence: exit code + grep counts.
- [ ] **AC9 — Guide reconciled, no deferred-tier claims (negative):** `grep -cE 'follow-up task|ships in a follow-up|ship.*follow-up' docs/security/security-review-guide.md` returns 0; `grep -c 'Judgment/invariant-tier RULE blocks in this guide' docs/security/security-review-guide.md` returns 0 (the anti-pattern that refused judgment/invariant blocks here is gone); `grep -c 'until then' docs/security/security-review-guide.md` returns 0 (the crypto-insecure-random note no longer defers judgment-tier adjudication). Evidence: grep counts (all negative).
- [ ] **AC10 — DoD exercised at verification time (operator-executable):** scenario 007 walk exits 0 with `grep -c '"confidence": "confirmed"' /tmp/scen007-stdout.log` ≥ 1 and `grep -c '"blocking": true' /tmp/scen007-stdout.log` ≥ 1; scenario 008 walk exits 0 with `grep -c '"confidence": "rejected"' /tmp/scen008-stdout.log` ≥ 1 and `grep -c '"blocking": true' /tmp/scen008-stdout.log` returns 0; the new SSRF fixture run (Verification operator rung) produces a report whose findings cite `go-security/ssrf-user-controlled-url`, which `validate-citations.sh` keeps (resolves in `rules/index.json`), with verifier verdict `confirmed` or `plausible`. Evidence: scenario exit codes + grep counts on scenario logs + fixture report grep.

## Verification

## Container-executable (runs inside the YOLO container at prompt time)

- `make precommit` — exits 0 (check-links, check-json, check-index, check-coverage, check-acceptance, check-rule-tests, bench-test).
- `make check-index` — exits 0 (committed `rules/index.json` byte-matches the live derivation).
- `python3 scripts/build-index.py | jq 'length'` — prints 180.
- `python3 scripts/build-index.py | jq '[.[] | select(has("class"))] | length'` — prints 2.
- `jq -n '[{kind:"rule",rule_id:"go-security/ssrf-user-controlled-url"},{kind:"rule",rule_id:"go-security/xss-untrusted-html"},{kind:"rule",rule_id:"go-security/resource-ownership"}]' > /tmp/security-findings.json && bash scripts/validate-citations.sh /tmp/security-findings.json > /tmp/security-validated.json && jq '.findings | length, .dropped_count' /tmp/security-validated.json` — prints `3` then `0` (AC5 non-vacuous).
- The jq / grep / `validate-citations.sh` checks named in AC1-AC7, AC9.
- `ast-grep test -c sgconfig.yml` — exits 0 (existing rule-test harness; this spec adds no detectors).

## Operator-executable (runs on the host after PR merge, spec verification ladder)

- `make release-check` — precommit + check-versions clean, run before tagging.
- **Invariant-linked DoD:** walk `scenarios/007-security-idor-confirmed.md` and `scenarios/008-security-idor-rejected-by-verifier.md` in fresh Claude Code sessions (both are walkable — the `--security` wiring shipped in v0.49.0). 007 ends exit 0 with `"confidence": "confirmed"` and `"blocking": true`; 008 ends exit 0 with `"confidence": "rejected"` and no `"blocking": true` (evidence grep counts per AC10).
- **Judgment-tier DoD (new fixture):** scaffold a generic Go app under `$WORK` — `go mod init example.com/url-app`, a handler `pkg/handler/fetch.go` exposing `GET /fetch?url=...` that forwards the user-supplied URL to `http.Get(userURL)` with no scheme/SSRF mitigation — then run `/coding:local-review --security` over `$WORK` (in-place, plugin pinned to the branch under test, mirroring the scenario 007/008 setup). Confirm the report emits a finding citing `go-security/ssrf-user-controlled-url`; `bash scripts/validate-citations.sh` keeps it (rule_id resolves in `rules/index.json`); the verifier verdict is `confirmed` or `plausible`. The run happens against the installed plugin at spec-verification time (after the review-mode wiring and the task-5 agent are live).
- **Release tail (out of band, not gated here):** after merge, `.maintainer.yaml` (`autoRelease: true`) cuts v0.50.0 via the maintainer-agent-releaser; confirm the released version via `claude plugin list`.

## Desired Behavior

1. **Judgment-tier rule base authored.** `docs/security/security-review-guide.md` gains 7 new `### RULE go-security/<slug> (LEVEL)` blocks — `ssrf-user-controlled-url`, `xss-untrusted-html`, `deserialization-unsafe`, `open-redirect`, `webhook-verification` (MUST), `mass-assignment`, `insecure-defaults` (SHOULD) — each conforming to `docs/rule-block-schema.md` (field order Owner → Applies when → Enforcement, then `**Trigger**: **/*.go`, `**Why**:`, `#### Bad`/`#### Good` generic examples). Each block's enforcement cites no `rules/<lang>/<slug>.yml` path, so each derives `enforcement_type: judgment`.
2. **Invariant-linked authz rules authored.** The guide gains `### RULE go-security/resource-ownership (MUST)` and `### RULE go-security/tenant-isolation (MUST)`, each carrying `**Class**: security-invariant` (after `**Trigger**:`, last field line before `**Why**:`), `**Trigger**: @commits` (always-run whole-change, matching the architecture-tier semantics the pipeline documents), and an enforcement field that describes LLM adjudication against the derived session security model: resolve the resource's `authorization_functions` from the model per `docs/security/security-review-pipeline.md`, fire when the diff accesses a resource by identifier without the owning authorization function enforced, and emit findings as `kind=invariant` with `invariant_id` resolving in the session model.
3. **Index walker learns the Class field.** `scripts/build-index.py` recognizes a `**Class**:` field line and emits a `class` key in the index entry with the field value verbatim; when the field is absent the entry carries no `class` key, so the existing 171 entries stay byte-stable and `check-index` stays deterministic.
4. **Schema reference updated.** `docs/rule-block-schema.md` documents the optional `**Class**:` field — placement (after `**Trigger**:`, or after `**Enforcement**:` when no Trigger), v1 value `security-invariant` — and the `class` index key it feeds.
5. **Index regenerated and citations validated.** `make build-index` regenerates `rules/index.json` to 180 entries: the 7 judgment rules (5 MUST, 2 SHOULD), the 2 invariant-linked rules (`class: security-invariant`), all owner `go-security-specialist`, all IDs in the two-component `go-security/<slug>` form. `make check-index` passes; `validate-citations.sh` resolves findings citing the new rule_ids against the regenerated index (unchanged gate — rule_id ∈ index).
6. **Cross-language layout decision recorded.** The guide documents spike Finding 2's decision: cross-language security rules split per language under `rules/security/{go,python,node}/` with a runner case mirroring the node/frontend one, while go-first v1 keeps single-language (Go) rules flat under `rules/security/`. The decision is recorded as prose; no directories, runner cases, or detectors are created now.
7. **Guide reconciled to the shipped state.** The "judgment and invariant tiers ship in a follow-up task" sentence (line 13), the anti-patterns item refusing judgment/invariant blocks in this guide, and the crypto-insecure-random note deferring judgment-tier adjudication "until then" are all replaced with text describing the complete v1 base as shipped. The three-tier framing (mechanical / judgment / invariant) stays and now lists all tiers as live.
8. **Ship readiness.** CHANGELOG gains a `## Unreleased` section with a `feat:` bullet describing the comprehensive rule base (the `changelog/unreleased-entry-required` and `changelog/conventional-prefix-required` gates stay green); `make precommit` exits 0 after every prompt; the `.maintainer.yaml` autoRelease tail (v0.50.0) is left to the releaser.

## Constraints

- **Rule identity:** all 9 new IDs use the two-component `go-security/<slug>` form (spike Finding 1) — never the design's three-component `security/<topic>/<slug>` form. The 9 existing security rule IDs (`go-security/*` in `docs/go-security-linting.md` and the 5 mechanical ones) are unchanged.
- **Owner:** `go-security-specialist` in every new block and index entry.
- **Schema contract (frozen):** field order Owner → Applies when → Enforcement; `**Trigger**:` immediately after `**Enforcement**:`; judgment-tier rules MUST carry a Trigger, mechanical rules omit it. The 7 judgment rules carry `**Trigger**: **/*.go`; the 2 invariant rules carry `**Trigger**: @commits`. The new `**Class**:` field sits after `**Trigger**:`; its v1 value is exactly `security-invariant`.
- **Enforcement-type derivation:** none of the 9 new enforcement fields cites a `rules/<lang>/<slug>.yml` path or `scripts/rule-checks.sh`, so every new entry derives `enforcement_type: judgment` — and `check-coverage.sh` sees no orphan YAML (no new YAML files exist).
- **Walker invariants:** `scripts/build-index.py` stays Python stdlib, keeps the `rule-block-schema.md` skip, keeps duplicate-ID detection across the walked sets, and emits byte-stable sorted output.
- **Pipeline guide untouched:** `docs/security/security-review-pipeline.md` is a procedure contract with zero RULE blocks and is not modified; the invariant rules reference it by relative link (`security-review-pipeline.md`), they do not add blocks to it.
- **Extend, don't create:** all new blocks and the layout-decision prose land in the existing `docs/security/security-review-guide.md`; no new guide is created (no README/llms.txt/code-review.md checklist).
- **No changes to:** `scripts/validate-citations.sh` (already `kind` rule/invariant/toolchain), `commands/*.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, `.maintainer.yaml`, `scenarios/`.
- **Index freshness:** any prompt that edits a RULE block also runs `make build-index` and commits the result — `make check-index` fails otherwise; `make precommit` exits 0 after every prompt.
- **Generic content only:** Bad/Good examples use User, Order, Product, Customer — never trading or project-specific domains.
- **Release tail:** `.dark-factory.yaml` sets `autoRelease: false` (dark-factory commits locally); the v0.50.0 release is cut by the maintainer-agent-releaser per `.maintainer.yaml` (`autoRelease: true`) — out of band. This spec requires only the CHANGELOG `## Unreleased` entry.
- **Approval discipline:** never edit frontmatter status manually — approval goes through `dark-factory spec approve` with explicit user confirmation.

## Failure Modes

| Trigger | Expected behavior | Recovery | Detection | Reversibility | Concurrency |
|---------|-------------------|----------|-----------|---------------|-------------|
| Guide edited without regenerating the index | `check-index` fails precommit ("rules/index.json is stale") | Run `make build-index` in the same prompt that edited the guide, commit the result | `make precommit` exits non-zero on `check-index` | Reversible — derived artifact, regenerable | Last-writer-wins if two prompts regen concurrently; mitigated by prompt ordering 1→2→3 and the check-index gate |
| `build-index.py` Class support regresses existing extraction (a non-Class entry gains a `class` key, or field parsing breaks) | `check-index` diff shows existing entries changed, or build-index exits 1 | Revert the parse change; confirm existing 171 entries derive byte-identically; re-apply | `git diff` on `/tmp/coding-rules-index-check.json`; build-index stderr | Reversible | Sequential prompts only |
| Malformed RULE block (bad heading, wrong field order, missing required field, duplicate ID) | build-index exits 1 naming the doc and rule | Fix the block to match `rule-block-schema.md`, re-run `make build-index` | build-index stderr line with `doc_path` + rule | Reversible | — |
| A judgment rule ships without `**Trigger**:` | Index entry lacks a `trigger` array; the dispatcher never scopes the rule, so it can silently never fire | Add `**Trigger**:` and regenerate | jq audit (AC1 `trigger` arrays) + index review | Reversible | — |
| `ast-grep`/`jq` missing in the container | `check-rule-tests` / `check-acceptance` fail fail-closed ("command not found") | Install `ast-grep` (the existing `check-acceptance` preflight names the install command) | `make precommit` exits non-zero | Reversible | — |
| Judgment-tier LLM rule silently stops producing findings on real PRs | No finding emitted for a real SSRF/XSS/IDOR pattern; no CI gate can see it | Operator re-runs the AC10 SSRF fixture and the 007/008 walks at spec-verification time | Operator rung fixture run | Reversible | — |
| An invariant rule fires but the finding's `invariant_id` does not resolve in the session model (enforcement misread or invented invariant) | `validate-citations.sh` drops the finding with a WARN and exits 1 (fail-closed: no model, no invariant findings) | Fix the enforcement text to describe adjudication against the derived model's invariants per the pipeline doc | `WARN: dropped … kind=invariant` on stderr | Reversible | Session-local models — no shared state to race on |

## Security / Abuse Cases

The feature touches files (guide, schema, walker, index) and adds judgment rules the LLM adjudicator applies to untrusted consumer PR code.

- **Attacker-controlled input:** consumer source code is data the LLM adjudicator reads; it is never executed and never parsed as code (the pipeline guide's security contract). The RULE-block text, `**Trigger**:` globs, and `**Class**:` value are repo-controlled constants, never derived from scanned code — no injection path into the rules, walker, or index.
- **Trust boundary:** `build-index.py` reads only repo-owned `docs/` files; the index is derived from trusted repo state. The invariant rules' adjudication consumes the session security model, whose `file:line` evidence strings are display-only references — enforcement text must keep that contract.
- **What can hang / retry forever / race:** none — no new network, no loops, no retries; the only external tool is `ast-grep` (bounded single-shot). The session model is session-local (pipeline lifecycle), so concurrent reviews do not share state.
- **Input validation:** RULE IDs validated by build-index (lowercase, ≥2 slash components, level tokens MUST/SHOULD/MAY); duplicate-ID detection spans both walked doc sets; the `class` value is emitted verbatim from the trusted field with no normalization path.
- **Provenance integrity:** every rule finding must cite a `rule_id` in the regenerated index; every invariant finding must cite an `invariant_id` in the session model. `validate-citations.sh` is unchanged and remains the gate — invented security policy is rejected.

## Suggested Decomposition

Prompts generated in this order — each row is one prompt with an auditable scope. Ordering keeps `make precommit` green after every prompt: every prompt that adds RULE blocks also regenerates the index (the check-index gate is why guide authoring and index regen are bundled, per the spec-007 lesson).

| # | Prompt focus | Covers DBs | Covers ACs | Depends on |
|---|---|---|---|---|
| 1 | Author the 7 judgment-tier RULE blocks in the guide (levels, Trigger, Bad/Good, Why) + reconcile judgment-tier prose (crypto-insecure-random note, "judgment tier ships in a follow-up" sentence) + `make build-index` regen (178 entries) + commit | 1, 5, 7 | 1, 4, 9 | — |
| 2 | Extend `scripts/build-index.py` with `Class` parsing → `class` key + document the field and key in `docs/rule-block-schema.md` + author the 2 invariant-linked RULE blocks (`**Class**: security-invariant`, `**Trigger**: @commits`, enforcement citing the pipeline) + `make build-index` regen (180 entries) + commit | 2, 3, 4, 5, 7 | 2, 3, 4, 9 | prompt 1 (shared guide file — sequential edits avoid conflicts; regen pattern established) |
| 3 | Record the cross-language layout decision in the guide + final guide reconciliation + CHANGELOG `## Unreleased` feat entry + final cross-cutting gates (`make precommit`, all negative scope-lock ACs, citation validation) | 6, 7, 8 | 5, 6, 7, 8 | prompts 1, 2 |

Rationale: prompt 1 lands the judgment-tier surface with no dependency on the Class mechanism. Prompt 2 bundles the walker's `Class` support, the schema documentation, and the two blocks that use `Class` in one prompt, so no intermediate state ever has Class-carrying blocks without walker support. Prompt 3 is documentation + CHANGELOG + final gates. AC10 is operator-executable (runs at spec-verification time, after merge) and is covered by the Verification operator rung, not by a prompt — it requires the merged plugin, the `--security` wiring (v0.49.0), and the task-5 agent.

## Do-Nothing Option

If this task does not ship, the guide's promise that the judgment and invariant tiers "ship in a follow-up task" stays unfulfilled, and security review mode keeps only 5 mechanical MUST detectors. Its findings on real apps remain limited to mechanical shapes (secrets, TLS, weak crypto, SQL interpolation); the authz/business-logic findings that differentiate security review from generic linters never fire, and the invariant-linked authz rules — the design's core differentiator — do not exist in the rule base or the index. The goal's "decent → comprehensive" progression is blocked at decent. The current approach is not acceptable: the comprehensive tier is the stated deliverable of this task, and the guide currently ships an explicit placeholder for it.

## Verification Result

**Verified:** 2026-08-23T21:18:46Z (HEAD 3c1f966)
**Binary:** n/a — structural spec, verified directly in worktree; AC10 gate references installed coding plugin v0.49.0 (see Evidence)
**Scenario:** n/a — no new scenario file (AC10 operator DoD deferred, see Evidence)
**Evidence:**
- AC1: `grep -Ec '^### RULE go-security/(…7 slugs…)'` = 7; jq 7 entries (5 MUST / 2 SHOULD, enforcement_type judgment, owner go-security-specialist, trigger non-empty); total `^### RULE ` = 14; Why/Bad/Good each = 14
- AC2: 2 invariant RULE headings; `**Class**: security-invariant` = 2; jq 2 entries class=security-invariant, MUST, judgment, trigger ["@commits"]; `security-review-pipeline.md` cited 4×
- AC3: `build-index.py:64` — `"Class"` in field key tuple; jq `has("class")` length = 2; schema doc `**Class**:` hits (51,54,58,63) and `"class"` hits (51,119,136)
- AC4: `make check-index` exit 0; index length 180; `security/` 3-component count 0; go-security ID count 18; removed-go-security-ID diff count 0; rules/index.json clean in git
- AC5: citation fixture `validate-citations.sh` exit 0, `.findings | length` = 3, `.dropped_count` = 0 (non-vacuous)
- AC6: layout decision at guide:461 (`rules/security/{go,python,node}`); `rules/security/*.yml` count 5; `git status --short -- rules/security/` empty
- AC7: `git status --short` empty; `git diff origin/master...HEAD --stat` touches no `scripts/validate-citations.sh`, `commands/`, `agents/*`, `.maintainer.yaml`, `scenarios/`
- AC8: `make precommit` exit 0; CHANGELOG `## Unreleased` present + 1 `feat:` bullet
- AC9: negative greps all 0 — `follow-up task|ships in a follow-up|ship.*follow-up` = 0; `Judgment/invariant-tier RULE blocks in this guide` = 0; `until then` = 0
- AC10 (DEFERRED — verified-with-deferred-runtime-evidence): installed coding plugin at spec-verification time is v0.49.0 — `--security` wiring live (local-review.md, 6 hits) and go-security-specialist/security-verifier agents live, but the rule base is NOT installed (installed guide = 5 RULE blocks, installed index has 0 `go-security/ssrf-user-controlled-url` entries). The SSRF DoD fixture therefore cannot produce a finding that the installed validator keeps; scenario 007/008 walks not run (no /tmp/scen007-*/scen008-* evidence). AC10 to be satisfied post-release v0.50.0.
**Verdict:** PASS (AC1-AC9 verified against fresh in-repo evidence; AC10 verified-with-deferred-runtime-evidence, pending v0.50.0 release)
