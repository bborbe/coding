---
status: completed
summary: 'Extended scripts/build-index.py with **Class**: field parsing emitting an optional `class` index key, documented the field and key in docs/rule-block-schema.md, appended go-security/resource-ownership and go-security/tenant-isolation invariant RULE blocks (MUST, class: security-invariant, trigger: @commits) to docs/security/security-review-guide.md, regenerated rules/index.json to 180 entries (178 prior entries byte-stable), and added the CHANGELOG ## Unreleased entry; all verification checks pass except 12d which conflicts with the appended mandatory CHANGELOG instruction.'
execution_id: coding-security-comprehensive-rules-exec-048-invariant-rules-class-field
dark-factory-version: dev
created: "2026-08-23T20:53:15Z"
queued: "2026-08-23T20:53:15Z"
started: "2026-08-23T20:54:34Z"
completed: "2026-08-23T20:57:22Z"
---
---
status: pending
spec: [011-security-comprehensive-rules]
summary: Extend scripts/build-index.py with **Class** field parsing → class index key, document the field and key in docs/rule-block-schema.md, append two invariant-linked RULE blocks (go-security/resource-ownership and go-security/tenant-isolation with **Class**: security-invariant, **Trigger**: @commits), regenerate rules/index.json to 180 entries, and leave the tree for the daemon commit.
execution_id: pending
dark-factory-version: dev
branch: dark-factory/security-comprehensive-rules
created: "2026-08-23T20:30:00Z"
---

# Invariant-linked authz rules + walker Class field

<summary>
- Extend `scripts/build-index.py` with `**Class**:` field parsing so a judgment rule can carry an optional `class` index key, emitted verbatim only when present
- Document the new `**Class**:` field and the `class` index key in `docs/rule-block-schema.md` (new `### Optional Field: Class` section, schema-table row, updated example entry)
- Append 2 invariant-linked RULE blocks to `docs/security/security-review-guide.md` — `go-security/resource-ownership` (MUST) and `go-security/tenant-isolation` (MUST), both owner `go-security-specialist`, `**Class**: security-invariant`, `**Trigger**: @commits`, enforcement citing `security-review-pipeline.md`
- Regenerate `rules/index.json` from 178 to 180 entries; all 178 prior entries stay byte-identical (the `Class` field addition is provably non-perturbing)
- The 3 changes ship together: no invariant block exists without walker support, and no walker support ships without the schema documenting it
- Working-tree changes are left for the daemon's `workflow: direct` post-prompt commit; no git is run inside the container
</summary>

<objective>
The invariant-linked authz tier ships: `scripts/build-index.py` recognizes the `**Class**:` field and emits a `class` key on the 2 invariant rules only, `docs/rule-block-schema.md` documents the field and key, the guide gains 2 schema-conformant `go-security/<slug>` blocks (`class: security-invariant`, `trigger: ["@commits"]`, enforcement citing the derived-model pipeline), and `rules/index.json` is regenerated to 180 entries with `make precommit` green and all prior entries byte-stable.
</objective>

<context>
Spec 011 prompt **2 of 3**. Depends on prompt 1 having shipped the 7 judgment-tier rules and reconciled the deferral prose. This prompt bundles three changes that MUST ship together because of an ordering invariant: no intermediate state can have `**Class**: security-invariant` blocks in `docs/security/security-review-guide.md` without walker support, and no walker support can ship without the schema documenting the new field.

Read fully before writing:

- `/workspace/CLAUDE.md` — project conventions, generic content only.
- `/workspace/docs/rule-block-schema.md` — the schema to extend. Today it documents Owner / Applies when / Enforcement (required), Trigger (optional — "immediately after `**Enforcement**:`"), Why (recommended), Bad / Good (recommended). Class does not yet exist.
- `/workspace/scripts/build-index.py` — the walker to extend. Today its `parse_fields()` field-key tuple is `("Owner", "Applies when", "Enforcement", "Trigger")` (line ~64); it maps keys via `key.lower().replace(" ", "_")`. In `walk_docs()` the trigger array block sits after field parsing, before the duplicate-ID check (lines ~152-158). The walker skips `rule-block-schema.md`, walks both `docs/*.md` and `docs/security/*.md`, detects duplicate IDs across both sets, and emits sorted byte-stable JSON.
- `/workspace/docs/security/security-review-guide.md` — contains 5 mechanical + 7 new judgment RULE blocks after prompt 1. The 2 invariant blocks land at the end here.
- `/workspace/docs/security/security-review-pipeline.md` — the procedure contract for invariant adjudication. The 2 new blocks cite this file by relative link `security-review-pipeline.md`. Read this file to write a defensible Enforcement text.
- `/workspace/scripts/validate-citations.sh` — citation gate. Resolves `kind: rule` findings against `rules/index.json` by `rule_id`; it never inspects `class`. Do not modify it.
- `/workspace/Makefile` — `make build-index` regenerates the index; `make precommit` runs check-links/check-json/check-index/check-coverage/check-acceptance/check-rule-tests/bench-test.

The 2 new IDs (two-component `go-security/<slug>` form):

1. `go-security/resource-ownership` (MUST)
2. `go-security/tenant-isolation` (MUST)

Both carry `**Class**: security-invariant` and `**Trigger**: @commits` (always-on, whole-change scoping). Owner: `go-security-specialist`. Neither cites a YAML path or `scripts/rule-checks.sh`, so both derive `enforcement_type: judgment`.
</context>

<requirements>

### 1. Extend `scripts/build-index.py` with `Class` parsing

Three edits to `scripts/build-index.py`, all in service of emitting an optional `class` key on index entries:

(a) **Field-key tuple.** Add `"Class"` to the field-key tuple inside `parse_fields()`. Today the tuple is `("Owner", "Applies when", "Enforcement", "Trigger")`. The new tuple is `("Owner", "Applies when", "Enforcement", "Trigger", "Class")`. The existing `result[key.lower().replace(" ", "_")]` mapping makes the index key `class`. No other rename. Keep Python-stdlib-only (pathlib / json / re / sys).

(b) **Index entry emission.** Inside `walk_docs()`, immediately after the trigger-array block and before the duplicate-ID check, add an analogous block:

```python
if "class" in fields and fields["class"]:
    entry["class"] = fields["class"]
```

The emitted JSON key must be `class` (lowercase, matching the `trigger` field's convention). When the field is absent the entry carries no `class` key — the existing 178 entries stay byte-stable.

(c) **Determinism.** Output must remain byte-stable: when no RULE block carries `**Class**:`, the regenerated index must be byte-identical to the prompt-1 commit's index. Verify with the two-run diff in `<verification>`.

**Do NOT** add a validator for the Class value string. v1 only ships the literal value `security-invariant`; reject no other values yet — the schema doc is the contract.

**Do NOT** refactor `parse_fields()` beyond the field-key tuple edit. Do NOT change the duplicate-ID detection. Do NOT remove the `rule-block-schema.md` skip.

### 2. Document `**Class**:` in `docs/rule-block-schema.md`

Add a new subsection after the existing `### Optional Field: Trigger` section. Title: `### Optional Field: Class`. Content (target wording, adjust to match the doc's prose style):

```markdown
### Optional Field: Class

A small set of judgment-tier RULE blocks carry a `**Class**:` field immediately after `**Trigger**:` (or immediately after `**Enforcement**:` when no Trigger is present). The walker indexes it as a `class` string in `rules/index.json`. The dispatcher uses it to scope which owner agents consume which judgment tier — invariant-linked rules (`class: security-invariant`) require the derived session security model to fire and are scoped by `**Trigger**: @commits`.

```markdown
**Class**: <token>
```

- v1 token: `security-invariant`. Marks a rule that requires whole-repo reasoning against the derived session security model (see `docs/security/security-review-pipeline.md`).
- Missing `**Class**:` field → `class` key omitted from the index entry (no scoping applied).
- All judgment-tier rules MAY carry a Class; mechanical and script rules omit it.
```

Also add a row to the `rules/index.json Schema` table (the field-types table) for the new key:

| `class` | string | Optional **Class**: field | Present only when the doc block includes a `**Class**:` line. v1 value: `security-invariant`. |

Update the `### Anchor Derivation` section if it lists fields that emit index keys — keep the `class` mention consistent.

Also update the JSON example entry near the bottom of the schema doc to include a `class` key in one of the example entries (use a generic `go-security/<slug>`-shaped example so the example doesn't pin a specific rule).

**Do NOT** alter the Required Fields section. **Do NOT** alter the ID Format or Level Tokens sections. **Do NOT** alter the Anti-patterns section.

### 3. Append 2 invariant RULE blocks to `docs/security/security-review-guide.md`

Append after prompt 1's 7 judgment blocks. **Field order is frozen** (schema § Optional Field: Trigger + Class; spec 011 Constraint "Schema contract"): `**Owner**:` → `**Applies when**:` → `**Enforcement**:` → `**Trigger**:` → `**Class**:` → `**Why**:`. `**Trigger**:` sits immediately after `**Enforcement**:`; `**Class**:` sits after `**Trigger**:`, last field before `**Why**:`. Do not reorder, and do not vary between the two blocks. After the field block come `#### Bad` and `#### Good` code blocks.

**Block 8 — `go-security/resource-ownership` (MUST)**
- Owner: `go-security-specialist`
- Applies when: a Go handler / service method outside `*_test.go`, `vendor/`, `mocks/` reads, mutates, or deletes a resource (DB row, file, third-party-API object) addressed by a path parameter, query parameter, body field, or header value, without first verifying that the authenticated user owns the resource. "Owns" is defined per resource by the `authorization_functions` field in the derived session security model (see `docs/security/security-review-pipeline.md`).
- Enforcement: judgment — LLM adjudicator resolves the resource's `authorization_functions` from the derived session security model per `docs/security/security-review-pipeline.md`, fires when the diff accesses a resource by identifier without the owning authorization function enforced, and emits findings as `kind=invariant` with `invariant_id` resolving in the session model.
- Trigger: `@commits`
- Class: `security-invariant`
- Why: resource-ownership gaps are the canonical IDOR / BOLA class — the attacker authenticates as a legitimate user and accesses another user's data via a guessed or harvested identifier. Generic linters cannot detect these: the missing check is the absence of an authorization call, not the presence of a forbidden call. Whole-repo reasoning against the derived model is the only enforcement path.
- Bad:
  ```go
  func GetOrder(w http.ResponseWriter, r *http.Request) {
      orderID := chi.URLParam(r, "orderID")
      order, err := orderRepo.Find(r.Context(), orderID)
      if err != nil {
          http.Error(w, "not found", http.StatusNotFound)
          return
      }
      json.NewEncoder(w).Encode(order)
  }
  ```
- Good:
  ```go
  func GetOrder(w http.ResponseWriter, r *http.Request) {
      user := userFromCtx(r.Context())
      orderID := chi.URLParam(r, "orderID")
      order, err := orderRepo.FindOwnedBy(r.Context(), orderID, user.ID)
      if err != nil {
          http.Error(w, "not found", http.StatusNotFound)
          return
      }
      json.NewEncoder(w).Encode(order)
  }
  ```

**Block 9 — `go-security/tenant-isolation` (MUST)**
- Owner: `go-security-specialist`
- Applies when: a Go handler / service method outside `*_test.go`, `vendor/`, `mocks/` issues a query, mutation, or third-party call scoped by an account / tenant / org identifier without first verifying the authenticated user belongs to that tenant. "Belongs" is defined per tenant resource by the `authorization_functions` field in the derived session security model (see `docs/security/security-review-pipeline.md`).
- Enforcement: judgment — LLM adjudicator resolves the tenant resource's `authorization_functions` from the derived session security model per `docs/security/security-review-pipeline.md`, fires when the diff scopes the call by tenant without the owning authorization function enforced, and emits findings as `kind=invariant` with `invariant_id` resolving in the session model.
- Trigger: `@commits`
- Class: `security-invariant`
- Why: tenant isolation gaps let an authenticated user in tenant A read or mutate tenant B's data via a guessed tenant identifier — cross-tenant data leakage at scale. The authorization check is a missing-call absence, not a forbidden-call presence; whole-repo reasoning against the derived model is required.
- Bad:
  ```go
  func ListInvoices(w http.ResponseWriter, r *http.Request) {
      tenantID := r.URL.Query().Get("tenant_id")
      invoices, err := invoiceRepo.List(r.Context(), tenantID)
      if err != nil {
          http.Error(w, "list failed", http.StatusInternalServerError)
          return
      }
      json.NewEncoder(w).Encode(invoices)
  }
  ```
- Good:
  ```go
  func ListInvoices(w http.ResponseWriter, r *http.Request) {
      user := userFromCtx(r.Context())
      invoices, err := invoiceRepo.ListForTenant(r.Context(), user.TenantID)
      if err != nil {
          http.Error(w, "list failed", http.StatusInternalServerError)
          return
      }
      json.NewEncoder(w).Encode(invoices)
  }
  ```

### 4. Regenerate `rules/index.json`

Run `make build-index`. Expected: `rules/index.json` grows from 178 (prompt 1 end state) to **180 entries**. The 2 new entries must:
- have `id` in `go-security/<slug>` form
- have `owner == "go-security-specialist"`
- have `doc_path == "docs/security/security-review-guide.md"`
- have `anchor == id`
- have `level == "MUST"`
- have `enforcement_type == "judgment"`
- have `trigger == ["@commits"]`
- have `class == "security-invariant"`
- non-empty `applies_when` and `enforcement`

The 171 pre-prompt-1 entries and the 7 prompt-1 entries must be **byte-stable** — adding the `Class` field to the walker MUST NOT mutate any existing entry's bytes (verified by the two-run diff in `<verification>`).

Run `make precommit` — must exit 0.

### 5. Do NOT commit

Do NOT run `git` of any kind — the container's `.git` is masked (`hideGit: true`) and dark-factory's `workflow: direct` post-prompt commit stages and commits all dirty files on completion (repo convention: "Do NOT commit — dark-factory handles git"). Touched paths expected in the daemon's commit: `scripts/build-index.py`, `docs/rule-block-schema.md`, `docs/security/security-review-guide.md`, `rules/index.json`.

</requirements>

<constraints>
- **Rule identity:** the 2 new IDs use the two-component `go-security/<slug>` form (spike Finding 1).
- **Owner:** `go-security-specialist` in every new block and index entry.
- **Schema contract (frozen):** field order `**Owner**:` → `**Applies when**:` → `**Enforcement**:` → `**Trigger**:` → `**Class**:` → `**Why**:`; `**Trigger**:` immediately after `**Enforcement**:`, `**Class**:` after `**Trigger**:`. The `class` index key is emitted only when the `**Class**:` field is present, value verbatim, v1 token `security-invariant`.
- **Walker invariants:** `scripts/build-index.py` stays Python stdlib, keeps the `rule-block-schema.md` skip, keeps duplicate-ID detection, emits byte-stable sorted output. No Class-value validator ships.
- **Enforcement-type derivation:** neither new enforcement field cites `rules/<lang>/<slug>.yml` or `scripts/rule-checks.sh` → both derive `enforcement_type: judgment`; `check-coverage.sh` must not flag an orphan.
- **Extend, don't create:** all changes land in existing files; no new guide, no README/llms.txt/code-review.md changes.
- **No changes to:** `scripts/validate-citations.sh` (unchanged — `kind` rule/invariant/toolchain), `commands/*.md`, `agents/*.md`, `.maintainer.yaml`, `scenarios/`, `rules/security/`, `CHANGELOG.md` (prompt 3's).
- **Index freshness:** this prompt edits RULE blocks and the walker, so it must run `make build-index` and leave `make check-index` green — `make precommit` exits 0.
- **Generic content only:** Bad/Good examples use User, Order, Invoice — never trading or project-specific domains.
- **Git discipline:** no git inside the container (hideGit masks `.git`); the daemon owns the post-prompt commit.
- **Scope split:** the cross-language layout prose and the CHANGELOG entry belong to prompt 3; AC10 (operator-rung fixture walks) is out of scope for all prompts.
</constraints>

<verification>
All commands are container-executable (repo root). No git — `.git` is masked.

```bash
# 1. Two invariant blocks present
grep -Ec '^### RULE go-security/(resource-ownership|tenant-isolation)' docs/security/security-review-guide.md
# expect: 2

# 2. Class field appears exactly twice in the guide (one per invariant block)
grep -c '\*\*Class\*\*: security-invariant' docs/security/security-review-guide.md
# expect: 2

# 3. Each invariant block's enforcement cites the pipeline
grep -c 'security-review-pipeline.md' docs/security/security-review-guide.md
# expect: >=1

# 4. Walker recognises the Class field (string literal in the field-key tuple)
grep -n '"Class"' scripts/build-index.py
# expect: >=1 line

# 5. Schema docs document the field and the key
grep -n '\*\*Class\*\*' docs/rule-block-schema.md   # expect: >=1
grep -n '"class"' docs/rule-block-schema.md         # expect: >=1

# 6. Regenerate, expect 180 entries
make build-index
python3 scripts/build-index.py | jq 'length'
# expect: 180

# 7. Two new entries have the right shape
python3 scripts/build-index.py | jq '.[] | select(.id=="go-security/resource-ownership" or .id=="go-security/tenant-isolation") | {id, level, enforcement_type, owner, class, trigger}'
# expect: 2 entries, class security-invariant, level MUST, enforcement_type judgment, owner go-security-specialist, trigger ["@commits"]

# 8. Only the 2 invariant entries carry a `class` key (no spurious entries)
python3 scripts/build-index.py | jq '[.[] | select(has("class"))] | length'
# expect: 2

# 9. Negative: no three-component security/... IDs; go-security count = 18 (9 existing + 7 prompt-1 + 2 new)
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("security/"))] | length'    # expect: 0
python3 scripts/build-index.py | jq '[.[] | select(.id | startswith("go-security/"))] | length'   # expect: 18

# 10. Determinism + byte-stability — second build-index run produces byte-identical output
cp rules/index.json /tmp/index-run1.json
make build-index
diff /tmp/index-run1.json rules/index.json   # expect: no output (byte-identical — the Class addition perturbed nothing)

# 11. Precommit green
make precommit   # expect: exit 0

# 12. Scope-lock negatives — no out-of-scope files touched; AC9 deferral phrasing still 0 after the append
ls rules/security/*.yml | wc -l   # expect: 5
grep -cE 'follow-up task|until then' docs/security/security-review-guide.md   # expect: 0 (AC9 — no deferral phrasing reintroduced)
grep -c 'rules/security/{go,python,node}' docs/security/security-review-guide.md   # expect: 0 (layout prose is prompt 3's)
awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c 'security'     # expect: 0 (CHANGELOG is prompt 3's)

# 13. Final state — only the four intended files carry changes (do NOT commit)
grep -c 'resource-ownership\|tenant-isolation' docs/security/security-review-guide.md   # sanity: guide edited
jq 'length' rules/index.json                                                              # sanity: index regenerated
```

</verification>

<notes>
- **Field order for invariant blocks (frozen).** Both blocks use `Owner / Applies when / Enforcement / Trigger / Class / Why` — no re-read decision needed. Do not vary between the two blocks.
- **Byte-stability of the 178 committed entries is the critical regression check.** Adding `Class` to the walker must not perturb any other entry. If the two-run diff shows changes to entries that don't carry a `**Class**:` field, the walker edit is wrong — revert and re-apply the field-key tuple edit only.
- **Citation gate is unchanged.** `validate-citations.sh` resolves `kind: rule` findings against `rules/index.json` by `rule_id`; it never inspects `class`. Do not modify the gate.
- **No invariant scenario fixture ships here.** AC10 (the SSRF inline fixture + 007/008 walks) is operator-executable at spec-verification time, not in any prompt. No `scenarios/011-*` file.
- **Generic examples only.** The Bad/Good snippets use User/Order/Invoice-shaped entities. No trading domain.
- **The `Class` value `security-invariant` is the v1 token.** Future tokens (e.g. `architecture-decision`, `cross-cutting-concern`) are out of scope; reject them at code-review time but do not encode the rejection in the walker.
- **Prompt 3 closes the batch.** It lands CHANGELOG, the layout-decision prose, and the final gates. If anything in prompt 3 is missing, prompt 2's work is still mergeable in isolation — the spec's decomposition guarantees it.
</notes>
