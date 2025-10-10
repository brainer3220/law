"""Usage ledger entries."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project

__all__ = ["UsageLedger"]


class UsageLedger(Base):
    """Token and cost usage records."""

    __tablename__ = "usage_ledger"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_in: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), nullable=False
    )
    tokens_out: Mapped[int] = mapped_column(
        BigInteger, server_default=text("0"), nullable=False
    )
    cost_cents: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False
    )
    meta: Mapped[dict | None] = mapped_column(JSONB)

    project: Mapped["Project"] = relationship(back_populates="usage_entries")

    __table_args__ = (Index("idx_usage_project_at", "project_id", "at"),)
