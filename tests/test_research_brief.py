"""Research Brief workflow tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.rag.retriever import RetrievedDocument
from app.workflows.research_brief import (
    ResearchBriefWorkflow,
    assemble_research_brief,
)


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


class FakePersister:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.document_id = uuid4()

    async def persist_markdown(
        self,
        *,
        workspace_id: object,
        filename: str,
        content: str,
    ) -> object:
        self.calls.append((filename, content))
        return self.document_id


def create_sequenced_client(responses: list[str]) -> SimpleNamespace:
    create = AsyncMock(
        side_effect=[
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
            )
            for text in responses
        ]
    )
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


def test_assemble_research_brief() -> None:
    pack = assemble_research_brief(
        product_name="Aussie Coffee",
        brief="Open cafes",
        research_md="Demand is growing",
        competitors_md="Local chains",
    )
    assert "# Research Brief — Aussie Coffee" in pack
    assert "Demand is growing" in pack
    assert "Local chains" in pack


@pytest.mark.asyncio
async def test_research_brief_runs_and_persists() -> None:
    persister = FakePersister()
    client = create_sequenced_client(
        [
            "```research\nCoffee demand\n```\n```competitors\nLocal rivals\n```",
        ]
    )
    workflow = ResearchBriefWorkflow(
        FakeRetriever(
            [
                RetrievedDocument(
                    content="Existing cafe notes",
                    score=0.8,
                    metadata={"filename": "notes.md"},
                )
            ]
        ),
        persister,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        config=Settings(
            openrouter_model="google/gemini-3.5-flash",
            web_search_enabled=False,
        ),
    )

    result = await workflow.invoke(
        workspace_id=str(uuid4()),
        space_id=str(uuid4()),
        brief="I want to open a network of coffee shops in Australia.",
        product_name="Aussie Roast",
    )

    assert result.product_name == "Aussie Roast"
    assert result.document_id == persister.document_id
    assert len(result.artifacts) == 3
    assert result.artifacts[0].content_md == "Coffee demand"
    assert result.artifacts[1].kind == "competitors"
    assert "Local rivals" in result.artifacts[1].content_md
    assert result.artifacts[2].kind == "pack"
    assert persister.calls
    assert "research-brief-" in persister.calls[0][0]
    assert "Coffee demand" in persister.calls[0][1]
    assert client.chat.completions.create.await_count == 1
