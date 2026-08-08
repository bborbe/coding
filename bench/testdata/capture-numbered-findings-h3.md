## PR Review: `bench-pr-3` vs `bench-base-3` (python-skeleton, full mode)

**Step 0**: Already at PR head (worktree short-circuit) — no worktree created/removed.
**Step 3a**: LICENSE present.
**Step 3b**: `make precommit` — **PASS** (ruff format/check, pytest 30 passed, mypy 12 files, trivy scan clean).
**Step 4**: Mechanical funnel (`ast-grep-runner`) — 0 findings across 74 YAML checks. Judgment-tier candidates dispatched to 5 owners (agent-auditor, go-quality-assistant, node-quality-assistant, python-architecture-assistant, python-quality-assistant). Go/Node rules and Python-architecture rules were confirmed false-positive triggers (glob matches on `Dockerfile`/`Makefile.*`/test file, not actual Go/Node/composition-root code) — no violations.

### Must Fix (Critical)
None.

### Should Fix (Important)
1. **`CHANGELOG.md:18`** — `- ci: install trivy in CI` uses prefix `ci:`, not in the recognized set (`feat/fix/refactor/test/docs/chore/perf`). Breaks automated version-bump detection. Fix: use `chore:`. *(rule: `changelog/conventional-prefix-required`)*
2. **`README.md` "Security gates" section (~lines 76-94)** — rationale/ADR-style content (why no severity threshold, why `osv-scanner` excluded, cross-skeleton comparison table) belongs in `CLAUDE.md`/ADR, not user-facing README. Fix: trim to a short factual statement; move rationale elsewhere. *(rule: `readme/user-facing-not-agent-context`)*
3. **`.github/workflows/ci.yml:32`** — `sudo apt-key add -` is deprecated; can silently break on a future `ubuntu-latest` bump. Fix: use a keyring-based install or switch to `aquasecurity/setup-trivy` action.
4. **CI + `Makefile.precommit`** — Trivy has no version pin (unlike `PIP_AUDIT_VERSION ?= 2.9.0` set for pip-audit in the same PR), so CI and local runs can diverge over time. Fix: pin a Trivy version.
5. **`Makefile.precommit` `trivy` target** — no `--severity` filter and no documented rationale for failing on any severity, unlike the `audit` target which explicitly explains its "any severity" choice. Fix: either add a severity threshold or document the deliberate all-severity choice.

### Nice to Have (Optional)
- Manual Trivy apt-install (update/install/repo-key) duplicates the maintained `aquasecurity/setup-trivy` action — adds ~30-60s/run and maintenance surface with no caching/pinning.
- Commit subject `switch build backend to hatchling and add conventional changelog prefixes` is 73 chars (soft cap 50) — FYI only, not in the active rule set.

### Positive notes
- `hatchling` build-backend switch is clean and correctly scoped; Dockerfile `README.md` copy fix is correct and well-commented.
- `pip-audit`/`trivy` wiring into `check`, `uv export` + `uvx pip-audit@pinned`, `mktemp`+`trap` cleanup — solid.
- ruff `S` (bandit) ruleset addition with reasoned `S104`/`S101` suppressions — good pattern.
- `tests/test_factory.py` swap to `TestClient` HTTP calls instead of `app.routes` introspection is a more resilient test, with a clear "why" comment.

No functional or architectural code changed (`src/skeleton/` untouched) — this PR is build-backend + CI security-gate plumbing only.
