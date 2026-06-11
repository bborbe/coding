---
status: active
---

# Scenario 005: Selector mode short-circuits cleanly on a README-only whitespace diff

Validates that `/coding:code-review master selector` (in-place review — works on a local-only branch, mirroring scenario 002) against a branch whose diff is a single README.md whitespace edit emits `selector clean — no adjudication needed`, produces a report with empty Must Fix / Should Fix / Nice to Have sections, and spawns zero sub-agents — locking down the regression risk that the classify step incorrectly marks any rule as applicable when no rule-relevant files changed.

## Setup

- [ ] Clone master at the current HEAD: `WORK=$(mktemp -d) && cd "$WORK" && git clone --depth=1 --branch master git@github.com:bborbe/coding.git . && git checkout -b selector-clean-fixture`
- [ ] Apply a README-only whitespace edit (no `.go` / `.py` / `rules/**` / `docs/**` touched): `sed -i.bak 's/^# bborbe\/coding$/# bborbe\/coding  /' README.md && rm README.md.bak && git add README.md && git commit -qm 'docs: whitespace typo'`
- [ ] `git diff --name-only master..HEAD` prints exactly one line: `README.md`
- [ ] `ast-grep --version` resolves on host (Step 4.0 preflight will pass)

## Action

- [ ] Run `/coding:code-review master selector` in `$WORK` (in-place; the fixture branch is local-only, which `/coding:pr-review`'s worktree flow does not support — that journey is scenario 006's) in a fresh Claude Code session; tee stdout to `/tmp/scen005-stdout.log`, stderr to `/tmp/scen005-stderr.log`, capture exit code to `/tmp/scen005-exit`

## Expected

- [ ] `cat /tmp/scen005-exit` prints `0`
- [ ] Guide resolution prints `GUIDE_OK` (not `GUIDE_MISSING`) — verify via: `grep -c 'GUIDE_OK' /tmp/scen005-stdout.log` ≥ 1
- [ ] Stdout contains the literal string `selector clean — no adjudication needed` — the Step 4c-sel short-circuit fires because no candidate rule is applicable to a README-only diff: `grep -c 'selector clean — no adjudication needed' /tmp/scen005-stdout.log` ≥ 1
- [ ] Traceability section is present in the report with a candidate count ≥ 0: `grep -c 'Candidates:' /tmp/scen005-stdout.log` ≥ 1; every line in the Skipped subsection carries a one-line reason (≤ 8 words) for each candidate that was evaluated
- [ ] Zero `coding:*` sub-agent spawns: `grep '"subagent_type"' /tmp/scen005-stdout.log` returns no lines, OR the session's stream-json transcript has no `tool_use` blocks whose `subagent_type` field starts with `coding:`
- [ ] Zero findings reported: either all three severity sections (`Must Fix` / `Should Fix` / `Nice to Have`) read `None.`, or the report carries an explicit funnel-clean/selector-clean statement with no finding entries (observable outcome over exact formatting; M2.7 walk 2026-06-11 used the latter form)
- [ ] Report includes `Should Fix (Important)` section with body `None.`
- [ ] Report includes `Nice to Have (Optional)` section with body `None.`
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen005-*`

---

**Status**: walked 2026-06-11 (MiniMax-M2.7-highspeed via `CLAUDE_CONFIG_DIR=~/.claude-verify`, skill @ f93717e): 1m29s, 17 turns, zero `coding:*` spawns, GUIDE_OK ×2 in stream, classify table with per-candidate `applies_when` + reasons, 5 candidates → 0 applicable → 5 skipped, literal `selector clean — no adjudication needed` fired. Transcript: `/tmp/scen005-walk2.jsonl` (volatile; key numbers recorded here). Promoted draft → active. Note: original draft used `/coding:pr-review` — switched to `/coding:code-review` (in-place) because the fixture branch is local-only; pr-review's worktree flow needs an origin branch (that journey is scenario 006's).
