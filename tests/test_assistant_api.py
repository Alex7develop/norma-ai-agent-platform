"""RAG assistant HTTP contract tests."""

from uuid import uuid4

from fastapi.testclient import TestClient
from tests.auth_helpers import authenticated_client

from app.api.v1.assistant import get_rag_assistant
from app.main import app
from app.workflows.rag_assistant import RagAssistantResult


class FakeAssistantAgent:
    async def answer(self, *, workspace_id: str, question: str) -> RagAssistantResult:
        return RagAssistantResult(
            answer="Vectors are stored in Qdrant [1].",
            sources=[
                {
                    "citation": 1,
                    "document_id": "document-1",
                    "filename": "architecture.md",
                    "chunk_index": 1,
                    "score": 0.9,
                }
            ],
            model="google/gemini-3.5-flash",
        )


def test_assistant_query_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/assistant/query",
            json={
                "workspace_id": str(uuid4()),
                "question": "Where are vectors stored?",
            },
        )
    assert response.status_code == 401


def test_assistant_query_contract() -> None:
    app.dependency_overrides[get_rag_assistant] = FakeAssistantAgent
    try:
        with authenticated_client("app.api.v1.assistant"):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/assistant/query",
                    json={
                        "workspace_id": str(uuid4()),
                        "question": "Where are vectors stored?",
                    },
                )
    finally:
        app.dependency_overrides.pop(get_rag_assistant, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].endswith("[1].")
    assert payload["sources"][0]["filename"] == "architecture.md"
