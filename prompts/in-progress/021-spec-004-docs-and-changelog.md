---
status: approved
spec: [004-bench-review-environment-control]
created: "2026-08-08T08:08:00Z"
queued: "2026-08-08T08:19:41Z"
---

<summary>
- The benchmark's own documentation now states what an operator has to have in place before a run, in the place the operator actually reads
- It names the one environment variable that must be exported, says the runner deliberately never sets it, and explains why setting it would silently change how every run authenticates
- It describes where the runner looks to decide which copy of the rule set the review will really load, and lists every condition that stops a run before it starts
- An operator hitting one of those conditions can act on the message without reading the runner's source
- It records the guarantee that the working copy handed to the review carries exactly two comparison points and nothing else
- It says what a failed run leaves behind and where to find it
- The changelog entry describes the whole of this work — all three defects — so the release classifier weighs it correctly instead of cutting a patch for the last slice
- A final sweep confirms no personal filesystem paths and no third-party dependencies were introduced anywhere in the benchmark
- The full repository gate runs green with a larger test suite than before
- Deliberately the last piece of this spec, so the documentation describes what actually shipped rather than what was planned
</summary>

<objective>
Write down, in `bench/README.md`, the three operator-facing facts this spec establishes — the authentication precondition and why the runner refuses to satisfy it, the plugin load path the start-up check resolves together with every condition that aborts a run, and the two-ref guarantee for the prepared working copy — and consolidate `CHANGELOG.md`'s `## Unreleased` section so one reader sees the whole change. Last prompt of spec 004, deliberately last so the changelog describes what all three earlier prompts actually shipped: spec 002's final prompt described only its own slice and the release classifier cut a patch instead of a minor.
</objective>

<context>
Read `CLAUDE.md` for project conventions (Python 3 stdlib only, no personal paths, generic examples only, never commit — dark-factory handles git).

Read `specs/in-progress/004-bench-review-environment-control.md`. This prompt satisfies **Desired Behavior 5** and **Acceptance Criteria AC1, AC14, AC15 and AC16**. Load-bearing sections:

- **Non-goals**: "Do NOT make `review_env()` supply an authentication token. Any value of `ANTHROPIC_AUTH_TOKEN` switches Claude Code into API-key mode and bypasses the OAuth path entirely — for every operator, including those whose OAuth works. Silently changing the authentication path of a measurement instrument to save one `export` is a worse trade than documenting the `export`." Document the `export`; never add the token.
- **Constraints → CHANGELOG**: conventional prefixes (`fix:` / `feat:` / `docs:`) per `docs/changelog-guide.md`; the non-conforming `bench:` style used in v0.35.1 is not repeated, because dark-factory's version-bump detector reads the prefix. "**The entry describes the whole change, not the last prompt's slice.**"
- **AC14's anti-keyword-stuffing clause**: the five README patterns must match on **at least four distinct line numbers**, and each of the three topics must be its own prose block of **≥3 non-empty lines under its own heading**. "Without this, one keyword-dense line satisfies every grep while documenting nothing."
- **AC16's anti-keyword-stuffing clause**: the three CHANGELOG topic patterns must match on **exactly three distinct bullet lines**, and the section must contain **≥3 bullets**.

**This prompt depends on prompts 1, 2 and 3 of this spec having landed.** Verify before you start:

```bash
grep -n 'def resolve_plugin_load_path\|def load_install_records\|def resolution_line' bench/run.py
grep -n 'def prune_refs\|def publish_keep_refs' bench/run.py
grep -n 'def write_failure_artifact\|FAILURE_STDOUT_LABEL' bench/run.py
```

If any of `resolve_plugin_load_path`, `prune_refs` or `write_failure_artifact` is absent, stop and report `status: failed` with the message `"prompts 1-3 of spec 004 not yet landed"`. Do not implement them here.

Read `bench/run.py` — the shipped behaviour you are documenting. **Take every documented fact from the code, not from this prompt and not from memory.** In particular read: the install-record constants and abort markers, `installed_plugins_path`, `plugin_cache_root`, `load_install_records`, `record_applies`, `select_install_record`, `resolve_plugin_load_path`, `check_plugin_resolution`, `resolution_line` (prompt 1); `keep_ref_name`, `synthetic_ref_names`, `publish_keep_refs`, `prune_refs` and their call site in `prepare_worktree` (prompt 2); `FAILURE_ARTIFACT_SUFFIX`, `FAILURE_STDOUT_LABEL`, `FAILURE_STDERR_LABEL`, `FAILURE_EMPTY_STREAM_MARKER`, `failure_artifact_path`, `write_failure_artifact` and the three call sites in `process_pr` (prompt 3); and `review_env`, which sets exactly `CLAUDE_CONFIG_DIR` and `DISABLE_AUTOUPDATER` and no token. Quote the real marker literals and the real path shapes; do not describe anything the code does not do.

Read `bench/README.md` — the file you extend. It already documents the configuration tuple, `prs.json`, how to run it, the diff-range rule, the harvest contract (`## Reading review output`), how to verify an entry without cloning, `## Fixed invariants`, `## Safety invariant` and the result-row schema. It says nothing about authentication, nothing about where the plugin is loaded from, and nothing about the ref set. Match its voice: short declarative sections, a `##` heading per topic, tables where the shape fits, and a `> **Why …**` paragraph wherever a reader would otherwise restore the wrong behaviour. Its existing `## Fixed invariants` bullet about the isolated config directory still describes the *old* preflight ("would resolve the `coding` plugin to content whose hash differs from `--coding-repo`'s") and must be brought in line with what prompt 1 shipped.

Read `CHANGELOG.md` — it currently has **no** `## Unreleased` section; the newest section is `## v0.35.2`. The frozen header runs from `# Changelog` down to the last `* PATCH …` bullet; `## Unreleased` goes immediately after that header line and directly above `## v0.35.2`. Note that v0.35.1's three `- bench: …` bullets are the file's only non-conforming entries and are exactly the release that under-described a 1,075-line change.

Read `docs/changelog-guide.md` — `RULE changelog/preamble-frozen` and `RULE changelog/conventional-prefix-required`, plus the prefix→bump table (`feat:` → minor, everything else → patch).

Read `docs/dod.md` — no personal paths anywhere, a `## Unreleased` CHANGELOG entry required, 4-version alignment NOT touched (releases are manual, handled by maintainer-agent-releaser).
</context>

<requirements>

## 1. Three new sections in `bench/README.md`

Place all three after the existing `## Running it` section and before `## Diff-range rule` — authentication and plugin resolution are preconditions of running, and the ref guarantee describes what a run then hands the reviewer. Each is its own `##` heading with **at least three non-empty prose lines** of its own; AC14 rejects a single keyword-dense line.

### a. The authentication precondition

State: which environment variable must be exported before a run (`ANTHROPIC_AUTH_TOKEN` is the variable the runner deliberately does **not** set — name the variable an operator must actually have in place for the live `claude` invocation to authenticate, taking it from `review_env` and the surrounding invocation rather than inventing one); that the runner deliberately does not set it; and why — any value of `ANTHROPIC_AUTH_TOKEN` switches Claude Code into **API-key mode** and bypasses the OAuth path entirely, for every operator including those whose OAuth works. Setting it to save one `export` would silently change the authentication path of a measurement instrument.

In the same section, say what a failed run leaves behind: one artifact per failed (PR, configuration) pair under `bench/.cache/failures/`, carrying **both** of the subprocess's output streams under the labels the runner writes, with an empty stream explicitly marked empty. Record why in a `> **Why …**` note: Claude Code writes its real errors to stdout while stderr carries incidental warnings, so an artifact holding only stderr preserves the wrong half — an expired OAuth session was once diagnosed wrongly for exactly this reason.

### b. The plugin load path and the abort conditions

State the shape the check resolves, taken from the code: the isolated config directory's install record at `<config dir>/plugins/installed_plugins.json`, whose entry for the plugin names an install path under `<config dir>/plugins/cache/<marketplace>/<plugin>/<version>/`, and that this recorded path — not the marketplace directory, and never a version inferred from the directory names — is what gets hashed and compared against `--coding-repo`.

List every condition that aborts the whole run before the first review, with the marker literal the runner prints for each (read them from the constants in `bench/run.py`; do not paraphrase them). A table is the right shape:

| Condition | What the operator does |
|---|---|
| no install record for the plugin | install the plugin into the isolated config directory |
| the record cannot be read or parsed | repair or reinstall |
| the recorded install path is not on disk | reinstall, which rewrites the record |
| the recorded install path lies outside the config directory's own plugin tree | reinstall so the record names a path inside it |
| the record applies only to a different working directory | install at user scope |
| the resolved content hash differs from `--coding-repo` | reinstall or repoint the plugin |

State that there is no fallback: the marketplace directory is never hashed and never used as a rescue path, because a resolution that agrees with nothing produces a measurement that cannot be attributed. State that a passing check prints one line naming the resolved load path, the recorded version and the content hash, so the claim can be cross-checked against the filesystem without reading the source.

The section must contain the literal `installed_plugins.json` (or `install record`) and the literal `plugins/cache`.

### c. The two-ref guarantee

State that before any review is invoked, the prepared working copy under `bench/.cache/repos/` contains exactly the checked-out head branch `bench-pr-<N>` plus the two synthetic remote-tracking refs `origin/bench-base-<N>` and `origin/bench-pr-<N>`, and nothing else: every other branch, every other remote-tracking ref, every tag and the default-branch symref are removed on **every** run, including against a cache directory an earlier version of the runner populated. State that the commits the manifest names stay reachable, so range resolution and the offline short-circuit still work and a repeat run needs no fetch.

Record why in a `> **Why …**` note: the upstream repository's real branches are what made the reviewer answer with "Target branch options: 1. `main` … Which should I use as the target for comparison?" instead of reviewing, while an earlier run with identical inputs reviewed correctly. Removing the alternatives removes the question; instructing the reviewer more firmly would leave the choice present and make determinism a property of the model's disposition.

The section must contain the literal `bench-base-` (or the phrase `two synthetic`).

## 2. Update the existing `## Fixed invariants` list

Bring the isolated-config bullet in line with what shipped: the runner aborts the whole run before the first review when the plugin the isolated config directory will actually load — the directory named by its install record — resolves to content whose hash differs from `--coding-repo`'s, or when any of the abort conditions in section 1b holds. Add the failure-artifact location (`bench/.cache/failures/`, one file per failed (PR, configuration) pair, both streams labelled) and the two-ref guarantee to the same list. These are invariants, not knobs — do not document a configuration option that does not exist, and do not invent one.

Do not restate the harvest contract; `## Reading review output` already owns it and is unchanged by this spec.

## 3. Add the `## Unreleased` CHANGELOG entry

Insert `## Unreleased` immediately after the frozen header block (the `# Changelog` title, the "All notable changes…" line, the SemVer link line and the three MAJOR/MINOR/PATCH bullets) and directly above `## v0.35.2`. Do not move, delete or insert anything inside the header. Do not create a version section, do not rename `## Unreleased` to a version, do not touch any released section, and do not touch the four version strings in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

The section carries **four** bullets: three `fix:` bullets, one per defect, plus one `docs:` bullet for the documentation. Do not add a `feat:` bullet — this spec repairs an instrument that was already shipped and adds no new capability. Do not use the `- bench: ` style.

AC16 checks the section mechanically. Three patterns are applied to it with `grep -n`:

- `plugin|load path`
- `branch|ref`
- `stdout`

and the **union of matched line numbers must be exactly three distinct values**, with at least three `- ` bullets in the section. That means each of the three `fix:` bullets carries exactly one of the three topics and the `docs:` bullet carries **none** of them. `grep -iE 'branch|ref'` matches the substring `ref` inside ordinary words — **`preflight`, `reference`, `prefix`, `refuse`, `refusing`, `refresh`, `refactor` and `prefer` all contain it.** Avoid every one of them outside the branch bullet. Write "start-up check" rather than "preflight", "aborts" rather than "refuses".

Wording that satisfies the checks and describes the change (adjust freely, then re-run the union check below):

```markdown
## Unreleased

- fix: bench runner — the start-up check now hashes the directory Claude Code actually loads the coding plugin from, taken from the isolated config directory's install record, and aborts the whole run by name when no record exists, when it cannot be parsed, when it names a directory missing on disk, when it points outside that config directory's own cache tree, or when it applies only to a different working directory; a passing check prints the resolved directory, the recorded version and the content hash
- fix: bench runner — the working copy handed to the review now carries exactly the checked-out head branch and the two synthetic remote-tracking branches for that pull request, with every upstream branch, every tag and the default-branch pointer removed on every run, so identical inputs stop producing a clarifying question instead of a review
- fix: bench runner — a failed review now preserves both of the subprocess's output streams in one labelled artifact under `bench/.cache/failures/`, with an empty stream marked empty, because Claude Code writes its real errors to stdout while stderr carries incidental warnings and the discarded half once caused a wrong diagnosis
- docs: bench — document the authentication variable an operator must export before a run and why the runner deliberately does not set it, the install-record shape the start-up check reads together with the conditions that abort a run, and the two-name guarantee for the working copy handed to the review, in `bench/README.md`
```

Verify the union before you finish, and iterate on the wording until it prints exactly three distinct line numbers:

```bash
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md > /tmp/unreleased.txt
grep -c '^- ' /tmp/unreleased.txt                                   # expect >= 3
grep -cE '^- (fix|feat|docs): ' /tmp/unreleased.txt                 # expect == the bullet count
grep -c '^- bench: ' /tmp/unreleased.txt                            # expect 0
{ grep -niE 'plugin|load path' /tmp/unreleased.txt; \
  grep -niE 'branch|ref' /tmp/unreleased.txt; \
  grep -niE 'stdout' /tmp/unreleased.txt; } | cut -d: -f1 | sort -u  # expect exactly 3 lines
```

## 4. Final sweep

Run these and fix anything they surface. They are checks, not licence to refactor:

- `grep -rn '/Users/\|~/Documents/' bench/` returns no lines (exit 1). This includes the README, the fixtures and every test file.
- Every `import` / `from` line in `bench/run.py`, `bench/testsupport.py` and every `bench/test_*.py` names a Python 3 standard-library module only. No third-party imports, no `requirements.txt`, no `pyproject.toml`, no `setup.py`, no packaging of any kind.
- `python3 -m unittest discover -s bench -p 'test_*.py'` reports `OK` with `Ran N tests`, **`N > 55`** (AC1).
- `make precommit` exits 0.

If one of these fails for a reason introduced by prompt 1, 2 or 3, fix it here rather than leaving the spec unshippable, and say so in the completion report.

## 5. Do not modify

`bench/run.py` behaviour (this is a documentation prompt — change it only if the sweep in requirement 4 surfaces a genuine defect, and say so in the report), `bench/prs.json`, `bench/testdata/`, `bench/test_*.py`, `bench/testsupport.py`, `Makefile`, `commands/`, `rules/`, `agents/`, `docs/`, `scripts/`, `specs/`, `.claude-plugin/`.

Do not add a scenario file. The spec's **Scenario coverage** section is explicit: all three defect classes are unit-testable at the boundary the current tests stub away, and the remaining evidence (AC17–AC21) needs real tokens against a live review, which no scenario harness can supply.
</requirements>

<constraints>
- Python 3 standard library only — no third-party dependencies anywhere in `bench/`
- Changes land only in `bench/README.md` and `CHANGELOG.md` (plus any fix requirement 4 genuinely forces)
- The existing tests keep passing and their assertions are not weakened. The suite's test count is strictly greater than 55
- `make precommit` (which runs `bench-test`) stays green. Bench tests must not require network access, a real `claude` binary, or GitHub access
- **Do NOT make `review_env()` supply an authentication token.** Any value of `ANTHROPIC_AUTH_TOKEN` switches Claude Code into API-key mode and bypasses the OAuth path entirely, for every operator including those whose OAuth works. The README documents the `export`; the runner never performs it
- No credential material is read, logged, written or quoted. The README names the variable only — never a value, never an example value, never a placeholder that looks like one
- Frozen invariants — document them as fixed, never as configurable: the isolated config directory `$HOME/.claude-verify`; the 45-minute review timeout; the cache, results and failure-artifact locations; the three required section names; the `--golden` exit-2 rejection. Do not document a knob that does not exist
- Do NOT change the harvest contract or the non-review sanity gate shipped in v0.35.2, and do not rewrite the `## Reading review output` section that documents them
- Do NOT add a field to the result row (no plugin version, no load path) — the content hash already pins what ran, and the result-row table in the README must keep matching `build_row`
- `bench/prs.json` remains a frozen input — schema, entries and `dev-1` version unchanged
- No rule, agent, command or doc that participates in a review may be edited, including `commands/pr-review.md`. This spec repairs the instrument, never the measured configuration
- Every git invocation still targets a path under `bench/.cache/repos/` — the safety invariant from spec 002 is unchanged and the README's `## Safety invariant` section stays true
- Generic examples only — no trading-domain content (`CLAUDE.md`)
- No personal paths (`/Users/`, `~/Documents/`) in any shipped file including the README (`docs/dod.md`)
- CHANGELOG entries use conventional prefixes (`fix:` / `feat:` / `docs:`) per `docs/changelog-guide.md`; the `bench:` style of v0.35.1 is not repeated, because dark-factory's version-bump detector reads the prefix. The `## Unreleased` section describes the whole change — all three defects — not this prompt's slice
- The frozen CHANGELOG header is not moved, deleted, or written into; `## Unreleased` goes immediately after it
- The 4-version alignment is NOT touched — releases are manual (`docs/dod.md`)
- Do NOT re-harvest, migrate or re-validate anything already under `bench/.cache/` or `bench/results/` — rows recorded before this change carry an unproven hash, and the recovery the README states is to delete the cache and re-run
- Do NOT add a scenario file
- Do NOT commit — dark-factory handles git
</constraints>

<verification>
```
# Prompts 1-3 landed (precondition, not a new check)
grep -n 'def resolve_plugin_load_path\|def prune_refs\|def write_failure_artifact\|def resolution_line' bench/run.py

# AC14 — the five README patterns, each present
grep -c 'ANTHROPIC_AUTH_TOKEN' bench/README.md          # expect >= 1
grep -ciE 'API.key mode|does not set it' bench/README.md # expect >= 1
grep -ciE 'installed_plugins|install record' bench/README.md # expect >= 1
grep -ciE 'plugins/cache' bench/README.md                # expect >= 1
grep -ciE 'bench-base-|two synthetic' bench/README.md    # expect >= 1

# AC14 anti-keyword-stuffing — the five patterns match on >= 4 distinct lines
{ grep -n 'ANTHROPIC_AUTH_TOKEN' bench/README.md; \
  grep -niE 'API.key mode|does not set it' bench/README.md; \
  grep -niE 'installed_plugins|install record' bench/README.md; \
  grep -niE 'plugins/cache' bench/README.md; \
  grep -niE 'bench-base-|two synthetic' bench/README.md; } | cut -d: -f1 | sort -u | tee /tmp/readme-lines.txt | wc -l   # expect >= 4

# AC14 — each topic is its own heading with >= 3 non-empty lines under it
grep -n '^## ' bench/README.md

# AC16 — the Unreleased section, its prefixes and its bullet count
sed -n '/^## Unreleased/,/^## v/p' CHANGELOG.md | tee /tmp/unreleased.txt
test -s /tmp/unreleased.txt && echo "unreleased section non-empty"
grep -c '^- ' /tmp/unreleased.txt                            # expect >= 3
grep -c '^- bench: ' /tmp/unreleased.txt                     # expect 0
grep -vE '^(## |$)' /tmp/unreleased.txt | grep -cvE '^- (fix|feat|docs): ' ; echo "non-conforming bullet count above (expect 0)"
grep -ciE 'plugin|load path' /tmp/unreleased.txt             # expect >= 1
grep -ciE 'branch|ref' /tmp/unreleased.txt                   # expect >= 1
grep -ciE 'stdout' /tmp/unreleased.txt                       # expect >= 1

# AC16 anti-keyword-stuffing — exactly three distinct bullet lines carry the three topics
{ grep -niE 'plugin|load path' /tmp/unreleased.txt; \
  grep -niE 'branch|ref' /tmp/unreleased.txt; \
  grep -niE 'stdout' /tmp/unreleased.txt; } | cut -d: -f1 | sort -u | tee /tmp/topic-lines.txt | wc -l   # expect exactly 3

# The frozen CHANGELOG header was not disturbed
head -12 CHANGELOG.md
grep -n '^## ' CHANGELOG.md | head -3   # expect '## Unreleased' first, then '## v0.35.2'

# The 4-version alignment is untouched
grep -rn '"version"' .claude-plugin/plugin.json .claude-plugin/marketplace.json

# AC15 — no personal paths, stdlib-only imports, no packaging
grep -rn '/Users/\|~/Documents/' bench/ ; echo "personal-path grep exit=$?  (expect 1)"
grep -nE '^(import |from )' bench/run.py bench/testsupport.py bench/test_*.py
ls bench/ ; test ! -e requirements.txt && test ! -e pyproject.toml && test ! -e setup.py && echo "no packaging files"

# AC1 — the suite grew and is green
python3 -m unittest discover -s bench -p 'test_*.py' -v 2>&1 | tail -30
python3 -m unittest discover -s bench -p 'test_*.py' 2>&1 | grep -E '^Ran |^OK|^FAILED'

# The README's documented facts match the code it documents
python3 -c "
import sys, pathlib; sys.path.insert(0, 'bench')
import run
readme = (pathlib.Path('bench') / 'README.md').read_text(encoding='utf-8')
for name in ('plugins/cache', 'installed_plugins.json', 'bench-base-'):
    assert name in readme, name
assert 'ANTHROPIC_AUTH_TOKEN' in readme
# the runner still supplies no token
import inspect
src = inspect.getsource(run.review_env)
assert 'ANTHROPIC_AUTH_TOKEN' not in src, src
assert 'CLAUDE_CONFIG_DIR' in src and 'DISABLE_AUTOUPDATER' in src
print('OK')
"

# Reserved and mandatory flags unchanged
python3 bench/run.py --golden bench/golden.json ; echo "golden exit=$?  (expect 2)"
python3 bench/run.py ; echo "no-flags exit=$?  (expect 2)"

# Repo gate
make precommit
```

Expected: `make precommit` exits 0; all five README greps return at least 1 and the distinct-line count is at least 4; the extracted Unreleased section is non-empty, has at least three bullets, zero `- bench: ` bullets, zero non-conforming bullets, and the topic-line union is exactly 3; `## Unreleased` is the first `## ` heading in `CHANGELOG.md` and `## v0.35.2` the second; the personal-path grep exits 1 with no output; every import line names a stdlib module and no packaging file exists; the unittest run prints `OK` with `Ran N tests`, `N > 55`; the inline Python prints `OK`; both `run.py` invocations exit 2.

Operator-executed after merge, in the spec-verification phase (real tokens, live review command, not runnable here): **AC17** (the resolution line in a real `make bench` run names a directory that exists, whose version segment equals the recorded version, and `diff -r` against `--coding-repo`'s `rules/` and `commands/` reports no differences), **AC18** (three consecutive one-PR runs, each `0 failed`, no raw output containing "which should I use" or "target branch options"), **AC19** (`git branch -a` in a live prepared working copy printing exactly three lines), **AC20** (an induced failure whose artifact carries the real cause under the stdout label) and **AC21** (the full five-PR fixture unregressed: five rows, `tts-mcp#20` at 0 findings, one distinct `rules_commands_hash`).
</verification>
