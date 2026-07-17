"""Vector persistence boundary."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """Provider-neutral vector payload."""

    id: str
    vector: Sequence[float]
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    """Operations required from a vector database adapter."""

    async def upsert(self, records: Sequence[VectorRecord]) -> None:
        """Insert or update vector records."""

        ...
