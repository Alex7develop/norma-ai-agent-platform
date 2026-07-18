"""Workspace-scoped knowledge ingestion and retrieval endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_workspace_access
from app.core.config import settings
from app.database.auth_models import User
from app.database.session import get_db_session
from app.rag.container import retriever
from app.rag.document_processing import DocumentProcessingError
from app.schemas.knowledge import (
    DocumentResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.knowledge import (
    KnowledgeDocumentNotFound,
    KnowledgeIngestionError,
    KnowledgeService,
)
from app.services.projects import ProjectService, SpaceNotFound
from app.services.queue import JobQueue

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeService:
    """Compose the application service with request-scoped persistence."""

    return KnowledgeService(session, queue=JobQueue())


def _document_response(result: object) -> DocumentResponse:
    return DocumentResponse.model_validate(result)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: UUID,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    space_id: UUID | None = None,
) -> list[DocumentResponse]:
    """List indexed documents for one workspace/space."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    documents = await service.list_documents(
        workspace_id=workspace_id, space_id=space_id
    )
    return [_document_response(document) for document in documents]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    workspace_id: UUID,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentResponse:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        result = await service.get_document(
            workspace_id=workspace_id, document_id=document_id
        )
    except KnowledgeDocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _document_response(result)


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    workspace_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    space_id: Annotated[UUID | None, Form()] = None,
) -> DocumentResponse:
    """Enqueue document indexing and return immediately for polling."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    projects = ProjectService(session)
    try:
        resolved_space = (
            space_id
            if space_id is not None
            else await projects.default_space_id(
                workspace_id=workspace_id, user_id=user.id
            )
        )
        if space_id is not None:
            await projects.require_space(
                space_id=space_id, workspace_id=workspace_id
            )
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")
    data = await file.read(settings.max_upload_size_bytes + 1)
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Document size limit exceeded")

    try:
        result = await service.enqueue(
            workspace_id=workspace_id,
            space_id=resolved_space,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KnowledgeIngestionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail="Failed to enqueue document ingest"
        ) from exc
    return _document_response(result)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: UUID,
    workspace_id: UUID,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete a document only inside its workspace namespace."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        await service.delete(workspace_id=workspace_id, document_id=document_id)
    except KnowledgeDocumentNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> SearchResponse:
    """Return semantic chunks scoped to one workspace."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    results = await retriever.retrieve(
        payload.query,
        workspace_id=str(payload.workspace_id),
        space_id=str(payload.space_id) if payload.space_id else None,
        limit=payload.limit,
    )
    return SearchResponse(
        results=[
            SearchResult(
                content=result.content,
                score=result.score,
                metadata=result.metadata,
            )
            for result in results
        ]
    )
