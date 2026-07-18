"""Application services for bounded document ingestion and retrieval."""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.database.document_models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentUpload,
)
from app.rag.container import embedding_provider, vector_store
from app.rag.document_processing import chunk_text, parse_document
from app.rag.embeddings import EmbeddingProvider
from app.rag.vectorstore import VectorRecord, VectorStore
from app.services.queue import JobQueue

logger = logging.getLogger(__name__)


class KnowledgeIngestionError(RuntimeError):
    """Raised when a valid document cannot be indexed."""


class KnowledgeDocumentNotFound(LookupError):
    """Raised when a scoped document does not exist."""


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    """Transport-neutral indexed document result."""

    id: UUID
    workspace_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    chunk_count: int
    created_at: datetime
    error: str | None = None


class KnowledgeService:
    """Coordinate parsers, relational metadata, embeddings, and vectors."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        embeddings: EmbeddingProvider = embedding_provider,
        vectors: VectorStore = vector_store,
        queue: JobQueue | None = None,
    ) -> None:
        self.session = session
        self.embeddings = embeddings
        self.vectors = vectors
        self.queue = queue or JobQueue()

    @staticmethod
    def _build_result(document: Document, chunk_count: int) -> IndexedDocument:
        return IndexedDocument(
            id=document.id,
            workspace_id=document.workspace_id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            sha256=document.sha256,
            status=document.status.value,
            chunk_count=chunk_count,
            created_at=document.created_at,
            error=document.error,
        )

    async def _to_result(self, document: Document) -> IndexedDocument:
        chunk_count = await self.session.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document.id
            )
        )
        return self._build_result(document, int(chunk_count or 0))

    async def list_documents(
        self,
        *,
        workspace_id: UUID,
        space_id: UUID | None = None,
    ) -> list[IndexedDocument]:
        """List newest documents inside one workspace/space."""

        filters = [Document.workspace_id == workspace_id]
        if space_id is not None:
            filters.append(Document.space_id == space_id)
        rows = (
            await self.session.execute(
                select(Document, func.count(DocumentChunk.id))
                .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
                .where(*filters)
                .group_by(Document.id)
                .order_by(Document.created_at.desc())
            )
        ).all()
        return [
            self._build_result(document, int(chunk_count))
            for document, chunk_count in rows
        ]

    async def get_document(
        self, *, workspace_id: UUID, document_id: UUID
    ) -> IndexedDocument:
        document = await self.session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
        )
        if document is None:
            raise KnowledgeDocumentNotFound("Document not found")
        return await self._to_result(document)

    async def enqueue(
        self,
        *,
        workspace_id: UUID,
        space_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> IndexedDocument:
        """Create a pending document and queue async indexing."""

        if len(data) > settings.max_upload_size_bytes:
            raise KnowledgeIngestionError("Document size limit exceeded")

        digest = hashlib.sha256(data).hexdigest()
        existing = await self.session.scalar(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.space_id == space_id,
                Document.sha256 == digest,
            )
        )
        if existing is not None and existing.status is DocumentStatus.COMPLETED:
            return await self._to_result(existing)
        if existing is not None:
            await self.vectors.delete_document(
                workspace_id=str(workspace_id),
                document_id=str(existing.id),
            )
            await self.session.delete(existing)
            await self.session.flush()

        document = Document(
            workspace_id=workspace_id,
            space_id=space_id,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(data),
            sha256=digest,
            status=DocumentStatus.PENDING,
        )
        self.session.add(document)
        await self.session.flush()
        self.session.add(DocumentUpload(document_id=document.id, data=data))
        await self.session.commit()
        await self.session.refresh(document)
        await self.queue.enqueue_knowledge_ingest(document_id=document.id)
        return await self._to_result(document)

    async def execute_ingest(self, *, document_id: UUID) -> IndexedDocument:
        """Worker entrypoint: parse, embed, and index a pending upload."""

        document = await self.session.scalar(
            select(Document)
            .options(selectinload(Document.upload))
            .where(Document.id == document_id)
        )
        if document is None:
            raise KnowledgeDocumentNotFound("Document not found")
        if document.upload is None:
            document.status = DocumentStatus.FAILED
            document.error = "Missing upload payload"
            await self.session.commit()
            raise KnowledgeIngestionError("Missing upload payload")

        data = document.upload.data
        document.status = DocumentStatus.PROCESSING
        document.error = None
        await self.session.commit()

        try:
            return await self._index_bytes(document=document, data=data)
        except Exception as exc:
            document.status = DocumentStatus.FAILED
            document.error = f"{type(exc).__name__}: indexing failed"
            await self.session.commit()
            raise

    async def ingest(
        self,
        *,
        workspace_id: UUID,
        space_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> IndexedDocument:
        """Synchronously index one document (used by workflow workers)."""

        if len(data) > settings.max_upload_size_bytes:
            raise KnowledgeIngestionError("Document size limit exceeded")

        digest = hashlib.sha256(data).hexdigest()
        existing = await self.session.scalar(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.space_id == space_id,
                Document.sha256 == digest,
            )
        )
        if existing is not None and existing.status is DocumentStatus.COMPLETED:
            return await self._to_result(existing)
        if existing is not None:
            await self.vectors.delete_document(
                workspace_id=str(workspace_id),
                document_id=str(existing.id),
            )
            await self.session.delete(existing)
            await self.session.flush()

        document = Document(
            workspace_id=workspace_id,
            space_id=space_id,
            filename=filename,
            content_type=content_type or "application/octet-stream",
            size_bytes=len(data),
            sha256=digest,
            status=DocumentStatus.PROCESSING,
        )
        self.session.add(document)
        await self.session.flush()
        return await self._index_bytes(document=document, data=data)

    async def _index_bytes(
        self, *, document: Document, data: bytes
    ) -> IndexedDocument:
        parsed = parse_document(filename=document.filename, data=data)
        chunks = chunk_text(
            parsed.text,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        if not chunks:
            raise KnowledgeIngestionError("Document produced no chunks")

        # Replace any previous chunks for re-runs.
        existing_chunks = (
            await self.session.scalars(
                select(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )
        ).all()
        for chunk in existing_chunks:
            await self.session.delete(chunk)
        await self.session.flush()

        chunk_models = [
            DocumentChunk(
                document_id=document.id,
                workspace_id=document.workspace_id,
                space_id=document.space_id,
                chunk_index=index,
                content=content,
            )
            for index, content in enumerate(chunks)
        ]
        self.session.add_all(chunk_models)
        await self.session.flush()

        try:
            vectors: list[VectorRecord] = []
            for offset in range(0, len(chunks), 32):
                batch = chunks[offset : offset + 32]
                batch_embeddings = await self.embeddings.embed_documents(batch)
                vectors.extend(
                    VectorRecord(
                        id=str(chunk_models[offset + index].id),
                        vector=embedding,
                        metadata={
                            "source_type": "document",
                            "workspace_id": str(document.workspace_id),
                            "space_id": str(document.space_id),
                            "document_id": str(document.id),
                            "chunk_id": str(chunk_models[offset + index].id),
                            "chunk_index": offset + index,
                            "filename": document.filename,
                            "content": batch[index],
                        },
                    )
                    for index, embedding in enumerate(batch_embeddings)
                )
            await self.vectors.upsert(vectors)
        except Exception as exc:
            try:
                await self.vectors.delete_document(
                    workspace_id=str(document.workspace_id),
                    document_id=str(document.id),
                )
            except Exception:
                logger.exception("Failed to compensate partial vector ingestion")
            document.status = DocumentStatus.FAILED
            document.error = f"{type(exc).__name__}: indexing failed"
            await self.session.commit()
            raise KnowledgeIngestionError("Document indexing failed") from exc

        upload = await self.session.get(DocumentUpload, document.id)
        if upload is not None:
            await self.session.delete(upload)
        document.status = DocumentStatus.COMPLETED
        document.error = None
        await self.session.commit()
        await self.session.refresh(document)
        return await self._to_result(document)

    async def delete(self, *, workspace_id: UUID, document_id: UUID) -> None:
        """Delete one document and all of its vectors."""

        document = await self.session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.workspace_id == workspace_id,
            )
        )
        if document is None:
            raise KnowledgeDocumentNotFound("Document not found")

        await self.vectors.delete_document(
            workspace_id=str(workspace_id),
            document_id=str(document_id),
        )
        await self.session.delete(document)
        await self.session.commit()
