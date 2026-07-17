"""RAG assistant HTTP contract tests."""

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.assistant import get_memory_service, get_rag_assistant
from app.main import app
from app.workflows.rag_assistant import RagAssistantResult
from tests.auth_helpers import authenticated_client


class FakeAssistantAgent:
    async def answer(self, **_: object) -> RagAssistantResult:
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


class FakeMemoryService:
    def __init__(self) -> None:
        self.conversation_id = uuid4()

    async def get_or_create_conversation(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(id=self.conversation_id)

    async def load_chat_context(self, **_: object) -> list[object]:
        return []

    async def load_workspace_notes(self, **_: object) -> list[str]:
        return []

    async def append_turn(self, **_: object) -> None:
        return None


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
    memory = FakeMemoryService()
    app.dependency_overrides[get_rag_assistant] = FakeAssistantAgent
    app.dependency_overrides[get_memory_service] = lambda: memory
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
        app.dependency_overrides.pop(get_memory_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].endswith("[1].")
    assert payload["sources"][0]["filename"] == "architecture.md"
    assert payload["conversation_id"] == str(memory.conversation_id)
