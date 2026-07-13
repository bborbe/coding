---
status: active
---

# Scenario 001: Dispatcher fail-fasts when ast-grep binary is missing

Validates that the Step 4.0 preflight block in `commands/pr-review.md` and `commands/code-review.md` exits 1 with the documented error message when `ast-grep` / `sg` is absent from PATH, and that `scripts/ast-grep-runner.sh` exits 2 and emits a machine-readable JSON error with `.errors[].kind == "missing-tool"` — closing the silent-empty-review failure mode observed on [bborbe/coding#34](https://github.com/bborbe/coding/pull/34).

## Setup

- [ ] Build a masked PATH that excludes any directory containing `ast-grep` or `sg`:
  ```bash
  PATH_MASKED=$(echo "$PATH" | tr ':' '\n' | while read d; do
    [ -x "$d/ast-grep" ] || [ -x "$d/sg" ] || echo "$d"
  done | paste -sd: -)
  ```
- [ ] `PATH=$PATH_MASKED command -v ast-grep; echo "exit=$?"` prints `exit=1`
- [ ] `PATH=$PATH_MASKED command -v sg; echo "exit=$?"` prints `exit=1`
- [ ] Extract the Step 4.0 bash block verbatim from `commands/pr-review.md` and `commands/code-review.md` (search for `#### 4.0:` and pick the fenced `bash` block beneath it). Keep them as `$PRREVIEW_STEP40` and `$CODEREVIEW_STEP40` shell variables. **Fragility note**: the extraction relies on the literal section header `#### 4.0:`. If a future refactor renames or renumbers the heading, the extraction silently picks up the wrong block; bump this scenario's brittleness by re-anchoring on the new heading text.
- [ ] Locate `scripts/ast-grep-runner.sh` in the coding plugin root (resolve via `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/plugins/marketplaces/coding}/scripts/ast-grep-runner.sh`, falling back to `$HOME/Documents/workspaces/coding/scripts/ast-grep-runner.sh`). Keep path as `$RUNNER`.

## Action

- [ ] Run the pr-review Step 4.0 block under the masked PATH; capture stderr and exit code:
  ```bash
  PATH=$PATH_MASKED bash -c "$PRREVIEW_STEP40" 2> /tmp/scen001-pr.stderr
  echo $? > /tmp/scen001-pr.exit
  ```
- [ ] Run the code-review Step 4.0 block the same way; save to `/tmp/scen001-cr.{stderr,exit}`
- [ ] Run `scripts/ast-grep-runner.sh` directly under the masked PATH against a temp dir; capture stdout, stderr, and exit code:
  ```bash
  TMPWORK=$(mktemp -d)
  PATH=$PATH_MASKED bash -c '"$RUNNER" "$TMPWORK"' > /tmp/scen001-runner.stdout 2> /tmp/scen001-runner.stderr
  echo $? > /tmp/scen001-runner.exit
  rm -rf "$TMPWORK"
  ```

## Expected

- [ ] `cat /tmp/scen001-pr.exit` prints `1`
- [ ] `/tmp/scen001-pr.stderr` contains the literal string `ast-grep/sg not in PATH`
- [ ] `cat /tmp/scen001-cr.exit` prints `1`
- [ ] `/tmp/scen001-cr.stderr` contains the literal string `ast-grep/sg not in PATH` (parity with pr-review.md)
- [ ] `cat /tmp/scen001-runner.exit` prints `2` (not `1` — the runner uses exit 2 for all toolchain/infrastructure failures to distinguish them from findings-present exit 1 in future)
- [ ] `jq -e '.errors[] | select(.kind == "missing-tool" and .tool == "ast-grep")' /tmp/scen001-runner.stdout` exits `0`
- [ ] `jq '.stats.yamls_run' /tmp/scen001-runner.stdout` returns `0` and `jq '.findings_by_owner' /tmp/scen001-runner.stdout` returns `{}`
- [ ] Each block's wall-clock under 1 second (each block is a single `command -v` check that returns immediately — 1s is generous even on CI environments with slow disk I/O; the regression risk is the `sg --version` loop on coding#34 which took 30 min, so any threshold below the 30-min `activeDeadlineSeconds` ceiling proves the contract, and 1s catches the loop with 1800× margin)
- [ ] Host shell `command -v ast-grep` (after all subshells) still resolves a path

## Cleanup

- `rm -f /tmp/scen001-*.{stderr,exit,stdout}`

## Walk 2026-06-09

Setup — masked PATH verified:

```
$ PATH=$PATH_MASKED command -v ast-grep; echo "exit=$?"
exit=1
$ PATH=$PATH_MASKED command -v sg; echo "exit=$?"
exit=1
```

Note: The Step 4.0 blocks contain `<REVIEW_DIR>` / `<directory>` placeholder that an LLM dispatcher substitutes at runtime. For walking purposes the placeholder was replaced with `/tmp`.

pr-review Step 4.0 under masked PATH:

```
wall_ms=11
exit: 1
stderr: ERROR: ast-grep/sg not in PATH. Install via 'npm install -g @ast-grep/cli' (or 'apk add ast-grep' in alpine). pr-reviewer container fix: bborbe/maintainer agent/pr-reviewer/Dockerfile commit 1de083f.
```

code-review Step 4.0 under masked PATH:

```
wall_ms=10
exit: 1
stderr: ERROR: ast-grep/sg not in PATH. Install via 'npm install -g @ast-grep/cli' (or 'apk add ast-grep' in alpine). pr-reviewer container fix: bborbe/maintainer agent/pr-reviewer/Dockerfile commit 1de083f.
```

`scripts/ast-grep-runner.sh` under masked PATH (RUNNER resolved from coding worktree):

```
wall_ms=229
exit: 2
stdout: {"stats":{"yamls_run":0,"findings_count":0,"elapsed_ms":0},"findings_by_owner":{},"errors":[{"kind":"missing-tool","tool":"ast-grep","detail":"ast-grep / sg binary not in PATH — install via: npm install -g @ast-grep/cli | brew install ast-grep"}]}
```

Host ast-grep after all subshells: `/opt/homebrew/bin/ast-grep`

### Results

- [x] `cat /tmp/scen001-pr.exit` prints `1` — PASS
- [x] `/tmp/scen001-pr.stderr` contains `ast-grep/sg not in PATH` — PASS
- [x] `cat /tmp/scen001-cr.exit` prints `1` — PASS
- [x] `/tmp/scen001-cr.stderr` contains `ast-grep/sg not in PATH` — PASS
- [x] `cat /tmp/scen001-runner.exit` prints `2` — PASS
- [x] `jq -e '.errors[] | select(.kind == "missing-tool" and .tool == "ast-grep")'` exits `0` — PASS
- [x] `.stats.yamls_run == 0` and `.findings_by_owner == {}` — PASS
- [x] Wall-clock under 1 second (pr: 11ms, cr: 10ms, runner: 229ms — all well under 1s) — PASS
- [x] Host `command -v ast-grep` still resolves (`/opt/homebrew/bin/ast-grep`) — PASS

All 9 Expected items: **9/9 PASS**
