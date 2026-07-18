# Deployment

## Local Docker (recommended)

```bash
cp .env.example .env
# set SECRET_KEY and OPENROUTER_API_KEY
docker compose up --build
```

Services:

| Service | Role |
|-|-|
| `backend` | FastAPI / Uvicorn |
| `worker` | Redis consumer (`app.workers.main`) |
| `migrate` | Alembic `upgrade head` (oneshot) |
| `postgres` | Relational state |
| `redis` | Job queue + worker heartbeat |
| `qdrant` | Vectors |
| `embeddings` | BGE-M3 HTTP embeddings |

Frontend is typically run via Vite locally (`npm run dev`) against
`VITE_API_URL=http://localhost:8000/api/v1`.

## Important env vars

See [`.env.example`](../.env.example):

- `DATABASE_URL`, `REDIS_URL`
- `QDRANT_HOST` / `QDRANT_PORT` / `QDRANT_COLLECTION`
- `EMBEDDING_SERVICE_URL`, `EMBEDDING_MODEL`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
- `SECRET_KEY`, cookie/JWT timings
- `WEB_SEARCH_ENABLED`, `WEB_SEARCH_MAX_RESULTS`
- `LAUNCH_STRATEGY_QUEUE`
- `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI`
- `FRONTEND_ORIGIN` (OAuth callback redirect target)

## Health checks

- API liveness: `GET /api/v1/health`
- Readiness: `GET /api/v1/ready` (includes worker heartbeat)
- Worker Compose healthcheck reads `norma:worker:heartbeat` from Redis

First embeddings boot downloads BGE-M3 into a named volume and can take several
minutes.

## Production notes (not fully productized yet)

- Rotate `SECRET_KEY`; never commit secrets  
- Terminate TLS at a reverse proxy  
- Back up Postgres volumes; treat Qdrant as rebuildable from documents  
- Scale `backend` and `worker` independently  
- Add rate limits, audit logs, and managed secret storage before public SaaS  

See also: [architecture.md](architecture.md), [development.md](development.md).
