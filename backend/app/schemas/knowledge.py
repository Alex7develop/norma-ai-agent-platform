"""Knowledge ingestion and retrieval API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Indexed document metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    chunk_count: int
    created_at: datetime


class SearchRequest(BaseModel):
    """Workspace-scoped semantic search request."""

    workspace_id: UUID
    query: str = Field(min_length=1, max_length=4_000)
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    """One ranked document chunk."""

    content: str
    score: float
    metadata: dict[str, Any]


class SearchResponse(BaseModel):
    """Ranked retrieval response."""

    results: list[SearchResult]
