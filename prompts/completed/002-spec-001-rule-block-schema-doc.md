---
status: completed
spec: [001-rule-base-interfaces-and-walker]
summary: 'Created docs/rule-block-schema.md defining the ### RULE block contract and rules/index.json schema; updated README.md and llms.txt with new doc link; added CHANGELOG.md entry.'
container: coding-rule-base-pilot-exec-002-spec-001-rule-block-schema-doc
dark-factory-version: v0.173.0
created: "2026-05-31T19:51:00Z"
queued: "2026-05-31T20:01:51Z"
started: "2026-05-31T20:01:52Z"
completed: "2026-05-31T20:04:58Z"
branch: dark-factory/rule-base-interfaces-and-walker
---

<summary>
- New schema doc `docs/rule-block-schema.md` defines the `### RULE` block contract (required fields, level tokens, ID format, anchor derivation)
- Same doc defines the seven fields of `rules/index.json` entries
- Canonical example cited: `docs/go-context-cancellation-in-loops.md`
- README.md updated with link in "Claude Code Authoring" table
- llms.txt updated with entry under appropriate section
</summary>

<objective>
Create the schema doc that locks the contracts for `### RULE` blocks in `docs/*.md` and for `rules/index.json`. This doc is the authoritative reference for any future rule author — it must describe what already exists in `docs/go-context-cancellation-in-loops.md`, not require changes to it.
</objective>

<context>
Read `docs/go-context-cancellation-in-loops.md` — specifically lines 160–165 which contain the existing `### RULE` block. This is the canonical example the schema doc must cite verbatim.
Read `docs/dod.md` — it already references the rule-block structure; the new schema doc supersedes and fully documents what dod.md sketches.
Read `scripts/check-versions.sh` — the new schema doc should follow a similar style (clear sections, generic examples, no personal paths).
</context>

<requirements>
1. Create the file `docs/rule-block-schema.md`.
2. The doc must start with a title and brief overview (1-2 sentences): what this doc is for and who should read it.
3. Add a section titled "### RULE Block Contract" that defines:
   - The heading format: `### RULE <id> (MUST|SHOULD|MAY)` on a single line
   - The three required fields that must appear beneath the heading, each on its own line:
     - `**Owner**: <agent-name>` — the `coding:`-prefixed agent name (e.g. `go-context-assistant`)
     - `**Applies when**: <free-text description>` — when the rule fires
     - `**Enforcement**: <free-text description>` — how it is enforced
   - The level tokens: `MUST` (required), `SHOULD` (recommended), `MAY` (optional)
   - The ID format: `<lang>/<topic>/<slug>` where each component is lowercase letters, digits, and hyphens only, with at least one character per component
   - The anchor derivation rule: the `anchor` field is **the rule ID verbatim** (with slashes preserved). It is used as a machine-readable cross-reference key by the walker and dispatcher — NOT as a browser-clickable GitHub heading slug. Locator semantics: `(doc_path, anchor)` uniquely identifies a rule block; the dispatcher resolves it via `grep "^### RULE <anchor>" <doc_path>`.
4. Add a section titled "rules/index.json Schema" that defines the seven fields of each entry in the index:
   - `id` (string) — the rule ID, sourced from the `### RULE` heading
   - `level` (string) — one of `MUST`, `SHOULD`, `MAY`, sourced from the heading
   - `doc_path` (string) — the relative path from repo root to the doc file (e.g. `docs/go-context-cancellation-in-loops.md`)
   - `anchor` (string) — same value as `id`; the rule ID verbatim, used as a machine-readable cross-reference key (not a GitHub slug)
   - `owner` (string) — the agent name from the `Owner:` field
   - `applies_when` (string) — the text from the `Applies when:` field, copied verbatim
   - `enforcement` (string) — the text from the `Enforcement:` field, copied verbatim
   - State explicitly: top-level is a JSON array, entries are objects, keys are alphabetically sorted in output
5. Add a "Canonical Example" section that cites `docs/go-context-cancellation-in-loops.md` by path and reproduces (or closely describes) the heading line and the three field lines as they appear in that file at lines 160–165.
6. Use generic examples only (User, Order, Product, Customer) — no trading-domain identifiers.
7. Update `README.md`: add a row to the "Claude Code Authoring" table with the new doc: link text `Rule Block Schema`, link target `docs/rule-block-schema.md`, description `### RULE block contract and index schema`.
8. Update `llms.txt`: add a line in the "Claude Code Authoring" section: `- [Rule Block Schema](docs/rule-block-schema.md): ### RULE block contract and index schema`.
</requirements>

<constraints>
- Do NOT rewrite `docs/go-context-cancellation-in-loops.md` — the schema doc must describe what is already there
- Generic examples only (User, Order, Product, Customer) — no Candle, Epic, Broker, SignalStore
- No personal paths anywhere
- `scripts/check-versions.sh` and the four-version-alignment surface are not modified
- `make precommit` exit behavior is unchanged by this prompt
- **Do NOT include a literal `### RULE <id> (LEVEL)` heading anywhere in `docs/rule-block-schema.md`.** When showing the canonical example, use a fenced code block (\`\`\`markdown ... \`\`\`) or a `#### Example` (H4) heading — never a real `### RULE` H3. The walker in prompt 2 picks up every `### RULE` H3 across `docs/`; an example heading here would create a phantom index entry and break the pilot smoke (`len(d) == 1` would become `len(d) == 2`).
</constraints>

<verification>
Run the following commands from the repo root and confirm each exits 0:
```
# Schema doc exists and covers rule block contract — match bolded or unbolded field labels and level tokens anywhere
grep -nE '(\*\*)?(Owner|Applies when|Enforcement|Anchor)(\*\*)?:|\b(MUST|SHOULD|MAY)\b' docs/rule-block-schema.md | wc -l
# Should return >= 6

# Schema doc covers all seven index fields
for field in id level doc_path anchor owner applies_when enforcement; do
  grep -q "\\b$field\\b" docs/rule-block-schema.md && echo "$field: ok" || echo "$field: MISSING"
done

# Schema doc cites the canonical example
grep -n 'go-context-cancellation-in-loops' docs/rule-block-schema.md

# README.md has the link
grep -n 'rule-block-schema' README.md

# llms.txt has the entry
grep -n 'rule-block-schema' llms.txt

# make precommit still passes
make precommit
```
</verification>
