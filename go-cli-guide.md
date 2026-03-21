# Go CLI Applications Guide

## Flag Parsing: cobra + slog

**NEVER use stdlib `flag` package** — transitive dependencies like `github.com/golang/glog` register flags via `init()`, polluting `--help` output with unwanted flags (`-alsologtostderr`, `-log_dir`, `-v`, etc.).

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

Use `log/slog` (stdlib Go 1.21+). See [go-glog-guide.md](go-glog-guide.md) for legacy glog projects only.

## Why Not stdlib `flag`?

The `flag` package uses a global `flag.CommandLine` FlagSet. Any package imported (directly or transitively) that calls `flag.String()`, `flag.Bool()`, etc. in `init()` adds flags to this global set. `github.com/golang/glog` is the most common offender — it adds 8+ flags to every binary that transitively imports it.

Cobra uses its own `pflag` library which is isolated from `flag.CommandLine`.
