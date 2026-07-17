"""Request and response contracts for multi-agent workflows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LaunchStrategyRequest(BaseModel):
    workspace_id: UUID
    brief: str = Field(min_length=8, max_length=8_000)
    product_name: str | None = Field(default=None, max_length=200)


class WorkflowArtifactResponse(BaseModel):
    id: UUID
    kind: str
    title: str
    content_md: str
    document_id: UUID | None = None
    created_at: datetime


class WorkflowRunResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    workflow_type: str
    status: str
    brief: str
    product_name: str | None
    error: str | None = None
    model: str | None = None
    pack_filename: str | None = None
    document_id: UUID | None = None
    artifacts: list[WorkflowArtifactResponse]
    created_at: datetime
    updated_at: datetime
