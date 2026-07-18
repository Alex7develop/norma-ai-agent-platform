"""Memory agent facade over the persistence-backed MemoryService."""

from typing import Any
from uuid import UUID

from app.services.memory import ChatTurn, MemoryService


class MemoryAgent:
    """Load and write conversational / workspace memory for other agents."""

    def __init__(self, service: MemoryService) -> None:
        self.service = service

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Protocol-compatible helper used by orchestration when needed."""

        action = state.get("action", "load")
        if action == "remember_workflow":
            memory = await self.service.remember_workflow_summary(
                workspace_id=UUID(str(state["workspace_id"])),
                space_id=UUID(str(state["space_id"])),
                run_id=UUID(str(state["run_id"])),
                summary_md=str(state["summary_md"]),
            )
            return {"memory_id": str(memory.id)}

        conversation_id = state.get("conversation_id")
        space_id = state.get("space_id")
        chat: list[ChatTurn] = []
        if conversation_id:
            chat = await self.service.load_chat_context(
                conversation_id=UUID(str(conversation_id)),
                limit=int(state.get("chat_limit", 12)),
            )
        notes = await self.service.load_workspace_notes(
            workspace_id=UUID(str(state["workspace_id"])),
            space_id=UUID(str(space_id)) if space_id else None,
            limit=int(state.get("notes_limit", 5)),
        )
        return {
            "chat_context": [
                {"role": turn.role, "content": turn.content} for turn in chat
            ],
            "workspace_notes": notes,
        }

    async def load_for_assistant(
        self,
        *,
        workspace_id: UUID,
        space_id: UUID,
        conversation_id: UUID | None,
        question: str | None = None,
    ) -> tuple[list[ChatTurn], list[str]]:
        chat: list[ChatTurn] = []
        if conversation_id is not None:
            chat = await self.service.load_chat_context(
                conversation_id=conversation_id
            )
        notes = await self.service.load_workspace_notes(
            workspace_id=workspace_id,
            space_id=space_id,
            query=question,
        )
        return chat, notes
