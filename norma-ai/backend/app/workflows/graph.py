"""LangGraph composition boundary.

Concrete graphs belong to product use cases and will be added only after their
state, failure, approval, and persistence semantics are defined.
"""

from typing import Any, Protocol


class Workflow(Protocol):
    """Framework-neutral interface exposed by a compiled workflow."""

    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute a workflow from the supplied state."""

        ...
