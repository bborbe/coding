---
status: active
---

# Scenario 003: 100-file synthetic PR funnel converges to ≤30 distinct owners

Validates that the ast-grep mechanical funnel against a 100-file synthetic PR with mixed violations completes in ≤30 seconds and surfaces findings under ≤30 distinct Owner agents — proving the funnel decouples LLM-tier cost from file count (since the dispatcher's Step 4b invokes ONE Task per Owner with findings, the upper bound on LLM calls is the distinct-Owner count plus a small fixed overhead). The full-pipeline LLM-call measurement (Phase 10 acceptance, requires an LLM-shim wrapping the `claude` binary) is deferred to a future scenario 004 — not yet written; this scenario captures the structural ceiling.

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
- [ ] Runner is available: resolve path via `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh`, falling back to `$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh`

## Action

- [ ] Run `scripts/ast-grep-runner.sh "$WORK"` (full scan — all 100 files):
  ```bash
  RUNNER="${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh"
  [ -x "$RUNNER" ] || RUNNER="$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh"
  start=$(date +%s%N); "$RUNNER" "$WORK" > /tmp/scen003-full.json; end=$(date +%s%N)
  echo "full wall_ms=$(( (end - start) / 1000000 ))"
  ```
- [ ] Run diff-scope variant: re-run with only 10 of the 100 files as changed-file args:
  ```bash
  # Pick 10 files deterministically
  FILES_10=(); while IFS= read -r f; do FILES_10+=("$f"); done < <(find "$WORK" -name "*.go" | sort | head -10)
  start=$(date +%s%N); "$RUNNER" "$WORK" "${FILES_10[@]}" > /tmp/scen003-diff.json; end=$(date +%s%N)
  echo "diff wall_ms=$(( (end - start) / 1000000 ))"
  ```
- [ ] Assert diff-scope restricts findings to those 10 files via jq:
  ```bash
  jq -r '.findings_by_owner | to_entries[] | .value[] | select(.file | endswith(".go")) | .file' \
    /tmp/scen003-diff.json | sort -u > /tmp/scen003-diff-gofiles.txt
  # Every path must be one of the FILES_10
  ```

## Expected

- [ ] `jq '.stats.elapsed_ms' /tmp/scen003-full.json` ≤ `30000` (mechanical funnel completes in ≤30 seconds — distinct from wall_ms which includes jq subprocess overhead)
- [ ] `jq '.findings_by_owner | keys | length' /tmp/scen003-full.json` returns a number ≤ `30` (structural upper bound on Step 4b LLM calls: one Task per owner with findings)
- [ ] `jq '.stats.findings_count' /tmp/scen003-full.json` > `0` — negative control: the synthetic violations were actually surfaced
- [ ] `jq -r '.findings_by_owner | to_entries[] | .value[] | .rule_id' /tmp/scen003-full.json | sort -u | wc -l` returns ≥ `3` — at least 3 distinct rule_ids surfaced (proves the fixture exercises multiple mechanical patterns)
- [ ] Citation check: `comm -23 <(jq -r '.findings_by_owner | to_entries[] | .value[] | .rule_id' /tmp/scen003-full.json | sort -u) <(jq -r '.[].id' $CODING_ROOT/rules/index.json | sort)` is empty — every surfaced rule_id is in the index
- [ ] Diff-scoped: `jq '.stats.findings_count' /tmp/scen003-diff.json` < full scan `findings_count` — scoping to 10 files reduces finding count
- [ ] Diff-scoped: all `.go` file paths in `/tmp/scen003-diff-gofiles.txt` are members of `FILES_10` — scope restriction holds

## Cleanup

- `rm -rf "$WORK" /tmp/scen003-*`

After the scenario passes, the operator should record the measured `(wall_ms, distinct_owners, findings_count)` tuple in the Progress section of the task page (`[[Refactor coding pr-review to doc-driven rules pipeline]]`) so future runs have a baseline. This is a follow-up note, not part of the scenario contract.

## Walk 2026-06-09

Setup confirmed:

```
$ git ls-files '*.go' | wc -l
100
$ ast-grep --version  (resolves: /opt/local/bin/ast-grep)
```

Full scan (`scripts/ast-grep-runner.sh "$WORK"`):

```
exit=0  wall_ms=5212
yamls_run=66  findings_count=117  elapsed_ms=4948
distinct_owners=4
```

Owners: `go-architecture-assistant`, `go-quality-assistant`, `go-time-assistant`, `license-assistant`

Distinct rule_ids (6):
```
go-architecture/constructor-returns-interface
go-architecture/no-globals-or-singletons
go-concurrency/no-raw-go-func
go-library/semver-vprefix-tag-required
go-licensing/license-file-required
go-time/no-time-now-direct
```

Citation check (comm output): empty — all 6 rule_ids in index.

Diff-scoped scan (10 files — `pkg/h/a/file1-5.go` + `pkg/h/b/file1-5.go`):

```
exit=0  wall_ms=2061
yamls_run=66  findings_count=12  elapsed_ms=1845
distinct_owners=3
```

Scope restriction verified: all Go-file findings point exclusively to the 10 scanned files (pkg/h/a/* and pkg/h/b/*). Script-tier findings (license, semver) point to WORK dir root — these are always-run checks that are not file-scoped.

### Results

- [x] `elapsed_ms` ≤ 30000 (full scan: 4948 ms) — PASS
- [x] Distinct owners ≤ 30 (full: 4 owners) — PASS
- [x] `findings_count` > 0 (full: 117) — PASS
- [x] Distinct rule_ids ≥ 3 (full: 6) — PASS
- [x] Citation check: empty (all 6 rule_ids in index) — PASS
- [x] Diff-scoped findings_count < full (12 < 117) — PASS
- [x] Diff-scoped Go-file paths restricted to the 10 scanned files — PASS

All 7 Expected items: **7/7 PASS**

Baseline tuple: `(wall_ms=5212, elapsed_ms=4948, distinct_owners=4, findings_count=117)` (full scan); diff-scoped 10 files: `(elapsed_ms=1845, findings_count=12)`.
