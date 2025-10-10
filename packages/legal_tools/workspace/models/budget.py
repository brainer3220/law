"""Project budget configuration."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project

__all__ = ["ProjectBudget"]


class ProjectBudget(Base):
    """Budget configuration per project."""

    __tablename__ = "project_budgets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    period: Mapped[str] = mapped_column(
        Text, server_default=text("'monthly'"), nullable=False
    )
    token_limit: Mapped[int | None] = mapped_column(BigInteger)
    hardcap: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="project_budget")
