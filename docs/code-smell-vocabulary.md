# Code Smell Vocabulary

Twelve named code smells from Martin Fowler's *Refactoring*, as one-line definitions. Language-agnostic — Go, Python, Node, and any other language reviewed by this plugin share these definitions.

## Why a vocabulary instead of instructions

A named smell is denser than the paragraph that describes it. "Check for shotgun surgery" and "check whether changing one requirement would force edits in several files, which risks missing one and creating inconsistency" instruct the same check — but the first is a term with an established meaning, and the second is prose a reviewer has to parse.

For review agents this matters twice over: extra words are distractions that invite hallucination, and a shared term means a finding is reviewable ("that's feature envy") instead of arguable.

**Use the term. Do not restate the definition inline.** If a review report needs to explain a smell, link here.

## The twelve

| Term | Definition |
|---|---|
| **Shotgun surgery** | One change forces edits in many places; miss one and behavior goes inconsistent. |
| **Divergent change** | One module changes for many unrelated reasons — the inverse of shotgun surgery. |
| **Feature envy** | Logic lives in a module other than the one owning the data it works on. |
| **Data clumps** | The same group of values travels together through many signatures without being a type. |
| **Long method** | A unit doing too much to hold in one reading. |
| **Large class** | A type accreting responsibilities that change for unrelated reasons. |
| **Long parameter list** | Callers must assemble many positional arguments, inviting silent order drift. |
| **Primitive obsession** | Domain concepts encoded as bare strings, ints, or maps instead of named types. |
| **Duplicated code** | The same logic maintained in more than one place. |
| **Message chains** | A caller navigates `a.b().c().d()`, coupling it to structure it should not know. |
| **Dead code** | Nothing depends on it; deleting it changes no observable behavior. |
| **Speculative generality** | An abstraction built for a use case that never arrived. |

## Which layer catches which

Naming all twelve does not mean all twelve are worth an agent's judgment — several are already caught mechanically, and re-checking them by hand produces noise.

| Layer | Smells | Why |
|---|---|---|
| **Mechanical** (linters: `funlen`, `dupl`, `gocyclo`, `vulture`, `ts-prune`) | Long method, Large class, Long parameter list, Duplicated code, Dead code | Threshold- or reachability-detectable. Cheaper and more consistent than judgment. |
| **Judgment** (architecture assistants) | Shotgun surgery, Divergent change, Feature envy, Primitive obsession, Message chains, Data clumps, Speculative generality | Require knowing what the code *means* — no threshold separates a good abstraction from a speculative one. |

A judgment-tier finding still needs a `file:line` citation and a named structural fix, not "consider refactoring".

## Structural vs behavioral ownership

These smells are **structural** — they describe how code is organized. They belong to the structural review pass:

- `go-architecture-assistant` — see [go-architecture-patterns.md](go-architecture-patterns.md)
- `python-architecture-assistant` — see [python-architecture-patterns.md](python-architecture-patterns.md)
- `node-quality-assistant` — see [node-service-guide.md](node-service-guide.md)

The **behavioral** pass ([architecture-dimensions-guide.md](architecture-dimensions-guide.md)) covers data flow, failure paths, concurrency, observability, and drift. Three of these terms also work as evolvability probes there — shotgun surgery, divergent change, and speculative generality all answer "what would the next feature cost?" — and §7 of that guide uses them in that role. That is the only overlap; the other nine stay structural.

## Antipatterns

| ❌ | ✅ |
|---|---|
| Copying these definitions into a language-specific guide | Linking here; language guides carry only the language-specific fix |
| Inventing house terms ("widget drift") | Using established vocabulary the model already knows |
| Reporting a mechanical-tier smell as an architectural finding | Letting the linter own it; report only judgment-tier smells |
| "This has feature envy" with no location | `pkg/order/service.go:88 — feature envy: inventory math on an order type` |
| Naming a smell as the whole finding | Naming the smell, the site, and the structural fix |

## Related

- [architecture-dimensions-guide.md](architecture-dimensions-guide.md) — behavioral pass; §7 uses three of these as evolvability probes
- [go-architecture-patterns.md](go-architecture-patterns.md) — Go structural patterns
- [python-architecture-patterns.md](python-architecture-patterns.md) — Python structural patterns
- [node-service-guide.md](node-service-guide.md) — Node service structure
