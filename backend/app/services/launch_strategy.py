"""Orchestrate Launch Strategy runs, persistence, and knowledge ingest."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.workflow_models import (
    ArtifactKind,
    WorkflowArtifact,
    WorkflowRun,
    WorkflowStatus,
)
from app.services.knowledge import KnowledgeService
from app.workflows.launch_strategy import LaunchStrategyResult, LaunchStrategyWorkflow


class WorkflowRunNotFound(LookupError):
    """Raised when a workspace-scoped workflow run does not exist."""


@dataclass(frozen=True, slots=True)
class KnowledgeIngestAdapter:
    """Adapt KnowledgeService to the ExecutionAgent persister port."""

    knowledge: KnowledgeService

    async def persist_markdown(
        self,
        *,
        workspace_id: UUID,
        filename: str,
        content: str,
    ) -> UUID:
        indexed = await self.knowledge.ingest(
            workspace_id=workspace_id,
            filename=filename,
            content_type="text/markdown",
            data=content.encode("utf-8"),
        )
        return indexed.id


class LaunchStrategyService:
    """Create, execute, and load Launch Strategy workflow runs."""

    def __init__(
        self,
        session: AsyncSession,
        workflow: LaunchStrategyWorkflow | None = None,
        knowledge: KnowledgeService | None = None,
    ) -> None:
        self.session = session
        self.workflow = workflow
        self.knowledge = knowledge

    async def run(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        brief: str,
        product_name: str | None = None,
    ) -> tuple[WorkflowRun, str]:
        """Execute the coordinator synchronously and persist artifacts."""

        if self.workflow is None or self.knowledge is None:
            raise RuntimeError("Launch strategy workflow is not configured")

        run = WorkflowRun(
            workspace_id=workspace_id,
            user_id=user_id,
            workflow_type=LaunchStrategyWorkflow.WORKFLOW_TYPE,
            status=WorkflowStatus.RUNNING,
            brief=brief.strip(),
            product_name=(product_name or None),
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)

        try:
            # Rebind persister to this request's knowledge session.
            self.workflow.persister = KnowledgeIngestAdapter(self.knowledge)
            self.workflow.execution.persister = self.workflow.persister
            result = await self.workflow.invoke(
                workspace_id=str(workspace_id),
                brief=brief,
                product_name=product_name,
            )
            await self._persist_result(run, result)
            run.status = WorkflowStatus.COMPLETED
            run.product_name = result.product_name
            run.error = None
            await self.session.commit()
        except Exception as exc:
            run.status = WorkflowStatus.FAILED
            run.error = f"{type(exc).__name__}: workflow failed"
            await self.session.commit()
            raise

        loaded = await self.get_run(run_id=run.id, workspace_id=workspace_id)
        return loaded, result.model

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
