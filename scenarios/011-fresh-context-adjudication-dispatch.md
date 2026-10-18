---
status: active
---

# Scenario 011: A cold-context adjudicator flags what the authoring session excused

Validates that `/coding:local-review` over a diff seeding a judgment-tier rule violation is excused by the session that authored the change and flagged by the fresh-context `coding:selector-adjudicator` dispatch, at a cost of exactly one dispatch.

## Test PR

The fixture is built inline in Setup (no perpetual fixture PR): a scratch repository under `$WORK` holding a minimal generic Go order service — a `User` / `Order` / `Product` / `Customer` domain — created with `mktemp -d` and `git init`. The branch is local-only, so the walk uses `/coding:local-review` in place rather than the branch-vs-target flow.

The seeded violation is `go-composition/no-same-package-private-helper-for-business-logic`: one change introduces new order-total business logic as a same-package private helper function called from a method, instead of behind a small interface + constructor + struct + method seam. That rule is the right seed because its enforcement is judgment-tier — the mechanical funnel emits nothing for it, so the verdict rests entirely on the adjudicator reading the rule's `applies_when` text against the diff. A mechanically-detected violation would be reported by the funnel regardless of any rationale, which would break the comparison this scenario exists to make.

## Setup

- [ ] Clone the coding plugin at the pre-change release into one isolated config directory, and at the post-change release into a second one (the pinning technique scenarios 005 and 006 use)
- [ ] Scaffold the fixture and commit a baseline on `master`: `WORK=$(mktemp -d) && cd "$WORK" && go mod init example.com/order-app && mkdir -p pkg/order && git init -q && git config user.email fixture@example.com && git config user.name fixture`, then add an `Order` type, a `Product` type and a handler that lists orders, and commit
- [ ] Create the feature branch and add the seeded violation: an `orderTotal(...)` private helper in `pkg/order` holding the new total-calculation business logic, called from an `OrderService` method — `git checkout -b order-total && git add -A && git commit -qm 'add order total'`
- [ ] Record the seeded violation's `path:LINE` from the diff (`git diff HEAD~1 --unified=0 | grep -n '^+.*orderTotal'` gives the added line), then state the authoring rationale in the conversation before running the review, verbatim: "The total calculation is used by this one handler only, so a private helper in the same package is the simplest place for it — a seam would be ceremony." That sentence is the contamination under test, recorded here so the walk is reproducible

## Action

- [ ] In a fresh Claude Code session pinned to the pre-change release, state the rationale above and run `/coding:local-review`; tee stdout to `/tmp/scen011-pre-stdout.log` and the stream-json transcript to `/tmp/scen011-pre.jsonl`
- [ ] In a fresh Claude Code session pinned to the post-change release, build the identical fixture, state the identical rationale, and run `/coding:local-review`; tee stdout to `/tmp/scen011-post-stdout.log` and the stream-json transcript to `/tmp/scen011-post.jsonl`
- [ ] In a third fresh session pinned to the post-change release, run `/coding:local-review` over a diff that short-circuits clean (a README-only whitespace edit, per scenario 005); tee the stream-json transcript to `/tmp/scen011-clean.jsonl`

## Expected

- [ ] Pre-change run: zero findings cite the seeded rule — `grep -c 'go-composition/no-same-package-private-helper-for-business-logic' /tmp/scen011-pre-stdout.log` prints `0`
- [ ] Pre-change run: no finding's first bold run is the seeded violation's `path:LINE` — `grep -cF '<seeded path:LINE>' /tmp/scen011-pre-stdout.log` prints `0`
- [ ] Post-change run: exactly one finding cites the seeded rule — `grep -c 'go-composition/no-same-package-private-helper-for-business-logic' /tmp/scen011-post-stdout.log` prints `1`
- [ ] Post-change run: that finding's first bold run is the seeded violation's `path:LINE`
- [ ] **The verdict pair, and the assertion no scripted check can make:** excused in the session that wrote the code, flagged by the cold one — the two reports disagree on the same diff, with the same rationale present in the conversation
- [ ] Cost observation: the post-change transcript contains exactly one `tool_use` block whose `subagent_type` is `coding:selector-adjudicator` (`grep -c '"subagent_type": *"coding:selector-adjudicator"' /tmp/scen011-post.jsonl` prints `1`), and the clean short-circuit transcript contains none (`grep -c '"subagent_type": *"coding:selector-adjudicator"' /tmp/scen011-clean.jsonl` prints `0`)
- [ ] Both post-change runs exit `0` and each run completes in under 10 minutes (wall clock `real` < 10m)

## Cleanup

- `rm -rf "$WORK" /tmp/scen011-*`

---

**Status**: active — carried per the acceptance criterion for this change. The walk itself is executed on the operator rung after the plugin release, and the recipe above is what the operator runs.
