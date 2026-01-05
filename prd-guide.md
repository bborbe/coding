# Product Requirements Document (PRD) Guide

## Overview

A Product Requirements Document (PRD) defines what needs to be built and why, BEFORE implementation begins. PRDs serve as a reference for developers and AI assistants, providing essential business and technical context for features.

## Purpose

PRDs provide:
- **Business context** - Why this feature exists and what problem it solves
- **Requirements** - What the feature must do (functional and non-functional)
- **Scope definition** - What's included and explicitly what's NOT included
- **Success criteria** - How to measure if the feature succeeds
- **Implementation guidance** - Technical approach and design considerations

**Critical for AI assistants:** PRDs enable AI to understand the feature's purpose, constraints, and acceptance criteria, preventing misaligned implementations.

## When to Create a PRD

Create a PRD when:
- Feature requires **>1 day of work**
- **Multiple implementation approaches** are possible
- **Business context** needs to be preserved for future reference
- Feature **affects multiple components**
- You need to **align with stakeholders** before implementation
- The feature has **complex requirements** or edge cases

**Don't create PRDs for:**
- Simple bug fixes
- Trivial features (<1 day)
- Internal refactoring with no external impact
- Obvious enhancements with single approach

## Storage and Naming

**Location:** `tasks/` or `docs/prd/` (project-specific)

### Naming Conventions

**Private repositories:** `feature-name.md` (lowercase with hyphens)

**Examples:**
- `order-cancellation.md`
- `user-authentication.md`
- `payment-refunds.md`
- `fix-authentication-timeout.md`

**Public repositories:** `YYYY-MM-DD-feature-name.md` (date prefix for chronological ordering)

**Examples:**
- `2025-12-05-json-error-handler.md`
- `2025-12-06-request-id-middleware.md`
- `2026-01-10-async-context-refactor.md`

**Why date prefix for public repos:**
- Chronological ordering (GitHub sorts alphabetically)
- No coordination overhead (multiple contributors can create PRDs simultaneously)
- Timeline clarity (immediately shows when decision was proposed)
- Avoids naming collisions
- Matches industry patterns (Go proposals, Kubernetes KEPs, Python PEPs)

**Naming Guidelines:**
- Use lowercase with hyphens (kebab-case)
- Describe what the feature does or what needs to be fixed
- No prefixes like "PRD-" or "BUG-" (folder context makes this clear)
- Action-oriented for tasks (e.g., "fix-auth-bug" not "auth-bug")
- Keep names concise but descriptive
- **Never change filename** - status lives in frontmatter, not filename (keeps links stable)

## PRD Template

```markdown
---
id: YYYY-MM-DD-feature-name
title: Feature Name
status: Draft
created: 2024-11-27
authors: ["@username"]
tags: [prd]
related_issues: []
implemented_pr: ""
superseded_by: ""
---

# PRD: [Feature Name]

**Status**: Draft
**Author**: [Your Name]
**Created**: 2024-11-27
**Updated**: 2024-11-27

## Summary

[2-3 sentences describing what this feature is and why we're building it]

## Background & Motivation

### Problem
[What problem are we solving? What's broken or missing?]

### Why Now?
[Why is this important now? What's the business driver?]

### Current State
[How do things work today without this feature?]

## Goals and Non-Goals

### Goals
- Goal 1: [What we want to achieve]
- Goal 2: [Specific, measurable outcome]
- Goal 3: [Business or technical objective]

### Non-Goals
- [Explicitly state what we're NOT doing]
- [Helps prevent scope creep]

## Requirements

### Functional Requirements
1. **Requirement 1**: [Specific behavior the system must have]
2. **Requirement 2**: [Another specific behavior]
3. **Requirement 3**: [Another specific behavior]

### Non-Functional Requirements
- **Performance**: [Response time, throughput requirements]
- **Scalability**: [Load expectations]
- **Reliability**: [Uptime, error rate expectations]
- **Security**: [Authentication, authorization requirements]

## User Stories

**As a** [user type]
**I want** [action]
**So that** [benefit]

**Acceptance Criteria**:
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## API Impact

### New Endpoints
```
POST /api/v1/orders/:id/cancel
```

**Request**:
```json
{
  "reason": "customer_request",
  "notes": "Optional cancellation notes"
}
```

**Response**:
```json
{
  "order_id": "ord_123",
  "status": "cancelled",
  "cancelled_at": "2024-11-27T10:00:00Z"
}
```

### Modified Endpoints
[List any existing endpoints that will change]

### Kafka Topics
- **Produces**: `orders.cancelled` - Event when order is cancelled
- **Consumes**: [Any new topics this feature consumes]

## Technical Design

### Architecture
[High-level technical approach - components affected, data flow]

### Data Model Changes
```sql
ALTER TABLE orders ADD COLUMN cancelled_at TIMESTAMP;
ALTER TABLE orders ADD COLUMN cancellation_reason VARCHAR(255);
```

### Key Design Decisions
1. **Decision 1**: [What and why]
2. **Decision 2**: [What and why]

(For major decisions, create separate ADRs)

## Edge Cases & Error Handling

### Edge Cases
1. **Already cancelled order**: Return 409 Conflict
2. **Order already shipped**: Return 400 Bad Request with clear message
3. **Concurrent cancellation**: Use optimistic locking to prevent

### Error Responses
- 400: Invalid request (order in wrong state)
- 404: Order not found
- 409: Order already cancelled

## Implementation Plan

### Phase 1: Core Functionality (Week 1)
- [ ] Add database columns
- [ ] Implement cancellation logic
- [ ] Add API endpoint
- [ ] Write unit tests

### Phase 2: Integration (Week 2)
- [ ] Integrate with payment refund service
- [ ] Publish Kafka events
- [ ] Add monitoring and alerts

### Phase 3: Rollout (Week 3)
- [ ] Deploy to dev
- [ ] Deploy to staging with feature flag
- [ ] Monitor for 3 days
- [ ] Deploy to production

## Monitoring & Rollout

### Metrics
- `orders_cancelled_total` - Counter of cancelled orders
- `order_cancellation_duration_seconds` - Cancellation processing time
- `order_cancellation_errors_total` - Cancellation failures

### Alerts
- High cancellation error rate (>5%)
- Slow cancellation processing (p99 >2s)

### Feature Flag
- `enable_order_cancellation` - Boolean flag to enable/disable

### Rollback Plan
1. Disable feature flag immediately
2. If needed, rollback deployment
3. Fix issues and redeploy

## Dependencies

### Upstream Services
- Payment Service: Must support refund API
- Inventory Service: Must support restocking

### Downstream Services
- Notification Service: Will receive cancellation events
- Analytics Service: Will track cancellation metrics

## Open Questions

- [ ] How long should we allow cancellations after order placed?
- [ ] Should we support partial cancellations?
- [ ] What happens if refund fails?

## Updates Log

**2024-11-27**: Initial PRD created
**2024-11-28**: Added refund integration details after discussion
```

## Complete Example

```markdown
# PRD: User Authentication System

**Status**: Implemented
**Author**: Development Team
**Created**: 2024-10-15
**Updated**: 2024-11-20

## Summary

Implement JWT-based user authentication system with login/logout endpoints, token validation middleware, and integration with existing user database. This enables secure access control for our API endpoints.

## Background & Motivation

### Problem
Currently, all API endpoints are publicly accessible without authentication. This creates security risks and prevents user-specific functionality (like user profiles, order history, etc.).

### Why Now?
We're launching B2B features next quarter that require authenticated access. Without auth, we can't differentiate between users or protect sensitive data.

### Current State
- All endpoints are public
- No user sessions or tracking
- Can't implement user-specific features

## Goals and Non-Goals

### Goals
- Secure API endpoints with JWT authentication
- Support login/logout workflows
- Enable user-specific features
- Maintain <200ms authentication overhead

### Non-Goals
- Social login (OAuth) - future PRD
- Two-factor authentication - future PRD
- Password reset flow - separate PRD
- Admin user management UI

## Requirements

### Functional Requirements
1. **User Login**: Accept email/password, return JWT token on success
2. **Token Validation**: Middleware validates JWT on protected endpoints
3. **User Logout**: Invalidate tokens (add to blacklist)
4. **Token Refresh**: Issue new tokens before expiration
5. **Password Hashing**: Use bcrypt with salt for password storage

### Non-Functional Requirements
- **Performance**: Token validation <50ms p99
- **Scalability**: Support 10,000 concurrent authenticated users
- **Reliability**: 99.9% uptime for auth service
- **Security**: Tokens expire after 24 hours, refresh tokens after 7 days

## User Stories

### Story 1: User Login
**As a** registered user
**I want** to log in with email and password
**So that** I can access my account

**Acceptance Criteria**:
- [ ] Valid credentials return JWT token
- [ ] Invalid credentials return 401 with error message
- [ ] Passwords are hashed with bcrypt
- [ ] Failed login attempts are rate-limited

### Story 2: Access Protected Resource
**As an** authenticated user
**I want** to access protected endpoints using my token
**So that** I can retrieve my personal data

**Acceptance Criteria**:
- [ ] Valid token grants access
- [ ] Expired token returns 401
- [ ] Invalid token returns 401
- [ ] Missing token returns 401

## API Impact

### New Endpoints

**POST /api/v1/auth/login**
```json
// Request
{
  "email": "user@example.com",
  "password": "securepassword"
}

// Response (200 OK)
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 86400
}

// Error (401 Unauthorized)
{
  "error": "invalid_credentials",
  "message": "Email or password is incorrect"
}
```

**POST /api/v1/auth/logout**
```json
// Request
Headers: Authorization: Bearer <token>

// Response (200 OK)
{
  "message": "Logged out successfully"
}
```

**POST /api/v1/auth/refresh**
```json
// Request
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}

// Response (200 OK)
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 86400
}
```

### Modified Endpoints
- All `/api/v1/orders/*` endpoints now require authentication
- All `/api/v1/users/*` endpoints now require authentication

## Technical Design

### Architecture
```text
Client → Login Endpoint → Auth Service → Database
                              ↓
                         JWT Token
                              ↓
Client → Protected Endpoint → Validate Middleware → Service
                                      ↓
                              Check Token Blacklist
```

### Data Model Changes
```sql
-- New table for token blacklist
CREATE TABLE token_blacklist (
  token_hash VARCHAR(64) PRIMARY KEY,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_blacklist_expires ON token_blacklist(expires_at);

-- Add to existing users table
ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
ALTER TABLE users ADD COLUMN last_login TIMESTAMP;
```

### Key Design Decisions
1. **JWT over sessions**: Stateless tokens reduce database load
2. **Token blacklist**: Track logged-out tokens until expiration
3. **bcrypt for passwords**: Industry standard with configurable cost factor
4. **Middleware pattern**: Reusable authentication across endpoints

## Edge Cases & Error Handling

### Edge Cases
1. **Expired token during request**: Return 401, client should refresh
2. **Token in blacklist**: Return 401 with "token_revoked" error
3. **Concurrent logins**: Allow multiple active tokens per user
4. **Password with special characters**: URL-encode properly
5. **Very old refresh token**: Require full re-login

### Error Responses
- 400: Malformed request (missing email/password)
- 401: Invalid credentials or token
- 429: Rate limit exceeded (max 5 failed attempts per minute)
- 500: Internal server error

## Implementation Plan

### Phase 1: Core Auth (Week 1)
- [ ] Create auth service interface
- [ ] Implement JWT utility functions
- [ ] Add bcrypt password hashing
- [ ] Create token blacklist
- [ ] Write unit tests for auth service

### Phase 2: API Endpoints (Week 2)
- [ ] Implement login endpoint
- [ ] Implement logout endpoint
- [ ] Implement refresh endpoint
- [ ] Add authentication middleware
- [ ] Write integration tests

### Phase 3: Integration (Week 3)
- [ ] Protect existing endpoints with middleware
- [ ] Add rate limiting
- [ ] Update API documentation
- [ ] Add monitoring metrics

### Phase 4: Rollout (Week 4)
- [ ] Deploy to dev environment
- [ ] Deploy to staging with feature flag
- [ ] Load testing (10,000 concurrent users)
- [ ] Security audit
- [ ] Deploy to production

## Monitoring & Rollout

### Metrics
- `auth_login_attempts_total` - Counter (labels: success/failure)
- `auth_token_validation_duration_seconds` - Histogram
- `auth_token_blacklist_size` - Gauge
- `auth_active_tokens_total` - Gauge

### Alerts
- High login failure rate (>10% failures)
- Slow token validation (p99 >100ms)
- Token blacklist growing >10,000 entries

### Feature Flag
- `enable_authentication` - Boolean to enable/disable auth enforcement
- Start with flag OFF, test thoroughly before enabling

### Rollback Plan
1. Disable `enable_authentication` flag
2. Revert middleware changes if needed
3. Monitor for 24 hours before re-enabling

## Dependencies

### Upstream Services
- User Database: Must have users table with email field

### Downstream Services
- All API services: Must handle 401 responses gracefully

### External Libraries
- `github.com/golang-jwt/jwt/v5` - JWT implementation
- `golang.org/x/crypto/bcrypt` - Password hashing

## Open Questions

- [x] Token expiration time: 24 hours (confirmed)
- [x] Support multiple devices: Yes (multiple active tokens)
- [ ] Admin API for token revocation?
- [ ] Support API keys for service-to-service auth?

## Updates Log

**2024-10-15**: Initial PRD created
**2024-10-20**: Added token refresh endpoint based on team feedback
**2024-11-01**: Clarified rate limiting requirements
**2024-11-20**: Marked as implemented, production deployment complete
```

## Best Practices

### For AI Context

**Write assuming AI has no prior knowledge:**
- Explain business context clearly
- Define all acronyms and domain terms
- Link to related documentation
- Include "why" not just "what"

**Example:**

❌ Bad: "Add cancellation endpoint"

✓ Good: "Add order cancellation endpoint to enable customers to cancel orders within 24 hours of purchase. This reduces customer service workload and improves customer satisfaction."

### Content Quality

**Critical sections:**
1. **Summary** - Clear 2-3 sentence description
2. **Background & Motivation** - Why this feature matters
3. **Goals and Non-Goals** - Scope boundaries
4. **Requirements** - Specific, testable criteria
5. **User Stories** - How users will interact with feature

**What to include:**
- Business justification
- Acceptance criteria (testable)
- Edge cases and error handling
- Dependencies on other services
- Monitoring and rollback plans
- Success metrics

**What to avoid:**
- Implementation details (that's for code)
- Assuming reader knows business context
- Vague requirements ("should be fast")
- Missing non-goals (scope creep risk)
- No success criteria

### Maintenance

**Update PRD during implementation:**
- Mark status as "In Progress" when starting
- Update when requirements change during development
- Add discoveries to "Open Questions"
- Document decisions in "Updates Log"
- Mark "Implemented" when complete
- **STOP editing after implementation** - PRD becomes immutable historical reference

**Don't delete old PRDs:**
- They provide historical context
- AI assistants benefit from seeing past features
- Mark as "Rejected" if decided not to implement
- Mark as "Deprecated" if feature was removed or superseded

## Status Management

**Available statuses:**
- **Draft** 📝 - Being written internally
- **Proposed** - Ready for review (PR open)
- **In Review** - Actively collecting feedback
- **Approved** - Decision made, not yet implemented
- **In Progress** 🚧 - Implementation started
- **Implemented** ✅ - Code merged, PRD now immutable
- **Superseded** - Replaced by newer PRD
- **Rejected** ❌ - Decided not to implement (keep for history)
- **Withdrawn** - Pulled back by author
- **Deprecated** - Feature removed or obsolete

**Common usage (90% of PRDs):**
```
Draft → In Progress → Implemented
```

**With formal process (10% of PRDs, like open source projects):**
```
Draft → Proposed → In Review → Approved → In Progress → Implemented
```

**End-of-life statuses (use when PRD becomes irrelevant):**
- Superseded, Rejected, Withdrawn, Deprecated

## Warning Banners

Warning banners are **only used for PRDs that are no longer relevant**:

**Superseded** (replaced by newer PRD):
```markdown
> ⚠️ SUPERSEDED
> This PRD has been replaced. See [2026-01-15-feature-v2.md](link)
```

**Rejected** (decided not to implement):
```markdown
> ⚠️ REJECTED
> This feature was not implemented. See rejection rationale below.
```

**Deprecated** (feature was removed):
```markdown
> ⚠️ DEPRECATED
> This feature has been removed from the library.
```

**Withdrawn** (pulled back by author):
```markdown
> ⚠️ WITHDRAWN
> This proposal was withdrawn and is no longer being pursued.
```

**No banner needed** for:
- Draft, Proposed, In Review, Approved, In Progress (work in progress)
- **Implemented** (feature exists, PRD documents design)

**Rationale**: An Implemented PRD from days/weeks ago is not "irrelevant" - it documents current design decisions. Only add warning banners when the PRD no longer applies to the codebase.

## Updates Log

Track significant changes with date and description:
```markdown
## Updates Log
**2024-11-27**: Initial PRD created
**2024-11-28**: Added refund integration after payment team discussion
**2024-12-01**: Reduced scope - removing partial cancellations (future PRD)
**2024-12-15**: Marked as implemented, deployed to production
```

## PRD Immutability

### Critical Principle: PRDs Become Immutable After Implementation

**Once Status: Implemented, STOP editing the PRD.**

The PRD becomes a **historical snapshot** of the original design decision. This is intentional and valuable.

### Why Immutability Matters

**PRDs answer:** "Why did we build it THIS way at THAT time?"

If you keep updating the PRD after implementation:
- ❌ Historical context is lost
- ❌ Can't see original trade-offs and constraints
- ❌ Can't understand why certain decisions were made
- ❌ Knowledge disappears when maintainers leave ("Bus Factor")

If PRDs are immutable:
- ✅ Original reasoning preserved forever
- ✅ Can trace feature evolution through multiple PRDs
- ✅ Future maintainers understand past constraints
- ✅ Prevents re-litigating old decisions

### Where Future Changes Go

**If the feature changes after implementation:**

**Option 1: Update Living Documentation**
- Update README.md, API docs, Wiki pages
- Living documentation = always current, reflects actual behavior
- PRD = historical snapshot of original design

**Option 2: Write New PRD (for major redesigns)**
- Create new PRD with new date: `YYYY-MM-DD-feature-v2.md`
- Reference original PRD: "Supersedes 2025-01-15-feature.md"
- New PRD documents new design decisions and trade-offs
- Both PRDs preserved = complete evolution history

### Example Evolution

```
2025-01-15-jwt-authentication.md     (Status: Implemented)
  ↓ (6 months later, major redesign needed)
2025-07-20-oauth2-migration.md       (Status: Implemented, supersedes JWT PRD)
  ↓ (both preserved)
Complete history of authentication evolution
```

### What to Do After Implementation

1. **Mark as implemented:**
   ```yaml
   **Status**: Implemented
   **Created**: 2025-12-05
   **Implemented**: 2025-12-05
   ```

2. **Add final Updates Log entry:**
   ```markdown
   ## Updates Log
   **2025-12-05**: Implementation complete
   - All phases completed
   - Tests passing (95% coverage)
   - Documented in README.md
   - Deployed to production
   ```

3. **STOP editing the PRD:**
   - Do NOT update when feature evolves
   - Do NOT add new sections or requirements
   - Do NOT modify technical specifications
   - PRD is now a permanent historical record

## Common Mistakes to Avoid

**1. Too much technical detail:**
- PRD defines WHAT and WHY, not HOW
- Implementation details belong in code/ADRs
- Focus on requirements and acceptance criteria

**2. Missing non-goals:**
- Explicitly state what's out of scope
- Prevents scope creep during implementation
- Helps AI understand boundaries

**3. Vague requirements:**
- "Fast" → "Response time <200ms p99"
- "Reliable" → "99.9% uptime, <0.1% error rate"
- "Scalable" → "Handle 10,000 concurrent users"

**4. No user stories:**
- Requirements without user context are hard to validate
- User stories provide real-world validation

**5. Ignoring edge cases:**
- Edge cases often discovered during implementation
- Document them in PRD to prevent bugs

**6. Missing dependencies:**
- Document what services/APIs you depend on
- Note what depends on YOUR feature
- Helps identify integration risks early

## PRD vs ADR

**When to use PRD:**
- Defining a new feature
- Documenting user requirements
- Planning implementation phases

**When to use ADR:**
- Making architectural decisions
- Choosing between technical alternatives
- Documenting technology choices

**Use both:**
- PRD describes the feature
- ADR documents major technical decisions within that feature
- Link them together

**Example:**
- PRD: "User Authentication System" (what we're building)
- ADR: "Use JWT over Sessions" (how we're building it)

## Related Documentation

- For ADR documentation: See [adr-guide.md](adr-guide.md)
- For overall documentation structure: See [documentation-guide.md](documentation-guide.md)
