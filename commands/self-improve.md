---
description: Review THIS session and propose at most two durable improvements to the Claude Code environment (commands, agents, skills, guides, runbooks, memory/CLAUDE.md rules). Default outcome is "nothing worth keeping."
allowed-tools: Read, Edit, Glob, Grep, mcp__semantic-search__search_related
---

# Self Improve

You tune the environment, not the project. This session is the evidence.

**This command must stay inline** — it analyzes the parent conversation, and a
sub-agent runs in a fresh context that cannot see this session. Do not delegate
it to an agent.

Your output is almost always **zero or one** change. Two is the ceiling. A run
that concludes "nothing worth keeping this session" is a success.

The environment accretes commands, agents, and rules over time. Every new
artifact costs maintenance forever. Adding one is the expensive move — justify
it or don't.

---

## Phase 1 — Report (read-only)

### 1. What ran
List the skills, slash commands, and agents actually used this session. Note
which caused friction (retries, wrong output, needed correction).

### 2. Find repetition or cost
Scan the transcript for:
- the same instruction given 2+ times (this session or clearly a habit)
- a correction the user made that was general, not one-off
- a preventable mistake that cost real back-and-forth
- a workflow reinvented from scratch that a tool already half-covers

Ignore anything that happened once with no cost. One-offs never graduate.

Record each candidate as an **incident** — what happened, what it cost — not
as a rule. Do NOT draft rule wording or a diff sketch until Step 5 has chosen
the home: wording drafted early comes out CLAUDE.md-shaped (a terse imperative
bullet) and biases placement toward memory files.

### 3. Rate each candidate
Gate first, then grade — the same shape as `/vault-cli:reflect`'s significance filter.

**Hard gate (no quote, no proposal):** can you cite a verbatim quote + where it
happened? Fails the gate → discard silently.

Passers get a **worth-it score**:

| Signal | Weight |
|---|---|
| Recurrence — plausibly recurs in 3+ future sessions | +2 |
| Cost — the miss cost real back-and-forth (retry, correction, wasted turns) | +1 |
| Generality — the fix applies beyond this one task / project / file | +1 |
| Repair — fixes a tool that misfired, not a new rule bolted on | +1 |
| Obvious-anyway — the "fix" is just doing the naturally obvious thing | −2 |
| Routes to a `CLAUDE.md` though an existing artifact could own it (judged after Step 5 placement) | −1 |

Tier by score:
- **≥ 3 → propose** (ranked, max two)
- **1–2 → borderline** — name it in one line under Rejected, don't propose
- **≤ 0 → discard silently**

The score makes borderline calls explicit and inspectable instead of a coin-flip;
`Obvious-anyway −2` kills "just do it in the natural order" non-improvements.

### 4. Prefer editing over creating
Does an existing rule / command / agent / skill almost cover this? If yes,
propose a small edit to it. Only propose a NEW artifact when nothing existing
is close.

### 5. Place the fix — discover, walk the ladder, argue the exception

Placement is a search problem, not a routing decision. The reasoning that
generated a proposal is biased toward memory files (always loaded, zero
discovery cost) — counter that bias with mandatory discovery and a burden of
proof on the CLAUDE.md target.

**5a. Discovery (mandatory, before any routing).** Search for existing homes:
semantic search over the vault(s) when available
(`mcp__semantic-search__search_related "<topic>"`), plus Glob/Grep over
`commands/`, `skills/`, `agents/`, and the project's guide/runbook dirs. List
the top 2–3 candidate homes found, as file paths. No named candidates means
you haven't searched — do not route yet.

Query discipline: search the **workflow/domain name** ("development guide PR
workflow", "deploy runbook"), not the rule text you have in mind — rule-text
queries return junk and fake an empty result. Minimum two queries. Note that
guides and runbooks often live OUTSIDE the repo (e.g. an Obsidian vault), so
semantic search is the primary channel and Glob/Grep over the cwd alone is
insufficient evidence that no home exists.

**Empty discovery never routes to a CLAUDE.md.** If no home is found, propose
creating/extending a guide in the domain's knowledge dir, or output "no home
found — operator decides". A CLAUDE.md target must BEAT a named alternative;
it never wins by forfeit.

**5b. The ladder.** Work down the rungs. To descend past a rung you must NAME
the concrete candidate at that rung and give a one-line reason it cannot own
the fix. "Nothing fits" without a filename is not a reason. The candidate you
name must be the STRONGEST discovery hit for that rung — not a straw man you
can safely reject — and for the guide/runbook rung you must quote one heading
or line from the candidate file to prove it was actually opened.

1. The artifact that misfired → repair it.
2. The artifact already loaded at the moment of the mistake (command / skill /
   agent step) → extend it.
3. The guide or runbook read at point-of-use for that workflow → add the rule
   where it is read in context.
4. Project `CLAUDE.md` → only for a project convention no artifact can enforce.
5. Global `CLAUDE.md` → the exception. Requires the admission argument below.

New artifacts (slash command for a retyped prompt, agent for an independent
responsibility, skill for a multi-step capability with scripts/state) sit on
rungs 2–3: create one only when discovery proves nothing existing is close.

**5c. Global CLAUDE.md admission argument.** A proposal may target the global
memory only if ALL FOUR hold, argued one line each in the output:

- **Always-on:** matters in sessions unrelated to its domain. Counter-test:
  name one plausible session type where the line is dead weight — if you can
  name one, it fails.
- **Unowned:** name the closest artifact/guide from discovery and why it is
  not (and cannot be) loaded at the moment the rule applies.
- **Behavioral, not procedural:** shapes conduct everywhere ("be terse",
  "English only") — not a step in any workflow. Workflow steps always have a
  point-of-use home.
- **One stable line:** expressible as one terse imperative bullet that will
  not churn when tools change.

**De-generalization test** (apply before grading Always-on): state the rule
with its workflow named — "when opening a PR, run X"; "when deploying, check
Y". If the un-generalized version names a workflow step, the rule is
procedural and belongs at that step's point-of-use home. Generalizing the
wording until it sounds behavioral is the tell of a misroute, not a pass —
gates test the incident, not the phrasing.

Any argument missing or hand-wavy → auto-demote the proposal to the best named
home from discovery. If the target memory file already feels long, also
nominate one existing line to demote to a guide (soft one-in-one-out).

Memory files are prompt overhead in every future session. A rule that merely
restates what an artifact should enforce itself, or tells the operator to work
around a broken tool, is a symptom patch — repair the tool instead; fall back
to a `CLAUDE.md` rule only when the tool genuinely can't be changed (external
constraint).

### 6. Output
Short. Max two proposals, ranked.

**Session in one line:** <process-level summary>

Per proposal:
- **Change:** what, and where (exact target file / artifact)
- **Worth-it:** <score> (e.g. recurrence +2, cost +1)
- **Evidence:** verbatim quote(s) + how often
- **Placement:** discovery hits (top candidate homes as file paths) + the ladder walk (rung → named candidate → one-line why-not), ending at the chosen home; global-`CLAUDE.md` targets append the four admission-argument lines
- **Edit or new:** if new, why nothing existing fit
- **Diff sketch:** the concrete line(s) to add or change

Then **Rejected** — one line each for dropped candidates and why.

If nothing clears the bar, say exactly: "Nothing worth keeping this session." Stop.

---

## Phase 2 — Apply (only after explicit approval)

Do NOT edit in Phase 1. Wait for the user to pick which proposals to accept.

On approval:
1. Read the target file before editing.
2. Smallest change that captures the rule. No prose bloat.
3. Match the target artifact's existing conventions — CLAUDE.md: terse imperative bullets; command/agent/skill: existing section structure and frontmatter; runbook: numbered step format; guide: existing rule format.
4. Report what changed, one line per file.

Never edit beyond the approved proposals. Never expand scope while applying.

---

## Principles
- Default to zero. Two is the ceiling.
- Edit existing before creating new.
- No quote, no proposal.
- Placement is discovered, not assumed — a `CLAUDE.md` target must survive the admission argument.
- Fix the cause (missing rule/tool), not the symptom (one bad turn).
- Every permanent rule you add, someone maintains forever.
