"""Identity registration, authentication, and refresh rotation."""

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    AuthenticationError,
    create_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.database.auth_models import (
    AuthSession,
    User,
    Workspace,
    WorkspaceMembership,
    WorkspaceRole,
)


class EmailAlreadyRegistered(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    workspaces: list[tuple[Workspace, WorkspaceRole]]
    tokens: TokenPair


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def workspaces_for(
        self, user_id: object
    ) -> list[tuple[Workspace, WorkspaceRole]]:
        rows = await self.session.execute(
            select(Workspace, WorkspaceMembership.role)
            .join(WorkspaceMembership)
            .where(WorkspaceMembership.user_id == user_id)
        )
        return list(rows.tuples())

    async def _issue_tokens(self, user: User) -> TokenPair:
        auth_session = AuthSession(
            user_id=user.id,
            token_hash="pending",
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
        self.session.add(auth_session)
        await self.session.flush()
        access = create_token(
            user_id=user.id,
            token_type="access",
            lifetime=timedelta(minutes=settings.access_token_minutes),
        )
        refresh = create_token(
            user_id=user.id,
            token_type="refresh",
            session_id=auth_session.id,
            lifetime=timedelta(days=settings.refresh_token_days),
        )
        auth_session.token_hash = hash_refresh_token(refresh)
        return TokenPair(access, refresh)

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        workspace_name: str,
    ) -> AuthResult:
        user = User(
            email=email.strip().lower(),
            display_name=display_name.strip(),
            password_hash=hash_password(password),
        )
        workspace = Workspace(name=workspace_name.strip())
        self.session.add_all([user, workspace])
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise EmailAlreadyRegistered("Email is already registered") from exc
        self.session.add(
            WorkspaceMembership(
                user_id=user.id,
                workspace_id=workspace.id,
                role=WorkspaceRole.OWNER,
            )
        )
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return AuthResult(user, [(workspace, WorkspaceRole.OWNER)], tokens)

    async def login(self, *, email: str, password: str) -> AuthResult:
        user = await self.session.scalar(
            select(User).where(User.email == email.strip().lower())
        )
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.password_hash)
        ):
            raise AuthenticationError("Email or password is incorrect")
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return AuthResult(user, await self.workspaces_for(user.id), tokens)

    async def refresh(self, token: str) -> AuthResult:
        claims = decode_token(token, expected_type="refresh")
        if claims.session_id is None:
            raise AuthenticationError("Refresh session is missing")
        auth_session = await self.session.scalar(
            select(AuthSession).where(
                AuthSession.id == claims.session_id,
                AuthSession.user_id == claims.user_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        if (
            auth_session is None
            or auth_session.expires_at <= datetime.now(UTC)
            or not hmac.compare_digest(
                auth_session.token_hash, hash_refresh_token(token)
            )
        ):
            raise AuthenticationError("Refresh session is invalid")
        user = await self.session.get(User, claims.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User is unavailable")

        access = create_token(
            user_id=user.id,
            token_type="access",
            lifetime=timedelta(minutes=settings.access_token_minutes),
        )
        refresh = create_token(
            user_id=user.id,
            token_type="refresh",
            session_id=auth_session.id,
            lifetime=timedelta(days=settings.refresh_token_days),
        )
        auth_session.token_hash = hash_refresh_token(refresh)
        auth_session.expires_at = datetime.now(UTC) + timedelta(
            days=settings.refresh_token_days
        )
        await self.session.commit()
        return AuthResult(
            user,
            await self.workspaces_for(user.id),
            TokenPair(access, refresh),
        )

    async def revoke(self, token: str | None) -> None:
        if not token:
            return
        try:
            claims = decode_token(token, expected_type="refresh")
        except AuthenticationError:
            return
        if claims.session_id:
            auth_session = await self.session.get(AuthSession, claims.session_id)
            if auth_session:
                auth_session.revoked_at = datetime.now(UTC)
                await self.session.commit()
