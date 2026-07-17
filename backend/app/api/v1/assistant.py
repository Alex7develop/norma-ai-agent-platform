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

from app.agents.rag_assistant import RagAssistantAgent
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
) -> AssistantResponse:
    """Answer from workspace knowledge through a LangGraph workflow."""

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
