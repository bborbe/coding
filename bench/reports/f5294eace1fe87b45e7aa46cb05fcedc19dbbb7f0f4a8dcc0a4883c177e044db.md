f5294eace1fe87b45e7aa46cb05fcedc19dbbb7f0f4a8dcc0a4883c177e044db

## Configuration
- model: MiniMax-M3.1-Flash-Preview[1m]
- effort: high
- mode: full
- config_hash: f5294eace1fe87b45e7aa46cb05fcedc19dbbb7f0f4a8dcc0a4883c177e044db
- rules_commands_hash: 83034aa7e535f23937b54a88b6e6b3a49aa0a2b3421f5d2c3b00a6fee857a40b
- prs_version: curated-1
- coding version: 0.60.0
- golden baseline coding version: v0.35.6
- golden version: golden-curated-4
- runner_version: 1
- rows skipped: 0
- cost: not recorded — the ledger carries no cost field.

*golden-curated-4* carries 21 `rejected` entries, so precision is measurable: reporting one costs precision. With so few adjudicated, a single hit still moves the number a long way — read it as directional, not calibrated.

No signature embeds a line reference, so a re-report of the same issue at a different line still matches. `recall` measures issue detection.

## Runs
| run | span | PRs | complete | golden in scope | findings | hits | misses | matched rejected | gap candidates | recall | precision | wall time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17T22:30:48.777768+00:00 … 2026-10-17T22:30:48.777768+00:00 | 1/20 | partial | 6 | 12 | 0 | 5 | 0 | 12 | 0.000 | n/a | 222 |

## Per-PR
| run | pr_id | golden in scope | hits | misses | findings | gap candidates | dropped items | missing sections | duration (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | tts-mcp#16 | 6 | 0 | 5 | 12 | 12 | 0 | — | 222 |

*Effective fixture: **1 of 20** PRs produced a scored row.* The 19 absent rows are not a zero-finding result — they were rejected before scoring, so they lower confidence without lowering recall.

## Gap-triage candidates
These findings matched no golden entry. They are **not a precision failure** — the golden set is a bootstrap from one strong-model run, and a finding it does not describe is evidence the set is incomplete.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:8

**`skills/voice/SKILL.md:8`** — "**This skill is the sole authority on spoken-output volume** — there is no competing always-on rule in `~/.claude/CLAUDE.md`" is false against the live file, and this PR does not change it. `~/.claude/CLA.md` lines 83–87 still carry `Voice Chat Brevity` and `Attention Costs Operator`, the latter of which explicitly gates `mcp__tts__say` with *"is there something the user must DO…? If no, do not send; silence is the default."* That rule **contradicts `narrate` mode's entire purpose** — a spoken gist of an answer is by definition usually not an action-requiring event. The PR's thesis (two sources of truth, move to one) is unachieved at merge: the diff relocates the text into the skill but removes nothing. Fix: land the `~/.claude/CLAUDE.md` removal in the same PR, or restate as intent ("supersedes the old rule once removed") and track the removal as a required follow-up. *(rule: `agent-cmd/single-source-of-truth`)*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — the same false environment claim is duplicated into the frontmatter `description`: "Sole authority on spoken-output volume — no always-on rule competes with it." Worse here than in the body, because the description is the text Claude pattern-matches on when deciding to activate the skill — it invites the skill to override a live rule it does not actually supersede. Delete the clause. *(rule: `skill-writing/skill-md-frontmatter-required`)*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:87

**`skills/voice/SKILL.md:87`** — "Anything at all when the user is clearly sitting there watching it scroll by" sits under **`Never speak, in any mode:`**, but `narrate` and `interview` are modes whose whole purpose is speaking to a present user. An unconditional "in any mode" ban lets Claude silently nullify the mode the user just selected — the one place the file stops telling Claude unambiguously what to do. Scope it: ad-hoc commentary only, not the mode's own channel. *(rule: `skill-writing/skill-md-frontmatter-required`)*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:59

**`skills/voice/SKILL.md:59`** vs **`:86`** — "never read a whole reply aloud" (Speaking playbook) and "The reply verbatim… never let voice and text be the same content at the same length" ("Never speak" list) are the same constraint in two homes. The playbook is untouched by this diff, so the two drift independently. Keep volume in "How much to speak", cross-reference from `:59`.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:14

**`skills/voice/SKILL.md:14-19`** vs **`:69-74`** vs **`:76-79`** vs **`:93`** — mode behaviour is defined in four places; `narrate` appears in all four, `interview` in three. The capability table is the only place stating the modes do not compose and the only place giving the `Answers` column. Make the table authoritative and reduce Args to pointers. *(rule: `skill-writing/skill-md-frontmatter-required`)*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:15

**`skills/voice/SKILL.md:15`** — `narrate` is gated on "every **substantive** answer"; nothing in the file defines substantive. `interview` has a full playbook for its trigger; `narrate` has none for its. Give it the same treatment (one line on what counts).

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:71

**`skills/voice/SKILL.md:71-72`** — `| on | ✅ | ❌ screen only | ❌ decisions only |`: a ❌ next to a positive under a column headed "Every question" reads both ways. Use `partial — decisions only`.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:33

**`skills/voice/SKILL.md:33`** — "Skip the utterance for `off` and `status`" omits `restart`, which is a documented arg with no stated confirmation behaviour.

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:3

**`skills/voice/SKILL.md:3`** — description is ~604 chars, mostly non-trigger content (authority claim, selftest caveat, Args list). Keep the trigger phrases; the caveat is already covered in "No selftest on activation".

### run 1 — tts-mcp#16 — CHANGELOG.md:16

**`CHANGELOG.md:16`** — `feat:` on the authority-relocation bullet describes a policy relocation, not a capability; it forces a minor bump. Use `refactor:` and reserve `feat:` for `narrate`. *(rule: `changelog/conventional-prefix-required`, advisory — prefix presence passes)*

### run 1 — tts-mcp#16 — CHANGELOG.md:12

**`CHANGELOG.md:12`, `:16`, `:17`** — none of the three bullets is imperative; the repo's own v0.3.1/v0.4.0 bullets are. Advisory only — the rule is scoped to commit subjects, and the commit subject `make the voice skill own…` passes. *(rule: `git-commit/imperative-mood`, advisory)*

### run 1 — tts-mcp#16 — skills/voice/SKILL.md:78

**`skills/voice/SKILL.md:78`** — `say("Build failed in capitalcom-gateway.")` names an internal repo in a public one; use a generic service name.
