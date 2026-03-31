---
description: Generate GoDoc for all public functions, interfaces, types, and so on, and follow the existing best practice
argument-hint: [optional: directory path]
allowed-tools: [Read, Edit, Glob, TodoWrite, Grep]
---

# Generate GoDoc Comments

Automatically generate comprehensive GoDoc comments for all exported Go code elements following best practices from the coding-guidelines repository.

## Usage

`/godoc [optional: directory path]`

Examples:
- `/godoc` - Document files in current directory
- `/godoc lib/core` - Document specific directory
- `/godoc .` - Document current directory and subdirectories

## Best Practices Reference

Follow all guidelines from `docs/go-doc-best-practices.md`:

### Core Principles
- **Complete Sentences**: Start with the name of the function/type/package
- **Third-Person**: Use descriptive, instructive tone (not first-person)
- **No Code Duplication**: Don't repeat the function signature
- **Focus on Behavior**: Explain what it does and how it's used, not implementation details
- **Be Concise**: Clear and to the point

### Documentation Standards by Type

**Package Comments** (in doc.go):
```go
// Package calculator provides basic mathematical operations.
package calculator
```

**Function/Method Comments**:
```go
// Multiply returns the product of two integers.
func Multiply(a, b int) int

// Merge combines two sorted slices into a single sorted slice.
// It assumes both inputs are sorted in ascending order.
func Merge(a, b []int) []int
```

**Struct and Interface Comments**:
```go
// User represents a user in the system.
type User struct {
    ID    int
    Email string
}

// Store provides persistent storage operations for trading data.
type Store interface {
    Save(ctx context.Context) error
}
```

**Constant and Variable Comments**:
```go
// MaxRetries defines the maximum number of retry attempts.
const MaxRetries = 3

// DefaultTimeout is the standard timeout duration for API calls.
var DefaultTimeout = 30 * time.Second
```

## Process

### Phase 1: Discovery

1. **Determine Target Directory**:
   - If argument provided: Use specified directory path
   - If no argument: Use current working directory

2. **Find All Go Files**:
   - Use Glob to find all `*.go` files (excluding `*_test.go`, `*_suite_test.go`)
   - Exclude vendor directories and generated files
   - Create initial todo list with all Go files found

### Phase 2: Analysis and Documentation

For each Go file:

1. **Read File Content**: Use Read tool to examine the entire file

2. **Identify Missing Documentation**: Look for exported items without doc comments:
   - Package declarations (should have doc.go or package comment)
   - Type declarations: `type Name struct`, `type Name interface`, `type Name [...]`
   - Function declarations: `func Name(...)`
   - Method declarations: `func (receiver) Name(...)`
   - Constant declarations: `const Name =`
   - Variable declarations: `var Name =`

3. **Generate Documentation**: For each missing doc comment:

   **Context Awareness**: Consider the trading system domain:
   - Price, Order, Trade, Position → financial concepts
   - Broker, Account, Strategy → trading infrastructure
   - Candle, Signal, Indicator → technical analysis
   - Epic, Symbol, Resolution → market data identifiers
   - Command, Event, Store → CQRS patterns

   **Documentation Template by Type**:

   - **Types (struct/interface/alias)**:
     ```
     // [Name] [verb describing role/purpose].
     // [Optional: Additional context about usage or key characteristics]
     ```

   - **Functions/Methods**:
     ```
     // [Name] [verb describing action] [object/outcome].
     // [Optional: Important parameters, side effects, or assumptions]
     ```

   - **Constants/Variables**:
     ```
     // [Name] [describes the value or its purpose].
     ```

4. **Apply Documentation**: Use Edit tool to add doc comments:
   - Add comment immediately before the declaration
   - Maintain existing file structure and formatting
   - Preserve copyright headers and imports
   - Don't modify existing documentation

5. **Update Progress**: Mark file as completed in todo list

### Phase 3: Package Documentation

1. **Check for Package Comment**:
   - Look for `doc.go` file in the directory
   - If package comment exists in any file, verify it follows best practices

2. **Create/Update doc.go** (if needed):
   - Only if no package documentation exists
   - Follow pattern:
     ```go
     // Copyright (c) 2025 Benjamin Borbe All rights reserved.
     // Use of this source code is governed by a BSD-style
     // license that can be found in the LICENSE file.

     // Package [name] [describes the package purpose and main functionality].
     //
     // [Optional: Additional details about key components or usage patterns]
     package [name]
     ```

### Phase 4: Summary

Provide final summary:
- Total Go files processed
- Total documentation comments added
- Files that were already fully documented
- Any files skipped (with reasons)

## Important Rules

1. **Only Add Missing Documentation**: Never modify existing doc comments
2. **Preserve Code Structure**: Don't change any code, imports, or formatting
3. **Be Conservative**: If unsure about documentation, note it and skip
4. **Maintain Copyright**: Keep all existing copyright headers intact
5. **Sequential Processing**: Process files one at a time for clarity
6. **Quality Over Speed**: Ensure each comment is accurate and helpful

## Context-Specific Patterns

### Trading Domain Terms

When documenting trading system code, use appropriate terminology:

- **Price/Level**: "price level", "market price", "stop/limit level"
- **Order/Trade**: "market order", "pending order", "executed trade", "open position"
- **Strategy**: "trading strategy", "signal generation", "entry/exit logic"
- **Broker**: "broker integration", "account management", "order execution"
- **Candle**: "OHLC data", "price candle", "timeframe", "resolution"
- **Signal**: "trading signal", "entry/exit signal", "signal generation"
- **Risk**: "position sizing", "risk management", "stop loss", "drawdown"

### Common Method Patterns

- **Parse[Type]**: "Parse[Type] converts various input types to [Type]."
- **[Type]Ptr**: "[Type]Ptr converts a pointer to [source] into a [Type] pointer."
- **Validate**: "Validate checks if the [type] meets all required constraints."
- **String**: "String returns the string representation of [type]."
- **Equal**: "Equal returns true if the [type] matches the provided [type]."
- **Clone**: "Clone creates a deep copy of the [type]."
- **Ptr**: "Ptr returns a pointer to the [type] value."

## Error Handling

If you encounter:
- **Non-Go files**: Skip silently
- **Test files**: Skip (tests have different documentation standards)
- **Generated files**: Skip (marked with `// Code generated`)
- **Vendor files**: Skip
- **Ambiguous cases**: Document best effort, note uncertainty
- **Already documented**: Mark as complete, no changes needed

## Output Format

Use emojis and clear status for progress tracking:
- 📁 File discovered
- 📝 Documentation added
- ✅ File completed
- ⏭️ File skipped (already documented)
- 🎯 Phase completed

Example:
```
📊 Phase 1: Discovery
Found 15 Go files in lib/core/

📝 Phase 2: Documentation Generation
📁 Processing: core_price.go
  • Added doc for type Price
  • Added doc for method Add
  • Added doc for method Sub
  • Added doc for func ParsePrice
✅ Completed: core_price.go (4 comments added)

📁 Processing: core_broker-identifier.go
  • Added doc for type BrokerIdentifier
  • Added doc for func ParseBrokerIdentifier
✅ Completed: core_broker-identifier.go (2 comments added)

🎯 Summary: Documented 15 files, added 47 comments
```
