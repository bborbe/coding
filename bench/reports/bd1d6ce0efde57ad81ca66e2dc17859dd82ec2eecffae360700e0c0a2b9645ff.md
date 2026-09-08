bd1d6ce0efde57ad81ca66e2dc17859dd82ec2eecffae360700e0c0a2b9645ff

## Configuration
- model: sonnet
- effort: medium
- mode: short
- config_hash: bd1d6ce0efde57ad81ca66e2dc17859dd82ec2eecffae360700e0c0a2b9645ff
- rules_commands_hash: ecc803331f860b845a6a1b8a103e889bce02520e8cc04ea88102de74c8d5600d
- prs_version: curated-1
- coding version: 0.51.0
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
| 1 | 2026-08-10T12:21:25.269360+00:00 … 2026-08-10T13:18:11.670252+00:00 | 20/20 | complete | 158 | 14 | 5 | 132 | 0 | 9 | 0.036 | 1.000 | 1232 |
| 2 | 2026-08-10T12:43:54.664847+00:00 … 2026-08-10T13:38:05.334481+00:00 | 20/20 | complete | 158 | 14 | 1 | 136 | 0 | 13 | 0.007 | 1.000 | 1234 |
| 3 | 2026-08-10T13:07:48.304482+00:00 … 2026-08-10T14:04:23.521458+00:00 | 19/20 | partial | 149 | 9 | 4 | 126 | 0 | 5 | 0.031 | 1.000 | 1155 |
| 4 | 2026-08-10T13:27:44.216805+00:00 … 2026-08-10T14:08:05.794755+00:00 | 17/20 | partial | 133 | 6 | 2 | 115 | 0 | 4 | 0.017 | 1.000 | 1074 |
| 5 | 2026-08-10T13:49:14.364860+00:00 … 2026-08-10T14:06:28.625360+00:00 | 8/20 | partial | 76 | 6 | 2 | 63 | 0 | 4 | 0.031 | 1.000 | 609 |

## Per-PR
| run | pr_id | golden in scope | hits | misses | findings | gap candidates | dropped items | missing sections | duration (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | tts-mcp#20 | 1 | 0 | 1 | 0 | 0 | 0 | — | 25 |
| 1 | github-pr-review-agent#11 | 16 | 0 | 14 | 0 | 0 | 0 | — | 82 |
| 1 | quant#109 | 10 | 0 | 10 | 1 | 1 | 0 | — | 98 |
| 1 | node-skeleton#2 | 12 | 1 | 11 | 2 | 1 | 0 | — | 92 |
| 1 | python-skeleton#3 | 17 | 1 | 15 | 2 | 1 | 0 | — | 58 |
| 1 | backup#15 | 4 | 0 | 2 | 0 | 0 | 0 | — | 29 |
| 1 | bw#41 | 3 | 0 | 2 | 0 | 0 | 0 | — | 34 |
| 1 | dark-factory#71 | 2 | 0 | 2 | 0 | 0 | 0 | — | 46 |
| 1 | tts-mcp#16 | 6 | 0 | 5 | 0 | 0 | 0 | — | 42 |
| 1 | tts-mcp#3 | 6 | 0 | 5 | 0 | 0 | 0 | — | 42 |
| 1 | distill#6 | 10 | 1 | 6 | 2 | 1 | 0 | — | 51 |
| 1 | vault-ui#39 | 6 | 0 | 6 | 0 | 0 | 0 | — | 65 |
| 1 | recurring-task-creator#30 | 6 | 0 | 4 | 0 | 0 | 0 | — | 56 |
| 1 | discord-assistant#5 | 13 | 1 | 12 | 3 | 2 | 0 | — | 125 |
| 1 | tts-mcp#13 | 10 | 1 | 8 | 2 | 1 | 0 | — | 105 |
| 1 | github-releaser-agent#8 | 13 | 0 | 9 | 0 | 0 | 0 | — | 73 |
| 1 | discord-assistant#1 | 9 | 0 | 9 | 2 | 2 | 0 | — | 96 |
| 1 | helm#3 | 4 | 0 | 3 | 0 | 0 | 0 | — | 32 |
| 1 | vault-cli#68 | 1 | 0 | 1 | 0 | 0 | 0 | — | 32 |
| 1 | tts-mcp#10 | 9 | 0 | 7 | 0 | 0 | 0 | — | 48 |
| 2 | github-pr-review-agent#11 | 16 | 0 | 14 | 2 | 2 | 0 | — | 69 |
| 2 | node-skeleton#2 | 12 | 0 | 12 | 0 | 0 | 0 | — | 105 |
| 2 | python-skeleton#3 | 17 | 0 | 16 | 2 | 2 | 0 | — | 44 |
| 2 | bw#41 | 3 | 0 | 2 | 1 | 1 | 0 | — | 29 |
| 2 | dark-factory#71 | 2 | 0 | 2 | 0 | 0 | 0 | — | 45 |
| 2 | tts-mcp#16 | 6 | 0 | 5 | 0 | 0 | 0 | — | 34 |
| 2 | tts-mcp#3 | 6 | 0 | 5 | 1 | 1 | 0 | — | 33 |
| 2 | distill#6 | 10 | 1 | 6 | 1 | 0 | 0 | — | 59 |
| 2 | discord-assistant#5 | 13 | 0 | 13 | 0 | 0 | 0 | — | 146 |
| 2 | github-releaser-agent#8 | 13 | 0 | 9 | 1 | 1 | 0 | — | 84 |
| 2 | discord-assistant#1 | 9 | 0 | 9 | 2 | 2 | 0 | — | 61 |
| 2 | helm#3 | 4 | 0 | 3 | 0 | 0 | 0 | — | 30 |
| 2 | tts-mcp#20 | 1 | 0 | 1 | 0 | 0 | 0 | — | 39 |
| 2 | quant#109 | 10 | 0 | 10 | 1 | 1 | 0 | — | 135 |
| 2 | vault-cli#68 | 1 | 0 | 1 | 0 | 0 | 0 | — | 34 |
| 2 | backup#15 | 4 | 0 | 2 | 0 | 0 | 0 | — | 32 |
| 2 | vault-ui#39 | 6 | 0 | 6 | 2 | 2 | 0 | — | 55 |
| 2 | tts-mcp#13 | 10 | 0 | 9 | 1 | 1 | 0 | — | 86 |
| 2 | recurring-task-creator#30 | 6 | 0 | 4 | 0 | 0 | 0 | — | 53 |
| 2 | tts-mcp#10 | 9 | 0 | 7 | 0 | 0 | 0 | — | 62 |
| 3 | node-skeleton#2 | 12 | 0 | 12 | 0 | 0 | 0 | — | 163 |
| 3 | python-skeleton#3 | 17 | 1 | 15 | 1 | 0 | 0 | — | 62 |
| 3 | bw#41 | 3 | 0 | 2 | 1 | 1 | 0 | — | 47 |
| 3 | dark-factory#71 | 2 | 0 | 2 | 0 | 0 | 0 | — | 38 |
| 3 | tts-mcp#16 | 6 | 0 | 5 | 0 | 0 | 0 | — | 35 |
| 3 | tts-mcp#3 | 6 | 0 | 5 | 0 | 0 | 0 | — | 57 |
| 3 | distill#6 | 10 | 1 | 6 | 2 | 1 | 0 | — | 64 |
| 3 | discord-assistant#5 | 13 | 1 | 12 | 1 | 0 | 0 | — | 95 |
| 3 | github-releaser-agent#8 | 13 | 0 | 9 | 0 | 0 | 0 | — | 50 |
| 3 | discord-assistant#1 | 9 | 0 | 9 | 1 | 1 | 0 | — | 74 |
| 3 | tts-mcp#20 | 1 | 0 | 1 | 0 | 0 | 0 | — | 29 |
| 3 | github-pr-review-agent#11 | 16 | 0 | 14 | 0 | 0 | 0 | — | 72 |
| 3 | quant#109 | 10 | 0 | 10 | 1 | 1 | 0 | — | 88 |
| 3 | vault-cli#68 | 1 | 0 | 1 | 0 | 0 | 0 | — | 40 |
| 3 | backup#15 | 4 | 0 | 2 | 0 | 0 | 0 | — | 33 |
| 3 | vault-ui#39 | 6 | 0 | 6 | 1 | 1 | 0 | — | 53 |
| 3 | helm#3 | 4 | 0 | 3 | 0 | 0 | 0 | — | 39 |
| 3 | recurring-task-creator#30 | 6 | 0 | 4 | 0 | 0 | 0 | — | 50 |
| 3 | tts-mcp#13 | 10 | 1 | 8 | 1 | 0 | 0 | — | 65 |
| 4 | node-skeleton#2 | 12 | 0 | 12 | 0 | 0 | 0 | — | 106 |
| 4 | python-skeleton#3 | 17 | 1 | 15 | 1 | 0 | 0 | — | 63 |
| 4 | bw#41 | 3 | 0 | 2 | 0 | 0 | 0 | — | 49 |
| 4 | tts-mcp#16 | 6 | 0 | 5 | 0 | 0 | 0 | — | 58 |
| 4 | tts-mcp#3 | 6 | 0 | 5 | 0 | 0 | 0 | — | 41 |
| 4 | distill#6 | 10 | 1 | 6 | 1 | 0 | 0 | — | 66 |
| 4 | discord-assistant#5 | 13 | 0 | 13 | 1 | 1 | 0 | — | 102 |
| 4 | github-releaser-agent#8 | 13 | 0 | 9 | 0 | 0 | 0 | — | 59 |
| 4 | discord-assistant#1 | 9 | 0 | 9 | 2 | 2 | 0 | — | 81 |
| 4 | tts-mcp#20 | 1 | 0 | 1 | 0 | 0 | 0 | — | 25 |
| 4 | github-pr-review-agent#11 | 16 | 0 | 14 | 0 | 0 | 0 | — | 65 |
| 4 | quant#109 | 10 | 0 | 10 | 1 | 1 | 0 | — | 138 |
| 4 | vault-cli#68 | 1 | 0 | 1 | 0 | 0 | 0 | — | 49 |
| 4 | backup#15 | 4 | 0 | 2 | 0 | 0 | 0 | — | 35 |
| 4 | dark-factory#71 | 2 | 0 | 2 | 0 | 0 | 0 | — | 34 |
| 4 | vault-ui#39 | 6 | 0 | 6 | 0 | 0 | 0 | — | 60 |
| 4 | helm#3 | 4 | 0 | 3 | 0 | 0 | 0 | — | 44 |
| 5 | node-skeleton#2 | 12 | 0 | 12 | 1 | 1 | 0 | — | 71 |
| 5 | python-skeleton#3 | 17 | 1 | 15 | 1 | 0 | 0 | — | 66 |
| 5 | bw#41 | 3 | 0 | 2 | 0 | 0 | 0 | — | 41 |
| 5 | tts-mcp#16 | 6 | 0 | 5 | 0 | 0 | 0 | — | 47 |
| 5 | tts-mcp#3 | 6 | 0 | 5 | 1 | 1 | 0 | — | 51 |
| 5 | distill#6 | 10 | 1 | 6 | 1 | 0 | 0 | — | 176 |
| 5 | github-releaser-agent#8 | 13 | 0 | 9 | 0 | 0 | 0 | — | 59 |
| 5 | discord-assistant#1 | 9 | 0 | 9 | 2 | 2 | 0 | — | 97 |

*Effective fixture: **84 of 100** PRs produced a scored row.* The 16 absent rows are not a zero-finding result — they were rejected before scoring, so they lower confidence without lowering recall.

## Gap-triage candidates
These findings matched no golden entry. They are **not a precision failure** — the golden set is a bootstrap from one strong-model run, and a finding it does not describe is evidence the set is incomplete.

### run 1 — quant#109 — task/recurring-schedules/prod/home-assistant-update-backup.yaml:68

**`task/recurring-schedules/prod/home-assistant-update-backup.yaml:68`** — Saturday-scheduled task gets `due_date: "{{current_date}}"` while other Saturday-scheduled tasks added in this same PR (`check-ftmo-demo-accounts.yaml`, `lexoffice-invoices.yaml`, `moneymoney-review.yaml`, `plan-next-week.yaml`, `plan-weekend.yaml`, `renew-gmail-oauth-tokens.yaml`, `weekly-review.yaml`) get `due_date: "{{next_sun_date}}"`. Same weekday, two different due-date policies with no distinguishing comment — `opnsense-update.yaml`, `run-update-all-saturday.yaml`, `shutdown-k3s.yaml`, `topic-backup-saturday.yaml`, and `turn-on-hell.yaml` have the same inconsistency. Confirm this split is intentional (e.g. same-day-doable ops tasks vs. tasks that legitimately need Sunday buffer) or normalize it.

### run 1 — node-skeleton#2 — package.json:5

**`package.json:5`** — `"main": "src/index.ts"` points a package-consumer-facing field at a `.ts` file with no compiled output; harmless for this skeleton (it's not required as a dependency) but worth a comment if that's intentional going forward.

### run 1 — python-skeleton#3 — Makefile.precommit:118

**`Makefile.precommit:118-119`** — `trivy fs` pins `--db-repository` but not a Trivy CLI version (unlike `pip-audit`, which is pinned via `PIP_AUDIT_VERSION`); CI installs whatever `apt-get install trivy` resolves to at run time, so gate behavior can drift silently between runs. Not blocking since this mirrors go-skeleton/node-skeleton per the stated rationale.

### run 1 — distill#6 — hooks/deny-generated-file-edits.sh:29

**`hooks/deny-generated-file-edits.sh:29`** — `source_dir=$(grep -oE 'Source:[[:space:]]*\S+' ...)` stops at the first whitespace, so a `Source:` path containing a space (e.g. under `~/Library/...`) would be truncated in the denial message. Low impact — cosmetic on the guidance text only.

### run 1 — discord-assistant#5 — src/config.js:171

**`src/config.js:171-181`** — `config.isAddressed` allocates a `new RegExp(...)` per wake phrase on every call (every mic transcription event), where the Python side precompiles `_WAKE_RE` once at module load. Not a correctness issue at this call frequency, but easy to hoist to module scope like the Python side does.

### run 1 — discord-assistant#5 — src/config.js:343

**`src/config.js:343-364`** — `WAKE_LEAD_WORDS` duplicates `shim/claude_openai_shim.py`'s `_FILLER_WORDS ∪ {"hey"}` by hand across two languages/processes. Currently in sync (verified: 20 words match exactly), but the comment already flags this as a manual-sync risk — no single source of truth exists to catch future drift other than a diligent reviewer.

### run 1 — tts-mcp#13 — src/server.py:332

**`src/server.py:332-353`** — `voice` is validated synchronously against `state.voices` before enqueueing (400 on mismatch), but `instruct` is not checked against the configured engine at all — an `instruct` sent while running the `voxtral` engine is accepted with `202 Accepted` and only fails later, surfacing as an async status error rather than an immediate request error. Inconsistent validation timing for two similarly-shaped input errors; worth a synchronous check (e.g. `state.engine.kind == VOXTRAL` and `body.instruct is not None` → 400) to match the voice-validation pattern.

### run 1 — discord-assistant#1 — src/index.js:272

**`src/index.js:272`** — Swallowing the `uncaughtException` for network faults assumes discord.js's internal reconnect machinery is still intact after an exception that, by definition, had "no listener to catch it" inside `ws`. If that throw happened outside discord.js's own shard state machine (as the comment implies), `gatewayReady` may be left permanently `false` with no `shardResume`/`shardReady` ever firing again — a silent, unrecoverable hang that's worse than the crash-and-restart this PR is meant to fix, since `supervise.sh` never gets a nonzero exit to act on. No test exercises this path to confirm reconnection actually happens after the throw is swallowed.

### run 1 — discord-assistant#1 — scripts/supervise.sh:41

**`scripts/supervise.sh:41`** — `SUPERVISE_DELAY_MIN=0` produces `delay=$((0*2))=0` forever, i.e. no backoff at all. Harmless with the documented default of 2, but an unvalidated env override silently defeats the anti-hot-loop protection the script exists to provide.

### run 2 — github-pr-review-agent#11 — README.md:29

**`README.md:29-33`** — the new run-modes table doesn't mention `SKIP_POST` env var parity (code supports both `--skip-post` and `env:"SKIP_POST"` per `cmd/run-task/main.go:75`), unlike other flags in the same file which are documented with both forms elsewhere. Minor doc completeness gap, not incorrect.

### run 2 — github-pr-review-agent#11 — pkg/skip_post_boundary_test.go

**`pkg/skip_post_boundary_test.go`** — the file carries a substantial header comment plus per-case comments explaining the regression it guards against; verbose relative to the rest of the test suite's style, but justified given the subtlety (interface-nil vs concrete-nil) it protects.

### run 2 — python-skeleton#3 — Makefile.precommit:120

**`Makefile.precommit:120`** — `--skip-dirs .venv` is the only exclusion passed to `trivy fs`; if the repo ever accumulates other local/build dirs (e.g. `dist/`, `.mypy_cache/`, `node_modules/` for tooling), they'll be scanned unnecessarily and could slow CI or surface noise. Not a correctness issue given the current tree, just worth revisiting if scan time grows.

### run 2 — python-skeleton#3 — pyproject.toml:65

**`pyproject.toml:65`** — comment for `S104` wraps across three lines with hand-aligned indentation; harmless but slightly fragile to reformat by hand if `ruff format`/editors reflow it later.

### run 2 — bw#41 — bundles/intellij/metadata.py:29

**`bundles/intellij/metadata.py:29`** — Unrelated whitespace-only cleanup (blank-line removal) bundled into what looks like an ARP-table-focused change; consider splitting into its own commit for a cleaner history, though harmless as-is.

### run 2 — tts-mcp#3 — skills/voice/SKILL.md:16

**`skills/voice/SKILL.md:16`** — "Re-running `/voice on` mid-session re-handshakes" line was removed along with the handshake section, but the new "No selftest on activation" section doesn't mention that `/voice on` no longer re-tests mid-session — a user relying on the old re-handshake-by-toggling trick will silently get no verification now. Worth a one-line pointer to `/tts-mcp:voice-test` as the replacement, though the section already links to it generally so this is minor.

### run 2 — github-releaser-agent#8 — pkg/githubtags/tags.go:34

**`pkg/githubtags/tags.go:34`** — the `TagsFetcher` interface doc comment dropped "Implementations MUST be safe for concurrent use." during this refactor instead of relocating it; `httpTagsFetcher` is used across concurrent planning-step invocations so the contract is worth restating on the interface.

### run 2 — discord-assistant#1 — .

**`.` (repo root)** — no `LICENSE*` file present in the repo.

### run 2 — discord-assistant#1 — scripts/supervise.sh:15

**`scripts/supervise.sh:15`** — `delay` never resets on sustained uptime; it only resets on a fresh `supervise.sh` invocation. A bot that runs stably for days but crashes twice a week keeps escalating toward `DELAY_MAX` indefinitely rather than backing off only for tight crash loops. Minor given the loop's stated "deliberately dumb" scope.

### run 2 — quant#109 — task/recurring-schedules/prod/plan-next-week.yaml:27

**`task/recurring-schedules/prod/plan-next-week.yaml:27-49`** — this file's diff mixes the `due_date` addition (matching the commit's stated scope) with an unrelated rewrite of the Success Criteria/Tasks/Definition-of-Done checklist text (Must/Should/Could → priority groups + explicit deferrals). Consider splitting content rewrites from mechanical field additions in future commits for easier review/revert.

### run 2 — vault-ui#39 — src/vault_ui/api/tasks.py:606

**`src/vault_ui/api/tasks.py:606`** — `compute_activity_date` runs inside `_task_to_response` for every task on every list call; when a task's transcript isn't in its direct `project_dir`, `transcript_mtime` falls back to `root.glob("*/{session}.jsonl")`, scanning all of `~/.claude/projects/` per task. On a frequently-polled board endpoint with many active sessions this is an O(tasks × projects) filesystem walk per request, not O(tasks). Worth caching the glob result per session_id per request, or building one root listing up front instead of re-globbing per task.

### run 2 — vault-ui#39 — src/vault_ui/activity.py:47

**`src/vault_ui/activity.py:47`** — `transcript_mtime`'s glob fallback silently returns the first match by filesystem iteration order if a session_id somehow collided across two project dirs (unlikely but unenforced); not worth guarding given session IDs are UUIDs, just noting it's implicit.

### run 2 — tts-mcp#13 — src/server.py:352

**`src/server.py:352`** — `instruct` isn't validated against the configured engine before the request is queued (unlike `voice`, which gets a synchronous 400), so a `voxtral`-engine request with `instruct` set returns 202 and only fails later, async, on the worker thread. Not a bug (the worker's `except (RuntimeError, ValueError)` paths correctly catch and record it as a failed status either way), just an inconsistency with the eager `voice` check just above it.

### run 3 — bw#41 — groups/meta/k3s.py:19

**`groups/meta/k3s.py:19-24`** — only IPv4 (`net.ipv4.neigh.default.gc_thresh*`) thresholds are raised; if any k3s node path uses IPv6 pod networking, the equivalent `net.ipv6.neigh.default.gc_thresh*` keys would still be at kernel defaults and could hit the same overflow. Worth confirming IPv6 is genuinely unused on these nodes, or add the IPv6 keys too.

### run 3 — distill#6 — hooks/deny-generated-file-edits.sh:38

**`hooks/deny-generated-file-edits.sh:38`** — `Source:` extraction (`\S+`) truncates at the first whitespace, so a source dir path containing a space would be cut short in the denial message. Low impact given the documented convention paths don't contain spaces.

### run 3 — discord-assistant#1 — src/index.js:264

**`src/index.js:264`** — new `RECOVERABLE_NET`/`connectedOnce` classification logic has no test coverage, unlike `config`/`health`/`llm` which are all unit-tested in this repo. Untestable in place since it's inline in the `uncaughtException` handler.

### run 3 — quant#109 — task/recurring-schedules/prod/check-ftmo-demo-accounts.yaml:65

**`task/recurring-schedules/prod/check-ftmo-demo-accounts.yaml:65`** — `due_date: "{{next_sun_date}}"` on a `weekday: Saturday` schedule, but sibling Saturday schedules in this same PR get `due_date: "{{current_date}}"` (e.g. `home-assistant-update-backup.yaml:68`, `opnsense-update.yaml:66`, `run-update-all-saturday.yaml:64`, `topic-backup-saturday.yaml:67`, `turn-on-hell.yaml:66`, `shutdown-k3s.yaml:64`) while others get `{{next_sun_date}}` (`lexoffice-invoices.yaml:65`, `moneymoney-review.yaml:65`, `plan-next-week.yaml:67`, `plan-weekend.yaml:65`, `renew-gmail-oauth-tokens.yaml:64`, `weekly-review.yaml:64`). No field in the diff (priority, category, task content) explains the split — e.g. two same-day "check X before Y" ops tasks (`run-update-all-saturday`, `topic-backup-saturday`) get same-day due dates while a same-shape check task (`check-ftmo-demo-accounts`) gets a next-day due date. If the intent is "ops tasks due same day, planning/review tasks due end-of-weekend," that rule isn't documented anywhere and isn't obviously followed (`renew-gmail-oauth-tokens` is a same-day token renewal, not a weekend-spanning planning task, yet gets `next_sun_date`). Worth a one-line comment in the PR description stating the criterion, or fixing the outliers.

### run 3 — vault-ui#39 — src/vault_ui/activity.py:76

**`src/vault_ui/activity.py:76-89`** — `transcript_mtime`'s glob fallback scans every directory under `~/.claude/projects` on every task/goal card render when the direct path misses; for vaults with many cards and many project dirs this adds O(n) stat calls per response. Consider caching the glob result per request or per session_id if response times become noticeable under load.

### run 4 — discord-assistant#5 — src/config.js:447

**`src/config.js:447-452`** — `config.isAddressed` compiles a fresh `RegExp` on every call inside `.some()`, once per candidate phrase. It's on a hot path (every `speech_started` event during a call). Not a correctness issue — only a minor allocation/perf cost — but worth hoisting to a module-level compiled regex like the Python side (`shim/claude_openai_shim.py:207`) does.

### run 4 — discord-assistant#1 — src/index.js:262

**`src/index.js:262-265`** — This adds a second `client.once('clientReady', ...)` listener purely to set `connectedOnce`, separate from the existing one at `src/index.js:75` that sets `gatewayReady`. Both fire on the same event; could be folded into the existing handler to keep gateway-state tracking in one place.

### run 4 — discord-assistant#1 — src/index.js:272

**`src/index.js:272`** — `RECOVERABLE_NET` matches on `err.message` globally via `uncaughtException`, so a coincidental `ECONNRESET`/`ETIMEDOUT` thrown from unrelated code (e.g. an LLM/endpoint HTTP call) would also be swallowed as a "gateway fault" once `connectedOnce` is true. Same pattern as the existing `RECOVERABLE` regex, so it's consistent with precedent — just worth knowing the scoping is by message text, not by source.

### run 4 — quant#109 — task/recurring-schedules/prod/plan-next-week.yaml:24

**`task/recurring-schedules/prod/plan-next-week.yaml:24-51`** — this file mixes the `due_date` addition (the stated PR theme) with an unrelated rewrite of the Success Criteria / Tasks / Definition of Done checklist (Must/Should/Could → priority groups + explicit deferrals + new `/plan-week` gate check). Consider splitting scope-unrelated content changes into a separate commit/PR for cleaner history, though not blocking.

### run 5 — node-skeleton#2 — src/config.ts:44

**`src/config.ts:44-54`** — `config.check()` replaces the old require-time `throw` in `config.js`, but no test exercises it (invalid `PORT` / `SHUTDOWN_TIMEOUT_MS` producing the expected problem strings). This is new validation logic, not a mechanical rename — it deserves direct test coverage rather than relying on `src/index.ts` wiring it in correctly.

### run 5 — tts-mcp#3 — skills/voice/SKILL.md:16

**`skills/voice/SKILL.md:16`** — "No selftest on activation" section header reads oddly as a heading (states what does *not* happen rather than what the section covers); consider "Startup behavior" or similar for scan-ability, though this is a minor style nit.

### run 5 — discord-assistant#1 — src/index.js:259

**`src/index.js:259-260`** — `RECOVERABLE_NET` matches on error message text alone, scoped only by `connectedOnce`, not by error source. `uncaughtException` is process-global, so if any other synchronous/EventEmitter-based path elsewhere in the process ever throws an uncaught error whose message happens to contain e.g. `ECONNRESET` or `ETIMEDOUT` (not necessarily the gateway), this handler will swallow it and incorrectly flip `gatewayReady = false` even though the actual Discord connection is healthy — masking an unrelated fault as a gateway outage and draining traffic unnecessarily.

### run 5 — discord-assistant#1 — README.md

**`README.md`** — no LICENSE file at repo root (pre-existing, not introduced by this diff — flagging since Step 3a checks for it).
