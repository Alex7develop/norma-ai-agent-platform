"""Public API smoke tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.readiness import ReadinessReport, check_dependencies


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Norma AI",
        "version": "v1",
    }


@pytest.mark.parametrize(
    ("checks", "expected_status", "expected_code"),
    [
        (
            {
                "postgres": True,
                "redis": True,
                "qdrant": True,
                "embeddings": True,
            },
            "ready",
            200,
        ),
        (
            {
                "postgres": True,
                "redis": False,
                "qdrant": True,
                "embeddings": True,
            },
            "degraded",
            503,
        ),
    ],
)
def test_readiness_check(
    checks: dict[str, bool], expected_status: str, expected_code: int
) -> None:
    async def override_readiness() -> ReadinessReport:
        return ReadinessReport(checks=checks)

    app.dependency_overrides[check_dependencies] = override_readiness
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_code
    assert response.json()["status"] == expected_status
