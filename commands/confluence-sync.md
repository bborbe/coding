---
allowed-tools:
  - Read
  - Glob
  - mcp__atlassian__getAccessibleAtlassianResources
  - mcp__atlassian__getConfluenceSpaces
  - mcp__atlassian__searchConfluenceUsingCql
  - mcp__atlassian__getConfluencePage
  - mcp__atlassian__createConfluencePage
  - mcp__atlassian__updateConfluencePage
argument-hint: "[<file.md> | --scan <dir>]"
description: Sync markdown pages carrying the confluence_export frontmatter marker to Confluence (create/update via the Atlassian MCP)
---

# Confluence Sync

Publishes markdown pages to Confluence, driven by frontmatter. A page marked with
`confluence_export: true` (plus a target space) is the source of truth; Confluence is the
rendered view. Frontmatter is always stripped before publish.

This command is scriptless by design: it reads and converts the markdown with its own
tools and writes through the Atlassian MCP, which carries the session's credentials. No
Python, no API tokens, no setup.

## Usage

```bash
/coding:confluence-sync path/to/page.md      # sync one exportable page
/coding:confluence-sync --scan <dir>         # list every exportable page under a directory
```

The frontmatter contract is documented in `docs/confluence-sync.md`.

## Your Task

### Sync a single page

1. Resolve the file path. If the argument is a bare page name, locate it with `Glob` first.
2. Read the file and parse the YAML frontmatter block between the leading `---` lines.
3. Validate:
   - `confluence_export` must be truthy (`true` — the string `"true"` counts).
   - `confluence_space` must be present and non-empty.
   - If either fails, report which field is missing and STOP.
4. Convert the body (frontmatter stripped) to Confluence HTML, `contentFormat: "html"`:
   - headings → `<h1>`–`<h6>`, paragraphs → `<p>`
   - tables → `<table>/<thead>/<tbody>/<tr>/<th>/<td>`
   - fenced code → `<pre><code class="language-...">`
   - lists → `<ul>/<ol>/<li>`, links → `<a href="...">`
   - wiki-links best-effort as plain text: `[[Page]]` → `Page`, `[[Page|alias]]` → `alias`
   - keep the body under ~18,000 characters (Confluence limit) — if it exceeds it, truncate
     the HTML and say so.
5. Resolve the target page (cloudId from `mcp__atlassian__getAccessibleAtlassianResources`):
   - If `confluence_page_id` is set: fetch it via `mcp__atlassian__getConfluencePage`.
   - Else: search via `mcp__atlassian__searchConfluenceUsingCql` with
     `space = "<space>" AND title = "<page_name>" AND type = page`. Take the first hit.
   - Page title = `confluence_page_name` frontmatter, defaulting to the file name.
6. **Confirm before any write.** Show the target space, page title, and whether this is a
   create or an update, then get an explicit yes. This is a published, team-visible wiki —
   never create or update a Confluence page without confirmation.
7. Execute:
   - Found (or `confluence_page_id` set): `mcp__atlassian__updateConfluencePage` with
     `pageId`, `body` = converted HTML, `contentFormat: "html"`.
   - Not found: `mcp__atlassian__createConfluencePage` with `spaceId` = space key, `title`,
     `body` = converted HTML, `contentFormat: "html"`.
8. Report the outcome (created/updated, page id, title, link if available).

### Scan mode

Glob `**/*.md` under the directory, read each file's frontmatter, and list the exportable
ones (path, space, page name, page id). If the user wants to sync some, run the single-page
flow per file — each write still needs its own confirmation.

## Constraints

- NEVER send frontmatter as part of the body — strip it before converting.
- NEVER write to Confluence without showing the target and getting an explicit yes.
- NEVER hardcode a space key, page id, or personal path — everything comes from the file's
  frontmatter or the user's arguments.
- NEVER create scripts or heredocs for this task — this command is scriptless by design.
