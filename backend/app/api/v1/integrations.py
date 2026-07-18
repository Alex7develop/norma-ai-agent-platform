"""Third-party integration endpoints (Notion OAuth + import)."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_workspace_access
from app.core.config import settings
from app.database.auth_models import User
from app.database.session import get_db_session
from app.schemas.integrations import (
    NotionAuthorizeResponse,
    NotionImportItem,
    NotionImportRequest,
    NotionImportResponse,
    NotionPageResponse,
    NotionStatusResponse,
)
from app.services.knowledge import KnowledgeService
from app.services.notion import (
    NotionAPIError,
    NotionClient,
    NotionConfigurationError,
    NotionIntegrationService,
    NotionNotConnected,
    build_authorize_url,
    create_oauth_state,
    exchange_code_for_token,
    parse_oauth_state,
)
from app.services.projects import ProjectService, SpaceNotFound
from app.services.queue import JobQueue

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_notion_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NotionIntegrationService:
    return NotionIntegrationService(session)


def get_knowledge_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeService:
    return KnowledgeService(session, queue=JobQueue())


@router.get("/notion/authorize", response_model=NotionAuthorizeResponse)
async def notion_authorize(
    workspace_id: Annotated[UUID, Query()],
    space_id: Annotated[UUID, Query()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> NotionAuthorizeResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    projects = ProjectService(session)
    try:
        await projects.require_space(space_id=space_id, workspace_id=workspace_id)
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        state = create_oauth_state(
            user_id=user.id,
            workspace_id=workspace_id,
            space_id=space_id,
        )
        url = build_authorize_url(state=state)
    except NotionConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return NotionAuthorizeResponse(authorize_url=url)


@router.get("/notion/callback")
async def notion_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    _session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RedirectResponse:
    frontend = settings.frontend_origin.rstrip("/")
    try:
        claims = parse_oauth_state(state)
        token_payload = await exchange_code_for_token(code)
        access_token = str(token_payload["access_token"])
        await service.upsert_connection(
            user_id=claims.user_id,
            workspace_id=claims.workspace_id,
            access_token=access_token,
            external_workspace_id=str(token_payload.get("workspace_id") or "")
            or None,
            external_workspace_name=str(token_payload.get("workspace_name") or "")
            or None,
        )
    except (ValueError, NotionConfigurationError, NotionAPIError) as exc:
        logger.exception("Notion OAuth callback failed")
        return RedirectResponse(
            url=f"{frontend}/?notion=error&detail={type(exc).__name__}",
            status_code=status.HTTP_302_FOUND,
        )
    return RedirectResponse(
        url=f"{frontend}/?notion=connected",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/notion/status", response_model=NotionStatusResponse)
async def notion_status(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> NotionStatusResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    connection = await service.get_connection(
        user_id=user.id, workspace_id=workspace_id
    )
    if connection is None:
        return NotionStatusResponse(connected=False)
    return NotionStatusResponse(
        connected=True,
        workspace_name=connection.external_workspace_name,
        workspace_id=connection.external_workspace_id,
    )


@router.delete("/notion", status_code=status.HTTP_204_NO_CONTENT)
async def notion_disconnect(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        await service.disconnect(user_id=user.id, workspace_id=workspace_id)
    except NotionNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/notion/pages", response_model=list[NotionPageResponse])
async def notion_pages(
    workspace_id: Annotated[UUID, Query()],
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[NotionPageResponse]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        token = await service.access_token(user_id=user.id, workspace_id=workspace_id)
    except NotionNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        async with NotionClient(token) as client:
            pages = await client.search_pages()
    except NotionAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [NotionPageResponse(id=page.id, title=page.title) for page in pages]


@router.post(
    "/notion/import",
    response_model=NotionImportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def notion_import(
    payload: NotionImportRequest,
    service: Annotated[NotionIntegrationService, Depends(get_notion_service)],
    knowledge: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> NotionImportResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    projects = ProjectService(session)
    try:
        await projects.require_space(
            space_id=payload.space_id, workspace_id=payload.workspace_id
        )
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        token = await service.access_token(
            user_id=user.id, workspace_id=payload.workspace_id
        )
    except NotionNotConnected as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    items: list[NotionImportItem] = []
    try:
        async with NotionClient(token) as client:
            for page_id in payload.page_ids:
                try:
                    filename, markdown = await client.export_page_markdown(page_id)
                    document = await knowledge.enqueue(
                        workspace_id=payload.workspace_id,
                        space_id=payload.space_id,
                        filename=filename,
                        content_type="text/markdown",
                        data=markdown.encode("utf-8"),
                    )
                    items.append(
                        NotionImportItem(
                            page_id=page_id,
                            document_id=document.id,
                            filename=filename,
                            status="pending",
                        )
                    )
                except Exception as exc:
                    logger.exception("Failed to import Notion page %s", page_id)
                    items.append(
                        NotionImportItem(
                            page_id=page_id,
                            status="failed",
                            error=f"{type(exc).__name__}: import failed",
                        )
                    )
    except NotionAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return NotionImportResponse(items=items)
