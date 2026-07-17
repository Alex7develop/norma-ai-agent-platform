"""Self-hosted authentication endpoints using HttpOnly cookies."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import AuthenticationError
from app.database.auth_models import User
from app.database.session import get_db_session
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    SessionResponse,
    UserResponse,
    WorkspaceResponse,
)
from app.services.auth import AuthResult, AuthService, EmailAlreadyRegistered

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    return AuthService(session)


def set_auth_cookies(response: Response, result: AuthResult) -> None:
    secure = settings.app_env == "production"
    response.set_cookie(
        settings.access_cookie_name,
        result.tokens.access_token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        result.tokens.refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
    )


def session_response(result: AuthResult) -> SessionResponse:
    return SessionResponse(
        user=UserResponse(
            id=result.user.id,
            email=result.user.email,
            display_name=result.user.display_name,
        ),
        workspaces=[
            WorkspaceResponse(id=workspace.id, name=workspace.name, role=role.value)
            for workspace, role in result.workspaces
        ],
    )


@router.post("/register", response_model=SessionResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    try:
        result = await service.register(
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
            workspace_name=payload.workspace_name,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    set_auth_cookies(response, result)
    return session_response(result)


@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    try:
        result = await service.login(
            email=str(payload.email), password=payload.password
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    set_auth_cookies(response, result)
    return session_response(result)


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token is missing")
    try:
        result = await service.refresh(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    set_auth_cookies(response, result)
    return session_response(result)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.revoke(request.cookies.get(settings.refresh_cookie_name))
    response.delete_cookie(settings.access_cookie_name, path="/")
    response.delete_cookie(
        settings.refresh_cookie_name,
        path=f"{settings.api_v1_prefix}/auth",
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=SessionResponse)
async def me(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SessionResponse:
    workspaces = await service.workspaces_for(user.id)
    return SessionResponse(
        user=UserResponse(id=user.id, email=user.email, display_name=user.display_name),
        workspaces=[
            WorkspaceResponse(id=workspace.id, name=workspace.name, role=role.value)
            for workspace, role in workspaces
        ],
    )
