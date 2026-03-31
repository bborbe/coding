# Architecture Decision Records (ADR) Guide

## Overview

Architecture Decision Records (ADRs) document important architectural decisions and their rationale for future reference. They serve as a historical record explaining WHY certain technical choices were made, helping future developers (and AI assistants) understand the context behind architectural patterns.

## Purpose

ADRs provide:
- **Historical context** for architectural decisions
- **Rationale** explaining why certain choices were made over alternatives
- **Consequences** documenting trade-offs and impacts
- **Reference** for future similar decisions

**Critical for AI assistants:** ADRs enable AI to understand not just WHAT the architecture is, but WHY it is that way, preventing inappropriate suggestions that conflict with documented decisions.

## When to Create an ADR

Create an ADR when:
- Making a **technology choice** (database, message queue, framework)
- Deciding on an **architectural pattern**
- Making decisions that **affect multiple components**
- Making decisions that are **expensive to reverse**
- The team **debated multiple approaches**
- The decision has **long-term consequences**

**Don't create ADRs for:**
- Minor implementation details
- Decisions that are easily reversible
- Obvious technology choices with no alternatives
- Tactical decisions affecting only one component

## Storage and Naming

**Location:** `docs/adr/` (or `service-name/docs/adr/` for service-specific decisions)

**Naming:** `NNNN-decision-title.md`

**Examples:**
- `0001-use-kafka-for-events.md`
- `0002-postgresql-vs-scylladb.md`
- `0003-blue-green-deployments.md`

**Numbering:**
- Start at 0001 and increment
- Never reuse numbers
- Gaps are OK (if you delete a draft ADR)
- Each ADR folder has independent numbering

## ADR Template

```markdown
# ADR-NNNN: [Decision Title]

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
**Date**: 2024-11-27
**Deciders**: [Names or team]

## Context

[Describe the technical context and the problem that needs a decision.
What forces are at play? What are the constraints?]

### Background
[Additional context about why this decision is needed now]

### Constraints
- Constraint 1: [e.g., Must work with existing PostgreSQL]
- Constraint 2: [e.g., Budget limit of $X/month]
- Constraint 3: [e.g., Must support 10,000 req/sec]

## Decision

We will [decision in one clear sentence].

### Reasoning
[Explain WHY this decision was made. This is the most important part.]

## Considered Options

### Option 1: [Name]
**Pros**:
- Pro 1
- Pro 2

**Cons**:
- Con 1
- Con 2

**Why Not Chosen**: [Brief explanation]

### Option 2: [Name]
**Pros**:
- Pro 1
- Pro 2

**Cons**:
- Con 1
- Con 2

**Why Not Chosen**: [Brief explanation]

### Option 3: [Chosen Option Name] ✓
**Pros**:
- Pro 1
- Pro 2
- Pro 3

**Cons**:
- Con 1
- Con 2

**Why Chosen**: [Detailed explanation of why this was selected]

## Consequences

### Positive
- Positive consequence 1
- Positive consequence 2

### Negative
- Negative consequence 1 (and how we'll mitigate)
- Negative consequence 2 (and how we'll mitigate)

### Neutral
- Neutral impact 1
- Neutral impact 2

## Implementation Notes

[Any specific notes about implementing this decision]

### Migration Path
[If replacing something, how do we migrate?]

### Timeline
[When will this be implemented?]

## Related Decisions

- [ADR-0002: Related decision](./0002-related-decision.md)
- [PRD: Feature X](../prd/2024-001-feature-x.md)

## References

- [Link to relevant documentation]
- [Link to research or benchmarks]
- [Link to discussion/meeting notes]
```

## Complete Example

```markdown
# ADR-0001: Use Kafka for Event Streaming

**Status**: Accepted
**Date**: 2024-01-15
**Deciders**: Engineering Team

## Context

We need an event streaming platform to enable asynchronous communication
between microservices. Currently, services communicate only via
synchronous HTTP calls, which creates tight coupling and makes the
system brittle.

### Background
- System has grown to 15+ microservices
- Synchronous calls create cascading failures
- Need to support event-driven patterns
- Must handle 50,000 events/second

### Constraints
- Must run in Kubernetes
- Budget: <$500/month for infrastructure
- Team familiar with message queues but not Kafka

## Decision

We will use Apache Kafka (via Strimzi operator) as our event streaming
platform.

### Reasoning
Kafka provides exactly-once semantics, high throughput, and persistent
event log that matches our event sourcing needs. Strimzi makes it
Kubernetes-native.

## Considered Options

### Option 1: RabbitMQ
**Pros**:
- Team has experience with it
- Simple setup
- Good documentation

**Cons**:
- Not designed for event streaming
- Limited retention (messages deleted after consumption)
- Lower throughput than Kafka

**Why Not Chosen**: Doesn't support event sourcing pattern we need

### Option 2: AWS Kinesis
**Pros**:
- Fully managed
- No operational overhead
- Good AWS integration

**Cons**:
- Vendor lock-in
- Expensive at our scale ($800/month projected)
- Can't run locally for development

**Why Not Chosen**: Cost and vendor lock-in concerns

### Option 3: Kafka + Strimzi ✓
**Pros**:
- Industry standard for event streaming
- Persistent event log (supports replay)
- High throughput (millions of msgs/sec)
- Strimzi provides Kubernetes-native operations
- Can run locally in Docker

**Cons**:
- Steeper learning curve
- More operational complexity
- Requires careful partition management

**Why Chosen**: Best fit for our event sourcing needs, scales to our
requirements, and Strimzi makes Kubernetes deployment manageable.

## Consequences

### Positive
- Services become more loosely coupled
- Can replay events for debugging
- Supports event sourcing and CQRS patterns
- High throughput enables real-time processing

### Negative
- Team needs Kafka training (2-week sprint allocated)
- More moving parts to monitor
- Partition management requires careful planning

### Neutral
- Need to establish Kafka topic naming conventions
- Will need Kafka monitoring dashboards

## Implementation Notes

### Migration Path
1. Deploy Strimzi operator to Kubernetes
2. Create test Kafka cluster in dev
3. Migrate one service pair as pilot (orders → notifications)
4. Roll out to remaining services over 2 months

### Timeline
- Month 1: Setup + pilot migration
- Month 2-3: Full rollout

## Related Decisions
- ADR-0002: Event schema versioning with Avro
- PRD-2024-001: Event-driven order processing

## References
- [Kafka vs RabbitMQ Benchmark](https://example.com/benchmark)
- [Strimzi Documentation](https://strimzi.io)
- Team decision meeting notes: 2024-01-10
```

## Status Management

**Status values:**
- **Proposed**: Draft, under discussion
- **Accepted**: Decision made, being implemented
- **Deprecated**: No longer relevant
- **Superseded**: Replaced by newer ADR (link to it)

**When to update status:**
- Start as "Proposed" during discussion
- Move to "Accepted" when decision is final
- Mark "Deprecated" if no longer applicable
- Mark "Superseded by ADR-XXXX" if replaced

**Important:** Don't edit historical ADRs when decisions change. Instead, create a new ADR and mark the old one as "Superseded". ADRs are historical records.

## ADR Organization: Root vs Service Level

### Root-Level ADRs (`docs/adr/`)

**Use for:** Project-wide architectural decisions affecting multiple services.

**Examples:**
- Technology choices (Kafka, PostgreSQL, Kubernetes)
- Cross-service patterns (event schema format, API versioning)
- Infrastructure decisions (monitoring stack, deployment strategy)
- Shared libraries and frameworks

**Why root level:** AI assistant needs to understand project-wide context when working on any service.

### Service-Level ADRs (`service-name/docs/adr/`)

**Use for:** Service-specific architectural decisions.

**Examples:**
- Service-specific data model design
- Internal service patterns (caching strategy, state management)
- Service-specific library choices
- Algorithm choices unique to this service

**Why service level:** Decision only matters when working on THIS specific service.

### Decision Matrix

| Decision Type | Location | Example |
|--------------|----------|---------|
| Message queue technology | Root `docs/adr/` | ADR-0001: Use Kafka |
| Event schema format | Root `docs/adr/` | ADR-0002: Use Avro for events |
| Deployment strategy | Root `docs/adr/` | ADR-0003: Blue-green deployments |
| Order service caching | Service `docs/adr/` | order-service/docs/adr/0001-redis-cache |
| Payment retry algorithm | Service `docs/adr/` | payment-service/docs/adr/0001-exponential-backoff |
| Database choice (affects multiple) | Root `docs/adr/` | ADR-0004: PostgreSQL for OLTP |

### Numbering Strategy

**Root ADRs:** Sequential across entire project (0001, 0002, 0003, ...)

**Service ADRs:** Sequential within each service (each service starts at 0001)

**Example structure:**
```
docs/adr/
├── 0001-use-kafka.md
├── 0002-use-avro.md
└── 0003-postgres-for-oltp.md

order-service/docs/adr/
├── 0001-redis-caching.md
└── 0002-optimistic-locking.md

payment-service/docs/adr/
├── 0001-exponential-backoff.md
└── 0002-idempotency-keys.md
```

### Cross-Referencing

Always link between root and service ADRs:

```markdown
# order-service/docs/adr/0001-redis-caching.md

## Related Decisions
- [Root ADR-0001: Use Kafka](../../../docs/adr/0001-use-kafka.md) -
  Events invalidate cache
- [Root ADR-0004: PostgreSQL](../../../docs/adr/0004-postgres.md) -
  Cache sits in front of DB
```

## Best Practices

### For AI Context

**Write assuming the reader wasn't in the decision meeting:**
- Explain WHY, not just WHAT was decided
- Include the options you DIDN'T choose and why
- Provide business context, not just technical details
- Link to related PRDs and ADRs

**Example:**

❌ Bad: "We chose PostgreSQL"

✓ Good: "We chose PostgreSQL over MongoDB because we need ACID transactions for financial data, strong consistency guarantees, and our team has 5 years of PostgreSQL operations experience. While MongoDB offered better horizontal scaling, the consistency requirements were non-negotiable."

### Content Quality

**Critical sections:**
1. **Context** - Explain the problem and constraints clearly
2. **Reasoning** - This is the most important part - explain WHY
3. **Considered Options** - Show alternatives and why they weren't chosen
4. **Consequences** - Be honest about trade-offs

**What to include:**
- Business context (why does this matter?)
- Technical constraints (what limits our choices?)
- Team considerations (expertise, learning curve)
- Cost implications
- Performance requirements
- Security considerations

**What to avoid:**
- Assuming prior knowledge
- Only documenting what you chose (not why)
- Skipping the alternatives you considered
- Hiding negative consequences
- Using jargon without explanation

### Maintenance

**When decisions change:**
- Create NEW ADR
- Mark old ADR as "Superseded by ADR-XXXX"
- Don't edit historical ADRs

**Why:** ADRs are historical records. Future developers need to understand what was decided when, and why things changed.

**Example:**
```markdown
# ADR-0001: Use MySQL for Primary Database

**Status**: Superseded by ADR-0015
**Date**: 2023-01-15
...
```

## Writing Tips

**Start with the decision:**
- Don't bury the decision at the end
- State it clearly in the "Decision" section
- Then explain the reasoning

**Be specific:**
- "We chose PostgreSQL 15" not "We chose a database"
- "Must handle 10,000 requests/second" not "Must be fast"
- "Budget limit of $500/month" not "Must be cheap"

**Include data:**
- Benchmark results
- Cost calculations
- Performance measurements
- Team expertise assessment

**Link everything:**
- Related ADRs
- PRD documents
- External references
- Meeting notes
- Research documents

## Common Mistakes to Avoid

**1. Not documenting alternatives:**
- ADR should show what you DIDN'T choose and why
- This prevents future developers from suggesting the same rejected options

**2. Skipping the "why":**
- Don't just document what you chose
- Explain the reasoning and trade-offs

**3. Writing too late:**
- Document WHEN decision is made, not months later
- Fresh context produces better documentation

**4. Editing historical ADRs:**
- Don't change past decisions
- Create new ADR and mark old as superseded

**5. Too much detail:**
- ADR is not implementation documentation
- Focus on the decision, not the implementation

**6. No consequences:**
- Every decision has trade-offs
- Document negative consequences honestly

## Related Documentation

- For PRD documentation: See [prd-guide.md](prd-guide.md)
- For overall documentation structure: See [documentation-guide.md](documentation-guide.md)
- For PRD workflow with AI: See `~/.claude/docs/prd-workflow-guide.md` (global guide)
