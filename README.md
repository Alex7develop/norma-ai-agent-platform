<div align="center">

# Norma AI

## The AI Operating System for Knowledge and Execution

**An autonomous AI workspace that understands your information,  
remembers context, and helps you execute complex tasks.**

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Production-green.svg)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange.svg)]()
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

<br/>

**Transform scattered information into structured knowledge and autonomous action.**

[Documentation](docs/README.md) · [Roadmap](docs/roadmap.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

</div>

---

# What is Norma AI?

Knowledge is scattered across documents, chats, drives, and repos. Norma AI is
an intelligent layer between people and that knowledge: **RAG + multi-agent
workflows + long-term memory**, scoped by workspace, project, and knowledge space.

It combines:

- Large language models (via OpenRouter)
- LangGraph agent workflows
- Retrieval Augmented Generation (Qdrant + BGE-M3)
- Conversation and vectorized workspace memory
- Async workers for long-running ingest and strategy runs

---

# Vision

Build an AI system that works like a chief of staff, researcher, product manager,
and technical advisor — not only answering questions, but helping you **ship
outcomes**.

> Humans define goals. AI accelerates execution.

---

# Features (shipped)

- **RAG knowledge base** — PDF / DOCX / Markdown / TXT, async index, space isolation  
- **RAG Assistant** — cited answers, conversation threads, memory notes  
- **Launch Strategy pack** — research → planning → specs → content → ingest  
- **Research Brief** — shorter async workflow: retrieve → research → persist  
- **Live web research** — DuckDuckGo snippets for the Research Agent  
- **Auth** — email/password, HttpOnly JWT cookies, workspace membership  
- **Projects & knowledge spaces** — UI switcher + create flows  
- **Async workers** — Redis queue for documents and workflows, heartbeat readiness  
- **React workspace** — Assistant / Workflows / Knowledge views  

Deep dives: [agents](docs/agents.md) · [RAG](docs/rag.md) · [memory](docs/memory.md) · [API](docs/api.md) · [Walkthrough](docs/walkthrough.md)

---

# Walkthrough

1. **Register** — create an account at the auth screen.  
2. **Upload knowledge** — Knowledge view: file upload or Notion import; wait for **completed**.  
3. **Ask** — Assistant: New chat, question grounded in your space.  
4. **Run a workflow** — Workflows: Launch Strategy or Research Brief.  
5. **Inspect** — open artifacts; the persisted pack appears in Knowledge.

Full steps: [docs/walkthrough.md](docs/walkthrough.md).

---

# Architecture (overview)

```text
React (Vite)  →  FastAPI  →  services / LangGraph
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   PostgreSQL      Redis       Qdrant
   (state)       (jobs)      (vectors)
                     │
                     ▼
              worker process
                     │
                     ▼
            embedding service (BGE-M3)
                     │
                     ▼
                 OpenRouter
```

Modular monolith with clear boundaries. Full write-up:
[docs/architecture.md](docs/architecture.md).

---

# Multi-agent system

Launch Strategy coordinator (worker):

```text
retrieve → research → planning → spec → content → persist → memory
```

RAG Assistant (request path): retrieve → generate (or no-context).

Details: [docs/agents.md](docs/agents.md).

---

# Quick start

```bash
git clone https://github.com/Alex7develop/norma-ai-agent-platform.git
cd norma-ai-agent-platform
cp .env.example .env
# set SECRET_KEY and OPENROUTER_API_KEY
docker compose up --build
```

| URL | Purpose |
|-|-|
| http://localhost:8000/docs | OpenAPI |
| http://localhost:8000/api/v1/health | Liveness |
| http://localhost:8000/api/v1/ready | Readiness (incl. worker) |
| http://localhost:5173 | React UI (`cd frontend && npm run dev`) |

First embeddings boot may take several minutes (BGE-M3 download).

Ops: [docs/deployment.md](docs/deployment.md) · local hacking: [docs/development.md](docs/development.md)

---

# Documentation

| Path | Description |
|-|-|
| [docs/README.md](docs/README.md) | Docs index |
| [docs/architecture.md](docs/architecture.md) | System design |
| [docs/agents.md](docs/agents.md) | Agents & LangGraph |
| [docs/rag.md](docs/rag.md) | Knowledge engine |
| [docs/memory.md](docs/memory.md) | Conversations & notes |
| [docs/api.md](docs/api.md) | HTTP overview |
| [docs/deployment.md](docs/deployment.md) | Docker / ops |
| [docs/development.md](docs/development.md) | Contributor setup |
| [docs/roadmap.md](docs/roadmap.md) | Phased roadmap |

Community: [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

# Roadmap (summary)

Phases 1–4 are complete for the MVP product surface. **Phase 5** has started
with **Notion** (OAuth + page import). Remaining: Slack, GitHub, Google Drive, CRM.

Full checklist: [docs/roadmap.md](docs/roadmap.md).

---

# Security

Workspace membership isolation, HttpOnly cookies, hashed refresh tokens, and
environment-backed secrets. Report vulnerabilities per [SECURITY.md](SECURITY.md).

---

# Philosophy

AI should amplify creativity, decisions, and execution — not replace judgment.

---

# Support

- Star the repository  
- Open issues with repro steps  
- Share product feedback  

<div align="center">

### The intelligent operating system for the next generation of work.

</div>
