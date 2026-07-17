"""Contracts for future agents; no agent implementation lives here yet."""

from typing import Any, Protocol


class Agent(Protocol):
    """Minimal boundary that orchestration code may depend on."""

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Process workflow state and return the resulting state."""

        ...
