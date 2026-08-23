---
status: completed
spec: [009-security-verifier-citations]
summary: Extended scripts/validate-citations.sh to resolve each finding's provenance by kind (rule/invariant/toolchain) with fail-closed invariant model handling, added a 10-file fixture set under scripts/testdata/validate-citations/, and kept the legacy rule_id path and frozen exit semantics byte-compatible
execution_id: coding-security-verifier-exec-038-spec-009-validator-polymorphic-contract
dark-factory-version: dev
created: "2026-08-23T10:01:50Z"
queued: "2026-08-23T10:13:18Z"
started: "2026-08-23T10:13:20Z"
completed: "2026-08-23T10:15:51Z"
branch: dark-factory/security-verifier-citations
---

# Extend the citation validator to the polymorphic provenance contract

<summary>
- The citation validator learns to validate every finding by its provenance kind instead of assuming a `rule_id` on every finding
- Rule-kind findings are still checked against the rule index exactly as they are today — no behavior change on the existing path
- Invariant-kind findings are now checked against a security model read from a new environment variable, mirroring how the index file is read
- Toolchain-kind findings are kept without any id — they are tool output (gosec/trivy/osv-scanner/vulncheck), not rule violations
- Findings that carry no `kind` field keep working as rule findings, so the existing acceptance suite and the selector guide's legacy findings stay green
- An unknown kind, or a kind whose provenance does not resolve, drops the finding with a WARN line that names the offending id
- When the model is absent, unreadable, or unparseable, every invariant finding is dropped rather than silently kept (fail-closed)
- Exit codes keep their frozen meaning — 0 all resolved, 1 any drop, 2 missing rule index — and a missing model is a drop path (exit 1), never the reserved exit 2
- A fixture set lands under the scripts testdata directory covering the full matrix, each runnable standalone from the repo root
- No rule, no detector, no index entry, no command, no doc, and no README or changelog file changes
</summary>

<objective>
Extend `scripts/validate-citations.sh` so every finding that flows through the review funnel resolves exactly one provenance — `rule` (rule_id in the index), `invariant` (invariant_id in the derived model), or `toolchain` (no id) — fail-closed on a missing model, while keeping the legacy no-kind path and the frozen exit semantics byte-compatible.
</objective>

<context>
Read `CLAUDE.md` (repo root) — project conventions (generic examples only, no personal paths).

Read `scripts/validate-citations.sh` (full) — the script this prompt modifies. Note its current shape: a bash wrapper (`set -euo pipefail`) with `INDEX_FILE="${INDEX_FILE:-rules/index.json}"`, exit 2 when the index is missing, stdin-or-arg input handling, and a single heredoc-fed Python block that walks findings (flat list or owner-grouped), resolves `rule_id` against the index's `id` set, emits `{"findings": [...], "dropped_count": N}` on stdout, logs dropped findings to stderr, and exits 0/1. The `walk()` helper currently yields only dicts that contain `"rule_id"` — that predicate is what this prompt extends.

Read `scripts/acceptance.sh` (the `=== 4/5 Broken-YAML isolation ===` section 4(d)) — it builds a temp findings file `[{"rule_id": "fake/this-rule-does-not-exist", "file": "x.go", "line": 1}]` (no `kind` field) and asserts the validator exits non-zero. That assertion must keep passing unchanged — the legacy no-kind path is the mechanism.

Read `docs/security/security-review-pipeline.md` (the `Model schema and lifecycle` section) — the frozen source of truth for the model: invariant ids live at `invariants[].id` (the schema block shows `{"id": "INV-1", "statement": ..., "evidence": ..., "attack_surfaces": [...]}` inside `invariants[]`).

Read `rules/index.json` (via `jq -r '.[].id'`) — confirm `go-security/hardcoded-secret` is a real index id; the rule-valid and legacy-rule fixtures cite it.

Read `Makefile` — `precommit` runs `check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test`; `check-acceptance` runs `scripts/acceptance.sh` including section 4(d). Nothing in `precommit` scans `scripts/testdata/`, so the fixture JSON files are verification material, not build input.
</context>

<requirements>
1. Modify `scripts/validate-citations.sh` in place. Preserve the overall structure — bash wrapper with `set -euo pipefail`, the stdin-or-arg input handling (arg if `-f` exists, else buffer stdin via `mktemp`), the heredoc-fed Python block, and the stdout/stderr split. Do not add any new file for the validator logic.

2. Add a new environment variable read at the top of the bash wrapper, mirroring the existing `INDEX_FILE` line:
   ```bash
   SECURITY_MODEL_FILE="${SECURITY_MODEL_FILE:-}"
   ```
   Default is empty (unset). Pass it into the Python block alongside `INDEX_FILE` and the findings path (extend the `python3 -` argument list and `sys.argv` reads accordingly). A missing model must NEVER trigger the exit-2 branch — that branch stays reserved for a missing `rules/index.json` only.

3. Extend the Python `walk()` helper's finding predicate. Today it yields a dict only when `"rule_id" in item`; change it to yield a dict when it carries any provenance-relevant field: `"kind" in item or "rule_id" in item or "invariant_id" in item`. Keep the same recursion into lists and dicts and the same `(parent_key, index, finding_dict)` yield shape. This is the single mechanical change that makes the polymorphic contract reachable — a `kind: invariant` finding (no `rule_id`) and a `kind: toolchain` finding (no id at all) must both be considered, not skipped.

4. Implement exactly-one-provenance resolution per finding, applied in this order:
   - Let `kind = finding.get("kind")`. If `kind` is `None`, treat the finding as `kind: "rule"` (legacy path — a finding with only `rule_id` and no `kind` validates exactly as today).
   - `kind == "rule"`: resolve `rule_id` in the existing `valid_ids` set built from `rules/index.json`. A missing `rule_id`, or one absent from the set, drops the finding (existing behavior, unchanged).
   - `kind == "invariant"`: resolve `invariant_id` in the model's invariant-id set. If the model is unavailable (see requirement 5) OR `invariant_id` is missing OR absent from the set, drop the finding with WARN (fail-closed). An invariant finding is never kept without a resolvable model.
   - `kind == "toolchain"`: keep the finding without any id validation — tool-output contract. Do not require `rule_id`, `invariant_id`, or any provenance field.
   - any other `kind` value: drop the finding as unprovenanced (this is the `unknown-kind` case).
   - A finding that carries BOTH `rule_id` and `invariant_id` is validated only against the field named by its `kind`; the other field is ignored (exactly-one-provenance contract).

5. Load the model once, before the walk loop. Compute `model_invariant_ids` as the set of `inv["id"]` for every dict `inv` in `model.get("invariants", [])`. Mark the model **unavailable** when `SECURITY_MODEL_FILE` is unset, or set but the file does not exist / cannot be read, or `json.load` raises (`OSError` or `json.JSONDecodeError`). When the model is unavailable, every `kind: invariant` finding drops with WARN — never kept, never a hard script failure (it is the exit-1 drop path). The script reads the model file only; it never writes, never executes, never shells out.

6. Keep the stdout output contract byte-compatible: `json.dump({"findings": valid_findings, "dropped_count": len(dropped)}, ...)` with the owner-tagged `{"owner": owner, **finding}` entries, and the validated subset still emitted even when drops push the exit code to 1.

7. Keep the stderr WARN contract, extended to the polymorphic cases. The exact wording is flexible ("agent decides at impl time"), but the shape must mirror the current one: a `WARN: dropped N finding(s) ...` header line and one per-finding line naming the kind and the offending provenance id — e.g. `kind=rule rule_id='security/fake/does-not-exist'`, `kind=invariant invariant_id='INV-9'` (including the fail-closed absent-model case, which still names the dropped `invariant_id`), and `kind='mystery'` for an unrecognized kind. The literal substring `WARN: dropped` must appear on stderr whenever any finding is dropped, and each dropped finding's offending provenance id must be named.

8. Freeze exit semantics, unchanged: 0 = every finding resolved; 1 = any finding dropped (validated subset still on stdout, offenders on stderr); 2 = `rules/index.json` missing (the existing `[[ ! -f "$INDEX_FILE" ]]` branch, byte-unchanged). A missing or unparseable model is the fail-closed drop path (exit 1), never exit 2.

9. Create the fixture set under `scripts/testdata/validate-citations/` (new directory). Each file is a standalone JSON findings file (or model file) runnable from the repo root with `bash scripts/validate-citations.sh <fixture>`. Use generic examples only (User, Order, Product, Customer) — no trading terms:
   - `rule-valid.json` — one finding, `kind: rule`, `rule_id` that resolves in `rules/index.json` (e.g. `go-security/hardcoded-secret`), plus `file`/`line` fields.
   - `rule-invalid.json` — one finding, `kind: rule`, `rule_id: security/fake/does-not-exist`.
   - `unknown-kind.json` — one finding, `kind: mystery`, with a severity field but no rule_id / invariant_id.
   - `invariant-valid.json` — one finding, `kind: invariant`, `invariant_id: INV-1`, plus `file`/`line` fields.
   - `security-model.json` — the companion model whose `invariants[].id` includes `INV-1` (shape per the pipeline guide's schema block: `{"version": 1, "invariants": [{"id": "INV-1", "statement": "...", "evidence": "...", "attack_surfaces": [...]}]}`). Give the statement a generic shape, e.g. "a member may only read orders they own".
   - `toolchain.json` — one finding, `kind: toolchain`, no `rule_id` and no `invariant_id`, carrying tool-output fields (e.g. `tool: osv-scanner`, `package`, `version`, `advisory` / OSV id, plus `file`/`line`).
   - `legacy-rule.json` — one finding with ONLY `rule_id` and no `kind` (the acceptance.sh shape), `rule_id` resolving in `rules/index.json` (e.g. `go-security/hardcoded-secret`).
   - `security-model-bad.json` — the companion model with unparseable JSON (e.g. `{"invariants": [}`) — exercises the `json.JSONDecodeError` fail-closed branch (spec failure-mode row 1: missing/unreadable/unparseable).
   - `invariant-invalid.json` — one finding, `kind: invariant`, `invariant_id: INV-99` (absent from the valid `security-model.json` `invariants[].id`) — exercises provenance rejection against a PRESENT model (spec failure-mode row 2).
   - `both-ids.json` — two findings, each carrying BOTH `rule_id` and `invariant_id`: (1) `kind: rule` with a resolving `rule_id` (e.g. `go-security/hardcoded-secret`) and a fake `invariant_id` (e.g. `INV-99`) → kept, validated against `rule_id` only; (2) `kind: invariant` with `invariant_id: INV-1` (in the valid model) and a fake `rule_id` → kept, validated against `invariant_id` only. Locks the exactly-one-provenance contract (spec failure-mode row 6).

10. Do NOT touch: any other file under `scripts/`, `rules/` (including `rules/index.json` and `rules/security/*.yml`), any `docs/*.md`, any `agents/*.md` (and do NOT create `agents/security-verifier.md` — prompt 2 owns it), any `commands/*.md`, `README.md`, `llms.txt`, `CHANGELOG.md` (prompt 4 owns the changelog entry), `scenarios/`, `CLAUDE.md`.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; git-based evidence (AC13 `git status --short` scope-lock) runs on the operator side of the spec's Verification ladder.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt (including `check-acceptance`, which runs `scripts/acceptance.sh` section 4(d) against this validator).
- Provenance resolution (frozen): exactly one provenance per finding, chosen by `kind`. `rule` → `rule_id` ∈ `rules/index.json`; `invariant` → `invariant_id` ∈ `invariants[].id` of the model at `SECURITY_MODEL_FILE`; `toolchain` → kept, no id. Absent `kind` defaults to `rule` (legacy path). Unrecognized `kind` or unresolvable provenance → dropped.
- Fail-closed (frozen): an invariant finding is never kept without a resolvable model. `SECURITY_MODEL_FILE` unset, missing, or unparseable → invariant findings drop with WARN.
- Exit semantics (frozen): 0 = all resolved; 1 = any drop (validated subset still emitted, offenders logged to stderr); 2 = `rules/index.json` missing. A missing model is the drop path (exit 1), never exit 2.
- Existing `rule_id` path unchanged (frozen): findings with a `rule_id` (with or without `kind`) validate exactly as today; `scripts/acceptance.sh` section 4(d) and the selector-guide's validator-invocation block pass unchanged.
- Rule base frozen: no new `### RULE` blocks, no new `rules/security/*.yml`, `rules/index.json` byte-unchanged, no `scripts/build-index.py` change. `docs/security/security-review-guide.md` stays at exactly 5 RULE blocks; `rules/security/*.yml` stays at exactly 5 files.
- Model schema frozen: the validator resolves `invariant_id` against `invariants[].id` exactly as documented in `docs/security/security-review-pipeline.md`.
- The validator is a bounded single-pass script over already-present files: no retry loop, no network, no writes, no execution of parsed JSON (the findings and model files are untrusted input — parse and id-match only).
- No config knobs, opt-out flags, or tunable thresholds beyond the `SECURITY_MODEL_FILE` env var the spec requires.
- Generic examples only (User, Order, Product, Customer) — never trading terms; no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin. No version-existence claims.
- CHANGELOG.md is NOT touched by this prompt (prompt 4 owns the `## Unreleased` bullet).
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — git evidence is operator-side). The fixture matrix matches the spec's Container-executable rung; each run echoes its exit code.
```bash
# --- Fixture matrix (AC1-AC6) ---
bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-valid.json; echo "rule-valid exit=$?"          # exit 0, dropped_count 0
bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-invalid.json; echo "rule-invalid exit=$?"     # exit 1, stderr WARN naming security/fake/does-not-exist
bash scripts/validate-citations.sh scripts/testdata/validate-citations/unknown-kind.json; echo "unknown-kind exit=$?"     # exit 1, stderr WARN
SECURITY_MODEL_FILE=scripts/testdata/validate-citations/security-model.json bash scripts/validate-citations.sh scripts/testdata/validate-citations/invariant-valid.json; echo "invariant-valid+model exit=$?"   # exit 0, dropped_count 0
bash scripts/validate-citations.sh scripts/testdata/validate-citations/invariant-valid.json; echo "invariant-valid no model exit=$?"     # exit 1, stderr WARN naming INV-1
SECURITY_MODEL_FILE=/nonexistent bash scripts/validate-citations.sh scripts/testdata/validate-citations/invariant-valid.json; echo "invariant-valid missing model exit=$?"   # exit 1 (fail-closed; NOT exit 2)
bash scripts/validate-citations.sh scripts/testdata/validate-citations/toolchain.json; echo "toolchain exit=$?"          # exit 0, dropped_count 0
bash scripts/validate-citations.sh scripts/testdata/validate-citations/legacy-rule.json; echo "legacy-rule exit=$?"       # exit 0 (no kind; rule_id resolves)
SECURITY_MODEL_FILE=scripts/testdata/validate-citations/security-model-bad.json bash scripts/validate-citations.sh scripts/testdata/validate-citations/invariant-valid.json; echo "invariant-valid bad model exit=$?"   # exit 1 (fail-closed, unparseable model), stderr WARN naming INV-1
SECURITY_MODEL_FILE=scripts/testdata/validate-citations/security-model.json bash scripts/validate-citations.sh scripts/testdata/validate-citations/invariant-invalid.json; echo "invariant-invalid exit=$?"   # exit 1, stderr WARN naming INV-99
SECURITY_MODEL_FILE=scripts/testdata/validate-citations/security-model.json bash scripts/validate-citations.sh scripts/testdata/validate-citations/both-ids.json; echo "both-ids exit=$?"   # exit 0, dropped_count 0 (each finding validated only against its kind's field)

# --- stdout contract: findings array + dropped_count ---
jq -r '.dropped_count' <(bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-valid.json)          # 0
jq -r '.findings | length' <(bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-valid.json)      # >= 1
jq -r '.dropped_count' <(bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-invalid.json)       # >= 1

# --- stderr WARN shape: offender id named on every drop ---
bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-invalid.json 2>&1 >/dev/null | grep -c 'WARN: dropped'               # >= 1
bash scripts/validate-citations.sh scripts/testdata/validate-citations/rule-invalid.json 2>&1 >/dev/null | grep -c 'security/fake/does-not-exist'  # >= 1
bash scripts/validate-citations.sh scripts/testdata/validate-citations/invariant-valid.json 2>&1 >/dev/null | grep -c 'INV-1'                     # >= 1 (fail-closed names the invariant)

# --- Legacy path unchanged: acceptance.sh section 4(d) still green ---
bash scripts/acceptance.sh >/dev/null 2>&1; echo "acceptance exit=$?"   # exit 0

# --- Scope-lock negatives: nothing outside the allowed set changed (container form) ---
grep -c '^### RULE go-security/' docs/security/security-review-guide.md    # must return 5
ls rules/security/*.yml | wc -l                                            # must return 5
python3 scripts/build-index.py | jq length                                 # must return 171

# --- Full precommit ---
make precommit                                                             # must exit 0
```
</verification>
