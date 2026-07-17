"""Shared SQLAlchemy declarative base and model registry."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all persisted models."""


# Import model modules after Base is defined so Alembic sees every table in
# Base.metadata without introducing circular imports.
from app.database import document_models as document_models  # noqa: E402, F401
