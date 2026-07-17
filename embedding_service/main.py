"""FastAPI application for local dense embedding inference."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "BAAI/bge-m3"
MAX_BATCH_SIZE = 128
MAX_TEXT_LENGTH = 32_768

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_TEXT_LENGTH),
]


class EmbedRequest(BaseModel):
    """Texts to encode in one inference batch."""

    model_config = ConfigDict(extra="forbid")

    texts: list[NonEmptyText] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


class EmbedResponse(BaseModel):
    """Normalized dense embeddings returned by the model."""

    embeddings: list[list[float]]
    dimension: int


class HealthResponse(BaseModel):
    """Service readiness information."""

    status: str
    model: str
    dimension: int


class EmbeddingEngine:
    """Owns the model and serializes CPU-heavy inference calls."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name, device="cpu")
        dimension = self._model.get_embedding_dimension()
        if dimension is None:
            raise RuntimeError(
                "The embedding model did not report its output dimension"
            )
        self.dimension = int(dimension)
        self._lock = Lock()

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts as L2-normalized dense vectors."""

        with self._lock:
            embeddings = self._model.encode(
                texts,
                batch_size=min(len(texts), 32),
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        return embeddings.tolist()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the configured model once before accepting requests."""

    model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL).strip()
    if not model_name:
        raise RuntimeError("EMBEDDING_MODEL must not be empty")

    app.state.engine = await run_in_threadpool(EmbeddingEngine, model_name)
    yield


app = FastAPI(
    title="Local Embedding Service",
    version="1.0.0",
    lifespan=lifespan,
)


def get_engine(request: Request) -> EmbeddingEngine:
    """Return the model initialized during application startup."""

    return request.app.state.engine


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Report readiness after the model has loaded."""

    engine = get_engine(request)
    return HealthResponse(
        status="ok",
        model=engine.model_name,
        dimension=engine.dimension,
    )


@app.post("/embed", response_model=EmbedResponse)
async def embed(payload: EmbedRequest, request: Request) -> EmbedResponse:
    """Return normalized dense embeddings for a bounded text batch."""

    engine = get_engine(request)
    embeddings = await run_in_threadpool(engine.encode, payload.texts)
    return EmbedResponse(embeddings=embeddings, dimension=engine.dimension)
