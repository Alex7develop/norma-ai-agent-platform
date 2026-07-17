"""LangGraph coordinator for the Launch Strategy multi-agent pack."""

from dataclasses import dataclass
from typing import Any, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from openai import AsyncOpenAI

from app.agents.content import ContentAgent
from app.agents.execution import ExecutionAgent, KnowledgePersister, assemble_pack
from app.agents.planning import PlanningAgent
from app.agents.research import ResearchAgent
from app.agents.spec import SpecAgent
from app.core.config import Settings, settings
from app.rag.retriever import Retriever
from app.services.llm import create_openrouter_client


class LaunchStrategyState(TypedDict):
    """Serializable state passed between coordinator nodes."""

    workspace_id: str
    brief: str
    product_name: str
    context_chunks: list[str]
    research_md: str
    competitors_md: str
    positioning_md: str
    roadmap_md: str
    marketing_md: str
    business_model_md: str
    financial_md: str
    prd_md: str
    tech_spec_md: str
    cursor_prompts_md: str
    linkedin_md: str
    telegram_md: str
    pack_md: str
    pack_filename: str
    document_id: str


@dataclass(frozen=True, slots=True)
class LaunchStrategyArtifact:
    kind: str
    title: str
    content_md: str
    document_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class LaunchStrategyResult:
    """Transport-neutral coordinator result."""

    product_name: str
    pack_filename: str
    document_id: UUID
    artifacts: list[LaunchStrategyArtifact]
    model: str


_EMPTY_STATE_FIELDS = {
    "context_chunks": [],
    "research_md": "",
    "competitors_md": "",
    "positioning_md": "",
    "roadmap_md": "",
    "marketing_md": "",
    "business_model_md": "",
    "financial_md": "",
    "prd_md": "",
    "tech_spec_md": "",
    "cursor_prompts_md": "",
    "linkedin_md": "",
    "telegram_md": "",
    "pack_md": "",
    "pack_filename": "",
    "document_id": "",
}


class LaunchStrategyWorkflow:
    """Coordinate research, planning, spec, content, and execution agents."""

    WORKFLOW_TYPE = "launch_strategy"

    def __init__(
        self,
        retriever: Retriever,
        persister: KnowledgePersister,
        *,
        client: AsyncOpenAI | None = None,
        config: Settings = settings,
    ) -> None:
        self.retriever = retriever
        self.persister = persister
        self.client = client or create_openrouter_client(config)
        self.config = config
        self.research = ResearchAgent(self.client, config=config)
        self.planning = PlanningAgent(self.client, config=config)
        self.spec = SpecAgent(self.client, config=config)
        self.content = ContentAgent(self.client, config=config)
        self.execution = ExecutionAgent(persister)
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        builder = StateGraph(LaunchStrategyState)
        builder.add_node("retrieve_context", self._retrieve_context)
        builder.add_node("research_synthesize", self.research.invoke)
        builder.add_node("draft_pack", self.planning.invoke)
        builder.add_node("draft_specs", self.spec.invoke)
        builder.add_node("draft_content", self.content.invoke)
        builder.add_node("assemble_and_persist", self.execution.invoke)
        builder.add_edge(START, "retrieve_context")
        builder.add_edge("retrieve_context", "research_synthesize")
        builder.add_edge("research_synthesize", "draft_pack")
        builder.add_edge("draft_pack", "draft_specs")
        builder.add_edge("draft_specs", "draft_content")
        builder.add_edge("draft_content", "assemble_and_persist")
        builder.add_edge("assemble_and_persist", END)
        return builder.compile()

    async def _retrieve_context(self, state: LaunchStrategyState) -> dict[str, Any]:
        documents = await self.retriever.retrieve(
            state["brief"],
            workspace_id=state["workspace_id"],
            limit=6,
        )
        return {
            "context_chunks": [document.content for document in documents],
        }

    async def invoke(
        self,
        *,
        workspace_id: str,
        brief: str,
        product_name: str | None = None,
    ) -> LaunchStrategyResult:
        """Run the coordinator graph and return structured artifacts."""

        resolved_name = (product_name or "").strip() or _default_product_name(brief)
        result = await self.graph.ainvoke(
            {
                "workspace_id": workspace_id,
                "brief": brief.strip(),
                "product_name": resolved_name,
                **_EMPTY_STATE_FIELDS,
            }
        )
        document_id = UUID(result["document_id"])
        pack_kwargs = {
            "product_name": resolved_name,
            "brief": brief,
            "research_md": result["research_md"],
            "competitors_md": result["competitors_md"],
            "positioning_md": result["positioning_md"],
            "roadmap_md": result["roadmap_md"],
            "marketing_md": result["marketing_md"],
            "business_model_md": result["business_model_md"],
            "financial_md": result["financial_md"],
            "prd_md": result["prd_md"],
            "tech_spec_md": result["tech_spec_md"],
            "cursor_prompts_md": result["cursor_prompts_md"],
            "linkedin_md": result["linkedin_md"],
            "telegram_md": result["telegram_md"],
        }
        pack_md = result["pack_md"] or assemble_pack(**pack_kwargs)
        artifacts = [
            LaunchStrategyArtifact(
                "research", "Market research", result["research_md"]
            ),
            LaunchStrategyArtifact(
                "competitors", "Competitors", result["competitors_md"]
            ),
            LaunchStrategyArtifact(
                "positioning", "Positioning", result["positioning_md"]
            ),
            LaunchStrategyArtifact("roadmap", "Roadmap", result["roadmap_md"]),
            LaunchStrategyArtifact(
                "marketing", "Marketing outline", result["marketing_md"]
            ),
            LaunchStrategyArtifact(
                "business_model", "Business model", result["business_model_md"]
            ),
            LaunchStrategyArtifact(
                "financial", "Financial model", result["financial_md"]
            ),
            LaunchStrategyArtifact("prd", "PRD", result["prd_md"]),
            LaunchStrategyArtifact(
                "tech_spec", "Technical specification", result["tech_spec_md"]
            ),
            LaunchStrategyArtifact(
                "cursor_prompts", "Cursor prompts", result["cursor_prompts_md"]
            ),
            LaunchStrategyArtifact(
                "linkedin", "LinkedIn content", result["linkedin_md"]
            ),
            LaunchStrategyArtifact(
                "telegram", "Telegram content", result["telegram_md"]
            ),
            LaunchStrategyArtifact(
                "pack",
                result["pack_filename"] or "Launch strategy pack",
                pack_md,
                document_id,
            ),
        ]
        return LaunchStrategyResult(
            product_name=resolved_name,
            pack_filename=result["pack_filename"],
            document_id=document_id,
            artifacts=artifacts,
            model=self.config.openrouter_model,
        )


def _default_product_name(brief: str) -> str:
    first_line = brief.strip().splitlines()[0] if brief.strip() else "Initiative"
    cleaned = first_line.strip().rstrip(".")
    if len(cleaned) > 80:
        return cleaned[:77].rstrip() + "..."
    return cleaned or "Initiative"
