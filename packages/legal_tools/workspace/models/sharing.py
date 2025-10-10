"""Sharing and permission related models."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import (
    Base,
    PermissionRole,
    ShareMode,
    PrincipalType,
    permission_role_enum,
    share_mode_enum,
    principal_type_enum,
)

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project

__all__ = ["Permission", "ShareLink"]


class Permission(Base):
    """Project-level role assignment to principals."""

    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    principal_type: Mapped[PrincipalType] = mapped_column(
        principal_type_enum(), nullable=False
    )
    principal_id: Mapped[str | None] = mapped_column(Text)
    role: Mapped[PermissionRole] = mapped_column(permission_role_enum(), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="permissions")

    __table_args__ = (Index("idx_permissions_project", "project_id"),)


class ShareLink(Base):
    """Share link with optional domain restrictions."""

    __tablename__ = "share_links"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mode: Mapped[ShareMode] = mapped_column(share_mode_enum(), nullable=False)
    domains: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]"), nullable=False
    )
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="share_links")
