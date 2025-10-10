"""Audit log model."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, ResourceType, resource_type_enum

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Organization, Project

__all__ = ["AuditLog"]


class AuditLog(Base):
    """Audit trail for workspace actions."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth.users.id"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE")
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[ResourceType | None] = mapped_column(resource_type_enum())
    resource_id: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSONB)

    project: Mapped["Project | None"] = relationship(back_populates="audit_logs")
    organization: Mapped["Organization | None"] = relationship()

    __table_args__ = (
        Index(
            "idx_audit_project",
            "project_id",
            "at",
            postgresql_using="btree",
        ),
        Index("idx_audit_action", "action"),
        Index(
            "idx_audit_meta",
            "meta",
            postgresql_using="gin",
            postgresql_ops={"meta": "jsonb_path_ops"},
        ),
    )
