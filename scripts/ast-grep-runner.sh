#!/usr/bin/env bash
# scripts/ast-grep-runner.sh — deterministic mechanical funnel runner.
#
# Runs all ast-grep YAMLs listed in rules/index.json against TARGET_DIR,
# groups findings by owner, then runs scripts/rule-checks.sh (script-tier
# checks) and merges the results.  Emits a single JSON object to stdout:
#
#   {
#     "stats":  { "yamls_run": N, "findings_count": N, "elapsed_ms": N },
#     "findings_by_owner": { "<owner>": [ {finding}, ... ] },
#     "errors": [ {kind, detail, ...} ]
#   }
#
# Usage:
#   scripts/ast-grep-runner.sh <target-dir> [changed-file ...]
#
# When changed files are given only those files are scanned (diff-scope).
# Paths may be relative to target-dir or absolute.
#
# Exit codes:
#   0  — ran (findings may be non-empty)
#   2  — ast-grep binary missing
#
# Requires: ast-grep (sg), jq on PATH.
# bash 3.2 compatible (macOS); shellcheck-clean.

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Preflight — ast-grep binary
# ---------------------------------------------------------------------------
AGBIN=""
if command -v ast-grep >/dev/null 2>&1; then
  AGBIN="ast-grep"
elif command -v sg >/dev/null 2>&1; then
  AGBIN="sg"
else
  printf '{"stats":{"yamls_run":0,"findings_count":0,"elapsed_ms":0},"findings_by_owner":{},"errors":[{"kind":"missing-tool","tool":"ast-grep","detail":"ast-grep / sg binary not in PATH — install via: npm install -g @ast-grep/cli | brew install ast-grep"}]}\n'
  exit 2
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

usage() {
  printf 'usage: %s <target-dir> [changed-file ...]\n' "$0" >&2
  exit 2
}

[ "$#" -lt 1 ] && usage

TARGET_DIR="$1"
shift

if [ ! -d "$TARGET_DIR" ]; then
  printf 'error: target not found or not a directory: %s\n' "$TARGET_DIR" >&2
  exit 2
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

# Normalise changed files: make absolute, resolve relative-to-target
CHANGED_FILES=()
for f in "$@"; do
  case "$f" in
    /*) CHANGED_FILES+=("$f") ;;
    *)  CHANGED_FILES+=("$TARGET_DIR/$f") ;;
  esac
done

START_MS=$(python3 -c 'import time; print(int(time.time()*1000))')

# Temporary workspace for collected data (bash 3.2: no associative arrays)
TMPDIR_WORK="$(mktemp -d)"
# shellcheck disable=SC2064
trap 'rm -rf "$TMPDIR_WORK"' EXIT

FINDINGS_DIR="$TMPDIR_WORK/findings"   # one file per owner
ERRORS_FILE="$TMPDIR_WORK/errors.json"
mkdir -p "$FINDINGS_DIR"
printf '[]' > "$ERRORS_FILE"

YAMLS_RUN=0
FINDINGS_COUNT=0

# ---------------------------------------------------------------------------
# append_error <kind> <json-kv-pairs…>
#   e.g. append_error "missing-yaml" '"rule_id":"x","path":"y"'
# ---------------------------------------------------------------------------
append_error() {
  local kind="$1"; shift
  local kvs="${1:-}"
  local entry
  if [ -n "$kvs" ]; then
    entry="{\"kind\":$(jq -n --arg v "$kind" '$v'),${kvs}}"
  else
    entry="{\"kind\":$(jq -n --arg v "$kind" '$v')}"
  fi
  local cur
  cur="$(cat "$ERRORS_FILE")"
  printf '%s' "$cur" | jq --argjson e "$entry" '. + [$e]' > "$ERRORS_FILE.tmp" && mv "$ERRORS_FILE.tmp" "$ERRORS_FILE"
}

# ---------------------------------------------------------------------------
# append_finding <owner> <finding-json>
# ---------------------------------------------------------------------------
append_finding() {
  local owner="$1"
  local finding="$2"
  local owner_slug
  owner_slug="$(printf '%s' "$owner" | tr '/' '_')"
  local owner_file="$FINDINGS_DIR/${owner_slug}.jsonl"
  printf '%s\n' "$finding" >> "$owner_file"
  FINDINGS_COUNT=$((FINDINGS_COUNT + 1))
}

# ---------------------------------------------------------------------------
# 1. Collect mechanical-rule inventory from index.json
#    Fields per line (tab-separated): rule_id \t yml_path \t owner \t level
# ---------------------------------------------------------------------------
INDEX_FILE="$ROOT/rules/index.json"
if [ ! -f "$INDEX_FILE" ]; then
  printf 'error: rules/index.json not found at %s\n' "$INDEX_FILE" >&2
  exit 2
fi

INVENTORY_FILE="$TMPDIR_WORK/inventory.tsv"
jq -r '.[] | select(.enforcement | test("rules/[a-z0-9_-]+/[a-z0-9_-]+\\.yml"; "")) |
  [ .id,
    ( .enforcement | capture("(?<p>rules/[a-z0-9_-]+/[a-z0-9_-]+\\.yml)") | .p ),
    .owner,
    .level
  ] | @tsv' "$INDEX_FILE" > "$INVENTORY_FILE"

# ---------------------------------------------------------------------------
# 2. Run ast-grep per YAML
# ---------------------------------------------------------------------------
while IFS=$'\t' read -r rule_id yml_rel owner level; do
  yml_path="$ROOT/$yml_rel"
  if [ ! -f "$yml_path" ]; then
    append_error "missing-yaml" "\"rule_id\":$(jq -n --arg v "$rule_id" '$v'),\"path\":$(jq -n --arg v "$yml_rel" '$v')"
    continue
  fi

  # Build scan target: either the changed-file list or the whole target dir
  SCAN_OUT="$TMPDIR_WORK/scan_$$.json"
  SCAN_ERR="$TMPDIR_WORK/scan_err_$$"
  if [ "${#CHANGED_FILES[@]}" -gt 0 ]; then
    # Pass only the changed files (filter to existing ones)
    EXIST_FILES=()
    for f in "${CHANGED_FILES[@]}"; do
      [ -f "$f" ] && EXIST_FILES+=("$f")
    done
    if [ "${#EXIST_FILES[@]}" -eq 0 ]; then
      YAMLS_RUN=$((YAMLS_RUN + 1))
      continue
    fi
    "$AGBIN" scan --rule "$yml_path" --json=stream "${EXIST_FILES[@]}" > "$SCAN_OUT" 2>"$SCAN_ERR" || true
  else
    "$AGBIN" scan --rule "$yml_path" --json=stream "$TARGET_DIR" > "$SCAN_OUT" 2>"$SCAN_ERR" || true
  fi

  YAMLS_RUN=$((YAMLS_RUN + 1))

  # ast-grep exits 1 both for "found error-severity findings" (normal) and for
  # genuine YAML parse errors.  Distinguish by checking stderr for the parse-
  # error string.  If stdout is empty AND stderr has "Cannot parse rule", that's
  # a real error; otherwise findings were found (or nothing was found).
  if grep -q "Cannot parse rule\|invalid rule\|failed to parse" "$SCAN_ERR" 2>/dev/null; then
    err_msg="$(cat "$SCAN_ERR")"
    append_error "scan-error" "\"rule_id\":$(jq -n --arg v "$rule_id" '$v'),\"detail\":$(jq -n --arg v "$err_msg" '$v')"
    rm -f "$SCAN_OUT" "$SCAN_ERR"
    continue
  fi
  rm -f "$SCAN_ERR"

  # Parse stream output: each match is a JSON object on its own line
  if [ -s "$SCAN_OUT" ]; then
    while IFS= read -r match_line; do
      [ -z "$match_line" ] && continue
      # Extract fields from the stream match object
      file=$(printf '%s' "$match_line" | jq -r '.file // ""')
      line=$(printf '%s' "$match_line" | jq -r '.range.start.line // 0')
      column=$(printf '%s' "$match_line" | jq -r '.range.start.column // 0')
      matched_text=$(printf '%s' "$match_line" | jq -r '.text // ""')
      message=$(printf '%s' "$match_line" | jq -r '.message // ""')

      finding=$(jq -n \
        --arg rule_id "$rule_id" \
        --arg rule_level "$level" \
        --arg file "$file" \
        --argjson line "$line" \
        --argjson column "$column" \
        --arg matched_text "$matched_text" \
        --arg message "$message" \
        '{rule_id:$rule_id, rule_level:$rule_level, file:$file, line:$line, column:$column, matched_text:$matched_text, message:$message}')
      append_finding "$owner" "$finding"
    done < "$SCAN_OUT"
  fi
  rm -f "$SCAN_OUT"

done < "$INVENTORY_FILE"

# ---------------------------------------------------------------------------
# 3. Run script-tier checks (rule-checks.sh) and merge findings
# ---------------------------------------------------------------------------
RULE_CHECKS="$ROOT/scripts/rule-checks.sh"
if [ -f "$RULE_CHECKS" ] && [ -x "$RULE_CHECKS" ]; then
  RC_OUT="$TMPDIR_WORK/rule-checks-out.json"
  if "$RULE_CHECKS" "$TARGET_DIR" "$@" > "$RC_OUT" 2>/dev/null; then
    # Merge findings_by_owner from rule-checks output
    if [ -s "$RC_OUT" ] && jq -e '.findings_by_owner' "$RC_OUT" >/dev/null 2>&1; then
      while IFS= read -r owner; do
        while IFS= read -r finding; do
          [ -z "$finding" ] && continue
          append_finding "$owner" "$finding"
        done < <(jq -r --arg o "$owner" '.findings_by_owner[$o][] | tojson' "$RC_OUT" 2>/dev/null || true)
      done < <(jq -r '.findings_by_owner | keys[]' "$RC_OUT" 2>/dev/null || true)

      # Merge errors[]
      while IFS= read -r err; do
        [ -z "$err" ] && continue
        local_cur
        local_cur="$(cat "$ERRORS_FILE")"
        printf '%s' "$local_cur" | jq --argjson e "$err" '. + [$e]' > "$ERRORS_FILE.tmp" && mv "$ERRORS_FILE.tmp" "$ERRORS_FILE"
      done < <(jq -r '.errors[] | tojson' "$RC_OUT" 2>/dev/null || true)
    fi
  else
    rc_stderr="$(cat "$RC_OUT" 2>/dev/null || true)"
    append_error "rule-checks-error" "\"detail\":$(jq -n --arg v "$rc_stderr" '$v')"
  fi
fi

# ---------------------------------------------------------------------------
# 4. Assemble final JSON
# ---------------------------------------------------------------------------
END_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
ELAPSED=$((END_MS - START_MS))

# Build findings_by_owner from per-owner .jsonl files
FINDINGS_JSON="$TMPDIR_WORK/findings_by_owner.json"
printf '{}' > "$FINDINGS_JSON"

for owner_file in "$FINDINGS_DIR"/*.jsonl; do
  [ -f "$owner_file" ] || continue
  # Derive owner name from filename (reverse the tr '/' '_' substitution isn't reversible,
  # but owner names use '-' not '/', so the original name is preserved)
  basename_no_ext="$(basename "$owner_file" .jsonl)"
  owner_name="$basename_no_ext"
  # Collect all findings for this owner into a JSON array
  findings_array=$(jq -s '.' "$owner_file")
  FINDINGS_JSON_TMP="$TMPDIR_WORK/fbo_tmp.json"
  jq --arg o "$owner_name" --argjson arr "$findings_array" \
    '. + {($o): $arr}' "$FINDINGS_JSON" > "$FINDINGS_JSON_TMP" && mv "$FINDINGS_JSON_TMP" "$FINDINGS_JSON"
done

ERRORS_JSON="$(cat "$ERRORS_FILE")"
FINDINGS_OBJ="$(cat "$FINDINGS_JSON")"

jq -n \
  --argjson yamls_run "$YAMLS_RUN" \
  --argjson findings_count "$FINDINGS_COUNT" \
  --argjson elapsed_ms "$ELAPSED" \
  --argjson findings_by_owner "$FINDINGS_OBJ" \
  --argjson errors "$ERRORS_JSON" \
  '{stats:{yamls_run:$yamls_run, findings_count:$findings_count, elapsed_ms:$elapsed_ms}, findings_by_owner:$findings_by_owner, errors:$errors}'
