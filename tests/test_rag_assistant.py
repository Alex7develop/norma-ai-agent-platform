"""LangGraph RAG assistant workflow tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.rag.retriever import RetrievedDocument
from app.workflows.rag_assistant import RagAssistant


class FakeRetriever:
    def __init__(self, documents: list[RetrievedDocument]) -> None:
        self.documents = documents

    async def retrieve(
        self,
        query: str,
        *,
        workspace_id: str,
        space_id: str | None = None,
        source_type: str | None = "document",
        limit: int = 10,
    ) -> list[RetrievedDocument]:
        return self.documents[:limit]


def create_fake_client(answer: str) -> SimpleNamespace:
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=answer))]
        )
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


@pytest.mark.asyncio
async def test_rag_assistant_generates_cited_answer() -> None:
    retriever = FakeRetriever(
        [
            RetrievedDocument(
                content="Qdrant stores Norma AI vectors.",
                score=0.91,
                metadata={
                    "document_id": "document-1",
                    "filename": "architecture.md",
                    "chunk_index": 2,
                },
            )
        ]
    )
    client = create_fake_client("Norma stores vectors in Qdrant [1].")
    assistant = RagAssistant(
        retriever,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        config=Settings(openrouter_model="google/gemini-3.5-flash"),
    )

    result = await assistant.invoke(
        workspace_id="workspace-1",
        question="Where are vectors stored?",
    )

    assert result.answer == "Norma stores vectors in Qdrant [1]."
    assert result.sources[0]["filename"] == "architecture.md"
    assert result.sources[0]["citation"] == 1
    client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_rag_assistant_skips_llm_without_context() -> None:
    client = create_fake_client("This must not be used")
    assistant = RagAssistant(
        FakeRetriever([]),  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
    )

    result = await assistant.invoke(
        workspace_id="workspace-1",
        question="Unknown question",
    )

    assert "could not find relevant information" in result.answer
    assert result.sources == []
    client.chat.completions.create.assert_not_awaited()
