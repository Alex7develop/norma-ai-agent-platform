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
filtered by `workspace_id` and `space_id`. BGE-M3 runs behind an HTTP boundary so
API and embedding capacity can scale independently.

Within a workspace, knowledge is further isolated by **projects** and
**knowledge spaces**. Registration creates a default project (`My project`) and
space (`Main`). Documents, conversations, workflow runs, and workspace memories
carry a required `space_id`.

Document uploads are async: `POST /knowledge/documents` stores raw bytes in
`document_uploads`, enqueues a Redis job, and returns **202**. The unified
`worker` (`python -m app.workers.main`) indexes the file and deletes the upload
payload. Launch Strategy runs use the same worker and queue. The worker writes a
Redis heartbeat (`norma:worker:heartbeat`); `/ready` fails when it is missing.

## First agent workflow

The initial LangGraph workflow is stateless and intentionally narrow:
workspace-scoped retrieval followed by one grounded OpenRouter generation. The
system prompt treats retrieved documents as untrusted context, requires source
citations, and avoids an LLM call when retrieval returns no evidence.

The selected model is configured through `OPENROUTER_MODEL`; provider-specific
details do not leak into the graph. Conversation memory and external tool loops
remain separate future capabilities rather than hidden behavior in the first
assistant.

## Launch Strategy multi-agent workflow

The second LangGraph workflow coordinates specialist agents for a launch brief:

1. retrieve space-scoped workspace context
2. Research Agent synthesizes market and competitor notes (DuckDuckGo web
   snippets when `WEB_SEARCH_ENABLED`, plus workspace context)
3. Planning Agent drafts positioning, roadmap, and marketing outline
4. Spec Agent drafts business model, financial outline, PRD, and tech TZ
5. Content Agent drafts Cursor prompts plus LinkedIn and Telegram posts
6. Execution Agent assembles one markdown pack and ingests it through
   `KnowledgeService` into the run's knowledge space
7. Memory Agent stores a short workflow summary in `workspace_memories`

`POST /workflows/launch-strategy` returns **202** with a `pending` run; the
worker BRPOPs jobs from Redis, updates `current_step`, and clients poll
`GET /workflows/runs/{id}`. Runs and artifacts are persisted for auditability.
The pack becomes ordinary space knowledge, so the RAG assistant can cite it later.

## Conversation memory

Assistant turns are stored in `conversations` / `conversation_messages`, scoped
by workspace, knowledge space, and user. Optional `conversation_id` continues a
thread. Before generation, the RAG workflow receives recent chat turns and
workspace memory notes as supporting (untrusted) context alongside retrieved
chunks. Workflow summaries are embedded into Qdrant (`source_type=memory`) and
retrieved semantically for the current question, with SQL recent-notes fallback.

## Authentication

Users authenticate with email and password. Access and refresh JWTs are issued
as HttpOnly cookies. Refresh tokens are stored only as SHA-256 hashes and can
be revoked. Knowledge and assistant endpoints require a valid access cookie and
a matching workspace membership; missing membership returns 404 to avoid
workspace enumeration.

## Frontend workspace

The React client consumes only versioned API contracts. It restores the current
session through `/auth/me`, switches workspace/project/space in the sidebar
(with create project/space), lists and manages indexed documents for the
selected space (polling pending ingest), shows Launch Strategy run history with
step pipeline + elapsed time, and renders assistant source metadata alongside
each answer.

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
