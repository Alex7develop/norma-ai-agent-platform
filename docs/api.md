# API Overview

Base URL (local): `http://localhost:8000/api/v1`  
Interactive OpenAPI: `http://localhost:8000/docs`

Auth uses **HttpOnly cookies** (`norma_access`, `norma_refresh`). Browser clients
send `credentials: "include"`. Knowledge, assistant, workflow, and project
routes require workspace membership (missing membership → **404**).

## Health

| Method | Path | Notes |
|-|-|-|
| GET | `/health` | Liveness |
| GET | `/ready` | Postgres, Redis, Qdrant, embeddings, worker heartbeat |

## Auth

| Method | Path | Notes |
|-|-|-|
| POST | `/auth/register` | Creates user, workspace, default project/space |
| POST | `/auth/login` | Sets cookies |
| POST | `/auth/refresh` | Rotates access via refresh cookie |
| POST | `/auth/logout` | Revokes refresh |
| GET | `/auth/me` | Current user + workspaces |

## Projects & spaces

| Method | Path | Notes |
|-|-|-|
| GET | `/projects?workspace_id=` | Ensures defaults, lists projects+spaces |
| POST | `/projects` | Create project (+ default Main space) |
| POST | `/projects/{id}/spaces?workspace_id=` | Create space |

## Knowledge

| Method | Path | Notes |
|-|-|-|
| GET | `/knowledge/documents` | Optional `space_id` |
| GET | `/knowledge/documents/{id}` | Poll ingest status |
| POST | `/knowledge/documents` | Multipart upload → **202** |
| DELETE | `/knowledge/documents/{id}` | Soft delete + vectors |
| POST | `/knowledge/search` | Semantic search |

## Assistant

| Method | Path | Notes |
|-|-|-|
| POST | `/assistant/query` | RAG answer + sources + `conversation_id` |
| GET | `/assistant/conversations` | Optional `space_id` |
| GET | `/assistant/conversations/{id}/messages` | Thread history |

## Workflows

| Method | Path | Notes |
|-|-|-|
| POST | `/workflows/launch-strategy` | Enqueue → **202** |
| GET | `/workflows/runs` | History (`space_id`, `limit`) |
| GET | `/workflows/runs/{id}` | Full artifacts + `current_step` |

## Integrations — Notion

| Method | Path | Notes |
|-|-|-|
| GET | `/integrations/notion/authorize` | `workspace_id`, `space_id` → authorize URL |
| GET | `/integrations/notion/callback` | OAuth redirect (sets connection, redirects to frontend) |
| GET | `/integrations/notion/status` | Connected flag + Notion workspace name |
| DELETE | `/integrations/notion` | Disconnect |
| GET | `/integrations/notion/pages` | Pages shared with the integration |
| POST | `/integrations/notion/import` | Import page ids → knowledge ingest **202** |

Requires `NOTION_CLIENT_ID` / `NOTION_CLIENT_SECRET` / `NOTION_REDIRECT_URI`.

## Conventions

- Tenancy fields: `workspace_id`, often `space_id`  
- Async jobs return quickly with a pollable resource id  
- Errors: transport validation **422**, auth **401**, membership **404**, infra **503**

See also: [deployment.md](deployment.md), [development.md](development.md).
