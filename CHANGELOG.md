# Changelog

All notable changes to this project will be documented in this file.

Please choose versions by [Semantic Versioning](http://semver.org/).

* MAJOR version when you make incompatible API changes,
* MINOR version when you add functionality in a backwards-compatible manner, and
* PATCH version when you make backwards-compatible bug fixes.

## v0.4.0

- Add `go-kubernetes-crd-controller-guide.md` covering CRD types, generated clientset, self-install, event-handler pattern, and deliberate exclusions (no Lister, no WaitForCacheSync, no separate YAML manifest)
- Add `/coding:audit-guide` command + `guide-auditor` agent for auditing coding guides against style/structure/indexing/self-containment standards; explicit forbidden-term grep blocks work-context leakage (seibert, octopus, trading domain, personal paths)
- Improve `go-time-injection.md`

## v0.3.1

- Fix agent paths to use canonical plugin path `~/.claude/plugins/marketplaces/coding/docs/`
- Clarify definition-of-done to follow all guides, not just language-specific ones

## v0.3.0

- Rewrite README.md per readme-guide.md (add Overview, Requirements, Quick Start, Contributing; CI and license badges; collapse agents into details; reorder commands; fix license to BSD-2-Clause)
- Add GitHub Actions CI workflow running `make precommit` on push and PRs
- Fix Makefile check-links silent-fail bug (pipe subshell swallowed `EXIT=1`) and allow directory links (`-f` → `-e`); strip anchors before check
- Add `check-json` target validating `.claude-plugin/plugin.json`
- Add sentinel error naming convention (`ErrXxx`) and backwards-compat alias pattern to go-error-wrapping-guide.md

## v0.2.2

- commit: Read project CLAUDE.md as step 2 of detection — honors project-specific release checklists (extra files to bump, version-sync rules) that the generic workflow would otherwise miss

## v0.2.1

- Add go-mod dependency fix guide
- Skip license checks for private repos
- Improve factory guide
- Sync plugin version to v0.2.0 and add release checklist to CLAUDE.md
- Improve /commit to detect unreleased commits since last tag on clean working tree

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
