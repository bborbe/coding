---
allowed-tools: Bash(git status:*), Bash(go mod:*), Read, Grep
argument-hint: [basic|standard|integration] [path]
description: Write Go tests with configurable coverage modes for changed or specified files
---

# Go Write Test

Write Go tests in batch mode with three coverage levels. Defaults to testing only git-modified files.

## Arguments

**Mode** (required):
- `basic`: One happy path test per function
- `standard`: Happy path + error cases + edge cases
- `integration`: Standard + multi-component workflows with in-memory DB

**Path** (optional):
- If omitted: Tests git-modified `.go` files (default)
- If provided: Tests all `.go` files in specified path

## Usage

```bash
# Test git-modified files (default)
/coding:go-write-test basic
/coding:go-write-test standard

# Test specific paths
/coding:go-write-test basic .
/coding:go-write-test standard pkg/user
/coding:go-write-test integration myservice/
```

## Implementation

### Step 1: Validate Go Project

```bash
if [ ! -f "go.mod" ]; then
    echo "❌ Error: Not in a Go project (no go.mod found)"
    exit 1
fi

echo "🔍 Analyzing Go project..."
PROJECT_NAME=$(grep "^module " go.mod | awk '{print $2}')
echo "📦 Project: $PROJECT_NAME"
```

### Step 2: Parse and Validate Arguments

```bash
MODE=$1
PATH_ARG=$2

if [[ ! "$MODE" =~ ^(basic|standard|integration)$ ]]; then
  echo "❌ Error: Invalid mode. Use: basic, standard, or integration"
  exit 1
fi

echo "✅ Mode: $MODE"
```

### Step 3: Determine Target Files

**Default (no path)**: Git-modified files
```bash
if [ -z "$PATH_ARG" ]; then
  MODIFIED_FILES=$(git status --porcelain | grep '\.go$' | grep -v '_test\.go$' | awk '{print $2}')

  if [ -z "$MODIFIED_FILES" ]; then
    echo "No modified Go files found."
    echo ""
    echo "Suggestions:"
    echo "  /coding:go-write-test $MODE .           # Test all files in current directory"
    echo "  /coding:go-write-test $MODE pkg/        # Test specific package"
    exit 0
  fi

  echo "📝 Targeting git-modified files:"
  echo "$MODIFIED_FILES"
  TARGET="Files: $MODIFIED_FILES"
else
  echo "📝 Targeting path: $PATH_ARG"
  TARGET="Path: $PATH_ARG"
fi
```

### Step 4: Invoke Test Writer Agent

Use the Task tool to spawn `coding:go-test-writer-assistant` agent:

```
Write Go tests in $MODE mode.

Target: $TARGET
Mode: $MODE

The agent will:
1. Discover and prioritize functions needing tests
2. Generate test files and suite setup
3. Write tests in batch mode
4. Validate with ginkgo (retry up to 2 times)
5. Report coverage improvements

See agent documentation for detailed implementation patterns.
```

### Step 5: Done

Agent will report completion with:
- Files analyzed
- Tests created
- Validation results
- Coverage improvements
