"""RAG assistant API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AssistantQuery(BaseModel):
    """One workspace-grounded question, optionally continuing a conversation."""

    workspace_id: UUID
    question: str = Field(min_length=1, max_length=4_000)
    conversation_id: UUID | None = None


class AssistantSource(BaseModel):
    """Retrieved source cited by the assistant."""

    citation: int
    document_id: str | None
    filename: str | None
    chunk_index: int | None
    score: float


class AssistantResponse(BaseModel):
    """Grounded assistant answer and its retrieval evidence."""

    answer: str
    sources: list[AssistantSource]
    model: str
    conversation_id: UUID


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationMessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime
