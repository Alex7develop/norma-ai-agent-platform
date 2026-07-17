"""Stateless RAG assistant endpoint."""

import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAIError
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.rag_assistant import RagAssistantAgent
from app.api.dependencies import get_current_user, require_workspace_access
from app.database.auth_models import User
from app.database.session import get_db_session
from app.rag.container import retriever
from app.rag.embeddings import EmbeddingServiceError
from app.schemas.assistant import AssistantQuery, AssistantResponse
from app.services.llm import OpenRouterConfigurationError
from app.workflows.rag_assistant import RagAssistant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


async def get_rag_assistant() -> AsyncIterator[RagAssistantAgent]:
    """Create and close the request-scoped OpenRouter client."""

    try:
        workflow = RagAssistant(retriever)
    except OpenRouterConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        yield RagAssistantAgent(workflow)
    finally:
        await workflow.client.close()


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(
    payload: AssistantQuery,
    agent: Annotated[RagAssistantAgent, Depends(get_rag_assistant)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> AssistantResponse:
    """Answer from workspace knowledge through a LangGraph workflow."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    try:
        result = await agent.answer(
            workspace_id=str(payload.workspace_id),
            question=payload.question,
        )
    except OpenAIError as exc:
        logger.exception("OpenRouter request failed")
        raise HTTPException(
            status_code=502, detail="Language model request failed"
        ) from exc
    except (
        EmbeddingServiceError,
        ResponseHandlingException,
        UnexpectedResponse,
    ) as exc:
        logger.exception("Knowledge retrieval failed")
        raise HTTPException(
            status_code=503, detail="Knowledge retrieval failed"
        ) from exc

    return AssistantResponse(
        answer=result.answer,
        sources=result.sources,
        model=result.model,
    )
