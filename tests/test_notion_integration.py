"""Notion OAuth and import contract tests."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.integrations import get_knowledge_service, get_notion_service
from app.main import app
from app.services.knowledge import IndexedDocument
from app.services.notion import (
    NotionPageSummary,
    build_authorize_url,
    create_oauth_state,
    parse_oauth_state,
)
from tests.auth_helpers import authenticated_client


def test_oauth_state_roundtrip() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    space_id = uuid4()
    token = create_oauth_state(
        user_id=user_id, workspace_id=workspace_id, space_id=space_id
    )
    claims = parse_oauth_state(token)
    assert claims.user_id == user_id
    assert claims.workspace_id == workspace_id
    assert claims.space_id == space_id


def test_build_authorize_url_contains_client() -> None:
    with patch("app.services.notion.settings") as settings:
        settings.notion_client_id = "client-123"
        settings.notion_client_secret = type(
            "S", (), {"get_secret_value": lambda self: "secret"}
        )()
        settings.notion_redirect_uri = (
            "http://localhost:8000/api/v1/integrations/notion/callback"
        )
        url = build_authorize_url(state="abc")
    assert "client_id=client-123" in url
    assert "state=abc" in url
    assert "response_type=code" in url


def test_notion_authorize_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integrations/notion/authorize",
            params={"workspace_id": str(uuid4()), "space_id": str(uuid4())},
        )
    assert response.status_code == 401


def test_notion_import_contract() -> None:
    workspace_id = uuid4()
    space_id = uuid4()
    document_id = uuid4()

    class FakeNotionService:
        async def access_token(self, **_: object) -> str:
            return "notion-token"

    class FakeKnowledge:
        async def enqueue(self, **kwargs: object) -> IndexedDocument:
            return IndexedDocument(
                id=document_id,
                workspace_id=kwargs["workspace_id"],  # type: ignore[arg-type]
                filename=str(kwargs["filename"]),
                content_type=str(kwargs["content_type"]),
                size_bytes=len(kwargs["data"]),  # type: ignore[arg-type]
                sha256="b" * 64,
                status="pending",
                chunk_count=0,
                created_at=datetime.now(UTC),
            )

    class FakeClient:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def export_page_markdown(self, page_id: str) -> tuple[str, str]:
            return f"{page_id}.md", f"# Page {page_id}\n"

    app.dependency_overrides[get_notion_service] = FakeNotionService
    app.dependency_overrides[get_knowledge_service] = FakeKnowledge
    try:
        with authenticated_client("app.api.v1.integrations"):
            with (
                patch(
                    "app.api.v1.integrations.ProjectService"
                ) as project_cls,
                patch("app.api.v1.integrations.NotionClient", FakeClient),
            ):
                project_cls.return_value.require_space = AsyncMock()
                with TestClient(app) as client:
                    response = client.post(
                        "/api/v1/integrations/notion/import",
                        json={
                            "workspace_id": str(workspace_id),
                            "space_id": str(space_id),
                            "page_ids": [str(uuid4())],
                        },
                    )
    finally:
        app.dependency_overrides.pop(get_notion_service, None)
        app.dependency_overrides.pop(get_knowledge_service, None)

    assert response.status_code == 202
    payload = response.json()
    assert payload["items"][0]["status"] == "pending"
    assert payload["items"][0]["document_id"] == str(document_id)


def test_notion_pages_lists_results() -> None:
    class FakeNotionService:
        async def access_token(self, **_: object) -> str:
            return "notion-token"

    class FakeClient:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def search_pages(self, **_: object) -> list[NotionPageSummary]:
            return [NotionPageSummary(id="page-1", title="Strategy")]

    app.dependency_overrides[get_notion_service] = FakeNotionService
    try:
        with authenticated_client("app.api.v1.integrations"):
            with patch("app.api.v1.integrations.NotionClient", FakeClient):
                with TestClient(app) as client:
                    response = client.get(
                        "/api/v1/integrations/notion/pages",
                        params={"workspace_id": str(uuid4())},
                    )
    finally:
        app.dependency_overrides.pop(get_notion_service, None)

    assert response.status_code == 200
    assert response.json()[0]["title"] == "Strategy"
