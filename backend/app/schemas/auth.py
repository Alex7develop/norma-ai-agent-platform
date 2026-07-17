"""Authentication and workspace schemas."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    workspace_name: str = Field(default="My workspace", min_length=1, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    role: str


class SessionResponse(BaseModel):
    user: UserResponse
    workspaces: list[WorkspaceResponse]
