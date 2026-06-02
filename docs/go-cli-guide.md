# Go CLI Applications Guide

## Flag Parsing: cobra + slog

### RULE go-cli/cobra-not-stdlib-flag (MUST)

**Owner**: go-quality-assistant
**Applies when**: a Go CLI binary's `main.go` / `pkg/cli/...` imports `flag` (stdlib) and calls `flag.String` / `flag.Bool` / `flag.Parse`, instead of using `github.com/spf13/cobra` (with its `pflag` library).
**Enforcement**: `rules/go/cobra-not-stdlib-flag.yml`
**Why**: Stdlib `flag` uses a process-global `flag.CommandLine` FlagSet. Any transitive dependency that calls `flag.String(...)` in its `init()` adds flags to this global set — and `github.com/golang/glog` is the most common offender, adding 8+ flags (`-alsologtostderr`, `-log_dir`, `-log_backtrace_at`, `-stderrthreshold`, `-v`, `-vmodule`, …) to every binary that transitively imports it. The result: `my-tool --help` displays a wall of irrelevant glog flags before your three actual flags, and the binary accepts those flags at runtime even though no one wanted them. Cobra uses `pflag` which is isolated from `flag.CommandLine` — the global pollution can't reach it, `--help` shows only your flags, and your flag namespace stays under your control.

#### Bad

```go
// main.go — stdlib flag pollutes --help with transitive glog flags
package main

import (
	"flag"
	"fmt"
)

func main() {
	var config string
	flag.StringVar(&config, "config", "", "Path to config")
	flag.Parse()
	fmt.Println(config)
}
// my-tool --help prints --config AND -alsologtostderr, -log_dir, -v, -vmodule, ...
```

#### Good

```go
// main.go
package main

import "github.com/bborbe/my-tool/pkg/cli"

func main() {
	cli.Execute()
}

// pkg/cli/cli.go — cobra/pflag, isolated from flag.CommandLine
func Run(ctx context.Context, args []string) error {
	var config string
	rootCmd := &cobra.Command{
		Use:          "my-tool",
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error { return nil },
	}
	rootCmd.Flags().StringVar(&config, "config", "", "Path to config")
	rootCmd.SetArgs(args)
	return rootCmd.ExecuteContext(ctx)
}
// my-tool --help prints only --config (and cobra's --help itself)
```

**Always use `github.com/spf13/cobra`** for CLI flag parsing, even for single-command binaries.

## Single-Command Binary Pattern

```go
// main.go
package main

import "github.com/bborbe/my-tool/pkg/cli"

func main() {
    cli.Execute()
}
```

```go
// pkg/cli/cli.go
package cli

import (
    "context"
    "fmt"
    "log/slog"
    "os"
    "os/signal"
    "syscall"

    "github.com/spf13/cobra"
)

func Execute() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    sigCh := make(chan os.Signal, 1)
    signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)
    go func() {
        <-sigCh
        cancel()
    }()

    if err := Run(ctx, os.Args[1:]); err != nil {
        fmt.Fprintf(os.Stderr, "Error: %v\n", err)
        os.Exit(1)
    }
}

func Run(ctx context.Context, args []string) error {
    var configPath string
    var verbose bool

    rootCmd := &cobra.Command{
        Use:          "my-tool",
        Short:        "One-line description",
        SilenceUsage: true,
        RunE: func(cmd *cobra.Command, args []string) error {
            // setup logging
            level := slog.LevelWarn
            if verbose {
                level = slog.LevelDebug
            }
            slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: level})))

            // load config, build deps, run...
            return nil
        },
    }

    rootCmd.Flags().StringVar(&configPath, "config", "", "Path to config YAML file")
    rootCmd.Flags().BoolVar(&verbose, "verbose", false, "Enable verbose logging")
    _ = rootCmd.MarkFlagRequired("config")

    rootCmd.SetArgs(args)
    return rootCmd.ExecuteContext(ctx)
}
```

## Multi-Command Binary Pattern

For CLIs with subcommands (like vault-cli), use the same `Execute()`/`Run()` split but add commands via `rootCmd.AddCommand()`:

```go
func Run(ctx context.Context, args []string) error {
    rootCmd := &cobra.Command{
        Use:          "my-cli",
        Short:        "Multi-command CLI",
        SilenceUsage: true,
    }

    rootCmd.PersistentFlags().StringVar(&configPath, "config", "", "Config file path")
    rootCmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose logging")

    rootCmd.AddCommand(createFooCommand(ctx))
    rootCmd.AddCommand(createBarCommand(ctx))

    rootCmd.SetArgs(args)
    return rootCmd.ExecuteContext(ctx)
}
```

## Key Rules

| Rule | Reason |
|------|--------|
| `context.Background()` in `Execute()` only | Single root context, threaded through |
| Signal handling in `Execute()` | Keeps `RunE` focused on business logic |
| `SilenceUsage: true` | Cobra doesn't print usage on runtime errors |
| `MarkFlagRequired` for mandatory flags | Cobra handles missing flag errors cleanly |
| `log/slog` to stderr | Never glog in new projects |
| `Run(ctx, args)` returns error | Testable without `os.Exit` |

## Logging

### RULE go-cli/slog-not-glog-in-new-projects (MUST)

**Owner**: go-quality-assistant
**Applies when**: a *new* Go CLI binary (created after Go 1.21 release; no prior glog usage in the same module) imports `github.com/golang/glog`. Existing glog-using projects are exempt — they should not introduce slog and glog side by side.
**Enforcement**: judgment (semantic — distinguishing "new project" from "existing project mid-migration" requires checking git history / module age; ast-grep partial: `import "github.com/golang/glog"` in any main module without prior glog usage)
**Why**: glog has two structural problems slog doesn't: (1) it registers 8+ flags via stdlib `flag.init()` which pollutes every binary's `--help` output (see `go-cli/cobra-not-stdlib-flag`); (2) it predates structured logging — every log line is a free-form string, so log aggregators can't reliably parse `user_id=<X>` / `request_id=<Y>` fields. `log/slog` (stdlib Go 1.21+) emits structured key-value logs, integrates with `context.Context` for request-scoped fields, and has no `flag` pollution. For *existing* glog projects, the migration cost is real and not always worth it — but new projects should not pay the glog tax.

#### Bad

```go
// New CLI binary in 2026 importing glog
import (
	"github.com/golang/glog"
	"github.com/spf13/cobra"
)

func runE(cmd *cobra.Command, args []string) error {
	glog.Infof("starting with config=%s", configPath)  // free-form, no structured fields
	return nil
}
```

#### Good

```go
// New CLI binary using log/slog
import (
	"log/slog"
	"github.com/spf13/cobra"
)

func runE(cmd *cobra.Command, args []string) error {
	slog.Info("starting", "config", configPath, "verbose", verbose)
	return nil
}
```

Use `log/slog` (stdlib Go 1.21+). See [go-glog-guide.md](go-glog-guide.md) for legacy glog projects only.

## Why Not stdlib `flag`?

The `flag` package uses a global `flag.CommandLine` FlagSet. Any package imported (directly or transitively) that calls `flag.String()`, `flag.Bool()`, etc. in `init()` adds flags to this global set. `github.com/golang/glog` is the most common offender — it adds 8+ flags to every binary that transitively imports it.

Cobra uses its own `pflag` library which is isolated from `flag.CommandLine`.
