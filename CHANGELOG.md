# Changelog

All notable changes to Norma AI are documented here.
Format inspired by [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added

- Notion OAuth integration: connect workspace, list shared pages, import into a knowledge space via async ingest.
- Research Brief async workflow (retrieve → research → persist) alongside Launch Strategy.
- Assistant conversation list + New chat; mobile navigation drawer.
- Document ingest status badges in Knowledge views.

### Documentation

- Added engineering docs under `docs/` (agents, RAG, memory, API, deployment, development, roadmap).
- Added CONTRIBUTING, SECURITY, CODE_OF_CONDUCT; README now acts as documentation hub.
- Documented Notion endpoints in `docs/api.md`.
- Product walkthrough in README and `docs/walkthrough.md`.

## [0.1.0] — 2026-07-18

### Added

- FastAPI modular monolith with Alembic, auth (HttpOnly JWT cookies), workspaces.
- Knowledge engine: async document ingest, BGE-M3 embeddings, Qdrant retrieval.
- Projects and knowledge spaces with UI switcher / create flows.
- RAG Assistant LangGraph workflow with conversation memory.
- Launch Strategy multi-agent pack (research, planning, spec, content, execution).
- DuckDuckGo web research tool for Research Agent.
- Redis worker for Launch Strategy + knowledge ingest; heartbeat readiness.
- Vectorized workspace memory notes (`source_type=memory`).
- React workspace: Assistant, Workflows, Knowledge views with run progress UX.

### Security

- Workspace membership authorization on knowledge/assistant/workflow/project APIs.
- Refresh tokens stored as SHA-256 hashes and revocable on logout.
