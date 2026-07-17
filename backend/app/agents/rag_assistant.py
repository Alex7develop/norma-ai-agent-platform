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
        chat_context: list[dict[str, str]] | None = None,
        workspace_notes: list[str] | None = None,
    ) -> RagAssistantResult:
        """Answer one question using scoped knowledge and optional memory."""

        return await self.workflow.invoke(
            workspace_id=workspace_id,
            question=question,
            chat_context=chat_context,
            workspace_notes=workspace_notes,
        )
