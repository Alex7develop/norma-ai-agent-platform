"""Vector persistence boundary."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """Provider-neutral vector payload."""

    id: str
    vector: Sequence[float]
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    """Operations required from a vector database adapter."""

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        """Insert or update vector records."""

        ...

    async def delete_document(self, *, workspace_id: str, document_id: str) -> None:
        """Delete every vector belonging to one scoped document."""

        ...


class QdrantVectorStore:
    """Qdrant adapter that owns collection schema and vector persistence."""

    def __init__(
        self,
        client: AsyncQdrantClient | None = None,
        *,
        collection_name: str = settings.qdrant_collection,
        dimension: int = settings.embedding_dimension,
    ) -> None:
        self.client = client or AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            check_compatibility=False,
        )
        self.collection_name = collection_name
        self.dimension = dimension
        self._initialized = False
        self._initialization_lock = asyncio.Lock()

    async def ensure_collection(self) -> None:
        """Create the collection and tenant filters once per process."""

        if self._initialized:
            return
        async with self._initialization_lock:
            if self._initialized:
                return
            if not await self.client.collection_exists(self.collection_name):
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.dimension,
                        distance=models.Distance.COSINE,
                    ),
                )
                for field_name in (
                    "workspace_id",
                    "space_id",
                    "document_id",
                    "source_type",
                    "memory_id",
                ):
                    await self.client.create_payload_index(
                        collection_name=self.collection_name,
                        field_name=field_name,
                        field_schema=models.PayloadSchemaType.KEYWORD,
                    )
            self._initialized = True

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        """Insert or update vector records."""

        if not records:
            return
        await self.ensure_collection()
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=record.id,
                    vector=list(record.vector),
                    payload=record.metadata,
                )
                for record in records
            ],
            wait=True,
        )

    async def delete_document(self, *, workspace_id: str, document_id: str) -> None:
        """Delete vectors only when both workspace and document match."""

        await self.ensure_collection()
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="workspace_id",
                            match=models.MatchValue(value=workspace_id),
                        ),
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        ),
                    ]
                )
            ),
            wait=True,
        )
