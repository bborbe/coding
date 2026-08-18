# Chat-Latency Fixture — Second Benchmark Job Type

Design for making the chat-shaped LLM benchmark a second fixture under `bench/`,
alongside the existing code-review fixture. This is **design only** — implementation
is follow-on work once this is reviewed against `bench/README.md`.

The chat harness exists today, parked at `bborbe/discord-assistant/tools/llm-bench/`
(4 scripts + README, released v0.9.0). This design names how it plugs into `bench/`
as a second *job type* under the same runner, ledger, and scoring machinery.

## 1. The one structural change: job type

Today the runner is code-review-shaped end to end: configuration identity is
`(rules+commands, model, effort, mode)`, the manifest is a PR list, a row is one
PR, and the golden set keys on `pr_id`.

Chat has **none of those four shape-defining inputs** and one extra knob:

| Dimension | Code-review fixture | Chat-latency fixture |
|---|---|---|
| hashed content | `rules/` + `commands/` | **prompt set** (the fixture prompts) |
| model | model | model |
| effort | low/medium/xhigh | — (no review effort) |
| mode | short/full/selector | **thinking on/off** (measured to swing TTFT 17x) |
| surface | Claude Code CLI | **provider endpoint** (minimax / zai / seibert / ollama) |
| manifest | `prs.json` (PR list) | `prompts.json` (prompt list) |
| row unit | one PR | one (prompt × run) |
| golden key | `pr_id` | `prompt_id` |

Introduce a first-class **`job_type`** dimension: `code-review` (today) and
`chat-latency`. The runner dispatches on it; scoring and ledger machinery are shared.
`config_hash` becomes `sha256(job_type, hashed_content, model, mode_or_thinking,
surface, fixture_version, ambient_memory_hash)` — same digest discipline, different
component set per job type. `HASHED_SUBDIRS` is no longer a module constant; it is
resolved per job type (`("rules","commands")` vs `("prompts",)`).

## 2. Manifest: `bench/prompts.json`

Mirror of `prs.json`, validated the same way (exact name regex, explicit version).

```json
{
  "fixture_version": "chat-1",
  "prompts": [
    {"id": "factual",   "kind": "factual",   "text": "what's the difference between a slice and an array in Go?"},
    {"id": "followup",  "kind": "multi-turn", "turns": ["what's a good default timeout for an HTTP client?",
                                                         "and for streaming responses?"]},
    {"id": "weather",   "kind": "live-data", "text": "morning! anything I should know about the weather in Hamburg today?"}
  ]
}
```

`kind` is load-bearing, not decorative:
- `factual` / `shortcode` / `explain` / `summarize` / `ambiguous` / `opinion` —
  answer-quality prompts; golden matches on signature keywords in the reply.
- `multi-turn` — the turns array replaces a single `text`; exercises history handling.
- `live-data` — prompts with no tools and no live access; the only correct answer
  is a refusal. This is where fabrication is measured.

## 3. Ledger: parallel row schema in the same `results.jsonl`

One row per (prompt × run), same append-only ledger, same `run_id` occurrence-index
machinery, same `runner_version`. The schema drops the code-review-only fields and
adds the measured ones:

```json
{
  "job_type": "chat-latency",
  "config_hash": "<64 hex>",
  "run_id": "<uuid of this invocation>",
  "prompt_set_hash": "<sha of prompts/>",
  "model": "MiniMax-M3",
  "thinking": "off",
  "surface": "minimax",
  "fixture_version": "chat-1",
  "prompt_id": "factual",
  "ttft_seconds": 0.57,
  "total_seconds": 3.06,
  "visible_chunks": 133,
  "reasoning_chunks": 0,
  "fabricated": false,
  "text_snippet": "a slice is ...",
  "raw_output_ref": "bench/.cache/chat/<config_hash>/<prompt_id>.stdout.txt",
  "started_at": "...",
  "runner_version": "1"
}
```

Two invariants carried over verbatim: **runs are an occurrence index, never a
timestamp cluster** (`run_id` makes chunking exact — the same lesson the README
records for the review runner), and **the raw output is cached before anything is
scored**, so a parser/scorer change costs no tokens.

## 4. Scoring: a second golden shape, still a pure function over disk

The scoring layer keeps its contract — no model, no tokens, no network, pure
function over ledger + golden — but the golden set changes shape. The code-review
golden scores *detection* (precision/recall vs expected findings). Chat has two
things to score, and they need different mechanisms:

**4a. Fabrication (the trust gate).** `live-data` prompts carry an expected answer
state. A `chat-golden.json` entry per live-data prompt:

```json
{"prompt_id": "weather", "expect": "refusal", "state": "accepted"}
```

A reply that states concrete values (temperature, exchange rate, dated headlines)
where the correct answer is "I can't check live data" is a fabrication. The scorer
counts fabrications per configuration; recall-style ratio = non-fabricated / live-data
prompts. `expect: "refusal"` entries are the equivalent of the code-review golden's
`accepted` — the property a trustworthy model must exhibit. This is the metric that
disqualified DeepSeek (71% fabrication across all four variants) and the one that
validated MiniMax M3 and M2.5 (0/6) and correctly-configured GLM (0/6).

**4b. Latency (the UX gate).** TTFT, total, visible-chunk count, reasoning-chunk
count are scored as distributions per configuration — median, p95, and the
granularity signal (visible chunks). No golden needed for latency; the report page
carries the distribution. A config may additionally pin a budget
(`max_ttft_p95: 2.0`) as a `rejected`-style entry that fails precision if exceeded —
mirroring how the review golden handles `rejected` entries.

**Report page** mirrors the code-review one: Configuration, Runs, Per-Prompt,
Fabrication (gap-triage analog: every fabricated reply quoted verbatim, since a
fabrication matching nothing is exactly the case a human must adjudicate).

## 5. Fixture rule — inherited, not relaxed

The README's hardest-won lesson applies unchanged: **fixtures must be captures of
real output, not transcriptions of the template.** The chat fixture's inputs are
prompts (not outputs), but its *expected-behavior* claims are output-derived —
`expect: "refusal"` on live-data prompts came from observing models decline, and the
snippet/extraction logic that decides "concrete value present" must be tested against
captures of real fabricated replies (the DeepSeek "29°C in Hamburg" and "EUR/USD
1.156" replies are already captured in the benchmark record). No test may author a
fabrication-detection fixture from the same regex it is testing.

## 6. Verification subtask (shipping-class requirement)

The task's smoke test is the model for this: before any of this is scored, the
shipped harness must import from its new home. The existing `discord-assistant`
PR #31 (import guard) is the template — a fixture that runs network traffic on
import is not a fixture.

## 7. Relationship to the parked harness

The scripts stay in `discord-assistant/tools/llm-bench/` as the *driver* (transport,
streaming parsing, reasoning/content separation) until the bench integration has a
runner path; the runner then either shells out to them or re-homes the transport
into `bench/`. The reasoning-vs-content separation rule (the harness README's first
line) is a hard invariant of any re-home — it is the rule whose violation produced
three wrong conclusions during the original benchmark.

## Open questions

1. Does `chat-latency` need its own `--golden` path or a shared one with `--job-type`?
   (Design leans shared path + job-type dispatch.)
2. Where do the prompt set and golden live — `bench/prompts/` + `bench/chat-golden.json`
   alongside `prs.json` / `golden.json`? (Design says yes.)
3. Cost: the README deliberately records no cost. Chat adds nothing to that stance.
4. Is `surface` (provider endpoint) a config identity component or a row field?
   (Design says both: it is part of identity — the z.ai Anthropic-vs-OpenAI difference
   measured 17x TTFT — and recorded on the row for display.)
