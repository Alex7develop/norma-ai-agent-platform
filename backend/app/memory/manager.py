"""Long-term memory boundary.

Concrete persistence lives in `app.services.memory.MemoryService` and the
`MemoryAgent` facade. Orchestration code should depend on those application
boundaries rather than storage details.
"""

from typing import Any, Protocol


class MemoryManager(Protocol):
    """Storage-neutral contract for scoped memory operations."""

    async def remember(
        self, *, tenant_id: str, subject_id: str, value: dict[str, Any]
    ) -> str:
        """Persist a memory and return its identifier."""

        ...
