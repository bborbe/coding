# Documentation Guide

## 1. Overview of Documentation Structure

Each project uses three layers:

    README.md        → What it does, install, use (for humans on GitHub)
    CLAUDE.md        → How to change the code safely (for AI agents)
    docs/            → Detailed and in-depth documentation (for both)
    docs/adr/        → (Optional) Architecture Decision Records
    docs/prd/        → Product Requirement Definitions

### What Goes Where

| Content | README.md | CLAUDE.md | docs/ |
|---------|-----------|-----------|-------|
| What the project does | Yes | 1 line only | Overview |
| Install/usage | Yes | Never | - |
| Features/marketing | Yes | Never | - |
| Build/test commands | Brief | Detailed | - |
| Architecture | Never | Package map | Full detail |
| Design decisions | Never | Constraints list | ADRs |
| Env vars/config | User-facing | Agent-needs | Full reference |
| API docs | Brief | Never | Full detail |
| Workflow rules | Never | Yes | - |

### Detailed Guides

- **[readme-guide.md](readme-guide.md)** — How to write a good README.md (templates, sections, project types)
- **[claude-md-guide.md](claude-md-guide.md)** — How to write a good CLAUDE.md (architecture, constraints, build commands)

## 2. Internal vs Public Projects

**CRITICAL DISTINCTION**: README purpose differs based on audience and
project type.

### Project Types

**Internal Projects** (always multi-service):

-   Multi-service monorepos containing business logic\
-   Examples: ecommerce-platform, inventory-system, customer-portal\
-   Private repositories\
-   For internal team use only

**Public Projects** (always single-purpose libraries):

-   Single-purpose, reusable technical libraries\
-   Examples: `github.com/bborbe/errors`, `github.com/bborbe/metrics`,
    `github.com/bborbe/time`\
-   Published on GitHub\
-   For external developers to adopt

**Note**: Multi-service projects are **always internal**. You publish
technical libraries, not business logic.

### README Philosophy by Project Type

**Internal Projects** (multi-service):

-   **Very short** (50-100 lines)\
-   Minimal, practical reference for daily work\
-   Only what you need daily: how to run, quick commands, links to
    docs\
-   No "sales pitch" or detailed explanations\
-   Assumes reader already knows why the project exists

**Example**: "Here's how to run it, here's where the docs are, done."

**Public Projects** (libraries):

-   **Comprehensive** (200-400 lines)\
-   Marketing + documentation to attract users\
-   Convince users the library is useful and well-maintained\
-   Show features, benefits, examples\
-   Include badges (build status, coverage, version)\
-   Detailed quick start with copy-paste examples\
-   Comparison with alternatives

**Example**: "Here's why this is great, here's what it does, here's how
easy it is to use."

### Key Differences

  ---
  Aspect                     Internal Projects   Public Libraries
                             (Multi-Service)     (Single-Purpose)
  -------------------------- ------------------- -------------------------
  Project Type               Multi-service       Single-purpose library
                             monorepo

  Visibility                 Private             Public (GitHub)

  Content                    Business logic      Reusable technical
                                                 components

  Primary Goal               Quick reference     Attract users

  README Length              50-100 lines        200-400 lines

  Tone                       Terse, practical    Welcoming, explanatory

  Examples                   Minimal             Comprehensive

  Installation               Link to docs        Detailed steps

  Features List              Optional            Required

  Badges                     Rarely              Usually

  Screenshots/Demos          Rare                Common for some libs

  Comparison to Alternatives Never               Often helpful
  ---

---

## 3. What Goes in `README.md`

### For Internal Projects (Multi-Service)

Keep it **very short** (50-100 lines). Only daily essentials.

**Required sections**:

-   One-line purpose\
-   How to run locally\
-   Link to docs/

**Optional sections** (only if needed daily):

-   Common commands (build, test, deploy)\
-   Quick configuration reference

**Do NOT include**:

-   Full architecture\
-   Long explanations\
-   Detailed API docs\
-   Troubleshooting\
-   Historical notes\
-   Features list\
-   Installation instructions (link to docs instead)

**Template** (for individual services in monorepo):

```markdown
# [Service Name]

> Brief one-line description

Part of the [Project Name](../) monorepo.

## Running Locally

```bash
go run main.go
# or
make run
```

## Configuration

Key environment variables:
- `SERVICE_PORT` - HTTP port (default: 8080)
- `DATABASE_URL` - Database connection string

See [../docs/configuration.md](../docs/configuration.md) for full details.

## Documentation

- [Root project docs](../docs/)
- [Service-specific docs](./docs/) (if exists)
```

### For Public Projects (Libraries)

More comprehensive (200-400 lines). Convince users to adopt.

**Required sections**:

-   Brief description (one-liner or short paragraph)\
-   Features (with emojis for visual appeal)\
-   Installation (`go get`)\
-   Quick Start with copy-paste example\
-   Usage examples (Basic → Advanced)\
-   Testing section (make commands)\
-   Dependencies\
-   License

**Optional sections** (use when valuable):

-   Badges (GoDoc, Go Report Card - only if you maintain them)\
-   API Reference (inline for key functions)\
-   Advanced Features section\
-   Requirements (Go version)

**Do NOT include**:

-   Contributing guidelines (unnecessary for your libraries)\
-   Roadmap (adds maintenance burden)\
-   FAQ (wait until questions actually emerge)\
-   Comparison with alternatives (unless critical)\
-   Build status badges (unless CI is public and stable)

**Template** (based on your actual libraries):

```markdown
# [Library Name]

[![Go Reference](https://pkg.go.dev/badge/github.com/bborbe/[name].svg)](https://pkg.go.dev/github.com/bborbe/[name])
[![Go Report Card](https://goreportcard.com/badge/github.com/bborbe/[name])](https://goreportcard.com/report/github.com/bborbe/[name])

[One-sentence description, or 2-3 sentence paragraph explaining purpose and value]

## Features

- 🎯 **Feature 1** - Brief explanation
- 💉 **Feature 2** - Brief explanation
- 📅 **Feature 3** - Brief explanation
- ✅ **Feature 4** - Brief explanation

## Installation

```bash
go get github.com/bborbe/[name]
```

## Quick Start

```go
import "github.com/bborbe/[name]"

// Simple, copy-paste ready example showing core functionality
result := name.DoSomething()
```

## Usage

### Basic Usage

```go
// Show most common use case with clear example
```

### Advanced Usage

```go
// Show more complex scenarios if needed
```

## API Reference

[Optional: Include key functions inline with signatures and examples]

### FunctionName
```go
func FunctionName[T any](param T) T
```
Brief description and example.

[For simple libraries, you can skip this and just link to GoDoc]

Complete API documentation: [pkg.go.dev](https://pkg.go.dev/github.com/bborbe/[name])

## Testing

```bash
make test          # Run all tests with coverage
make precommit     # Format, test, lint, etc.
make generate      # Generate mocks using counterfeiter
```

## Dependencies

- `github.com/bborbe/errors` - Error handling
- `github.com/bborbe/run` - Application runner
[List only direct dependencies users should know about]

## Requirements

- Go 1.24+ or later

## License

BSD-style license. See [LICENSE](LICENSE) file for details.
```

**Examples from actual libraries**:

- **Minimal** (errors): Just title + description (4 lines)
- **Moderate** (metrics): ~70 lines with features + examples
- **Comprehensive** (time, collection, http): 200-320 lines with full examples and API reference

---

## 4. What Goes in `docs/` - Context Memory for AI Assistants

**CRITICAL PURPOSE**: `docs/` serves as **context memory** for AI
assistants (Claude Code, etc.) when resuming work after months.

**Goal**: Enable AI to quickly understand:

-   **Business context**: Why does this component exist? What problem
    does it solve?\
-   **Technical context**: How does it work? What patterns are used?\
-   **Current state**: What's implemented? What's planned? What
    decisions were made?\
-   **Operational context**: How to run, deploy, debug?

### Recommended Structure

    docs/
    ├── overview.md           → Business + technical overview
    ├── architecture.md       → Technical design and patterns
    ├── api.md                → API/interface documentation
    ├── configuration.md      → All configuration options
    ├── operations.md         → Running, deploying, monitoring
    ├── troubleshooting.md    → Common issues and solutions
    ├── development.md        → Development workflow and setup
    ├── prd/                  → Product requirements (features)
    │   ├── 2024-001-feature-name.md
    │   └── 2024-002-another-feature.md
    └── adr/                  → Architecture decisions
        ├── 0001-use-kafka-for-events.md
        └── 0002-postgresql-vs-scylladb.md

### 4.1 overview.md - The Starting Point

**Purpose**: First file AI reads to understand the component.

**Must answer**:

-   What is this component? (1-2 sentences)\
-   Why does it exist? What business problem does it solve?\
-   What are its responsibilities?\
-   What are its dependencies (upstream/downstream)?\
-   Where does it fit in the system?

**Template**:

```markdown
# [Component Name] Overview

## Purpose

[2-3 sentences explaining what this component does and why it exists]

## Business Context

- **Problem**: [What business problem does this solve?]
- **Solution**: [How does this component solve it?]
- **Value**: [Why is this important to the business?]

## Responsibilities

- Responsibility 1
- Responsibility 2
- Responsibility 3

## System Context

```
[Simple diagram showing where this component fits]
External API → This Service → Kafka → Downstream Services
```

## Key Dependencies

- **Upstream**: Services/APIs this component depends on
- **Downstream**: Services/APIs that depend on this component
- **Infrastructure**: Databases, message queues, etc.

## Current State

- **Status**: Production / Development / Deprecated
- **Maturity**: Stable / Active Development / Experimental
- **Last Major Update**: 2024-11-20

## Quick Links

- [Architecture](./architecture.md)
- [API Documentation](./api.md)
- [Operations Guide](./operations.md)
```

### 4.2 architecture.md - Technical Design

**Purpose**: Explain HOW the component works technically.

**Must include**:

-   High-level architecture diagram\
-   Key design patterns used\
-   Data flow (how data moves through the system)\
-   Internal components and their interactions\
-   Technology choices and why

**Template**:

```markdown
# Architecture

## Design Philosophy

[1-2 paragraphs explaining the design approach and principles]

## Component Architecture

```
[Diagram showing internal components]
HTTP Handler → Service Layer → Repository → Database
     ↓
  Kafka Producer
```

## Key Patterns

- **Pattern 1**: [e.g., Repository Pattern] - Used for data access abstraction
- **Pattern 2**: [e.g., Factory Pattern] - Used for creating complex objects
- **Pattern 3**: [e.g., Command Pattern] - Used for event processing

## Data Flow

### Request Flow
1. HTTP request arrives at handler
2. Handler validates input
3. Service layer processes business logic
4. Repository persists data
5. Event published to Kafka

### Event Processing Flow
[Explain how events are consumed and processed]

## Technology Stack

- **Language**: Go 1.24
- **Database**: PostgreSQL 15
- **Message Queue**: Kafka (Strimzi)
- **Metrics**: Prometheus
- **Logging**: Structured JSON logs

## Key Decisions

See [ADRs](./adr/) for detailed architectural decisions:
- [ADR-0001: Use Kafka for events](./adr/0001-kafka-events.md)
- [ADR-0002: PostgreSQL for state](./adr/0002-postgresql.md)
```

### 4.3 api.md - Interface Documentation

**Purpose**: Document all interfaces (HTTP, gRPC, Kafka topics).

**Must include**:

-   All endpoints/topics with examples\
-   Request/response schemas\
-   Validation rules\
-   Error responses

**Example**:

```markdown
# API Documentation

## HTTP Endpoints

### POST /api/orders

Create a new order.

**Request**:
```json
{
  "customer_id": "cust_123",
  "items": [
    {"product_id": "prod_456", "quantity": 2}
  ]
}
```

**Response** (201 Created):
```json
{
  "order_id": "ord_789",
  "status": "pending",
  "created_at": "2024-11-27T10:00:00Z"
}
```

**Errors**:
- 400: Invalid request (missing customer_id)
- 404: Customer not found
- 500: Internal server error

### GET /api/orders/:id

[Document other endpoints...]

## Kafka Topics

### Produces To

**Topic**: `orders.created`

**Schema**:
```json
{
  "order_id": "string",
  "customer_id": "string",
  "created_at": "timestamp"
}
```

### Consumes From

**Topic**: `payments.completed`

**Handling**: Updates order status to "paid"
```

### 4.4 configuration.md - All Configuration

**Purpose**: Document every environment variable and config option.

**Must include**:

-   All ENV vars with types and defaults\
-   Required vs optional\
-   Examples for different environments

**Example**:

```markdown
# Configuration

## Environment Variables

### Required

- `DATABASE_URL` (string) - PostgreSQL connection string
  - Example: `postgresql://user:pass@localhost:5432/dbname`
- `KAFKA_BROKERS` (string) - Comma-separated Kafka brokers
  - Example: `kafka-1:9092,kafka-2:9092`

### Optional

- `PORT` (int) - HTTP server port
  - Default: `8080`
- `LOG_LEVEL` (string) - Logging level
  - Default: `info`
  - Options: `debug`, `info`, `warn`, `error`
- `MAX_CONNECTIONS` (int) - Database connection pool size
  - Default: `10`

## Configuration Files

[If using config files, document structure here]

## Example Configurations

### Development
```bash
DATABASE_URL=postgresql://localhost:5432/dev
KAFKA_BROKERS=localhost:9092
LOG_LEVEL=debug
```

### Production
```bash
DATABASE_URL=postgresql://prod-db:5432/orders
KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
LOG_LEVEL=info
MAX_CONNECTIONS=50
```
```

### 4.5 operations.md - Running and Deploying

**Purpose**: How to operate this component in production.

**Must include**:

-   How to deploy\
-   How to monitor\
-   How to rollback\
-   Key metrics and alerts

**Example**:

```markdown
# Operations Guide

## Deployment

### Prerequisites
- Kubernetes cluster with access
- Database migrations applied
- Kafka topics created

### Deploy to Dev
```bash
make deploy-dev
# or
kubectl apply -f k8s/dev/
```

### Deploy to Production
```bash
# Check current version
kubectlprod get deployment order-service

# Deploy new version
make deploy-prod VERSION=v1.2.3

# Monitor rollout
kubectlprod rollout status deployment/order-service
```

## Monitoring

### Key Metrics
- `orders_created_total` - Total orders created
- `orders_failed_total` - Failed order creations
- `order_processing_duration_seconds` - Processing time

### Alerts
- **High Error Rate**: >5% errors in 5 minutes
- **High Latency**: p99 >1s for 5 minutes
- **Low Throughput**: <10 orders/minute

### Dashboards
- [Grafana: Order Service Overview](https://grafana.example.com/d/orders)

## Rollback

```bash
# Rollback to previous version
kubectlprod rollout undo deployment/order-service

# Rollback to specific version
kubectlprod rollout undo deployment/order-service --to-revision=5
```

## Health Checks

- `/healthz` - Liveness probe (always returns 200)
- `/readyz` - Readiness probe (checks DB + Kafka connectivity)
```

### 4.6 troubleshooting.md - Common Issues

**Purpose**: Known issues and how to fix them.

**Must include**:

-   Common errors with solutions\
-   Debug procedures\
-   FAQ

**Example**:

```markdown
# Troubleshooting

## Common Issues

### Database Connection Timeout

**Symptom**: `pq: connection timeout` errors in logs

**Cause**: Database connection pool exhausted

**Solution**:
1. Check current connections: `SELECT count(*) FROM pg_stat_activity;`
2. Increase `MAX_CONNECTIONS` environment variable
3. Check for connection leaks in code

### Kafka Consumer Lag

**Symptom**: Consumer lag increasing, events not processed

**Cause**: Processing too slow or consumer crashed

**Solution**:
1. Check consumer group lag: `kafka-consumer-groups --describe --group order-service`
2. Scale up consumer replicas
3. Check for errors in processing logic

## Debug Procedures

### Enable Debug Logging
```bash
# Temporarily enable debug logging
kubectlprod set env deployment/order-service LOG_LEVEL=debug

# Remember to revert after debugging
kubectlprod set env deployment/order-service LOG_LEVEL=info
```

### Access Logs
```bash
# View recent logs
kubectlprod logs deployment/order-service --tail=100

# Follow logs in real-time
kubectlprod logs deployment/order-service -f

# Filter for errors
kubectlprod logs deployment/order-service | grep ERROR
```
```

### 4.7 development.md - Development Workflow

**Purpose**: How to work on this component locally.

**Must include**:

-   Local setup steps\
-   How to run tests\
-   Development workflow\
-   Code organization

**Example**:

```markdown
# Development Guide

## Local Setup

### Prerequisites
- Go 1.24+
- Docker and Docker Compose
- Make

### Setup
```bash
# Clone and install dependencies
git clone [repo]
cd order-service
go mod download

# Start dependencies (DB, Kafka)
docker-compose up -d

# Run migrations
make migrate

# Run service
make run
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run integration tests
make test-integration
```

## Code Organization

```
order-service/
├── cmd/            - Main application entry
├── internal/       - Private application code
│   ├── handler/   - HTTP handlers
│   ├── service/   - Business logic
│   ├── repository/- Data access
│   └── model/     - Domain models
├── pkg/           - Public libraries
└── docs/          - Documentation
```

## Development Workflow

1. Create feature branch from `master`
2. Make changes and write tests
3. Run `make precommit` (format, test, lint)
4. Commit and push
5. Create pull request
```

---

## 5. Product Requirement Definitions (PRDs)

**Purpose**: Document features BEFORE implementation to provide context for AI assistants.

**Full documentation**: See [prd-guide.md](prd-guide.md) for complete PRD templates, examples, and best practices.

**Key points**:
- **Stored in**: `docs/prd/`
- **Naming**: `YYYY-NNN-feature-name.md` (e.g., `2024-001-order-cancellation.md`)
- **When to create**: Feature requires >1 day of work, multiple approaches possible, affects multiple components
- **Status tracking**: Draft → In Progress → Implemented → Deprecated

**PRD Workflow**: For AI-assisted PRD creation and implementation workflow, see project-local PRD workflow guide.

For complete template with all sections, examples, and detailed guidance, see [prd-guide.md](prd-guide.md).

---

## 6. Architecture Decision Records (ADRs)

**Purpose**: Document important architectural decisions and their rationale for future reference.

**Full documentation**: See [adr-guide.md](adr-guide.md) for complete ADR templates, examples, and best practices.

**Key points**:
- **Stored in**: `docs/adr/` (root-level) or `service-name/docs/adr/` (service-specific)
- **Naming**: `NNNN-decision-title.md` (e.g., `0001-use-kafka-for-events.md`)
- **When to create**: Technology choices, architectural patterns, decisions affecting multiple components, expensive-to-reverse decisions
- **Status tracking**: Proposed → Accepted → Deprecated/Superseded

**Organization**:
- **Root-level ADRs** (`docs/adr/`): Project-wide decisions affecting multiple services
- **Service-level ADRs** (`service-name/docs/adr/`): Service-specific architectural decisions

For complete template, examples, organization guidance, and best practices, see [adr-guide.md](adr-guide.md).

---

## 7. When to Add Documentation

Add docs when: - A change affects users or APIs\
- Multiple people work on the feature\
- It's larger than 1--2 tickets\
- A decision has long-term impact\
- A problem might repeat

---

## 8. Writing for AI Context Resumption

**Critical Principle**: Write documentation so an AI assistant (Claude
Code, etc.) can understand the project state after months of absence.

### What AI Assistants Need

**Business Context**:

-   WHY does this exist?\
-   What problem are we solving?\
-   Who are the users?\
-   What's the business value?

**Technical Context**:

-   HOW does it work?\
-   What patterns are used?\
-   What technologies are involved?\
-   How do components interact?

**Current State**:

-   What's implemented vs planned?\
-   What decisions were made?\
-   What's working vs broken?\
-   What are known limitations?

**Operational Context**:

-   How to run locally?\
-   How to deploy?\
-   How to debug?\
-   What's being monitored?

### Writing Best Practices

**Assume Zero Prior Knowledge**:

```markdown
❌ Bad: "Use the standard deployment process"
✓ Good: "Deploy using `make deploy-prod`, which builds the Docker image,
pushes to GCR, and applies Kubernetes manifests"

❌ Bad: "Configure the usual environment variables"
✓ Good: "Required environment variables: DATABASE_URL (PostgreSQL
connection), KAFKA_BROKERS (comma-separated list)"
```

**Explain WHY, Not Just WHAT**:

```markdown
❌ Bad: "We use PostgreSQL for storage"
✓ Good: "We use PostgreSQL for storage because we need ACID transactions
for order processing and strong consistency guarantees"
```

**Include Diagrams for System Understanding**:

```markdown
✓ Good:
```text
User Request → API Gateway → Order Service → PostgreSQL
                                   ↓
                              Kafka (orders.created)
                                   ↓
                            Notification Service
```
```

**Document Current State**:

```markdown
✓ Good:
## Current State (2024-11-27)

**Implemented**:
- Order creation and retrieval
- Payment processing integration
- Email notifications

**In Progress**:
- Order cancellation (see PRD-2024-003)
- Refund processing

**Known Issues**:
- High latency on order search (>2s) - investigating database indexes
- Occasional Kafka consumer lag during peak hours

**Planned**:
- Partial cancellations (Q1 2025)
- Subscription orders (Q2 2025)
```

**Keep Documentation Updated**:

```markdown
✓ Good: Add update log to long-lived docs

## Updates Log
- 2024-11-27: Added cancellation endpoint documentation
- 2024-10-15: Updated deployment process for new Kubernetes cluster
- 2024-09-01: Initial version
```

**Link Related Documentation**:

```markdown
✓ Good:
This order cancellation feature (PRD-2024-003) requires:
- [Payment refund integration](./integration/payment-service.md)
- [Kafka event schema update](../adr/0015-order-event-schema.md)
- [Database migration](./operations.md#migrations)
```

---

## 9. Style Rules

### Do:

-   Keep files focused\
-   Use examples\
-   Link between docs (use relative links)\
-   Use diagrams when helpful\
-   Keep docs up-to-date (remove outdated content)\
-   Version diagrams with dates or git commits\
-   **Write for AI assistants**: Assume reader has no prior knowledge\
-   **Explain WHY**: Not just what was done, but why it was done that
    way\
-   **Document current state**: What works, what's broken, what's
    planned

### Don't:

-   Duplicate content\
-   Write unnecessarily long text\
-   Document obvious code patterns (let GoDoc handle that)\
-   Create extensive docs for every tiny component\
-   **Assume prior knowledge**: AI has no memory of previous work\
-   **Skip business context**: Technical details without business
    reasoning\
-   **Leave docs stale**: Outdated docs are worse than no docs

---

## 10. Multi-Service Projects / Monorepos

For projects containing multiple services (like `ecommerce-platform`, `inventory-system`):

### Repository Root Structure

    README.md           → High-level overview of entire project
    docs/               → Project-wide documentation
    ├── architecture.md → Overall system architecture
    ├── development.md  → Development workflows, tooling
    ├── deployment.md   → Project-wide deployment procedures
    ├── adr/           → Cross-service architectural decisions
    └── prd/           → Project-wide features
    <service-a>/
    ├── README.md      → Service-specific quickstart
    ├── docs/          → Service-specific docs (optional)
    <service-b>/
    ├── README.md      → Service-specific quickstart
    └── docs/          → Service-specific docs (optional)

### Root README.md

The root README provides project-wide orientation.

Multi-service projects are **always internal**, so keep it minimal
(50-100 lines).

**Required**:

-   Brief project purpose\
-   List of key services (or link to service list)\
-   Essential daily commands\
-   Link to docs/

**Template**:

```markdown
# [Project Name]

> Brief one-line description

[Optional: One paragraph context if needed]

## Services

See [docs/services.md](./docs/services.md) for full service list.

Key services:
- [service-name](./service-name/) - Brief description
- [service-name](./service-name/) - Brief description
- [service-name](./service-name/) - Brief description

## Quick Commands

```bash
# Run all tests
make test

# Update all dependencies
make gomodupdate

# Precommit checks
make precommit

# Deploy to dev
make deploy-dev

# Deploy to prod
make deploy-prod
```

## Documentation

See [docs/](./docs/) for detailed documentation:

- [Architecture](./docs/architecture.md)
- [Development Guide](./docs/development.md)
- [Deployment](./docs/deployment.md)
```

### Root docs/

Project-wide documentation that affects multiple services.

-   Cross-service architecture diagrams\
-   Shared infrastructure (Kafka, databases, monitoring)\
-   Development workflows (commit process, testing, CI/CD)\
-   Deployment procedures affecting multiple services\
-   Common patterns used across services

### Service-Level README.md

**Each service MUST have its own README.md** following the standard structure (Section 2).

-   Overview of the specific service\
-   How to run this service locally\
-   Service-specific configuration\
-   Link to root docs/ for shared infrastructure

### Service-Level docs/

**IMPORTANT**: Most services should have their own `docs/` folder for
AI context.

**Purpose**: Provide comprehensive context about THIS specific service
for AI assistants.

**When to create** (generally always for non-trivial services):

-   Service has unique business logic\
-   Service has its own API or interfaces\
-   Service has specific operational concerns\
-   **AI needs context to work on this service**

**Recommended structure** (use Section 4 templates):

``` markdown
service-name/
├── README.md              → Minimal quickstart (50-100 lines)
└── docs/
    ├── overview.md        → Business + technical overview
    ├── architecture.md    → How this service works
    ├── api.md             → Service-specific API/interfaces
    ├── configuration.md   → Environment variables
    ├── operations.md      → Deploy, monitor, troubleshoot
    ├── prd/              → Service-specific features
    └── adr/              → Service-specific decisions
```

**Key principle**: README stays minimal, `docs/` contains all the
context AI needs.

### When to Document at Root vs Service Level

  ---
  Root docs/                    Service docs/
  ----------------------------- ------------------------------------------
  Cross-service data flow       Service-specific API endpoints

  Shared Kafka topics           Service-unique business logic

  Common deployment process     Service-specific troubleshooting

  Shared monitoring setup       Service-unique configuration

  Project-wide ADRs             Service-specific decisions
  ---

---

## Summary Table

  ---
  File / Folder             Purpose
  ------------------------- ----------------------------------------------
  README.md                 Quickstart + high-level overview

  docs/                     Detailed technical documentation

  docs/prd/                 Product Requirement Definitions

  docs/adr/                 Long-term architectural decisions

  docs/api.md               Full interface and endpoint documentation

  docs/architecture.md      Internal design and system structure

  docs/configuration.md     Full configuration reference

  docs/operations.md        Deployment and operations

  docs/troubleshooting.md   Known issues and fixes
  ---
