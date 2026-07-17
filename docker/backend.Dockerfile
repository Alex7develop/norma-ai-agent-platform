FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build metadata is copied before source to preserve dependency layer caching.
COPY pyproject.toml README.md alembic.ini ./
COPY backend ./backend
RUN pip install .

RUN addgroup --system norma && adduser --system --ingroup norma norma
USER norma

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
