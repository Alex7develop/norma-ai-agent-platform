"""Application services for bounded document ingestion and retrieval."""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.document_models import Document, DocumentChunk, DocumentStatus
from app.rag.container import embedding_provider, vector_store
from app.rag.document_processing import chunk_text, parse_document
from app.rag.embeddings import EmbeddingProvider
from app.rag.vectorstore import VectorRecord, VectorStore

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


class KnowledgeService:
    """Coordinate parsers, relational metadata, embeddings, and vectors."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        embeddings: EmbeddingProvider = embedding_provider,
        vectors: VectorStore = vector_store,
    ) -> None:
        self.session = session
        self.embeddings = embeddings
        self.vectors = vectors

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
        )

    async def _to_result(self, document: Document) -> IndexedDocument:
        chunk_count = await self.session.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.document_id == document.id
            )
        )
        return self._build_result(document, int(chunk_count or 0))

    async def list_documents(self, *, workspace_id: UUID) -> list[IndexedDocument]:
        """List newest documents inside one workspace."""

        rows = (
            await self.session.execute(
                select(Document, func.count(DocumentChunk.id))
                .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
                .where(Document.workspace_id == workspace_id)
                .group_by(Document.id)
                .order_by(Document.created_at.desc())
            )
        ).all()
        return [
            self._build_result(document, int(chunk_count))
            for document, chunk_count in rows
        ]

    async def ingest(
        self,
        *,
        workspace_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> IndexedDocument:
        """Parse, persist, embed, and index one document."""

        if len(data) > settings.max_upload_size_bytes:
            raise KnowledgeIngestionError("Document size limit exceeded")

        digest = hashlib.sha256(data).hexdigest()
        existing = await self.session.scalar(
            select(Document).where(
                Document.workspace_id == workspace_id,
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
            await self.session.commit()

        parsed = parse_document(filename=filename, data=data)
        chunks = chunk_text(
            parsed.text,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        if not chunks:
            raise KnowledgeIngestionError("Document produced no chunks")

        document = Document(
            workspace_id=workspace_id,
            filename=filename,
            content_type=content_type or parsed.file_type,
            size_bytes=len(data),
            sha256=digest,
            status=DocumentStatus.PROCESSING,
        )
        self.session.add(document)
        await self.session.flush()

        chunk_models = [
            DocumentChunk(
                document_id=document.id,
                workspace_id=workspace_id,
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
                            "workspace_id": str(workspace_id),
                            "document_id": str(document.id),
                            "chunk_id": str(chunk_models[offset + index].id),
                            "chunk_index": offset + index,
                            "filename": filename,
                            "content": batch[index],
                        },
                    )
                    for index, embedding in enumerate(batch_embeddings)
                )
            await self.vectors.upsert(vectors)
        except Exception as exc:
            try:
                await self.vectors.delete_document(
                    workspace_id=str(workspace_id),
                    document_id=str(document.id),
                )
            except Exception:
                logger.exception("Failed to compensate partial vector ingestion")
            document.status = DocumentStatus.FAILED
            document.error = f"{type(exc).__name__}: indexing failed"
            await self.session.commit()
            raise KnowledgeIngestionError("Document indexing failed") from exc

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
