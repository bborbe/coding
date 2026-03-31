---
allowed-tools: Task, Bash(git diff:+), Bash(git log:+), Bash(git status:+), Bash(git ls-files:+)
argument-hint: "[short|standard|full] [directory]"
description: Perform a comprehensive code review of recent changes
---

## Context

- Current git status: `!git status`
- Recent changes: `!git diff HEAD~1`
- Recent commits: `!git log --oneline -5`
- Current branch: `!git branch --show-current`

## Your task

Perform a code review with configurable depth based on mode.

### Step 1: Parse Arguments

Parse the first argument to determine mode:
- If first arg is `short|quick|fast` → **Short mode** (manual review only)
- If first arg is `full|comprehensive|complete` → **Full mode** (all 13 agents)
- Otherwise → **Standard mode** (4 core agents, default)

Any remaining arguments are treated as the directory path.

### Step 2: Project Detection

Detect project type to determine which specialist agents to invoke:
- **Go project**: Check for `*.go` files or `go.mod`
- **Python project**: Check for `*.py` files or `pyproject.toml`/`requirements.txt`
- **Other languages**: Add detection as needed

### Step 3: Run Automated Checks (All Modes)

**3a. Check for LICENSE file**

Use Glob to check if LICENSE file exists in project root:
```
LICENSE or LICENSE.md or LICENSE.txt
```

Store result for later:
- If missing → flag for license-assistant in Standard mode, report in Short mode
- If present → skip license-assistant in Standard mode

**3b. Run make precommit (if available)**

Check if Makefile exists and has a `precommit` target:
1. Use Read tool to check if Makefile exists (will error if missing)
2. Use Grep tool to search for `^precommit:` pattern in Makefile

If both checks pass, use Task tool with simple-bash-runner agent:
```
Task tool with subagent_type="coding:simple-bash-runner", prompt="cd [directory] && make precommit"
```

This provides automated checks (formatting, linting, tests, security) before running agents. Include the output and any failures in the final report.

If Makefile doesn't exist or lacks `precommit` target, skip this step. If `make precommit` fails, note the failures but continue with the review.

### Step 4: Automated Agent Review

Based on detected mode, invoke agents **in parallel**:

**Short Mode**: No agents - skip to Step 5
- BUT: If LICENSE file is missing (from Step 3a), add to report "Should Fix" section:
  - "Missing LICENSE file"
  - "README missing license section" (check with Grep for `## License` in README.md)

**Standard Mode** (default - core architectural compliance):

*For Go projects:*
1. **go-quality-assistant**: Idiomatic Go patterns, architecture, error handling, context cancellation in loops
2. **go-factory-pattern-assistant**: Factory pattern compliance, zero-business-logic rule (review mode only - no updates)
3. **http-handler-assistant**: HTTP handler organization, inline handler detection, architectural patterns (review mode only - no updates)
4. **go-test-coverage-assistant**: Test coverage gaps, missing tests for critical components (review mode only - no updates)

*For Python projects:*
1. **python-quality-assistant**: Idiomatic Python patterns, type hints, error handling, logging, async safety

*For all projects (conditional):*
5. **license-assistant**: ONLY if LICENSE file is missing (from Step 3a) - review mode only

**Full Mode**:

*Go projects:*
1. **godoc-assistant**: Documentation completeness and GoDoc format
2. **go-quality-assistant**: Idiomatic Go patterns, architecture, error handling
3. **go-test-quality-assistant**: Test file quality, Ginkgo/Gomega patterns, mock usage, test suite setup (review mode only - no updates)
4. **go-security-specialist**: Security vulnerabilities, OWASP compliance, dependency scanning
5. **srp-checker**: Single Responsibility Principle compliance, separation of concerns (review mode only - no updates)
6. **go-version-manager**: Go version currency and consistency across project files (check-only mode)
7. **go-tooling-assistant**: Makefile and tools.go configuration validation (review mode only - no updates)
8. **go-factory-pattern-assistant**: Factory pattern implementation, dependency injection, handler wrapping (review mode only - no updates)
9. **http-handler-assistant**: HTTP handler organization, inline handler detection, architectural patterns (review mode only - no updates)
10. **go-test-coverage-assistant**: Test coverage gaps, missing tests for critical components (review mode only - no updates)

*Python projects:*
1. **python-quality-assistant**: Code quality, type hints, error handling

*All projects:*
11. **license-assistant**: LICENSE file, README license section (ALWAYS run in full mode, review mode only)
12. **readme-quality-assistant**: README.md quality and completeness (review mode only - no updates)
13. **shellcheck-assistant**: Shell script quality, security, and best practices
14. **context7-library-checker**: Check library usage against up-to-date docs, detect deprecated APIs (review mode only)

Run agents concurrently using multiple Task tool calls in a single message for maximum efficiency.

### Step 5: Consolidated Report

Merge all findings into a unified report with priority-ranked sections:

#### Must Fix (Critical)
- Security vulnerabilities (hardcoded credentials, SQL injection, etc.)
- Context violations (context.Background() in business logic)
- `fmt.Errorf` usage — must use `errors.Wrapf(ctx, err, ...)` or `errors.Errorf(ctx, ...)` from `github.com/bborbe/errors`
- Bare `return err` without wrapping — must use `errors.Wrapf(ctx, err, "description")`
- Concurrency bugs (infinite loops without ctx.Done(), race conditions)
- Raw `go func()` or `go methodName()` in production code — must use `github.com/bborbe/run` for proper context cancellation and error propagation:
  - Parallel tasks: `run.CancelOnFirstFinish`, `run.CancelOnFirstError`, `run.All`, `run.Sequential`
  - Bounded concurrency: `run.NewConcurrentRunner(maxConcurrent)` instead of manual semaphore + goroutine pool
  - Background fire-and-forget: `run.NewBackgroundRunner(ctx)` with parallel skip instead of raw `go func()`
  - Signal handling: `run.ContextWithSig(ctx)` instead of manual `signal.Notify` + context cancel boilerplate
- Raw channel producer/consumer patterns — must use `github.com/bborbe/collection` (`ChannelFnMap`, `ChannelFnList`, `ChannelFnCount`) instead of manual `make(chan T)` + goroutine loops
- Data correctness issues
- Transaction-inside-transaction deadlocks:
  - Command executors receive `tx libkv.Tx` but don't pass to dependencies
  - Dependencies open own transactions (`db.View()`, `db.Update()`) instead of accepting `tx` parameter
  - Check if functions called from tx context open new transactions (grep for `db.View\|db.Update` in functions that should accept tx)
  - Verify command executor uses `needsTx: true` when dependencies need transaction access
- Circular package imports (any cycle in the pkg/* import graph)
- Wrong dependency direction (pkg/ importing any pkg/* subpackage — shared base must not depend on subpackages)
- Business logic in factory functions (loops, switch statements, complex conditionals)
- SRP violations: God objects, functions mixing 3+ concerns (validation + persistence + logging)
- Outdated Go versions (2+ minor versions behind)
- Missing test suite files (packages with tests but no *_suite_test.go)
- Manual mock implementations (must use Counterfeiter)
- Direct time package usage in tests (causes flaky tests)

#### Should Fix (Important)
- Error handling issues (missing wrapping, wrong patterns)
- Architectural violations (constructor patterns, interface usage)
- SRP violations: Business logic mixed with I/O, multiple database operations in single method
- Factory methods outside pkg/factory/ package
- Inline handlers in main.go (should be in pkg/handler/)
- Handler files in pkg/ instead of pkg/handler/ (e.g., pkg/handler_upload.go → pkg/handler/upload.go)
- Raw `http.Handler`/`ServeHTTP` implementations instead of `libhttp.WithError` or `libhttp.WithErrorTx`
- Missing factory methods for handlers
- Incorrect handler wrapping patterns
- Wrong file layout ordering: constructor (`NewFoo`) below struct definition (must be above: Interface → Constructor → Struct → Methods)
- Missing tests for critical components (command executors, message handlers, HTTP handlers)
- Missing mocks/ directories for services/libraries
- Missing documentation for exported items
- README missing critical sections (installation, examples, API docs)
- Performance bottlenecks
- Go version inconsistencies across project files
- Go version 1 minor version behind latest stable
- Missing critical Makefile targets (test, check, precommit)
- tools.go missing required development dependencies
- Deprecated tools in tools.go (e.g., golang.org/x/lint/golint)
- Missing GitHub workflows (ci.yml, claude-code-review.yml, claude.yml)
- Missing license headers on source files
- LICENSE file outdated or missing
- README missing license section
- Shell script errors and warnings from shellcheck
- Wrong test package naming (internal instead of external *_test packages)
- Missing test suite setup (time.Local, format.TruncatedDiff, suiteConfig.Timeout)
- Wrong Counterfeiter configuration:
  - **Check interface location FIRST**: lib/ interfaces → lib/mocks/ | service pkg/ interfaces → {service}/mocks/
  - **Never generate mocks from vendor/**: if an interface comes from a lib (e.g. `lib-cdb`), import the existing mocks from `lib/{name}/mocks/` instead of regenerating with counterfeiter from `../vendor/`. Search source repos (`$OCTOPUS_BASE/lib/`) for existing `mocks/` directories before generating new fakes
  - Verify fake name has no "Fake"/"Mock" prefix (use `--fake-name UserService` NOT `--fake-name FakeUserService`)
  - Check output path matches interface location (lib interface in lib/mocks, service interface in service/mocks)
  - Counterfeiter directives must be placed directly above the interface they mock, not grouped at file top
- Mock variable naming with "mock" prefix in tests

#### Nice to Have (Optional)
- Style improvements
- Minor documentation enhancements
- README style and formatting improvements
- Code organization suggestions
- SRP violations: Large structs (>10 methods), long functions (>40 lines), naming suggesting multiple responsibilities
- Optional optimizations
- Go patch version updates
- Additional Makefile targets for convenience (e.g., make ensure)
- Tool version updates in tools.go
- License year range updates (single year → year range for old files)
- LICENSE file year updates to current year
- Handler naming convention improvements (kebab-case file names)
- Factory naming convention refinements
- Shell script style improvements (shellcheck info/style level)
- Missing //go:generate directives in test suite files
- Missing copyright headers in test files

### Step 6: Next Steps Recommendation

**For Go projects only**: If the `go-test-coverage-assistant` agent reported missing tests in the consolidated report, add a "Next Steps" section suggesting the appropriate `/go-write-test` command.

**Detection criteria**:
- Check if "Missing tests for critical components" appears in the "Should Fix (Important)" section
- Check if specific files or components were listed as lacking test coverage

**If missing tests detected**, add this section to the report:

```markdown
## Next Steps

### Missing Tests Detected
Test coverage gaps were identified in the codebase.

Quick fixes:
- `/go-write-test basic` - Add minimal tests for git-modified files (fastest)
- `/go-write-test standard` - Add comprehensive tests with error cases
- `/go-write-test integration pkg/[package]` - Add integration tests for specific package

Run `/go-write-test basic` to quickly add tests for your recent changes.
```

**If no missing tests detected**, skip this section entirely.

**Customization**:
- If specific packages were identified (e.g., pkg/user, pkg/order), mention them in the suggestion
- If many files need tests, emphasize `/go-write-test basic` for quick batch coverage
- If few critical functions need tests, emphasize `/go-write-test standard pkg/[package]` for comprehensive coverage

### Step 7: Manual Review (All Projects)

For non-Go projects or additional analysis, focus on:

1. **Code Quality**: Check for readability, maintainability, and adherence to best practices
2. **Security**: Look for potential vulnerabilities or security issues
3. **Performance**: Identify potential performance bottlenecks
4. **Testing**: Assess test coverage and quality
5. **Documentation**: Check if code is properly documented

Provide specific, actionable feedback with line-by-line comments where appropriate.
