"""Knowledge retrieval boundary."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.rag.embeddings import EmbeddingProvider, HttpEmbeddingProvider
from app.rag.vectorstore import QdrantVectorStore


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    """A ranked chunk returned by retrieval."""

    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever(Protocol):
    """Interface consumed by future RAG use cases."""

    async def retrieve(
        self, query: str, *, workspace_id: str, limit: int = 10
    ) -> Sequence[RetrievedDocument]:
        """Return the most relevant document chunks."""

        ...


class QdrantRetriever:
    """Workspace-scoped semantic retrieval backed by Qdrant."""

    def __init__(
        self,
        embeddings: EmbeddingProvider | None = None,
        client: AsyncQdrantClient | None = None,
        *,
        collection_name: str = settings.qdrant_collection,
    ) -> None:
        self.embeddings = embeddings or HttpEmbeddingProvider()
        self.client = client or AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            check_compatibility=False,
        )
        self.collection_name = collection_name
        self._store = QdrantVectorStore(
            self.client,
            collection_name=collection_name,
        )

    async def retrieve(
        self,
        query: str,
        *,
        workspace_id: str,
        limit: int = 10,
    ) -> Sequence[RetrievedDocument]:
        """Embed a query and search only inside one workspace."""

        await self._store.ensure_collection()
        query_vector = await self.embeddings.embed_query(query)
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="workspace_id",
                        match=models.MatchValue(value=workspace_id),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            RetrievedDocument(
                content=str(point.payload.get("content", "")),
                score=point.score,
                metadata={
                    key: value
                    for key, value in point.payload.items()
                    if key != "content"
                },
            )
            for point in result.points
            if point.payload is not None
        ]
