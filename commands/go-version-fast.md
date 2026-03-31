---
description: Fast Go version update using Perl regex for bulk file replacement (go.mod and Dockerfile only)
argument-hint: <go-version> <directory...>
allowed-tools:
  - Bash
---

# Go Version Fast

Fast bulk Go version updater using Perl regex. Updates go.mod and Dockerfile files across multiple directories in seconds.

## Usage

```bash
/go-version-fast 1.25.4 commerce golden jira
/go-version-fast 1.25.4 .
/go-version-fast 1.25.4 atlassian/community*
```

## What It Does

- Updates `go.mod`: `go 1.X.Y` → `go <target-version>`
- Updates `Dockerfile`: `FROM golang:1.X.Y` → `FROM golang:<target-version>`
- Excludes vendor directories
- Processes all directories in single pass (~5-10 seconds)

## Implementation

Parse arguments:
- First argument: target Go version (e.g., `1.25.4`)
- Remaining arguments: directory paths

Execute bulk update:

```bash
# Fetch latest stable version if "latest" provided
if [ "$VERSION" = "latest" ]; then
  FETCHED=$(curl -s "https://go.dev/dl/?mode=json" | jq -r '.[] | select(.stable == true) | .version' | head -n 1)
  if [ -z "$FETCHED" ] || [ "$FETCHED" = "null" ]; then
    echo "Error: Failed to fetch latest Go version" >&2
    exit 1
  fi
  VERSION=$(echo "$FETCHED" | sed 's/go//')
fi

# Validate version format (should be X.Y or X.Y.Z)
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+(\.[0-9]+)?$'; then
  echo "Error: Invalid version format: $VERSION (expected X.Y or X.Y.Z)" >&2
  exit 1
fi

# Validate directories exist
for dir in <directories>; do
  if [ ! -d "$dir" ]; then
    echo "Error: Directory not found: $dir" >&2
    exit 1
  fi
done

# Bulk update go.mod and Dockerfile files
# Regex handles both "go 1.25" and "go 1.25.3" formats
find <directories> \( -name "go.mod" -o -name "Dockerfile" \) \
  -not -path "*/vendor/*" \
  -type f \
  -exec perl -pi -e "s/^go 1\.\d+(\.\d+)?\$/go $VERSION/; s/FROM golang:1\.\d+(\.\d+)?/FROM golang:$VERSION/" {} +

# Count and report results
FILE_COUNT=$(find <directories> \( -name "go.mod" -o -name "Dockerfile" \) -not -path "*/vendor/*" -type f | wc -l | tr -d ' ')
echo "Updated $FILE_COUNT files (go.mod and Dockerfile) to Go $VERSION"
```

## Workflow

1. **Validate Arguments**
   - Check version format (X.Y or X.Y.Z or "latest")
   - Verify directories exist
   - Exit with error if validation fails

2. **Fetch Version (if needed)**
   - If "latest" specified, fetch from go.dev
   - Validate fetch succeeded (check for null/empty)
   - Strip "go" prefix to get version number
   - Otherwise use provided version as-is

3. **Bulk Update**
   - Single find command across all directories
   - Perl regex replacement for both file types
   - Handles both "go 1.25" and "go 1.25.3" formats
   - Non-vendor files only

4. **Report Summary**
   - Count files updated
   - Show version applied
   - Suggest verification command

## Trade-offs

**Advantages:**
- ✅ 100x faster than agent-based approach
- ✅ Processes multiple directories at once
- ✅ Simple, reliable regex replacement
- ✅ No agent startup overhead

**Limitations:**
- ❌ No consistency checking across file types
- ❌ No verification with `go list -m`
- ❌ Updates only go.mod + Dockerfile (not CI configs)
- ❌ No detailed reporting per file

## When to Use

**Use `/go-version-fast` when:**
- Updating multiple directories (3+)
- You know the target version
- Speed is priority
- You'll verify manually with `make precommit`

**Use `/go-version` (full) when:**
- Need comprehensive file checking (CI configs, README, etc.)
- Want consistency validation
- First time updating or uncertain about versions
- Need verification and detailed reports

## Examples

```bash
# Update multiple directories to Go 1.25.4
/go-version-fast 1.25.4 commerce golden jira

# Update to latest stable
/go-version-fast latest atlassian hubspot google

# Update all subdirectories with glob pattern
/go-version-fast 1.25.4 */

# Update current directory
/go-version-fast 1.25.4 .
```

## Verification

After running, verify with:
```bash
# Check one module from each directory
cd commerce/gateway && go list -m
cd golden/party-v1 && go list -m
cd jira/gateway && go list -m

# Or run make precommit
make precommit
```

## Notes

- Processes go.mod and Dockerfile only (primary version files)
- Excludes vendor directories automatically
- Version format: `X.Y` or `X.Y.Z` (no "go" prefix in argument)
- Handles both `go 1.25` and `go 1.25.3` formats in files
- Use "latest" to auto-fetch current stable version
- Validates version format and directory existence before updating
- After bulk update, run `make precommit` in each project
- Consider running `/go-version check` first to see current state
