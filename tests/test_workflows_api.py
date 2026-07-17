"""Workflow HTTP contract tests."""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.workflows import get_launch_strategy_service
from app.database.workflow_models import (
    ArtifactKind,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowStatus,
)
from app.main import app
from app.workflows.launch_strategy import LaunchStrategyWorkflow
from tests.auth_helpers import authenticated_client


class FakeLaunchStrategyService:
    def __init__(self) -> None:
        self.run_id = uuid4()

    async def run(self, **kwargs: object) -> tuple[WorkflowRun, str]:
        workspace_id = kwargs["workspace_id"]
        run = WorkflowRun(
            id=self.run_id,
            workspace_id=workspace_id,  # type: ignore[arg-type]
            user_id=kwargs["user_id"],  # type: ignore[arg-type]
            workflow_type=LaunchStrategyWorkflow.WORKFLOW_TYPE,
            status=WorkflowStatus.COMPLETED,
            brief=str(kwargs["brief"]),
            product_name="Aussie Roast",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        run.artifacts = [
            WorkflowArtifact(
                id=uuid4(),
                run_id=self.run_id,
                kind=ArtifactKind.PACK,
                title="launch-strategy-aussie-roast.md",
                content_md="# Pack",
                document_id=uuid4(),
                created_at=datetime.now(UTC),
            )
        ]
        return run, "google/gemini-3.5-flash"


def test_launch_strategy_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/workflows/launch-strategy",
            json={
                "workspace_id": str(uuid4()),
                "brief": "Open coffee shops in Australia",
            },
        )
    assert response.status_code == 401


def test_launch_strategy_contract() -> None:
    service = FakeLaunchStrategyService()
    app.dependency_overrides[get_launch_strategy_service] = lambda: service
    try:
        with authenticated_client("app.api.v1.workflows"):
            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/workflows/launch-strategy",
                    json={
                        "workspace_id": str(uuid4()),
                        "brief": "Open coffee shops in Australia",
                        "product_name": "Aussie Roast",
                    },
                )
    finally:
        app.dependency_overrides.pop(get_launch_strategy_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["product_name"] == "Aussie Roast"
    assert payload["artifacts"][0]["kind"] == "pack"
    assert payload["model"] == "google/gemini-3.5-flash"


def test_get_workflow_run_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/workflows/runs/{uuid4()}",
            params={"workspace_id": str(uuid4())},
        )
    assert response.status_code == 401
