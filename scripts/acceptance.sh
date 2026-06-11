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

echo "=== 1/5 Mode coverage ==="

# Short mode in both dispatcher commands must skip Step 4 entirely (no runner agent).
if grep -qE "Short Mode.*No agents|Short Mode.*skip" commands/pr-review.md && \
   grep -qE "Short Mode.*No agents|Short Mode.*skip" commands/code-review.md; then
  ok "short mode skips Step 4 in both pr-review.md AND code-review.md"
else
  fail "short mode skip directive missing from pr-review.md or code-review.md"
fi

# All modes (selector/full) invoke the deterministic runner script (Step 4a is mandatory for
# the dispatcher). The former coding:ast-grep-runner agent is deprecated and must
# NOT be invoked by either command.
if grep -qE "scripts/ast-grep-runner\.sh" commands/code-review.md && \
   grep -qE "scripts/ast-grep-runner\.sh" commands/pr-review.md; then
  ok "ast-grep-runner.sh invoked in both dispatcher commands"
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

# Default/otherwise token must route to Selector mode in both commands.
if grep -qE "Selector mode \(the default\)|Selector mode \(default\)" commands/pr-review.md && \
   grep -qE "Selector mode \(the default\)|Selector mode \(default\)" commands/code-review.md; then
  ok "default/otherwise token routes to Selector mode (default) in both commands"
else
  fail "Selector mode (default) routing missing from pr-review.md or code-review.md"
fi

echo "=== 2/5 Per-language routing ==="

# Full-mode per-owner dispatch block present — findings_by_owner feeds the dispatch set and
# coding:<owner> agent prompts reference it. Per-owner dispatch lives in full mode only
# (standard/selector path removed); the check asserts what remains true post-flip.
if grep -qE "coding:<owner>|findings_by_owner" commands/code-review.md && \
   grep -qE "coding:<owner>|findings_by_owner" commands/pr-review.md; then
  ok "full-mode per-owner dispatch block (findings_by_owner / coding:<owner>) present in both dispatcher commands"
else
  fail "full-mode per-owner dispatch block missing from pr-review.md or code-review.md"
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

echo "=== 3/5 Context loading (Step 2.5 globs) ==="

# Each canonical context-doc mapping must be referenced in both dispatcher commands.
for mapping in "teamvault-conventions.md" "go-k8s-binary-conventions.md" "k8s-manifest-guide.md" "changelog-guide.md"; do
  if grep -qF "$mapping" commands/pr-review.md && grep -qF "$mapping" commands/code-review.md; then
    ok "Step 2.5 mapping '$mapping' present in both dispatcher commands"
  else
    fail "Step 2.5 mapping '$mapping' missing from pr-review.md OR code-review.md"
  fi
done

echo "=== 4/5 Broken-YAML isolation ==="

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

echo "=== 5/5 Selector mode contracts ==="

# (a) Both command files reference --selector token in Step 1 parse, the
# short-circuit string, and the GUIDE_OK/GUIDE_MISSING fail-fast block.
for cmd in commands/pr-review.md commands/code-review.md; do
  if grep -qE '\-\-selector|selector.*mode' "$cmd"; then
    ok "$cmd: --selector token present in Step 1 parse"
  else
    fail "$cmd: --selector token missing from Step 1 parse"
  fi
  if grep -qF 'selector clean — no adjudication needed' "$cmd"; then
    ok "$cmd: short-circuit string 'selector clean — no adjudication needed' present"
  else
    fail "$cmd: short-circuit string 'selector clean — no adjudication needed' missing"
  fi
  if grep -qF 'GUIDE_OK' "$cmd" && grep -qF 'GUIDE_MISSING' "$cmd"; then
    ok "$cmd: GUIDE_OK/GUIDE_MISSING fail-fast block present"
  else
    fail "$cmd: GUIDE_OK/GUIDE_MISSING fail-fast block missing"
  fi
done

# (b) docs/selector-mode-guide.md exists and contains the required sections
# and the verbatim recall contract sentence.
SELECTOR_GUIDE="docs/selector-mode-guide.md"
if [ -f "$SELECTOR_GUIDE" ]; then
  ok "docs/selector-mode-guide.md exists"
else
  fail "docs/selector-mode-guide.md missing"
fi
if grep -qF 'Step 4c-sel' "$SELECTOR_GUIDE" && grep -qF 'CLASSIFY' "$SELECTOR_GUIDE"; then
  ok "selector guide contains Step 4c-sel CLASSIFY"
else
  fail "selector guide missing Step 4c-sel CLASSIFY"
fi
if grep -qF 'Step 4d-sel' "$SELECTOR_GUIDE" && grep -qF 'ADJUDICATE' "$SELECTOR_GUIDE"; then
  ok "selector guide contains Step 4d-sel ADJUDICATE"
else
  fail "selector guide missing Step 4d-sel ADJUDICATE"
fi
if grep -qF 'When uncertain, include.' "$SELECTOR_GUIDE"; then
  ok "selector guide contains verbatim recall contract sentence 'When uncertain, include.'"
else
  fail "selector guide missing verbatim recall contract sentence 'When uncertain, include.'"
fi

# (c) Sibling consistency: both pr-review.md and code-review.md reference the
# same guide filename and the same step labels (4c-sel, 4d-sel).
pr_guide=$(grep -oE 'selector-mode-guide\.md' commands/pr-review.md | head -1)
cr_guide=$(grep -oE 'selector-mode-guide\.md' commands/code-review.md | head -1)
if [ "$pr_guide" = "selector-mode-guide.md" ] && [ "$cr_guide" = "selector-mode-guide.md" ]; then
  ok "both commands reference the same guide filename: selector-mode-guide.md"
else
  fail "commands reference different guide filenames: pr-review='$pr_guide' code-review='$cr_guide'"
fi
for label in '4c-sel' '4d-sel'; do
  pr_has=$(grep -c "$label" commands/pr-review.md || true)
  cr_has=$(grep -c "$label" commands/code-review.md || true)
  if [ "$pr_has" -ge 1 ] && [ "$cr_has" -ge 1 ]; then
    ok "step label '$label' present in both commands"
  else
    fail "step label '$label' missing — pr-review=$pr_has code-review=$cr_has"
  fi
done

# (d) Citation validator rejects unknown rule_ids: build a temp findings JSON
# citing a fake rule_id, run validate-citations.sh, assert non-zero exit.
FAKE_FINDINGS="$WORK/fake-findings.json"
cat > "$FAKE_FINDINGS" <<'FAKE_EOF'
[{"rule_id": "fake/this-rule-does-not-exist", "file": "x.go", "line": 1}]
FAKE_EOF
fake_exit=0
bash scripts/validate-citations.sh "$FAKE_FINDINGS" > /dev/null 2>&1 || fake_exit=$?
if [ "$fake_exit" -ne 0 ]; then
  ok "citation validator exits non-zero for unknown rule_id 'fake/this-rule-does-not-exist'"
else
  fail "citation validator returned 0 for unknown rule_id — validator not enforcing index membership"
fi

# (e) Runner .git exclusion: create a temp dir with a .git/COMMIT_EDITMSG
# containing a go-errors violation and a normal .go file with the same
# violation; run ast-grep-runner.sh over both paths; assert findings contain
# the .go file hit and ZERO findings whose file path contains .git/
GIT_EXCL_DIR="$WORK/git-excl-test"
mkdir -p "$GIT_EXCL_DIR/.git" "$GIT_EXCL_DIR/pkg"
# Plant a violation in .git/COMMIT_EDITMSG (should be excluded)
cat > "$GIT_EXCL_DIR/.git/COMMIT_EDITMSG" <<'GIT_EOF'
package x
import "fmt"
func G() error { return fmt.Errorf("stale") }
GIT_EOF
# Plant the same violation in a normal .go file (should be found)
cat > "$GIT_EXCL_DIR/pkg/real.go" <<'REAL_EOF'
package x
import "fmt"
func F() error { return fmt.Errorf("bad") }
REAL_EOF

RUNNER_OUT="$WORK/git-excl-runner.json"
bash scripts/ast-grep-runner.sh "$GIT_EXCL_DIR" \
  "$GIT_EXCL_DIR/pkg/real.go" \
  "$GIT_EXCL_DIR/.git/COMMIT_EDITMSG" \
  > "$RUNNER_OUT" 2>/dev/null || true

git_findings=$(jq -r '[.findings_by_owner | to_entries[] | .value[] | .file] | map(select(contains("/.git/"))) | length' "$RUNNER_OUT" 2>/dev/null || echo "0")
if [ "$git_findings" -eq 0 ]; then
  ok "runner excludes .git/ paths — zero findings with /.git/ in file path"
else
  fail "runner produced $git_findings finding(s) from .git/ paths — exclusion not working"
fi

go_findings=$(jq -r '[.findings_by_owner | to_entries[] | .value[] | .file] | map(select(contains("pkg/real.go"))) | length' "$RUNNER_OUT" 2>/dev/null || echo "0")
if [ "$go_findings" -ge 1 ]; then
  ok "runner still finds violations in normal .go file after .git/ exclusion"
else
  fail "runner found zero violations in pkg/real.go — normal scan broken or no-fmt-errorf YAML missing"
fi

echo ""
echo "=== Summary ==="
echo "  PASS: $ACCEPTANCE_PASS"
echo "  FAIL: $ACCEPTANCE_FAIL"

if [ "$ACCEPTANCE_FAIL" -gt 0 ]; then
  exit 1
fi
