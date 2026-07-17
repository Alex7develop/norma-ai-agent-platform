"""Public API smoke tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Norma AI",
        "version": "v1",
    }
