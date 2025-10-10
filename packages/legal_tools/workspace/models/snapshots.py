"""Snapshot models for reproducible project states."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project
    from .content import File

__all__ = ["Snapshot", "SnapshotFile"]


class Snapshot(Base):
    """Snapshot of project state for reproducibility."""

    __tablename__ = "snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(Text)
    instruction_ver: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID] = mapped_column(
        nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="snapshots")
    files: Mapped[list["SnapshotFile"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class SnapshotFile(Base):
    """Pinned file version inside a snapshot."""

    __tablename__ = "snapshot_files"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("snapshots.id", ondelete="CASCADE"), primary_key=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("files.id"), primary_key=True)
    file_version: Mapped[int] = mapped_column(Integer, primary_key=True)

    snapshot: Mapped[Snapshot] = relationship(back_populates="files")
    file: Mapped["File"] = relationship()
