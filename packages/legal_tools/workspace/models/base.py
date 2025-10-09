"""Shared SQLAlchemy base and enum helpers for workspace models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

from ..schema.enums import (
    PrincipalType,
    ResourceType,
    SensitivityLevel,
    PermissionRole,
    ShareMode,
    pg_enum,
)

__all__ = [
    "Base",
    "PermissionRole",
    "SensitivityLevel",
    "ShareMode",
    "PrincipalType",
    "ResourceType",
    "permission_role_enum",
    "sensitivity_level_enum",
    "share_mode_enum",
    "principal_type_enum",
    "resource_type_enum",
]


class Base(DeclarativeBase):
    """Declarative base class shared by all workspace models."""


# Enum helper factories -----------------------------------------------------

def permission_role_enum() -> PgEnum:
    """Return a configured ENUM for the ``permission_role`` type."""

    return pg_enum(PermissionRole)


def sensitivity_level_enum() -> PgEnum:
    """Return a configured ENUM for the ``sensitivity_level`` type."""

    return pg_enum(SensitivityLevel)


def share_mode_enum() -> PgEnum:
    """Return a configured ENUM for the ``share_mode`` type."""

    return pg_enum(ShareMode)


def principal_type_enum() -> PgEnum:
    """Return a configured ENUM for the ``principal_type`` type."""

    return pg_enum(PrincipalType)


def resource_type_enum() -> PgEnum:
    """Return a configured ENUM for the ``resource_type`` type."""

    return pg_enum(ResourceType)
