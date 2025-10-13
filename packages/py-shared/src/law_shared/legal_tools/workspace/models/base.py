"""Shared SQLAlchemy base and enum helpers for workspace models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from ..schema.enums import (
    PermissionRole,
    pg_enum,
)

__all__ = [
    "Base",
    "PermissionRole",
    "permission_role_enum",
]


class Base(DeclarativeBase):
    """Declarative base class shared by all workspace models."""


# Enum helper factories -----------------------------------------------------

def permission_role_enum() -> PgEnum:
    """Return a configured ENUM for the ``permission_role`` type."""

    return pg_enum(PermissionRole)
