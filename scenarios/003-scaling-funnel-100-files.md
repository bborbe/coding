---
status: draft
---

# Scenario 003: 100-file synthetic PR completes review in ≤30 LLM calls

Validates that a 100-file synthetic PR with known mechanical violations completes `/coding:pr-review master standard` within ≤30 LLM calls and ≤30 minutes — proving the ast-grep funnel decouples LLM cost from PR size and stays under the prod bot's `activeDeadlineSeconds=1800` ceiling. Companion decoupling scenario (200-file re-run with ≤30 LLM calls) lives separately as scenario 004.

## Setup

- [ ] Build the synthetic-PR fixture:
  ```bash
  WORK=$(mktemp -d) && cd "$WORK" && git init -q
  mkdir -p pkg/{handler,service,store,worker,internal}/{user,order,product,customer,billing}
  i=0
  for dir in pkg/handler/{user,order,product,customer,billing} \
             pkg/service/{user,order,product,customer,billing} \
             pkg/store/{user,order,product,customer,billing} \
             pkg/worker/{user,order,product,customer,billing} \
             pkg/internal/{user,order,product,customer,billing}; do
    for n in 1 2 3 4; do
      i=$((i+1))
      cat > "$dir/file$n.go" <<EOF
  package $(basename $dir)
  import "fmt"
  func NewService$i() *Service$i { return &Service$i{} }
  type Service$i struct{}
  func (s *Service$i) Process() error { return fmt.Errorf("processing failed") }
  EOF
    done
  done
  git add . && git commit -qm initial
  ```
- [ ] `git ls-files '*.go' | wc -l` returns exactly `100`
- [ ] `ast-grep --version` resolves on host
- [ ] Pin the LLM-call counter via a Claude CLI shim:
  ```bash
  CLAUDE_BIN=$(command -v claude)
  mkdir -p /tmp/llm-count-shim
  cat > /tmp/llm-count-shim/claude <<SHIM
  #!/bin/sh
  printf '1\n' >> /tmp/llm-call-count.log
  exec "$CLAUDE_BIN" "\$@"
  SHIM
  chmod +x /tmp/llm-count-shim/claude
  : > /tmp/llm-call-count.log
  export PATH=/tmp/llm-count-shim:$PATH
  ```
  Every `claude` invocation under the shim appends one line; final count is `wc -l < /tmp/llm-call-count.log`
- [ ] Positive control on the shim: `claude --version >/dev/null && [ "$(wc -l < /tmp/llm-call-count.log)" = "1" ]` (after the manual probe, reset with `: > /tmp/llm-call-count.log` before the Action step)

## Action

- [ ] Run `/coding:pr-review master standard` against `$WORK` in a fresh Claude Code session under the shim PATH; tee stdout to `/tmp/scaling-pr-stdout.log`, stderr to `/tmp/scaling-pr-stderr.log`, capture exit code to `/tmp/scaling-pr-exit`
- [ ] Record wall-clock duration with `time` wrapping the slash command; capture the `real` line to `/tmp/scaling-pr-time.log`
- [ ] Extract the Step 5 Consolidated Report section: `awk '/^### Step 5:/{flag=1} flag' /tmp/scaling-pr-stdout.log > /tmp/scaling-pr-report.md`

## Expected

- [ ] `cat /tmp/scaling-pr-exit` prints `0`
- [ ] `wc -l < /tmp/llm-call-count.log` returns ≤ `30` (proves the funnel: ast-grep mechanical layer carries 100-file scale at constant LLM cost)
- [ ] `/tmp/scaling-pr-time.log` `real` line parses to ≤ `30m00s` (stays under the prod bot's `activeDeadlineSeconds=1800` ceiling — the same one that killed coding#27)
- [ ] `jq '.stats.findings_count' /tmp/scaling-pr-stdout.log` returns > `0` — negative control: the synthetic violations were actually surfaced (if 0, the funnel didn't run and the LLM count is misleadingly low)
- [ ] `grep -oE 'go-[a-z-]+/[a-z-]+' /tmp/scaling-pr-report.md | sort -u | wc -l` returns ≥ `3` — at least 3 distinct rule_ids surfaced (the per-Owner adjudication phase processed findings, didn't drop them)
- [ ] `grep -c 'dropped finding' /tmp/scaling-pr-stderr.log` returns `0` — citation validator dropped nothing; every surfaced finding cites a real rule_id

## Cleanup

- `rm -rf "$WORK" /tmp/scaling-pr-* /tmp/llm-count-shim /tmp/llm-call-count.log`

After the scenario passes, the operator should record the measured `(LLM count, duration, findings count)` tuple in the Progress section of the task page (`[[Refactor coding pr-review to doc-driven rules pipeline]]`) so future Phase-10 reruns have a baseline. This is a follow-up note, not part of the scenario contract.
