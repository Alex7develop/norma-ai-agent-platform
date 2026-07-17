<div align="center">

# Norma AI

## The AI Operating System for Knowledge and Execution

**An autonomous AI workspace that understands your information,  
remembers context and helps you execute complex tasks.**

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Production-green.svg)]()
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange.svg)]()
[![LangChain](https://img.shields.io/badge/LangChain-Framework-black.svg)]()
[![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

<br/>

**Transform scattered information into structured knowledge and autonomous action.**

</div>


---

# What is Norma AI?

Modern people and companies are drowning in information.

Knowledge is spread across:

- Documents
- Emails
- Slack messages
- Notion pages
- Google Drive
- GitHub repositories
- Meeting notes
- PDFs
- Internal systems

The problem is not lack of information.

The problem is:

> Information exists, but intelligence cannot access it.

---

**Norma AI creates an intelligent layer between humans and their knowledge.**

It combines:

- Large Language Models
- Autonomous AI Agents
- Retrieval Augmented Generation (RAG)
- Long-term Memory
- Workflow Automation

to create an AI operating system that understands, remembers and executes.

---

# Vision

Our vision is to build an AI system that works like a:

- Chief of Staff
- Research Analyst
- Product Manager
- Knowledge Manager
- Business Assistant
- Technical Advisor

Instead of asking:

> "What can AI answer?"

Norma asks:

> "What can AI help you accomplish?"


---

# Core Features

## Multi-Agent AI System

Norma is not a single chatbot.

It is an ecosystem of specialized AI agents working together.

```
                         User

                          │

                          ▼

                   Norma Core Agent

                          │

        ┌─────────────────┼─────────────────┐

        ▼                 ▼                 ▼


 Research Agent      Planning Agent     Memory Agent


        │                 │                 │


        ▼                 ▼                 ▼


 Knowledge         Workflows          Personal Context


        │

        ▼


 Execution Agent


        │

        ▼


      Final Result

```


---

# Intelligent Memory

Norma remembers context.

Examples:

```
User:
"I want to build a coffee business in Australia."

Norma stores:

- Business interests
- Previous decisions
- Market preferences
- Current projects
- Important context

Future conversations become smarter.
```

---

# 📚 Knowledge Base with RAG

Upload your knowledge:

```
Documents

├── PDF
├── DOCX
├── Markdown
├── TXT
├── Code
└── Web Pages

        ↓

   Embeddings

        ↓

     Qdrant

        ↓

 Semantic Retrieval

        ↓

 AI Response

```

---

# Autonomous Workflows

Norma can execute complex tasks.

Example:

```
User:

"Create a launch strategy for my SaaS product"


Norma:


1. Understand objective

2. Research market

3. Analyze competitors

4. Create positioning

5. Generate roadmap

6. Prepare marketing plan

7. Save knowledge


Result:

Complete strategic document

```

---

# Architecture

High-level architecture:

```

                     Frontend

                React + TypeScript

                         │

                         ▼


                     FastAPI


                         │


                         ▼


                   LangGraph


                         │


        ┌────────────────────────────────┐


        ▼                ▼               ▼


   AI Agents          Memory          Tools


        │                │               │


        ▼                ▼               ▼


   LangChain        PostgreSQL       APIs


        │


        ▼


    OpenRouter


        │


        ▼


 GPT / Claude / Gemini


        │


        ▼


      Qdrant


```

---

# AI Agents

## Norma Core Agent

The brain of the system.

Responsibilities:

- Understand user intent
- Create execution plans
- Coordinate agents
- Manage workflow state


---

## Research Agent

Responsible for:

- Information discovery
- Document analysis
- Market research
- Knowledge retrieval


---

## Memory Agent

Maintains long-term context:

- User preferences
- Previous conversations
- Project history
- Important decisions


---

## Planning Agent

Transforms goals into actions.

Example:

Input:

```
Build an AI SaaS product
```

Output:

```
Research

↓

Architecture

↓

Development plan

↓

Launch strategy

↓

Marketing

```

---

## Execution Agent

Turns decisions into actions.

Examples:

- Create documents
- Generate reports
- Prepare tasks
- Build specifications


---

# 🛠 Technology Stack


## Backend

| Technology | Purpose |
|-|-|
| Python 3.12 | Core language |
| FastAPI | API layer |
| Pydantic | Data validation |
| SQLAlchemy | ORM |
| PostgreSQL | Persistent storage |
| Redis | Cache and queues |


---

## AI Layer

| Technology | Purpose |
|-|-|
| LangGraph | Agent orchestration |
| LangChain | AI framework |
| OpenRouter | LLM gateway |
| Claude | Reasoning model |
| GPT | General intelligence |


---

## Knowledge Layer

| Technology | Purpose |
|-|-|
| Qdrant | Vector database |
| BGE-M3 | Embeddings |
| RAG | Knowledge retrieval |
| Reranking | Better relevance |


---

## Infrastructure

| Technology | Purpose |
|-|-|
| Docker | Containers |
| Docker Compose | Local environment |
| GitHub Actions | CI/CD |
| Nginx | Reverse proxy |


---

# 📂 Project Structure

```
norma-ai/
├── backend/app/
│   ├── api/v1/       # Versioned HTTP transport
│   ├── core/         # Configuration, logging, security primitives
│   ├── database/     # SQLAlchemy engine, sessions, model base
│   ├── services/     # Application use cases
│   ├── schemas/      # Validated transport and service DTOs
│   ├── agents/       # Provider-neutral agent contracts
│   ├── workflows/    # Workflow orchestration contracts
│   ├── rag/          # Embedding, vector store, retrieval boundaries
│   ├── memory/       # Long-term memory boundaries
│   └── main.py       # FastAPI composition root
├── backend/alembic/  # Versioned PostgreSQL schema migrations
├── embedding_service/ # Local BGE-M3 inference API
├── frontend/         # React, TypeScript, Vite, Tailwind CSS
├── docker/           # Container build definitions
├── docs/             # Architecture and engineering decisions
├── tests/            # Automated backend tests
├── docker-compose.yml
└── pyproject.toml
```

Norma AI begins as a modular monolith: domain boundaries remain explicit while
deployment stays simple for the MVP. PostgreSQL owns durable relational data,
Redis supports ephemeral coordination, and Qdrant owns vector search. See
[`docs/architecture.md`](docs/architecture.md) for dependency rules and the
scaling path.

---

# Roadmap


## Phase 1 — Foundation

Status: Foundation Ready


- [x] Project concept
- [x] Architecture design
- [x] FastAPI backend
- [x] Docker setup
- [x] OpenRouter integration


---

## Phase 2 — Knowledge Engine


- [x] Document upload
- [x] Embeddings pipeline
- [x] Qdrant integration
- [x] RAG retrieval


---

## Phase 3 — Agent System


- [ ] LangGraph workflow
- [ ] Coordinator Agent
- [ ] Research Agent
- [ ] Memory Agent
- [ ] Execution Agent


---

## Phase 4 — Product


- [ ] React interface
- [ ] Authentication
- [ ] User projects
- [ ] Knowledge spaces


---

## Phase 5 — Enterprise


- [ ] Slack integration
- [ ] Notion integration
- [ ] GitHub integration
- [ ] Google Drive integration
- [ ] CRM integrations


---

# Quick Start

```bash
git clone https://github.com/<your-org>/norma-ai.git
cd norma-ai
cp .env.example .env
docker compose up --build
```

The API is available at `http://localhost:8000`, interactive documentation at
`http://localhost:8000/docs`, liveness at
`http://localhost:8000/api/v1/health`, and infrastructure readiness at
`http://localhost:8000/api/v1/ready`.

Knowledge endpoints are available under `/api/v1/knowledge`. Uploads support
PDF, DOCX, Markdown, and TXT; semantic search is isolated by `workspace_id`.
The first Docker startup downloads BGE-M3 into a persistent model cache and can
therefore take several minutes.

For backend development without Docker:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --app-dir backend --reload
pytest
```

For frontend development:

```bash
cd frontend
npm install
npm run dev
```

---

# Security

Norma AI is designed with privacy in mind.

Principles:

- User data isolation
- Secure API communication
- Controlled tool execution
- Permission-based integrations


---

# Philosophy


AI should not replace human thinking.

AI should amplify:

- Creativity
- Decision making
- Execution speed
- Knowledge management


Norma AI is built around this idea:

> Humans define goals. AI accelerates execution.


---

# Future Vision

The future workplace will not be humans versus AI.

It will be humans working with intelligent systems.

Norma AI aims to become the operating layer between people and information — helping individuals and organizations transform knowledge into action.


---

# Support

If you like the idea:

- Star the repository
- Follow development
- Share feedback


---

<div align="center">

## Norma AI

### The intelligent operating system for the next generation of work.

</div>
