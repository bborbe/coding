---
status: completed
spec: [012-intent-aware-review-and-self-containment]
execution_id: coding-intent-drift-exec-050-spec-012-self-containment-guide-and-agent
dark-factory-version: v0.198.7
created: "2026-10-17T20:46:40Z"
queued: "2026-10-17T21:14:48Z"
started: "2026-10-17T21:14:50Z"
completed: "2026-10-17T21:17:21Z"
branch: dark-factory/intent-aware-review-and-self-containment
---

# Self-containment guide, agent, and index regen

<summary>
- Adds a new rule guide that names five self-containment rules for agent-authored diffs
- Four of the rules are deterministic and one is judgment-tier; all five are owned by one new specialist agent
- The rules catch leaked planning context: home-directory paths, requirement ids, references to planning directories or planning prose, revision and sign-off meta, and comments that echo the authoring instruction
- Adds the owning agent, which reads the guide as its source of truth and adjudicates the judgment rule
- Registers the guide and the agent in the plugin's README tables, the machine-readable doc index, and the doc-to-agent alignment table
- Regenerates the derived rule index so the five new rules are discoverable by the shared review funnel
- Nothing is removed: every existing rule entry stays byte-identical
- No script, command, changelog, or scenario file is touched by this prompt
</summary>

<objective>
The shared rule base carries a new self-containment rule family: a new guide ships five `### RULE self-containment/<slug>` blocks (four script-tier, one judgment-tier) plus the owning agent, both registered across the plugin's surfaces, and the derived `rules/index.json` is regenerated from 189 to 194 entries with `make precommit` green and no existing entry altered. This is prompt **1 of 4** for spec 012; prompts 2-4 add the script checks and fixtures, the intent wiring, and the changelog entry.
</objective>

<context>
Read fully before writing:

- `CLAUDE.md` — project conventions: general-purpose content only (User / Order / Product / Customer, never trading or project-specific domains), the Doc ↔ Agent Alignment table, and the "Adding a new guide" checklist. The repo forbids `~/.claude/` and `/Users/bborbe/` in shipped plugin files.
- `docs/rule-block-schema.md` — the authoritative `### RULE` block contract. Heading is `### RULE <id> (LEVEL)` on one line. Three required fields, in this order, each on its own line: `**Owner**:`, `**Applies when**:`, `**Enforcement**:`. Optional `**Trigger**:` comes immediately after `**Enforcement**:` and is MANDATORY on judgment-tier rules. Then a recommended `**Why**:` paragraph, then `#### Bad` / `#### Good` code blocks. ID format is two or more slash-separated lowercase components (`<lang>/<topic>[/<slug>]`).
- `docs/changelog-guide.md` — read the `### RULE changelog/unreleased-entry-required` block: it is a script-tier block whose `**Enforcement**:` line begins `script (\`scripts/rule-checks.sh\`)`. Mirror that shape.
- `docs/git-workflow.md` — read the `### RULE git-workflow/never-direct-commit-to-master` block: a judgment-tier block carrying `**Trigger**: @commits`. Mirror that shape.
- `docs/agent-command-development-guide.md` — the agent-authoring rules (`agent-cmd/agent-frontmatter`: `name` + `description` + `tools`; body sections `When to Use` / `Process` / `Output Format` / `Constraints` / `Success Criteria`; "References to the guide use `coding/docs/` paths"; generic examples only; `README.md` + `llms.txt` entries).
- `agents/security-verifier.md` and `agents/go-context-assistant.md` — the two agent-file shapes to mirror: frontmatter block, `# Purpose`, a "Source of truth" line naming the companion guide, an adjudication section, and a `## Constraints` list.
- `docs/dod.md` — the injected Definition of Done. Two items bind this prompt: "New doc or agent → README.md tables + llms.txt updated" and "Doc ↔ Agent alignment table in CLAUDE.md updated if applicable". Both are satisfied here.
- `scripts/build-index.py` — the walker. Its heading regex is `^### RULE\s+([a-z0-9-]+/[a-z0-9-]+(?:/[a-z0-9-]+)?)\s+\((MUST|SHOULD|MAY)\)$`, so a two-component `self-containment/<slug>` id is valid. `derive_enforcement_type()` returns `mechanical` when the enforcement text matches `rules/[a-z]+/[a-z0-9_-]+\.yml`, `script` when it contains the literal `scripts/rule-checks.sh`, and `judgment` otherwise. `parse_fields()` reads the bold field lines and **copies `Owner` / `Applies when` / `Enforcement` / `Trigger` verbatim into `rules/index.json`** — which is why those field lines must never quote a marker literal (see requirement 1).
- `rules/index.json` — currently **189** entries. This prompt grows it to **194**.
- `README.md` — `### Claude Code Authoring` guides table and the `## Agents` → "Other agents" table. Both are markdown tables with a header row and `|---|` separator.
- `llms.txt` — `## Claude Code Authoring` bullet list of `- [Name](path): description` lines.
- `Makefile` — `make build-index` regenerates `rules/index.json`; `make check-index` fails when the committed index is stale; `make precommit` runs check-links, check-changelog-fold, check-json, check-index, check-coverage, check-acceptance, check-rule-tests, bench-test.

**Verified repo facts this prompt relies on**

- `build-index.py` walks `docs/*.md` and `docs/security/*.md` only — so `docs/self-containment-guide.md` is indexed and nothing under `scripts/` is.
- Two-component ids are already in use: `changelog/*`, `git-commit/*`, `git-workflow/*`, `adr/*`, `agent-cmd/*`, `claude-md/*`.
- The five new rule ids (two-component form, all owner `self-containment-assistant`):

  | id | level | enforcement tier |
  |---|---|---|
  | `self-containment/no-home-dir-paths` | MUST | script |
  | `self-containment/no-requirement-ids` | SHOULD | script |
  | `self-containment/no-planning-doc-refs` | SHOULD | script |
  | `self-containment/no-revision-meta` | SHOULD | script |
  | `self-containment/no-steering-echoes` | SHOULD | judgment |

- `docs/self-containment-guide.md` and `agents/self-containment-assistant.md` do not exist yet.

**The literal-free field-line contract (verbatim — this is the constraint that keeps the index clean)**

`scripts/build-index.py` copies the `Owner` / `Applies when` / `Enforcement` lines verbatim into `rules/index.json`. Any of these marker forms appearing on one of those three lines would land in the index and trip the scope-lock gate. The marker forms are:

```
~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change
```

Note the planning-directory alternative `\b(specs|prompts|docs/plans)/` — the field lines must therefore never write those directory names with a trailing slash. The `**Why**:` paragraph and the `#### Bad` / `#### Good` examples are NOT copied into the index, so they may quote the markers freely.
</context>

<requirements>

### 1. Create `docs/self-containment-guide.md`

Open with an H1 title and a short overview, then a prose section covering all three of these points:

- **What self-containment means** — a diff stands on its own when every artifact it adds resolves inside the repository: no path that only exists on the author's machine, no identifier that resolves only against a planning document, no reference to a planning directory that will never ship, no revision or sign-off meta describing the authoring process, and no comment that echoes the instruction that produced the change.
- **Why agent-authored diffs leak planning context** — the diff is the main input to the review funnel and agents routinely carry artifacts of how the change was planned rather than what it does. Each leak is a defect a human reviewer would flag.
- **That the script tier scans whole changed files, not diff hunks** — the mechanical runner is handed a file list and no base ref, so a self-containment check can flag a pre-existing match on a line the diff never touched. The adjudicator's changed-line filter drops those; narrowing the checks to hunks is out of scope. Point at `commands/pr-review.md` Step 4a, which already states the whole-file contract for the funnel.

Then a section documenting the **six documented exemption paths**, listing them literally (the guide is one of them, so quoting them here is correct): the two planning directories (one for specifications, one for prompts — write them with their trailing slash), the guide itself, the agent file, the mechanical runner script, and the fixtures directory under `scripts/testdata/`. State the rule in both directions:

- planning context belongs *in* the planning directories — the rule catches it leaking *out* of them;
- no artifact outside those six may quote a marker literal. The derived rule index is the sharp case: the walker copies three of the guide's field lines verbatim, so those three lines describe the markers in words ("a home-directory path") and never quote them. An author who genuinely needs a literal adds their artifact to the six — the list is closed and stated here, not a glob a consumer repo can widen.

Then five `### RULE` blocks, in this order, each followed by `**Why**:`, `#### Bad` and `#### Good`. Use generic User / Order / Product / Customer domains throughout. The guide is one of the six exempt paths, so its prose, `**Why**:` paragraphs and Bad/Good examples may quote the marker forms — but its three indexed field lines (pinned below) may not.

**Field-line wording is pinned.** Use exactly these lines so the derived index inherits no marker literal. Do not paraphrase, and do not add a trailing slash to any directory name on a field line.

Block 1:

```
### RULE self-containment/no-home-dir-paths (MUST)

**Owner**: self-containment-assistant
**Applies when**: a changed file carries a path rooted at the author's home directory — a tilde-rooted path or an absolute user-home path — so the path resolves only on the author's machine and never in the repo or a consumer's checkout.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a tilde-rooted path or an absolute user-home path; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: <one or two sentences on the failure mode this prevents>
```

Block 2:

```
### RULE self-containment/no-requirement-ids (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file carries a requirement identifier — an `FR`, `NFR` or `SC` token followed by a number — that resolves only against a planning document that will never be in the tree.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a requirement identifier of the `FR`/`NFR`/`SC` form; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: <one or two sentences>
```

Block 3:

```
### RULE self-containment/no-planning-doc-refs (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file refers to a planning directory that will never ship in the tree — a requirements, prompt or plan folder — or attributes the change to planning prose rather than to the code.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a planning-directory reference or a planning-prose attribution; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: <one or two sentences>
```

Block 4:

```
### RULE self-containment/no-revision-meta (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file records revision or sign-off provenance — a phrase stating the code was revised after a review round, changed at a reviewer's request, or attributed to a sign-off — describing the authoring process instead of the code.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a revision or sign-off provenance phrase; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: <one or two sentences>
```

Block 5 (the judgment-tier block — `**Trigger**:` sits immediately after `**Enforcement**:`, and the enforcement text must cite neither a `rules/<lang>/<slug>.yml` path nor `scripts/rule-checks.sh` so the walker derives `judgment`):

```
### RULE self-containment/no-steering-echoes (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file's comment or identifier restates the instruction that produced the change instead of describing what the code does — the text answers "what was I asked to do" rather than "what does this do".
**Enforcement**: judgment — the adjudicator reads the changed files and flags a comment or identifier that echoes the authoring instruction rather than describing the code.
**Trigger**: @commits
**Why**: <one or two sentences>
```

For blocks 1-4 the `#### Bad` example shows the marker (a tilde-rooted output path; an `FR`-style identifier; a reference to a planning folder plus a planning-prose attribution; a revision-meta line) and the `#### Good` example shows the same artifact made self-contained (a repo-relative path; the behaviour described in words; the rationale stated in the code's own terms; no provenance line at all). For block 5 the `#### Bad` example is a comment that restates the instruction (`# requested: add retry`) and the `#### Good` example is a comment that describes the code (`# retry once, then surface the error`). Never use a real operator path anywhere in the guide: the tilde-rooted examples use a clearly generic destination (e.g. a scratch file name), never a documents directory.

### 2. Create `agents/self-containment-assistant.md`

Follow `docs/agent-command-development-guide.md`. Frontmatter:

```
---
name: self-containment-assistant
description: <one sentence: when to invoke — on the changed files of an agent-authored diff, to catch leaked planning context.>
tools: Read, Grep, Glob
color: <a colour not already used by a sibling agent>
---
```

Body sections:

- `# Purpose` — the agent's job is self-containment of changed files: it adjudicates `self-containment/no-steering-echoes` (the judgment-tier rule) over the changed files, and assigns severity to the script tier's findings for the four script-tier rules.
- A **Source of truth** line naming `docs/self-containment-guide.md` as the rule definitions, with `rules/index.json` entries filtered on `owner: self-containment-assistant` as the machine-readable view. This mirrors `agents/go-context-assistant.md`.
- `## When invoked by the dispatcher` — the dispatcher calls this agent with pre-filtered mechanical findings plus the judgment-tier rule ids it owns; it adjudicates severity and cites the rule by id. Every emitted `rule_id` must exist in `rules/index.json`.
- `## Adjudication` — the judgment rule's test, stated positively: a comment or identifier is a violation when it answers "what was I asked to do" instead of "what does this do". State that a finding on a pre-existing line the diff never touched is dropped, not reported (the whole-file scan contract).
- `## Constraints` — read-only analysis; never invent a `rule_id`; generic examples only; no personal paths in the agent's own text; the agent does not edit files.
- `## Success Criteria` — the verifiable assertions (every emitted rule id resolves in `rules/index.json`; the judgment rule is adjudicated over every changed file; a dropped pre-existing-line finding is not reported).

### 3. Register the guide and the agent

- `README.md` — add a row to the `### Claude Code Authoring` guides table linking the new guide, and a row to the `## Agents` → "Other agents" table for `self-containment-assistant`. Match the existing column shapes exactly.
- `llms.txt` — add a `- [Self-Containment Guide](docs/self-containment-guide.md): <description>` bullet under `## Claude Code Authoring`, and a `- [self-containment-assistant](agents/self-containment-assistant.md): <description>` bullet alongside the other agent references in that file.
- `CLAUDE.md` — add a row to the `### Doc ↔ Agent Alignment` table mapping the new guide to `self-containment-assistant`.

Descriptions on all three surfaces must not quote a marker literal.

### 4. Regenerate `rules/index.json`

`rules/index.json` is a derived artifact. Before regenerating, snapshot the current file so the "nothing removed" property can be proven (this container has no git — see `<verification>`):

```bash
cp rules/index.json /tmp/index-before.json
make build-index
python3 scripts/build-index.py | jq 'length'   # expect 194
```

Expected: the file grows from 189 to **194** entries. The five new entries each have `id` in the two-component `self-containment/<slug>` form, `doc_path == "docs/self-containment-guide.md"`, `anchor == id`, `owner == "self-containment-assistant"`, a level in `MUST`/`SHOULD`/`MAY`, and non-empty `applies_when` / `enforcement`. The four script entries derive `enforcement_type == "script"`; the judgment entry derives `enforcement_type == "judgment"` and carries `trigger == ["@commits"]`. All 189 pre-existing entries stay byte-identical.

`make check-index` must pass afterwards.

### 5. Self-check before finishing

Re-run the `<verification>` block and confirm every expectation; walk each of the five desired behaviours and the index properties above against the actual files. Do not report success if `make precommit` exited non-zero.
</requirements>

<constraints>
- **Rule identity:** all 5 new ids use the two-component `self-containment/<slug>` form, matching `changelog/*`, `git-commit/*`, `git-workflow/*`. Every component is lowercase letters, digits and hyphens only.
- **Owner:** `self-containment-assistant` in every new block and every new index entry.
- **Schema contract (frozen):** field order `**Owner**:` → `**Applies when**:` → `**Enforcement**:`; `**Trigger**:` immediately after `**Enforcement**:` on the judgment rule and absent on all four script rules; `**Why**:` immediately after the last field line (no blank line between them, or the walker stops parsing). Script rules derive `enforcement_type: script` because their enforcement text cites `scripts/rule-checks.sh`.
- **No marker literals on any line this change adds outside the six exempt paths.** The guide and the agent are two of the six exempt paths, so their prose, `**Why**:` paragraphs and examples may quote the markers. Their `Owner` / `Applies when` / `Enforcement` lines may NOT: the walker copies those three lines verbatim into `rules/index.json`, so they describe the markers in words (the pinned wording above does exactly that). `README.md`, `llms.txt` and `CLAUDE.md` are NOT exempt: their added lines must not quote a marker literal.
- **Generic content only:** every Bad/Good example uses User, Order, Product, Customer — never trading or project-specific domains, never a real operator path.
- **No new ast-grep YAML.** All 5 rules are script- or judgment-tier, so `rules/` gains no `.yml` and `scripts/check-coverage.sh` sees no orphan.
- **Do NOT modify** `scripts/build-index.py` (the walker is unchanged — it already parses the three required fields and `Trigger`), `docs/rule-block-schema.md`, `scripts/rule-checks.sh` (prompt 2's single-writer file), `scripts/acceptance.sh` (prompt 2's), `commands/*.md` (prompt 3's), `docs/selector-mode-guide.md` (prompt 3's), `CHANGELOG.md` (prompt 4's), `docs/security/**`, `scripts/validate-citations.sh`, `agents/security-verifier.md`, `.maintainer.yaml`, `scenarios/**`.
- **No new scenario file** — spec 012 ships no scenario; the script tier is locked by committed fixtures asserted in `scripts/acceptance.sh` (prompt 2), and the intent half is exercised by an `--intent` fixture at verification time (prompt 3).
- **Index freshness:** this prompt edits `### RULE` blocks, so it must run `make build-index` and leave `make check-index` green.
- **Do NOT commit and do NOT run any `git` command.** This container's `.git` is masked (`hideGit: true`, confirmed in `.dark-factory.log` as `hideGitSource=arg`), so git fails with `fatal: not a git repository`; the daemon's `workflow: direct` post-prompt commit stages everything on completion. Every verification check below is git-free by design.
- **Cross-prompt boundary:** prompts 2 and 4 depend on the five rule ids existing in `rules/index.json` after this prompt. If `make build-index` leaves fewer than five `self-containment/` entries, the run has failed — report `Status: failed` with an explicit message naming the missing ids.
</constraints>

<verification>
All commands are container-executable from the repo root. This container has **no git** — no check below uses it.

```bash
# 1. Five self-containment RULE blocks, one per expected id
grep -Ec '^### RULE self-containment/' docs/self-containment-guide.md            # expect: 5
grep -Ec '^### RULE self-containment/(no-home-dir-paths|no-requirement-ids|no-planning-doc-refs|no-revision-meta|no-steering-echoes) \((MUST|SHOULD)\)$' docs/self-containment-guide.md   # expect: 5

# 2. Every block carries Why / Bad / Good
grep -c '\*\*Why\*\*' docs/self-containment-guide.md     # expect: 5
grep -c '^#### Bad' docs/self-containment-guide.md       # expect: 5
grep -c '^#### Good' docs/self-containment-guide.md      # expect: 5

# 3. Field order and Trigger placement — Owner before Applies when before Enforcement
grep -nE '^\*\*(Owner|Applies when|Enforcement|Trigger)\*\*:' docs/self-containment-guide.md

# 4. The judgment block is the only one with a Trigger, and it reads @commits
grep -c '^\*\*Trigger\*\*: @commits$' docs/self-containment-guide.md   # expect: 1

# 5. The guide documents the six exemption paths and the whole-file scan contract
grep -c 'whole' docs/self-containment-guide.md          # expect: >= 1 (whole changed files, not diff hunks)
grep -c 'exempt' docs/self-containment-guide.md         # expect: >= 1

# 6. The agent exists with complete frontmatter and names its guide
grep -c '^name: self-containment-assistant$' agents/self-containment-assistant.md   # expect: 1
grep -c 'docs/self-containment-guide.md' agents/self-containment-assistant.md        # expect: >= 1
grep -c '^tools:' agents/self-containment-assistant.md                               # expect: 1

# 7. Registration on all three surfaces
grep -c 'docs/self-containment-guide.md' README.md llms.txt CLAUDE.md
grep -c 'self-containment-assistant' README.md llms.txt CLAUDE.md

# 8. Regenerate and check the index
cp rules/index.json /tmp/index-before.json
cp CHANGELOG.md /tmp/changelog-before.md
make build-index
python3 scripts/build-index.py | jq 'length'                                   # expect: 194
make check-index                                                               # expect: exit 0

# 9. AC1 — the five entries, exactly, with the right shape
python3 scripts/build-index.py | jq -c '[.[] | select(.id|startswith("self-containment/")) | {id,level,enforcement_type,owner,trigger}] | sort_by(.id)'
# expect exactly 5 entries: 4 with "enforcement_type":"script", 1 with "enforcement_type":"judgment"
# (the judgment one additionally carrying "trigger":["@commits"]); every one "owner":"self-containment-assistant";
# every level in MUST/SHOULD.
python3 scripts/build-index.py | jq '[.[] | select((.id|startswith("self-containment/")) and .enforcement_type=="script")] | length'   # expect: 4
python3 scripts/build-index.py | jq '[.[] | select((.id|startswith("self-containment/")) and .enforcement_type=="judgment")] | length' # expect: 1
python3 scripts/build-index.py | jq -r '.[] | select(.id|startswith("self-containment/")) | select(.owner != "self-containment-assistant") | .id'   # expect: no output
python3 scripts/build-index.py | jq -r '.[] | select((.id|startswith("self-containment/")) and (.level|IN("MUST","SHOULD","MAY")|not)) | .id'          # expect: no output

# 10. Nothing removed — the pre-change id set is a subset of the post-change set
comm -23 <(jq -r '.[].id' /tmp/index-before.json | sort) <(python3 scripts/build-index.py | jq -r '.[].id' | sort)
# expect: no output
comm -13 <(jq -r '.[].id' /tmp/index-before.json | sort) <(python3 scripts/build-index.py | jq -r '.[].id' | sort)
# expect: exactly the 5 new self-containment ids

# 11. No marker literal inherited into the index from the guide's field lines
python3 scripts/build-index.py | jq -c '.[] | select(.id|startswith("self-containment/"))' > /tmp/sc-entries.json
if grep -qE '~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change' /tmp/sc-entries.json; then
  echo "FAIL: marker literal present in a self-containment index entry"; else echo "OK: index entries are literal-free"; fi

# 12. No marker literal on the new README / llms.txt / CLAUDE.md lines
if grep -E 'self-containment' README.md llms.txt CLAUDE.md | grep -qE '~/[A-Za-z0-9._-]|/Users/[A-Za-z0-9._-]|/home/[A-Za-z0-9._-]|\b(FR|NFR|SC)-[0-9]|\b(specs|prompts|docs/plans)/|the plan says|as discussed|revised per|as requested in the review|signed off by|v[0-9]+ of this change'; then
  echo "FAIL: marker literal on a new registration line"; else echo "OK: registration lines are literal-free"; fi

# 13. Scope lock — this prompt's files only (absence checks use ! grep -q)
if grep -q 'self-containment' scripts/rule-checks.sh; then echo "FAIL: prompt 2's file was touched"; else echo "OK: rule-checks.sh untouched"; fi
if grep -q 'self-containment' scripts/acceptance.sh;  then echo "FAIL: prompt 2's file was touched"; else echo "OK: acceptance.sh untouched"; fi
if cmp -s CHANGELOG.md /tmp/changelog-before.md;      then echo "OK: CHANGELOG.md untouched"; else echo "FAIL: CHANGELOG.md was modified"; fi
if awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -q '^- '; then echo "FAIL: Unreleased section already present"; else echo "OK: no Unreleased section yet"; fi
test ! -d rules/self-containment && echo "OK: no new ast-grep YAML directory" || echo "FAIL: unexpected rules/self-containment directory"

# 14. Full gate
make precommit   # expect: exit 1 ONLY on check-changelog-fold ("not a git repository"), because .git is masked; every other target must pass
make check-links check-json check-index check-coverage check-acceptance bench-test   # expect: exit 0 — the git-free targets are the real in-container gate
```

Note on `make precommit` in this container: the container's `.git` is masked, and `check-changelog-fold` / `check-rule-tests` shell out to tooling that may need it. If `make precommit` fails **only** on a `check-changelog-fold` / `not a git repository` message, report it in the completion report's `## Improvements` as an environment gap (category: GLOBAL), report `status: partial` with the real exit code, and do not fabricate a green run.
</verification>

<notes>
- **Why the field lines are pinned word-for-word.** `scripts/build-index.py`'s `parse_fields()` copies `Owner` / `Applies when` / `Enforcement` verbatim into `rules/index.json`. Writing the planning directory names with a trailing slash, or quoting the tilde-rooted form, on one of those three lines puts a marker literal into the index and trips the spec's scope-lock gate. The `**Why**:` paragraph and the `#### Bad` / `#### Good` examples are not copied, so they may quote the markers.
- **Field-block parsing is whitespace-sensitive.** Keep `**Why**:` on the line immediately after the last field line — a blank line there makes the walker stop collecting fields (harmless for the required three, but it silently drops the `Trigger` line if one were placed after a blank).
- **`**Trigger**: @commits`** is what makes the judgment rule always a candidate. The dispatcher treats `@commits` as an always-match for PR review; the walker stores it as `"trigger": ["@commits"]`.
- **Two-component ids are already supported** by the walker's regex `([a-z0-9-]+/[a-z0-9-]+(?:/[a-z0-9-]+)?)`, and `changelog/*`, `git-commit/*`, `git-workflow/*`, `adr/*`, `agent-cmd/*`, `claude-md/*` already ship in that form.
- **No git in this container.** `.dark-factory.log` records `hideGit=true hideGitSource=arg`. The pre-change `rules/index.json` baseline is captured with `cp rules/index.json /tmp/index-before.json` *before* `make build-index`, which is the git-free equivalent of reading the file at the target branch. `/tmp` does not persist across prompts, so the comparison must happen inside this run.
- **Prompt 2 is the only writer of `scripts/rule-checks.sh`.** Do not add a check here, even a placeholder — the rule blocks ship first, the enforcement lands next.
- **Open question for the reviewer:** the repo's own "Adding a new guide" checklist in `CLAUDE.md` also mentions adding the agent to `commands/code-review.md`'s agent list. Spec 012's Constraints state that no command file needs editing for the self-containment half (the funnel and the index drive dispatch, and `commands/code-review.md` carries no per-owner agent table — verified). This prompt therefore does not edit any command file. If the reviewer wants an explicit `code-review.md` mention, it belongs in prompt 3.
</notes>
