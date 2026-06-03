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
- [ ] Run `make build-index` in the coding repo root so the Owner-lookup in Action below reads a current index
- [ ] Fetch the PR head SHA: `PR_SHA=$(gh pr view 2 --repo bborbe/maintainer --json headRefOid -q .headRefOid)`; confirm non-empty
- [ ] Confirm the PR is still open and shows exactly 1 changed file: `gh pr view 2 --repo bborbe/maintainer --json state,changedFiles -q '"\(.state) changedFiles=\(.changedFiles)"'` prints `OPEN changedFiles=1`
- [ ] Clone the PR to a worktree for the dispatcher to scan (mirrors `commands/pr-review.md` Step 0b): `WORK=$(mktemp -d) && cd "$WORK" && git clone --depth=1 --branch delete-this-pr-never git@github.com:bborbe/maintainer.git . && git remote update --prune`
- [ ] Confirm the fixture file landed: `test -f pkg/scenarios-test-fixture/violations.go`

## Action

- [ ] Generate the PR diff scoped to the fixture file (mirrors `commands/pr-review.md` Step 0c): `git diff origin/master...HEAD -- pkg/scenarios-test-fixture/violations.go > /tmp/scen004-diff.patch; wc -l /tmp/scen004-diff.patch`
- [ ] Step 4.0 preflight (mirrors `commands/pr-review.md`): `(command -v ast-grep >/dev/null 2>&1 || command -v sg >/dev/null 2>&1) || exit 1; echo "preflight ok"`
- [ ] Step 4a mechanical funnel against the fixture: `cd ~/Documents/workspaces/coding && ast-grep scan "$WORK/pkg/scenarios-test-fixture" > /tmp/scen004-findings.log 2>&1; echo $? > /tmp/scen004-ag-exit`
- [ ] Step 4b owner extraction: `grep -oE 'go-[a-z-]+/[a-z-]+' /tmp/scen004-findings.log | sort -u > /tmp/scen004-rules && python3 -c "import json; idx={r['id']:r['owner'] for r in json.load(open('rules/index.json'))}; rules=open('/tmp/scen004-rules').read().splitlines(); owners=set(idx.get(r) for r in rules if r in idx and idx.get(r)); print('\\n'.join(sorted(owners)))" > /tmp/scen004-owners`
- [ ] Step 4b agent-presence check: `while read owner; do test -f "agents/$owner.md" && echo "$owner: AGENT_PRESENT" || echo "$owner: AGENT_MISSING"; done < /tmp/scen004-owners > /tmp/scen004-agent-presence`
- [ ] Step 4d citation validation (every surfaced rule_id must exist in the index): `comm -23 /tmp/scen004-rules <(jq -r '.[].id' rules/index.json | sort) > /tmp/scen004-hallucinated-rules`
- [ ] Count findings: `grep -c '^error\[' /tmp/scen004-findings.log > /tmp/scen004-findings-count`

## Expected

- [ ] `cat /tmp/scen004-findings-count` returns ≥ `5` — all 5 deliberate violations surface. The fmt.Errorf violation now fires after `rules/go/no-fmt-errorf.yml` was rewritten as a structural rule (`kind: call_expression` + selector match on `fmt.Errorf`) — the original `pattern: fmt.Errorf($$$ARGS)` was parsed as `type_conversion_expression` and matched nothing.
- [ ] `wc -l < /tmp/scen004-rules` returns ≥ `3` — multiple distinct rule_ids surfaced (negative control: if the fixture parses to zero, the funnel didn't run)
- [ ] `wc -l < /tmp/scen004-owners` returns ≥ `1` — at least one Owner has findings to adjudicate
- [ ] Every line in `/tmp/scen004-agent-presence` ends with `AGENT_PRESENT` — Step 4b can resolve every Owner's agent file (regression risk: a renamed agent file silently no-ops that owner's findings; this catches it)
- [ ] `wc -l < /tmp/scen004-hallucinated-rules` returns `0` — citation discipline holds: every surfaced rule_id is registered in the index
- [ ] Funnel wall-clock under 5 seconds — small fixture, mechanical layer fast

## Cleanup

- `rm -rf "$WORK" /tmp/scen004-*`

After the scenario passes, the operator should record the measured `(findings_count, distinct_rule_ids, distinct_owners)` tuple in the Progress section of the task page (`[[Refactor coding pr-review to doc-driven rules pipeline]]`) so future runs have a baseline. This is a follow-up note, not part of the scenario contract.
