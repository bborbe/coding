---
status: completed
spec: [008-security-review-pipeline]
summary: 'Created docs/security/security-review-pipeline.md (procedure-contract guide: recon pass, evidence-pointered security-model schema + session-local lifecycle, freshness gate, diff-relevant truncation, attack-surface inventory drift bridge, report contract, anti-patterns; zero RULE headings), registered it in README.md and llms.txt, and added the ## Unreleased CHANGELOG entry; make precommit exits 0 with the rule index unchanged at 171 entries.'
execution_id: coding-security-review-pipeline-exec-035-spec-008-pipeline-guide
dark-factory-version: dev
created: "2026-08-23T10:30:00Z"
queued: "2026-08-23T08:26:14Z"
started: "2026-08-23T08:26:16Z"
completed: "2026-08-23T08:28:09Z"
branch: dark-factory/security-review-pipeline
---

# Add the security review pipeline guide and register it

<summary>
- Ships a new in-plugin procedure guide that tells a review session how to derive a per-review security model before adjudication: entry points, identities, auth mechanisms, resources with their authorization functions, trust boundaries, and cross-cutting invariants, each backed by a `file:line` evidence pointer
- Specifies the model's JSON schema and its lifecycle: derived in-session at review start, written to a session-local path outside the reviewed repo's tree, and never committed to any repo
- Documents the freshness gate that re-derives only entries whose evidence changed in the diff, carries unchanged entries forward, and surfaces stale entries via a literal `model refresh:` line
- Bounds model cost with diff-relevant truncation — only the touched entry points and invariants plus cheap inventory counts reach the classifier and adjudicator
- Defines a countable attack-surface inventory and a deterministic bridge from inventory drift to the matching security trait group
- Documents the Security Model report contract (derivation metadata, entry-point count, inventory counts, refresh lines)
- Registers the new guide in the plugin's README table and llms.txt so it is discoverable and link-checked
- Adds a `## Unreleased` CHANGELOG entry describing the pipeline
- Keeps the rule base untouched — the guide is a procedure contract with zero rule headings, so the rule index stays at 171 entries
</summary>

<objective>
Author the security review pipeline guide that defines how a review session derives, keeps fresh, and bounds a per-review evidence-pointered security model, and register it in the plugin's documentation index. The result is a single frozen derivation contract that the security classifier extension, the task-3 verifier, and the operator's end-to-end walk all reference as the source of truth.
</objective>

<context>
Read `CLAUDE.md` (repo root) — the "When Changing Files / Adding a new guide" checklist and the "Writing Docs" section (start with name + overview, GOOD and BAD examples, generic User/Order/Product/Customer examples only, reference related guides with relative links, end with an antipatterns section).

Read `docs/security/security-review-guide.md` (full) — the sibling guide in the same directory. The new guide must match its style: `# <Name>` title, an intro paragraph naming its companion guides as relative links, sectioned body, and a closing "Anti-patterns to refuse" section. Unlike that guide, this one is a **procedure contract** — it contains zero `### RULE` headings.

Read `docs/selector-mode-guide.md` (skim) — the classify/adjudicate procedure the pipeline feeds. This prompt only references its existence; prompt 2 of this spec extends it.

Read `docs/changelog-guide.md` — the `## Unreleased` bullet format (conventional prefix required: `- <prefix>: <what> [context]`; `feat:` for a new capability). Also available in-container at `/home/node/.claude/plugins/marketplaces/coding/docs/changelog-guide.md`.

Read `docs/dod.md` (repo root) — the Definition-of-Done gate: new doc → README.md tables + llms.txt updated; no Doc↔Agent row unless the doc is an enforceable rule guide; `## Unreleased` entry; four version strings NOT touched.

Read `README.md` — the "### Go — Infrastructure" table. The row `| [Security Review Guide](docs/security/security-review-guide.md) | Mechanical security rule base |` sits at ~line 148; the new row goes immediately after it in the same table.

Read `llms.txt` — the bullet `- [Security Review Guide](docs/security/security-review-guide.md): Mechanical security rule base (5 detectors) for Security Review Mode` sits at ~line 28 as the last bullet of the "## Go — Testing & Quality" section. The new bullet goes immediately after it.

Read `CHANGELOG.md` (head only) — the topmost versioned section is `## v0.46.0`; there is currently no `## Unreleased` section. Insert `## Unreleased` directly above `## v0.46.0`.

Read `scripts/build-index.py` and `Makefile` — understand WHY the new guide must contain zero `### RULE` headings: `build-index.py` walks `docs/*.md` and `docs/security/*.md`, and a `### RULE` heading in `docs/security/security-review-pipeline.md` either adds an index entry (breaking the 171 count and `make check-index`) or — if malformed — makes the walker exit 1.
</context>

<requirements>
1. Create `docs/security/security-review-pipeline.md`. Title it `# Security Review Pipeline`. Open with a paragraph naming this guide as the companion to `docs/security/security-review-guide.md` (the mechanical rule base) and `docs/selector-mode-guide.md` (the classify/adjudicate procedure it feeds), using relative links. State plainly that this guide is a **procedure contract**, not an enforceable rule guide: it contains zero `### RULE` headings — including never as a fenced-code illustration, since `scripts/build-index.py` does not skip fenced regions and a `### RULE` line anywhere (even in an example) breaks the index — it adds no index entries, and no agent is bound to it. Do NOT create any other new file (no `.schema.json`, no `scenarios/*`).

2. **Recon pass procedure section.** Document the in-session derivation procedure as step-by-step prose:
   - Enumerate entry points (routes/handlers) from the diff's **touched packages** plus the index of existing handlers when available. State the recall contract verbatim in effect: a missed entry point is a **permanent blind spot** for the review, and over-listing is cheap.
   - Resolve identities (anonymous, authenticated, member, admin, service-account) and auth mechanisms (session-cookie, api-token) from the codebase.
   - Resolve resources and their `authorization_functions` via symbol resolution against the codebase — reusing the existing `trigger` glob machinery, the `@commits` special-case, and the ast-grep funnel. State explicitly: **no new search infrastructure** — no `symbols:`/`imports:` trigger types, no new scripts, no new parse tools; the recon is an in-session LLM procedure documented here, not a binary or detector. If ast-grep/jq are unavailable when the mechanical funnel is reused, the existing Step 4.0/4a fail-fast reports "mechanical funnel unavailable" and the recon continues with judgment-tier resolution only, noting the gap.
   - Derive invariants as `resource → identifier → authorization_function`, with the function's `file:line` as evidence. An invariant's evidence must resolve to a real symbol in the diff/package; a non-resolving invariant is excluded from the applicable set.
   - State the authz-function resolution recall contract: the accuracy ceiling of authz-function resolution is measured and bounded, not solved, in v1.
   - Recovery for under-listing: an entry point missed at enumeration is re-derived by re-running the recon with a wider package scope (diff-touched packages + existing-handler index).
   - Security note: the model is LLM-derived text consumed only by the LLM adjudicator — it is never executed, never parsed as code, never fed into a shell or build step; `file:line` evidence strings are display-only references and the recon writes no files to those paths.

3. **Model schema and lifecycle section.** Include a fenced JSON block (opening fence exactly ` ```json `) for `security-model.json` documenting ALL of these fields: `version` (frozen at `1`), `derived_from` (repo, head, review_id), `entry_points[]` (type, method, path, handler, auth, evidence), `identities[]`, `auth_mechanisms[]`, `resources[]` (name, identifiers, `authorization_functions[]`, evidence), `trust_boundaries[]`, `external_interactions[]`, `invariants[]` (id, statement, evidence, `attack_surfaces[]`). State that every entry carries a `file:line` evidence pointer. State the lifecycle in prose: the model is derived in-session at review start, exists only for the current review session, is written to a session-local path **outside** the reviewed repo's tree (mirroring the existing `/tmp/pr-review-findings.json` pattern), and is **never committed** to any repo. State that no separate `.schema.json` file ships — this guide's documented schema is the source of truth. Failure handling: if the model file is accidentally written inside the reviewed repo tree, delete it and re-write it to the session-local path; two concurrent sessions each derive their own session-local model (no shared state to race on); a recon that aborts mid-derivation discards the partial model and re-runs from scratch on the next invocation (the model is read only at review start, never a half-built file).

4. **Freshness gate and size control section.** Document: at review start, each candidate entry's evidence source is compared against the diff — an entry whose source changed in the diff is re-derived; an unchanged entry is carried forward (`carry forward`); stale-model events surface in the report with the literal `model refresh:` line naming the affected entry (including an entry whose evidence symbol no longer resolves — it is dropped and the line surfaces it). Document size control: classifier and adjudicator input is truncated to **diff-relevant** entries — the entry points and invariants whose attack surface the diff touches — plus the cheap inventory counts; the whole model is never passed as context on large repos. On a diff too large to enumerate (mega-PR), derivation is limited to the touched entry points and invariants and the report notes the truncation.

5. **Attack-surface inventory and drift bridge section.** Document the countable per-review **attack-surface inventory**: HTTP endpoints, authenticated, admin-only, file uploads, external URL inputs, webhooks, HTML rendering, database queries. Document the deterministic diff→traits **drift** bridge: a category-count change selects the matching security trait group — a new HTTP endpoint selects `authz` + `input-origin`; a new file upload selects `input-origin` + `data-to-sink`; a new external-URL input selects `external-io` + `input-origin`; a new webhook selects `external-io` + `authz`; a new render path selects `input-origin`; a new DB query selects `data-to-sink`. State that the inventory is a drift signal that makes the model checkable and the diff→traits selection deterministic.

6. **Report contract section.** Document the Security Model section of the review report: `derived_from`, entry-point count, inventory counts, and any `model refresh:` lines. State that the contract is documented now and wired in task 4 when the security-review signal is set.

7. **Closing "Anti-patterns to refuse" section** (matching the sibling guide's style). Include at least: a hand-maintained model (the model is always derived per review); committing the model to any repo; passing whole-model context on large repos; letting the LLM decide invariant selection (selection is deterministic); adding new search infrastructure (`symbols:`/`imports:` triggers, new scripts) instead of reusing the existing funnel; trading-specific examples (examples stay generic — User, Order, Product, Customer).

8. Add a table row to `README.md` in the "### Go — Infrastructure" table, immediately after the existing `| [Security Review Guide](docs/security/security-review-guide.md) | Mechanical security rule base |` row:
   ```
   | [Security Review Pipeline](docs/security/security-review-pipeline.md) | Per-review evidence-pointered security model derivation (entry points, resources, invariants) |
   ```
   Match the exact surrounding table formatting (same `| Guide | Description |` column shape, no trailing whitespace). Do NOT edit any other README section or row.

9. Add a bullet to `llms.txt` immediately after the existing Security Review Guide bullet (line ~28):
   ```
   - [Security Review Pipeline](docs/security/security-review-pipeline.md): Per-review evidence-pointered security model derivation procedure — entry points, resources + authorization functions, invariants, attack-surface inventory (procedure contract, not a rule guide)
   ```
   Match the existing bullet formatting (dash, space, `[Title](path): description`). Do NOT edit any other section or bullet.

10. Add a `## Unreleased` section to `CHANGELOG.md` directly above the topmost versioned section (`## v0.46.0`), after the frozen preamble header block, with exactly one bullet (follow `docs/changelog-guide.md`; conventional prefix required):
    ```
    ## Unreleased

    - feat: Add docs/security/security-review-pipeline.md — per-review evidence-pointered security-model derivation procedure (entry points, resources + authorization functions, invariants, freshness gate, diff-relevant truncation, attack-surface inventory drift bridge, report contract) and register it in README.md and llms.txt
    ```
    If `## Unreleased` already exists (do not expect it — verify first), append the bullet to it instead of creating a second section. Do NOT touch the four version strings (`CHANGELOG.md` top versioned entry, `plugin.json`, both `marketplace.json` fields).

11. Do NOT touch: `CLAUDE.md` (no Doc↔Agent row — this guide is a procedure contract, not an enforceable rule guide), any `commands/*.md`, `scripts/validate-citations.sh`, any `agents/*.md` (and do NOT create `agents/security-verifier.md`), `docs/security/security-review-guide.md`, `rules/security/*.yml`, `rules/index.json`, `scripts/build-index.py`, `scenarios/*`.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. `.git` is masked in the container; do NOT run `git` commands. Git-based evidence (AC9 `git status --short` scope-lock; AC10 operator DoD walk) runs on the operator side of the spec's Verification ladder.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt.
- Model lifecycle (frozen): per-review, evidence-pointered (every entry carries `file:line`), consumed only by the current review session, written to a session-local path outside the reviewed repo's tree, and **never committed** to any repo. There is no hand-maintained model.
- Freshness gate (frozen): entry evidence source changed in the diff → re-derive; unchanged → carry forward; stale-model events surface in the report with the literal `model refresh:` line.
- No new search infrastructure (frozen): reuse the existing `trigger` glob machinery, the `@commits` special-case, and the ast-grep funnel. No `symbols:`/`imports:` trigger types, no new scripts, no new parse tools. The recon is an in-session LLM procedure documented in the guide, not a new binary or detector.
- `docs/security/security-review-pipeline.md` contains ZERO `### RULE` headings — `scripts/build-index.py` walks `docs/security/*.md`; a heading there fails `make check-index` and changes the 171-entry index. The zero-RULE guarantee covers ANY line whose first three characters are `###` followed by `RULE` (regex `^### RULE\s+`), INCLUDING inside fenced code blocks — `build-index.py` does not skip fenced regions, so a RULE block shown as a fenced example would silently add an index entry (or exit 1 if malformed). Never write `### RULE` even as an illustration.
- Rule identity (frozen): `docs/security/security-review-guide.md` stays at exactly 5 RULE blocks; `rules/security/*.yml` stays at exactly 5 detectors; `rules/index.json` stays at 171 entries. This prompt adds no RULE blocks and does not touch the index.
- Scope-lock (frozen): do NOT modify `scripts/validate-citations.sh`, any `commands/*.md`, or `agents/*.md`; do NOT create `agents/security-verifier.md`. No CLAUDE.md Doc↔Agent row for this guide.
- No config knobs, opt-out flags, or tunable thresholds.
- Generic examples only (User, Order, Product, Customer) — never trading terms; no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin.
- No version-existence claims (no "in v0.47+", no "since v1.2").
- CHANGELOG: a `## Unreleased` bullet describes the security review pipeline, per `docs/dod.md`; the four version strings are NOT touched.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — `.git` is masked).
```bash
# --- Guide exists + AC1 evidence ---
test -f docs/security/security-review-pipeline.md && echo "guide exists: ok"
grep -c 'entry_points' docs/security/security-review-pipeline.md            # must return >= 1
grep -c 'never committed' docs/security/security-review-pipeline.md         # must return >= 1
grep -c '```json' docs/security/security-review-pipeline.md                 # must return >= 1 (fenced JSON schema block)

# --- AC2: recon procedure documented ---
grep -n 'file:line' docs/security/security-review-pipeline.md               # must return >= 1
grep -nE 'touched package|blind spot' docs/security/security-review-pipeline.md   # must return >= 1

# --- AC3: freshness gate + size control ---
grep -n 'carry forward' docs/security/security-review-pipeline.md           # must return >= 1
grep -n 'model refresh' docs/security/security-review-pipeline.md           # must return >= 1
grep -n 'diff-relevant' docs/security/security-review-pipeline.md           # must return >= 1

# --- AC4: attack-surface inventory + drift bridge ---
grep -n 'attack-surface inventory' docs/security/security-review-pipeline.md   # must return >= 1
grep -n 'drift' docs/security/security-review-pipeline.md                      # must return >= 1

# --- AC8: integration references registered ---
grep -n 'security-review-pipeline' README.md                                # must return >= 1
grep -n 'security-review-pipeline' llms.txt                                 # must return >= 1

# --- Scope-lock negatives (container form; git status --short is operator-side) ---
grep -c '^### RULE ' docs/security/security-review-pipeline.md              # must return 0
grep -n 'security-review-pipeline' CLAUDE.md || echo "no Doc<->Agent row: ok"   # must return 0 lines
test ! -f agents/security-verifier.md && echo "no new agent: ok"
grep -rn 'security-review-pipeline' commands/ scripts/validate-citations.sh 2>/dev/null || echo "no command/validator mention: ok"

# --- Rule base untouched ---
grep -c '^### RULE go-security/' docs/security/security-review-guide.md     # must return 5
ls rules/security/*.yml | wc -l                                             # must return 5
python3 scripts/build-index.py | jq length                                  # must return 171

# --- CHANGELOG ---
grep -n -m1 '^## Unreleased' CHANGELOG.md                                   # must return a line
grep -n 'security-review-pipeline' CHANGELOG.md                             # must return >= 1 line (hyphenated form — matches the req-10 bullet text)

# --- Full precommit ---
make precommit                                                              # must exit 0
```
</verification>
