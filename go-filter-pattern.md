# Go Filter Pattern

This document describes patterns for implementing filters in Go, with a focus on functional composition, performance optimization, and semantic clarity.

## Pattern Overview

Filters are predicates that determine whether data should be included or excluded from a result set. The filter pattern combines:

1. **Filter Interface**: Defines the filtering contract
2. **Functional Implementation**: Uses closures for simple, efficient filtering
3. **Semantic Clarity**: Clear naming that matches user intent
4. **Performance Optimization**: Preprocessing to minimize runtime overhead

## Core Filter Interface

```go
// Filter interface with clear semantics: returns true if item should be EXCLUDED
type ItemFilter interface {
    // Filtered returns true if item should be filtered out (excluded)
    Filtered(ctx context.Context, tx Tx, item Item) (bool, error)
}
```

**Critical**: Document the return value semantics clearly:
- `true` = filter out (exclude)
- `false` = pass through (include)

## Pattern Evolution: From Struct to Function

### Anti-Pattern: Unnecessary Struct Complexity

```go
// ❌ Avoid: Struct with internal state check on every call
func NewItemFilter(allowedTypes []Type) ItemFilter {
    return &itemFilter{
        allowedTypes: collection.NewSet[Type](allowedTypes...),
    }
}

type itemFilter struct {
    allowedTypes collection.Set[Type]
}

func (f *itemFilter) Filtered(ctx context.Context, tx Tx, item Item) (bool, error) {
    if f.allowedTypes.Length() == 0 {
        return false, nil // Checked on EVERY call
    }
    return !f.allowedTypes.Contains(item.Type), nil
}
```

**Problems**:
- Empty check happens on every filter call
- Unnecessary struct allocation
- More boilerplate code

### Good Pattern: No-Op Filter for Empty Input

```go
// ✅ Good: Return no-op filter for empty input
func NewItemFilter(allowedTypes []Type) ItemFilter {
    if len(allowedTypes) == 0 {
        return ItemFilterNone() // Checked ONCE at creation
    }
    allowedTypeSet := collection.NewSet[Type](allowedTypes...)
    return ItemFilterFunc(func(ctx context.Context, tx Tx, item Item) (bool, error) {
        return !allowedTypeSet.Contains(item.Type), nil
    })
}

// No-op filter implementation
func ItemFilterNone() ItemFilter {
    return ItemFilterFunc(func(ctx context.Context, tx Tx, item Item) (bool, error) {
        return false, nil // Never filter anything
    })
}
```

**Benefits**:
- ✅ Empty check happens once at filter creation
- ✅ No unnecessary struct allocation
- ✅ Uses established no-op pattern
- ✅ Set conversion happens once, not on every call

## Performance Optimization: Preprocess Outside Closure

### Anti-Pattern: Processing Inside Closure

```go
// ❌ Avoid: Conversion happens on EVERY filter call
func NewItemFilter(allowedTypes []Type) ItemFilter {
    return ItemFilterFunc(func(ctx context.Context, tx Tx, item Item) (bool, error) {
        allowedSet := collection.NewSet[Type](allowedTypes...) // O(n) conversion per call
        return !allowedSet.Contains(item.Type), nil
    })
}
```

**Problem**: Slice-to-set conversion happens on every filter evaluation.

### Good Pattern: Preprocess Outside Closure

```go
// ✅ Good: Conversion happens ONCE at filter creation
func NewItemFilter(allowedTypes []Type) ItemFilter {
    if len(allowedTypes) == 0 {
        return ItemFilterNone()
    }
    allowedTypeSet := collection.NewSet[Type](allowedTypes...) // O(n) conversion once
    return ItemFilterFunc(func(ctx context.Context, tx Tx, item Item) (bool, error) {
        return !allowedTypeSet.Contains(item.Type), nil // O(1) lookup per call
    })
}
```

**Benefits**:
- ✅ Set conversion: O(n) once vs O(n) per call
- ✅ Contains lookup: O(1) hash map vs O(n) slice search
- ✅ Closure captures preprocessed data

## Semantic Clarity: Include vs Exclude

### Anti-Pattern: Inverted Semantics

```go
// ❌ Confusing: Parameter name doesn't match behavior
func CreateFilters(
    excludedTypes []Type, // ← Name suggests "exclude these"
) []Filter {
    filters := []Filter{}
    if len(excludedTypes) > 0 {
        // But actually INCLUDES only these types!
        filters = append(filters, NewIncludeTypeFilter(excludedTypes))
    }
    return filters
}
```

**Problem**: Parameter name `excludedTypes` suggests exclusion, but filter does inclusion.

### Good Pattern: Semantic Alignment

```go
// ✅ Good: Parameter name matches filter behavior
func CreateFilters(
    allowedTypes []Type, // ← Clear: these types are allowed
) []Filter {
    filters := []Filter{}
    if len(allowedTypes) > 0 {
        filters = append(filters, NewIncludeTypeFilter(allowedTypes))
    }
    return filters
}

// NewIncludeTypeFilter includes only items matching allowedTypes.
// If allowedTypes is empty, all items pass through (no filtering).
func NewIncludeTypeFilter(allowedTypes []Type) Filter {
    // Implementation
}
```

**Benefits**:
- ✅ Parameter name matches intent (`allowedTypes` → "allow these")
- ✅ Documentation clarifies behavior
- ✅ Empty list behavior is explicit

## Environment Variable Mapping

When filters are configured via environment variables:

```go
// Configuration mapping
type Config struct {
    // FILTER_ALLOWED_TYPES=FOO,BAR,BAZ
    FilterAllowedTypes []Type `env:"FILTER_ALLOWED_TYPES" usage:"types to include (empty = all)"`
}

// Factory usage
func CreateFilterFromConfig(config Config) Filter {
    return NewIncludeTypeFilter(config.FilterAllowedTypes)
}
```

**Guidelines**:
- Use clear env var names: `ALLOWED_TYPES` not `EXCLUDED_TYPES` if filter includes
- Document empty behavior: "empty = all" or "empty = none"
- Match parameter names to env var semantics

## Complete Example: Order Status Filter

Real-world example with type-based filtering:

```go
// Filter that includes only orders with allowed statuses.
// If allowedStatuses is empty, all orders pass through (no filtering).
func NewOrderFilterByStatus(
    allowedStatuses OrderStatuses,
) OrderFilter {
    // Early return: no filtering needed
    if len(allowedStatuses) == 0 {
        return OrderFilterNone()
    }

    // Preprocess: convert to set once
    allowedStatusSet := allowedStatuses.Set()

    // Return functional filter
    return OrderFilterFunc(func(
        ctx context.Context,
        order Order,
    ) (bool, error) {
        // Efficient O(1) lookup per call
        return allowedStatusSet.Contains(order.Status), nil
    })
}
```

**Evolution**:
1. ❌ Started with struct + method (~50 lines)
2. ✅ Moved to functional closure (~30 lines)
3. ✅ Added early return for empty input (~25 lines)
4. ✅ Preprocessed set outside closure (~10 lines)

## Testing Filters

```go
var _ = Describe("StrategyFilterSignalFinderType", func() {
    var (
        ctx      context.Context
        tx       Tx
        strategy Strategy
    )

    BeforeEach(func() {
        ctx = context.Background()
        tx = nil
        strategy = Strategy{Type: "FOO"}
    })

    Context("with empty allowed types", func() {
        It("allows all strategies through", func() {
            filter := NewStrategyFilter([]Type{})

            filtered, err := filter.Filtered(ctx, tx, strategy)
            Expect(err).NotTo(HaveOccurred())
            Expect(filtered).To(BeFalse(), "should pass through when no filter")
        })
    })

    Context("with allowed types specified", func() {
        It("allows strategies with allowed type", func() {
            filter := NewStrategyFilter([]Type{"FOO", "BAR"})
            strategy.Type = "FOO"

            filtered, err := filter.Filtered(ctx, tx, strategy)
            Expect(err).NotTo(HaveOccurred())
            Expect(filtered).To(BeFalse(), "should pass through FOO")
        })

        It("filters out strategies with non-allowed type", func() {
            filter := NewStrategyFilter([]Type{"FOO", "BAR"})
            strategy.Type = "BAZ"

            filtered, err := filter.Filtered(ctx, tx, strategy)
            Expect(err).NotTo(HaveOccurred())
            Expect(filtered).To(BeTrue(), "should filter out BAZ")
        })
    })
})
```

**Test Coverage**:
- Empty input (no filtering)
- Allowed items pass through
- Disallowed items filtered out
- Edge cases (single item, unknown types)

## Pattern Checklist

When implementing a filter:

- [ ] **Interface semantics clear**: Document what `true` return value means
- [ ] **Naming aligned**: Parameter names match filter behavior (allowed/excluded)
- [ ] **Empty input handled**: Early return with no-op filter if appropriate
- [ ] **Preprocessing done**: Convert/process data outside closure, not inside
- [ ] **Set-based lookups**: Use `collection.Set` for O(1) contains operations
- [ ] **Documentation complete**: Clarify empty input behavior
- [ ] **Tests comprehensive**: Cover empty, allowed, disallowed cases
- [ ] **Env var semantics match**: Environment variable names align with behavior

## Anti-Patterns to Avoid

1. **Semantic Inversion**: Parameter named `excluded` but filter includes
2. **Runtime Checks**: Checking empty on every call instead of at creation
3. **Repeated Preprocessing**: Converting to set on every filter call
4. **Unclear Documentation**: Not documenting what `true`/`false` means
5. **Struct Overhead**: Using struct when functional approach is simpler
6. **Linear Search**: Using slice contains instead of set lookup

## Related Patterns

- **Functional Composition Pattern**: See `go-functional-composition-pattern.md`
- **Strategy Pattern**: When you need runtime filter selection
- **Chain of Responsibility**: When filters need to pass data between each other
- **Specification Pattern**: When combining multiple filter conditions

## Real-World Usage

This pattern is particularly effective for:

- **Data Filtering**: Filtering collections based on attributes
- **Access Control**: Filtering resources based on permissions
- **Content Filtering**: Including/excluding items by type/category
- **Pipeline Processing**: Filtering stages in data processing pipelines
- **Query Building**: Dynamically building filter conditions
- **Report Generation**: Filtering data for specific report views
