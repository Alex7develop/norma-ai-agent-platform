"""Knowledge ingestion orchestration tests with infrastructure fakes."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.services.knowledge import KnowledgeService


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.scalar_calls = 0

    async def scalar(self, _: Any) -> Any:
        self.scalar_calls += 1
        return None if self.scalar_calls == 1 else 1

    def add(self, value: Any) -> None:
        self.added.append(value)

    def add_all(self, values: list[Any]) -> None:
        self.added.extend(values)

    async def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid4()

    async def commit(self) -> None:
        return None

    async def refresh(self, value: Any) -> None:
        value.created_at = datetime.now(UTC)


class FakeEmbeddings:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


class FakeVectorStore:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def upsert(self, records: list[Any]) -> None:
        self.records.extend(records)

    async def delete_document(self, *, workspace_id: str, document_id: str) -> None:
        return None


@pytest.mark.asyncio
async def test_ingest_coordinates_persistence_embeddings_and_vectors() -> None:
    session = FakeSession()
    vectors = FakeVectorStore()
    workspace_id = uuid4()
    service = KnowledgeService(  # type: ignore[arg-type]
        session,
        embeddings=FakeEmbeddings(),
        vectors=vectors,
    )

    result = await service.ingest(
        workspace_id=workspace_id,
        filename="notes.txt",
        content_type="text/plain",
        data=b"Norma stores useful knowledge.",
    )

    assert isinstance(result.id, UUID)
    assert result.workspace_id == workspace_id
    assert result.status == "completed"
    assert result.chunk_count == 1
    assert len(vectors.records) == 1
    assert vectors.records[0].metadata["workspace_id"] == str(workspace_id)
