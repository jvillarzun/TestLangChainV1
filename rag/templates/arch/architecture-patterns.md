# Software Architecture Patterns — Reference Guide

## Clean Architecture (preferred for mobile + backend)

```
Layers (inner → outer, dependency rule: inward only):

  ┌─────────────────────────────────┐
  │         Frameworks & Drivers    │  ← UI, DB, Web, Devices
  │  ┌───────────────────────────┐  │
  │  │    Interface Adapters     │  │  ← Controllers, Presenters, Gateways
  │  │  ┌─────────────────────┐ │  │
  │  │  │   Application       │ │  │  ← Use Cases, Application Services
  │  │  │  ┌───────────────┐  │ │  │
  │  │  │  │    Domain     │  │ │  │  ← Entities, Business Rules
  │  │  │  └───────────────┘  │ │  │
  │  │  └─────────────────────┘ │  │
  │  └───────────────────────────┘  │
  └─────────────────────────────────┘
```

**Rules:**
- Domain knows nothing about outer layers
- Use Cases orchestrate domain entities
- Adapters convert between formats (DTO ↔ Domain model)
- Frameworks are plugins — swappable

## SOLID Applied

```
S — Single Responsibility: one reason to change per class
O — Open/Closed: open for extension, closed for modification
L — Liskov Substitution: subtypes must be usable as their base type
I — Interface Segregation: small, specific interfaces > one fat interface
D — Dependency Inversion: depend on abstractions, not concretions
```

## Architectural Decision Record (ADR) Template

```markdown
# ADR-001: [Decision Title]

## Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

## Context
[What is the issue motivating this decision?]

## Decision
[What is the change we're proposing/have agreed to implement?]

## Consequences
### Positive
- 

### Negative (tradeoffs)
- 

### Neutral
- 
```

## API Design Patterns

### REST Resource Naming
```
GET    /users              → list
POST   /users              → create
GET    /users/{id}         → get one
PATCH  /users/{id}         → partial update
PUT    /users/{id}         → full replace
DELETE /users/{id}         → delete

# Nested resources
GET    /users/{id}/accounts
POST   /users/{id}/accounts

# Actions (when REST doesn't fit)
POST   /payments/{id}/refund
POST   /accounts/{id}/activate
```

### Error Response Standard
```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Account balance is insufficient for this transaction",
    "details": { "available": 150.00, "required": 500.00 },
    "trace_id": "req_abc123"
  }
}
```

## Event-Driven Architecture

```
Producer → Event Bus → Consumer(s)

Event envelope:
{
  "id":         "uuid",
  "type":       "payment.completed",
  "version":    "1.0",
  "timestamp":  "ISO8601",
  "source":     "payments-service",
  "data":       { ... }
}

Rules:
- Events are immutable facts (past tense: payment.completed, not payment.complete)
- Consumers are idempotent (handle duplicate delivery)
- Schema evolution: additive only (never remove fields)
- Dead letter queue for unprocessable events
```

## Microservice Communication

| Pattern | When to use | Tradeoff |
|---|---|---|
| Sync REST/gRPC | Query data, simple CRUD | Coupling, latency chain |
| Async Events | State changes, fan-out | Eventual consistency |
| Saga (choreography) | Distributed transactions (simple) | Hard to trace |
| Saga (orchestration) | Distributed transactions (complex) | Central coordinator |
| BFF (Backend for Frontend) | Multiple client types | Extra service |

## Database Per Service

```
Each service owns its data:
  payments-svc  → payments_db   (Postgres)
  users-svc     → users_db      (Postgres)
  sessions-svc  → sessions_db   (Redis)
  search-svc    → search_index  (Elasticsearch)

Cross-service queries → API calls or read-optimized projections
Never share a database between two services
```

## Caching Strategy

```
Cache-aside (lazy):    App checks cache → miss → load DB → write cache
Write-through:         App writes cache → cache writes DB (sync)
Write-behind:          App writes cache → cache writes DB (async)

TTL guidelines:
  Static content:     24h - 7d
  User sessions:      15m - 1h
  API responses:      1m - 5m
  Real-time data:     0 (no cache) or <10s
```
