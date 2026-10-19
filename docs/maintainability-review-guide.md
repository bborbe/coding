# Maintainability Review Guide

Rules for reviewing the maintainability of changed files whose type has no dedicated rule family: Terraform, shell, and the other source types listed on each rule's trigger. This guide is the source of truth for the `maintainability/*` rule family; `agents/maintainability-assistant.md` reads it and adjudicates the five judgment-tier rules in the family.

## What the lens judges

The lens judges maintainability defects in changed files whose type has no dedicated rule family:

- A **comment that restates the code** — it describes what the next line does rather than why it does it.
- A **definition nothing references** — dead code the change leaves behind or adds.
- A **change that suppresses a symptom** — it makes a failure stop surfacing without removing its cause.
- An **indirection with no second user** — an abstraction built for a use case the change does not contain.
- A **name that no longer describes the behaviour** — the definition drifted, or outgrew the scope its name states.

The lens **excludes correctness**. A bug is not a maintainability finding, and correctness stays with tests, the mechanical funnel and the language rule families. A maintainability finding is always about the shape of the code, never about whether it produces the right result.

## Language-agnostic by construction

The rules name no language. The trigger list is the only place a file type appears. Adding or removing a file type later is a one-line trigger edit plus `make build-index` — never a command change, never a new rule id. The five tests are stated in terms every language shares: a comment, a definition, a reference, an indirection, a name.

## Why the trigger list is the dedup boundary

A file type owned by an existing rule family is deliberately absent from every trigger. On a diff that touches only owned files, no maintainability rule enters the candidate set. On a mixed diff — `infra/main.tf` plus `pkg/order.go` — the rules are candidates, and each rule's `Applies when` confines the finding to the non-owned file, so the owned file is adjudicated only by its own family.

This is the only dedup mechanism. There is no adjudicator-side suppression and no candidate-set filter: the trigger globs decide which rules run, and the `Applies when` line decides which files a running rule may report on. A glob that names an owned extension is the only way the boundary can break.

## Whole changed files, not diff hunks

The adjudicator is handed the diff. A finding on a line the diff never touched is dropped, not reported — a pre-existing smell in a changed file does not become this change's responsibility. The review's changed-code rule applies here exactly as it does elsewhere in the funnel.

## Vocabulary

The lens reuses the shared [code smell vocabulary](code-smell-vocabulary.md). `dead code` and `speculative generality` carry their established meanings from that document, and the other three findings are stated in plain terms rather than as new house terms. This guide defines no second vocabulary.

## Why dead code is judgment-tier here

The reachability detectors this plugin carries (`vulture` and `ts-prune`) run only on Python and Node. On a non-owned file, no mechanical detector owns the reachability question, so the judgment has to be made by the adjudicator: search the repository for a reference, and flag a definition only when nothing depends on it. That is why `maintainability/dead-code` is judgment-tier while the same smell is mechanical on the languages that have their own families.

## Rules

### RULE maintainability/comment-restates-code (SHOULD)

**Owner**: maintainability-assistant
**Applies when**: a changed file whose type has no dedicated rule family carries a comment that restates the adjacent statement in prose — it describes what the next line does rather than why it does it, so it adds no information and drifts as soon as the code changes.
**Enforcement**: judgment — the adjudicator reads each changed non-owned file and flags a comment that restates the adjacent statement instead of explaining intent, constraint or trade-off.
**Trigger**: **/*.tf, **/*.tfvars, **/*.hcl, **/*.sh, **/*.bash, **/*.zsh, **/*.rb, **/*.java, **/*.kt, **/*.rs, **/*.c, **/*.h, **/*.cc, **/*.cpp, **/*.hpp, **/*.cs, **/*.php, **/*.swift, **/*.scala, **/*.lua, **/*.pl, **/*.sql
**Why**: A comment that restates the code is a second copy of the code written in a weaker notation. It cannot be more precise than the line below it, and every edit to that line makes the comment wrong, so it becomes a maintenance task that documents nothing.

#### Bad

```hcl
resource "order_worker" "batch" {
  # set the instance type to t3.micro
  instance_type = "t3.micro"
}
```

#### Good

```hcl
resource "order_worker" "batch" {
  # t3.micro is the smallest instance that holds a 200-order batch in memory.
  instance_type = "t3.micro"
}
```

### RULE maintainability/dead-code (SHOULD)

**Owner**: maintainability-assistant
**Applies when**: a changed definition, branch or file whose type has no dedicated rule family has no reference anywhere in the repository, and the change does not state why it is retained.
**Enforcement**: judgment — the adjudicator reads each changed non-owned file, searches the repository for a reference to each changed definition, and flags one that nothing depends on.
**Trigger**: **/*.tf, **/*.tfvars, **/*.hcl, **/*.sh, **/*.bash, **/*.zsh, **/*.rb, **/*.java, **/*.kt, **/*.rs, **/*.c, **/*.h, **/*.cc, **/*.cpp, **/*.hpp, **/*.cs, **/*.php, **/*.swift, **/*.scala, **/*.lua, **/*.pl, **/*.sql
**Why**: Nothing depends on dead code, so deleting it changes no observable behaviour — but it still costs every reader a decision about whether it matters and every future change a check against it. The mechanical reachability detectors run only on the languages that have their own families, so on a non-owned file this judgment has no mechanical owner.

#### Bad

```hcl
locals {
  legacy_order_batch_size = 50
}
```

#### Good

```hcl
locals {
  order_batch_size = 50
}

resource "order_worker" "batch" {
  user_data = "BATCH_SIZE=${local.order_batch_size}"
}
```

### RULE maintainability/bandaid-fix (SHOULD)

**Owner**: maintainability-assistant
**Applies when**: a changed line in a file whose type has no dedicated rule family suppresses a symptom rather than the cause — a special-case branch, a retry or sleep, a widened type, an ignore directive, or a `|| true`-equivalent — with no stated reason.
**Enforcement**: judgment — the adjudicator reads each changed non-owned file and flags a change that makes a failure disappear instead of removing its cause.
**Trigger**: **/*.tf, **/*.tfvars, **/*.hcl, **/*.sh, **/*.bash, **/*.zsh, **/*.rb, **/*.java, **/*.kt, **/*.rs, **/*.c, **/*.h, **/*.cc, **/*.cpp, **/*.hpp, **/*.cs, **/*.php, **/*.swift, **/*.scala, **/*.lua, **/*.pl, **/*.sql
**Why**: A suppressed symptom keeps failing silently. The next reader sees a green result and cannot tell whether the cause was fixed or hidden, so the same failure returns somewhere the suppression does not reach.

#### Bad

```bash
deploy_order_service.sh --apply || true
```

#### Good

```bash
if ! deploy_order_service.sh --apply; then
  echo "order service deploy failed; the previous version stays live" >&2
  exit 1
fi
```

### RULE maintainability/speculative-abstraction (SHOULD)

**Owner**: maintainability-assistant
**Applies when**: a changed file whose type has no dedicated rule family adds an indirection with no second user — an interface with one implementation, a parameter every caller passes the same value for, a config field nothing reads, or an abstraction for a use case absent from the change.
**Enforcement**: judgment — the adjudicator reads each changed non-owned file and flags an indirection whose only justification is a use case the change does not contain.
**Trigger**: **/*.tf, **/*.tfvars, **/*.hcl, **/*.sh, **/*.bash, **/*.zsh, **/*.rb, **/*.java, **/*.kt, **/*.rs, **/*.c, **/*.h, **/*.cc, **/*.cpp, **/*.hpp, **/*.cs, **/*.php, **/*.swift, **/*.scala, **/*.lua, **/*.pl, **/*.sql
**Why**: An abstraction with one user is a second place to change and a second place to get wrong. It pays its cost only when a second user arrives, and until then it guesses at a shape the codebase has not needed.

#### Bad

```bash
run_order_deploy() {
  deploy_order_service.sh --apply
}

run_order_deploy
```

#### Good

```bash
deploy_order_service.sh --apply
```

### RULE maintainability/naming-size-drift (SHOULD)

**Owner**: maintainability-assistant
**Applies when**: a changed definition, in a file whose type has no dedicated rule family, whose behavior no longer matches its name — or a unit in such a file that has grown past the scope its name states — a getter that writes, a validator that mutates, a parse that fetches.
**Enforcement**: judgment — the adjudicator reads each changed non-owned file and compares what a definition does with what its name promises.
**Trigger**: **/*.tf, **/*.tfvars, **/*.hcl, **/*.sh, **/*.bash, **/*.zsh, **/*.rb, **/*.java, **/*.kt, **/*.rs, **/*.c, **/*.h, **/*.cc, **/*.cpp, **/*.hpp, **/*.cs, **/*.php, **/*.swift, **/*.scala, **/*.lua, **/*.pl, **/*.sql
**Why**: A name is the first documentation a reader gets. When behaviour and name disagree, every call site is read under a false assumption, and the fix always costs more than renaming the definition when the drift was introduced.

#### Bad

```bash
validate_order() {
  sed -i 's/pending/confirmed/' "$1"
}
```

#### Good

```bash
confirm_order() {
  sed -i 's/pending/confirmed/' "$1"
}
```

## Antipatterns

- **Reporting a bug as a maintainability finding.** The lens excludes correctness. A wrong result belongs to tests, the mechanical funnel or the language family that owns the file — not here.
- **Reporting a pre-existing smell on an untouched line.** The adjudicator is handed the diff; a smell the change did not introduce is dropped, not reported.
- **Re-adjudicating a file that has its own rule family.** The trigger globs decide which rules run, and `Applies when` confines each finding to a non-owned file. An owned file is never this lens's to judge.
- **Flagging a comment for being terse.** A short comment that explains intent is exactly what the lens wants. Only a comment that could be deleted without losing information is a finding.
- **Calling every wrapper speculative.** An indirection with a stated second user — a caller outside the change, a configuration surface something reads — is not speculative. The test is the second user, not the indirection's shape.
- **Naming a smell without a fix.** Every finding carries a file and line, the rule id, the smell, and the structural fix.

## Related

- [Rule Block Schema](rule-block-schema.md) — the `### RULE` contract these blocks follow
- [Code Smell Vocabulary](code-smell-vocabulary.md) — the shared terms this guide reuses
- [Agent & Command Development Guide](agent-command-development-guide.md) — the agent authoring conventions
