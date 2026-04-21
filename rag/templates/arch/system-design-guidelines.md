# System Design Guidelines

## Non-Functional Requirements Checklist

Before designing, confirm:
- **Scalability**: expected RPS now and 2 years out
- **Availability**: 99.9% (8.7h/yr downtime) vs 99.99% (52min/yr)?
- **Consistency**: strong vs eventual — what does the business tolerate?
- **Latency**: p50/p95/p99 targets per endpoint
- **Data retention**: how long, GDPR requirements?
- **Geography**: single region or multi-region?

## Capacity Estimation Template

```
DAU: 1M users
Writes/user/day: 5
Reads/user/day: 50

Write RPS: 1M × 5 / 86400 ≈ 58 RPS
Read  RPS: 1M × 50 / 86400 ≈ 580 RPS

Storage/write: 1 KB average
Storage/day:  58 × 86400 × 1KB ≈ 5 GB/day
Storage/year: 5 × 365 ≈ 1.8 TB/year
```

## High Availability Patterns

```
Load Balancer (active-active)
├── App Server 1
├── App Server 2
└── App Server N

Database (active-passive with replica lag < 1s):
├── Primary  ← writes
└── Replica  ← reads, promoted if primary fails

CDN → reduce latency for static assets, absorb read traffic

Circuit Breaker:
  CLOSED  → requests flow normally
  OPEN    → fail fast (after N failures in window)
  HALF-OPEN → probe if service recovered
```

## Observability — Three Pillars

```
LOGS:   structured JSON, correlation ID across services
        { "level": "error", "trace_id": "abc", "service": "payments", ... }

METRICS: RED method per service
        - Rate:    requests/second
        - Errors:  error rate %
        - Duration: p50/p95/p99 latency

TRACES: distributed tracing (OpenTelemetry)
        span per service call, propagate trace context in headers
```

## Security Checklist

- [ ] Auth: JWT with short expiry (15min) + refresh token rotation
- [ ] HTTPS everywhere, HSTS header
- [ ] Input validation at API boundary (never trust client)
- [ ] SQL: parameterized queries only
- [ ] Secrets: env vars / vault, never in code
- [ ] Rate limiting per user + per IP
- [ ] CORS: explicit allowlist, not wildcard in production
- [ ] Audit log: who did what and when (immutable)
- [ ] Dependency scanning in CI (OWASP, Snyk)

## Deployment Architecture (Cloud-native)

```
GitHub → CI/CD Pipeline → Container Registry
                              │
                    ┌─────────┴─────────┐
                    │   Kubernetes      │
                    │  ┌─────────────┐  │
                    │  │   Ingress   │  │
                    │  └──────┬──────┘  │
                    │  ┌──────┴──────┐  │
                    │  │  Services   │  │
                    │  │  (pods)     │  │
                    │  └─────────────┘  │
                    └───────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  Managed Services  │
                    │  DB / Cache / MQ   │
                    └───────────────────┘
```

## Architecture Review Checklist

Before approving:
- [ ] Single points of failure identified and mitigated
- [ ] Data flow diagram covers all PII
- [ ] Rollback strategy defined for each deployment
- [ ] Load tested at 2× expected peak
- [ ] Runbook written for top 5 failure scenarios
- [ ] On-call rotation and escalation path documented
