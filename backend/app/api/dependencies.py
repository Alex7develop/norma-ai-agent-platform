"""Authentication and workspace authorization dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import AuthenticationError, decode_token
from app.database.auth_models import User, WorkspaceMembership
from app.database.session import get_db_session


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    token = request.cookies.get(settings.access_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        claims = decode_token(token, expected_type="access")
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = await session.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User is unavailable")
    return user


async def require_workspace_access(
    session: AsyncSession,
    *,
    user_id: UUID,
    workspace_id: UUID,
) -> WorkspaceMembership:
    membership = await session.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.workspace_id == workspace_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return membership
