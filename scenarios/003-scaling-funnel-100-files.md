---
status: active
---

# Scenario 003: 100-file synthetic PR funnel converges to ≤30 distinct owners

Validates that the ast-grep mechanical funnel against a 100-file synthetic PR with mixed violations completes in ≤30 seconds and surfaces findings under ≤30 distinct Owner agents — proving the funnel decouples LLM-tier cost from file count (since the dispatcher's Step 4b invokes ONE Task per Owner with findings, the upper bound on LLM calls is the distinct-Owner count plus a small fixed overhead). The full-pipeline LLM-call measurement (Phase 10 acceptance) lives in [companion scenario 004](004-funnel-decoupling-doubled-fixture.md) — that one requires a real `/coding:pr-review` invocation; this one measures the mechanical-layer ceiling structurally.

## Setup

- [ ] Build the synthetic-PR fixture (100 .go files across realistic package layout, 4 distinct mechanical-rule violation types):
  ```bash
  WORK=$(mktemp -d) && cd "$WORK" && git init -q
  i=0
  # Layer A: constructor-returns-interface (40 files)
  for dir in pkg/h/{a,b,c,d} pkg/s/{a,b,c,d}; do
    mkdir -p $dir
    for n in 1 2 3 4 5; do
      i=$((i+1)); pkg=$(basename $dir)
      printf 'package %s\ntype Service%d struct{}\nfunc NewService%d() *Service%d { return &Service%d{} }\n' "$pkg" $i $i $i $i > "$dir/file$n.go"
    done
  done
  # Layer B: no-raw-go-func (30 files)
  for dir in pkg/w/{a,b,c}; do
    mkdir -p $dir
    for n in 1 2 3 4 5 6 7 8 9 10; do
      i=$((i+1)); pkg=$(basename $dir)
      printf 'package %s\nfunc Run%d() {\n\tgo func() { _ = 1 }()\n}\n' "$pkg" $i > "$dir/file$n.go"
    done
  done
  # Layer C: no-globals-or-singletons (15 files)
  for dir in pkg/r/{a,b,c}; do
    mkdir -p $dir
    for n in 1 2 3 4 5; do
      i=$((i+1)); pkg=$(basename $dir)
      printf 'package %s\ntype Service%d struct{}\nfunc NewService%d() *Service%d { return &Service%d{} }\nvar sharedService%d = NewService%d()\nvar _ = sharedService%d\n' "$pkg" $i $i $i $i $i $i $i > "$dir/file$n.go"
    done
  done
  # Layer D: no-time-now-direct (15 files)
  for dir in pkg/i/{a,b,c}; do
    mkdir -p $dir
    for n in 1 2 3 4 5; do
      i=$((i+1)); pkg=$(basename $dir)
      printf 'package %s\nimport "time"\nfunc Now%d() time.Time { return time.Now() }\n' "$pkg" $i > "$dir/file$n.go"
    done
  done
  git add . && git commit -qm initial
  ```
- [ ] `git ls-files '*.go' | wc -l` returns exactly `100`
- [ ] `ast-grep --version` resolves on host

## Action

- [ ] Run the mechanical funnel — `ast-grep scan` from inside the coding project root, against the fixture: `cd ~/Documents/workspaces/coding && start=$(date +%s%N); ast-grep scan "$WORK" > /tmp/scen003-findings.log 2>&1; exit=$?; end=$(date +%s%N); echo "wall_ms=$(( (end - start) / 1000000 ))" > /tmp/scen003-wall; echo "exit=$exit" > /tmp/scen003-exit`
- [ ] Extract distinct rule_ids from findings: `grep -oE 'go-[a-z-]+/[a-z-]+' /tmp/scen003-findings.log | sort -u > /tmp/scen003-rules`
- [ ] Look up distinct Owner agents by intersecting rule_ids with `rules/index.json`: `python3 -c "import json; idx={r['id']:r['owner'] for r in json.load(open('rules/index.json'))}; rules=open('/tmp/scen003-rules').read().splitlines(); owners=set(idx.get(r) for r in rules if r in idx); print('\\n'.join(sorted(owners)))" > /tmp/scen003-owners`
- [ ] Count findings: `grep -c '^error\[' /tmp/scen003-findings.log > /tmp/scen003-findings-count`

## Expected

- [ ] `cat /tmp/scen003-wall` reports `wall_ms` ≤ `30000` (mechanical funnel completes in ≤30 seconds)
- [ ] `wc -l < /tmp/scen003-owners` returns a number ≤ `30` (structural upper bound on Step 4b LLM calls: one Task per owner with findings)
- [ ] `cat /tmp/scen003-findings-count` > `0` — negative control: the synthetic violations were actually surfaced (if 0, the funnel didn't run, owner count is misleadingly low)
- [ ] `wc -l < /tmp/scen003-rules` returns ≥ `3` — at least 3 distinct rule_ids surfaced (proves the fixture exercises multiple mechanical patterns, not a single rule)
- [ ] Every rule_id in `/tmp/scen003-rules` appears as an `id` in `rules/index.json` (citation discipline at funnel exit): `comm -23 /tmp/scen003-rules <(jq -r '.[].id' rules/index.json | sort)` is empty

## Cleanup

- `rm -rf "$WORK" /tmp/scen003-*`

After the scenario passes, the operator should record the measured `(wall_ms, distinct_owners, findings_count)` tuple in the Progress section of the task page (`[[Refactor coding pr-review to doc-driven rules pipeline]]`) so future runs have a baseline. This is a follow-up note, not part of the scenario contract.
