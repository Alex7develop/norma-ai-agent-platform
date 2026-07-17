"""Infrastructure readiness checks.

Liveness and readiness are intentionally separate: liveness confirms that the
process runs, while readiness controls whether it should receive traffic.
"""

import asyncio
from dataclasses import dataclass

import httpx
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.database.session import engine


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Provider-neutral result consumed by the API layer."""

    checks: dict[str, bool]

    @property
    def is_ready(self) -> bool:
        return all(self.checks.values())


async def _check_postgres() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _check_redis() -> None:
    client = Redis.from_url(settings.redis_url)
    try:
        await client.ping()
    finally:
        await client.aclose()


async def _check_qdrant() -> None:
    client = AsyncQdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        check_compatibility=False,
    )
    try:
        await client.get_collections()
    finally:
        await client.close()


async def _check_embeddings() -> None:
    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.get(f"{settings.embedding_service_url}/health")
        response.raise_for_status()


async def check_dependencies() -> ReadinessReport:
    """Check required infrastructure concurrently with bounded latency."""

    names = ("postgres", "redis", "qdrant", "embeddings")
    checks = (
        _check_postgres(),
        _check_redis(),
        _check_qdrant(),
        _check_embeddings(),
    )
    results = await asyncio.gather(
        *(asyncio.wait_for(check, timeout=3) for check in checks),
        return_exceptions=True,
    )
    return ReadinessReport(
        checks=dict(
            zip(
                names,
                (not isinstance(result, BaseException) for result in results),
                strict=True,
            )
        )
    )
