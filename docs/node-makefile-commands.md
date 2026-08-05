# Node Makefile Commands

Standard build targets for a Node.js service, and the include layout that keeps them consistent across projects.

## Goal

Every Node service exposes the same entry points, so a developer or agent arriving at an unfamiliar repo can run `make precommit` without reading anything first. The targets are the contract; the commands behind them may vary with the project's tooling.

Scope: backend services. Frontend applications use a build-oriented variant — see [Frontend Variant](#frontend-variant).

## Include Layout

The Makefile is split by concern, and each fragment is included by the root:

```makefile
include Makefile.variables
include Makefile.precommit
include Makefile.docker
include example.env

SERVICE = organisation/service-name
```

| File | Owns |
|------|------|
| `Makefile` | Includes, `SERVICE`, `all`, `install`, `run`, `clean-local` |
| `Makefile.variables` | Shared variables (image registry, version) |
| `Makefile.precommit` | `precommit`, `format`, `lint`, `formatcheck`, `test`, `check`, `audit`, `trivy` |
| `Makefile.docker` | Image build and push |
| `Makefile.k8s` | Deployment targets (included by `k8s/Makefile`) |

Splitting them means a fragment can be copied to a new service unchanged, and a change to the security gates lands in one file rather than in every repo's monolithic Makefile.

## Required Targets

```makefile
.PHONY: all
all: precommit

.PHONY: install
# Install dependencies from the lockfile
install:
	@npm ci

.PHONY: run
# Run the application
run:
	node src/index.js

.PHONY: precommit
# Everything that must pass before a commit
precommit: install format test check
	@echo "All precommit checks passed"

.PHONY: format
# Format code, autofix what the linter can
format:
	npx prettier --write .
	npx eslint --fix . || true

.PHONY: lint
lint:
	npx eslint .

.PHONY: formatcheck
# Verify formatting without rewriting (used in CI)
formatcheck:
	npx prettier --check .

.PHONY: test
# Run tests with the built-in node test runner
test:
	node --test

.PHONY: check
# Lint, formatting and security gates
check: lint formatcheck audit trivy

.PHONY: clean-local
clean-local:
	rm -rf node_modules coverage
```

### RULE node/make/required-targets (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: a Node service repository has no `Makefile`, or its `Makefile` is missing any of `install`, `precommit`, `format`, `lint`, `test`, `check`.
**Enforcement**: judgment — the agent reads the Makefile and its includes for the target set.
**Trigger**: Makefile, Makefile.*, package.json
**Why**: the target names are the interface every other tool assumes — CI, the review pipeline, and agents working in the repo all invoke `make precommit` without inspecting the project first. A repo that names its targets differently forces every caller to special-case it, and in practice means the checks stop being run at all.

### RULE node/make/install-from-lockfile (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: the `install` target runs `npm install` rather than `npm ci`.
**Enforcement**: judgment — the agent reads the `install` recipe.
**Trigger**: Makefile, Makefile.*
**Why**: `npm install` may resolve versions not in the lockfile and rewrites `package-lock.json` as a side effect, so a build can silently pick up a different dependency tree than the one that was reviewed. `npm ci` installs exactly the lockfile and fails when the two disagree, which is the behaviour a reproducible build needs.

## Security Gates

Two scanners run as part of `check`:

```makefile
.PHONY: audit
# Dependency vulnerabilities from the npm advisory database.
# Fails on high/critical only: moderate findings in dev-only transitive deps
# would otherwise block every commit for something unreachable at runtime.
audit:
	npm audit --audit-level=high

.PHONY: trivy
# Filesystem scan: dependency vulns (reads package-lock.json) + secret detection.
trivy:
	trivy fs \
	--db-repository ghcr.io/aquasecurity/trivy-db \
	$(if $(wildcard .trivyignore),--ignorefile .trivyignore,) \
	--scanners vuln,secret \
	--skip-dirs node_modules \
	--quiet \
	--no-progress \
	--disable-telemetry \
	--exit-code 1 .
```

Keep the `trivy` invocation identical across languages, so behaviour and ignore-file handling are the same whichever repo a developer is in.

### RULE node/make/security-gates-in-check (SHOULD)

**Owner**: node-quality-assistant
**Applies when**: the `check` target omits dependency-vulnerability scanning or secret detection.
**Enforcement**: judgment — the agent reads the `check` target's prerequisites.
**Trigger**: Makefile, Makefile.*
**Why**: a gate that must be remembered is a gate that is skipped. Wiring the scanners into `check` — which `precommit` depends on — means a vulnerable dependency or a committed secret is caught before the commit exists, rather than by a periodic scan days later when it is already pushed.

## TypeScript

Node executes `.ts` files directly by stripping type annotations, so no build step is needed — but **stripping does not type-check**. A TypeScript project without an explicit checking step has the annotation cost and none of the safety.

```makefile
.PHONY: typecheck
typecheck:
	npx tsc --noEmit

.PHONY: check
check: lint formatcheck typecheck audit trivy
```

### RULE node/make/typecheck-for-typescript (MUST)

**Owner**: node-quality-assistant
**Applies when**: the repository contains a `tsconfig.json` but no Makefile target running `tsc --noEmit` (or equivalent) reachable from `check`.
**Enforcement**: judgment — the agent checks for `tsconfig.json`, then for a type-checking target in the `check` dependency chain.
**Trigger**: tsconfig.json, Makefile, Makefile.*
**Why**: Node deletes type annotations without validating them, so a file whose types are wrong runs normally — a `const n: number = "text"` executes and prints a string. Without `tsc --noEmit` in the pipeline the type system provides no guarantee whatsoever, and the project pays TypeScript's cost while getting JavaScript's safety.

## Frontend Variant

Frontend applications have a genuinely different shape: a bundler produces the artefact, so `build` is a required step rather than an optional one, and the security gates typically live in CI rather than the Makefile.

```makefile
precommit: lint build test

lint:
	npm install
	npm run lint:analyse

build:
	npm install
	npm run build

test:
	npm install
	npm run test -- --run
```

This is a deliberate variant, not a deviation to be corrected. The service rules in this guide do not apply to it; only the shared expectation that `make precommit` is the single entry point carries over.

## Related

- `node-service-guide.md` — the service contract these targets verify
- `go-makefile-commands.md` — the equivalent target set in Go
- `python-makefile-commands.md` — the equivalent target set in Python
