"""Authentication HTTP contract tests."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.v1.auth import get_auth_service
from app.core.config import settings
from app.core.security import AuthenticationError
from app.database.auth_models import User, Workspace, WorkspaceRole
from app.main import app
from app.services.auth import AuthResult, EmailAlreadyRegistered, TokenPair


class FakeAuthService:
    def __init__(self) -> None:
        self.user = User(
            id=uuid4(),
            email="founder@norma.ai",
            display_name="Founder",
            password_hash="unused",
            is_active=True,
        )
        self.workspace = Workspace(id=uuid4(), name="Norma HQ")

    async def register(self, **_: object) -> AuthResult:
        return AuthResult(
            self.user,
            [(self.workspace, WorkspaceRole.OWNER)],
            TokenPair("access-token", "refresh-token"),
        )

    async def login(self, **_: object) -> AuthResult:
        return AuthResult(
            self.user,
            [(self.workspace, WorkspaceRole.OWNER)],
            TokenPair("access-token", "refresh-token"),
        )

    async def workspaces_for(self, _: object) -> list[tuple[Workspace, WorkspaceRole]]:
        return [(self.workspace, WorkspaceRole.OWNER)]

    async def revoke(self, _: str | None) -> None:
        return None


class RejectingAuthService(FakeAuthService):
    async def login(self, **_: object) -> AuthResult:
        raise AuthenticationError("Email or password is incorrect")

    async def register(self, **_: object) -> AuthResult:
        raise EmailAlreadyRegistered("Email is already registered")


def test_register_sets_http_only_cookies() -> None:
    service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "founder@norma.ai",
                    "password": "secure-password-12",
                    "display_name": "Founder",
                    "workspace_name": "Norma HQ",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "founder@norma.ai"
    assert response.cookies[settings.access_cookie_name] == "access-token"
    assert response.cookies[settings.refresh_cookie_name] == "refresh-token"


def test_login_rejects_bad_credentials() -> None:
    app.dependency_overrides[get_auth_service] = RejectingAuthService
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "founder@norma.ai", "password": "wrong-password"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
