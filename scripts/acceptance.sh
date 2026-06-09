#!/bin/bash
# scripts/acceptance.sh — acceptance suite for the doc-driven review pipeline.
#
# Runs the 4 unit/integration tests that were left over from the
# scenario-writing cut (only E2E-bar scenarios shipped as scenarios/*.md;
# these stay as scripted assertions because they don't need a real
# slash-command run).
#
#   1. Mode coverage — short/standard/full dispatch contracts in commands/
#   2. Per-language routing — Go vs Python agent scope in code-review.md
#   3. Context loading — Step 2.5 file-glob → doc mapping consistency
#   4. Broken-YAML isolation — ast-grep error on bad YAML doesn't mask
#      findings from good YAMLs in the same dir
#
# Wired into `make precommit` via Makefile target `check-acceptance`.
# Exits 1 on any FAIL so CI catches dispatcher contract drift.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

# Preflight — fail fast if a required binary is missing rather than letting
# downstream checks silently no-op (e.g. jq absent → cross-language leak check
# silently reports PASS, hiding real coverage gaps).
for bin in jq ast-grep; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "ERROR: $bin is required by scripts/acceptance.sh but not in PATH." >&2
    echo "  jq:       brew install jq      | apt-get install -y jq" >&2
    echo "  ast-grep: npm install -g @ast-grep/cli  | brew install ast-grep" >&2
    exit 1
  fi
done

ACCEPTANCE_PASS=0
ACCEPTANCE_FAIL=0

ok()   { ACCEPTANCE_PASS=$((ACCEPTANCE_PASS+1)); printf "  ✅ %s\n" "$1"; }
fail() { ACCEPTANCE_FAIL=$((ACCEPTANCE_FAIL+1)); printf "  ❌ %s\n" "$1"; }

echo "=== 1/4 Mode coverage ==="

# Short mode in both dispatcher commands must skip Step 4 entirely (no runner agent).
if grep -qE "Short Mode.*No agents|Short Mode.*skip" commands/pr-review.md && \
   grep -qE "Short Mode.*No agents|Short Mode.*skip" commands/code-review.md; then
  ok "short mode skips Step 4 in both pr-review.md AND code-review.md"
else
  fail "short mode skip directive missing from pr-review.md or code-review.md"
fi

# Standard mode invokes the deterministic runner script (Step 4a is mandatory for
# the dispatcher). The former coding:ast-grep-runner agent is deprecated and must
# NOT be invoked by either command.
if grep -qE "scripts/ast-grep-runner\.sh" commands/code-review.md && \
   grep -qE "scripts/ast-grep-runner\.sh" commands/pr-review.md; then
  ok "standard mode invokes scripts/ast-grep-runner.sh in both dispatcher commands"
else
  fail "scripts/ast-grep-runner.sh not referenced in pr-review.md or code-review.md"
fi
if grep -qE '^coding:ast-grep-runner agent' commands/code-review.md commands/pr-review.md; then
  fail "deprecated coding:ast-grep-runner agent still invoked in a dispatcher command"
else
  ok "deprecated coding:ast-grep-runner agent not invoked by either command"
fi

# Full mode lists at least 4 conditional / legacy-path agents that haven't migrated
# to RULE blocks yet (license, readme, shellcheck, context7, go-version-manager, …).
conditional_agents=0
for a in license-assistant readme-quality-assistant shellcheck-assistant context7-library-checker go-version-manager go-tooling-assistant; do
  if grep -qE "$a" commands/code-review.md; then
    conditional_agents=$((conditional_agents+1))
  fi
done
if [ "$conditional_agents" -ge 4 ]; then
  ok "full mode references $conditional_agents legacy-path agents (≥ 4) in code-review.md"
else
  fail "full mode references only $conditional_agents legacy-path agents (< 4) in code-review.md"
fi

echo "=== 2/4 Per-language routing ==="

# Per-Owner adjudication block present (Step 4b) — the routing surface.
if grep -qE "Per-Owner adjudication|coding:<owner>|findings_by_owner" commands/code-review.md && \
   grep -qE "Per-Owner adjudication|coding:<owner>|findings_by_owner" commands/pr-review.md; then
  ok "Step 4b per-Owner adjudication block present in both dispatcher commands"
else
  fail "Step 4b per-Owner adjudication block missing from pr-review.md or code-review.md"
fi

# Every owner referenced in rules/index.json must have a matching agent file in agents/.
# If an owner has findings but no agent file, Step 4b's `coding:<owner>` dispatch fails.
missing_owner_agents=0
while IFS= read -r owner; do
  if [ -n "$owner" ] && [ ! -f "agents/${owner}.md" ]; then
    missing_owner_agents=$((missing_owner_agents+1))
  fi
done < <(jq -r '.[].owner' rules/index.json | sort -u)
if [ "$missing_owner_agents" -eq 0 ]; then
  ok "every owner in rules/index.json has a corresponding agents/<owner>.md file"
else
  fail "$missing_owner_agents owner(s) in rules/index.json have no matching agent file — Step 4b would silently no-op for these"
fi

# Cross-language leak: rule IDs encode language by prefix (`go-*`, `python-*`).
# rules/index.json does NOT carry an explicit `language` field, so the rule_id
# prefix is the source of truth. A `go-*` rule must be owned by a `go-*` agent
# (or a shared owner that doesn't start with `python-`), and vice versa.
go_python_leak=$(jq -r '.[] | select(.id | startswith("go-")) | .owner' rules/index.json | grep -cE '^python-' || true)
python_go_leak=$(jq -r '.[] | select(.id | startswith("python-")) | .owner' rules/index.json | grep -cE '^go-' || true)
if [ "$go_python_leak" -eq 0 ] && [ "$python_go_leak" -eq 0 ]; then
  ok "no cross-language owner leak: go-* rules → non-python owners, python-* rules → non-go owners"
else
  fail "cross-language owner leak: go→python=$go_python_leak, python→go=$python_go_leak"
fi

echo "=== 3/4 Context loading (Step 2.5 globs) ==="

# Each canonical context-doc mapping must be referenced in both dispatcher commands.
for mapping in "teamvault-conventions.md" "go-k8s-binary-conventions.md" "k8s-manifest-guide.md" "changelog-guide.md"; do
  if grep -qF "$mapping" commands/pr-review.md && grep -qF "$mapping" commands/code-review.md; then
    ok "Step 2.5 mapping '$mapping' present in both dispatcher commands"
  else
    fail "Step 2.5 mapping '$mapping' missing from pr-review.md OR code-review.md"
  fi
done

echo "=== 4/4 Broken-YAML isolation ==="

# Construct a sandbox: one valid YAML + one syntactically broken YAML.
# Verify ast-grep errors on the broken one but the valid one still surfaces findings.
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/rules/go"
cp rules/go/no-fmt-errorf.yml "$WORK/rules/go/good.yml"
cat > "$WORK/rules/go/broken.yml" <<'EOF'
id: t/broken
language: go
severity: error
message: x
rule:
  pattern-regex: 'something'
EOF
cat > "$WORK/sample.go" <<'EOF'
package x
import "fmt"
func F() error { return fmt.Errorf("bad") }
EOF

broken_out=$(ast-grep scan --rule "$WORK/rules/go/broken.yml" "$WORK/sample.go" 2>&1 || true)
if echo "$broken_out" | grep -q "Cannot parse rule"; then
  ok "broken YAML reports parse error"
else
  fail "broken YAML did not report parse error (ast-grep output: $(echo "$broken_out" | head -1))"
fi

good_out=$(ast-grep scan --rule "$WORK/rules/go/good.yml" "$WORK/sample.go" 2>&1)
good_count=$(echo "$good_out" | grep -c '^error\[' || true)
if [ "$good_count" -ge 1 ]; then
  ok "good YAML still surfaces $good_count finding(s) — isolation holds"
else
  fail "good YAML emitted zero findings — broken YAML may be masking the others when run together"
fi

echo ""
echo "=== Summary ==="
echo "  PASS: $ACCEPTANCE_PASS"
echo "  FAIL: $ACCEPTANCE_FAIL"

if [ "$ACCEPTANCE_FAIL" -gt 0 ]; then
  exit 1
fi
