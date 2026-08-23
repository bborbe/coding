#!/usr/bin/env bash
# validate-citations.sh — citation validator for the doc-driven review pipeline.
#
# Input: a JSON file containing findings. Each finding resolves exactly one
# provenance, chosen by its `kind` field:
#   - kind == "rule"       → rule_id must resolve against rules/index.json
#   - kind == "invariant"  → invariant_id must resolve against invariants[].id
#                            in the security model at $SECURITY_MODEL_FILE
#   - kind == "toolchain"  → tool output (gosec/trivy/osv-scanner/vulncheck);
#                            kept without any id validation
#   - kind missing         → legacy path, treated as kind == "rule"
#   - any other kind       → dropped as unprovenanced
# Output: filtered JSON on stdout (findings with resolved provenance only);
#         dropped findings logged to stderr with their kind and offending id.
# Exit:   0 if every finding resolved;
#         1 if any finding was dropped (the offenders are still logged, so the
#           dispatcher can continue with the validated subset after capturing
#           the drift signal);
#         2 if rules/index.json is missing. A missing or unparseable security
#           model is the fail-closed drop path (exit 1), never exit 2.
#
# Usage:
#   bash scripts/validate-citations.sh findings.json > validated.json
#   SECURITY_MODEL_FILE=security-model.json bash scripts/validate-citations.sh findings.json > validated.json
#   bash scripts/validate-citations.sh < findings.json > validated.json
#
# Assumes the script is invoked from the coding repo root (or a clone with
# rules/index.json at the conventional path).

set -euo pipefail

INDEX_FILE="${INDEX_FILE:-rules/index.json}"
SECURITY_MODEL_FILE="${SECURITY_MODEL_FILE:-}"

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

python3 - "$INDEX_FILE" "$FINDINGS_FILE" "$SECURITY_MODEL_FILE" <<'PYEOF'
import json
import sys

index_path = sys.argv[1]
findings_path = sys.argv[2]
model_path = sys.argv[3]

with open(index_path) as f:
    index = json.load(f)
valid_ids = {r["id"] for r in index}

# Load the security model once, before the walk. Invariant ids come from
# invariants[].id. The model is "unavailable" when unset, missing, unreadable,
# or unparseable — invariant findings then fail closed (dropped with WARN),
# never kept and never a hard script failure (it is the exit-1 drop path).
model_invariant_ids = set()
model_available = False
if model_path:
    try:
        with open(model_path) as f:
            model = json.load(f)
        model_invariant_ids = {
            inv["id"] for inv in model.get("invariants", [])
            if isinstance(inv, dict) and inv.get("id")
        }
        model_available = True
    except (OSError, json.JSONDecodeError):
        model_available = False

with open(findings_path) as f:
    findings = json.load(f)

# Findings can be either a flat list or grouped by owner.
def walk(obj, parent_key=None):
    """Yield (parent_key, item_index, finding_dict) for every finding."""
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, dict) and (
                "kind" in item or "rule_id" in item or "invariant_id" in item
            ):
                yield (parent_key, i, item)
            else:
                yield from walk(item, parent_key)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, k)

valid_findings = []
dropped = []

for owner, idx, finding in walk(findings):
    kind = finding.get("kind") or "rule"
    if kind == "rule":
        rid = finding.get("rule_id")
        if rid in valid_ids:
            valid_findings.append({"owner": owner, **finding})
        else:
            dropped.append({"owner": owner, "kind": kind, "provenance_id": rid, "finding": finding})
    elif kind == "invariant":
        iid = finding.get("invariant_id")
        if model_available and iid in model_invariant_ids:
            valid_findings.append({"owner": owner, **finding})
        else:
            dropped.append({"owner": owner, "kind": kind, "provenance_id": iid, "finding": finding})
    elif kind == "toolchain":
        # Tool output (gosec/trivy/osv-scanner/vulncheck) — kept, no id.
        valid_findings.append({"owner": owner, **finding})
    else:
        dropped.append({"owner": owner, "kind": kind, "provenance_id": None, "finding": finding})

# Emit validated findings to stdout.
json.dump({"findings": valid_findings, "dropped_count": len(dropped)}, sys.stdout, indent=2)
print()

# Log drops to stderr.
if dropped:
    print(f"WARN: dropped {len(dropped)} finding(s) without a resolved provenance:", file=sys.stderr)
    for d in dropped:
        kind = d["kind"]
        pid = d["provenance_id"]
        if kind == "rule":
            print(f"  - owner={d['owner']} kind={kind} rule_id={pid!r}", file=sys.stderr)
        elif kind == "invariant":
            print(f"  - owner={d['owner']} kind={kind} invariant_id={pid!r}", file=sys.stderr)
        else:
            print(f"  - owner={d['owner']} kind={kind!r}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
PYEOF
