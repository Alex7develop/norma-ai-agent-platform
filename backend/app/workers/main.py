"""Unified Redis worker for workflows and knowledge ingest jobs."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from app.core.logging import configure_logging
from app.database.session import SessionFactory
from app.rag.container import retriever
from app.services.knowledge import KnowledgeService
from app.services.launch_strategy import KnowledgeIngestAdapter, LaunchStrategyService
from app.services.llm import OpenRouterConfigurationError
from app.services.memory import MemoryService
from app.services.queue import (
    KNOWLEDGE_INGEST_JOB,
    LAUNCH_STRATEGY_JOB,
    RESEARCH_BRIEF_JOB,
    JobQueue,
)
from app.workflows.launch_strategy import LaunchStrategyWorkflow
from app.workflows.research_brief import ResearchBriefWorkflow

logger = logging.getLogger(__name__)


async def process_workflow_run(run_id: UUID) -> None:
    async with SessionFactory() as session:
        knowledge = KnowledgeService(session)
        memory = MemoryService(session)
        try:
            launch = LaunchStrategyWorkflow(
                retriever,
                KnowledgeIngestAdapter(knowledge, space_id=uuid4()),
            )
            brief = ResearchBriefWorkflow(
                retriever,
                KnowledgeIngestAdapter(knowledge, space_id=uuid4()),
            )
        except OpenRouterConfigurationError:
            logger.exception("OpenRouter is not configured for worker")
            return
        service = LaunchStrategyService(
            session,
            workflow=launch,
            research_brief=brief,
            knowledge=knowledge,
            memory=memory,
        )
        try:
            await service.execute_run(run_id=run_id)
        finally:
            await launch.client.close()
            await brief.client.close()


async def process_knowledge_ingest(document_id: UUID) -> None:
    async with SessionFactory() as session:
        service = KnowledgeService(session)
        await service.execute_ingest(document_id=document_id)


async def process_job(payload: dict[str, object]) -> None:
    job_type = payload.get("type")
    if job_type in {LAUNCH_STRATEGY_JOB, RESEARCH_BRIEF_JOB}:
        await process_workflow_run(UUID(str(payload["run_id"])))
        return
    if job_type == KNOWLEDGE_INGEST_JOB:
        await process_knowledge_ingest(UUID(str(payload["document_id"])))
        return
    logger.warning("Ignoring unknown job type: %s", job_type)


async def run_forever() -> None:
    configure_logging()
    queue = JobQueue()
    logger.info("Norma worker started")
    try:
        while True:
            await queue.beat()
            payload = await queue.dequeue(timeout_seconds=5)
            if payload is None:
                continue
            try:
                await process_job(payload)
            except Exception:
                logger.exception("Failed to process job: %s", payload)
            await queue.beat()
    finally:
        await queue.close()


def main() -> None:
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
