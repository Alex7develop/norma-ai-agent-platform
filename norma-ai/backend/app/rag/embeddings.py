"""Embedding provider boundary."""

from collections.abc import Sequence
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Decouple document processing from a specific embedding vendor."""

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of document chunks."""

        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed one retrieval query."""

        ...
