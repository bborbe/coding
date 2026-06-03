---
status: active
---

# Scenario 001: Dispatcher fail-fasts when ast-grep binary is missing

Validates that the Step 4.0 preflight block in `commands/pr-review.md` and `commands/code-review.md` (and the Step 0 preflight block in `agents/ast-grep-runner.md`) exits 1 with the documented error message when `ast-grep` / `sg` is absent from PATH — closing the silent-empty-review failure mode observed on [bborbe/coding#34](https://github.com/bborbe/coding/pull/34).

## Setup

- [ ] Build a masked PATH that excludes any directory containing `ast-grep` or `sg`:
  ```bash
  PATH_MASKED=$(echo "$PATH" | tr ':' '\n' | while read d; do
    [ -x "$d/ast-grep" ] || [ -x "$d/sg" ] || echo "$d"
  done | paste -sd: -)
  ```
- [ ] `PATH=$PATH_MASKED command -v ast-grep; echo "exit=$?"` prints `exit=1`
- [ ] `PATH=$PATH_MASKED command -v sg; echo "exit=$?"` prints `exit=1`
- [ ] Extract the Step 4.0 bash block verbatim from `commands/pr-review.md` and `commands/code-review.md` (search for `#### 4.0:` and pick the fenced `bash` block beneath it). Keep them as `$PRREVIEW_STEP40` and `$CODEREVIEW_STEP40` shell variables.
- [ ] Extract the Step 0 preflight bash block from `agents/ast-grep-runner.md` (search for `### 0. Preflight:`, pick the fenced `bash` block). Keep as `$RUNNER_STEP0`.

## Action

- [ ] Run the pr-review Step 4.0 block under the masked PATH; capture stderr and exit code:
  ```bash
  PATH=$PATH_MASKED bash -c "$PRREVIEW_STEP40" 2> /tmp/scen001-pr.stderr
  echo $? > /tmp/scen001-pr.exit
  ```
- [ ] Run the code-review Step 4.0 block the same way; save to `/tmp/scen001-cr.{stderr,exit}`
- [ ] Run the runner Step 0 block the same way; runner emits JSON to stdout before exit — save to `/tmp/scen001-runner.{stdout,exit}` (`PATH=$PATH_MASKED bash -c "$RUNNER_STEP0" > /tmp/scen001-runner.stdout 2> /tmp/scen001-runner.stderr; echo $? > /tmp/scen001-runner.exit`)

## Expected

- [ ] `cat /tmp/scen001-pr.exit` prints `1`
- [ ] `/tmp/scen001-pr.stderr` contains the literal string `ast-grep/sg not in PATH`
- [ ] `cat /tmp/scen001-cr.exit` prints `1`
- [ ] `/tmp/scen001-cr.stderr` contains the literal string `ast-grep/sg not in PATH` (parity with pr-review.md)
- [ ] `cat /tmp/scen001-runner.exit` prints `1`
- [ ] `jq -e '.errors[] | select(.kind == "missing-tool" and .tool == "ast-grep")' /tmp/scen001-runner.stdout` exits `0`
- [ ] `jq '.stats.yamls_run' /tmp/scen001-runner.stdout` returns `0` and `jq '.findings_by_owner' /tmp/scen001-runner.stdout` returns `{}`
- [ ] Each block's wall-clock under 1 second (regression risk: `sg --version` loop on coding#34 took 30 min; immediate exit is the contract)
- [ ] Host shell `command -v ast-grep` (after all subshells) still resolves a path

## Cleanup

- `rm -f /tmp/scen001-*.{stderr,exit,stdout}`
