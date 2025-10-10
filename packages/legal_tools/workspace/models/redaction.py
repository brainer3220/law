"""Redaction rules and execution logs."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project

__all__ = ["RedactionRule", "RedactionRun", "RedactionRunItem"]


class RedactionRule(Base):
    """Pattern-based masking rules for project content."""

    __tablename__ = "redaction_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    pattern: Mapped[str] = mapped_column(Text, nullable=False)
    replacement: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(
        Text, server_default=text("'all'"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="redaction_rules")


class RedactionRun(Base):
    """Execution log for redaction operations."""

    __tablename__ = "redaction_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    input_type: Mapped[str] = mapped_column(Text, nullable=False)
    input_ref: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, server_default=text("'queued'"), nullable=False
    )
    stats: Mapped[dict | None] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID] = mapped_column(
        nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="redaction_runs")
    items: Mapped[list["RedactionRunItem"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class RedactionRunItem(Base):
    """Association table between redaction runs and applied rules."""

    __tablename__ = "redaction_run_items"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("redaction_runs.id", ondelete="CASCADE"), primary_key=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("redaction_rules.id", ondelete="CASCADE"), primary_key=True
    )
    target_ref: Mapped[str] = mapped_column(Text, primary_key=True)
    count: Mapped[int | None] = mapped_column(Integer)

    run: Mapped[RedactionRun] = relationship(back_populates="items")
    rule: Mapped[RedactionRule] = relationship()
