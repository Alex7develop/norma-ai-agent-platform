"""Redis-backed job queue for long-running workflows."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.config import settings

LAUNCH_STRATEGY_JOB = "launch_strategy"
KNOWLEDGE_INGEST_JOB = "knowledge_ingest"
WORKER_HEARTBEAT_KEY = "norma:worker:heartbeat"


class JobQueue:
    """Thin Redis list queue used by the API and worker processes."""

    def __init__(
        self,
        *,
        redis_url: str | None = None,
        queue_name: str | None = None,
    ) -> None:
        self.redis_url = redis_url or settings.redis_url
        self.queue_name = queue_name or settings.launch_strategy_queue
        self._client: Redis | None = None

    async def connect(self) -> Redis:
        if self._client is None:
            # socket_timeout must stay unset so BRPOP can block for its own timeout.
            self._client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def enqueue_launch_strategy(self, *, run_id: UUID) -> None:
        client = await self.connect()
        payload = json.dumps({"type": LAUNCH_STRATEGY_JOB, "run_id": str(run_id)})
        await client.lpush(self.queue_name, payload)

    async def enqueue_knowledge_ingest(self, *, document_id: UUID) -> None:
        client = await self.connect()
        payload = json.dumps(
            {"type": KNOWLEDGE_INGEST_JOB, "document_id": str(document_id)}
        )
        await client.lpush(self.queue_name, payload)

    async def dequeue(self, *, timeout_seconds: int = 5) -> dict[str, Any] | None:
        client = await self.connect()
        try:
            item = await client.brpop(self.queue_name, timeout=timeout_seconds)
        except (TimeoutError, RedisTimeoutError):
            return None
        if item is None:
            return None
        _, raw = item
        return json.loads(raw)

    async def beat(self, *, ttl_seconds: int = 30) -> None:
        client = await self.connect()
        await client.set(
            WORKER_HEARTBEAT_KEY,
            datetime.now(UTC).isoformat(),
            ex=ttl_seconds,
        )

    async def heartbeat_alive(self) -> bool:
        client = await self.connect()
        value = await client.get(WORKER_HEARTBEAT_KEY)
        return value is not None
