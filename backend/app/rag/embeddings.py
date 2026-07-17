"""Embedding provider boundary."""

from collections.abc import Sequence
from typing import Protocol

import httpx

from app.core.config import settings


class EmbeddingProvider(Protocol):
    """Decouple document processing from a specific embedding vendor."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of document chunks."""

        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query."""

        ...


class EmbeddingServiceError(RuntimeError):
    """Raised when the local embedding service cannot produce vectors."""


class HttpEmbeddingProvider:
    """HTTP adapter for the independently scalable BGE-M3 service."""

    def __init__(
        self,
        base_url: str = settings.embedding_service_url,
        *,
        timeout_seconds: float = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/embed",
                    json={"texts": list(texts)},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingServiceError("Embedding service request failed") from exc

        payload = response.json()
        embeddings = payload.get("embeddings")
        dimension = payload.get("dimension")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise EmbeddingServiceError("Embedding service returned an invalid batch")
        if dimension != settings.embedding_dimension:
            raise EmbeddingServiceError(
                "Embedding dimension does not match configuration"
            )
        return embeddings

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed document chunks in one batch."""

        return await self._embed(texts)

    async def embed_query(self, text: str) -> list[float]:
        """Embed one search query."""

        embeddings = await self._embed([text])
        return embeddings[0]
