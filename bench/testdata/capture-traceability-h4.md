## PR Review: bench-pr-2 → bench-base-2 (full mode)

**Scope**: CommonJS JS → CommonJS TypeScript conversion of the node-skeleton reference service (18 files, 783/-111).

### Automated Checks
- `make precommit`: **PASS** (install, format, test 7/7, lint, typecheck, audit, trivy all clean)
- ast-grep mechanical funnel (74 YAML rules, diff-scoped): **0 findings**
- LICENSE file: present
- Judgment-rule candidates triggered by diff: all reviewed manually below (node-quality-assistant owns 22 of them)

### Manual Review

Read every changed `.ts` source in full (not diff fragments) plus `tsconfig.json`, `eslint.config.js`, `Makefile.precommit`. Cross-checked against `node-service-guide.md`'s TypeScript section and the repo's own `CLAUDE.md` invariants — the PR matches both exactly:
- No `any`, `as`, `!`, or `@ts-ignore` anywhere in source (verified by grep)
- `tsc --noEmit` wired into `make check` as `typecheck`
- `erasableSyntaxOnly` + no build step preserved; `require('./x.ts')` explicit-extension pattern used consistently
- All prior non-obvious invariants (readiness-before-close, 503 not 500, unref'd timer, stderr/stdout split, unmatched-label bucketing, error-handler arity) preserved verbatim in the ported code
- New `config.check()` validator is explicitly exempted by `node/config/data-not-behaviour` (a `check()` validator on config data is allowed) — not a violation despite adding a method to the config object
- CHANGELOG entry uses conventional `feat:` prefix correctly

#### Must Fix (Critical)
None.

#### Should Fix (Important)
- **No test coverage for `src/config.ts`'s new validation logic.** `config.check()` is new: it collects multiple problems instead of throwing on the first (previously only `PORT` was validated via immediate `throw`), and it adds a brand-new `SHUTDOWN_TIMEOUT_MS` check that didn't exist before. Zero tests exercise either the multi-problem collection or the new field validation — `test/` only covers `health.ts` via `server.ts`. Worth a small `test/config.test.ts` covering: valid config → `[]`, invalid `PORT` → problem, invalid `SHUTDOWN_TIMEOUT_MS` → problem, both invalid → both problems.

#### Nice to Have (Optional)
None.

### Traceability
| Rule ID | Owner | Verdict |
|---|---|---|
| node/config/data-not-behaviour | node-quality-assistant | compliant (check() exempted) |
| node/config/validate-before-serving | node-quality-assistant | compliant, improved (explicit check() before listen) |
| node/architecture/inject-dependencies | node-quality-assistant | compliant, unchanged |
| node/health/liveness-has-no-dependencies | node-quality-assistant | compliant, unchanged |
| node/health/readiness-returns-503 | node-quality-assistant | compliant, unchanged |
| node/http/error-handler-arity | node-quality-assistant | compliant, unchanged |
| node/k8s/scrape-annotation-matches-metrics | node-quality-assistant | not touched (k8s/ unchanged) |
| node/lifecycle/handles-sigterm | node-quality-assistant | compliant, unchanged |
| node/lifecycle/readiness-fails-before-close | node-quality-assistant | compliant, unchanged |
| node/lifecycle/shutdown-timer-unref | node-quality-assistant | compliant, unchanged |
| node/logging/errors-to-stderr | node-quality-assistant | compliant, unchanged |
| node/make/install-from-lockfile | node-quality-assistant | compliant, unchanged |
| node/make/required-targets | node-quality-assistant | compliant |
| node/make/security-gates-in-check | node-quality-assistant | compliant |
| node/make/typecheck-for-typescript | node-quality-assistant | compliant (this rule's target, added by the PR) |
| node/metrics/bounded-label-cardinality | node-quality-assistant | compliant, unchanged |
| node/metrics/own-registry | node-quality-assistant | compliant, unchanged |
| node/metrics/service-exposes-metrics | node-quality-assistant | compliant, unchanged |
| node/test/ephemeral-port | node-quality-assistant | compliant, unchanged |
| claude-md/agent-context-not-user-docs | agent-auditor | compliant |
| readme/user-facing-not-agent-context | agent-auditor | compliant |
| changelog/conventional-prefix-required | agent-auditor | compliant |

### Next Steps
Add `test/config.test.ts` for the new `check()` validation paths, otherwise ready to merge.
