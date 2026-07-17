# Local embedding service

CPU-only FastAPI service for normalized dense embeddings. The model defaults to
`BAAI/bge-m3` and can be changed with `EMBEDDING_MODEL`.

## Run locally

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r embedding_service/requirements.txt
.venv/bin/uvicorn embedding_service.main:app --host 0.0.0.0 --port 8000
```

The model is downloaded and loaded during application startup. A service is
ready when `GET /health` returns HTTP 200.

```bash
curl -X POST http://localhost:8000/embed \
  -H 'Content-Type: application/json' \
  -d '{"texts":["first text","second text"]}'
```

Requests are limited to 128 non-empty texts, with at most 32,768 characters per
text.
