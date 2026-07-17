# Architecture

Norma AI starts as a modular monolith. This keeps deployment and transactions
simple during product discovery while enforcing boundaries that can later be
extracted into services when scale or team ownership justifies it.

## Dependency direction

```text
API -> application services -> domain contracts
                              <- infrastructure adapters
```

- API handlers validate transport data and delegate to application services.
- Application services coordinate use cases and own transaction boundaries.
- Agent, workflow, RAG, and memory modules expose provider-neutral contracts.
- Database, Redis, Qdrant, and LLM clients are infrastructure adapters.
- Configuration is environment-backed and injected at composition boundaries.

Framework objects must not leak into domain contracts. In particular, future
agents should not know about FastAPI requests, and retrieval use cases should
not depend directly on Qdrant response models.

## Runtime topology

The local topology contains one stateless FastAPI process, PostgreSQL for
durable relational state, Redis for ephemeral coordination, and Qdrant for
vector search. All persistent services use named Docker volumes.

The liveness endpoint deliberately checks only the API process. A separate
readiness endpoint should be introduced when dependency adapters are wired, so
an infrastructure outage does not create a container restart loop.

## Scaling path

1. Add Alembic migrations, tenant-aware identity, and request observability.
2. Implement document ingestion and retrieval behind the existing RAG ports.
3. Implement memory policies and one auditable agent workflow.
4. Move long-running ingestion and execution to background workers.
5. Scale stateless API and workers independently.
6. Extract services only when operational load or ownership demands it.

## Security baseline

Secrets are read from the environment and never committed. Production work must
add managed secret storage, tenant isolation at every persistence boundary,
token rotation, audit logs, rate limits, explicit tool permissions, and
human approval for consequential actions.
