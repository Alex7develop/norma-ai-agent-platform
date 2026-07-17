"""RAG assistant entry point backed by a compiled LangGraph workflow."""

from app.workflows.rag_assistant import RagAssistant, RagAssistantResult


class RagAssistantAgent:
    """Expose the first auditable Norma AI agent use case."""

    def __init__(self, workflow: RagAssistant) -> None:
        self.workflow = workflow

    async def answer(
        self,
        *,
        workspace_id: str,
        question: str,
    ) -> RagAssistantResult:
        """Answer one question using only scoped retrieved knowledge."""

        return await self.workflow.invoke(
            workspace_id=workspace_id,
            question=question,
        )
