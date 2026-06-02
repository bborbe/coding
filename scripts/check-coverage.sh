#!/usr/bin/env bash
# check-coverage.sh — coverage lint for the doc-driven rule base.
#
# Fails if any of:
#   1. A rule's `enforcement` field cites a path like rules/<lang>/<file>.yml
#      but that file does not exist on disk.
#   2. An ast-grep YAML file exists in rules/<lang>/ but no rule in
#      rules/index.json references it (orphan YAML — possibly a leftover
#      after a rule was renamed or removed).
#   3. A YAML's `id:` field does not match any rule_id in rules/index.json
#      (rule was renamed in the doc but the YAML still has the old id).
#
# Run via `make check-coverage` or directly. Same exit-on-failure shape as
# scripts/check-versions.sh and the precommit-wired check-index target
# (PR #13).
#
# Run from repo root.

set -euo pipefail

INDEX_FILE="${INDEX_FILE:-rules/index.json}"
RULES_DIR="${RULES_DIR:-rules}"

if [[ ! -f "$INDEX_FILE" ]]; then
  echo "ERROR: $INDEX_FILE not found. Run from repo root." >&2
  exit 2
fi

python3 - "$INDEX_FILE" "$RULES_DIR" <<'PYEOF'
import json
import pathlib
import re
import sys

index_path = pathlib.Path(sys.argv[1])
rules_dir  = pathlib.Path(sys.argv[2])

with open(index_path) as f:
    index = json.load(f)

# 1. Index entries' enforcement paths must resolve to existing files.
missing_files = []
for r in index:
    enf = r.get("enforcement", "")
    # Strip backticks the schema sometimes wraps paths in.
    enf_clean = enf.strip("` ")
    # Pull out the rules/... .yml path if present (judgment-only entries skip).
    m = re.search(r"(rules/[a-z0-9_-]+/[a-z0-9_-]+\.yml)", enf_clean)
    if not m:
        continue
    p = pathlib.Path(m.group(1))
    if not p.exists():
        missing_files.append((r["id"], str(p)))

# 2. Every YAML in rules/<lang>/ must be referenced by exactly one index entry.
ref_paths = set()
for r in index:
    enf = r.get("enforcement", "").strip("` ")
    m = re.search(r"(rules/[a-z0-9_-]+/[a-z0-9_-]+\.yml)", enf)
    if m:
        ref_paths.add(pathlib.Path(m.group(1)))

orphan_yamls = []
for p in sorted(rules_dir.rglob("*.yml")):
    if p.name == "index.json":
        continue
    if p not in ref_paths:
        orphan_yamls.append(str(p))

# 3. YAML id: field must match an index entry's id.
valid_ids = {r["id"] for r in index}
id_mismatches = []
for p in sorted(rules_dir.rglob("*.yml")):
    try:
        with open(p) as f:
            for line in f:
                if line.startswith("id:"):
                    yaml_id = line.split(":", 1)[1].strip()
                    if yaml_id not in valid_ids:
                        id_mismatches.append((str(p), yaml_id))
                    break
    except OSError:
        continue

# Report.
fail = False
if missing_files:
    fail = True
    print("ERROR: index entries cite ast-grep files that do not exist:", file=sys.stderr)
    for rid, path in missing_files:
        print(f"  - rule {rid!r} enforcement -> {path!r} (not found)", file=sys.stderr)

if orphan_yamls:
    fail = True
    print("ERROR: orphan ast-grep YAMLs not referenced by any index entry:", file=sys.stderr)
    for path in orphan_yamls:
        print(f"  - {path}", file=sys.stderr)

if id_mismatches:
    fail = True
    print("ERROR: YAML 'id:' fields not in rules/index.json (rule rename drift?):", file=sys.stderr)
    for path, yaml_id in id_mismatches:
        print(f"  - {path}: id={yaml_id!r}", file=sys.stderr)

if fail:
    print(f"\ncheck-coverage: FAILED (run from repo root, re-run after fixing)", file=sys.stderr)
    sys.exit(1)

print(f"check-coverage: OK ({len(index)} rules, {len(ref_paths)} mechanical YAMLs, no drift)")
PYEOF
