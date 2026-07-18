"""RAG assistant endpoints with conversation memory."""

import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from openai import OpenAIError
from qdrant_client.http.exceptions import (
    ResponseHandlingException,
    UnexpectedResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.memory import MemoryAgent
from app.agents.rag_assistant import RagAssistantAgent
from app.api.dependencies import get_current_user, require_workspace_access
from app.database.auth_models import User
from app.database.session import get_db_session
from app.rag.container import retriever
from app.rag.embeddings import EmbeddingServiceError
from app.schemas.assistant import (
    AssistantQuery,
    AssistantResponse,
    ConversationMessageResponse,
    ConversationSummary,
)
from app.services.llm import OpenRouterConfigurationError
from app.services.memory import ConversationNotFound, MemoryService
from app.services.projects import ProjectService, SpaceNotFound
from app.workflows.rag_assistant import RagAssistant

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])


async def get_rag_assistant(
    _user: Annotated[User, Depends(get_current_user)],
) -> AsyncIterator[RagAssistantAgent]:
    """Create and close the request-scoped OpenRouter client after auth."""

    try:
        workflow = RagAssistant(retriever)
    except OpenRouterConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        yield RagAssistantAgent(workflow)
    finally:
        await workflow.client.close()


def get_memory_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MemoryService:
    return MemoryService(session)


@router.post("/query", response_model=AssistantResponse)
async def query_assistant(
    payload: AssistantQuery,
    agent: Annotated[RagAssistantAgent, Depends(get_rag_assistant)],
    memory_service: Annotated[MemoryService, Depends(get_memory_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> AssistantResponse:
    """Answer from workspace knowledge through a LangGraph workflow."""

    await require_workspace_access(
        session, user_id=user.id, workspace_id=payload.workspace_id
    )
    projects = ProjectService(session)
    try:
        if payload.space_id is None:
            space_id = await projects.default_space_id(
                workspace_id=payload.workspace_id, user_id=user.id
            )
        else:
            await projects.require_space(
                space_id=payload.space_id, workspace_id=payload.workspace_id
            )
            space_id = payload.space_id
    except SpaceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    memory = MemoryAgent(memory_service)
    try:
        conversation = await memory_service.get_or_create_conversation(
            workspace_id=payload.workspace_id,
            space_id=space_id,
            user_id=user.id,
            conversation_id=payload.conversation_id,
            title_seed=payload.question,
        )
        chat_turns, notes = await memory.load_for_assistant(
            workspace_id=payload.workspace_id,
            space_id=space_id,
            conversation_id=conversation.id,
            question=payload.question,
        )
        result = await agent.answer(
            workspace_id=str(payload.workspace_id),
            space_id=str(space_id),
            question=payload.question,
            chat_context=[
                {"role": turn.role, "content": turn.content} for turn in chat_turns
            ],
            workspace_notes=notes,
        )
        await memory_service.append_turn(
            conversation_id=conversation.id,
            user_content=payload.question,
            assistant_content=result.answer,
        )
        await session.commit()
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
        conversation_id=conversation.id,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    workspace_id: Annotated[UUID, Query()],
    memory_service: Annotated[MemoryService, Depends(get_memory_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
    space_id: Annotated[UUID | None, Query()] = None,
) -> list[ConversationSummary]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    conversations = await memory_service.list_conversations(
        workspace_id=workspace_id,
        user_id=user.id,
        space_id=space_id,
    )
    return [
        ConversationSummary(
            id=item.id,
            title=item.title,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in conversations
    ]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[ConversationMessageResponse],
)
async def list_conversation_messages(
    conversation_id: UUID,
    workspace_id: Annotated[UUID, Query()],
    memory_service: Annotated[MemoryService, Depends(get_memory_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ConversationMessageResponse]:
    await require_workspace_access(
        session, user_id=user.id, workspace_id=workspace_id
    )
    try:
        messages = await memory_service.list_messages(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            user_id=user.id,
        )
    except ConversationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [
        ConversationMessageResponse(
            id=message.id,
            role=message.role.value,
            content=message.content,
            created_at=message.created_at,
        )
        for message in messages
    ]
