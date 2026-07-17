"""Multi-agent workflow endpoints."""

import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAIError
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_workspace_access
from app.database.auth_models import User
from app.database.session import get_db_session
from app.database.workflow_models import WorkflowArtifact, WorkflowRun
from app.rag.container import retriever
from app.rag.embeddings import EmbeddingServiceError
from app.schemas.workflows import (
    LaunchStrategyRequest,
    WorkflowArtifactResponse,
    WorkflowRunResponse,
)
from app.services.knowledge import KnowledgeIngestionError, KnowledgeService
from app.services.launch_strategy import (
    KnowledgeIngestAdapter,
    LaunchStrategyService,
    WorkflowRunNotFound,
)
from app.services.llm import OpenRouterConfigurationError
from app.services.memory import MemoryService
from app.workflows.launch_strategy import LaunchStrategyWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_knowledge_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeService:
    return KnowledgeService(session)


def get_memory_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MemoryService:
    return MemoryService(session)


def get_workflow_reader(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LaunchStrategyService:
    return LaunchStrategyService(session)


async def get_launch_strategy_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    knowledge: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    memory: Annotated[MemoryService, Depends(get_memory_service)],
) -> AsyncIterator[LaunchStrategyService]:
    try:
        workflow = LaunchStrategyWorkflow(
            retriever,
            KnowledgeIngestAdapter(knowledge),
        )
    except OpenRouterConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        yield LaunchStrategyService(
            session,
            workflow=workflow,
            knowledge=knowledge,
            memory=memory,
        )
    finally:
        await workflow.client.close()


def _artifact_response(artifact: WorkflowArtifact) -> WorkflowArtifactResponse:
    return WorkflowArtifactResponse(
        id=artifact.id,
        kind=artifact.kind.value,
        title=artifact.title,
        content_md=artifact.content_md,
        document_id=artifact.document_id,
        created_at=artifact.created_at,
    )


def _run_response(
    run: WorkflowRun,
    *,
    model: str | None = None,
) -> WorkflowRunResponse:
    pack = next((item for item in run.artifacts if item.kind.value == "pack"), None)
    return WorkflowRunResponse(
        id=run.id,
        workspace_id=run.workspace_id,
        workflow_type=run.workflow_type,
        status=run.status.value,
        brief=run.brief,
        product_name=run.product_name,
        error=run.error,
        model=model,
        pack_filename=pack.title if pack else None,
        document_id=pack.document_id if pack else None,
        artifacts=[_artifact_response(item) for item in run.artifacts],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/launch-strategy", response_model=WorkflowRunResponse)
async def run_launch_strategy(
    payload: LaunchStrategyRequest,
    service: Annotated[LaunchStrategyService, Depends(get_launch_strategy_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> WorkflowRunResponse:
    """Run research → planning → execution and save the pack into knowledge."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    try:
        run, model = await service.run(
            workspace_id=payload.workspace_id,
            user_id=user.id,
            brief=payload.brief,
            product_name=payload.product_name,
        )
    except OpenAIError as exc:
        logger.exception("Launch strategy LLM request failed")
        raise HTTPException(
            status_code=502, detail="Language model request failed"
        ) from exc
    except KnowledgeIngestionError as exc:
        logger.exception("Launch strategy knowledge ingest failed")
        raise HTTPException(
            status_code=502, detail="Failed to save pack into knowledge"
        ) from exc
    except (
        EmbeddingServiceError,
        ResponseHandlingException,
        UnexpectedResponse,
    ) as exc:
        logger.exception("Launch strategy retrieval/indexing failed")
        raise HTTPException(
            status_code=503, detail="Knowledge infrastructure failed"
        ) from exc

    return _run_response(run, model=model)


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[LaunchStrategyService, Depends(get_workflow_reader)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> WorkflowRunResponse:
    """Load one workspace-scoped workflow run with artifacts."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        run = await service.get_run(run_id=run_id, workspace_id=workspace_id)
    except WorkflowRunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _run_response(run)
