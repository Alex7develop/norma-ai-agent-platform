"""Multi-agent workflow endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_workspace_access
from app.database.auth_models import User
from app.database.session import get_db_session
from app.database.workflow_models import WorkflowArtifact, WorkflowRun
from app.schemas.workflows import (
    LaunchStrategyRequest,
    WorkflowArtifactResponse,
    WorkflowRunResponse,
    WorkflowRunSummary,
)
from app.services.launch_strategy import LaunchStrategyService, WorkflowRunNotFound
from app.services.projects import ProjectService, SpaceNotFound
from app.services.queue import JobQueue
from app.workflows.launch_strategy import LaunchStrategyWorkflow
from app.workflows.research_brief import ResearchBriefWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LaunchStrategyService:
    return LaunchStrategyService(session, queue=JobQueue())


async def _enqueue_workflow(
    *,
    payload: LaunchStrategyRequest,
    service: LaunchStrategyService,
    session: AsyncSession,
    user: User,
    workflow_type: str,
) -> WorkflowRunResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    projects = ProjectService(session)
    try:
        if payload.space_id is None:
            space_id = await projects.default_space_id(
                workspace_id=payload.workspace_id, user_id=user.id
            )
        else:
            await projects.require_space(
                space_id=payload.space_id, workspace_id=payload.workspace_id
            )
            space_id = payload.space_id
        run = await service.enqueue(
            workspace_id=payload.workspace_id,
            user_id=user.id,
            brief=payload.brief,
            product_name=payload.product_name,
            space_id=space_id,
            workflow_type=workflow_type,
        )
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to enqueue %s", workflow_type)
        raise HTTPException(
            status_code=503, detail="Failed to enqueue workflow job"
        ) from exc

    return _run_response(run)


def _artifact_response(artifact: WorkflowArtifact) -> WorkflowArtifactResponse:
    return WorkflowArtifactResponse(
        id=artifact.id,
        kind=artifact.kind.value,
        title=artifact.title,
        content_md=artifact.content_md,
        document_id=artifact.document_id,
        created_at=artifact.created_at,
    )


def _run_response(run: WorkflowRun) -> WorkflowRunResponse:
    pack = next((item for item in run.artifacts if item.kind.value == "pack"), None)
    return WorkflowRunResponse(
        id=run.id,
        workspace_id=run.workspace_id,
        workflow_type=run.workflow_type,
        status=run.status.value,
        brief=run.brief,
        product_name=run.product_name,
        current_step=run.current_step,
        error=run.error,
        pack_filename=pack.title if pack else None,
        document_id=pack.document_id if pack else None,
        artifacts=[_artifact_response(item) for item in run.artifacts],
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _run_summary(run: WorkflowRun) -> WorkflowRunSummary:
    return WorkflowRunSummary(
        id=run.id,
        workspace_id=run.workspace_id,
        workflow_type=run.workflow_type,
        status=run.status.value,
        brief=run.brief,
        product_name=run.product_name,
        current_step=run.current_step,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post(
    "/launch-strategy",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_launch_strategy(
    payload: LaunchStrategyRequest,
    service: Annotated[LaunchStrategyService, Depends(get_workflow_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> WorkflowRunResponse:
    """Enqueue Launch Strategy and return immediately for polling."""

    return await _enqueue_workflow(
        payload=payload,
        service=service,
        session=session,
        user=user,
        workflow_type=LaunchStrategyWorkflow.WORKFLOW_TYPE,
    )


@router.post(
    "/research-brief",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_research_brief(
    payload: LaunchStrategyRequest,
    service: Annotated[LaunchStrategyService, Depends(get_workflow_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> WorkflowRunResponse:
    """Enqueue Research Brief and return immediately for polling."""

    return await _enqueue_workflow(
        payload=payload,
        service=service,
        session=session,
        user=user,
        workflow_type=ResearchBriefWorkflow.WORKFLOW_TYPE,
    )


@router.get("/runs", response_model=list[WorkflowRunSummary])
async def list_workflow_runs(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[LaunchStrategyService, Depends(get_workflow_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    space_id: Annotated[UUID | None, Query()] = None,
) -> list[WorkflowRunSummary]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    runs = await service.list_runs(
        workspace_id=workspace_id,
        limit=limit,
        space_id=space_id,
    )
    return [_run_summary(run) for run in runs]


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: UUID,
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[LaunchStrategyService, Depends(get_workflow_service)],
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
