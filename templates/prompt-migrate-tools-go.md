---
status: draft
---

# Migrate from tools.go to tools.env + Makefile @version pattern

<summary>
- This Go library currently pins CLI tool versions via `tools.go` (build tag `tools`), which pollutes `go.mod` with hundreds of unrelated transitive dependencies.
- Migrate to the `tools.env` + Makefile `@version` pattern: each tool invocation becomes `go run pkg@$(VERSION)` driven by a flat `tools.env` file at the repo root.
- After migration, `go.mod` shrinks dramatically (typically from 400+ lines to under 30) and contains only real direct/indirect deps of the library.
- The `replace` block (cellbuf, go-header, go-diskfs, ginkgolinter/types) becomes unnecessary because the conflicting tool deps are no longer in the graph. The `updater` tool will auto-drop these on the next `updater all` run because `tools.go` is gone.
- All `make` targets keep working: `make precommit`, `make test`, `make lint`, `make check`, etc.
- The pilot for this migration was `bborbe/errors v1.5.11` (commit `release v1.5.11` on master).
</summary>

<objective>
Apply the canonical `tools.env` + `@version` pattern to this repo so it stops polluting downstream `go.mod` files via tools.go cascade. Keep all developer-facing make targets working identically. Reduce `go.mod` to its true direct/indirect deps.
</objective>

<context>
Read `~/Documents/workspaces/coding/docs/go-tools-versioning-guide.md` first — this is the authoritative reference for the pattern, the migration steps, and the pitfalls. The canonical templates live at `~/Documents/workspaces/coding/templates/{tools.env,Makefile.library,Makefile.service}`.

Key concepts (from the guide):

- `tools.go` imports CLI tools under build tag `tools`. This pins versions in `go.mod` BUT pulls every transitive dep of every tool into the project. Cascades through library imports.
- `tools.env` declares versions as Make variables (e.g. `GOLANGCI_LINT_VERSION ?= v2.11.4`). Makefile `include`s it.
- Each Makefile tool invocation uses `go run pkg@$(VERSION)` instead of `go run -mod=mod pkg`. This builds the tool in a temporary module — the host project's `go.mod` is untouched.
- `//go:generate` directives use hardcoded `@version` (counterfeiter is the only common case): `//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate`.
- After deleting `tools.go`, write a minimal known-good `go.mod` (just direct deps + `go 1.x`), then `go mod tidy` repopulates legitimate indirects.
- `osv-scanner` must be pinned to `@v2.3.1` — newer versions are broken upstream.

Pilot evidence: `bborbe/errors v1.5.11` — go.mod went from 443 lines to 24 lines, all `make check` tools functional, no replaces needed.
</context>

<requirements>
1. **Sync `tools.env` from canonical.** Copy `~/Documents/workspaces/coding/templates/tools.env` to the repo root. This is the source of truth for tool versions across all bborbe Go projects.

2. **Update `Makefile`.** Add `include tools.env` near the top. Replace every `go run -mod=mod pkg` with `go run pkg@$(VERSION_VAR)` using the variable from `tools.env`. Specifically:

   - `go run -mod=mod github.com/shoenig/go-modtool` → `go run github.com/shoenig/go-modtool@$(GO_MODTOOL_VERSION)`
   - `go run -mod=mod github.com/incu6us/goimports-reviser/v3` → `go run github.com/incu6us/goimports-reviser/v3@$(GOIMPORTS_REVISER_VERSION)`
   - `go run -mod=mod github.com/segmentio/golines` → `go run github.com/segmentio/golines@$(GOLINES_VERSION)`
   - `go run -mod=mod github.com/golangci/golangci-lint/cmd/golangci-lint` (or `/v2/...`) → `go run github.com/golangci/golangci-lint/v2/cmd/golangci-lint@$(GOLANGCI_LINT_VERSION)` (note the `/v2/` path)
   - `go run -mod=mod github.com/kisielk/errcheck` → `go run github.com/kisielk/errcheck@$(ERRCHECK_VERSION)`
   - `go run -mod=mod golang.org/x/vuln/cmd/govulncheck` → `go run golang.org/x/vuln/cmd/govulncheck@$(GOVULNCHECK_VERSION)`
   - `go run -mod=mod github.com/google/osv-scanner/v2/cmd/osv-scanner` → `go run github.com/google/osv-scanner/v2/cmd/osv-scanner@$(OSV_SCANNER_VERSION)` (this resolves to v2.3.1 — the last working version)
   - `go run -mod=mod github.com/securego/gosec/v2/cmd/gosec` → `go run github.com/securego/gosec/v2/cmd/gosec@$(GOSEC_VERSION)`
   - `go run -mod=mod github.com/google/addlicense` → `go run github.com/google/addlicense@$(ADDLICENSE_VERSION)`

   Keep `go vet -mod=mod` and `go test -mod=mod` and `go list -mod=mod` unchanged — these are not tools, they're built-in Go subcommands. Keep `go generate -mod=mod` unchanged for the same reason.

3. **Update `//go:generate` directives.** Find every file containing `//go:generate go run -mod=mod github.com/maxbrunsfeld/counterfeiter/v6 -generate` and replace with `//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6@v6.12.2 -generate`. Do NOT use `$(COUNTERFEITER_VERSION)` here — `go generate` runs from the package directory and the simplest stable approach is hardcoding the pinned version at the directive site. Versions stay consistent with `tools.env` by convention.

4. **Delete `tools.go`** from the repo root.

5. **Reset `go.mod` to a minimal known-good state, then tidy.** This is the critical step — running `go mod tidy -e` on the polluted go.mod can truncate it. Instead:

   a. Identify the real direct deps by reading the source files (excluding `tools.go` which is now deleted, and excluding `_test.go` files for the require — those go in a separate require block).
   b. Manually rewrite `go.mod` as: `module ...`, `go 1.x`, then a single `require (...)` block listing only direct deps that production code actually imports. Drop the entire `replace (...)` block. Drop the `// indirect` block — `go mod tidy` will repopulate it.
   c. Run `go mod tidy`. Verify the new `go.mod` is dramatically smaller (target: under 30 lines for a library; services may have more depending on real deps).
   d. Verify go.sum was regenerated.

6. **Run `make precommit`.** Must pass end-to-end. If `make osv-scanner` reports actual vulnerabilities (real CVEs in deps), that's a separate concern — add suppressions to `.osv-scanner.toml` if appropriate, OR file a follow-up to update the affected dep, but do NOT bypass the scanner.

7. **Verify `mocks/` regeneration works.** `make generate` should run successfully and produce identical (or semantically equivalent) mock output to the previous run. Counterfeiter via `@version` works the same as via tools.go binding.

8. **Do NOT touch the existing `replace (...)` block manually.** It will be removed by the `updater` tool on the next `updater all` run automatically (because `tools.go` no longer exists). If a real replace is genuinely needed for non-tools.go reasons (extremely rare), keep that one entry; remove the rest.

9. **Commit + tag.** Use the `/coding:commit` workflow. The CHANGELOG entry should describe the migration: "Migrate to tools.env + Makefile @version pattern; remove tools.go and obsolete replace block."
</requirements>

<verification>
The following must all hold after the migration:

- `tools.env` exists and matches `~/Documents/workspaces/coding/templates/tools.env` content
- `tools.go` does NOT exist
- `Makefile` includes `tools.env` near the top
- `Makefile` contains zero `go run -mod=mod ` invocations (all replaced with `go run pkg@$(VAR)`)
- All `//go:generate` directives use `@version` syntax for counterfeiter
- `go.mod` does not contain a `replace (` block (or contains at most one truly-needed replace, not the four cellbuf/go-header/go-diskfs/ginkgolinter)
- `go.mod` line count is dramatically reduced (typically 5x to 50x smaller)
- `make precommit` passes
- `make test` passes with the same coverage as before the migration
- `git diff --stat go.mod` shows the file shrinking by hundreds of lines
</verification>

<out-of-scope>
- Don't bump dependency versions beyond what `go mod tidy` does naturally
- Don't refactor production code
- Don't touch `vendor/` (gitignored)
- Don't add new linters or remove existing ones
- Don't change Go language version (`go 1.x` directive)
</out-of-scope>
