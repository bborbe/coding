# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## v0.2.0

- Add readme-guide.md and claude-md-guide.md for README.md vs CLAUDE.md separation
- Update documentation-guide.md with CLAUDE.md overview and links to specific guides

## v0.1.0
- Add finder agents for self-contained check-guides
- Add templates, remove personal paths from agents
- Add vscode and intellij skills, archive old commands
- Add go-write-test, improve-guide, go-version commands with agents
- Remove personal paths from shared plugin docs
- Add 6 metrics patterns to prometheus guide
- Split go-quality-assistant into focused agents aligned with docs
- Add vendor counterfeiter detection to go-test-quality-assistant
- Add file organization rules to go-quality-assistant

## v0.0.3
- Make plugin self-contained: add all agents referenced by commands
- Add coding: prefix to agent references in commands
- Add pre-implementation-assistant, license-assistant, godoc-assistant, go-version-manager, shellcheck-assistant

## v0.0.2
- Trim to 4 essential commands: code-review, pr-review, check-guides, commit
- Trim to 12 agents required by those commands
- Remove 9 non-essential commands and 10 unused agents

## v0.0.1
- Restructure as Claude Code plugin with .claude-plugin/ metadata
- Move all guides into docs/ subdirectory
- Add 12 shareable slash commands (code-review, pr-review, check-guides, etc.)
- Add 22 shareable agents (go-quality-assistant, srp-checker, etc.)
- Add llms.txt index for AI agent discovery
- Add Makefile with link validation
- Rewrite README as human-first reference with tables
