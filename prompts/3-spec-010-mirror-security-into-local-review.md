---
status: draft
spec: [010-security-review-command-wiring]
created: "2026-08-23T17:17:00Z"
branch: dark-factory/security-review-command-wiring
---

# Mirror --security into commands/local-review.md (local mode)

<summary>
- The local uncommitted/recent-changes review command accepts a `--security` flag that activates the same dormant security mode as the PR review command, with PR-mode diff anchoring over `HEAD~1`
- The recon, six trait groups with deterministic invariant selection, verifier gate, derived blocking, fail-closed deps pass, citation validation, and `Security Findings` + `Security Model` report sections mirror the canonical wiring from the PR review command
- The command stays a thin wrapper — it replicates the proven security-mode section from `commands/pr-review.md` and references the frozen guides and agents by name
- The frozen security contract files are proven byte-unchanged, and existing selector / short / full behavior is untouched when the flag is absent
- The acceptance-suite invariants on the command (short-mode skip, runner reference, selector routing and short-circuit string, step labels, context-doc mappings) all stay green
</summary>

<objective>
Mirror the `--security` wiring from `commands/pr-review.md` (prompt 1's deliverable) into `commands/local-review.md` so the local uncommitted/recent-changes review can run the full security pipeline — recon-derived session model over the local diff, six trait groups with deterministic invariant selection, verifier-gated findings, derived blocking, a fail-closed deps pass, and the `Security Findings` + `Security Model` report sections — with PR-mode diff anchoring over the `HEAD~1` diff.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "Command = Thin Wrapper" and "Plugin Namespacing" rules and the generic-content rule.

Read `commands/local-review.md` (full) — the file to edit. Note the structure you must preserve: frontmatter `argument-hint: "[short|full|selector] [directory]"`, Step 1 argument parsing, Step 2 project detection, Step 3 automated checks, Step 4 dispatcher (4.0 toolchain preflight → 4a mechanical funnel → 4b-i candidate computation → selector-mode 4c-sel/4d-sel block → full-mode dispatch → 4c context conventions → 4d citation validation), Step 5 consolidated report, Step 6 next steps, Step 7 manual review. The DIFF for this command is `git diff HEAD~1` (or the directory diff parsed in Step 1).

Read `commands/pr-review.md` (the `#### Security mode (under \`--security\` only)` subsection inserted by prompt 1) — the canonical security-mode section you must replicate. It is the single source for the recon/classifier/adjudicator/verifier/blocking/deps-pass/citation-validation contract wording.

Read `docs/selector-mode-guide.md` (the dormant `## Security Extension (dormant)` section) — FROZEN; the command references it, never edits it.

Read `docs/security/security-review-pipeline.md` (full) — the recon procedure, model schema, freshness gate, diff-relevant truncation, attack-surface inventory drift bridge, report contract. FROZEN — reference, never re-document.

Read `agents/security-verifier.md` (full) — the 7-item falsification checklist and verdict contract. FROZEN.

Read `scripts/validate-citations.sh` (full) — the polymorphic validator (`SECURITY_MODEL_FILE`, `kind` resolution, fail-closed absent-model drop path). FROZEN.

Read `scripts/acceptance.sh` (the checks on `commands/local-review.md`) — the check-acceptance assertions that must stay green after your edit: the short-mode "No agents / skip Step 4" directive, the `scripts/ast-grep-runner.sh` reference, at least 4 of the legacy-path conditional agents (`license-assistant`, `readme-quality-assistant`, `shellcheck-assistant`, `context7-library-checker`, `go-version-manager`, `go-tooling-assistant`), the `Selector mode (the default)` routing, the `--selector`/`selector.*mode` token, the `selector clean — no adjudication needed` short-circuit string, `GUIDE_OK`/`GUIDE_MISSING`, the `selector-mode-guide.md` filename, the `4c-sel`/`4d-sel` labels, the Step 2.5 context-doc mappings (`teamvault-conventions.md`, `go-k8s-binary-conventions.md`, `k8s-manifest-guide.md`, `changelog-guide.md`), and the `coding:<owner>`/`findings_by_owner` dispatch block. Preserve all of them.
</context>

<requirements>
1. **Hard dependency guard.** Verify prompt 1 shipped the canonical wiring before editing anything: `grep -n '#### Security mode (under \`--security\` only)' commands/pr-review.md` must return a line. If it does not, STOP and report that prompt 1 must execute first — do NOT invent an alternative security-mode shape (the report-section wording and the diff-anchoring rule must be consistent across all three commands).

2. **Record the frozen-contract baseline FIRST.** Before making any edit, run:
   `sha256sum docs/selector-mode-guide.md scripts/validate-citations.sh agents/security-verifier.md agents/go-security-specialist.md docs/security/security-review-pipeline.md docs/security/security-review-guide.md > /tmp/df010-frozen.sha256`
   Keep it for the AC6 check in `<verification>`. If any of the six files is missing, STOP and report the missing path.

3. **Flag parsing (AC2).**
   a. In the frontmatter, change the `argument-hint` line to: `argument-hint: "[short|full|selector] [directory] [--security]"`.
   b. In Step 1 (Parse Arguments), add: `--security` is a position-independent boolean flag that may appear anywhere in the argument list (before or after the mode token and the directory); when present, set `SECURITY_REVIEW=1`, independent of the mode token. It is recognized as a flag and is NOT treated as the directory path by the "Any remaining arguments are treated as the directory path" rule. The flag is never silently ignored — the security pipeline runs in-session over the reviewed scope regardless of mode token; the existing short-mode "skip Step 4" directive applies only to the non-security funnel.

4. **Insert a new subsection — `#### Security mode (under \`--security\` only)`** — positioned immediately AFTER the "Selector mode (the default): Steps 4c-sel and 4d-sel" block (which ends with the sentence "Include the traceability section per `docs/selector-mode-guide.md` § Traceability Report Section.") and immediately BEFORE the "#### Full mode: per-owner dispatch" heading. Replicate the canonical security-mode section from `commands/pr-review.md` (same wording and step structure for recon/model derivation, classifier trait groups, adjudicator inputs, verifier gate, blocking, deps pass, and citation validation), with these local-mode specifics:

   - **Diff source** — the recon and the adjudicator consume the local diff `git diff HEAD~1` (or the directory diff parsed in Step 1); the session model mirrors `/tmp/local-review-findings.json`.
   - **Diff anchoring** — in local mode (PR mode), report security findings ONLY on diff-changed lines or invariants whose attack surface the diff touched; whole-file context is permitted for reasoning, never for gating (AC5: the string `changed lines` must appear at least once — the phrase "diff-changed lines" satisfies it).
   - **Freshness gate** — unchanged-evidence entries carried forward, changed-evidence entries re-derived, stale entries dropped and surfaced with the literal `model refresh:` line; large-repo truncation noted in the report.
   - **Model path** — `/tmp/security-model.json`, session-local, never inside the reviewed directory.
   - **Deps pass** — run over the local repo's dependency manifests; fail-closed (scan failure, DB-fetch timeout, or flagged vulnerability → Must-Fix toolchain finding, never a silent skip).
   - **Citation validation** — the Step 4d-sel citation-validation invocation passes `SECURITY_MODEL_FILE=/tmp/security-model.json`; invariant findings fail closed on an absent model, and the review continues with rule/toolchain findings (never a hard abort).

   Each of the literal strings `security-model.json`, `/tmp/security-model.json`, `SECURITY_MODEL_FILE`, `security-verifier`, and `model refresh` must appear at least once in this subsection (AC3/AC4 evidence).

5. **Report sections (AC4/AC5).** In Step 5 (Consolidated Report), add under the signal: a `Security Findings` section listing every security finding (rule, invariant, and toolchain) with `file:line`, provenance (`kind` + `rule_id`/`invariant_id`), verifier verdict fields, and derived blocking state; and a `Security Model` provenance block recording `derived_from` (repo, head, review_id), the entry-point count, each attack-surface inventory count, and any `model refresh:` lines verbatim. A scope containing Go source always produces the Security Model block (never a silent skip); a scope with no Go source — including when the Step 4 early-exit fires on a non-rule-relevant diff — states `no Go source — security model not derived` explicitly instead of omitting the section. The normal severity buckets and the selector traceability section still appear. The literal strings `Security Findings`, `Security Model`, and `model refresh` must each appear at least once in the command (AC4 evidence).

6. **Preserve existing behavior (no regression).** The existing Steps 1–7, 4.0, 4a, 4b-i, the selector-mode block, the full-mode dispatch block, 4c, 4d, and the existing Step 5 sections are preserved unchanged except the targeted additions in requirements 3–5. All of the `scripts/acceptance.sh` assertions on this file must still pass after your edit (listed in `<context>`). Do NOT touch `commands/pr-review.md`, `commands/code-review.md`, any `docs/*`, `scripts/*`, `agents/*`, `rules/*`, `README.md`, `llms.txt`, `scenarios/*`, or `CHANGELOG.md` (sibling prompts own them).

7. **Dormant contract and shipped artifacts untouched (AC6).** Do not edit `docs/selector-mode-guide.md`, `scripts/validate-citations.sh`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, `docs/security/security-review-pipeline.md`, or `docs/security/security-review-guide.md` — the command only references them. No `### RULE` heading anywhere in your edit. Generic examples only (User, Order, Product, Customer); never trading/project-specific content; no personal paths.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands; the git-based negative guard (AC6 `git diff origin/master` / `git status --porcelain`) runs on the operator side of the spec's Verification ladder — the container form is the checksum baseline in requirement 2.
- The `## Security Extension (dormant)` in `docs/selector-mode-guide.md` is the frozen classify/adjudicate contract: steps 4c-sel/4d-sel and the extension text MUST NOT be renumbered, rewritten, or edited; the `--security` wiring only sets the security-review signal that activates it, and when the signal is absent the existing procedure runs byte-for-byte.
- Shipped artifacts not re-authored: `docs/security/security-review-pipeline.md`, `docs/security/security-review-guide.md`, `agents/security-verifier.md`, `agents/go-security-specialist.md`, and `scripts/validate-citations.sh` already exist and are NOT modified. No new security detection rules.
- Blocking: derived per `blocking = confidence==confirmed ∧ exploitability==high ∧ impact≥medium`, never stored as severity; per-surface configurable thresholds are out of scope — no config fields, no opt-out flags.
- Finding provenance: exactly one of `rule_id ∈ rules/index.json`, `invariant_id ∈ derived model`, or `kind=toolchain` (no id). No new validation-script work.
- Model location: `security-model.json` is session-local under `/tmp`, never committed to any repo; if it is ever written inside the reviewed repo tree it is deleted and rewritten to the session-local path.
- Commands are thin wrappers: no inline rules; all agent references use the `coding:` prefix; the classify/adjudicate/verifier procedure is executed per the guides, not re-implemented in the command.
- HARD INVARIANT preserved: the applicable set is a subset of the Step 4b-i candidate set; trait groups never add a rule the glob did not produce.
- Selector-mode zero-sub-agent-spawn property preserved for the classify/adjudicate steps; the verifier execution mechanism is the only deviation point and is reversible (the session decides at review time).
- The `--security` mode must not bypass or soften the existing Step 4.0 toolchain preflight (ast-grep/sg fail-fast) or the Step 4a mechanical funnel.
- Local scope is the uncommitted / `HEAD~1` diff — unchanged from the existing command constraints.
- Generic content only: fixtures and examples use User, Order, Product, Customer — never trading/project-specific content, never personal paths.
- Existing tests must still pass: `make precommit` (incl. `check-acceptance`) exits 0.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- AC1: repo integrity ---
make precommit    # must exit 0

# --- AC2: --security flag wired ---
grep -n -- '--security' commands/local-review.md              # >= 1
grep -n 'argument-hint:.*--security' commands/local-review.md # >= 1

# --- AC3: security pipeline steps wired ---
grep -n 'security-model.json' commands/local-review.md        # >= 1
grep -n '/tmp/security-model.json' commands/local-review.md   # >= 1
grep -n 'SECURITY_MODEL_FILE' commands/local-review.md        # >= 1
grep -n 'security-verifier' commands/local-review.md          # >= 1

# --- AC4: report sections encoded ---
grep -n 'Security Findings' commands/local-review.md          # >= 1
grep -n 'Security Model' commands/local-review.md             # >= 1
grep -n 'model refresh' commands/local-review.md              # >= 1

# --- AC5: PR-mode diff anchoring ---
grep -n 'changed lines' commands/local-review.md              # >= 1

# --- AC6: frozen contract byte-unchanged (container form; the repo diff/status guard runs operator-side) ---
sha256sum -c /tmp/df010-frozen.sha256                         # all files: OK

# --- acceptance-suite invariants preserved (check-acceptance must stay green) ---
grep -n 'Selector mode (the default)' commands/local-review.md   # >= 1
grep -n 'selector clean — no adjudication needed' commands/local-review.md   # >= 1
grep -n '4c-sel' commands/local-review.md                        # >= 1
grep -n '4d-sel' commands/local-review.md                        # >= 1
grep -n 'scripts/ast-grep-runner.sh' commands/local-review.md    # >= 1
grep -n 'teamvault-conventions.md' commands/local-review.md      # >= 1
```
</verification>

<!-- OPEN QUESTION for the human reviewer: (1) RESOLVED in req 3b — the `--security` × explicit `short`/`full` mode-token interaction is bound: the security pipeline runs in-session over the reviewed scope regardless of mode token, while short mode's normal "skip Step 4 entirely" still applies to the non-security funnel. (2) RESOLVED in req 3b — `--security` is recognized as a flag and is NOT consumed by the "Any remaining arguments are treated as the directory path" fallback. (3) The frozen `docs/selector-mode-guide.md` sentence "No command sets that signal yet" becomes historically stale after wiring — accepted residual staleness per the frozen-contract constraint. -->
