# Agents

Norma AI uses specialized agents coordinated by LangGraph workflows. Agents are
provider-neutral: they talk to OpenRouter through a shared client and never see
FastAPI request objects.

## Current agents

| Agent | Role in product |
|-|-|
| Research Agent | Market brief + competitor notes; optional DuckDuckGo snippets |
| Planning Agent | Positioning, roadmap, marketing outline |
| Spec Agent | Business model, financial outline, PRD, tech spec |
| Content Agent | Cursor prompts, LinkedIn and Telegram drafts |
| Execution Agent | Assemble Launch Strategy pack and ingest into knowledge |
| Memory Agent | Conversation turns + workspace memory notes |
| RAG Assistant | Grounded Q&A over space-scoped knowledge |

There is no separate “Norma Core Agent” process. Coordination lives in the
compiled LangGraph graphs under `backend/app/workflows/`.

## Workflow 1 — RAG Assistant

Entry: `POST /api/v1/assistant/query`

```text
question
  → retrieve space-scoped chunks (Qdrant)
  → if empty: no-context response
  → else: OpenRouter generation with citations
```

Supporting context (untrusted):

- recent conversation turns
- workspace memory notes (semantic + SQL fallback)

Output: answer, source metadata, `conversation_id`.

## Workflow 2 — Launch Strategy

Entry: `POST /api/v1/workflows/launch-strategy` → **202** + `run_id`

Worker executes:

```text
queued → retrieve → research → planning → spec → content → persist → done
```

1. Retrieve knowledge-space context for the brief  
2. Research Agent (web + workspace)  
3. Planning Agent  
4. Spec Agent  
5. Content Agent  
6. Execution Agent → markdown pack → `KnowledgeService.ingest`  
7. Memory summary → PostgreSQL + Qdrant (`source_type=memory`)

Artifacts are stored in `workflow_artifacts`. Clients poll
`GET /api/v1/workflows/runs/{run_id}` and watch `current_step`.

## Workflow 3 — Research Brief

Entry: `POST /api/v1/workflows/research-brief` → **202** + `run_id`

Worker executes:

```text
queued → retrieve → research → persist → done
```

1. Retrieve knowledge-space context for the brief  
2. Research Agent (web + workspace) → research + competitors  
3. Assemble a short markdown brief → `KnowledgeService.ingest`  
4. Memory summary → PostgreSQL + Qdrant (`source_type=memory`)

Same run history and polling APIs as Launch Strategy; `workflow_type` is
`research_brief`.

## Design rules

- Retrieved and web content is untrusted prompt context.
- Missing evidence must be labeled **Assumption** where agents invent detail.
- Long runs never block HTTP; Redis queue + worker owns execution.
- Agent modules live in `backend/app/agents/`; orchestration in `workflows/`.

See also: [architecture.md](architecture.md), [rag.md](rag.md), [memory.md](memory.md).
