"""Notion OAuth, page search, and markdown export for knowledge ingest."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.integration_models import IntegrationConnection
from app.services.token_crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger(__name__)

NOTION_PROVIDER = "notion"
NOTION_VERSION = "2022-06-28"
NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"
NOTION_API = "https://api.notion.com/v1"
STATE_TYPE = "notion_oauth"


class NotionConfigurationError(RuntimeError):
    pass


class NotionNotConnected(LookupError):
    pass


class NotionAPIError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class NotionPageSummary:
    id: str
    title: str


@dataclass(frozen=True, slots=True)
class NotionOAuthState:
    user_id: UUID
    workspace_id: UUID
    space_id: UUID


def _require_oauth_config() -> tuple[str, str]:
    client_id = settings.notion_client_id
    secret = settings.notion_client_secret
    if not client_id or secret is None or not secret.get_secret_value():
        raise NotionConfigurationError("Notion OAuth is not configured")
    return client_id, secret.get_secret_value()


def create_oauth_state(
    *,
    user_id: UUID,
    workspace_id: UUID,
    space_id: UUID,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "type": STATE_TYPE,
            "sub": str(user_id),
            "workspace_id": str(workspace_id),
            "space_id": str(space_id),
            "nonce": str(uuid4()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def parse_oauth_state(token: str) -> NotionOAuthState:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid OAuth state") from exc
    if payload.get("type") != STATE_TYPE:
        raise ValueError("Invalid OAuth state type")
    return NotionOAuthState(
        user_id=UUID(str(payload["sub"])),
        workspace_id=UUID(str(payload["workspace_id"])),
        space_id=UUID(str(payload["space_id"])),
    )


def build_authorize_url(*, state: str) -> str:
    client_id, _ = _require_oauth_config()
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "owner": "user",
            "redirect_uri": settings.notion_redirect_uri,
            "state": state,
        }
    )
    return f"{NOTION_AUTHORIZE_URL}?{query}"


class NotionClient:
    """Thin Notion HTTP client used by the application service."""

    def __init__(
        self,
        access_token: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.access_token = access_token
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> NotionClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30)
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert self._client is not None
        response = await self._client.request(
            method,
            f"{NOTION_API}{path}",
            headers=self._headers(),
            **kwargs,
        )
        if response.status_code >= 400:
            raise NotionAPIError(
                f"Notion API {response.status_code}: {response.text[:300]}"
            )
        return response.json()

    async def search_pages(self, *, page_size: int = 50) -> list[NotionPageSummary]:
        payload = await self._request(
            "POST",
            "/search",
            json={
                "filter": {"value": "page", "property": "object"},
                "page_size": page_size,
            },
        )
        results: list[NotionPageSummary] = []
        for item in payload.get("results") or []:
            if item.get("object") != "page":
                continue
            results.append(
                NotionPageSummary(
                    id=str(item["id"]),
                    title=_page_title(item),
                )
            )
        return results

    async def export_page_markdown(self, page_id: str) -> tuple[str, str]:
        page = await self._request("GET", f"/pages/{page_id}")
        title = _page_title(page)
        blocks = await self._list_blocks(page_id)
        body = _blocks_to_markdown(blocks)
        markdown = f"# {title}\n\n{body}".strip() + "\n"
        filename = f"notion-{_slug(title)}.md"
        return filename, markdown

    async def _list_blocks(self, block_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            payload = await self._request(
                "GET", f"/blocks/{block_id}/children", params=params
            )
            for block in payload.get("results") or []:
                blocks.append(block)
                if block.get("has_children"):
                    children = await self._list_blocks(str(block["id"]))
                    block["_children"] = children
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")
        return blocks


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    client_id, client_secret = _require_oauth_config()
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            NOTION_TOKEN_URL,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/json",
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.notion_redirect_uri,
            },
        )
    if response.status_code >= 400:
        raise NotionAPIError(
            "Notion token exchange failed: "
            f"{response.status_code} {response.text[:300]}"
        )
    return response.json()


class NotionIntegrationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_connection(
        self, *, user_id: UUID, workspace_id: UUID
    ) -> IntegrationConnection | None:
        return await self.session.scalar(
            select(IntegrationConnection).where(
                IntegrationConnection.provider == NOTION_PROVIDER,
                IntegrationConnection.user_id == user_id,
                IntegrationConnection.workspace_id == workspace_id,
            )
        )

    async def upsert_connection(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        access_token: str,
        external_workspace_id: str | None,
        external_workspace_name: str | None,
    ) -> IntegrationConnection:
        existing = await self.get_connection(user_id=user_id, workspace_id=workspace_id)
        encrypted = encrypt_secret(access_token)
        if existing is None:
            existing = IntegrationConnection(
                provider=NOTION_PROVIDER,
                user_id=user_id,
                workspace_id=workspace_id,
                access_token_encrypted=encrypted,
                external_workspace_id=external_workspace_id,
                external_workspace_name=external_workspace_name,
            )
            self.session.add(existing)
        else:
            existing.access_token_encrypted = encrypted
            existing.external_workspace_id = external_workspace_id
            existing.external_workspace_name = external_workspace_name
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def disconnect(self, *, user_id: UUID, workspace_id: UUID) -> None:
        connection = await self.get_connection(
            user_id=user_id, workspace_id=workspace_id
        )
        if connection is None:
            raise NotionNotConnected("Notion is not connected")
        await self.session.delete(connection)
        await self.session.commit()

    async def access_token(self, *, user_id: UUID, workspace_id: UUID) -> str:
        connection = await self.get_connection(
            user_id=user_id, workspace_id=workspace_id
        )
        if connection is None:
            raise NotionNotConnected("Notion is not connected")
        return decrypt_secret(connection.access_token_encrypted)


def _rich_text(items: list[dict[str, Any]] | None) -> str:
    if not items:
        return ""
    parts: list[str] = []
    for item in items:
        text = item.get("plain_text") or ""
        annotations = item.get("annotations") or {}
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        href = item.get("href")
        if href:
            text = f"[{text}]({href})"
        parts.append(text)
    return "".join(parts)


def _page_title(page: dict[str, Any]) -> str:
    properties = page.get("properties") or {}
    for value in properties.values():
        if value.get("type") == "title":
            title = _rich_text(value.get("title") or [])
            if title.strip():
                return title.strip()
    return "Untitled"


def _slug(title: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in title)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return (cleaned.strip("-") or "page")[:80]


def _blocks_to_markdown(blocks: list[dict[str, Any]], *, depth: int = 0) -> str:
    lines: list[str] = []
    for block in blocks:
        block_type = block.get("type")
        data = block.get(block_type) or {}
        children = block.get("_children") or []
        indent = "  " * depth

        if block_type in {"paragraph", "quote", "callout"}:
            text = _rich_text(data.get("rich_text") or [])
            if block_type == "quote":
                lines.append(f"{indent}> {text}")
            elif text:
                lines.append(f"{indent}{text}")
        elif block_type in {"heading_1", "heading_2", "heading_3"}:
            level = int(block_type[-1])
            text = _rich_text(data.get("rich_text") or [])
            lines.append(f"{indent}{'#' * level} {text}")
        elif block_type in {"bulleted_list_item", "numbered_list_item"}:
            text = _rich_text(data.get("rich_text") or [])
            bullet = "-" if block_type == "bulleted_list_item" else "1."
            lines.append(f"{indent}{bullet} {text}")
        elif block_type == "to_do":
            text = _rich_text(data.get("rich_text") or [])
            checked = "x" if data.get("checked") else " "
            lines.append(f"{indent}- [{checked}] {text}")
        elif block_type == "code":
            text = _rich_text(data.get("rich_text") or [])
            language = data.get("language") or ""
            lines.append(f"{indent}```{language}\n{text}\n{indent}```")
        elif block_type == "divider":
            lines.append(f"{indent}---")
        elif block_type == "equation":
            expression = data.get("expression") or ""
            if expression:
                lines.append(f"{indent}$${expression}$$")
        else:
            # Unsupported / media blocks — skip content, still walk children.
            pass

        if children:
            child_md = _blocks_to_markdown(children, depth=depth + 1)
            if child_md.strip():
                lines.append(child_md)

        lines.append("")

    return "\n".join(lines).strip()
