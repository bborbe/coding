#!/usr/bin/env bash
# scripts/rule-checks.sh — script-tier ("bucket 2") mechanical checks.
#
# Rules that are file-existence / file-presence / file-layout / grep checks —
# no AST and no LLM needed.  Invoked by scripts/ast-grep-runner.sh and merged
# into the same JSON result, but can also be run standalone for debugging.
#
# Usage:
#   scripts/rule-checks.sh <target-dir> [changed-file ...]
#
# When changed files are given, only rules whose subject matter intersects
# the changed files are run (e.g. CHANGELOG rules only when CHANGELOG.md
# changed; LICENSE always checked since it's cheap).
#
# Output: same JSON contract as ast-grep-runner.sh:
#   {
#     "stats":  { "yamls_run": 0, "findings_count": N, "elapsed_ms": N },
#     "findings_by_owner": { "<owner>": [ {finding}, ... ] },
#     "errors": []
#   }
#
# Exit codes: always 0 (findings are in the JSON, not the exit code).
# bash 3.2 compatible (macOS); shellcheck-clean.

set -euo pipefail

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

# Normalise changed files to absolute paths
CHANGED_FILES=()
for f in "$@"; do
  case "$f" in
    /*) CHANGED_FILES+=("$f") ;;
    *)  CHANGED_FILES+=("$TARGET_DIR/$f") ;;
  esac
done

START_MS=$(python3 -c 'import time; print(int(time.time()*1000))')

TMPDIR_WORK="$(mktemp -d)"
# shellcheck disable=SC2064
trap 'rm -rf "$TMPDIR_WORK"' EXIT

FINDINGS_FILE="$TMPDIR_WORK/findings.jsonl"
touch "$FINDINGS_FILE"

FINDINGS_COUNT=0

# ---------------------------------------------------------------------------
# Helper: emit_finding <owner> <rule_id> <level> <file> <line> <col> <text> <msg>
# ---------------------------------------------------------------------------
emit_finding() {
  local owner="$1" rule_id="$2" level="$3" file="$4"
  local line="${5:-0}" col="${6:-0}" text="$7" msg="$8"
  jq -cn \
    --arg owner "$owner" \
    --arg rule_id "$rule_id" \
    --arg rule_level "$level" \
    --arg file "$file" \
    --argjson line "$line" \
    --argjson column "$col" \
    --arg matched_text "$text" \
    --arg message "$msg" \
    '{owner:$owner, rule_id:$rule_id, rule_level:$rule_level, file:$file, line:$line, column:$column, matched_text:$matched_text, message:$message}' \
    >> "$FINDINGS_FILE"
  FINDINGS_COUNT=$((FINDINGS_COUNT + 1))
}

# ---------------------------------------------------------------------------
# changed_file_matches <pattern> — returns 0 if any changed file matches the
# glob pattern (bash pattern, not regex), or if no changed-file filter was set.
# ---------------------------------------------------------------------------
changed_file_matches() {
  local pattern="$1"
  if [ "${#CHANGED_FILES[@]}" -eq 0 ]; then
    return 0  # no filter → always run
  fi
  local f
  for f in "${CHANGED_FILES[@]}"; do
    # shellcheck disable=SC2254
    case "$f" in
      $pattern) return 0 ;;
    esac
  done
  return 1
}

# ---------------------------------------------------------------------------
# RULE: go-licensing/license-file-required (MUST)
# Always run (cheap, applies to any Go project).
# ---------------------------------------------------------------------------
check_license_file_required() {
  local license_file="$TARGET_DIR/LICENSE"
  if [ ! -f "$license_file" ]; then
    emit_finding \
      "license-assistant" \
      "go-licensing/license-file-required" \
      "MUST" \
      "$TARGET_DIR/LICENSE" \
      0 0 \
      "(file absent)" \
      "No LICENSE file found at repo root. Public Go projects must have a root LICENSE file. See docs/go-licensing-guide.md."
  fi
}

# ---------------------------------------------------------------------------
# RULE: go-licensing/readme-license-section-required (MUST)
# Run when README.md changed, or always (cheap grep).
# ---------------------------------------------------------------------------
check_readme_license_section() {
  changed_file_matches "*README.md" || return 0
  local readme="$TARGET_DIR/README.md"
  if [ ! -f "$readme" ]; then
    return 0  # no README — different issue, not this rule
  fi
  if ! grep -qE '^## License' "$readme"; then
    local line
    line=$(wc -l < "$readme")
    emit_finding \
      "license-assistant" \
      "go-licensing/readme-license-section-required" \
      "MUST" \
      "$readme" \
      "$line" 0 \
      "(section absent)" \
      "README.md has no '## License' section. Add a License H2 section pointing at the root LICENSE file. See docs/go-licensing-guide.md."
  fi
}

# ---------------------------------------------------------------------------
# RULE: changelog/preamble-frozen (MUST)
# Run when CHANGELOG.md changed, or always.
# ---------------------------------------------------------------------------
check_changelog_preamble_frozen() {
  changed_file_matches "*CHANGELOG.md" || return 0
  local cl="$TARGET_DIR/CHANGELOG.md"
  [ -f "$cl" ] || return 0

  # The canonical preamble: first non-blank line must be "# Changelog"
  local first_content
  first_content=$(grep -m1 -v '^[[:space:]]*$' "$cl" || true)
  if [ "$first_content" != "# Changelog" ]; then
    emit_finding \
      "agent-auditor" \
      "changelog/preamble-frozen" \
      "MUST" \
      "$cl" \
      1 0 \
      "$first_content" \
      "CHANGELOG.md does not start with '# Changelog'. The preamble header must be the first content. See docs/changelog-guide.md."
    return 0
  fi

  # No ## Unreleased / ## vX.Y.Z should appear BEFORE the first ## heading that
  # follows the preamble block.  The preamble ends at the first ## heading.
  # Violation: a ## Unreleased appears before "All notable changes" line.
  local found_notable=0
  local lineno=0
  # shellcheck disable=SC2094  # $cl is passed as a string arg to emit_finding, not redirected into
  while IFS= read -r raw_line; do
    lineno=$((lineno + 1))
    case "$raw_line" in
      "All notable changes"*) found_notable=1 ;;
      "## Unreleased"*|"## v"[0-9]*)
        if [ "$found_notable" -eq 0 ]; then
          emit_finding \
            "agent-auditor" \
            "changelog/preamble-frozen" \
            "MUST" \
            "$cl" \
            "$lineno" 0 \
            "$raw_line" \
            "Section '$raw_line' appears before the canonical preamble block ('All notable changes...'). See docs/changelog-guide.md."
        fi
        ;;
    esac
  done < "$cl"
}

# ---------------------------------------------------------------------------
# RULE: changelog/unreleased-entry-required (SHOULD)
# Deterministic state-check: a source-changing PR in a repo that HAS a
# CHANGELOG.md must leave a `- ` bullet under `## Unreleased` (else the
# autoRelease agent has nothing to promote post-merge). Diff-scoped only.
# ---------------------------------------------------------------------------
check_changelog_unreleased_entry_required() {
  # Diff-scoped only — needs the PR's changed-file set to attribute the change.
  # A whole-repo run (no changed-file filter) would flag every repo mid-cycle
  # whose ## Unreleased is legitimately empty, so skip when unfiltered.
  [ "${#CHANGED_FILES[@]}" -gt 0 ] || return 0

  local cl="$TARGET_DIR/CHANGELOG.md"
  [ -f "$cl" ] || return 0  # repo has no CHANGELOG → rule N/A

  # Require at least one non-vendored changed file (something shippable).
  local shippable=0 f
  for f in "${CHANGED_FILES[@]}"; do
    case "$f" in
      */vendor/*|*/node_modules/*) ;;
      *) shippable=1 ;;
    esac
  done
  [ "$shippable" -eq 1 ] || return 0

  # Does the PR-HEAD CHANGELOG have a non-empty `## Unreleased` section?
  # Scan from the `## Unreleased` heading to the next `## ` heading for a
  # list bullet (`- ` or `* `).
  local has_bullet
  has_bullet=$(awk '
    /^## Unreleased[[:space:]]*$/ { inblk=1; next }
    inblk && /^## / { inblk=0 }
    inblk && /^[[:space:]]*[-*][[:space:]]/ { print "yes"; exit }
  ' "$cl")
  if [ "$has_bullet" = "yes" ]; then
    return 0  # PASS — an Unreleased bullet is present
  fi

  # FLAG — anchor at the `## Unreleased` line if present, else line 1.
  local uline
  uline=$(grep -nE '^## Unreleased' "$cl" 2>/dev/null | head -1 | cut -d: -f1 || true)
  emit_finding \
    "agent-auditor" \
    "changelog/unreleased-entry-required" \
    "SHOULD" \
    "$cl" \
    "${uline:-1}" 0 \
    "(no ## Unreleased bullet)" \
    "PR changes source but CHANGELOG.md has no '## Unreleased' bullet. In an autoRelease repo the release agent promotes '## Unreleased' post-merge; with none, no version ships. Add a conventional-prefixed bullet under '## Unreleased'. See docs/changelog-guide.md."
}

# ---------------------------------------------------------------------------
# RULE: git-commit/subject-under-50-chars (SHOULD)
# Run when .git exists (PR scan context).
# ---------------------------------------------------------------------------
check_git_subject_length() {
  changed_file_matches "*" || return 0  # git rules: always run if filter active
  local git_dir="$TARGET_DIR/.git"
  [ -d "$git_dir" ] || return 0

  local violations
  violations=$(git -C "$TARGET_DIR" log --format='%s' HEAD~10..HEAD 2>/dev/null | \
    awk '{ if (length($0) > 50) print NR": "length($0)" chars: "$0 }' || true)
  if [ -n "$violations" ]; then
    while IFS= read -r violation; do
      emit_finding \
        "agent-auditor" \
        "git-commit/subject-under-50-chars" \
        "SHOULD" \
        "$TARGET_DIR/.git/COMMIT_EDITMSG" \
        0 0 \
        "$violation" \
        "Commit subject exceeds 50 characters. See docs/git-commit-guide.md."
    done <<< "$violations"
  fi
}

# ---------------------------------------------------------------------------
# RULE: git-workflow/no-ai-attribution-in-commits (MUST)
# Run when .git exists.
# ---------------------------------------------------------------------------
check_no_ai_attribution() {
  changed_file_matches "*" || return 0
  local git_dir="$TARGET_DIR/.git"
  [ -d "$git_dir" ] || return 0

  local pattern='Co-Authored-By: Claude\|Generated with Claude Code\|Co-Authored-By: GitHub Copilot\|Co-Authored-By: Copilot'
  local hits
  hits=$(git -C "$TARGET_DIR" log --format='%B' HEAD~10..HEAD 2>/dev/null | \
    grep -n "$pattern" || true)
  if [ -n "$hits" ]; then
    while IFS= read -r hit; do
      emit_finding \
        "agent-auditor" \
        "git-workflow/no-ai-attribution-in-commits" \
        "MUST" \
        "$TARGET_DIR/.git/COMMIT_EDITMSG" \
        0 0 \
        "$hit" \
        "AI attribution found in commit message. Remove 'Co-Authored-By: Claude' / 'Generated with Claude Code' lines. See docs/git-workflow.md."
    done <<< "$hits"
  fi
}

# ---------------------------------------------------------------------------
# RULE: go-library/semver-vprefix-tag-required (MUST)
# Run when .git exists.
# ---------------------------------------------------------------------------
check_semver_tag() {
  changed_file_matches "*" || return 0
  local git_dir="$TARGET_DIR/.git"
  [ -d "$git_dir" ] || return 0

  # Check if there are ANY tags at all; if none, that's a violation.
  local tags
  tags=$(git -C "$TARGET_DIR" tag --list 2>/dev/null || true)
  if [ -z "$tags" ]; then
    emit_finding \
      "go-quality-assistant" \
      "go-library/semver-vprefix-tag-required" \
      "MUST" \
      "$TARGET_DIR" \
      0 0 \
      "(no tags)" \
      "No git tags found. Go library releases must use vMAJOR.MINOR.PATCH tags. See docs/go-library-guide.md."
    return 0
  fi

  # Check if any tag matches the semver-with-v-prefix pattern
  if ! git -C "$TARGET_DIR" tag --list 2>/dev/null | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    local first_bad
    first_bad=$(git -C "$TARGET_DIR" tag --list 2>/dev/null | head -1)
    emit_finding \
      "go-quality-assistant" \
      "go-library/semver-vprefix-tag-required" \
      "MUST" \
      "$TARGET_DIR" \
      0 0 \
      "$first_bad" \
      "No vMAJOR.MINOR.PATCH tag found. All release tags must start with 'v'. See docs/go-library-guide.md."
  fi
}

# ---------------------------------------------------------------------------
# RULE: go-tools-versioning/no-tools-go-for-clis (MUST)
# Run when tools.go or go.mod changed, or always (cheap grep).
# ---------------------------------------------------------------------------
check_no_tools_go_for_clis() {
  changed_file_matches "*tools.go*" || changed_file_matches "*go.mod" || \
    { [ "${#CHANGED_FILES[@]}" -eq 0 ]; } || return 0

  # Search recursively for tools.go files with the build tag + CLI imports
  while IFS= read -r tools_go; do
    if grep -q '//go:build tools' "$tools_go" 2>/dev/null; then
      # Check if it imports CLI tool packages (cmd/ path or known CLI tools)
      if grep -qE '_ "(github\.com/golangci|github\.com/google/osv-scanner|github\.com/maxbrunsfeld/counterfeiter|github\.com/securego/gosec|honnef\.co/go/tools)' "$tools_go" 2>/dev/null; then
        local line
        line=$(grep -n '//go:build tools' "$tools_go" | head -1 | cut -d: -f1)
        local evidence
        evidence=$(grep -E '_ "(github\.com/golangci|github\.com/google/osv-scanner|github\.com/maxbrunsfeld/counterfeiter|github\.com/securego/gosec|honnef\.co/go/tools)' "$tools_go" | head -1)
        emit_finding \
          "go-quality-assistant" \
          "go-tools-versioning/no-tools-go-for-clis" \
          "MUST" \
          "$tools_go" \
          "${line:-1}" 0 \
          "$evidence" \
          "tools.go with CLI tool imports found. Use tools.env + Makefile @version instead. See docs/go-tools-versioning-guide.md."
      fi
    fi
  done < <(find "$TARGET_DIR" -name "tools.go" -not -path "*/vendor/*" 2>/dev/null || true)
}

# ---------------------------------------------------------------------------
# RULE: go-mod-replace/no-cross-repo-replace (MUST)
# Run when go.mod changed, or scan all go.mod files.
# ---------------------------------------------------------------------------
check_no_cross_repo_replace() {
  changed_file_matches "*go.mod" || { [ "${#CHANGED_FILES[@]}" -eq 0 ]; } || return 0

  while IFS= read -r gomod; do
    local gomod_dir
    gomod_dir="$(dirname "$gomod")"
    local lineno=0
    # shellcheck disable=SC2094  # $gomod passed as a string arg to emit_finding, not redirected into
    while IFS= read -r raw; do
      lineno=$((lineno + 1))
      # Match: replace <module> => <rhs>
      # RHS that escapes the repo: absolute path (/...) or ../../ that climbs above gomod_dir
      case "$raw" in
        *"replace "*)
          # Extract the RHS after "=>"
          local rhs
          rhs=$(printf '%s' "$raw" | sed 's/.*=> *//')
          rhs=$(printf '%s' "$rhs" | sed 's/[[:space:]].*//')  # strip version if present
          case "$rhs" in
            /*)
              # Absolute path — always cross-repo
              emit_finding \
                "go-quality-assistant" \
                "go-mod-replace/no-cross-repo-replace" \
                "MUST" \
                "$gomod" \
                "$lineno" 0 \
                "$raw" \
                "go.mod replace with absolute path '$rhs' — breaks all non-local builds. Use a released version instead. See docs/go-mod-replace-guide.md."
              ;;
            ../*)
              # Relative path — check if it escapes the gomod_dir / TARGET_DIR
              # Normalise: resolve the path relative to gomod_dir
              local resolved
              resolved="$(cd "$gomod_dir" && cd "$rhs" 2>/dev/null && pwd || true)"
              if [ -n "$resolved" ]; then
                # If resolved path is NOT inside TARGET_DIR, it's cross-repo
                case "$resolved" in
                  "$TARGET_DIR"*) ;;  # inside repo — OK
                  *)
                    emit_finding \
                      "go-quality-assistant" \
                      "go-mod-replace/no-cross-repo-replace" \
                      "MUST" \
                      "$gomod" \
                      "$lineno" 0 \
                      "$raw" \
                      "go.mod replace '$rhs' escapes the repo root — breaks non-local builds. Use a released version. See docs/go-mod-replace-guide.md."
                    ;;
                esac
              else
                # Path doesn't exist — flag it (points to a non-existent location)
                emit_finding \
                  "go-quality-assistant" \
                  "go-mod-replace/no-cross-repo-replace" \
                  "MUST" \
                  "$gomod" \
                  "$lineno" 0 \
                  "$raw" \
                  "go.mod replace '$rhs' points to a path that does not exist — likely cross-repo. See docs/go-mod-replace-guide.md."
              fi
              ;;
          esac
          ;;
      esac
    done < "$gomod"
  done < <(find "$TARGET_DIR" -name "go.mod" -not -path "*/vendor/*" 2>/dev/null || true)
}

# ---------------------------------------------------------------------------
# RULE: python-project-structure/src-layout-required (MUST)
# Run when pyproject.toml or Python sources changed.
# ---------------------------------------------------------------------------
check_python_src_layout() {
  changed_file_matches "*pyproject.toml" || changed_file_matches "*.py" || \
    { [ "${#CHANGED_FILES[@]}" -eq 0 ]; } || return 0

  local pyproject="$TARGET_DIR/pyproject.toml"
  [ -f "$pyproject" ] || return 0

  # Look for packages= or package-dir= in pyproject.toml to determine package name.
  # Simple heuristic: any __init__.py at repo root level (not in src/) is a violation.
  while IFS= read -r init_py; do
    # Only flag root-level package dirs (depth 2: TARGET_DIR/<pkg>/__init__.py)
    local rel_path="${init_py#"$TARGET_DIR/"}"
    # Count path components
    local depth
    depth=$(printf '%s' "$rel_path" | tr -cd '/' | wc -c)
    if [ "$depth" -eq 1 ]; then
      local pkg_dir
      pkg_dir="$(dirname "$init_py")"
      local pkg_name
      pkg_name="$(basename "$pkg_dir")"
      # Skip common non-package dirs
      case "$pkg_name" in
        src|tests|test|docs|scripts|vendor|build|dist|.venv|venv) continue ;;
      esac
      emit_finding \
        "python-architecture-assistant" \
        "python-project-structure/src-layout-required" \
        "MUST" \
        "$init_py" \
        1 0 \
        "$pkg_name/__init__.py at root" \
        "Package '$pkg_name' is at repo root level instead of under src/. Use src-layout to prevent test-against-dev-dir bugs. See docs/python-project-structure.md."
    fi
  done < <(find "$TARGET_DIR" -maxdepth 2 -name "__init__.py" \
      -not -path "*/src/*" \
      -not -path "*/.venv/*" \
      -not -path "*/venv/*" \
      -not -path "*/vendor/*" \
      -not -path "*/build/*" \
      -not -path "*/dist/*" \
      2>/dev/null || true)
}

# ---------------------------------------------------------------------------
# RULE: python-project-structure/pyproject-toml-with-hatchling (MUST)
# Run when setup.py or pyproject.toml changed.
# ---------------------------------------------------------------------------
check_python_hatchling() {
  changed_file_matches "*setup.py" || changed_file_matches "*pyproject.toml" || \
    { [ "${#CHANGED_FILES[@]}" -eq 0 ]; } || return 0

  # Violation 1: setup.py present at root
  local setup_py="$TARGET_DIR/setup.py"
  if [ -f "$setup_py" ]; then
    emit_finding \
      "python-architecture-assistant" \
      "python-project-structure/pyproject-toml-with-hatchling" \
      "MUST" \
      "$setup_py" \
      1 0 \
      "setup.py present" \
      "setup.py found at repo root. Migrate to pyproject.toml + hatchling build backend. See docs/python-project-structure.md."
  fi

  # Violation 2: pyproject.toml present but missing hatchling build-backend
  local pyproject="$TARGET_DIR/pyproject.toml"
  if [ -f "$pyproject" ]; then
    if grep -q '\[build-system\]' "$pyproject"; then
      if ! grep -q 'build-backend.*=.*"hatchling\.build"' "$pyproject" && \
         ! grep -q "build-backend.*=.*'hatchling\.build'" "$pyproject"; then
        local line
        line=$(grep -n '\[build-system\]' "$pyproject" | head -1 | cut -d: -f1)
        local evidence
        evidence=$(grep 'build-backend' "$pyproject" | head -1 || echo "(no build-backend line)")
        emit_finding \
          "python-architecture-assistant" \
          "python-project-structure/pyproject-toml-with-hatchling" \
          "MUST" \
          "$pyproject" \
          "${line:-1}" 0 \
          "$evidence" \
          "pyproject.toml has [build-system] but build-backend is not 'hatchling.build'. Switch to hatchling. See docs/python-project-structure.md."
      fi
    fi
  fi
}

# ---------------------------------------------------------------------------
# RULE: skill-writing/scripts-in-scripts-subdir (MUST)
# Run when skills/ changed, or always.
# ---------------------------------------------------------------------------
check_skill_scripts_subdir() {
  changed_file_matches "*/skills/*" || { [ "${#CHANGED_FILES[@]}" -eq 0 ]; } || return 0

  local skills_dir="$TARGET_DIR/skills"
  [ -d "$skills_dir" ] || return 0

  # For each skill directory, check for *.sh or *.py next to SKILL.md
  while IFS= read -r skill_dir; do
    [ -d "$skill_dir" ] || continue
    # Only look one level deep (skills/<name>/)
    while IFS= read -r script_file; do
      emit_finding \
        "skill-auditor" \
        "skill-writing/scripts-in-scripts-subdir" \
        "MUST" \
        "$script_file" \
        1 0 \
        "$(basename "$script_file")" \
        "Script found directly in skills/ directory instead of skills/$(basename "$skill_dir")/scripts/. See docs/claude-code-skill-writing-guide.md."
    done < <(find "$skill_dir" -maxdepth 1 \( -name "*.sh" -o -name "*.py" \) 2>/dev/null || true)
  done < <(find "$skills_dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null || true)
}

# ---------------------------------------------------------------------------
# Run all checks
# ---------------------------------------------------------------------------
check_license_file_required
check_readme_license_section
check_changelog_preamble_frozen
check_changelog_unreleased_entry_required
check_git_subject_length
check_no_ai_attribution
check_semver_tag
check_no_tools_go_for_clis
check_no_cross_repo_replace
check_python_src_layout
check_python_hatchling
check_skill_scripts_subdir

# ---------------------------------------------------------------------------
# Assemble output JSON
# ---------------------------------------------------------------------------
END_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
ELAPSED=$((END_MS - START_MS))

# Build findings_by_owner from the findings file
FBO_FILE="$TMPDIR_WORK/fbo.json"
printf '{}' > "$FBO_FILE"

if [ -s "$FINDINGS_FILE" ]; then
  while IFS= read -r finding; do
    [ -z "$finding" ] && continue
    owner=$(printf '%s' "$finding" | jq -r '.owner')
    # Remove 'owner' from finding object (caller builds its own grouping key)
    clean_finding=$(printf '%s' "$finding" | jq 'del(.owner)')
    FBO_TMP="$TMPDIR_WORK/fbo_tmp.json"
    jq --arg o "$owner" --argjson f "$clean_finding" \
      'if has($o) then .[$o] += [$f] else . + {($o): [$f]} end' \
      "$FBO_FILE" > "$FBO_TMP" && mv "$FBO_TMP" "$FBO_FILE"
  done < "$FINDINGS_FILE"
fi

FBO_JSON="$(cat "$FBO_FILE")"

jq -n \
  --argjson findings_count "$FINDINGS_COUNT" \
  --argjson elapsed_ms "$ELAPSED" \
  --argjson findings_by_owner "$FBO_JSON" \
  '{stats:{yamls_run:0, findings_count:$findings_count, elapsed_ms:$elapsed_ms}, findings_by_owner:$findings_by_owner, errors:[]}'
