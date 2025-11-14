# Functional Options Pattern

This document describes the functional options pattern for Go constructors, which provides a clean and extensible way to handle optional configuration parameters without breaking backward compatibility.

**Pattern Origin**: This pattern was popularized by Dave Cheney in his blog post "Functional options for friendly APIs" and has become a widely adopted Go idiom for constructor configuration.

## Pattern Overview

The functional options pattern consists of:

1. **Options struct**: Exported struct holding all optional configuration
2. **Custom option type**: Named type with `func(*Options)` signature for modifying options
3. **Variadic options parameter**: Constructor accepts `...CustomOptionType`
4. **Default values**: Options struct initialized with sensible defaults
5. **Option application**: Loop through options to apply configurations

**Best Practice:** Always define a custom option type rather than using inline `func(*Options)` for better documentation, type safety, and API clarity.

## Basic Example

```go
// ConsumerOptions holds all optional configuration for consumers
type ConsumerOptions struct {
    TargetLag int64
    Delay     libtime.Duration
}

// ConsumerOption defines a function type for modifying consumer configuration
type ConsumerOption func(*ConsumerOptions)

// Constructor with variadic options parameter
func NewOffsetConsumer(
    saramaClient sarama.Client,
    topic Topic,
    offsetManager OffsetManager,
    messageHandler MessageHandler,
    logSamplerFactory log.SamplerFactory,
    options ...ConsumerOption,
) Consumer {
    // Initialize with default values
    consumerOptions := ConsumerOptions{
        TargetLag: 0,
        Delay:     0,
    }

    // Apply all provided options
    for _, option := range options {
        option(&consumerOptions)
    }

    return &offsetConsumer{
        // ... other fields
        consumerOptions: consumerOptions,
    }
}
```

**Key points:**
- Options struct is exported to allow external package option functions
- Custom option type is **singular**: `<Type>Option` (represents one option function)
- Options struct is **plural**: `<Type>Options` (holds multiple option values)
- Constructor parameter uses `...ConsumerOption` for variadic options
- Default values are set before applying options
- All options are applied in order via loop

## Creating Option Functions

Option functions should follow the `WithXxx` naming convention and return the custom option type:

```go
// ConsumerOption defines a function type for modifying consumer configuration.
type ConsumerOption func(*ConsumerOptions)

// WithTargetLag sets the target lag for the consumer
func WithTargetLag(targetLag int64) ConsumerOption {
    return func(opts *ConsumerOptions) {
        opts.TargetLag = targetLag
    }
}

// WithDelay sets the delay duration for the consumer
func WithDelay(delay libtime.Duration) ConsumerOption {
    return func(opts *ConsumerOptions) {
        opts.Delay = delay
    }
}
```

**Key points:**
- Function name starts with `With` followed by the option name
- Returns the custom option type (`ConsumerOption`, singular)
- Captures the parameter value in closure scope
- Type signature is `func(*ConfigStruct)`
- Provides better documentation and type clarity
- Makes function signature more readable
- Allows for easier refactoring and type checking

### Configuring External Types

When configuring types from external packages, you may see plural naming:

```go
// SaramaConfigOption defines a function type for modifying Sarama configuration
// Note: Some codebases use plural "Options" but singular "Option" is preferred
type SaramaConfigOption func(config *sarama.Config)

// CreateSaramaConfig creates a new Sarama configuration with default settings
func CreateSaramaConfig(
    ctx context.Context,
    brokers Brokers,
    opts ...SaramaConfigOption,
) (*sarama.Config, error) {
    config := sarama.NewConfig()
    config.Version = sarama.V3_6_0_0
    config.Producer.RequiredAcks = sarama.WaitForAll
    config.Producer.Retry.Max = 10
    // ... more defaults

    // Apply all options
    for _, opt := range opts {
        opt(config)
    }

    return config, nil
}

// WithVersion sets the Kafka version
func WithVersion(version sarama.KafkaVersion) SaramaConfigOption {
    return func(config *sarama.Config) {
        config.Version = version
    }
}
```

**Note**: While some existing code uses plural `SaramaConfigOptions`, the singular `SaramaConfigOption` is more semantically correct (one option function) and should be preferred for new code.

## Usage Examples

### Without Options (Use Defaults)

```go
consumer := kafka.NewOffsetConsumer(
    saramaClient,
    topic,
    offsetManager,
    messageHandler,
    logSamplerFactory,
)
```

### With Single Option

```go
consumer := kafka.NewOffsetConsumer(
    saramaClient,
    topic,
    offsetManager,
    messageHandler,
    logSamplerFactory,
    kafka.WithTargetLag(1000),
)
```

### With Multiple Options

```go
consumer := kafka.NewOffsetConsumer(
    saramaClient,
    topic,
    offsetManager,
    messageHandler,
    logSamplerFactory,
    kafka.WithTargetLag(1000),
    kafka.WithDelay(libtime.Duration(time.Second * 5)),
)
```

## When to Use This Pattern

### Good Use Cases

1. **Optional parameters**: When a constructor has multiple optional configuration values
2. **Future extensibility**: When you may need to add more options without breaking API
3. **Backward compatibility**: When you need to maintain compatibility while adding features
4. **Complex configuration**: When configuration has many possible combinations
5. **Sensible defaults**: When most users can use default values for optional parameters

### Benefits

- **Backward compatible**: New options don't break existing code
- **Self-documenting**: Option function names clearly describe what they configure
- **Type-safe**: Compile-time checking of option values
- **Flexible**: Users only specify options they care about
- **Extensible**: Easy to add new options without changing function signature
- **No nil checks**: Avoid passing nil for unused optional parameters

## Advanced Patterns

### Options with Validation

```go
// WithBatchSize validates and sets the batch size
func WithBatchSize(size int) func(*ConsumerOptions) {
    return func(opts *ConsumerOptions) {
        if size <= 0 {
            size = 1 // enforce minimum
        }
        if size > 1000 {
            size = 1000 // enforce maximum
        }
        opts.BatchSize = size
    }
}
```

### Conditional Options

```go
// WithTLS enables TLS with the provided config
func WithTLS(tlsConfig *tls.Config) func(*ClientOptions) {
    return func(opts *ClientOptions) {
        opts.TLSEnabled = true
        opts.TLSConfig = tlsConfig
    }
}
```

### Dependent Options

```go
// WithRetry enables retry with specified attempts and backoff
func WithRetry(maxAttempts int, backoff time.Duration) func(*ClientOptions) {
    return func(opts *ClientOptions) {
        opts.RetryEnabled = true
        opts.MaxRetryAttempts = maxAttempts
        opts.RetryBackoff = backoff
    }
}
```

### Composable Options

```go
// Combine multiple options into one
func WithDefaults() func(*ClientOptions) {
    return func(opts *ClientOptions) {
        WithTimeout(30 * time.Second)(opts)
        WithRetry(3, time.Second)(opts)
        WithTLS(nil)(opts)
    }
}
```

## Option Passing Through Layers

### Within Package (Same Options Type)

When constructors call other constructors, pass options through:

```go
// NewOffsetConsumer wraps NewOffsetConsumerWithProvider
func NewOffsetConsumer(
    saramaClient sarama.Client,
    topic Topic,
    offsetManager OffsetManager,
    messageHandler MessageHandler,
    logSamplerFactory log.SamplerFactory,
    options ...func(*ConsumerOptions),
) Consumer {
    saramaClientProvider := NewSaramaClientProviderExisting(saramaClient)
    return NewOffsetConsumerWithProvider(
        saramaClientProvider,
        topic,
        offsetManager,
        messageHandler,
        logSamplerFactory,
        options..., // Pass through options
    )
}
```

### Across Packages (Custom Types Enable Reuse)

Custom option types can be shared across related constructors:

```go
// In kafka package
type SaramaConfigOption func(config *sarama.Config)

// Used by multiple constructors
func NewSaramaClientProviderByType(
    ctx context.Context,
    providerType SaramaClientProviderType,
    brokers Brokers,
    opts ...SaramaConfigOption,
) (SaramaClientProvider, error) {
    switch providerType {
    case SaramaClientProviderTypeReused:
        return NewSaramaClientProviderReused(brokers, opts...), nil
    case SaramaClientProviderTypeNew:
        return NewSaramaClientProviderNew(brokers, opts...), nil
    default:
        return nil, errors.Errorf(ctx, "unknown provider type: %s", providerType)
    }
}

// External packages can create options
func WithCustomRetry(max int) kafka.SaramaConfigOption {
    return func(config *sarama.Config) {
        config.Producer.Retry.Max = max
        config.Metadata.Retry.Max = max
    }
}
```

**Key points:**
- Use `options...` to unpack and forward variadic options
- Custom types allow external packages to define options
- Maintains consistency across constructor variants
- Enables composition and reuse of options

## Testing with Options

```go
func TestConsumerWithOptions(t *testing.T) {
    consumer := NewOffsetConsumer(
        mockClient,
        "test-topic",
        mockOffsetManager,
        mockHandler,
        mockLogSampler,
        WithTargetLag(500),
        WithDelay(libtime.Duration(time.Second)),
    )

    // Test behavior with configured options
}

func TestConsumerDefaults(t *testing.T) {
    consumer := NewOffsetConsumer(
        mockClient,
        "test-topic",
        mockOffsetManager,
        mockHandler,
        mockLogSampler,
        // No options - test defaults
    )

    // Test default behavior
}
```

## Common Antipatterns to Avoid

### DON'T: Use inline function type instead of custom type

```go
// DON'T DO THIS
func NewConsumer(
    client sarama.Client,
    options ...func(*ConsumerOptions), // Inline type - hard to document
) Consumer {
    // ...
}

// DO THIS instead
type ConsumerOption func(*ConsumerOptions)

func NewConsumer(
    client sarama.Client,
    options ...ConsumerOption, // Custom type - clear and documented
) Consumer {
    // ...
}
```

**Why:** Custom types provide better documentation, easier refactoring, clearer GoDoc, and enable external packages to define options.

### DON'T: Use config struct parameter instead of options

```go
// DON'T DO THIS
type ConsumerConfig struct {
    TargetLag int64
    Delay     libtime.Duration
}

func NewOffsetConsumer(
    client sarama.Client,
    config ConsumerConfig, // Requires all fields
) Consumer {
    // ...
}

// DO THIS instead
func NewOffsetConsumer(
    client sarama.Client,
    options ...func(*ConsumerOptions),
) Consumer {
    // ...
}
```

**Why:** Config struct requires users to fill all fields, options pattern allows selective configuration.

### DON'T: Make options struct private if external options needed

```go
// DON'T DO THIS
type consumerOptions struct { // lowercase - private
    targetLag int64
    delay     libtime.Duration
}

// External packages can't create option functions

// DO THIS instead
type ConsumerOptions struct { // uppercase - exported
    TargetLag int64
    Delay     libtime.Duration
}
```

**Why:** External packages need access to the options struct to create their own option functions.

### DON'T: Use boolean flags for optional behavior

```go
// DON'T DO THIS
func NewConsumer(
    client sarama.Client,
    enableRetry bool,
    enableMetrics bool,
    enableTracing bool,
) Consumer {
    // Boolean parameter explosion
}

// DO THIS instead
func NewConsumer(
    client sarama.Client,
    options ...func(*ConsumerOptions),
) Consumer {
    // Clean interface with options
}

// Usage:
consumer := NewConsumer(
    client,
    WithRetry(),
    WithMetrics(),
    WithTracing(),
)
```

**Why:** Options pattern scales better and reads more clearly than boolean flags.

### DON'T: Return errors from option functions

```go
// DON'T DO THIS
func WithTimeout(timeout time.Duration) func(*Options) error {
    return func(opts *Options) error {
        if timeout < 0 {
            return errors.New("timeout must be positive")
        }
        opts.Timeout = timeout
        return nil
    }
}

// DO THIS instead
func WithTimeout(timeout time.Duration) func(*Options) {
    return func(opts *Options) {
        if timeout < 0 {
            timeout = time.Second // Use sensible default
        }
        opts.Timeout = timeout
    }
}
```

**Why:** Error handling in option functions complicates the pattern. Validate and correct in the option function instead.

### DON'T: Forget to initialize defaults

```go
// DON'T DO THIS
func NewConsumer(options ...func(*ConsumerOptions)) Consumer {
    consumerOptions := ConsumerOptions{} // No defaults!
    for _, option := range options {
        option(&consumerOptions)
    }
    // ...
}

// DO THIS instead
func NewConsumer(options ...func(*ConsumerOptions)) Consumer {
    consumerOptions := ConsumerOptions{
        TargetLag: 0,      // Explicit defaults
        Delay:     0,      // Clear intentions
        BatchSize: 100,    // Sensible values
    }
    for _, option := range options {
        option(&consumerOptions)
    }
    // ...
}
```

**Why:** Explicit defaults make the constructor's behavior clear and predictable.

## Naming Conventions

### Option Type Names

**Recommended Pattern**: Use **singular** for the function type (represents one option):

```go
// ✅ Preferred: Singular "Option" suffix for function type
type ConsumerOption func(*ConsumerOptions)
type ServerOption func(*ServerOptions)
type ClientOption func(*ClientOptions)
type HTTPClientOption func(*HTTPClientConfig)

// ⚠️ Acceptable but less clear: Plural "Options" suffix
type SaramaConfigOptions func(*sarama.Config)
```

**Rationale:**
- The function type represents **one option function**, so singular makes semantic sense
- Clearer distinction between the function type and the config struct
- More consistent with Go naming conventions (interfaces like `io.Reader`, not `io.Readers`)

**Naming formula:**
- Function type: `<Subject>Option` (singular)
  - `ConsumerOption` - modifies consumer configuration
  - `ServerOption` - modifies server configuration
  - `HTTPClientOption` - modifies HTTP client configuration

**Alternative naming patterns:**

```go
// Alternative 1: "Modifier" suffix (more explicit about intent)
type ConsumerModifier func(*ConsumerOptions)
type ServerModifier func(*ServerOptions)

// Alternative 2: "OptionsModifier" suffix (very explicit, but verbose)
type ConsumerOptionsModifier func(*ConsumerOptions)
type ServerOptionsModifier func(*ServerOptions)

// Alternative 3: "ConfigFunc" suffix (explicit about function)
type ConsumerConfigFunc func(*ConsumerOptions)
type ServerConfigFunc func(*ServerOptions)

// Alternative 4: "OptFunc" suffix (concise)
type ConsumerOptFunc func(*ConsumerOptions)
```

**Comparison:**

| Pattern | Example | Pros | Cons |
|---------|---------|------|------|
| `XxxOption` | `ConsumerOption` | Industry standard, concise, widely recognized | Less explicit about action |
| `XxxModifier` | `ConsumerModifier` | Clear intent (modifies), concise | May be ambiguous (modifies what?) |
| `XxxOptionsModifier` | `ConsumerOptionsModifier` | Very explicit | Verbose, redundant with function signature |

**Recommendation:**
- **Default choice**: `XxxOption` (e.g., `ConsumerOption`) - most widely adopted convention in Go, established by Dave Cheney's original pattern
- **Alternative**: `XxxModifier` (e.g., `ConsumerModifier`) - if you prefer more explicit action naming
- **Avoid**: `XxxOptionsModifier` - too verbose when the function signature already shows `func(*ConsumerOptions)`

Choose one pattern and use it consistently throughout your codebase.

### Option Struct Names

```go
// Struct holding configuration, typically plural "Options"
type ConsumerOptions struct {
    TargetLag int64
    Delay     libtime.Duration
}

// Alternative: Singular "Config" suffix
type ServerConfig struct {
    Port    int
    Timeout time.Duration
}
```

### Option Function Names

```go
// Always use "With" prefix followed by the option name
func WithTargetLag(lag int64) ConsumerOption
func WithDelay(delay time.Duration) ConsumerOption
func WithTimeout(timeout time.Duration) ServerOption
func WithTLS(config *tls.Config) ClientOption
```

## Pattern Variations

### Variadic Required and Optional Parameters

When you have both required and optional parameters:

```go
// Required parameters first, then variadic options
func NewConsumer(
    client sarama.Client,        // Required
    topic Topic,                 // Required
    handler MessageHandler,      // Required
    options ...func(*ConsumerOptions), // Optional
) Consumer {
    // ...
}
```

### Options with Different Types

```go
type ServerOptions struct {
    Port      int
    TLSConfig *tls.Config
    Logger    log.Logger
    Metrics   metrics.Registry
}

func WithPort(port int) func(*ServerOptions) {
    return func(opts *ServerOptions) {
        opts.Port = port
    }
}

func WithTLS(config *tls.Config) func(*ServerOptions) {
    return func(opts *ServerOptions) {
        opts.TLSConfig = config
    }
}

func WithLogger(logger log.Logger) func(*ServerOptions) {
    return func(opts *ServerOptions) {
        opts.Logger = logger
    }
}
```

## Real-World Applications

This pattern is particularly useful for:

- **Client constructors**: HTTP clients, database clients, API clients with various timeouts, retries, and configurations
- **Server initialization**: Web servers, gRPC servers with different middleware, TLS, and port configurations
- **Consumer/producer setup**: Message queue consumers with batching, lag management, and retry strategies
- **Service configuration**: Microservices with optional telemetry, tracing, and monitoring
- **Database connections**: Connection pools with optional tuning parameters
- **Testing utilities**: Test fixtures with optional behaviors and configurations

## Comparison with Other Patterns

### vs. Builder Pattern

**Functional Options:**
- Simpler implementation
- No separate builder type needed
- Immutable after construction
- Better for Go idioms

**Builder Pattern:**
- More familiar to Java/C# developers
- Allows validation before build
- More verbose in Go

### vs. Configuration Struct

**Functional Options:**
- Backward compatible additions
- Self-documenting option names
- Optional parameters truly optional
- No nil pointer handling needed

**Configuration Struct:**
- All configuration in one place
- May require nil checks
- Adding fields breaks backward compatibility
- Users must provide all fields or use pointers

## Best Practices

1. **Always define a custom option type**: Use `type XxxOption func(*XxxOptions)` instead of inline `func(*Options)`
2. **Use singular naming for function type**: `ConsumerOption` (singular) not `ConsumerOptions` (plural) - represents one option function
3. **Use plural naming for struct type**: `ConsumerOptions` (plural) - holds multiple configuration values
4. **Use descriptive names**: `WithTimeout`, `WithRetry`, `WithTLS` clearly describe what they configure
5. **Set sensible defaults**: Options should enhance defaults, not be required
6. **Keep options struct exported**: Allow external packages to create option functions
7. **Validate in options**: Handle invalid values gracefully in option functions (don't return errors)
8. **Document defaults**: Clearly document what happens when options are not provided in GoDoc
9. **Group related options**: Consider composite options for common combinations
10. **Maintain backward compatibility**: Never change existing option behavior
11. **Pass through layers**: Forward options when wrapping constructors using `options...`
12. **Be consistent**: Use the same naming pattern throughout your package

This pattern provides a clean, extensible, and idiomatic way to handle optional parameters in Go constructors while maintaining backward compatibility and code clarity.
