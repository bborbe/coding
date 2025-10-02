# Functional Composition Pattern

This document describes the functional composition pattern, which provides a composable and extensible approach to implementing any Go interface using functional programming techniques.

## Pattern Overview

The functional composition pattern consists of three main components:

1. **Interface**: Any Go interface (single method, multiple methods, any signatures)
2. **Function Type**: A type that allows functions to implement the interface directly
3. **List Type**: A slice type that implements the interface by calling each member

## Single-Method Interface Example

```go
// Any single-method interface
type Processor interface {
    Process(ctx context.Context, input Input) error
}

// Function type that implements the interface
type ProcessorFunc func(ctx context.Context, input Input) error

func (f ProcessorFunc) Process(ctx context.Context, input Input) error {
    return f(ctx, input)
}

// List type that implements the interface
type ProcessorList []Processor

func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for _, processor := range list {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
            if err := processor.Process(ctx, input); err != nil {
                return errors.Wrapf(ctx, err, "process failed")
            }
        }
    }
    return nil
}
```

## Multi-Method Interface Example

```go
// Multi-method interface
type Validator interface {
    Validate(data Data) error
    Transform(input Input) Output
    IsReady() bool
}

// Function type with fields for each method
type ValidatorFunc struct {
    ValidateFunc  func(data Data) error
    TransformFunc func(input Input) Output
    IsReadyFunc   func() bool
}

func (f ValidatorFunc) Validate(data Data) error {
    if f.ValidateFunc != nil {
        return f.ValidateFunc(data)
    }
    return nil // default behavior
}

func (f ValidatorFunc) Transform(input Input) Output {
    if f.TransformFunc != nil {
        return f.TransformFunc(input)
    }
    return Output{} // default behavior
}

func (f ValidatorFunc) IsReady() bool {
    if f.IsReadyFunc != nil {
        return f.IsReadyFunc()
    }
    return true // default behavior
}

// List type
type ValidatorList []Validator

func (list ValidatorList) Validate(data Data) error {
    for _, validator := range list {
        if err := validator.Validate(data); err != nil {
            return err
        }
    }
    return nil
}

func (list ValidatorList) Transform(input Input) Output {
    var result Output
    for _, validator := range list {
        result = validator.Transform(input)
        input = Input(result) // chain transformations
    }
    return result
}

func (list ValidatorList) IsReady() bool {
    for _, validator := range list {
        if !validator.IsReady() {
            return false
        }
    }
    return true
}
```

## When to Use This Pattern

### Good Use Cases

1. **Composable Operations**: When you need to combine multiple implementations of the same interface
2. **Pipeline Processing**: When operations should run sequentially on the same input
3. **Plugin Architecture**: When you want to allow easy extension with new implementations
4. **Functional Approach**: When you prefer functional programming over object-oriented patterns
5. **Any Interface**: Works with single-method or multi-method interfaces of any signature

### Benefits

- **Simplicity**: Factory functions return function types directly without complex structs
- **Composability**: Easy to combine multiple implementations using list types
- **Testability**: Simple to mock and test individual implementations
- **Extensibility**: New implementations can be added without modifying existing code
- **Context Awareness**: Built-in context cancellation support in list implementations
- **Error Handling**: Consistent error wrapping with contextual information
- **Universal**: Works with any Go interface regardless of method count or signatures

## Implementation Examples

### Factory Function Pattern

### Single-Method Interface Factory

```go
// Good: Functional approach
func NewDataProcessor(config Config) Processor {
    return ProcessorFunc(func(ctx context.Context, input Input) error {
        // Implementation logic with captured config
        log.Infof("Processing %v with config %v", input, config)
        return nil
    })
}

// Avoid: Unnecessary struct complexity
type dataProcessor struct {
    config Config
}

func (p *dataProcessor) Process(ctx context.Context, input Input) error {
    // Same logic but more boilerplate
    return nil
}
```

### Multi-Method Interface Factory

```go
// Good: Functional approach
func NewDataValidator(rules Rules) Validator {
    return ValidatorFunc{
        ValidateFunc: func(data Data) error {
            // Validation logic with captured rules
            return rules.Validate(data)
        },
        TransformFunc: func(input Input) Output {
            // Transform logic
            return rules.Transform(input)
        },
        IsReadyFunc: func() bool {
            return rules.IsConfigured()
        },
    }
}
```

### Composition Pattern

Combine multiple checkers into a single executable unit:

```go
func main() {
    // Single-method interface composition
    processors := ProcessorList{
        NewDataValidator(rules),
        NewDataTransformer(config),
        NewDataPersister(db),
    }

    err := processors.Process(ctx, input)
    if err != nil {
        // Handle error
    }

    // Multi-method interface composition
    validators := ValidatorList{
        NewSchemaValidator(schema),
        NewBusinessRuleValidator(rules),
        NewSecurityValidator(policy),
    }

    if validators.IsReady() {
        err := validators.Validate(data)
        output := validators.Transform(input)
    }
}
```

## Key Features

### Context Cancellation Support

List implementations can include context cancellation support:

```go
select {
case <-ctx.Done():
    return ctx.Err()
default:
    // Continue processing
}
```

This ensures that long-running operations can be cancelled gracefully.

### Error Wrapping

Errors are wrapped with contextual information using `github.com/bborbe/errors`:

```go
return errors.Wrapf(ctx, err, "check failed")
```

## Alternative Patterns

### When NOT to Use This Pattern

1. **Complex State Management**: When implementations need to maintain complex mutable internal state
2. **Lifecycle Management**: When implementations need initialization, cleanup, or lifecycle methods beyond the interface
3. **Complex Dependency Injection**: When implementations require complex dependency graphs or circular dependencies
4. **Performance Critical**: When function call overhead is a concern (though usually negligible)

### Alternative Approaches

For more complex scenarios, consider:

- **Service Pattern**: Traditional struct-based services with multiple methods
- **Strategy Pattern**: When you need runtime strategy selection
- **Chain of Responsibility**: When checkers need to pass data between each other
- **Command Pattern**: When operations are more complex than simple functions

## Testing

The functional pattern is highly testable:

```go
// Testing single-method interfaces
func TestProcessor(t *testing.T) {
    processor := NewDataProcessor(config)
    err := processor.Process(ctx, input)
    // Assert results
}

// Easy mocking for single-method interfaces
func TestWithMockProcessor(t *testing.T) {
    mockProcessor := ProcessorFunc(func(ctx context.Context, input Input) error {
        return nil // or return specific test behavior
    })

    processors := ProcessorList{mockProcessor}
    err := processors.Process(ctx, input)
    // Assert results
}

// Testing multi-method interfaces
func TestValidator(t *testing.T) {
    validator := NewDataValidator(rules)
    err := validator.Validate(data)
    output := validator.Transform(input)
    ready := validator.IsReady()
    // Assert results
}

// Easy mocking for multi-method interfaces
func TestWithMockValidator(t *testing.T) {
    mockValidator := ValidatorFunc{
        ValidateFunc: func(data Data) error {
            return nil
        },
        TransformFunc: func(input Input) Output {
            return Output{}
        },
        IsReadyFunc: func() bool {
            return true
        },
    }

    validators := ValidatorList{mockValidator}
    // Test all methods
}
```

## Migration from Struct-Based Patterns

When migrating from traditional struct-based patterns:

1. **Identify Target Interfaces**: Look for interfaces that could benefit from functional composition
2. **Create Function Types**: For single-method interfaces, create function types; for multi-method interfaces, create struct types with function fields
3. **Extract Factory Functions**: Convert constructors to return function types instead of structs
4. **Remove Unnecessary State**: Move dependencies to closure scope in factory functions
5. **Create List Types**: Implement list types that aggregate behavior across multiple implementations
6. **Update Tests**: Modify tests to use new functional implementations

## Real-World Applications

This pattern is particularly useful for:

- **HTTP Middleware**: Composing multiple middleware functions
- **Data Processing Pipelines**: Chaining processors, validators, and transformers
- **Plugin Systems**: Allowing dynamic composition of functionality
- **Event Handlers**: Combining multiple event processing functions
- **Configuration Validation**: Composing multiple validation rules
- **Testing**: Creating mock implementations easily

## Pattern Variations

### Aggregation Strategies

List implementations can use different aggregation strategies:

```go
// Fail-fast: Stop on first error
func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for _, processor := range list {
        if err := processor.Process(ctx, input); err != nil {
            return err // Stop immediately
        }
    }
    return nil
}

// Collect errors: Continue processing and collect all errors
func (list ProcessorList) ProcessAll(ctx context.Context, input Input) []error {
    var errors []error
    for _, processor := range list {
        if err := processor.Process(ctx, input); err != nil {
            errors = append(errors, err) // Continue processing
        }
    }
    return errors
}

// Transform chain: Pass output as input to next processor
func (list TransformerList) Transform(input Input) Output {
    current := input
    for _, transformer := range list {
        current = transformer.Transform(current)
    }
    return current
}
```

This pattern provides a clean, functional approach to implementing composable operations for any Go interface while maintaining the benefits of Go's interface system.