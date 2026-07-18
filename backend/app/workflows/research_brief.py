"""LangGraph coordinator for the Research Brief async workflow."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.agents.execution import KnowledgePersister
from app.agents.research import ResearchAgent
from app.core.config import Settings, settings
from app.rag.retriever import Retriever
from app.services.llm import create_openrouter_client

ProgressCallback = Callable[[str], Awaitable[None]]


class ResearchBriefState(TypedDict):
    """Serializable state passed between Research Brief nodes."""

    workspace_id: str
    space_id: str
    brief: str
    product_name: str
    context_chunks: list[str]
    research_md: str
    competitors_md: str
    pack_md: str
    pack_filename: str
    document_id: str


@dataclass(frozen=True, slots=True)
class ResearchBriefArtifact:
    kind: str
    title: str
    content_md: str
    document_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResearchBriefResult:
    """Transport-neutral Research Brief result."""

    product_name: str
    pack_filename: str
    document_id: UUID
    artifacts: list[ResearchBriefArtifact]
    model: str


_EMPTY_STATE_FIELDS = {
    "context_chunks": [],
    "research_md": "",
    "competitors_md": "",
    "pack_md": "",
    "pack_filename": "",
    "document_id": "",
}


class ResearchBriefWorkflow:
    """Coordinate retrieve → research → persist for a short research brief."""

    WORKFLOW_TYPE = "research_brief"

    def __init__(
        self,
        retriever: Retriever,
        persister: KnowledgePersister,
        *,
        client: AsyncOpenAI | None = None,
        config: Settings = settings,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.retriever = retriever
        self.persister = persister
        self.client = client or create_openrouter_client(config)
        self.config = config
        self.on_progress = on_progress
        self.research = ResearchAgent(self.client, config=config)
        self.graph = self._build_graph()

    async def _step(
        self,
        name: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self.on_progress is not None:
            await self.on_progress(name)
        return await handler(state)

    async def _node_retrieve(self, state: ResearchBriefState) -> dict[str, Any]:
        return await self._step("retrieve", self._retrieve_context, state)

    async def _node_research(self, state: ResearchBriefState) -> dict[str, Any]:
        return await self._step("research", self.research.invoke, state)

    async def _node_persist(self, state: ResearchBriefState) -> dict[str, Any]:
        return await self._step("persist", self._persist_brief, state)

    def _build_graph(self) -> Any:
        builder = StateGraph(ResearchBriefState)
        builder.add_node("retrieve_context", self._node_retrieve)
        builder.add_node("research_synthesize", self._node_research)
        builder.add_node("assemble_and_persist", self._node_persist)
        builder.add_edge(START, "retrieve_context")
        builder.add_edge("retrieve_context", "research_synthesize")
        builder.add_edge("research_synthesize", "assemble_and_persist")
        builder.add_edge("assemble_and_persist", END)
        return builder.compile()

    async def _retrieve_context(self, state: ResearchBriefState) -> dict[str, Any]:
        documents = await self.retriever.retrieve(
            state["brief"],
            workspace_id=state["workspace_id"],
            space_id=state.get("space_id") or None,
            limit=6,
        )
        return {
            "context_chunks": [document.content for document in documents],
        }

    async def _persist_brief(self, state: ResearchBriefState) -> dict[str, Any]:
        product_name = str(state["product_name"])
        pack_md = assemble_research_brief(
            product_name=product_name,
            brief=str(state["brief"]),
            research_md=str(state.get("research_md") or ""),
            competitors_md=str(state.get("competitors_md") or ""),
        )
        stamp = datetime.now(UTC).strftime("%Y%m%d")
        slug = _slugify(product_name)
        filename = f"research-brief-{slug}-{stamp}.md"
        document_id = await self.persister.persist_markdown(
            workspace_id=UUID(str(state["workspace_id"])),
            filename=filename,
            content=pack_md,
        )
        return {
            "pack_md": pack_md,
            "pack_filename": filename,
            "document_id": str(document_id),
        }

    async def invoke(
        self,
        *,
        workspace_id: str,
        brief: str,
        product_name: str | None = None,
        space_id: str | None = None,
    ) -> ResearchBriefResult:
        """Run the Research Brief graph and return structured artifacts."""

        resolved_name = (product_name or "").strip() or _default_product_name(brief)
        result = await self.graph.ainvoke(
            {
                "workspace_id": workspace_id,
                "space_id": space_id or "",
                "brief": brief.strip(),
                "product_name": resolved_name,
                **_EMPTY_STATE_FIELDS,
            }
        )
        document_id = UUID(result["document_id"])
        artifacts = [
            ResearchBriefArtifact(
                "research", "Market research", result["research_md"]
            ),
            ResearchBriefArtifact(
                "competitors", "Competitors", result["competitors_md"]
            ),
            ResearchBriefArtifact(
                "pack",
                result["pack_filename"] or "Research brief",
                result["pack_md"],
                document_id,
            ),
        ]
        return ResearchBriefResult(
            product_name=resolved_name,
            pack_filename=result["pack_filename"],
            document_id=document_id,
            artifacts=artifacts,
            model=self.config.openrouter_model,
        )


def assemble_research_brief(
    *,
    product_name: str,
    brief: str,
    research_md: str,
    competitors_md: str,
) -> str:
    """Merge research sections into one markdown brief."""

    return (
        f"# Research Brief — {product_name}\n\n"
        f"## Brief\n\n{brief.strip()}\n\n"
        f"## Market research\n\n{research_md.strip() or '_No research._'}\n\n"
        f"## Competitors\n\n{competitors_md.strip() or '_No competitors._'}\n"
    )


def _default_product_name(brief: str) -> str:
    first_line = brief.strip().splitlines()[0] if brief.strip() else "Initiative"
    cleaned = first_line.strip().rstrip(".")
    if len(cleaned) > 80:
        return cleaned[:77].rstrip() + "..."
    return cleaned or "Initiative"


def _slugify(value: str) -> str:
    slug = "".join(
        ch.lower() if ch.isalnum() else "-" for ch in value.strip()
    ).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:48] or "initiative"
