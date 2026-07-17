"""Persist and load conversation turns and workspace memory notes."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.memory_models import (
    Conversation,
    ConversationMessage,
    MemoryKind,
    MessageRole,
    WorkspaceMemory,
)


class ConversationNotFound(LookupError):
    """Raised when a conversation is missing or outside the workspace."""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: str
    content: str


class MemoryService:
    """Application service for chat history and workspace notes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_conversation(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
        title_seed: str,
    ) -> Conversation:
        if conversation_id is not None:
            conversation = await self.session.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.workspace_id == workspace_id,
                    Conversation.user_id == user_id,
                )
            )
            if conversation is None:
                raise ConversationNotFound("Conversation not found")
            return conversation

        title = title_seed.strip().splitlines()[0][:120] or "Conversation"
        conversation = Conversation(
            workspace_id=workspace_id,
            user_id=user_id,
            title=title,
        )
        self.session.add(conversation)
        await self.session.flush()
        return conversation

    async def load_chat_context(
        self,
        *,
        conversation_id: UUID,
        limit: int = 12,
    ) -> list[ChatTurn]:
        rows = (
            await self.session.scalars(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conversation_id)
                .order_by(ConversationMessage.created_at.desc())
                .limit(limit)
            )
        ).all()
        ordered = list(reversed(rows))
        return [
            ChatTurn(role=message.role.value, content=message.content)
            for message in ordered
        ]

    async def append_turn(
        self,
        *,
        conversation_id: UUID,
        user_content: str,
        assistant_content: str,
    ) -> None:
        now = datetime.now(UTC)
        self.session.add_all(
            [
                ConversationMessage(
                    conversation_id=conversation_id,
                    role=MessageRole.USER,
                    content=user_content,
                    created_at=now,
                ),
                ConversationMessage(
                    conversation_id=conversation_id,
                    role=MessageRole.ASSISTANT,
                    content=assistant_content,
                    created_at=now,
                ),
            ]
        )
        conversation = await self.session.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.updated_at = now
        await self.session.flush()

    async def remember_workflow_summary(
        self,
        *,
        workspace_id: UUID,
        run_id: UUID,
        summary_md: str,
    ) -> WorkspaceMemory:
        memory = WorkspaceMemory(
            workspace_id=workspace_id,
            kind=MemoryKind.WORKFLOW_SUMMARY,
            content=summary_md.strip(),
            source_run_id=run_id,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def load_workspace_notes(
        self,
        *,
        workspace_id: UUID,
        limit: int = 5,
    ) -> list[str]:
        rows = (
            await self.session.scalars(
                select(WorkspaceMemory)
                .where(WorkspaceMemory.workspace_id == workspace_id)
                .order_by(WorkspaceMemory.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [row.content for row in rows]

    async def list_conversations(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[Conversation]:
        rows = (
            await self.session.scalars(
                select(Conversation)
                .where(
                    Conversation.workspace_id == workspace_id,
                    Conversation.user_id == user_id,
                )
                .order_by(Conversation.updated_at.desc())
            )
        ).all()
        return list(rows)

    async def list_messages(
        self,
        *,
        conversation_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[ConversationMessage]:
        conversation = await self.session.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
                Conversation.user_id == user_id,
            )
        )
        if conversation is None:
            raise ConversationNotFound("Conversation not found")
        return list(conversation.messages)
