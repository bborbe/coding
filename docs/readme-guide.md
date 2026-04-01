# README.md Guide

Guide for writing README.md files. README.md is for humans browsing GitHub — it explains what the project does, how to install it, and how to use it.

## README.md vs CLAUDE.md

| | README.md | CLAUDE.md |
|---|---|---|
| **Audience** | Humans (users, contributors) | AI agents coding in the project |
| **Purpose** | What it does, install, use | How to change the code safely |
| **Contains** | Features, install, usage, config, license | Build commands, architecture map, constraints |
| **Never contains** | Architecture internals, workflow rules | Install instructions, feature marketing |

## Project Types

### Public Projects (Libraries, Tools, CLIs)

Comprehensive (200-400 lines). Convince users to adopt.

**Required sections:**
- Description (1-2 sentences)
- Badges (GoDoc, Go Report Card, CI)
- Installation
- Quick Start (copy-paste example)
- Usage / Commands
- Configuration (if applicable)
- Documentation links (if docs/ exists)
- License

**Optional sections:**
- Features list
- Shell completion
- Plugin/integration info
- Requirements
- Development (brief — details in CLAUDE.md)

### Internal Projects (Multi-Service)

Minimal (50-100 lines). Quick reference for daily work.

**Required sections:**
- One-line purpose
- How to run locally
- Link to docs/

**Optional sections:**
- Common commands
- Quick configuration reference

## Templates

### Public CLI Tool

```markdown
# tool-name

[![Go Reference](https://pkg.go.dev/badge/github.com/bborbe/tool-name.svg)](https://pkg.go.dev/github.com/bborbe/tool-name)
[![CI](https://github.com/bborbe/tool-name/actions/workflows/ci.yml/badge.svg)](https://github.com/bborbe/tool-name/actions/workflows/ci.yml)
[![Go Report Card](https://goreportcard.com/badge/github.com/bborbe/tool-name)](https://goreportcard.com/report/github.com/bborbe/tool-name)

One-sentence description of what this tool does.

## Overview

2-3 sentences expanding on the description. What problem does it solve? Who is it for?

## Installation

```bash
go install github.com/bborbe/tool-name@latest
```

## Quick Start

```bash
# Minimal example showing core functionality
tool-name do-something --flag value
```

## Usage

### command-a

```bash
tool-name command-a [flags]
tool-name command-a --verbose    # With explanation
```

### command-b

```bash
tool-name command-b [flags]
```

## Configuration

[Config file format, env vars, or flags — whatever the tool needs]

## Documentation

- [Topic A](docs/topic-a.md)
- [Topic B](docs/topic-b.md)

## Development

```bash
make test      # Run tests
make precommit # Full development workflow
```

## License

BSD-2-Clause
```

### Public Go Library

```markdown
# library-name

[![Go Reference](https://pkg.go.dev/badge/github.com/bborbe/library-name.svg)](https://pkg.go.dev/github.com/bborbe/library-name)
[![Go Report Card](https://goreportcard.com/badge/github.com/bborbe/library-name)](https://goreportcard.com/report/github.com/bborbe/library-name)

One-sentence description of the library's purpose and value.

## Features

- **Feature 1** - Brief explanation
- **Feature 2** - Brief explanation
- **Feature 3** - Brief explanation

## Installation

```bash
go get github.com/bborbe/library-name
```

## Quick Start

```go
import "github.com/bborbe/library-name"

// Simple, copy-paste ready example
result := name.DoSomething()
```

## Usage

### Basic Usage

```go
// Most common use case
```

### Advanced Usage

```go
// More complex scenarios
```

## API Reference

Complete API documentation: [pkg.go.dev](https://pkg.go.dev/github.com/bborbe/library-name)

## Testing

```bash
make test      # Run all tests
make precommit # Format, test, lint
```

## Requirements

- Go 1.24+

## License

BSD-2-Clause
```

### Public Python Tool

```markdown
# tool-name

One-sentence description.

## Install

```bash
uv tool install git+https://github.com/bborbe/tool-name
```

## Upgrade

```bash
uv tool upgrade tool-name
```

## Quick Start

```bash
tool-name /path/to/project
```

## Commands

| Command | Description |
|---------|-------------|
| `command-a` | What it does |
| `command-b` | What it does |

## How It Works

Brief explanation of the workflow (numbered steps).

## Requirements

- [uv](https://docs.astral.sh/uv/)
- Other requirements

## Documentation

- [Topic A](docs/topic-a.md)
- [Topic B](docs/topic-b.md)

## License

BSD-2-Clause
```

### Internal Service (Monorepo)

```markdown
# service-name

> Brief one-line description

Part of the [project-name](../) monorepo.

## Running Locally

```bash
make run
```

## Configuration

Key environment variables:
- `SERVICE_PORT` - HTTP port (default: 8080)
- `DATABASE_URL` - Database connection string

See [../docs/configuration.md](../docs/configuration.md) for full details.

## Documentation

- [Root project docs](../docs/)
```

## Section Guidelines

### Badges

Only include badges you actively maintain:
- **Go Reference** — always for public Go projects
- **CI** — only if CI is public and stable
- **Go Report Card** — always for public Go projects

### Installation

Show the simplest install path. One command if possible.

### Usage / Commands

- Use a table for CLI tools with many commands
- Show real, copy-paste examples
- Group related commands under subheadings

### Development

Keep brief in README (1-3 commands). Detailed dev setup belongs in CLAUDE.md or docs/development.md.

### Plugin/Extension Section

If the project ships a Claude Code plugin, include install + command table:

```markdown
## Claude Code Plugin

```bash
claude plugin marketplace add bborbe/tool-name
claude plugin install tool-name
```

| Command | Description |
|---------|-------------|
| `/tool:command-a` | What it does |
| `/tool:command-b` | What it does |
```

## Common Mistakes

### Architecture in README

README explains what and how to use. Architecture belongs in CLAUDE.md (for agents) or docs/architecture.md (for humans who need depth).

### Duplicating CLAUDE.md content

If README lists build commands and CLAUDE.md lists build commands, they drift. README gets a brief "Development" section; CLAUDE.md gets the full details.

### Too long for internal projects

Internal READMEs should be 50-100 lines. The team already knows why the project exists.

### Missing examples

Every command in a CLI tool should have at least one copy-paste example showing real usage, not just `--help` output.

## Checklist

Before committing a README:

- [ ] One-line description at the top
- [ ] Install command (public projects)
- [ ] At least one copy-paste Quick Start example
- [ ] All CLI commands documented with examples
- [ ] Configuration section (if applicable)
- [ ] License at the bottom
- [ ] No architecture internals (belongs in CLAUDE.md)
- [ ] No stale content (removed features, old commands)
- [ ] Badges link to real, working URLs (public projects)
