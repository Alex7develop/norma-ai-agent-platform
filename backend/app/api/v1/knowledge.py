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

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


def get_knowledge_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeService:
    """Compose the application service with request-scoped persistence."""

    return KnowledgeService(session)


@router.get("/documents", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: UUID,
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentResponse]:
    """List indexed documents for one workspace."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    documents = await service.list_documents(workspace_id=workspace_id)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    service: Annotated[KnowledgeService, Depends(get_knowledge_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentResponse:
    """Synchronously parse and index one bounded document."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")
    data = await file.read(settings.max_upload_size_bytes + 1)
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Document size limit exceeded")

    try:
        result = await service.ingest(
            workspace_id=workspace_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except KnowledgeIngestionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return DocumentResponse.model_validate(result)


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
