"""RAG assistant API schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class AssistantQuery(BaseModel):
    """One stateless workspace-grounded question."""

    workspace_id: UUID
    question: str = Field(min_length=1, max_length=4_000)


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
