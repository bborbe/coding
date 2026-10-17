# Self-Containment Guide

Rules for keeping an agent-authored diff self-contained: every artifact the diff adds must resolve inside the repository, with no residue of how the change was planned. This guide is the source of truth for the `self-containment/*` rule family; `agents/self-containment-assistant.md` reads it and adjudicates the one judgment-tier rule in the family.

## What self-containment means

A diff stands on its own when every artifact it adds resolves inside the repository:

- **No machine-local path.** A path that only exists on the author's machine — a tilde-rooted path, or an absolute path under a user's home directory — resolves nowhere in the repo or in a consumer's checkout. It ships as a broken reference.
- **No planning-only identifier.** A requirement identifier resolves against a planning document that is not in the tree. A reader of the merged code has no way to look it up.
- **No planning-directory reference.** A pointer into a requirements, prompt or plan folder points at a directory that will never ship, so the reference is dead on arrival.
- **No revision or sign-off meta.** A line recording that the code was revised after a review round, changed at a reviewer's request, or attributed to a sign-off describes the authoring process, not the code. Git history already carries that provenance.
- **No steering echo.** A comment or identifier that restates the instruction that produced the change answers "what was I asked to do" instead of "what does this do". The next reader never saw the instruction.

Each of these is a defect a human reviewer would flag, and each is cheap to fix at authoring time — the fix is always to say the same thing in the repository's own terms.

## Why agent-authored diffs leak planning context

The diff is the main input to the review funnel, and an agent that produced a change from a planning document routinely carries artifacts of *how the change was planned* into *what the change does*. The planning document is real and load-bearing while the work is in flight, and it is invisible afterwards: the identifier, the path, and the rationale all resolve for the author and for nobody else. Because the leak is invisible to the author, it survives self-review and reaches the reviewer as noise — the reviewer spends attention resolving a reference that cannot resolve, or asks why a comment narrates a review round they never saw. The rule family exists so the funnel can catch it mechanically instead of paying for it in review latency.

## The scan contract: whole changed files, not diff hunks

The script tier is handed a **file list and no base ref**, so it scans each changed file whole — it cannot narrow to the diff's hunks. A self-containment check can therefore flag a pre-existing match on a line the diff never touched: a changed file drags in every violation it already carried.

That is expected, not a bug in the run. Dropping those findings is the **adjudicator's** job, not the runner's — see `commands/pr-review.md` Step 4a, which states the same whole-file contract for the funnel ("The runner's scope is changed FILES, not changed LINES"), and Step 5's rule that only changed code is reportable. Narrowing the checks to hunks is out of scope for this family.

## The six documented exemption paths

Six paths are exempt from this rule family, because they are the machinery that defines, owns, or tests it:

| Exempt path | Why it is exempt |
|---|---|
| `specs/` | the planning directory for specifications — planning context belongs here |
| `prompts/` | the planning directory for prompts — planning context belongs here |
| `docs/self-containment-guide.md` | this guide — it defines the markers, so it must be able to name them |
| `agents/self-containment-assistant.md` | the owning agent — it adjudicates the family, so it must be able to name the markers |
| `scripts/rule-checks.sh` | the mechanical runner — it implements the greps, so it must carry the patterns |
| `scripts/testdata/` | the fixtures directory — a fixture must contain the violation it asserts |

The rule runs in both directions:

- **Planning context belongs *in* the planning directories.** The rule catches planning context leaking *out* of them — it never asks you to remove planning context from the planning directories themselves.
- **No artifact outside those six may quote a marker literal.** The derived rule index is the sharp case: `scripts/build-index.py` copies this guide's `Owner`, `Applies when` and `Enforcement` lines verbatim into `rules/index.json`, so those three lines describe the markers in words — "a home-directory path", "a requirement identifier" — and never quote one. An author who genuinely needs a literal adds their artifact to this list. The list is closed and stated here; it is not a glob a consumer repo can widen.

## Rules

### RULE self-containment/no-home-dir-paths (MUST)

**Owner**: self-containment-assistant
**Applies when**: a changed file carries a path rooted at the author's home directory — a tilde-rooted path or an absolute user-home path — so the path resolves only on the author's machine and never in the repo or a consumer's checkout.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a tilde-rooted path or an absolute user-home path; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: A machine-local path resolves for exactly one person. Every other reader — a reviewer, a CI job, a consumer installing the plugin — gets a dangling reference, and a path that is *read* or *written* at runtime fails outright outside the author's machine.

#### Bad

```go
// config/defaults.go
const defaultReportPath = "~/scratch/order-report.json"
```

#### Good

```go
// config/defaults.go
const defaultReportPath = "reports/order-report.json"
```

The good path is repo-relative, so it resolves for every reader and every checkout.

### RULE self-containment/no-requirement-ids (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file carries a requirement identifier — an `FR`, `NFR` or `SC` token followed by a number — that resolves only against a planning document that will never be in the tree.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a requirement identifier of the `FR`/`NFR`/`SC` form; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: The identifier is a lookup key into a document the reader does not have. It reads as a citation but carries no information, and it silently rots the moment the planning document is renumbered or archived.

#### Bad

```go
// OrderService.Charge implements FR-14.
```

#### Good

```go
// OrderService.Charge retries a failed charge once before surfacing the error.
```

The behaviour the identifier stood for is stated in words, so the comment survives the planning document.

### RULE self-containment/no-planning-doc-refs (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file refers to a planning directory that will never ship in the tree — a requirements, prompt or plan folder — or attributes the change to planning prose rather than to the code.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a planning-directory reference or a planning-prose attribution; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: A pointer into a planning folder is a dead link in every checkout that does not carry that folder — which is every checkout a consumer ever has. Attributing a change to planning prose ("the plan says …") hands the reader a rationale they cannot check.

#### Bad

```markdown
See prompts/012-order-retry.md for the rationale.
The plan says orders should retry once.
```

#### Good

```markdown
Orders retry a failed charge once; the retry lives in OrderService.Charge.
```

The rationale is stated in the code's own terms, so it resolves where the code does.

### RULE self-containment/no-revision-meta (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file records revision or sign-off provenance — a phrase stating the code was revised after a review round, changed at a reviewer's request, or attributed to a sign-off — describing the authoring process instead of the code.
**Enforcement**: script — `scripts/rule-checks.sh` (greps every changed file whole for a revision or sign-off provenance phrase; exempts the six documented planning and rule-authoring paths per changed file)
**Why**: Provenance lives in the commit history, where it is dated, attributed, and searchable. Duplicating it in a comment creates a second, undated copy that drifts from the real history and tells the next reader nothing about the code itself.

#### Bad

```go
// revised per the review round; signed off by the platform reviewer
func (s *OrderService) Charge(ctx context.Context, order Order) error {
```

#### Good

```go
// Charge retries a failed charge once, then returns the wrapped error.
func (s *OrderService) Charge(ctx context.Context, order Order) error {
```

No provenance line at all — the comment says what the code does, and the history says who changed it and when.

### RULE self-containment/no-steering-echoes (SHOULD)

**Owner**: self-containment-assistant
**Applies when**: a changed file's comment or identifier restates the instruction that produced the change instead of describing what the code does — the text answers "what was I asked to do" rather than "what does this do".
**Enforcement**: judgment — the adjudicator reads the changed files and flags a comment or identifier that echoes the authoring instruction rather than describing the code.
**Trigger**: @commits
**Why**: The instruction is not in the repository. A comment that restates it looks like documentation but documents a conversation the reader never had, and it goes stale the moment the code moves past the request that produced it.

#### Bad

```go
// requested: add retry
func (s *OrderService) Charge(ctx context.Context, order Order) error {
```

#### Good

```go
// retry once, then surface the error
func (s *OrderService) Charge(ctx context.Context, order Order) error {
```

The good comment describes the code's behaviour, which is the only thing the next reader can act on.

## Antipatterns

- **Quoting a marker literal outside the six exempt paths** — the derived index is the sharp case; the guide's `Owner` / `Applies when` / `Enforcement` lines describe markers in words.
- **Treating a whole-file hit on an untouched line as a real finding** — the runner scans changed files, not changed lines; dropping those is the adjudicator's job.
- **Deleting planning context from the planning directories** — the rule catches leaks *out* of them, not the planning documents themselves.
- **Rewording a steering echo into a slightly longer steering echo** — if the comment still answers "what was I asked to do", it is still a violation.

## Related

- [Rule Block Schema](rule-block-schema.md) — the `### RULE` block contract this guide follows.
- [Agent & Command Development Guide](agent-command-development-guide.md) — the agent-authoring rules `agents/self-containment-assistant.md` follows.
