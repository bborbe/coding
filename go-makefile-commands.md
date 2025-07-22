# Go Makefile Commands

## Build and Testing
- `make`: Run full precommit checks (default target)
- `make precommit`: Run format, generate, test, check, and addlicense
- `make test`: Run tests with coverage and race detection
- `make ensure`: Clean and verify Go modules

## Code Quality
- `make format`: Format Go code and fix imports
- `make generate`: Generate mocks and other code
- `make check`: Run vet, errcheck, and vulncheck
- `make vet`: Run Go vet
- `make errcheck`: Check for unchecked errors
- `make vulncheck`: Check for security vulnerabilities
- `make addlicense`: Add license headers to Go files