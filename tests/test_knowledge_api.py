"""Knowledge HTTP contract tests."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.knowledge import get_knowledge_service
from app.main import app
from app.services.knowledge import IndexedDocument


class FakeKnowledgeService:
    async def ingest(self, **kwargs: object) -> IndexedDocument:
        workspace_id = kwargs["workspace_id"]
        data = kwargs["data"]
        assert isinstance(data, bytes)
        return IndexedDocument(
            id=uuid4(),
            workspace_id=workspace_id,  # type: ignore[arg-type]
            filename=str(kwargs["filename"]),
            content_type=str(kwargs["content_type"]),
            size_bytes=len(data),
            sha256="a" * 64,
            status="completed",
            chunk_count=1,
            created_at=datetime.now(UTC),
        )


def test_upload_document_contract() -> None:
    workspace_id = uuid4()
    app.dependency_overrides[get_knowledge_service] = FakeKnowledgeService
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/knowledge/documents",
                data={"workspace_id": str(workspace_id)},
                files={"file": ("notes.txt", b"Knowledge", "text/plain")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["workspace_id"] == str(workspace_id)
    assert payload["status"] == "completed"
    assert payload["chunk_count"] == 1
