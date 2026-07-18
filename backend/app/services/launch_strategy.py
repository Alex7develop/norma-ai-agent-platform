"""Orchestrate workflow runs, persistence, and knowledge ingest."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.database.workflow_models import (
    ArtifactKind,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowStatus,
)
from app.services.knowledge import KnowledgeService
from app.services.memory import MemoryService
from app.services.queue import JobQueue
from app.workflows.launch_strategy import LaunchStrategyResult, LaunchStrategyWorkflow
from app.workflows.research_brief import ResearchBriefResult, ResearchBriefWorkflow


class WorkflowRunNotFound(LookupError):
    """Raised when a workspace-scoped workflow run does not exist."""


@dataclass(frozen=True, slots=True)
class KnowledgeIngestAdapter:
    """Adapt KnowledgeService to the ExecutionAgent persister port."""

    knowledge: KnowledgeService
    space_id: UUID

    async def persist_markdown(
        self,
        *,
        workspace_id: UUID,
        filename: str,
        content: str,
    ) -> UUID:
        indexed = await self.knowledge.ingest(
            workspace_id=workspace_id,
            space_id=self.space_id,
            filename=filename,
            content_type="text/markdown",
            data=content.encode("utf-8"),
        )
        return indexed.id


class LaunchStrategyService:
    """Create, enqueue, execute, and load workspace workflow runs."""

    def __init__(
        self,
        session: AsyncSession,
        workflow: LaunchStrategyWorkflow | None = None,
        research_brief: ResearchBriefWorkflow | None = None,
        knowledge: KnowledgeService | None = None,
        memory: MemoryService | None = None,
        queue: JobQueue | None = None,
    ) -> None:
        self.session = session
        self.workflow = workflow
        self.research_brief = research_brief
        self.knowledge = knowledge
        self.memory = memory
        self.queue = queue or JobQueue()

    async def enqueue(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        brief: str,
        product_name: str | None = None,
        space_id: UUID | None = None,
        workflow_type: str = LaunchStrategyWorkflow.WORKFLOW_TYPE,
    ) -> WorkflowRun:
        """Persist a pending run and push it onto the Redis queue."""

        if space_id is None:
            raise ValueError("space_id is required")
        if workflow_type not in {
            LaunchStrategyWorkflow.WORKFLOW_TYPE,
            ResearchBriefWorkflow.WORKFLOW_TYPE,
        }:
            raise ValueError(f"Unsupported workflow_type: {workflow_type}")

        run = WorkflowRun(
            workspace_id=workspace_id,
            space_id=space_id,
            user_id=user_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.PENDING,
            brief=brief.strip(),
            product_name=(product_name or None),
            current_step="queued",
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        # Avoid async lazy-load when the API serializes a brand-new pending run.
        set_committed_value(run, "artifacts", [])
        if workflow_type == ResearchBriefWorkflow.WORKFLOW_TYPE:
            await self.queue.enqueue_research_brief(run_id=run.id)
        else:
            await self.queue.enqueue_launch_strategy(run_id=run.id)
        return run

    async def execute_run(self, *, run_id: UUID) -> WorkflowRun:
        """Worker entrypoint: load a pending run and execute the graph."""

        if self.knowledge is None:
            raise RuntimeError("Workflow knowledge service is not configured")

        run = await self.session.scalar(
            select(WorkflowRun).where(WorkflowRun.id == run_id)
        )
        if run is None:
            raise WorkflowRunNotFound("Workflow run not found")

        run.status = WorkflowStatus.RUNNING
        run.current_step = "starting"
        run.error = None
        await self.session.commit()

        async def on_progress(step: str) -> None:
            run.current_step = step
            await self.session.commit()

        persister = KnowledgeIngestAdapter(self.knowledge, space_id=run.space_id)

        try:
            if run.workflow_type == ResearchBriefWorkflow.WORKFLOW_TYPE:
                if self.research_brief is None:
                    raise RuntimeError("Research brief workflow is not configured")
                self.research_brief.on_progress = on_progress
                self.research_brief.persister = persister
                result = await self.research_brief.invoke(
                    workspace_id=str(run.workspace_id),
                    space_id=str(run.space_id),
                    brief=run.brief,
                    product_name=run.product_name,
                )
                await self._persist_research_brief_result(run, result)
                if self.memory is not None:
                    await self.memory.remember_workflow_summary(
                        workspace_id=run.workspace_id,
                        space_id=run.space_id,
                        run_id=run.id,
                        summary_md=(
                            "Research Brief completed for "
                            f"**{result.product_name}**.\n\n"
                            f"Brief: {run.brief.strip()[:500]}\n\n"
                            f"Saved as `{result.pack_filename}` "
                            f"(document_id={result.document_id})."
                        ),
                    )
                run.product_name = result.product_name
            else:
                if self.workflow is None:
                    raise RuntimeError("Launch strategy workflow is not configured")
                self.workflow.on_progress = on_progress
                self.workflow.persister = persister
                self.workflow.execution.persister = persister
                result = await self.workflow.invoke(
                    workspace_id=str(run.workspace_id),
                    space_id=str(run.space_id),
                    brief=run.brief,
                    product_name=run.product_name,
                )
                await self._persist_result(run, result)
                if self.memory is not None:
                    await self.memory.remember_workflow_summary(
                        workspace_id=run.workspace_id,
                        space_id=run.space_id,
                        run_id=run.id,
                        summary_md=(
                            "Launch Strategy completed for "
                            f"**{result.product_name}**.\n\n"
                            f"Brief: {run.brief.strip()[:500]}\n\n"
                            f"Pack saved as `{result.pack_filename}` "
                            f"(document_id={result.document_id})."
                        ),
                    )
                run.product_name = result.product_name

            run.status = WorkflowStatus.COMPLETED
            run.current_step = "done"
            run.error = None
            await self.session.commit()
        except Exception as exc:
            run.status = WorkflowStatus.FAILED
            run.current_step = "failed"
            run.error = f"{type(exc).__name__}: workflow failed"
            await self.session.commit()
            raise

        return await self.get_run(run_id=run.id, workspace_id=run.workspace_id)

    async def _persist_result(
        self,
        run: WorkflowRun,
        result: LaunchStrategyResult,
    ) -> None:
        kind_map = {
            "research": ArtifactKind.RESEARCH,
            "competitors": ArtifactKind.COMPETITORS,
            "positioning": ArtifactKind.POSITIONING,
            "roadmap": ArtifactKind.ROADMAP,
            "marketing": ArtifactKind.MARKETING,
            "business_model": ArtifactKind.BUSINESS_MODEL,
            "financial": ArtifactKind.FINANCIAL,
            "prd": ArtifactKind.PRD,
            "tech_spec": ArtifactKind.TECH_SPEC,
            "cursor_prompts": ArtifactKind.CURSOR_PROMPTS,
            "linkedin": ArtifactKind.LINKEDIN,
            "telegram": ArtifactKind.TELEGRAM,
            "pack": ArtifactKind.PACK,
        }
        for artifact in result.artifacts:
            self.session.add(
                WorkflowArtifact(
                    run_id=run.id,
                    kind=kind_map[artifact.kind],
                    title=artifact.title,
                    content_md=artifact.content_md,
                    document_id=artifact.document_id,
                )
            )
        await self.session.flush()

    async def _persist_research_brief_result(
        self,
        run: WorkflowRun,
        result: ResearchBriefResult,
    ) -> None:
        kind_map = {
            "research": ArtifactKind.RESEARCH,
            "competitors": ArtifactKind.COMPETITORS,
            "pack": ArtifactKind.PACK,
        }
        for artifact in result.artifacts:
            self.session.add(
                WorkflowArtifact(
                    run_id=run.id,
                    kind=kind_map[artifact.kind],
                    title=artifact.title,
                    content_md=artifact.content_md,
                    document_id=artifact.document_id,
                )
            )
        await self.session.flush()

    async def get_run(
        self,
        *,
        run_id: UUID,
        workspace_id: UUID,
    ) -> WorkflowRun:
        run = await self.session.scalar(
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.artifacts))
            .where(
                WorkflowRun.id == run_id,
                WorkflowRun.workspace_id == workspace_id,
            )
        )
        if run is None:
            raise WorkflowRunNotFound("Workflow run not found")
        return run

    async def list_runs(
        self,
        *,
        workspace_id: UUID,
        limit: int = 30,
        space_id: UUID | None = None,
    ) -> list[WorkflowRun]:
        filters = [WorkflowRun.workspace_id == workspace_id]
        if space_id is not None:
            filters.append(WorkflowRun.space_id == space_id)
        query = (
            select(WorkflowRun)
            .where(*filters)
            .order_by(WorkflowRun.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.scalars(query)).all()
        return list(rows)
