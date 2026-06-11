---
status: draft
---

# Scenario 005: Selector mode short-circuits cleanly on a README-only whitespace diff

Validates that `/coding:pr-review master selector` against a branch whose diff is a single README.md whitespace edit emits `selector clean — no adjudication needed`, produces a report with empty Must Fix / Should Fix / Nice to Have sections, and spawns zero sub-agents — locking down the regression risk that the classify step incorrectly marks any rule as applicable when no rule-relevant files changed.

## Setup

- [ ] Clone master at the current HEAD: `WORK=$(mktemp -d) && cd "$WORK" && git clone --depth=1 --branch master git@github.com:bborbe/coding.git . && git checkout -b selector-clean-fixture`
- [ ] Apply a README-only whitespace edit (no `.go` / `.py` / `rules/**` / `docs/**` touched): `sed -i.bak 's/^# bborbe\/coding$/# bborbe\/coding  /' README.md && rm README.md.bak && git add README.md && git commit -qm 'docs: whitespace typo'`
- [ ] `git diff --name-only master..HEAD` prints exactly one line: `README.md`
- [ ] `ast-grep --version` resolves on host (Step 4.0 preflight will pass)

## Action

- [ ] Run `/coding:pr-review master selector` against `$WORK` in a fresh Claude Code session; tee stdout to `/tmp/scen005-stdout.log`, stderr to `/tmp/scen005-stderr.log`, capture exit code to `/tmp/scen005-exit`

## Expected

- [ ] `cat /tmp/scen005-exit` prints `0`
- [ ] Guide resolution prints `GUIDE_OK` (not `GUIDE_MISSING`) — verify via: `grep -c 'GUIDE_OK' /tmp/scen005-stdout.log` ≥ 1
- [ ] Stdout contains the literal string `selector clean — no adjudication needed` — the Step 4c-sel short-circuit fires because no candidate rule is applicable to a README-only diff: `grep -c 'selector clean — no adjudication needed' /tmp/scen005-stdout.log` ≥ 1
- [ ] Traceability section is present in the report with a candidate count ≥ 0: `grep -c 'Candidates:' /tmp/scen005-stdout.log` ≥ 1; every line in the Skipped subsection carries a one-line reason (≤ 8 words) for each candidate that was evaluated
- [ ] Zero `coding:*` sub-agent spawns: `grep '"subagent_type"' /tmp/scen005-stdout.log` returns no lines, OR the session's stream-json transcript has no `tool_use` blocks whose `subagent_type` field starts with `coding:`
- [ ] Report includes `Must Fix (Critical)` section with body `None.`
- [ ] Report includes `Should Fix (Important)` section with body `None.`
- [ ] Report includes `Nice to Have (Optional)` section with body `None.`
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen005-*`

---

Selector-mode sibling journey: scenarios/005 (resp. 006). These two files keep guarding the legacy default path until the default flip retires it.
