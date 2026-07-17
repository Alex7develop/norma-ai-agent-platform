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
durable relational state, Redis for ephemeral coordination, Qdrant for vector
search, and an independently scalable BGE-M3 embedding service. Persistent
services and the model cache use named Docker volumes.

The liveness endpoint deliberately checks only the API process. The readiness
endpoint checks PostgreSQL, Redis, Qdrant, and embeddings without turning a
temporary dependency outage into an application restart loop.

## Knowledge engine

Document metadata and extracted chunks are durable in PostgreSQL. Dense vectors
and retrieval payloads are stored in Qdrant using cosine distance and are always
filtered by `workspace_id`. BGE-M3 runs behind an HTTP boundary so API and
embedding capacity can scale independently.

The first ingestion path is synchronous and deliberately bounded by file,
page, character, and batch limits. The application service boundary is retained
so ingestion can move to a durable Redis-backed worker without changing API,
parser, embedding, or vector-store contracts.

## First agent workflow

The initial LangGraph workflow is stateless and intentionally narrow:
workspace-scoped retrieval followed by one grounded OpenRouter generation. The
system prompt treats retrieved documents as untrusted context, requires source
citations, and avoids an LLM call when retrieval returns no evidence.

The selected model is configured through `OPENROUTER_MODEL`; provider-specific
details do not leak into the graph. Conversation memory, tools, planning, and
multi-agent delegation remain separate future capabilities rather than hidden
behavior in the first assistant.

## Frontend workspace

The React client consumes only versioned API contracts. It keeps a generated
workspace UUID in local storage for the pre-authentication MVP, lists and
manages indexed documents, and renders assistant source metadata alongside each
answer. The UUID is a namespace convenience, not an authorization boundary;
the backend must derive workspace identity from authenticated claims before
multi-user deployment.

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
