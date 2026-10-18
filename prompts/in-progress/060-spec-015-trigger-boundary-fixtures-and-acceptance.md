---
status: failed
spec: [015-language-agnostic-maintainability-rules]
execution_id: coding-sc5-exec-060-spec-015-trigger-boundary-fixtures-and-acceptance
dark-factory-version: v0.198.7
created: "2026-10-18T15:58:21Z"
queued: "2026-10-18T16:35:18Z"
started: "2026-10-18T16:39:40Z"
completed: "2026-10-18T16:40:41Z"
branch: dark-factory/language-agnostic-maintainability-rules
lastFailReason: 'validate completion report: completion report status: partial'
---

# Maintainability fixture pair and trigger-boundary acceptance assertion

<summary>
- Three committed fixture trees give the review a reproducible Terraform/shell case that carries three of the five smells, a Go case that carries a smell the Go family owns, and a clean non-owned case that carries none
- The acceptance suite gains a deterministic check that simulates the review's judgment-rule selector over a non-owned file list and over an owned-source file list
- The first list must select all five maintainability rules; the second must select none
- That makes `make precommit` fail if a future edit points a maintainability trigger at a file type an existing rule family owns
- The fixtures are plain source files only — no README or notes file — so a scratch-repo review of a fixture produces exactly the intended findings
- No rule, guide, agent, command or index file is touched by this prompt
</summary>

<objective>
Add the three maintainability fixture trees under `specs/fixtures/maintainability/` and add the trigger-boundary assertion to `scripts/acceptance.sh`, so the dedup invariant that keeps maintainability rules off language-owned files is regression-locked by `make precommit`. This is prompt **2 of 3** for spec 015 and depends on prompt 1 (the five rule ids and their 22 trigger globs must already be in `rules/index.json`).
</objective>

<context>
Read fully before writing:

- `specs/in-progress/015-language-agnostic-maintainability-rules.md` — Desired Behaviors 4 and 6, AC3, and the Failure Modes rows "A trigger glob is pointed at a language-owned extension" and "The five rules fire on the same smell a language rule already reports on a mixed diff".
- `scripts/acceptance.sh` — the whole file. Note the header comment's numbered list (items 1–4), the six section banners `=== 1/6 … === 6/6`, the `ok` / `fail` helpers, the `set -uo pipefail` (no `-e`), the `jq` + `ast-grep` preflight, and the `=== 6/6 Self-containment script tier ===` block that shows the established fixture-assertion shape.
- `commands/pr-review.md` — the **Step 4b-i: Active judgment rules** section (the `jq` program that selects judgment rules whose triggers match `CHANGED_FILES`). The assertion reuses that selection logic.
- `docs/selector-mode-guide.md` — the selector contract (`CANDIDATES`, the HARD INVARIANT that the applicable set is a subset of the candidate set). The trigger-boundary property this prompt locks is what makes that invariant hold for non-owned files.
- `rules/index.json` — the committed index. The five `maintainability/*` entries (owner `maintainability-assistant`, `enforcement_type: judgment`) and their 22-glob trigger arrays must be present. If they are missing, prompt 1 has not shipped — stop and report that prompt 1 must run first.
- `rules/go/no-fmt-errorf.yml` — the Go detector the `go-covered` fixture must hit. It ignores `main.go`, `**/main.go`, `**/*_test.go`, `vendor/**`, `**/vendor/**` and `**/mocks/**`; the fixture path must avoid all of them.
- `.reviewignore` — `specs/` is excluded from the `coding` repo's own reviews, which is why the fixtures are reviewed by copying them into a scratch repo rather than by reviewing this checkout.

**Verified repo facts this prompt relies on**

- `specs/fixtures/` currently contains only `golden-legacy-verdict.json`; the `maintainability/` subtree does not exist.
- `scripts/acceptance.sh` is invoked by `make check-acceptance`, which is part of `make precommit`.
- The container's `.git` is masked for this run (`hideGit=true`), so no check below uses git.

**The selector logic the assertion simulates**

Step 4b-i of `commands/pr-review.md` selects an entry when `.trigger == null`, or when any trigger glob matches any changed file, where a glob is translated by `gsub("\\."; "\\.") | gsub("\\*\\*/"; "°") | gsub("\\*\\*"; "±") | gsub("\\*"; "[^/]*") | gsub("\\?"; "[^/]") | gsub("°"; "(.*/)?") | gsub("±"; ".*")` and matched as `^…$`. `@commits` is an always-match. The assertion below expresses the same rule with the per-pattern `any` nested around a per-file `any`, so a multi-file list is evaluated file by file. See `<notes>` for why the nesting differs from the shipped block.
</context>

<requirements>

### 1. Create the three fixture trees

Create exactly these five files. Add no `README`, no notes file and no other file: a scratch-repo review of a fixture tree treats every added file as part of the diff, and an extra Markdown file would draw unrelated Markdown/README findings and break the expected finding count.

**`specs/fixtures/maintainability/terraform-shell-smells/infra/main.tf`**

```hcl
resource "aws_instance" "order_worker" {
  ami = "ami-0123456789abcdef0"
  # set the instance type to t3.micro
  instance_type = "t3.micro"
}

locals {
  legacy_order_batch_size = 50
}
```

The comment immediately above `instance_type` is the `maintainability/comment-restates-code` violation (it restates the value below it). `legacy_order_batch_size` is referenced nowhere, so it is the `maintainability/dead-code` violation.

**`specs/fixtures/maintainability/terraform-shell-smells/scripts/deploy.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

terraform init -input=false
terraform apply -auto-approve || true
```

The final line is the `maintainability/bandaid-fix` violation (a `|| true`-equivalent with no stated reason). Do not add a comment above it: a second restating comment would produce a second comment finding and break the expected three-finding count.

**`specs/fixtures/maintainability/go-covered/pkg/order/order.go`**

```go
// Copyright (c) 2026 The Order Authors All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package order

import "fmt"

// Load reads an order by id.
func Load(id string) (string, error) {
	if id == "" {
		return "", fmt.Errorf("order id is required")
	}
	// return the id
	return id, nil
}
```

`fmt.Errorf` hits `go-errors/no-fmt-errorf`; `// return the id` restates the line below it. The file's path is outside every `ignores` entry in `rules/go/no-fmt-errorf.yml`. This fixture proves the boundary: the Go family owns the file, so the restating comment must produce **no** maintainability finding.

**`specs/fixtures/maintainability/terraform-shell-clean/infra/main.tf`**

```hcl
locals {
  retention_days = 30
}

# retention_days is the only knob an operator changes, so it lives at the top.
resource "aws_instance" "order_worker" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"

  tags = {
    RetentionDays = local.retention_days
  }
}
```

**`specs/fixtures/maintainability/terraform-shell-clean/scripts/deploy.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

terraform init -input=false
if ! terraform apply -auto-approve; then
  echo "order service deploy failed; the previous version stays live" >&2
  exit 1
fi
```

The clean fixture carries none of the five smells: the comment states why the local exists and sits at the top, the local is referenced, and the failure path is handled explicitly.

### 2. Add the trigger-boundary assertion to `scripts/acceptance.sh`

**2a. Update the header comment.** Change the opening line `Runs the 4 unit/integration tests` to `Runs the 5 unit/integration tests`. After the existing numbered item `4. Broken-YAML isolation — …`, add:

```
#   5. Maintainability trigger boundary — the five maintainability rules are
#      candidates for non-owned source files and for no language-owned file
```

**2b. Renumber the section banners.** The merged file already carries seven sections (`=== 1/7` … `=== 7/7`, including `=== 5/7 Selector mode contracts` and `=== 7/7 Review coverage contract` from the sibling change). Change `=== 1/7` … `=== 7/7` to `=== 1/8` … `=== 7/8` (seven one-character edits; the banner text after the number is unchanged).

**2c. Insert a new section immediately before the `echo ""` / `echo "=== Summary ==="` lines at the end of the file:**

```bash
echo "=== 8/8 Maintainability trigger boundary ==="

# Simulates the Step 4b-i judgment-rule selector from commands/pr-review.md.
# The per-pattern `any` is nested around a per-file `any` so a multi-file list is
# evaluated file by file; see the prompt notes for why the shipped block's single
# `any` over a multi-valued condition is not reused verbatim.
maint_candidates() {
  jq -r --arg files "$1" '
    [ .[] | select(.enforcement_type == "judgment") |
      select(
        .trigger == null or
        (.trigger | any(.[]; . as $pat |
          ($files | split("\n") | any(.[]; . as $f |
            ($f == $pat) or
            (($pat | startswith("@")) and $pat == "@commits") or
            (($pat | contains("*")) and
              ($f | test("^" + ($pat | gsub("\\."; "\\.") | gsub("\\*\\*/"; "°") | gsub("\\*\\*"; "±") | gsub("\\*"; "[^/]*") | gsub("\\?"; "[^/]") | gsub("°"; "(.*/)?") | gsub("±"; ".*")) + "$"))
            )
          ))
        ))
      )
    ] | .[] | .id + " " + .owner
  ' rules/index.json
}

NON_OWNED_FILES=$(printf '%s\n' "infra/main.tf" "scripts/deploy.sh")
OWNED_FILES=$(printf '%s\n' \
  "pkg/order.go" "app/main.py" "src/index.ts" "src/index.tsx" \
  "src/index.js" "src/index.jsx" "go.sum" \
  "package.json" "go.mod" "Makefile" "Dockerfile" "README.md" \
  "CHANGELOG.md" "CLAUDE.md" "agents/x.md" "commands/x.md" \
  "skills/x.md" "tsconfig.json" "pyproject.toml" ".golangci.yml" \
  ".golangci.yaml" "k8s/deployment.yaml")

for rid in \
  maintainability/comment-restates-code \
  maintainability/dead-code \
  maintainability/bandaid-fix \
  maintainability/speculative-abstraction \
  maintainability/naming-size-drift; do
  if maint_candidates "$NON_OWNED_FILES" | grep -qxF "$rid maintainability-assistant"; then
    ok "non-owned diff selects $rid"
  else
    fail "non-owned diff did not select $rid — a trigger is missing or mis-scoped"
  fi
done

if ! owned_out=$(maint_candidates "$OWNED_FILES"); then
  fail "owned-source selector simulation failed — cannot prove the trigger boundary"
else
  owned_leak=$(printf '%s\n' "$owned_out" | grep -c '^maintainability/' || true)
  if [ "$owned_leak" -eq 0 ]; then
    ok "owned-source diff selects zero maintainability rules — trigger boundary holds"
  else
    fail "owned-source diff selected $owned_leak maintainability rule(s) — a trigger crossed the dedup boundary"
  fi
fi
```

The five ids are hardcoded literals, never derived from the assertion's own output: a derived expectation would still pass after a trigger was deleted.

<!-- RESOLVED 2026-10-18: jq 1.6's any/2 (foreach + break) drops rules on multi-file diffs — reproduced on this host against the container's jq 1.6. The shipped block returns 3 candidates for infra/main.tf + scripts/deploy.sh + README.md (spec records 8) and 0 maintainability ids for the two-file non-owned list, while the nested form returns 8 and 5/0. The nested assertion is correct and version-stable for the trigger-boundary property. The shipped-selector defect is escalated to the spec owner as a separate, pre-existing issue: spec 015's Non-goals forbid editing commands/pr-review.md or commands/local-review.md here, so the assertion locks the boundary and the command fix is a follow-up task. -->


### 3. Self-check before finishing

Run the `<verification>` block. The acceptance suite must exit 0 and print five `non-owned diff selects …` pass lines plus the `owned-source diff selects zero …` pass line.
</requirements>

<constraints>
- **Single-writer file:** `scripts/acceptance.sh` is edited only by this prompt. Do not touch `scripts/rule-checks.sh`, `scripts/validate-citations.sh`, `scripts/build-index.py`, or any other script.
- **Fixtures are source files only.** No `README.md`, no `NOTES.md`, no `.gitkeep`, no hidden file in any fixture tree — an extra file enters the scratch-repo diff and changes the expected finding count.
- **Fixture paths must avoid the Go detector's ignores** (`main.go`, `**/main.go`, `**/*_test.go`, `vendor/**`, `**/vendor/**`, `**/mocks/**`).
- **Smell count is pinned:** the smells fixture carries exactly three smells (one restating comment, one dead local, one `|| true`); the clean fixture carries none. Do not add a second restating comment or any other smell to the smells fixture.
- **No command edit.** `commands/pr-review.md`, `commands/local-review.md` and `commands/code-review.md` are out of scope; the spec forbids changing them.
- **No rule edit.** Do not edit `docs/maintainability-review-guide.md`, `agents/maintainability-assistant.md`, `rules/index.json`, or any `### RULE` block. Prompt 1 owns them.
- **Do NOT modify** `CHANGELOG.md` (prompt 3's), `scenarios/**`, `.maintainer.yaml`, `docs/security/**`, `README.md`, `llms.txt`, `CLAUDE.md`.
- **Do NOT commit and do NOT run any `git` command.** The container's `.git` is masked (`hideGit=true`); the daemon commits on completion.
- **Generic content only:** fixture content uses User / Order / Product / Customer domains — never trading or project-specific terms.
- **Dependency guard:** before editing, run `python3 scripts/build-index.py | jq -e '[.[] | select(.id|startswith("maintainability/"))] | length == 5'`. If it does not print `true`, stop and report that prompt 1 must execute first.
</constraints>

<verification>
All commands are container-executable from the repo root. This container's `.git` is masked (`hideGit=true`) — no check below invokes git directly.

```bash
# 0. Dependency guard: prompt 1's five entries exist
python3 scripts/build-index.py | jq -e '[.[] | select(.id|startswith("maintainability/"))] | length == 5'   # expect: true

# 1. The five fixture files exist and the trees hold nothing else
test -f specs/fixtures/maintainability/terraform-shell-smells/infra/main.tf
test -f specs/fixtures/maintainability/terraform-shell-smells/scripts/deploy.sh
test -f specs/fixtures/maintainability/go-covered/pkg/order/order.go
test -f specs/fixtures/maintainability/terraform-shell-clean/infra/main.tf
test -f specs/fixtures/maintainability/terraform-shell-clean/scripts/deploy.sh
find specs/fixtures/maintainability -type f | wc -l                    # expect: 5
test -z "$(find specs/fixtures/maintainability -type f ! -name '*.tf' ! -name '*.sh' ! -name '*.go')"   # expect: exit 0

# 2. The smells fixture carries exactly its three intended markers
grep -c '|| true' specs/fixtures/maintainability/terraform-shell-smells/scripts/deploy.sh        # expect: 1
grep -c 'legacy_order_batch_size' specs/fixtures/maintainability/terraform-shell-smells/infra/main.tf   # expect: 1
grep -c 'set the instance type' specs/fixtures/maintainability/terraform-shell-smells/infra/main.tf     # expect: 1
grep -c 'fmt.Errorf' specs/fixtures/maintainability/go-covered/pkg/order/order.go                # expect: 1
ast-grep scan --rule rules/go/no-fmt-errorf.yml specs/fixtures/maintainability/go-covered/pkg/order/order.go 2>&1 | grep -q '^error\[go-errors/no-fmt-errorf\]'   # expect: exit 0
grep -c 'return the id' specs/fixtures/maintainability/go-covered/pkg/order/order.go             # expect: 1
! grep -q '|| true' specs/fixtures/maintainability/terraform-shell-clean/scripts/deploy.sh   # expect: exit 0
grep -c 'RetentionDays = local.retention_days' specs/fixtures/maintainability/terraform-shell-clean/infra/main.tf   # expect: 1

# 3. The acceptance suite is renumbered and the new section runs
grep -c '=== [1-7]/8 ' scripts/acceptance.sh          # expect: 7
grep -c '=== 8/8 Maintainability trigger boundary ===' scripts/acceptance.sh   # expect: 1
grep -c 'maint_candidates' scripts/acceptance.sh      # expect: >= 3

# 4. The acceptance suite passes and the new assertions ran
bash scripts/acceptance.sh                              # expect: exit 0
bash scripts/acceptance.sh 2>&1 | grep -c 'non-owned diff selects maintainability/'   # expect: 5
bash scripts/acceptance.sh 2>&1 | grep -c 'owned-source diff selects zero maintainability rules'   # expect: 1
make check-acceptance                                   # expect: exit 0

# 5. Nothing outside this prompt's scope changed
test -z "$(find rules -path '*maintainability*')"       # expect: exit 0
grep -c 'maintainability' CHANGELOG.md                  # expect: 1 (the existing `## Unreleased` bullet — unchanged)
! grep -q 'maintainability' commands/pr-review.md       # expect: exit 0

# 6. The git-free precommit targets stay green
make check-links check-json check-index check-coverage check-rule-tests bench-test   # expect: exit 0

# 7. Full gate is NOT a pass condition here: `make precommit` cannot pass with a
#    masked `.git` (check-changelog-fold exits 1 on `not a git repository`).
#    Step 6 is the in-container gate; the daemon's validationCommand still runs
#    `make precommit` afterwards, and the note below defines the report.
```

Note on `make precommit` under this run's masked `.git`: `check-changelog-fold` shells out to git and fails with `not a git repository`, which is an environment limitation, not a defect in this change. If `make precommit` fails **only** on that message, run the git-free targets and require them all green, then report the environment gap in `## Improvements` (category: GLOBAL) and report `status: partial` with the real exit code. Do not fabricate a green `make precommit`.
</verification>

<notes>
- **Why the selector expression is not copied byte-for-byte from Step 4b-i.** The shipped block wraps the whole per-pattern match in a single `any(. as $pat | <generator that emits one boolean per changed file>)`. With jq 1.6 (the version in this container and in typical CI images), `reduce` over a multi-valued update keeps only one branch, so a rule is silently dropped whenever the trigger matches one changed file but not the last one. Measured here: the shipped block returns 3 candidates for `infra/main.tf`, `scripts/deploy.sh`, `README.md` (the spec records 8), and drops `go-*`, `git-commit/*`, `rest/*` and `self-containment/*` rules on a two-file `pkg/order.go` + `app/main.py` diff. The nested form above returns the spec's 8 pre-existing candidates plus the five maintainability ids for that example, and all five maintainability ids for the two-file non-owned list, and it is stable across jq versions because every `any` sees a single-valued condition. Fixing the shipped block is a command change, which spec 015 forbids, so it is out of scope for this prompt.
- **Why the fixtures carry no README.** The operator copies a fixture tree into a scratch repo as the feature diff. A `README.md` there would match the Markdown and README rule families and add findings the AC4/AC5/AC6 counts do not expect.
- **Why the ids are literals in the assertion.** A derived expectation (`jq '[…] | length'`) would still pass after a trigger was deleted from one rule. Hardcoded ids make the gate fail on the regression it exists to catch, matching the self-containment block's stated rationale (`=== 6/8` after this prompt's renumbering).
- **The boundary property is per-file.** Glob matching is evaluated per changed file, so testing a two-file non-owned list and a twenty-two-file owned list exercises every owned extension the spec enumerates without depending on file order.
- **Prompt 3 owns the changelog and the cross-cutting gates.** Do not add a `## Unreleased` bullet here.
</notes>
