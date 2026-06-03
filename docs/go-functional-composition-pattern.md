# Functional Composition Pattern

This document describes the functional composition pattern, which provides a composable and extensible approach to implementing any Go interface using functional programming techniques.

## Rules

### RULE go-functional-composition/func-type-name (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go file introduces a function type that implements an interface `X` for the functional-composition pattern but names the type something other than `XFunc`.
**Enforcement**: judgment (ast-grep follow-up: `type_declaration` of `func` type where same package declares `type X interface` and the func type's signature matches X's method signature; the agent rules out unrelated func types that aren't pattern implementations)
**Why**: `XFunc` is the universal signal "this is the function-type adapter for interface `X`" — consumers find it via grep on the interface name, IDEs surface it next to the interface, tooling auto-completes the pattern. A custom name (`HandlerLambda`, `ProcessorClosure`, `RunFn`) breaks the convention; every consumer has to learn the local naming scheme instead.

#### Bad

```go
type Processor interface {
    Process(ctx context.Context, input Input) error
}

// Wrong name — breaks the convention; grepping for ProcessorFunc finds nothing.
type ProcessorLambda func(ctx context.Context, input Input) error

func (f ProcessorLambda) Process(ctx context.Context, input Input) error {
    return f(ctx, input)
}
```

#### Good

```go
type Processor interface {
    Process(ctx context.Context, input Input) error
}

type ProcessorFunc func(ctx context.Context, input Input) error

func (f ProcessorFunc) Process(ctx context.Context, input Input) error {
    return f(ctx, input)
}
```

### RULE go-functional-composition/list-type-name (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go file introduces a slice type that implements an interface `X` for the functional-composition pattern but names the type something other than `XList`.
**Enforcement**: judgment (ast-grep follow-up: `type_declaration` of `[]X` slice where same package declares `type X interface`; the agent rules out generic slice aliases that aren't pattern implementations)
**Why**: `XList` pairs with `XFunc` to complete the pattern: `XFunc` lets any function implement the interface; `XList` lets a slice of implementations behave as a single implementation that delegates to each member. A custom name (`Processors`, `ProcessorChain`, `ProcessorSet`) makes the pair invisible — consumers see `ProcessorFunc` and wonder where the aggregator lives.

#### Bad

```go
// Wrong name — pair convention broken; grep for ProcessorList finds nothing.
type Processors []Processor

func (list Processors) Process(ctx context.Context, input Input) error {
    for _, p := range list {
        if err := p.Process(ctx, input); err != nil {
            return err
        }
    }
    return nil
}
```

#### Good

```go
type ProcessorList []Processor

func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for _, p := range list {
        if err := p.Process(ctx, input); err != nil {
            return err
        }
    }
    return nil
}
```

### RULE go-functional-composition/list-checks-ctx-done (MUST)

**Owner**: go-context-assistant
**Applies when**: a `XList` method that accepts a `context.Context` iterates over its members without checking `ctx.Done()` between iterations — so a cancelled context cannot stop the chain mid-way.
**Enforcement**: judgment (ast-grep follow-up: `method_declaration` on a `[]X` receiver type whose body is a `for_statement` containing a call to the wrapped interface method but no `<-ctx.Done()` select case; the agent rules in/out based on whether iteration is bounded and cheap enough that ctx-check overhead is unjustified)
**Why**: List delegation without ctx-check turns "cancel this request" into "wait for the entire chain to finish anyway". The pattern's whole point is composability; composing 50 processors and then ignoring cancellation defeats the safety net every individual processor was supposed to provide. One `select { case <-ctx.Done(): return ctx.Err(); default: }` per iteration costs nanoseconds; the operator-visible win is bounded-time shutdown.

#### Bad

```go
func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for _, p := range list {
        if err := p.Process(ctx, input); err != nil {
            return err
        }
        // No ctx.Done check — even after cancellation we continue iterating.
    }
    return nil
}
```

#### Good

```go
func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for _, p := range list {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        if err := p.Process(ctx, input); err != nil {
            return err
        }
    }
    return nil
}
```

### RULE go-functional-composition/list-wraps-errors-with-ctx (MUST)

**Owner**: go-error-assistant
**Applies when**: a `XList` method returns an error from a wrapped member's call directly (`return err`) instead of wrapping with `errors.Wrapf(ctx, err, "<member-identifying context>")` from `github.com/bborbe/errors`.
**Enforcement**: judgment (ast-grep follow-up: `method_declaration` on a `[]X` receiver containing `return err` immediately after a wrapped-member call; the agent rules out cases where the call site is a single-member iteration that adds no context)
**Why**: A bare `return err` from a list iteration tells the caller "something in this list failed" but not which member nor what input shape. Wrapping with `errors.Wrapf(ctx, err, "process %T failed", processor)` (or similar member-identifying context) gives the operator a debugging breadcrumb without forcing the member implementations to know they live inside a list.

#### Bad

```go
func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for _, p := range list {
        if err := p.Process(ctx, input); err != nil {
            return err
        }
    }
    return nil
}
```

#### Good

```go
func (list ProcessorList) Process(ctx context.Context, input Input) error {
    for i, p := range list {
        if err := p.Process(ctx, input); err != nil {
            return errors.Wrapf(ctx, err, "processor[%d] failed", i)
        }
    }
    return nil
}
```

### RULE go-functional-composition/multi-method-func-explicit-delegate (SHOULD)

**Owner**: go-quality-assistant
**Applies when**: a multi-method interface `X` has a `XFunc` struct adapter, but the adapter omits a field for one or more of the interface's methods OR delegates without a `nil`-check + sane default, so calling the missing/zero field panics.
**Enforcement**: judgment (ast-grep follow-up: `struct_type` whose name matches `[A-Z][a-zA-Z]*Func` paired with a same-package interface; the agent verifies each interface method has a matching field + receiver method that nil-checks and returns a sane zero)
**Why**: The multi-method adapter's value is partial implementation — set only the methods you care about, the rest behave as harmless no-ops. A missing field or a panic-on-nil delegation flips the value proposition: instead of "test fixture for the method I'm testing", the adapter becomes "land mine for every other method on the interface". The nil-check + sane-default is what makes the pattern usable.

#### Bad

```go
type ValidatorFunc struct {
    ValidateFunc func(data Data) error
    // Missing TransformFunc + IsReadyFunc — calling Transform/IsReady panics with nil pointer.
}

func (f ValidatorFunc) Validate(data Data) error  { return f.ValidateFunc(data) }
func (f ValidatorFunc) Transform(in Input) Output { return f.TransformFunc(in) } // panic if nil
func (f ValidatorFunc) IsReady() bool             { return f.IsReadyFunc() }     // panic if nil
```

#### Good

```go
type ValidatorFunc struct {
    ValidateFunc  func(data Data) error
    TransformFunc func(input Input) Output
    IsReadyFunc   func() bool
}

func (f ValidatorFunc) Validate(data Data) error {
    if f.ValidateFunc != nil {
        return f.ValidateFunc(data)
    }
    return nil
}

func (f ValidatorFunc) Transform(in Input) Output {
    if f.TransformFunc != nil {
        return f.TransformFunc(in)
    }
    return Output{}
}

func (f ValidatorFunc) IsReady() bool {
    if f.IsReadyFunc != nil {
        return f.IsReadyFunc()
    }
    return true
}
```

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