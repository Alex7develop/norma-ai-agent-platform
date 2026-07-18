"""Vectorized workspace memory tests."""

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.rag.retriever import RetrievedDocument
from app.services.memory import MemoryService


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, value: Any) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid4()


class FakeEmbeddings:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2]


@pytest.mark.asyncio
async def test_remember_workflow_summary_upserts_vector() -> None:
    session = FakeSession()
    vectors = AsyncMock()
    service = MemoryService(  # type: ignore[arg-type]
        session,
        embeddings=FakeEmbeddings(),
        vectors=vectors,
        notes_retriever=AsyncMock(),
    )

    memory = await service.remember_workflow_summary(
        workspace_id=uuid4(),
        space_id=uuid4(),
        run_id=uuid4(),
        summary_md="Launch Strategy completed for Aussie Roast.",
    )

    assert memory.id is not None
    vectors.upsert.assert_awaited_once()
    record = vectors.upsert.await_args.args[0][0]
    assert record.metadata["source_type"] == "memory"
    assert "Aussie Roast" in record.metadata["content"]


@pytest.mark.asyncio
async def test_load_workspace_notes_prefers_semantic_hits() -> None:
    session = FakeSession()
    notes_retriever = AsyncMock()
    notes_retriever.retrieve.return_value = [
        RetrievedDocument(content="Semantic note", score=0.9, metadata={})
    ]
    service = MemoryService(  # type: ignore[arg-type]
        session,
        embeddings=FakeEmbeddings(),
        vectors=AsyncMock(),
        notes_retriever=notes_retriever,
    )

    notes = await service.load_workspace_notes(
        workspace_id=uuid4(),
        space_id=uuid4(),
        query="coffee launch",
    )

    assert notes == ["Semantic note"]
    notes_retriever.retrieve.assert_awaited_once()
