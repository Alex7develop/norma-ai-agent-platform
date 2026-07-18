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
from app.rag.container import embedding_provider, retriever, vector_store
from app.rag.embeddings import EmbeddingProvider
from app.rag.retriever import Retriever
from app.rag.vectorstore import VectorRecord, VectorStore


class ConversationNotFound(LookupError):
    """Raised when a conversation is missing or outside the workspace."""


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: str
    content: str


class MemoryService:
    """Application service for chat history and workspace notes."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        embeddings: EmbeddingProvider = embedding_provider,
        vectors: VectorStore = vector_store,
        notes_retriever: Retriever = retriever,
    ) -> None:
        self.session = session
        self.embeddings = embeddings
        self.vectors = vectors
        self.notes_retriever = notes_retriever

    async def get_or_create_conversation(
        self,
        *,
        workspace_id: UUID,
        space_id: UUID,
        user_id: UUID,
        conversation_id: UUID | None,
        title_seed: str,
    ) -> Conversation:
        if conversation_id is not None:
            conversation = await self.session.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.workspace_id == workspace_id,
                    Conversation.space_id == space_id,
                    Conversation.user_id == user_id,
                )
            )
            if conversation is None:
                raise ConversationNotFound("Conversation not found")
            return conversation

        title = title_seed.strip().splitlines()[0][:120] or "Conversation"
        conversation = Conversation(
            workspace_id=workspace_id,
            space_id=space_id,
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
        space_id: UUID,
        run_id: UUID,
        summary_md: str,
    ) -> WorkspaceMemory:
        content = summary_md.strip()
        memory = WorkspaceMemory(
            workspace_id=workspace_id,
            space_id=space_id,
            kind=MemoryKind.WORKFLOW_SUMMARY,
            content=content,
            source_run_id=run_id,
        )
        self.session.add(memory)
        await self.session.flush()
        try:
            vector = await self.embeddings.embed_query(content)
            await self.vectors.upsert(
                [
                    VectorRecord(
                        id=str(memory.id),
                        vector=vector,
                        metadata={
                            "source_type": "memory",
                            "workspace_id": str(workspace_id),
                            "space_id": str(space_id),
                            "memory_id": str(memory.id),
                            "kind": memory.kind.value,
                            "content": content,
                        },
                    )
                ]
            )
        except Exception:
            # Relational memory remains useful even if embedding fails.
            pass
        return memory

    async def load_workspace_notes(
        self,
        *,
        workspace_id: UUID,
        space_id: UUID | None = None,
        query: str | None = None,
        limit: int = 5,
    ) -> list[str]:
        if query:
            try:
                hits = await self.notes_retriever.retrieve(
                    query,
                    workspace_id=str(workspace_id),
                    space_id=str(space_id) if space_id else None,
                    source_type="memory",
                    limit=limit,
                )
                notes = [hit.content for hit in hits if hit.content.strip()]
                if notes:
                    return notes
            except Exception:
                pass

        filters = [WorkspaceMemory.workspace_id == workspace_id]
        if space_id is not None:
            filters.append(WorkspaceMemory.space_id == space_id)
        rows = (
            await self.session.scalars(
                select(WorkspaceMemory)
                .where(*filters)
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
        space_id: UUID | None = None,
    ) -> list[Conversation]:
        filters = [
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == user_id,
        ]
        if space_id is not None:
            filters.append(Conversation.space_id == space_id)
        rows = (
            await self.session.scalars(
                select(Conversation)
                .where(*filters)
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
