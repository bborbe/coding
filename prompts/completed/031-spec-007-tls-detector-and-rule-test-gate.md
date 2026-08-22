---
status: completed
spec: [007-security-rule-base]
summary: Shipped the go-security/tls-insecure-skip-verify detector, its native rule-test + generated snapshot, wired check-rule-tests into make precommit, authored the security-review-guide skeleton with the tls RULE block, extended build-index to walk docs/security/*.md, and regenerated the index to 167 entries — precommit green
execution_id: coding-security-rule-base-exec-031-spec-007-tls-detector-and-rule-test-gate
dark-factory-version: dev
created: "2026-08-22T23:25:00Z"
queued: "2026-08-22T21:36:41Z"
started: "2026-08-22T21:36:43Z"
completed: "2026-08-22T21:38:32Z"
branch: dark-factory/security-rule-base
---

<summary>
- Ships the foundational security detector: `rules/security/tls-insecure-skip-verify.yml`, authored fresh from the pinned pattern (it is untracked and absent from the worktree — do NOT hunt for an existing file)
- Adds its native ast-grep acceptance test (`rule-tests/security/tls-insecure-skip-verify-test.yml`) with a valid snippet (0 findings) and an invalid snippet (≥1 finding), and commits the generated snapshot
- Wires `ast-grep test -c sgconfig.yml` into `make precommit` as the new `check-rule-tests` target — the repo's first CI gate over its native rule-test harness (starts enforcing the existing 46 rule-tests too)
- AUTHORS `docs/security/security-review-guide.md` fresh (untracked, absent from worktree) with the three-tier framing prose and the tls RULE block — one block now, four more appended by prompt 2
- Extends `scripts/build-index.py` to also walk `docs/security/*.md` and regenerates `rules/index.json` so the tls rule is index-visible as `mechanical`, owner `go-security-specialist`
- `make precommit` exits 0 at the end (this is the atomicity seam: the detector YAML and its index reference land together so `check-coverage`'s orphan-YAML / missing-file checks both pass)
- DEVIATION FROM SPEC: the spec's suggested decomposition (detectors in prompts 1-2, guide+index in prompts 3-4) breaks `make precommit` because `check-coverage.sh` fails on a `rules/security/*.yml` that has no `rules/index.json` reference (verified empirically). Guide authoring and the build-index walk extension are therefore pulled into this prompt; the guide grows to its full 5 blocks in prompt 2.
</summary>

<objective>
Author the tls-insecure-skip-verify detector and its native rule-test, wire the rule-test harness into `make precommit`, author the security review guide's skeleton with the tls RULE block, extend the index walker to `docs/security/*.md`, and regenerate the index — leaving `make precommit` green. This is prompt 1 of 4; prompts 2-4 depend on the `check-rule-tests` gate, the `rule-tests/security/` + snapshot dirs, the guide file, and the walk extension all existing.
</objective>

<context>
Read `CLAUDE.md` (repo root) for project conventions — especially the "Adding a new guide" checklist (register in README.md, llms.txt, agents/ — that is prompt 3's job, not this prompt) and the rule-block schema rules.

Read the repo's rule-authoring source-of-truth docs (they ARE the coding plugin's own docs — do not look for them in the plugin dir):
- `docs/rule-block-schema.md` — the `### RULE` block contract: heading format `### RULE <id> (LEVEL)`, required field order Owner → Applies when → Enforcement, optional `**Why**:`, Bad/Good examples, no `**Trigger**:` on mechanical rules, ID format `<lang>/<topic>/<slug>`.
- `docs/ast-grep-rule-writing-guide.md` — YAML detector conventions: six top-level keys (`id`, `language`, `severity`, `message`, `rule`, `ignores`), the 3-line message with a `See docs/...md (RULE <id>).` citation, `constraints` placement (top-level sibling of `rule:`), the `main.go`/`**/main.go` dual-ignore pitfall, and smoke testing. Note: the `pattern.context + selector` struct-literal technique in that guide's "Struct-literal field matching" section does NOT apply to this rule — the pinned pattern below uses the `keyed_element` root form that ast-grep 0.45.1 requires (see the inline comment in the YAML).

Read these existing artifacts to mirror their shape:
- `rule-tests/admin-port-9090-test.yml` — the test-file convention (`id:` + `valid:`/`invalid:` blocks with Go snippets).
- `rules/go/admin-port-9090.yml` and `rules/go/no-fmt-errorf.yml` — detector frontmatter shape (message citation format, `ignores` list). `no-fmt-errorf.yml`'s comment documents the same `type_conversion_expression` silent-zero bug class this task's tls fix is about.
- `Makefile` — current `precommit:` phony list and per-target pattern (`@bash scripts/...`, `@python3 ...`).
- `scripts/build-index.py` — the walker. The change is localized to `walk_docs()`'s glob line (requirement 6).
- `scripts/check-coverage.sh` — understand WHY the detector YAML and its index entry must land in the same prompt: it fails on (a) an index entry citing a missing YAML and (b) a YAML in `rules/` with no index reference. This prompt keeps both satisfied.
- `docs/go-security-linting.md` — an existing guide with inline `### RULE` blocks, for prose/block style reference.

Verify the environment: `ast-grep --version` must report 0.45.1 (the pinned version). `ast-grep test -c sgconfig.yml` must currently exit 0 with 46 passed (baseline).
</context>

<requirements>
1. Create directory `rules/security/` and author `rules/security/tls-insecure-skip-verify.yml` from scratch with EXACTLY this content (it is the empirically-verified pattern for ast-grep 0.45.1 — do not re-derive, do not paraphrase):

```yaml
id: go-security/tls-insecure-skip-verify
language: go
severity: error
message: |
  tls.Config must not set InsecureSkipVerify to true.
  Disabling certificate verification makes the connection vulnerable to man-in-the-middle attacks.
  See docs/security/security-review-guide.md (RULE go-security/tls-insecure-skip-verify).
rule:
  # ast-grep 0.45.1 Go grammar: in type position `tls.Config` is a qualified_type
  # with a fieldless package_identifier child plus a `name` field (NOT a
  # selector_expression); `true` is its own node kind (quote it as 'true' in
  # YAML); keyed_element has no named key/value fields in this grammar, so value
  # scoping goes through the node-text regex `^InsecureSkipVerify:\s*true$`.
  # This form fires on `tls.Config{InsecureSkipVerify: true}` (value or `&`
  # pointer form) and stays silent on `InsecureSkipVerify: false` and on any
  # other tls.Config field (e.g. MinVersion). Verified 2026-08-22 on 0.45.1.
  kind: keyed_element
  all:
    - regex: '^InsecureSkipVerify:\s*true$'
    - inside:
        kind: literal_value
        stopBy: end
        inside:
          kind: composite_literal
          stopBy: end
          has:
            field: type
            kind: qualified_type
            all:
              - has:
                  kind: package_identifier
                  regex: '^tls$'
              - has:
                  field: name
                  kind: type_identifier
                  regex: '^Config$'
ignores:
  - "**/*_test.go"
  - "vendor/**"
  - "**/vendor/**"
  - "**/mocks/**"
```

2. Create directory `rule-tests/security/` and author `rule-tests/security/tls-insecure-skip-verify-test.yml` with EXACTLY this content (the `id:` MUST match the rule id; snippets are repo-controlled Go, never generated at runtime):

```yaml
id: go-security/tls-insecure-skip-verify
valid:
  - |
    package main

    import "crypto/tls"

    func main() {
        cfg := tls.Config{MinVersion: tls.VersionTLS12}
        _ = cfg
    }
invalid:
  - |
    package main

    import "crypto/tls"

    func main() {
        cfg := tls.Config{InsecureSkipVerify: true}
        _ = cfg
    }
```

3. Pre-create the snapshot dir and generate the snapshot:
   - `mkdir -p rule-tests/__snapshots__/go-security`
   - Run `ast-grep test -c sgconfig.yml -U -f tls-insecure-skip-verify` — must exit 0.
   - Confirm `rule-tests/__snapshots__/go-security/tls-insecure-skip-verify-snapshot.yml` was created (do NOT hand-write it; ast-grep generates it).
   - Run `ast-grep test -c sgconfig.yml -f tls-insecure-skip-verify` — must exit 0 with PASS. If it FAILS (the invalid snippet no longer yields a finding, or the valid snippet does), the rule-test gate is doing its job: this is failure mode "detector silently emits zero / over-matches". Fix the YAML pattern (the pinned form is verified — re-check the file bytes for typos first), then re-run. Do not proceed until this passes.

4. Wire the rule-test harness into the Makefile:
   - Add `check-rule-tests` to the `precommit:` phony list, after `check-acceptance` and before `bench-test`:
     `precommit: check-links check-json check-index check-coverage check-acceptance check-rule-tests bench-test`
   - Add a `.PHONY: check-rule-tests` line and this target (matching the existing per-target style):
     ```
     .PHONY: check-rule-tests
     check-rule-tests:
     	@ast-grep test -c sgconfig.yml
     ```
   - Do NOT add `check-rule-tests` to `release-check` (it inherits via precommit) and do NOT change any other target.

5. Create directory `docs/security/` and AUTHOR `docs/security/security-review-guide.md` from scratch with EXACTLY this content (one RULE block now; prompt 2 appends the other four between the tls block and EOF — keep the `## Rules` section so appending is a clean insert before end-of-file):

```markdown
# Security Review Guide

Companion to `go-security-linting.md` (the gosec workflow) and `teamvault-conventions.md` (secret handling). This guide is the source of truth for the mechanical security rule base that Security Review Mode enforces: every rule maps to a detector in `rules/security/*.yml` and an entry in `rules/index.json` owned by `go-security-specialist`.

## Tiers

Security Review Mode organizes rules into three tiers:

- **Mechanical tier** — MUST-level rules enforced by ast-grep detectors (`rules/security/*.yml`). A detector either fires or it does not; enforcement is the YAML path.
- **Judgment tier** — MUST-level rules that require LLM adjudication at review time (SSRF, authorization/IDOR, invariant-preservation concerns).
- **Invariant tier** — rules that require whole-repo reasoning rather than a single AST shape.

The judgment and invariant tiers ship in a follow-up task. This guide currently contains the 5 mechanical-tier rules below.

## Rules

### RULE go-security/tls-insecure-skip-verify (MUST)

**Owner**: go-security-specialist
**Applies when**: a `tls.Config` composite literal sets `InsecureSkipVerify: true` in a `*.go` file outside `*_test.go` and `vendor/`.
**Enforcement**: `rules/security/tls-insecure-skip-verify.yml`
**Why**: disabling certificate verification makes a TLS connection trivially vulnerable to man-in-the-middle attacks; the failure mode is silent exposure of credentials and secrets to an active attacker.

#### Bad

```go
client := &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
    },
}
```

#### Good

```go
client := &http.Client{
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{MinVersion: tls.VersionTLS12},
    },
}
```
```

6. Extend `scripts/build-index.py` to walk `docs/security/*.md` in ADDITION to `docs/*.md`, keeping every existing invariant intact. In `walk_docs()`, replace the iteration line:

```python
    for md_file in sorted(docs_dir.glob("*.md")):
```

with the union of both sets, still sorted and still skipping `rule-block-schema.md`:

```python
    md_files = sorted(set(docs_dir.glob("*.md")) | set(docs_dir.glob("security/*.md")))
    for md_file in md_files:
```

Leave everything else unchanged: the `rule-block-schema.md` skip line, `doc_path` computation (`md_file.relative_to(docs_dir.parent)`), the duplicate-ID detection via `seen_ids` (it already spans the whole loop, so it now covers the union of both walked sets), and the byte-stable sorted output. `md_files` must be a set-union so a file can never be walked twice.

7. Regenerate the index and verify:
   - Run `make build-index` (exits 0).
   - `rules/index.json` must now have 167 entries (was 166), with the new entry `go-security/tls-insecure-skip-verify` having `level: "MUST"`, `doc_path: "docs/security/security-review-guide.md"`, `anchor == id`, `owner: "go-security-specialist"`, `enforcement_type: "mechanical"`.
   - The other 166 entries must be byte-identical to before (same ids, same field values) — the walk extension must not perturb existing `docs/*.md` extraction. Check: the sorted id list minus `go-security/tls-insecure-skip-verify` equals the pre-change id list.

8. Run `make precommit` — must exit 0. If `check-coverage` reports the tls YAML as an orphan or `check-index` reports a stale index, you skipped a step above (the YAML and its index entry must both exist) — fix and re-run. If `check-rule-tests` fails, the snapshot or test file is wrong — fix per requirement 3.

9. Do NOT touch: `README.md`, `llms.txt`, `agents/go-security-specialist.md` (prompt 3 does integration), `commands/*.md`, `scripts/validate-citations.sh`, `CHANGELOG.md`. Do NOT create `agents/security-verifier.md`. Do NOT create any other `rules/security/*.yml` or `rule-tests/security/*` files (prompt 2 does the other four). Do NOT add `## Unreleased` to CHANGELOG (prompt 4 does it).
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. `.git` is a worktree pointer file, unusable inside the container; do NOT run `git` commands.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt.
- Rule identity: two-component `go-security/<slug>` ids, owner `go-security-specialist` in the block and the index entry.
- No new agent file, no command change: do not create `agents/security-verifier.md`, do not modify `commands/code-review.md` or any `commands/*.md`.
- `scripts/build-index.py` stays Python stdlib only.
- Rule-test discipline: the snapshot is generated via `ast-grep test -c sgconfig.yml -U` (with `rule-tests/__snapshots__/go-security/` pre-created) — never hand-written. The plain `ast-grep test -c sgconfig.yml` must pass.
- Snippet contract: the `valid:` snippet must yield 0 findings against this rule; the `invalid:` snippet must yield ≥1 finding. Snippets are repo-controlled Go files, never generated at runtime.
- The guide is authored fresh (untracked, absent from worktree). Do not look for a pre-existing draft. No DRAFT banner, no `~/Downloads/` references, no `security-spike-notes.md` references. Bad/Good examples use generic domains (User, Order, Product, HTTP client) — never trading terms.
- Do NOT edit frontmatter of the spec. Do NOT touch `security-spike-notes.md` (it does not exist in this worktree).
- No config knobs, opt-out flags, or tunable thresholds on the detector or the harness.
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git — `.git` is masked).
```bash
# --- Requirement 1: detector file present with pinned id ---
test -f rules/security/tls-insecure-skip-verify.yml && echo "yaml present: ok"
head -1 rules/security/tls-insecure-skip-verify.yml | grep -q '^id: go-security/tls-insecure-skip-verify' && echo "yaml id: ok"

# --- Requirements 2-3: rule-test + snapshot exist and pass ---
test -f rule-tests/security/tls-insecure-skip-verify-test.yml && echo "test present: ok"
test -f rule-tests/__snapshots__/go-security/tls-insecure-skip-verify-snapshot.yml && echo "snapshot present: ok"
ast-grep test -c sgconfig.yml -f tls-insecure-skip-verify 2>&1 | grep -q "PASS go-security/tls-insecure-skip-verify" && echo "per-rule test PASS: ok"
ast-grep test -c sgconfig.yml 2>&1 | tail -1   # must show 47 passed; 0 failed

# --- Requirement 4: check-rule-tests wired into precommit phony list ---
grep -n 'check-rule-tests' Makefile          # must hit the precommit: line AND the target

# --- Requirement 5: guide exists, exactly 1 RULE block so far, no forbidden content ---
grep -c '^### RULE go-security/' docs/security/security-review-guide.md   # must return 1
grep -nE 'DRAFT|~/Downloads|security-spike-notes' docs/security/security-review-guide.md   # must return 0 lines

# --- Requirements 6-7: walker extension + index regen (167 entries, existing 166 unchanged) ---
grep -n 'security/\*\.md' scripts/build-index.py    # must hit the new glob line
python3 -c "
import json
d = json.load(open('rules/index.json'))
assert isinstance(d, list) and len(d) == 167, f'expected 167 entries, got {len(d)}'
e = [x for x in d if x['id'] == 'go-security/tls-insecure-skip-verify']
assert len(e) == 1, 'tls entry missing from index'
e = e[0]
assert e['level'] == 'MUST', e
assert e['doc_path'] == 'docs/security/security-review-guide.md', e
assert e['anchor'] == e['id'], e
assert e['owner'] == 'go-security-specialist', e
assert e['enforcement_type'] == 'mechanical', e
print('tls index entry: ok')
"

# --- Requirement 8: full precommit green ---
make precommit   # must exit 0
```
</verification>
