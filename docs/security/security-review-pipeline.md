# Security Review Pipeline

Companion to [security-review-guide.md](security-review-guide.md) (the mechanical rule base) and [selector-mode-guide.md](../selector-mode-guide.md) (the classify/adjudicate procedure this pipeline feeds). This guide is a **procedure contract**, not an enforceable rule guide: it contains zero `### RULE` headings — including never as a fenced-code illustration, because `scripts/build-index.py` walks every line of `docs/security/*.md` and does not skip fenced regions, so a `### RULE` line anywhere (even inside an example) would either add an index entry or make the walker exit 1. It adds no index entries, and no agent is bound to it.

The pipeline defines how a review session derives, keeps fresh, and bounds a per-review **evidence-pointered security model**: a machine-readable snapshot of the code's attack surface — entry points, identities, auth mechanisms, resources with their authorization functions, trust boundaries, and cross-cutting invariants — each backed by a `file:line` evidence pointer into the reviewed repo. The model is the single frozen derivation contract that the security classifier extension, the verifier, and the operator's end-to-end walk all reference as the source of truth.

## Recon pass

The recon is an in-session LLM procedure that derives the model from the diff and the codebase. It is documented here — it is **not** a binary or detector, and it adds **no new search infrastructure**: it reuses the existing `trigger` glob machinery, the `@commits` special-case, and the ast-grep funnel. There are no `symbols:`/`imports:` trigger types, no new scripts, no new parse tools.

1. **Enumerate entry points** — routes/handlers from the diff's **touched packages**, plus the index of existing handlers when available. Recall contract, stated verbatim in effect: a missed entry point is a **permanent blind spot** for the review, and over-listing is cheap.
2. **Resolve identities** — anonymous, authenticated, member, admin, service-account — and **auth mechanisms** — session-cookie, api-token — from the codebase, by reading the middleware and role definitions the entry points reference.
3. **Resolve resources and their `authorization_functions`** — via symbol resolution against the codebase, reusing the existing `trigger` glob machinery, the `@commits` special-case, and the ast-grep funnel. If ast-grep/jq are unavailable when the mechanical funnel is reused, the existing Step 4.0/4a fail-fast reports `mechanical funnel unavailable` and the recon continues with judgment-tier resolution only, noting the gap.
4. **Derive invariants** — as `resource → identifier → authorization_function`, with the function's `file:line` as evidence. An invariant's evidence must resolve to a real symbol in the diff/package; a non-resolving invariant is excluded from the applicable set.

**Authz-function resolution recall contract**: the accuracy ceiling of authz-function resolution is measured and bounded, not solved, in v1. The pipeline records the ceiling and treats residual misses as a known, bounded limitation rather than a defect to fix inline.

**Recovery for under-listing**: an entry point missed at enumeration is re-derived by re-running the recon with a wider package scope — diff-touched packages plus the existing-handler index — and merged into the model before adjudication.

**Security note**: the model is LLM-derived text consumed only by the LLM adjudicator. It is never executed, never parsed as code, never fed into a shell or build step. `file:line` evidence strings are display-only references, and the recon writes no files to those paths.

## Model schema and lifecycle

The model file is `security-model.json`. Its schema is documented here and only here — no separate `.schema.json` file ships; this guide's documented schema is the source of truth.

```json
{
  "version": 1,
  "derived_from": {
    "repo": "<repository>",
    "head": "<commit-ish>",
    "review_id": "<review-session-id>"
  },
  "entry_points": [
    {
      "type": "http",
      "method": "GET",
      "path": "/users/{id}",
      "handler": "GetUserHandler",
      "auth": "session-cookie",
      "evidence": "pkg/handler/user.go:42"
    }
  ],
  "identities": [
    { "name": "anonymous", "evidence": "pkg/auth/middleware.go:11" },
    { "name": "authenticated", "evidence": "pkg/auth/middleware.go:12" },
    { "name": "member", "evidence": "pkg/auth/roles.go:8" },
    { "name": "admin", "evidence": "pkg/auth/roles.go:9" },
    { "name": "service-account", "evidence": "pkg/auth/roles.go:10" }
  ],
  "auth_mechanisms": [
    { "name": "session-cookie", "evidence": "pkg/auth/session.go:6" },
    { "name": "api-token", "evidence": "pkg/auth/token.go:5" }
  ],
  "resources": [
    {
      "name": "user",
      "identifiers": ["user_id"],
      "authorization_functions": ["RequireUserAccess"],
      "evidence": "pkg/authz/user.go:17"
    }
  ],
  "trust_boundaries": [
    { "name": "public-internet", "evidence": "pkg/handler/user.go:42" }
  ],
  "external_interactions": [
    { "name": "payment-gateway", "evidence": "pkg/payment/client.go:9" }
  ],
  "invariants": [
    {
      "id": "INV-1",
      "statement": "a member may only read orders they own",
      "evidence": "pkg/authz/order.go:33",
      "attack_surfaces": ["admin-only"]
    }
  ]
}
```

Every entry in the model carries a `file:line` evidence pointer that locates its origin in the reviewed repo.

**Lifecycle**: the model is derived in-session at review start and exists only for the current review session. It is written to a session-local path **outside** the reviewed repo's tree — mirroring the existing `/tmp/pr-review-findings.json` pattern — and it is **never committed** to any repo.

**Failure handling**:
- If the model file is accidentally written inside the reviewed repo tree, delete it and re-write it to the session-local path.
- Two concurrent sessions each derive their own session-local model — there is no shared state to race on.
- A recon that aborts mid-derivation discards the partial model and re-runs from scratch on the next invocation; the model is read only at review start, never as a half-built file.

## Freshness gate and size control

At review start, each candidate entry's evidence source is compared against the diff:

- An entry whose source changed in the diff is **re-derived**.
- An unchanged entry is carried forward (`carry forward`).
- Stale-model events surface in the report with the literal `model refresh:` line naming the affected entry — including an entry whose evidence symbol no longer resolves: it is dropped, and the line surfaces it.

**Size control**: classifier and adjudicator input is truncated to **diff-relevant** entries — the entry points and invariants whose attack surface the diff touches — plus the cheap inventory counts. The whole model is never passed as context on large repos.

On a diff too large to enumerate (a mega-PR), derivation is limited to the touched entry points and invariants, and the report notes the truncation.

## Attack-surface inventory and drift bridge

Each review carries a countable per-review **attack-surface inventory**: HTTP endpoints, authenticated, admin-only, file uploads, external URL inputs, webhooks, HTML rendering, database queries. The inventory is a drift signal that makes the model checkable.

The diff→traits **drift** bridge is deterministic: a category-count change selects the matching security trait group.

| Category count change | Security trait group |
|-----------------------|----------------------|
| New HTTP endpoint | `authz` + `input-origin` |
| New file upload | `input-origin` + `data-to-sink` |
| New external-URL input | `external-io` + `input-origin` |
| New webhook | `external-io` + `authz` |
| New render path | `input-origin` |
| New DB query | `data-to-sink` |

Because the selection is a pure function of the inventory counts, the diff→traits selection is deterministic — the same diff always selects the same trait group.

## Report contract

The Security Model section of the review report records, for each review:

- `derived_from` — repo, head, review_id
- Entry-point count
- Inventory counts (each category from the attack-surface inventory)
- Any `model refresh:` lines, verbatim

The contract is documented now and wired in when the security-review signal is set.

## Anti-patterns to refuse

- **A hand-maintained model** — the model is always derived per review, never maintained across reviews.
- **Committing the model to any repo** — the model is session-local and never committed.
- **Passing whole-model context on large repos** — input is truncated to diff-relevant entries plus inventory counts.
- **Letting the LLM decide invariant selection** — selection is deterministic via the drift bridge, not a judgment call.
- **Adding new search infrastructure** — `symbols:`/`imports:` trigger types, new scripts, new parse tools — instead of reusing the existing funnel; the recon is an in-session procedure, not a new binary or detector.
- **A `### RULE` heading anywhere in this guide** — even as a fenced example, it breaks the index; this guide is a procedure contract with zero rule blocks.
- **Trading-specific examples** — this repo serves anyone learning Go; examples stay generic (User, Order, Product, Customer).
