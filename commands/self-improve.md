---
description: Review THIS session and propose at most two durable improvements to the Claude Code environment (memory/CLAUDE.md rules, commands, agents, skills). Default outcome is "nothing worth keeping."
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

### 3. Keep-forever test
For each candidate, both must hold or discard it:
- **Recurrence:** plausibly recurs in 3+ future sessions?
- **Evidence:** you can cite a verbatim quote + where it happened.

Discard silently: one-offs, "nice to have," anything you can't quote.

### 4. Prefer editing over creating
Does an existing rule / command / agent / skill almost cover this? If yes,
propose a small edit to it. Only propose a NEW artifact when nothing existing
is close.

### 5. Route the fix by scope
| The fix is a… | It belongs in… |
|---|---|
| Global preference / habit | your global Claude memory (global `CLAUDE.md`) |
| Project convention | that project's `CLAUDE.md` |
| The exact same prompt, retyped | a slash command |
| An independent responsibility | an agent |
| Reusable multi-step capability with scripts/state | a skill |

**Repair before route-around.** If an existing command / agent / skill *misfired*
(wrong output, deadlock, needed a manual workaround), the fix belongs IN that
artifact — repair the tool. Only fall back to a `CLAUDE.md` rule when the tool
genuinely can't be changed (external constraint). A `CLAUDE.md` rule telling the
operator to work around a broken tool is a symptom patch — rank it below fixing
the tool.

### 6. Output
Short. Max two proposals, ranked.

**Session in one line:** <process-level summary>

Per proposal:
- **Change:** what, and where (exact target file / artifact)
- **Evidence:** verbatim quote(s) + how often
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
3. Memory/CLAUDE.md rules: match the existing terse, imperative bullet style.
4. Report what changed, one line per file.

Never edit beyond the approved proposals. Never expand scope while applying.

---

## Principles
- Default to zero. Two is the ceiling.
- Edit existing before creating new.
- No quote, no proposal.
- Fix the cause (missing rule/tool), not the symptom (one bad turn).
- Every permanent rule you add, someone maintains forever.
