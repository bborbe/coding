# Go Factory Pattern Guide

Factory functions compose objects by wiring dependencies together. They contain **zero business logic** - only constructor calls.

## 1. Core Principles

**Factories should only:**
- Pass dependencies to constructors
- Build nested object trees
- Return interface types

**Factories must NOT:**
- Contain loops, conditionals, or business logic
- Have inline function implementations with logic
- Mix object creation with execution

## 2. File Organization

**Services/Applications:**
```
pkg/factory/factory.go    # All factory functions in ONE file
pkg/thing.go              # Implementation types live in pkg/ (flat)
pkg/big_area/thing.go     # If pkg/ grows large, group into pkg/<subpkg>/
```

**Libraries:**
```
lib/mylib/factory.go      # NOT lib/mylib/pkg/factory/factory.go
```

**Rule:** Implementation types (structs, interfaces, methods with logic) MUST NOT live inside `pkg/factory/`. The factory package is wiring-only. Impl goes in `pkg/` directly, or in a `pkg/<subpkg>/` sibling package if `pkg/` becomes too large. A file named `pkg/factory/roundtripper.go` containing a `mocoRoundTripper` struct is wrong — move it to `pkg/roundtripper/` (or `pkg/roundtripper.go`).

**Naming:**
- Factories: `Create*` prefix (e.g., `CreateUserService`)
- Constructors: `New*` prefix (e.g., `NewUserService`) - in implementation files only

## 3. Good Factory Examples

### Simple Composition
```go
func CreateUserService(db DB, validator Validator) UserService {
    return NewUserService(db, validator, log.DefaultSamplerFactory)
}
```

### Nested Composition (Middleware/Decorators)
```go
func CreateMessageHandler(db DB) MessageHandler {
    return NewMessageHandlerBatchTxUpdate(
        db,
        NewMessageHandlerBatchTx(
            NewMessageHandlerTxSkipErrors(
                NewMessageHandlerTxMetrics(
                    NewUserMessageHandlerTx(
                        CreateStoreUserHandlerTx(),
                        log.DefaultSamplerFactory,
                    ),
                    NewMetrics(),
                ),
                log.DefaultSamplerFactory,
            ),
        ),
    )
}
```

### Run Function Wrapper
```go
func CreateConsumerRun(provider kafka.SaramaClientProvider, db DB) run.Func {
    return func(ctx context.Context) error {
        return kafka.NewOffsetConsumer(
            provider,
            "topic",
            CreateOffsetManager(db),
            CreateMessageHandler(db),
        ).Consume(ctx)
    }
}
```

**Acceptable anonymous function:** Only when it directly calls a method (like `.Consume(ctx)`) with no additional logic.

### List Composition
```go
func CreateAuthenticators(cookie CookieGenerator, oauth GoogleOAuth) []Authenticator {
    return []Authenticator{
        NewGoogleAuthenticator(cookie, oauth),
        NewBasicAuthenticator(NewUserProvider()),
    }
}
```

## 4. Bad Factory Patterns

### ❌ DON'T: Inline Business Logic
```go
// ❌ BAD: Loop, error handling, nested anonymous functions
func CreateIndexHandler(db DB, index Index) MessageHandler {
    return NewMessageHandlerBatchTxView(
        db,
        MessageHandlerBatchTxFunc(
            func(ctx context.Context, tx Tx, messages []*Message) error {
                batch := index.NewBatch()
                indexer := NewEventIndexer(NewUserStoreTx(), NewBatchIndex(batch))

                handler := NewUserMessageHandlerTx(
                    UserHandlerTxFunc(
                        func(ctx context.Context, tx Tx, user User) error {
                            return indexer.Add(ctx, tx, user)
                        },
                        func(ctx context.Context, tx Tx, id UserID) error {
                            return indexer.Remove(ctx, tx, id)
                        },
                    ),
                )

                for _, message := range messages {
                    if err := handler.ConsumeMessage(ctx, tx, message); err != nil {
                        return errors.Wrap(ctx, err, "consume failed")
                    }
                }

                return index.Batch(batch)
            },
        ),
    )
}
```

**Why bad:**
- For loop iterating messages
- Inline anonymous functions with logic
- Error handling inside factory

### ✅ DO: Move Implementation to Separate File
```go
// In factory.go:
func CreateIndexHandler(db DB, index Index) MessageHandler {
    return NewMessageHandlerBatchTxView(db, NewUserIndexHandler(index))
}

// In user_index_handler.go:
type userIndexHandler struct {
    index Index
}

func NewUserIndexHandler(index Index) MessageHandlerBatchTx {
    return &userIndexHandler{index: index}
}

func (h *userIndexHandler) Handle(ctx context.Context, tx Tx, messages []*Message) error {
    batch := h.index.NewBatch()
    indexer := NewEventIndexer(NewUserStoreTx(), NewBatchIndex(batch))

    handler := NewUserMessageHandlerTx(
        UserHandlerTxFunc(
            func(ctx context.Context, tx Tx, user User) error {
                return indexer.Add(ctx, tx, user)
            },
            func(ctx context.Context, tx Tx, id UserID) error {
                return indexer.Remove(ctx, tx, id)
            },
        ),
    )

    for _, message := range messages {
        if err := handler.ConsumeMessage(ctx, tx, message); err != nil {
            return errors.Wrap(ctx, err, "consume failed")
        }
    }

    return h.index.Batch(batch)
}
```

## 5. Usage in main.go

Factories wire the application together:

```go
func main() {
    db := bolt.NewDB(dbPath)
    currentTime := time.NewCurrentDateTime()
    producer := kafka.NewSyncProducer(brokers)

    // Use factories to build services
    userService := pkg.CreateUserService(db, currentTime, producer)

    router := mux.NewRouter()
    router.Handle("/users", pkg.CreateUserHandler(userService))

    http.NewServer(addr, router).ListenAndServe(ctx)
}
```

## 6. Common Antipatterns

### DON'T: Execute Logic in Factory
```go
// ❌ BAD
func CreateService(db DB) Service {
    service := NewService(db)
    service.Initialize()  // Execution!
    return service
}
```

### DON'T: Create Singletons
```go
// ❌ BAD
var instance Service

func CreateService(db DB) Service {
    if instance == nil {
        instance = NewService(db)
    }
    return instance
}
```

### DON'T: Split Factories Across Files
```go
// ❌ BAD
pkg/factory/user_factory.go
pkg/factory/handler_factory.go

// ✅ GOOD
pkg/factory/factory.go  // All factories in one file
```

## Summary

**Factory Checklist:**
- ✅ All factories in single file: `pkg/factory/factory.go` or `lib/{name}/factory.go`
- ✅ Use `Create*` prefix
- ✅ Only constructor calls - zero business logic
- ✅ Move complex logic to implementation files in `pkg/` (or `pkg/<subpkg>/` if `pkg/` is large) — NEVER inside `pkg/factory/`
- ✅ Return interface types
