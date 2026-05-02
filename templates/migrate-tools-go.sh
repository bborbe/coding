#!/bin/bash
# Migrate all trading sub-modules from tools.go to tools.env + Makefile @version pattern.
# Idempotent: safe to re-run. Uses the canonical pattern proven on 38+ migrations + lib pilot.
# Run from trading repo root.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Sanity: ensure root setup is in place (Makefile.precommit + tools.env)
[[ -f tools.env ]] || { echo "ERROR: tools.env missing at root"; exit 1; }
grep -q "include \$(ROOTDIR)/tools.env" Makefile.precommit || { echo "ERROR: Makefile.precommit not migrated"; exit 1; }

# Find all sub-modules with tools.go (skip vendor + workspace dirs)
SUBMODULES=()
while IFS= read -r line; do
  SUBMODULES+=("$line")
done < <(find . -maxdepth 5 -name "tools.go" -not -path "*/vendor/*" -not -path "./node_modules/*" | sed 's|/tools.go$||' | sort)

echo "Found ${#SUBMODULES[@]} sub-modules with tools.go"
echo "---"

# Update //go:generate counterfeiter directives across the whole repo (one pass)
# Migrate from `go run -mod=mod ... counterfeiter/v6 -generate` to `go run ... counterfeiter/v6@v6.12.2 -generate`
echo "Updating //go:generate counterfeiter directives..."
grep -rl '//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate' . 2>/dev/null \
  | grep -v vendor \
  | xargs -I {} sed -i '' 's|//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate|//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate|' {} 2>/dev/null
echo "✓ counterfeiter directives done"
echo "---"

# Drop the obsolete replace directives (in case any sub-module has them)
DROP_REPLACES=(
  github.com/charmbracelet/x/cellbuf
  github.com/denis-tingaikin/go-header
  github.com/diskfs/go-diskfs
  github.com/nunnatsa/ginkgolinter/types
  github.com/anthropics/anthropic-sdk-go
  github.com/opencontainers/runtime-spec
)

# Track failures
declare -a FAILED

for sm in "${SUBMODULES[@]}"; do
  echo "=== $sm ==="
  cd "$ROOT/$sm"

  # 1. Delete tools.go
  rm -f tools.go

  # 2. Drop obsolete replaces
  for r in "${DROP_REPLACES[@]}"; do
    go mod edit -dropreplace "$r" 2>/dev/null || true
  done

  # 3. Bump bborbe @latest (direct + indirect)
  if grep -q '^\tgithub.com/bborbe/' go.mod 2>/dev/null; then
    grep '^\tgithub.com/bborbe/' go.mod | awk '{print $1}' | xargs -I {} go get {}@latest 2>&1 | grep -E "upgraded|added" | tail -3 || true
  fi

  # 4. Tidy
  if ! go mod tidy 2>&1 | tail -3; then
    echo "  ⚠ tidy failed"
    FAILED+=("$sm")
    continue
  fi

  LINES=$(wc -l < go.mod | tr -d ' ')
  POLLUTED=$(grep -cE "(cellbuf|go-header|go-diskfs|golangci-lint/v2|osv-scanner|ginkgolinter|charmbracelet/x|denis-tingaikin)" go.mod 2>/dev/null || echo "0")
  POLLUTED=$(echo "$POLLUTED" | head -1 | tr -d ' ')
  echo "  → $LINES lines, polluted=$POLLUTED"

  if [ "$POLLUTED" -gt 0 ] 2>/dev/null; then
    FAILED+=("$sm (polluted=$POLLUTED)")
  fi
  cd "$ROOT"
done

echo ""
echo "==========="
echo "SUMMARY"
echo "==========="
echo "Migrated: $((${#SUBMODULES[@]} - ${#FAILED[@]}))/${#SUBMODULES[@]}"
if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo "Failed/polluted:"
  for f in "${FAILED[@]}"; do echo "  - $f"; done
  exit 1
fi
echo "All clean!"
