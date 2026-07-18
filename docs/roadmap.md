# Roadmap

Living product roadmap for Norma AI. Checkboxes reflect shipped capability in
the main branch.

## Phase 1 — Foundation

- [x] Project concept
- [x] Architecture design
- [x] FastAPI backend
- [x] Docker setup
- [x] OpenRouter integration

## Phase 2 — Knowledge Engine

- [x] Document upload
- [x] Embeddings pipeline (BGE-M3 service)
- [x] Qdrant integration
- [x] RAG retrieval
- [x] Async document ingest (Redis worker)

## Phase 3 — Agent System

- [x] LangGraph RAG Assistant workflow
- [x] Launch Strategy coordinator
- [x] Research Agent (+ web search)
- [x] Planning / Spec / Content agents
- [x] Memory Agent
- [x] Execution Agent

## Phase 4 — Product

- [x] React knowledge / assistant / workflows UI
- [x] Authentication (HttpOnly JWT cookies)
- [x] User projects
- [x] Knowledge spaces
- [x] Workspace switcher + create project/space
- [x] Workflow run history + progress UX
- [x] Vectorized workspace memory notes
- [x] Worker heartbeat / readiness

## Phase 5 — Enterprise (next)

- [ ] Slack integration
- [x] Notion integration (OAuth + page import into knowledge spaces)
- [ ] GitHub integration
- [ ] Google Drive integration
- [ ] CRM integrations

## Documentation track

- [x] `docs/architecture.md` and sibling engineering pages
- [x] Community files (`CONTRIBUTING`, `CHANGELOG`, `SECURITY`, `CODE_OF_CONDUCT`)
- [ ] Demo GIF / recorded walkthrough in README
- [ ] Published API reference beyond OpenAPI

See [CHANGELOG.md](../CHANGELOG.md) for release notes.
