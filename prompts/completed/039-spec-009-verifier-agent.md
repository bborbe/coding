---
status: completed
spec: [009-security-verifier-citations]
summary: Created agents/security-verifier.md — a read-only adversarial falsification gate (7-item checklist, confirmed|plausible|rejected verdict contract, counterevidence_checked/reject_reason fields, precision-over-recall incentive) with no dispatch-list, README, llms, CLAUDE.md, or CHANGELOG registration (owned by prompt 4); make precommit exits 0.
execution_id: coding-security-verifier-exec-039-spec-009-verifier-agent
dark-factory-version: dev
created: "2026-08-23T10:01:50Z"
queued: "2026-08-23T10:24:40Z"
started: "2026-08-23T10:24:41Z"
completed: "2026-08-23T10:26:37Z"
branch: dark-factory/security-verifier-citations
---

# Add the security-verifier falsification gate agent

<summary>
- A new read-only agent ships whose job is to try to falsify each candidate security finding before it can emit
- It is the precision half of the review split — its recall counterpart is the existing security specialist judge
- It embeds a 7-item falsification checklist that a confirmed verdict must pass in full, with a concrete attacker scenario
- It returns exactly one of three verdicts per candidate, with a fixed field set and a mandatory reason whenever it rejects
- Every surviving high-severity finding must carry the checked-counterevidence field, so a confirmation is never empty-handed
- It documents its dispatch contract — invoked post-adjudication with the findings, the diff, and the derived model — active only when the security signal exists
- It is registered nowhere in any dispatch list; it is its own self-contained agent file using repo frontmatter conventions
- All examples are generic, and no other file in the plugin changes
</summary>

<objective>
Author `agents/security-verifier.md` as an adversarial falsification gate so that no high-severity security finding can emit without surviving a precision-focused kill attempt — the counterweight to the judge's recall.
</objective>

<context>
Read `CLAUDE.md` (repo root) — project conventions (generic examples only, no personal paths) and the "Adding a new agent" checklist (create the agent file; note that this task deliberately does NOT add the agent to any command dispatch list, and the CLAUDE.md Doc↔Agent row is conditional per the spec's recorded decision — see the spec's Non-goals and requirement 9 below).

Read `agents/go-security-specialist.md` (full) — the judge counterpart this agent offsets. Mirror its frontmatter conventions (`name`, `description`, `model`, `effort`, `tools`, `color`) and note its citation discipline statement: "toolchain findings don't need a `rule_id` (they're tool-output, not rule-violations)" — the toolchain provenance contract this verifier's gate sits on top of.

Read `docs/security/security-review-guide.md` (skim the RULE ids) — the mechanical rule base whose findings reach this gate (`go-security/hardcoded-secret`, `go-security/sql-string-interpolation`, etc.).

Read `docs/security/security-review-pipeline.md` (the `Model schema and lifecycle` and `Recon pass` sections) — the derived model the verifier consumes (`entry_points`, `resources[].authorization_functions`, `invariants[]`, each with `file:line` evidence; model is session-local and never committed).

Read `docs/agent-command-development-guide.md` (skim the agent-authoring standards) — the repo's agent file structure conventions (purpose section, role definition, workflow phases, output format).
</context>

<requirements>
1. Create `agents/security-verifier.md` (repo root). This is the ONLY file this prompt creates or modifies.

2. Frontmatter, following the repo convention seen in `agents/go-security-specialist.md`:
   - `name: security-verifier`
   - `description: <wording at your discretion>` — must convey: the security-mode post-adjudication falsification gate that tries to kill high-severity findings before they emit, precision over recall. Do not put "judge", "reviewer", or "auditor" in the name; the verdict is adversarial falsification.
   - `model: sonnet`
   - `effort: high`
   - `color: red` (mirror the judge `go-security-specialist`'s `color`)
   - `tools: Read, Grep, Glob` — the agent is read-only; do NOT include `Bash` and do NOT include any `allowed-tools` field (there are no allowed Bash tool patterns for a read-only agent). The agent analyzes existing files only; it never edits code, never writes findings or the model, never runs build or scan commands.

3. **Purpose section.** State plainly: this agent is an adversarial falsification gate. It receives candidate security findings produced by adjudication (severity-graded, provenance-kind-tagged) and attempts to KILL each one by finding counterevidence before it is allowed to emit. It is the **precision** half of the judge→recall / verifier→precision split: it is rewarded for correctly rejecting false positives, and a false keep (confirming a real non-vulnerability) is the failure mode it is hired to prevent — the recall side is the judge's job. State that high-severity security findings cannot emit without passing this gate.

4. **Dispatch contract section.** Document how the agent is invoked: post-adjudication, pre-emission, with (a) the candidate findings (each with severity, kind, provenance id, file:line), (b) the diff, (c) the derived security model (per `docs/security/security-review-pipeline.md`), and (d) the mechanical findings. State the activation contract: this dispatch is active when the current review session carries the security-review signal — no command change in this task, no command dispatch list entry, no `--security` flag.

5. **The 7-item falsification checklist — embed verbatim as seven numbered items**, each headed by its exact anchor phrase (the audit grep matches these): (1) **attacker-controlled input** — is the vulnerable value reachable from input the attacker controls, with no validation barrier? (2) **resource lookup** — does the code resolve the resource the finding names, and is the resolution attacker-influenced? (3) **authorization-absence search** — actively search for authorization, starting with **middleware** / service-layer authz (a route-level middleware guard, or a service-layer ownership check, kills an authz finding), before concluding absence; (4) **alternative code path** — is there a second path to the same resource or sink that bypasses the claimed control? (5) **authentication upstream** — is the entry point reachable only behind an **authentication** boundary that the attacker cannot cross? (6) **sink reachability** — is the dangerous sink actually reachable from the diff's changed lines, or is the path dead/built-but-unreachable? (7) **concrete attacker scenario** — write a concrete step-by-step attacker scenario; if you cannot, the finding is not confirmed.

6. **Verdict contract section.** Define the per-candidate verdict: `confirmed | plausible | rejected`. Define the field set the verdict carries: `confidence`, `exploitability`, `impact`, `attack_preconditions`, `attack_path`, `security_boundary_missing`, `counterevidence_checked`, plus `reject_reason` when the verdict is `rejected`. State the confirmation rule exactly: `confirmed` requires passing the FULL checklist, a concrete attacker scenario (item 7), AND a populated `counterevidence_checked` listing the counterevidence actually checked and why it does not hold. State that every surviving high-severity finding carries a populated `counterevidence_checked`. State that `reject_reason` is REQUIRED whenever the verdict is `rejected` (the checklist item or counterevidence that killed the finding). State that `plausible` is not a confirmation — a plausible finding survives as a required human review item, it does not by itself block (the blocking model — `confidence==confirmed ∧ exploitability==high ∧ impact≥medium` — is a sibling prompt's deliverable in the dormant Security Extension of `docs/selector-mode-guide.md`; do NOT author the blocking model here).

7. **Read-only + incentive section.** Restate the read-only discipline (no writes to any repo or model file; the agent analyzes and returns a verdict only) and the precision-over-recall incentive explicitly: the agent is rewarded for killing findings with solid counterevidence, and the judge's recall covers the miss direction.

8. Use generic examples only (User, Order, Product, Customer — e.g. a finding about a user/order resource handler). No trading terms, no personal paths, no version-existence claims. The agent is authored fresh from the contract in this prompt — the spec's spike draft existed only on the author's host and is not accessible in the container, so do not attempt to read or reference any host path; the 7-item checklist and verdict contract in requirements 5-6 ARE the source material.

9. Do NOT touch: `README.md` / `llms.txt` (prompt 4 registers the agent), any `commands/*.md`, `docs/*.md`, `scripts/*`, `rules/*`, `scenarios/*`, `CHANGELOG.md`. Do NOT add the agent to any dispatch list. **CLAUDE.md Doc↔Agent row — conditional, per the spec's recorded decision:** the verifier's contract is its own agent file (the falsification procedure is not a doc guide), so by default NO CLAUDE.md Doc↔Agent row is added. The only exception: IF the finalized agent file names a companion doc guide as its source of truth (i.e. the falsification procedure itself is documented in a guide rather than in this file), then add the row to keep the Doc↔Agent table complete. The 7-item checklist and verdict contract live in this agent file itself, so the exception is not expected to fire — but if you author the file in a way that names a guide as the source of truth for the procedure, add the row accordingly.
</requirements>

<constraints>
- Do NOT commit — dark-factory handles git. Do NOT run `git` commands.
- Precommit stays green after every prompt — `make precommit` must exit 0 at the end of this prompt.
- Verifier contract (frozen): 7-item falsification checklist (attacker-controlled input; resource lookup; authorization-absence search incl. middleware/service-layer authz; alternative code path; authentication upstream; sink reachability; concrete attacker scenario), verdict `confirmed|plausible|rejected`, `counterevidence_checked` required for every surviving high-severity finding, `reject_reason` when rejected, read-only, precision-over-recall incentive.
- Agent registration scope (frozen): the verifier is NOT added to any command dispatch list (`commands/code-review.md`, `commands/pr-review.md`, `commands/local-review.md`). The CLAUDE.md Doc↔Agent row is conditional per the spec (added only if the agent names a companion guide as its source of truth; the procedure lives in the agent file itself, so the default is no row). Registration in README/llms is prompt 4's job.
- Rule base frozen: no new `### RULE` blocks, no `rules/security/*.yml` change, no `rules/index.json` change, no `scripts/build-index.py` change.
- Generic examples only (User, Order, Product, Customer) — never trading terms; no personal paths (`~/Documents/`, `/Users/bborbe/`); self-contained plugin. No version-existence claims.
- CHANGELOG.md is NOT touched by this prompt (prompt 4 owns the `## Unreleased` bullet).
</constraints>

<verification>
Run from repo root. All commands are container-executable (no git).
```bash
# --- AC7: agent exists + contract anchors ---
test -f agents/security-verifier.md && echo "agent exists: ok"
grep -c 'counterevidence_checked' agents/security-verifier.md                          # must return >= 3
grep -cE 'confirmed|plausible|rejected' agents/security-verifier.md                    # must return >= 3
grep -nE 'attacker-controlled input|resource lookup|middleware|alternative code path|authentication upstream|sink reachability|attacker scenario' agents/security-verifier.md | wc -l   # must return >= 7 (all seven checklist anchors)

# --- Read-only: no Bash in tools / no allowed-tools ---
grep -nE '^tools:.*Bash|^allowed-tools' agents/security-verifier.md                   # must return 0 lines

# --- Registration scope negatives: no dispatch-list / no other-file leakage ---
grep -rn 'security-verifier' commands/*.md 2>/dev/null || echo "no command reference: ok"      # must return 0 matches
grep -rn 'security-verifier' README.md llms.txt 2>/dev/null || echo "no README/llms registration yet: ok"   # must return 0 matches (prompt 4 owns it)
grep -n 'security-verifier' CLAUDE.md || echo "no Doc<->Agent row: ok"                            # must return 0 lines (default — the procedure lives in the agent file; a row would only be correct if the file names a companion guide as source of truth)

# --- Full precommit ---
make precommit                                                                         # must exit 0
```
</verification>
