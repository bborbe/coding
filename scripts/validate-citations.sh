#!/usr/bin/env bash
# validate-citations.sh — citation validator for the doc-driven review pipeline.
#
# Input: a JSON file containing findings with a `rule_id` field per finding.
# Output: filtered JSON on stdout (findings with valid rule_ids only);
#         dropped findings logged to stderr with their offending rule_ids.
# Exit:   0 if every finding's rule_id resolved against rules/index.json;
#         1 if any finding had a missing rule_id (the offenders are still
#           logged, so the dispatcher can continue with the validated subset
#           after capturing the drift signal).
#
# Usage:
#   bash scripts/validate-citations.sh findings.json > validated.json
#   bash scripts/validate-citations.sh < findings.json > validated.json
#
# Assumes the script is invoked from the coding repo root (or a clone with
# rules/index.json at the conventional path).

set -euo pipefail

INDEX_FILE="${INDEX_FILE:-rules/index.json}"

if [[ ! -f "$INDEX_FILE" ]]; then
  echo "ERROR: $INDEX_FILE not found. Run from repo root." >&2
  exit 2
fi

# If a path arg was given, read from it; otherwise buffer stdin to a tmp file
# so the heredoc-fed python sees the findings, not its own script body.
if [[ $# -ge 1 && -f "$1" ]]; then
  FINDINGS_FILE="$1"
else
  FINDINGS_FILE="$(mktemp)"
  trap 'rm -f "$FINDINGS_FILE"' EXIT
  cat > "$FINDINGS_FILE"
fi

python3 - "$INDEX_FILE" "$FINDINGS_FILE" <<'PYEOF'
import json
import sys

index_path = sys.argv[1]
findings_path = sys.argv[2]

with open(index_path) as f:
    index = json.load(f)
valid_ids = {r["id"] for r in index}

with open(findings_path) as f:
    findings = json.load(f)

# Findings can be either a flat list or grouped by owner.
def walk(obj, parent_key=None):
    """Yield (parent_key, item_index, finding_dict) for every finding."""
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, dict) and "rule_id" in item:
                yield (parent_key, i, item)
            else:
                yield from walk(item, parent_key)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, k)

valid_findings = []
dropped = []

for owner, idx, finding in walk(findings):
    rid = finding.get("rule_id")
    if rid in valid_ids:
        valid_findings.append({"owner": owner, **finding})
    else:
        dropped.append({"owner": owner, "rule_id": rid, "finding": finding})

# Emit validated findings to stdout.
json.dump({"findings": valid_findings, "dropped_count": len(dropped)}, sys.stdout, indent=2)
print()

# Log drops to stderr.
if dropped:
    print(f"WARN: dropped {len(dropped)} finding(s) with missing rule_id:", file=sys.stderr)
    for d in dropped:
        print(f"  - owner={d['owner']} rule_id={d['rule_id']!r}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
PYEOF
