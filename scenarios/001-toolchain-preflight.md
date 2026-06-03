---
status: draft
---

# Scenario 001: Dispatcher fail-fasts when ast-grep binary is missing

Validates that `/coding:code-review` and `/coding:pr-review` abort with an actionable error when `ast-grep` / `sg` is absent from PATH — closing the silent-empty-review failure mode observed on [bborbe/coding#34](https://github.com/bborbe/coding/pull/34).

## Setup

- [ ] Build a masked PATH that excludes any directory containing `ast-grep` or `sg`:
  ```bash
  PATH_MASKED=$(echo "$PATH" | tr ':' '\n' | while read d; do
    [ -x "$d/ast-grep" ] || [ -x "$d/sg" ] || echo "$d"
  done | paste -sd: -)
  ```
- [ ] `PATH=$PATH_MASKED command -v ast-grep; echo "exit=$?"` prints `exit=1`
- [ ] `PATH=$PATH_MASKED command -v sg; echo "exit=$?"` prints `exit=1`
- [ ] Create a minimal Go fixture: `WORK=$(mktemp -d) && cd "$WORK" && git init -q && printf 'package main\n\nfunc main() {}\n' > main.go && git add . && git commit -qm initial`
- [ ] Host shell `command -v ast-grep` (outside any subshell) still resolves a path

## Action

- [ ] In a fresh Claude Code session launched as `PATH=$PATH_MASKED claude`, run `/coding:code-review master` against `$WORK`; tee stdout to `/tmp/cr-stdout.log`, stderr to `/tmp/cr-stderr.log`, and capture exit code: `... ; echo $? > /tmp/cr-exit`
- [ ] In a fresh Claude Code session launched as `PATH=$PATH_MASKED claude`, run `/coding:pr-review master` against `$WORK`; same tee + exit-code capture to `/tmp/pr-{stdout,stderr,exit}.log`
- [ ] Direct runner test: in a `PATH=$PATH_MASKED` subshell, invoke the `coding:ast-grep-runner` agent via `claude` with the prompt `TARGET_DIR=$WORK. Run every YAML in rules/<lang>/*.yml. Return findings grouped by Owner.` — tee stdout to `/tmp/runner-stdout.log`, capture exit code to `/tmp/runner-exit`

## Expected

- [ ] `/tmp/cr-stderr.log` contains the literal string `ast-grep/sg not in PATH`
- [ ] `cat /tmp/cr-exit` prints `1`
- [ ] `grep -c 'coding:ast-grep-runner agent:' /tmp/cr-stdout.log` returns `0` (Step 4a was never invoked)
- [ ] `/tmp/pr-stderr.log` contains `ast-grep/sg not in PATH` and `cat /tmp/pr-exit` prints `1`
- [ ] `jq -e '.errors[] | select(.kind == "missing-tool" and .tool == "ast-grep")' /tmp/runner-stdout.log` exits 0
- [ ] `jq '.stats.yamls_run' /tmp/runner-stdout.log` returns `0` and `jq '.findings_by_owner' /tmp/runner-stdout.log` returns `{}`
- [ ] `cat /tmp/runner-exit` prints `1`
- [ ] Each invocation's wall-clock under 30 seconds (`time` output's `real` < 30s) — the regression risk being locked down is a 30-min `activeDeadlineSeconds` kill instead of immediate fail
- [ ] Host shell `command -v ast-grep` (re-run after all subshells) still resolves a path

## Cleanup

- `rm -rf "$WORK" /tmp/cr-* /tmp/pr-* /tmp/runner-*`
