# REST API Naming Guide

## Overview

One naming convention for REST resource paths across bborbe services. Resolves singular vs. plural, casing, nesting, query parameters, and when an action endpoint is acceptable.

**Core rule**: plural nouns for collections, singular nouns for singleton resources, HTTP methods for the verb.

**See also:**
- [go-http-service-guide.md](go-http-service-guide.md) - canonical admin endpoints, `/api/1.0/` prefix
- [go-http-handler-refactoring-guide.md](go-http-handler-refactoring-guide.md) - handler organization
- [go-json-error-handler-guide.md](go-json-error-handler-guide.md) - error response shape

## Scope

- Applies to **public/business API routes** — everything after the version prefix (`/api/1.0/<resources...>`). The prefix is the version boundary; naming starts after it.
- Does **not** apply to canonical admin/ops endpoints (`/healthz`, `/readiness`, `/metrics`, `/setloglevel/{level}`, `/gc`, `/resetdb`, `/resetbucket/{BucketName}`, `/regenerate`). These are an operational contract, not resources — see [Exceptions](#exceptions).
- **Existing routes are grandfathered.** Apply to new APIs and new endpoints; never rename a shipped route only to satisfy this guide (clients break, gain is cosmetic).

## Quick Reference

| Concept | Convention | Example |
|---------|------------|---------|
| Collection | Plural noun | `/users` |
| Individual resource | Collection + ID | `/users/123` |
| Nested collection | Plural noun | `/users/123/orders` |
| Nested resource | Collection + ID | `/users/123/orders/456` |
| Singleton resource | Singular noun | `/users/123/profile` |
| Filter / search / sort / page | Query parameters on the collection | `/orders?status=open&limit=50` |
| Action | `POST` + verb, only when necessary | `/orders/123/cancel` |
| Multi-word segment | lowercase kebab-case | `/audit-logs` |

## Resource Naming

### RULE rest/plural-collections (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: a new route addresses a collection of resources (or a member of one) using a singular noun — e.g. `/user/123`, `/order`.
**Enforcement**: judgment (route-table review)
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: The segment names the collection; the ID names the member. Mixing `/user/123` and `/orders/7` forces every client to memorise per-resource grammar. Plural is the dominant industry convention, so it is also what new readers guess first.

#### Bad

```
GET  /user
GET  /user/123
POST /order
```

#### Good

```
GET  /users
GET  /users/123
POST /orders
```

### RULE rest/singular-singletons (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: a route addresses a resource that exists exactly once per parent (or once per service) and names it in plural.
**Enforcement**: judgment (route-table review)
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: "Always plural" is the default, not the whole rule. A plural segment promises a collection — list, create, address by ID. A one-per-parent resource has none of that, so plural misleads. The segment's number must match the cardinality.

#### Bad

```
GET /users/123/profiles
GET /users/123/settingses
```

#### Good

```
GET /users/123/profile     # exactly one
GET /users/123/settings    # exactly one
GET /users/123/orders      # potentially many
```

### RULE rest/nouns-not-verbs (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: a route segment encodes a CRUD verb (`get`, `create`, `update`, `delete`, `list`) or a verb disguised as a noun (`user-search`, `order-processing`).
**Enforcement**: judgment (route-table review)
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: The HTTP method already carries the verb. A verb in the path duplicates it and invites contradictions (`GET /deleteUser/1`).

#### Bad

```
GET  /getUsers
POST /createOrder
POST /deleteUser/123
GET  /user-search?q=x
```

#### Good

```
GET    /users
POST   /orders
DELETE /users/123
GET    /users?query=x
```

### RULE rest/kebab-case-segments (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: a multi-word path segment uses camelCase, snake_case, or uppercase.
**Enforcement**: judgment (route-table review)
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: Paths are case-sensitive in practice and read by humans in logs; lowercase kebab-case is unambiguous and consistent.

#### Bad

```
/auditLogs
/shipping_addresses
/UserProfiles
```

#### Good

```
/audit-logs
/shipping-addresses
/user-profiles
```

Query parameter **names** use snake_case (`customer_id`, `created_at`), matching the JSON field names they filter on.

### RULE rest/domain-names-not-schema (SHOULD)

**Owner**: go-http-handler-assistant
**Applies when**: a path exposes storage terminology (table names, `_tbl`, `records`, `entries`, bucket names) instead of the domain noun.
**Enforcement**: judgment
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: The API is a contract about the domain; the schema changes underneath it. One canonical domain name per concept, used identically in API, code, and docs.

#### Bad

```
/customer_tbl
/user_records
```

#### Good

```
/customers
/users
```

Use correct irregular plurals (`/people`, `/children`, `/companies`) and keep uncountables as-is (`/metadata`, `/equipment`). Consistency beats grammatical cleverness — pick once, reuse everywhere.

### RULE rest/opaque-ids (SHOULD)

**Owner**: go-http-handler-assistant
**Applies when**: clients are expected to parse or construct meaning from an ID path segment.
**Enforcement**: judgment
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: An ID is a handle, not a query. Encoded meaning (`customer-123` vs `user-123`) becomes an undocumented second API. Prefixes are fine only when deliberately part of the public identifier scheme.

#### Bad

```
GET /users/customer-123    # client branches on the prefix
```

#### Good

```
GET /users/123
GET /users?type=customer
```

## Structure

### RULE rest/shallow-nesting (SHOULD)

**Owner**: go-http-handler-assistant
**Applies when**: a route nests more than two collection levels, or nests a child whose ID is already globally unique.
**Enforcement**: judgment
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: Nest to express ownership, not to mirror foreign keys. Deep paths force clients to know the whole ancestry just to fetch one item.

#### Bad

```
GET /projects/1/customers/2/orders/3/items/4
```

#### Good

```
GET /orders/3/items     # meaningful ownership: items of an order
GET /items/4            # item ID is globally unique
```

### RULE rest/query-params-for-queries (MUST)

**Owner**: go-http-handler-assistant
**Applies when**: filtering, sorting, searching, or paginating a collection is modelled as a separate path instead of query parameters.
**Enforcement**: judgment
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: Filters compose; paths don't. `/orders/open/by-customer/123` explodes combinatorially, `?status=open&customer_id=123` does not.

#### Bad

```
GET /orders/open
GET /orders/by-customer/123
GET /orders/recent
```

#### Good

```
GET /orders?status=open
GET /orders?customer_id=123
GET /orders?sort=-created_at&limit=50&offset=100
```

Conventions: `sort=<field>` ascending, `sort=-<field>` descending; `limit` + `offset` for pagination. A separate path is justified only when it is a genuinely different resource.

## Actions

### RULE rest/actions-as-exception (SHOULD)

**Owner**: go-http-handler-assistant
**Applies when**: a new `POST /<resource>/{id}/<verb>` endpoint is added.
**Enforcement**: judgment
**Trigger**: **/*.go, **/*.ts, **/*.py
**Why**: Most "actions" are state changes and fit `PATCH`. An explicit action is clearer only when the operation carries real domain semantics — validation beyond a field write, side effects, async processing, or no stored state at all. Ask first: can `PATCH` express it?

#### Bad

```
POST /users/123/set-email      # plain field write
```

#### Good

```
PATCH /users/123
{"email": "x@example.com"}

POST /orders/123/cancel        # refunds, notifications, stock release
POST /deployments/123/retry    # no field to patch
```

Action verbs are always `POST`, lowercase kebab-case, and attached to the resource they act on.

## Exceptions

| Route family | Why exempt |
|--------------|------------|
| `/healthz`, `/readiness`, `/metrics` | Infrastructure contract (Kubernetes, Prometheus). Already singular singletons. |
| `/setloglevel/{level}`, `/gc`, `/resetdb`, `/resetbucket/{BucketName}`, `/regenerate` | Admin-only ops verbs, not reachable from `/api/1.0/`. See [go-http-service-guide.md](go-http-service-guide.md). |
| Shipped `/api/1.0/...` routes predating this guide (e.g. trading `/api/1.0/candle/...`) | Grandfathered — renaming breaks clients for cosmetic gain. New endpoints on the same service follow this guide. |

## Checklist

- [ ] Collections plural (`/users`), singletons singular (`/users/123/profile`)
- [ ] IDs appended directly to the collection (`/users/42`)
- [ ] No HTTP verbs in paths
- [ ] Path segments lowercase kebab-case; query params snake_case
- [ ] Filtering / sorting / pagination via query params
- [ ] Nesting ≤ 2 levels, only for real ownership
- [ ] Action endpoints only where `PATCH` cannot express it
- [ ] Domain names, not storage names

## Out of Scope (future sections)

Status-code conventions, pagination response envelope, idempotency keys, versioning policy. Error response shape is already defined in [go-json-error-handler-guide.md](go-json-error-handler-guide.md).
