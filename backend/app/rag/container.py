"""Process-level RAG adapter composition and lifecycle."""

from qdrant_client import AsyncQdrantClient

from app.core.config import settings
from app.rag.embeddings import HttpEmbeddingProvider
from app.rag.retriever import QdrantRetriever
from app.rag.vectorstore import QdrantVectorStore

qdrant_client = AsyncQdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    check_compatibility=False,
)
embedding_provider = HttpEmbeddingProvider()
vector_store = QdrantVectorStore(qdrant_client)
retriever = QdrantRetriever(embedding_provider, qdrant_client)


async def close_rag_clients() -> None:
    """Close shared network clients during process shutdown."""

    await qdrant_client.close()
