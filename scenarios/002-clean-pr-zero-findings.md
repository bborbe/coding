---
status: active
---

# Scenario 002: Zero-violation PR in standard mode produces empty findings, no false positives

Validates that a diff with no mechanical-rule violations flows through `/coding:code-review master standard` (Step 4.0 → 4a → 4b → 4c → 4d → 5) and produces a report with empty Must Fix / Should Fix / Nice to Have sections — locking down the regression risk that the LLM tier hallucinates findings to fill the void when the mechanical layer surfaces none.

## Setup

- [ ] Clone master at the current HEAD: `WORK=$(mktemp -d) && cd "$WORK" && git clone --depth=1 --branch master git@github.com:bborbe/coding.git . && git checkout -b clean-pr-fixture`
- [ ] Apply a README-only whitespace edit (no `.go` / `.py` / `rules/**` / `docs/**` touched): `sed -i.bak 's/^# bborbe\/coding$/# bborbe\/coding  /' README.md && rm README.md.bak && git add README.md && git commit -qm 'docs: typo whitespace'`
- [ ] `git diff --name-only master..HEAD` prints exactly one line: `README.md`
- [ ] `ast-grep --version` resolves on host (Step 4.0 preflight will pass)

## Action

- [ ] Run `/coding:code-review master` against `$WORK` in a fresh Claude Code session (standard mode is the default — do not pass a mode argument); tee stdout to `/tmp/code-review-stdout.log`, stderr to `/tmp/code-review-stderr.log`, capture exit code to `/tmp/code-review-exit`

## Expected

- [ ] `cat /tmp/code-review-exit` prints `0`
- [ ] Runner block in stdout has `findings_count: 0`: extract the JSON block via `awk '/^{$/,/^}$/' /tmp/code-review-stdout.log > /tmp/code-review-runner.json && jq '.stats.findings_count' /tmp/code-review-runner.json` returns `0`
- [ ] Report includes a `Must Fix (Critical)` section whose body line is exactly `None.` — verified via: `awk '/^#### Must Fix/{flag=1; next} /^#### /{flag=0} flag && NF' /tmp/code-review-stdout.log` prints exactly `None.`
- [ ] Report includes a `Should Fix (Important)` section whose body line is exactly `None.` (same `awk` shape)
- [ ] Report includes a `Nice to Have (Optional)` section whose body line is exactly `None.` (same `awk` shape)
- [ ] `grep -c 'dropped finding' /tmp/code-review-stderr.log` returns `0` — citation validator had nothing to drop because no findings were generated
- [ ] Run completes in under 5 minutes (`time` output's `real` < 5m)

## Cleanup

- `rm -rf "$WORK" /tmp/code-review-*`
