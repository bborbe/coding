# Confluence Sync Guide

Sync markdown pages to Confluence from a frontmatter marker. Markdown stays the single
source of truth; Confluence is the rendered view for readers who never touch the repo or
vault.

## When to use

- A markdown page should be readable in Confluence (docs, how-tos, runbooks) without
  hand-copying it.
- The page should update in Confluence whenever the markdown changes.
- The page has no Confluence-specific needs beyond standard formatting.

Do not use it for one-off Confluence authoring (write the page directly), reverse sync
(Confluence → markdown), or attachment/media upload.

## Frontmatter contract

Add this to the markdown page's YAML frontmatter:

```yaml
---
confluence_export: true          # marker: this page is syncable
confluence_space: ENG            # target Confluence space key (required)
confluence_page_name: My Guide   # page title (optional; default = file name)
confluence_page_id: "123456"     # optional: update this exact page instead of find/create
---
```

| Field | Required | Meaning |
|-------|----------|---------|
| `confluence_export` | yes | `true` marks the page as syncable; anything else is ignored |
| `confluence_space` | yes | Confluence space key the page is published to |
| `confluence_page_name` | no | Title of the Confluence page (default: the file's name) |
| `confluence_page_id` | no | If set, the tool updates this page; otherwise it finds by space + title, creating it if missing |

The marker is the only control surface. Frontmatter is never part of the published body.

## Conversion behavior

The command converts markdown to Confluence HTML (storage format):

- Headings, paragraphs, tables, fenced code blocks, lists, and links convert 1:1.
- Obsidian wiki-links are handled best-effort: `[[Page]]` becomes `Page`,
  `[[Page|alias]]` becomes `alias`. Cross-vault resolution is out of scope.
- Images and attachments are not uploaded; an image renders as a link unless it is already
  reachable.

## Workflow

```bash
/coding:confluence-sync path/to/page.md     # sync one page (creates or updates)
/coding:confluence-sync --scan <dir>        # list all exportable pages under a directory
```

The command is scriptless and uses the session's Atlassian MCP — no Python, no API token,
no setup. Every create or update is confirmed with you before it hits Confluence.

## DO / DON'T

- DO mark a page `confluence_export: true` only when it is genuinely meant for Confluence
  readers — the marker is a publication, not a bookmark.
- DO keep `confluence_page_name` stable once a page exists; renaming it creates a new page
  instead of moving the old one.
- DO use `confluence_page_id` when the page was created outside this tool and you want to
  update that exact page.
- DON'T put secrets or internal-only content on an exported page — it is published to the
  wiki.
- DON'T hand-copy markdown into Confluence anymore; that is the drift this tool removes.
