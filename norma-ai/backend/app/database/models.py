"""Shared SQLAlchemy declarative base.

Domain models will be introduced with their migrations. Keeping only the base
here avoids inventing a persistence schema before product boundaries exist.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all persisted models."""
