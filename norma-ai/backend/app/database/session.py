"""Asynchronous SQLAlchemy engine and session lifecycle."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Connection creation is lazy; importing the app does not require PostgreSQL.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.debug,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide a request-scoped transaction boundary."""

    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
