"""Memory agent facade tests."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agents.memory import MemoryAgent
from app.services.memory import ChatTurn


@pytest.mark.asyncio
async def test_memory_agent_loads_chat_and_notes() -> None:
    service = AsyncMock()
    conversation_id = uuid4()
    workspace_id = uuid4()
    service.load_chat_context.return_value = [
        ChatTurn(role="user", content="Hello"),
        ChatTurn(role="assistant", content="Hi"),
    ]
    service.load_workspace_notes.return_value = ["Prior launch summary"]

    agent = MemoryAgent(service)
    result = await agent.invoke(
        {
            "workspace_id": str(workspace_id),
            "conversation_id": str(conversation_id),
        }
    )

    assert result["chat_context"][0]["content"] == "Hello"
    assert result["workspace_notes"] == ["Prior launch summary"]
    service.load_chat_context.assert_awaited_once()
    service.load_workspace_notes.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_agent_remembers_workflow() -> None:
    service = AsyncMock()
    memory_id = uuid4()
    service.remember_workflow_summary.return_value = AsyncMock(id=memory_id)
    # remember returns WorkspaceMemory-like object
    service.remember_workflow_summary.return_value = type(
        "M", (), {"id": memory_id}
    )()

    agent = MemoryAgent(service)
    result = await agent.invoke(
        {
            "action": "remember_workflow",
            "workspace_id": str(uuid4()),
            "run_id": str(uuid4()),
            "summary_md": "Done",
        }
    )

    assert result["memory_id"] == str(memory_id)
    service.remember_workflow_summary.assert_awaited_once()
