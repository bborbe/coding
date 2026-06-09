#!/usr/bin/env python3
#
# build-index.py — walks docs/*.md, extracts every ### RULE block, and emits
# rules/index.json (sorted, byte-stable, machine-readable).
#
# Exit semantics:
#   0  — index emitted successfully
#   1  — docs/ not found or empty, invalid rule ID, invalid level token,
#         missing required field, or duplicate rule ID
#
# Repo root is computed from the script's own location:
#   scripts/build-index.py  →  parent.parent == repo root
#
# No external dependencies — Python stdlib only (pathlib, json, re, sys).

import json
import pathlib
import re
import sys

# Regex for the ### RULE heading line
# Regex for the ### RULE heading line.
# Two or more slash-separated components: <lang>/<topic>[/<slug>]
RULE_HEADING_RE = re.compile(
    r"^### RULE\s+([a-z0-9-]+/[a-z0-9-]+(?:/[a-z0-9-]+)?)\s+\((MUST|SHOULD|MAY)\)$"
)

# Regex to detect any ### RULE heading line (valid or not)
ANY_RULE_LINE_RE = re.compile(r"^### RULE\s+")


def validate_rule_line(line: str, doc_path: str) -> None:
    """Check if a ### RULE line conforms to expected format. Exit on error."""
    if ANY_RULE_LINE_RE.match(line) and not RULE_HEADING_RE.match(line):
        # Extract the ID-like portion for the error message
        print(f"Invalid rule ID in {doc_path}: {line}", file=sys.stderr)
        sys.exit(1)

# Regex to extract field value from bold or plain "Field Name: value" lines
FIELD_RE = re.compile(r"^\*\*([A-Za-z ]+)\*\*:\s*(.+)$|^([A-Za-z ]+):\s*(.+)$")


def parse_fields(doc_path: str, rule_id: str, lines):
    """Extract Owner, Applies when, Enforcement, and optional Trigger from field lines.

    Returns a dict with keys: owner, applies_when, enforcement, and optionally trigger.
    Exits via sys.exit on missing required field.
    """
    result = {}
    for line in lines:
        m = FIELD_RE.match(line)
        if not m:
            # Non-field line (blank, code block, etc.) — stop parsing fields
            break
        # Bold form: **Key**: value
        if m.group(1):
            key = m.group(1).strip()
            value = m.group(2).strip()
        else:
            # Plain form: Key: value
            key = m.group(3).strip()
            value = m.group(4).strip()

        if key in ("Owner", "Applies when", "Enforcement", "Trigger"):
            result[key.lower().replace(" ", "_")] = value

    required = ["owner", "applies_when", "enforcement"]
    for field in required:
        if field not in result or not result[field]:
            print(
                f"Missing required field '{field}' in {doc_path} rule {rule_id}",
                file=sys.stderr,
            )
            sys.exit(1)

    return result


def derive_enforcement_type(enforcement: str) -> str:
    """Derive enforcement_type from the enforcement field value.

    mechanical — enforcement cites a rules/<lang>/<slug>.yml path
    script     — enforcement cites scripts/rule-checks.sh
    judgment   — anything else
    """
    if re.search(r"\brules/[a-z]+/[a-z0-9_-]+\.yml\b", enforcement):
        return "mechanical"
    if "scripts/rule-checks.sh" in enforcement:
        return "script"
    return "judgment"


def walk_docs(docs_dir: pathlib.Path) -> list[dict]:
    """Walk docs/*.md, extract every ### RULE block, return sorted entry list."""
    entries = []
    seen_ids = {}  # id -> doc_path

    for md_file in sorted(docs_dir.glob("*.md")):
        # Skip the schema documentation file itself
        if md_file.name == "rule-block-schema.md":
            continue
        doc_path = md_file.relative_to(docs_dir.parent)
        content = md_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        i = 0
        while i < len(lines):
            line = lines[i]
            # Validate any ### RULE line that doesn't match the valid pattern
            if ANY_RULE_LINE_RE.match(line):
                validate_rule_line(line, str(doc_path))
            m = RULE_HEADING_RE.match(line)
            if m:
                rule_id = m.group(1)
                level = m.group(2)

                # Collect lines immediately beneath the heading for field parsing
                field_lines = []
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    # Stop at a heading of same or higher level, or blank line followed by non-field
                    if next_line.startswith("#"):
                        break
                    if not next_line:
                        # Allow one blank; continue only if next is also blank or field
                        if not field_lines:
                            j += 1
                            continue
                        break
                    field_lines.append(lines[j])
                    j += 1

                fields = parse_fields(str(doc_path), rule_id, field_lines)

                enforcement_type = derive_enforcement_type(fields["enforcement"])

                entry = {
                    "id": rule_id,
                    "level": level,
                    "doc_path": str(doc_path),
                    "anchor": rule_id,  # verbatim, slashes preserved
                    "owner": fields["owner"],
                    "applies_when": fields["applies_when"],
                    "enforcement": fields["enforcement"],
                    "enforcement_type": enforcement_type,
                }

                # Parse optional Trigger field into a list of glob patterns
                if "trigger" in fields and fields["trigger"]:
                    raw_trigger = fields["trigger"]
                    trigger_list = [t.strip() for t in raw_trigger.split(",") if t.strip()]
                    if trigger_list:
                        entry["trigger"] = trigger_list

                # Check duplicate ID
                if rule_id in seen_ids:
                    print(
                        f"Duplicate rule ID '{rule_id}' found in: {seen_ids[rule_id]}, {doc_path}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

                seen_ids[rule_id] = str(doc_path)
                entries.append(entry)
            i += 1

    # Sort by id alphabetically
    entries.sort(key=lambda e: e["id"])
    return entries


def main():
    # Compute repo root: scripts/build-index.py → parent.parent
    script_path = pathlib.Path(__file__).resolve()
    repo_root = script_path.parent.parent
    docs_dir = repo_root / "docs"

    if not docs_dir.is_dir():
        print("docs/ directory not found or empty", file=sys.stderr)
        sys.exit(1)

    md_files = list(docs_dir.glob("*.md"))
    if not md_files:
        print("docs/ directory not found or empty", file=sys.stderr)
        sys.exit(1)

    entries = walk_docs(docs_dir)

    json.dump(
        entries,
        sys.stdout,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"build-index: {e}", file=sys.stderr)
        sys.exit(1)
