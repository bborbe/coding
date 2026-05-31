# Rule Block Schema

Authoritative reference for the `### RULE` block contract in `docs/*.md` files and the `rules/index.json` index schema. Read this before adding or modifying any rule block.

## ### RULE Block Contract

A rule block is a level-3 Markdown heading (`### RULE`) followed by three required field lines. The walker extracts these into `rules/index.json`.

#### Heading Format

```markdown
### RULE <id> (LEVEL)
```

All on a single line. Example:

```markdown
### RULE go/context-cancel-in-loop (SHOULD)
```

### Required Fields

Immediately beneath the heading, three fields must appear, each on its own line:

```markdown
**Owner**: <agent-name>
**Applies when**: <free-text description>
**Enforcement**: <free-text description>
```

- **Owner**: The `coding:`-prefixed agent name that enforces this rule (e.g. `go-context-assistant`, `python-quality-assistant`).
- **Applies when**: Describes the condition under which the rule fires.
- **Enforcement**: Describes how the rule is enforced — typically a path to an ast-grep rules file plus any LLM-adjudication notes.

### Level Tokens

| Token | Meaning |
|-------|---------|
| `MUST` | Rule is required; violation blocks merge. |
| `SHOULD` | Rule is recommended; violation triggers review but is not a hard block. |
| `MAY` | Rule is optional; informational only. |

### ID Format

Rule IDs must match `<lang>/<topic>/<slug>` where each component contains only lowercase letters (`a–z`), digits (`0–9`), and hyphens (`-`). Each component must have at least one character.

Valid examples:
- `go/context-cancel-in-loop`
- `python/import-order`
- `go/error-wrapping-require-context`

Invalid examples (do not use):
- `Go/Context/CancelInLoop` — uppercase letters not allowed
- `go/context cancel` — space not allowed
- `go//loop` — empty component

### Anchor Derivation

The `anchor` field in `rules/index.json` is **the rule ID verbatim** — slashes are preserved. It is a machine-readable cross-reference key used by the walker and dispatcher, not a browser-clickable GitHub heading slug.

Locator semantics: `(doc_path, anchor)` uniquely identifies a rule block. The dispatcher resolves it via `grep "^### RULE <anchor>" <doc_path>`.

## rules/index.json Schema

The index is a JSON array of rule entries. Top-level key is an array; entries are objects.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `id` | string | Heading `### RULE <id> (LEVEL)` | Rule identifier in `<lang>/<topic>/<slug>` format |
| `level` | string | Heading `### RULE <id> (LEVEL)` | One of `MUST`, `SHOULD`, `MAY` |
| `doc_path` | string | File location | Relative path from repo root to the doc file, e.g. `docs/go-context-cancellation-in-loops.md` |
| `anchor` | string | — | Identical to `id`; the rule ID verbatim, used as a machine-readable cross-reference key |
| `owner` | string | **Owner**: field | The `coding:`-prefixed agent name |
| `applies_when` | string | **Applies when**: field | Copied verbatim |
| `enforcement` | string | **Enforcement**: field | Copied verbatim |

JSON object keys are alphabetically sorted in output.

Example entry:

```json
{
  "id": "go/context-cancel-in-loop",
  "level": "SHOULD",
  "doc_path": "docs/go-context-cancellation-in-loops.md",
  "anchor": "go/context-cancel-in-loop",
  "owner": "go-context-assistant",
  "applies_when": "Go for loop body lacks a non-blocking select { case <-ctx.Done(): ...; default: } check, outside *_test.go and vendor/.",
  "enforcement": "rules/go/cancel-check-in-loop.yml (mechanical flag) + judgment-tier LLM adjudication for long-running enough to matter."
}
```

#### Canonical Example

The canonical rule block is in `docs/go-context-cancellation-in-loops.md` at lines 160–165:

```markdown
### RULE go-context/cancel-check-in-loop (SHOULD)

**Owner**: go-context-assistant
**Applies when**: Go `for` loop body lacks a non-blocking `select { case <-ctx.Done(): ...; default: }` check, outside `*_test.go` and `vendor/`.
**Enforcement**: `rules/go/cancel-check-in-loop.yml` (mechanical flag) + judgment-tier LLM adjudication for "long-running enough to matter".
```

This is the reference implementation. All new rule blocks must follow this structure exactly.

## Anti-patterns

- **Bold headings**: The heading must be `### RULE <id> (LEVEL)` — not `### RULE **<id>** (LEVEL)`.
- **Field order**: Owner → Applies when → Enforcement must appear in that order.
- **Empty components**: `go//loop` is invalid; each of the three ID components must be non-empty.
- **Mixed-case IDs**: `Go/Context/Loop` is invalid; IDs must be lowercase.
- **Non-prefixed owner**: `go-context-assistant` without the `coding:` prefix is invalid in the index but valid in the doc field — the walker adds the prefix on ingestion.
- **Non-array top-level**: `rules/index.json` must be a JSON array, not an object keyed by rule ID.

## Companion Guides

- [ast-grep Rule Writing Guide](ast-grep-rule-writing-guide.md) — conventions for the `rules/<lang>/<id>.yml` ast-grep detectors that mechanical-tier rules cite via `Enforcement:`
