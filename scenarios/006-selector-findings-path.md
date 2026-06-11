---
status: active
---

# Scenario 006: Selector mode surfaces all seeded violations on the perpetual fixture PR

Validates that `/coding:pr-review master selector` against `bborbe/maintainer#2` surfaces all 5 deliberate mechanical violations by name in the adjudication report, emits at least 1 judgment-tier finding beyond the mechanical 5, produces a traceability section with ≥ 1 skipped candidate carrying a reason, and spawns zero sub-agents — locking down the regression risk that selector mode silently drops owners or skips the adjudication step on a real multi-violation diff.

## Test PR

The stable fixture is [bborbe/maintainer#2](https://github.com/bborbe/maintainer/pull/2) (branch `delete-this-pr-never`, title `test: delete-this-pr-never`). The diff is one file (`pkg/scenarios-test-fixture/violations.go`, 38 additions) committed to violate 5 ast-grep YAML rules:

- `go-architecture/constructor-returns-interface`
- `go-architecture/no-globals-or-singletons`
- `go-time/no-time-now-direct`
- `go-concurrency/no-raw-go-func`
- `go-errors/no-fmt-errorf`

The PR stays open in perpetuity. The baseline for expected finding shape is `specs/fixtures/golden-legacy-verdict.json`.

## Setup

- [ ] `ast-grep --version` resolves on host
- [ ] Confirm the PR is still open and shows exactly 1 changed file: `gh pr view 2 --repo bborbe/maintainer --json state,changedFiles -q '"state=\(.state) changedFiles=\(.changedFiles)"'` prints `state=OPEN changedFiles=1`
- [ ] Clone the PR branch to a temporary worktree (mirrors `commands/pr-review.md` Step 0b): `WORK=$(mktemp -d) && cd "$WORK" && git clone --depth=1 --branch delete-this-pr-never git@github.com:bborbe/maintainer.git . && git remote update --prune`
- [ ] Confirm fixture file landed: `test -f pkg/scenarios-test-fixture/violations.go`

## Action

- [ ] Run `/coding:pr-review master selector` against `$WORK` in a fresh Claude Code session; tee stdout to `/tmp/scen006-stdout.log`, stderr to `/tmp/scen006-stderr.log`, capture exit code to `/tmp/scen006-exit`

## Expected

- [ ] `cat /tmp/scen006-exit` prints `0`
- [ ] Guide resolution prints `GUIDE_OK` (not `GUIDE_MISSING`): `grep -c 'GUIDE_OK' /tmp/scen006-stdout.log` ≥ 1
- [ ] All 5 seeded mechanical violations named in the report by rule_id — verify each is present in stdout:
  - `grep -c 'go-architecture/constructor-returns-interface' /tmp/scen006-stdout.log` ≥ 1
  - `grep -c 'go-architecture/no-globals-or-singletons' /tmp/scen006-stdout.log` ≥ 1
  - `grep -c 'go-time/no-time-now-direct' /tmp/scen006-stdout.log` ≥ 1
  - `grep -c 'go-concurrency/no-raw-go-func' /tmp/scen006-stdout.log` ≥ 1
  - `grep -c 'go-errors/no-fmt-errorf' /tmp/scen006-stdout.log` ≥ 1
- [ ] At least 1 judgment-tier finding beyond the mechanical 5 is reported (e.g. `go-licensing/source-file-header-required` per `specs/fixtures/golden-legacy-verdict.json`): total finding count in stdout > 5, or a non-mechanical rule_id appears in the report
- [ ] Traceability section present with candidates ≥ applicable: `grep -c 'Candidates:' /tmp/scen006-stdout.log` ≥ 1; at least 1 skipped candidate carries a one-line reason — `grep -c 'Skipped' /tmp/scen006-stdout.log` ≥ 1 (anti-no-op guard: a review that marks every candidate applicable would not satisfy this)
- [ ] Zero `coding:*` sub-agent spawns: `grep '"subagent_type"' /tmp/scen006-stdout.log` returns no lines, OR the session's stream-json transcript has no `tool_use` blocks whose `subagent_type` field starts with `coding:`
- [ ] Every finding's `rule_id` is present in `rules/index.json` (citation discipline holds): extract rule_ids from the report, cross-check against index — zero hallucinated rule_ids
- [ ] Run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen006-*`

---

**Status**: walked 2026-06-11 (MiniMax-M2.7-highspeed via `CLAUDE_CONFIG_DIR=~/.claude-verify`, branch `feature/selector-scenarios` @ f93717e): 3m21s, 30 turns, zero `coding:*` spawns, GUIDE_OK, all 5 seeded rule_ids + `go-licensing/source-file-header-required` (judgment tier) surfaced, traceability 31 candidates → 5 applicable → 26 skipped-with-reasons. Transcript: `/tmp/scen006-walk.jsonl` (volatile; key numbers recorded here). Promoted draft → active.
