"""Shared authentication overrides for API contract tests."""

from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.api.dependencies import get_current_user
from app.database.auth_models import User
from app.database.session import get_db_session
from app.main import app


def make_user() -> User:
    return User(
        id=uuid4(),
        email="tester@norma.ai",
        display_name="Tester",
        password_hash="unused",
        is_active=True,
    )


@contextmanager
def authenticated_client(module_path: str) -> Iterator[User]:
    """Override the current user and skip workspace membership checks."""

    user = make_user()

    async def override_user() -> User:
        return user

    async def override_session() -> AsyncIterator[MagicMock]:
        yield MagicMock()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db_session] = override_session
    try:
        with patch(f"{module_path}.require_workspace_access", new_callable=AsyncMock):
            yield user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db_session, None)
