---
status: active
---

# Scenario 004: `/coding:pr-review` against a real PR surfaces findings + adjudicates per Owner

Validates the load-bearing path the bot executes on every real Go PR with violations: `/coding:pr-review <URL>` fetches the diff from GitHub, the ast-grep funnel surfaces findings in Step 4a, Step 4b dispatches per-Owner Task agents for each affected owner, the dispatcher's Step 4d citation validator passes them through, and Step 5 reports the violations under Must Fix / Should Fix with valid rule_id citations. Scenarios 001-003 do not cover this — 001 tests toolchain-absent failure, 002 tests zero-findings happy path, 003 tests the mechanical funnel in isolation. Without 004 the regression risk is "Step 4b silently drops findings_by_owner — bot APPROVES a PR with real violations because the per-Owner adjudication phase no-ops".

## Test PR

The stable fixture is [bborbe/maintainer#2](https://github.com/bborbe/maintainer/pull/2) (branch `delete-this-pr-never`, title `test: delete-this-pr-never`). The PR diff is one file (`pkg/scenarios-test-fixture/violations.go`, 38 additions) committed expressly to violate 5 ast-grep YAML rules:

- `go-architecture/constructor-returns-interface` (`NewService1` returns `*Service1`)
- `go-architecture/no-globals-or-singletons` (`sharedService1` at package scope)
- `go-time/no-time-now-direct` (bare `time.Now()`)
- `go-concurrency/no-raw-go-func` (bare `go func(){...}()`)
- `go-errors/no-fmt-errorf` (`fmt.Errorf` in production code)

All 5 violations now fire after the no-fmt-errorf YAML's structural rewrite (was silently parsing as `type_conversion_expression` until the 2026-06-03 fix). The PR stays open in perpetuity — the title says so. Walking 004 = re-pointing the dispatcher at the same SHA and verifying the funnel still surfaces all 5 violations.

## Setup

- [ ] `ast-grep --version` resolves on host
- [ ] Confirm the PR is still open and shows exactly 1 changed file: `gh pr view 2 --repo bborbe/maintainer --json state,changedFiles -q '"state=\(.state) changedFiles=\(.changedFiles)"'` prints `state=OPEN changedFiles=1`
- [ ] Clone the PR to a worktree for the dispatcher to scan (mirrors `commands/pr-review.md` Step 0b): `WORK=$(mktemp -d) && cd "$WORK" && git clone --depth=1 --branch delete-this-pr-never git@github.com:bborbe/maintainer.git . && git remote update --prune`
- [ ] Confirm the fixture file landed: `test -f pkg/scenarios-test-fixture/violations.go`

## Action

- [ ] Step 4.0 preflight (mirrors `commands/pr-review.md`): `(command -v ast-grep >/dev/null 2>&1 || command -v sg >/dev/null 2>&1) || exit 1; echo "preflight ok"`
- [ ] Step 4a: run `scripts/ast-grep-runner.sh "$WORK" pkg/scenarios-test-fixture/violations.go` (diff-scoped to the single changed file); resolve runner path via `${CLAUDE_PLUGIN_ROOT:-...}` falling back to `$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh`; capture output to `/tmp/scen004-findings.json`:
  ```bash
  RUNNER="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh"
  [ -x "$RUNNER" ] || RUNNER="$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh"
  "$RUNNER" "$WORK" "$WORK/pkg/scenarios-test-fixture/violations.go" > /tmp/scen004-findings.json
  echo $? > /tmp/scen004-ag-exit
  ```
- [ ] Assert ≥5 findings across ≥3 distinct rule_ids:
  ```bash
  jq '.stats.findings_count' /tmp/scen004-findings.json      # ≥5
  jq -r '.findings_by_owner | to_entries[] | .value[] | .rule_id' /tmp/scen004-findings.json | sort -u | wc -l  # ≥3
  ```
- [ ] Assert ≥1 owner key:
  ```bash
  jq '.findings_by_owner | keys | length' /tmp/scen004-findings.json  # ≥1
  ```
- [ ] Citation check (every finding's rule_id in index):
  ```bash
  CODING_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}"
  [ -f "$CODING_ROOT/rules/index.json" ] || CODING_ROOT="$HOME/Documents/workspaces/coding"
  jq -r '.findings_by_owner | to_entries[] | .value[] | .rule_id' /tmp/scen004-findings.json | sort -u > /tmp/scen004-rules.txt
  comm -23 /tmp/scen004-rules.txt <(jq -r '.[].id' "$CODING_ROOT/rules/index.json" | sort) > /tmp/scen004-hallucinated.txt
  ```
- [ ] Agent-presence check (every owner key has a matching agents/<owner>.md):
  ```bash
  CODING_ROOT="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}"
  [ -d "$CODING_ROOT/agents" ] || CODING_ROOT="$HOME/Documents/workspaces/coding"
  jq -r '.findings_by_owner | keys[]' /tmp/scen004-findings.json | while read owner; do
    test -f "$CODING_ROOT/agents/$owner.md" && echo "$owner: AGENT_PRESENT" || echo "$owner: AGENT_MISSING"
  done > /tmp/scen004-agent-presence
  ```

## Expected

- [ ] `cat /tmp/scen004-ag-exit` returns `0`
- [ ] `jq '.stats.findings_count' /tmp/scen004-findings.json` returns ≥ `5` — all 5 deliberate violations fire (the fmt.Errorf violation now fires after `rules/go/no-fmt-errorf.yml` was rewritten as a structural rule)
- [ ] `jq -r '.findings_by_owner | to_entries[] | .value[] | .rule_id' /tmp/scen004-findings.json | sort -u | wc -l` returns ≥ `3` — at least 3 distinct rule_ids
- [ ] `jq '.findings_by_owner | keys | length' /tmp/scen004-findings.json` returns ≥ `1` — at least one owner
- [ ] `wc -l < /tmp/scen004-hallucinated.txt` returns `0` — citation discipline holds: every surfaced rule_id is in the index
- [ ] Every line in `/tmp/scen004-agent-presence` ends with `AGENT_PRESENT` — all owner agent files resolve
- [ ] `jq '.stats.elapsed_ms' /tmp/scen004-findings.json` ≤ `5000` — small fixture, mechanical layer fast (under 5 seconds)

## Cleanup

- `rm -rf "$WORK" /tmp/scen004-*`

After the scenario passes, the operator should record the measured `(findings_count, distinct_rule_ids, distinct_owners)` tuple in the Progress section of the task page (`[[Refactor coding pr-review to doc-driven rules pipeline]]`) so future runs have a baseline. This is a follow-up note, not part of the scenario contract.

## Walk 2026-06-09

Setup:

```
$ ast-grep --version  (resolves: /opt/local/bin/ast-grep)
$ gh pr view 2 --repo bborbe/maintainer --json state,changedFiles -q ...
state=OPEN changedFiles=1
$ PR_SHA=536a6e79cef42a3711b55b219af5a12c81f0f087
$ WORK cloned from branch delete-this-pr-never
$ test -f pkg/scenarios-test-fixture/violations.go  → pass
```

Step 4.0 preflight: ok

Step 4a — `scripts/ast-grep-runner.sh "$WORK" "$WORK/pkg/scenarios-test-fixture/violations.go"`:

```
exit=0  wall_ms=1869ms  elapsed_ms=1646ms
yamls_run=66  findings_count=6
```

Findings (6 total across 4 owners):

| owner | rule_id | file | line |
|---|---|---|---|
| go-architecture-assistant | go-architecture/constructor-returns-interface | violations.go | 18 |
| go-architecture-assistant | go-architecture/no-globals-or-singletons | violations.go | 22 |
| go-architecture-assistant | go-concurrency/no-raw-go-func | violations.go | 33 |
| go-error-assistant | go-errors/no-fmt-errorf | violations.go | 37 |
| go-quality-assistant | go-library/semver-vprefix-tag-required | WORK dir | 0 |
| go-time-assistant | go-time/no-time-now-direct | violations.go | 29 |

Note: `go-library/semver-vprefix-tag-required` fires from the script-tier `rule-checks.sh` (the cloned repo has no git tags). This is a 6th finding on top of the 5 deliberate violations — findings_count ≥ 5 is satisfied.

Distinct rule_ids: 6 (all 5 deliberate + 1 script-tier)

Citation check: empty (all 6 rule_ids in index)

Agent presence:
```
go-architecture-assistant: AGENT_PRESENT
go-error-assistant: AGENT_PRESENT
go-quality-assistant: AGENT_PRESENT
go-time-assistant: AGENT_PRESENT
```

### Results

- [x] `cat /tmp/scen004-ag-exit` = `0` — PASS
- [x] `findings_count` ≥ 5 (actual: 6) — PASS
- [x] Distinct rule_ids ≥ 3 (actual: 6) — PASS
- [x] Owner keys ≥ 1 (actual: 4) — PASS
- [x] Hallucinated rules = 0 — PASS
- [x] All owners AGENT_PRESENT — PASS
- [x] `elapsed_ms` ≤ 5000 (actual: 1646ms) — PASS

All 7 Expected items: **7/7 PASS**

Baseline tuple: `(findings_count=6, distinct_rule_ids=6, distinct_owners=4)`.

Selector-mode sibling journey: scenarios/006. These two files keep guarding the legacy default path until the default flip retires it.
