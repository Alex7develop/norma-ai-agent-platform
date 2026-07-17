"""Launch Strategy coordinator workflow tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.execution import assemble_pack
from app.agents.markdown_sections import split_fenced_sections
from app.core.config import Settings
from app.rag.retriever import RetrievedDocument
from app.workflows.launch_strategy import LaunchStrategyWorkflow


class FakeRetriever:
    def __init__(self, documents: list[RetrievedDocument]) -> None:
        self.documents = documents

    async def retrieve(
        self,
        query: str,
        *,
        workspace_id: str,
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


def test_split_fenced_sections() -> None:
    research, competitors = split_fenced_sections(
        "```research\nMarket A\n```\n```competitors\nRival B\n```",
        ("research", "competitors"),
    )
    assert research == "Market A"
    assert competitors == "Rival B"


def test_assemble_pack_includes_full_sections() -> None:
    pack = assemble_pack(
        product_name="Aussie Coffee",
        brief="Open cafes",
        research_md="Demand is growing",
        competitors_md="Local chains",
        positioning_md="Premium local",
        roadmap_md="Phase 1 Melbourne",
        marketing_md="Instagram first",
        business_model_md="Franchise hybrid",
        financial_md="Unit economics ranges",
        prd_md="MVP scope",
        tech_spec_md="API + RAG",
        cursor_prompts_md="Build intake form",
        linkedin_md="Launch post",
        telegram_md="Channel update",
    )
    assert "# Launch Strategy Pack — Aussie Coffee" in pack
    assert "Franchise hybrid" in pack
    assert "Build intake form" in pack
    assert "Channel update" in pack


@pytest.mark.asyncio
async def test_launch_strategy_runs_agents_and_persists() -> None:
    persister = FakePersister()
    client = create_sequenced_client(
        [
            "```research\nCoffee demand\n```\n```competitors\nLocal rivals\n```",
            (
                "```positioning\nNeighborhood premium\n```\n"
                "```roadmap\nMelbourne then Sydney\n```\n"
                "```marketing\nSoft launch + LinkedIn\n```"
            ),
            (
                "```business_model\nCompany-owned hubs\n```\n"
                "```financial\nCapex ranges\n```\n"
                "```prd\nMVP: 3 locations\n```\n"
                "```tech_spec\nPOS + CRM\n```"
            ),
            (
                "```cursor_prompts\nImplement store locator\n```\n"
                "```linkedin\nWe are expanding\n```\n"
                "```telegram\nSoft open next month\n```"
            ),
        ]
    )
    workflow = LaunchStrategyWorkflow(
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
        config=Settings(openrouter_model="google/gemini-3.5-flash"),
    )

    result = await workflow.invoke(
        workspace_id=str(uuid4()),
        brief="I want to open a network of coffee shops in Australia.",
        product_name="Aussie Roast",
    )

    assert result.product_name == "Aussie Roast"
    assert result.document_id == persister.document_id
    assert len(result.artifacts) == 13
    assert result.artifacts[0].content_md == "Coffee demand"
    assert result.artifacts[5].kind == "business_model"
    assert "Company-owned hubs" in result.artifacts[5].content_md
    assert result.artifacts[9].kind == "cursor_prompts"
    assert persister.calls
    assert "Implement store locator" in persister.calls[0][1]
    assert client.chat.completions.create.await_count == 4
