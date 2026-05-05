# Test Pyramid Triggers

Concrete, action-oriented criteria for choosing the right test type when generating or implementing code. Language-neutral. Use this as the operational rule; for Go-specific patterns see [go-test-types-guide.md](go-test-types-guide.md), for theory see the team's [Test Pyramid](obsidian://open?vault=Personal&file=50%20Knowledge%20Base/Test%20Pyramid) note.

## Default: Push tests down the pyramid

| Layer | Share of test count | Frequency |
|---|---|---|
| Unit | ~70% | nearly always |
| Integration | ~20% | selectively, one per real boundary |
| E2E | <10% (most projects zero per spec) | sparingly, critical journeys only |

When unsure between two layers, choose the lower one. Promotion is cheap; demotion is friction.

## Unit Test Triggers

**Write a unit test when the new code has any of:**

- A function with branches, loops, calculations, or state mutation
- A function with edge cases: nil/empty inputs, boundary values, error paths
- A data transformation, parser, formatter, marshaller, validator
- An algorithm or pure function (input → output, no I/O)

**Volume:** one unit test per public function, plus extra tests for edge cases. For complex logic, multiple unit tests per function.

**Skip when:**

- Trivial getter/setter
- Pure pass-through wrapper (no logic)
- No cyclomatic complexity AND no edge cases

## Integration Test Triggers

**Write an integration test when the new code does any of:**

- Talks to a real out-of-process dependency in production: database, HTTP API, filesystem, IPC, subprocess → 1 happy-path + 1 error-path test
- Establishes a contract between two components (A produces what B consumes) → 1 round-trip test
- Adds to a registry or dispatch table → 1 test that exercises the production lookup, not a direct call
- Adds new cross-module wiring → 1 test of the wiring, NOT every permutation

**Volume:** typically 1-2 integration tests per real boundary. Resist permutations — push them down to unit tests.

**Skip when:**

- The behavior is pure business logic (push to unit)
- Testing error wording or log messages (unit)
- Testing 50 input combinations (unit)
- The "boundary" is actually a fake/mock — that's still a unit test

## E2E Test Triggers

**Write an E2E test only when ALL of these hold:**

1. Unit and integration tests genuinely cannot reach the behavior (real Docker, real `gh`, real cluster — not just "touches a seam")
2. The behavior is load-bearing for an essential user journey (login, checkout, "operator queues prompt → daemon executes → PR opens")
3. No existing E2E test covers the same code path
4. The regression risk is concrete and named ("if this breaks at runtime, an operator hits X")

**Volume:** rare. A typical app has 3-10 critical journeys total. Most code changes need zero new E2E tests.

**Skip when:**

- A unit or integration test could prove the same thing
- Testing edge cases (push down)
- Testing visual rendering (use visual regression tools)
- You'd need `sleep(N)` to make it pass

## Decision Tree

For each new function, module, or behavior change:

```
1. Does the code have logic, a branch, a calculation, or an edge case?
   YES → unit test (almost always at least one)

2. Does the code cross a real out-of-process boundary in production?
   YES → 1 integration test (happy path) + 1 error-path test
   (skip if covered by an existing integration test that this change does not affect)

3. Is this on a critical user journey, AND would steps 1-2 fail to prove it works end-to-end?
   YES → 1 E2E test
   NO  → stop

4. Otherwise → no new test at this level.
```

If unsure between layers, choose the lower one.

## Anti-Triggers — Do NOT Write a Test

Skip test generation entirely when the change is:

- Pure refactor with no behavior change (rely on existing tests)
- Doc / comment only
- Config / version bump with no runtime consumer
- A rename without semantic change
- Already covered by an existing test that the change does not affect

## When the Pyramid is Inverted

If a project's test counts are flipped (more E2E than unit), the pyramid is broken. Symptoms:

- Slow CI (hours per run)
- Flaky failures requiring `sleep()` workarounds
- Every red build needs root-cause archaeology because E2E tests don't localize bugs
- Developers stop running tests locally

Fix: push behavior down. For each E2E test, ask "could a unit or integration test prove this?" — almost always yes, except for the load-bearing critical journeys.

## Anti-Patterns

- **Mockist unit test** — mocks are heavier than the code under test; pins implementation, not behavior
- **Permutation explosion** — 50 integration tests for 50 input combos; belongs in unit tests
- **E2E for edge cases** — testing "256-character name field error" via the full UI; push down
- **`sleep(5000)`** — fixed sleeps to make E2E pass; hides flakiness, doesn't fix it
- **Inverted pyramid** — many E2E, few unit
- **Hourglass** — many unit + many E2E, no integration; production breakage hides in the missing middle

## See Also

- [go-test-types-guide.md](go-test-types-guide.md) — Go-specific operational rules (Ginkgo, Counterfeiter, in-memory libs)
- [tdd-guide.md](tdd-guide.md) — test-driven development workflow
- Obsidian: [[Test Pyramid]] — human-context reference with pyramid theory and references
