"""Knowledge retrieval boundary."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    """A ranked chunk returned by retrieval."""

    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Retriever(Protocol):
    """Interface consumed by future RAG use cases."""

    async def retrieve(
        self, query: str, *, limit: int = 10
    ) -> Sequence[RetrievedDocument]:
        """Return the most relevant document chunks."""

        ...
