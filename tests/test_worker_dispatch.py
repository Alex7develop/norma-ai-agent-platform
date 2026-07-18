"""Worker job dispatch tests."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.queue import (
    KNOWLEDGE_INGEST_JOB,
    LAUNCH_STRATEGY_JOB,
    RESEARCH_BRIEF_JOB,
)
from app.workers.main import process_job


@pytest.mark.asyncio
async def test_process_job_routes_knowledge_ingest() -> None:
    document_id = uuid4()
    with patch(
        "app.workers.main.process_knowledge_ingest", new_callable=AsyncMock
    ) as handler:
        await process_job(
            {"type": KNOWLEDGE_INGEST_JOB, "document_id": str(document_id)}
        )
    handler.assert_awaited_once_with(document_id)


@pytest.mark.asyncio
async def test_process_job_routes_launch_strategy() -> None:
    run_id = uuid4()
    with patch(
        "app.workers.main.process_workflow_run", new_callable=AsyncMock
    ) as handler:
        await process_job({"type": LAUNCH_STRATEGY_JOB, "run_id": str(run_id)})
    handler.assert_awaited_once_with(run_id)


@pytest.mark.asyncio
async def test_process_job_routes_research_brief() -> None:
    run_id = uuid4()
    with patch(
        "app.workers.main.process_workflow_run", new_callable=AsyncMock
    ) as handler:
        await process_job({"type": RESEARCH_BRIEF_JOB, "run_id": str(run_id)})
    handler.assert_awaited_once_with(run_id)
