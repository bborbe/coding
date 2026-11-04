---
status: draft
spec: [016-bug-review-scripts-argv-e2big]
created: "2026-11-04T15:45:00Z"
branch: dark-factory/bug-review-scripts-argv-e2big
---

# Document the field bounds and record the fix in the changelog

<summary>
- The runner's in-repo schema doc names the two field bounds and the in-string truncation marker.
- The doc explains why the marker lives inside the string rather than in a new JSON field.
- The changelog carries a `- fix:` entry under `## Unreleased`, directly above the newest released section.
- No version string is bumped; release remains a separate step.
- The full `make precommit` chain, including both new fixture tests, is green.
- Shellcheck is clean for both scripts and the shared helper.
</summary>

<objective>
Update `agents/ast-grep-runner.md` and `CHANGELOG.md` so the settled behavior from prompts 1 and 2 is documented and releasable. This is prompt **3 of 3** for spec 016. It covers Desired Behavior 9 and Acceptance Criteria AC9 and AC10.
</objective>

<context>
Read fully before editing:

- `specs/in-progress/016-bug-review-scripts-argv-e2big.md` — Desired Behavior 3, 4, 5 and 9; AC9; AC10; Constraints.
- `agents/ast-grep-runner.md` — the whole file. It is marked DEPRECATED but still carries the authoritative JSON contract that consumers read. The word `truncated` does not occur in it today (`grep -c 'truncated'` returns 0).
- `CHANGELOG.md` — the preamble (`# Changelog`, the "All notable changes" line, the SemVer bullets) and the top of the file. There is **no** `## Unreleased` section today; the newest section is `## v0.65.4`. The changelog convention places `## Unreleased` directly above the highest `## vX.Y.Z`, after the preamble block.
- `/home/node/.claude/plugins/marketplaces/coding/docs/changelog-guide.md` — the `## Unreleased` placement rule, the conventional-prefix rule (`fix:` is in the allowed set), and the frozen-preamble rule.
- `scripts/rule-checks.sh` — its `check_changelog_preamble_frozen` and `check_changelog_unreleased_entry_required` checks run over changed files; the inserted section must sit after the preamble and start with a recognised prefix.
- `Makefile` — `precommit` now includes `test-ast-grep-runner-truncation` and `test-rule-checks-argv` from prompts 1 and 2.

**Verified repo facts this prompt relies on**

- `CHANGELOG.md` currently begins with the preamble and then `## v0.65.4`; inserting `## Unreleased` immediately above `## v0.65.4` matches the documented layout.
- AC9's awk extraction is `awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- fix:'`; the bullet must start with `- fix:`.
- `grep -c 'truncated' agents/ast-grep-runner.md` returns 0 today.
- The version strings are intentionally not bumped here: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and the changelog version heading are aligned only at release time.
</context>

<requirements>

### 1. Document the bounds in `agents/ast-grep-runner.md`

Add a new section immediately after the JSON contract code block, before the final "See `scripts/ast-grep-runner.sh` for exit codes..." line, with this content:

```markdown
## Field bounds

Each finding's `matched_text` is bounded to 8192 bytes and its `message` to
1024 bytes. Both are cut on a UTF-8 rune boundary; a cut never emits a partial
multi-byte sequence. A field that was cut ends with
`…[truncated, original <N> bytes]`, where `<N>` is the pre-cut byte length.

The marker is part of the string value, not a separate JSON field. The consumer
(`bborbe/github-pr-review-agent/pkg/funnel.go`) unmarshals findings into a fixed
seven-field struct and re-marshals it, so an extra field would be stripped; an
in-string marker survives any consumer that passes the string through.

A `matched_text` or `message` under its bound is emitted byte-for-byte as
before, with no marker.
```

Keep the existing JSON contract and the deprecation notice unchanged.

### 2. Add the changelog entry

Insert a `## Unreleased` section directly above `## v0.65.4`, after the preamble block. Use exactly this bullet shape (the text may be adjusted for accuracy, but it must start with `- fix:` and name the observable change):

```markdown
## Unreleased

- fix: **the mechanical review runner no longer dies on large findings.** `scripts/ast-grep-runner.sh` and `scripts/rule-checks.sh` now assemble each finding from files (`--rawfile`) and the aggregate from a file (`--slurpfile`) instead of passing payloads as command-line arguments, which the kernel rejects at 128 KiB (`jq: Argument list too long`) and which silently dropped every script-tier finding on an ordinary large PR. `matched_text` is bounded to 8192 bytes and `message` to 1024 bytes, cut on a UTF-8 rune boundary, with an in-string `…[truncated, original <N> bytes]` marker so the consumer's fixed seven-field struct keeps it. Fixture tests cover a 131072-byte match, a message over 1024 bytes, a 200-finding aggregate over 128 KiB, and byte-identical output for small matches.
```

Do not move, delete or edit the frozen preamble. Do not rename the existing released sections. Do not add a version number to the new section.

### 3. Do not bump versions

Leave `CHANGELOG.md`'s `## v0.65.4` heading, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and any tags untouched. Version alignment is enforced only by `make release-check` at release time.
</requirements>

<constraints>
- The emitted JSON schema, key names and types do not change; the marker stays inside the string.
- The documented bounds are fixed values (8192 and 1024), not knobs.
- The changelog entry must be under `## Unreleased` and start with `- fix:`.
- The changelog preamble (from the first line through the SemVer bullets) is frozen: insert the new section after it, never inside or above it.
- No version bump in this prompt.
- Do not change any script or test in this prompt; prompts 1 and 2 own them.
- Do NOT commit — dark-factory handles git.
- `make precommit` must pass, including both new fixture tests and `scripts/acceptance.sh`.
</constraints>

<verification>
Run from the repo root:

```bash
make precommit
shellcheck scripts/ast-grep-runner.sh scripts/rule-checks.sh scripts/lib/truncate-utf8.sh
test "$(grep -c 'truncated' agents/ast-grep-runner.md || true)" -ge 1
test "$(awk '/^## Unreleased/{f=1;next}/^## v/{f=0}f' CHANGELOG.md | grep -c '^- fix:' || true)" -ge 1
```

Also assert the AC6 final gate (both scripts are fixed by prompts 1 and 2):

```bash
test "$(grep -cE -- '--arg(json)? (matched_text|message)' scripts/ast-grep-runner.sh scripts/rule-checks.sh | awk -F: '{s+=$2} END{print s+0}')" -eq 0
test "$(grep -c -- '--argjson findings_by_owner' scripts/rule-checks.sh || true)" -eq 0
```

AC9 is proven by the two `grep`/`awk` assertions. AC10 is proven by `make precommit` and the shellcheck command.
</verification>
