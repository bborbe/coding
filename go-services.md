# Go Services

## Key Components
- **ConcurrentRunner**: Manages concurrent execution with limits (`run_concurrent-runner.go`)
- **Trigger System**: Fire/Done pattern for synchronization (`run_trigger.go`, `run_trigger-multi.go`)
- **Error Handling**: Aggregate multiple errors (`run_errors.go`)
- **Utilities**: Retry, skip, delay, panic handling, metrics, logging
