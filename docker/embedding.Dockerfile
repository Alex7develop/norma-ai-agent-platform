FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models \
    EMBEDDING_MODEL=BAAI/bge-m3

WORKDIR /app

COPY embedding_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --create-home --uid 10001 app \
    && mkdir -p "${HF_HOME}" \
    && chown -R app:app /home/app "${HF_HOME}"

COPY --chown=app:app embedding_service /app/embedding_service

USER app

EXPOSE 8001

CMD ["uvicorn", "embedding_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
