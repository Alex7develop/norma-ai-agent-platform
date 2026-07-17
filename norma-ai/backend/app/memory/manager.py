"""Long-term memory boundary."""

from typing import Any, Protocol


class MemoryManager(Protocol):
    """Storage-neutral contract for future scoped memory operations."""

    async def remember(
        self, *, tenant_id: str, subject_id: str, value: dict[str, Any]
    ) -> str:
        """Persist a memory and return its identifier."""

        ...
