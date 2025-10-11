"""Instruction, memory, file, and document domain models."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project

__all__ = [
    "Instruction",
    "ProjectUpdateFile",
    "Update",
]


class Instruction(Base):
    """Versioned system instructions for a project."""

    __tablename__ = "instructions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", onupdate="NO ACTION", ondelete="CASCADE"),
        primary_key=True,
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tsv: Mapped[str | None] = mapped_column(TSVECTOR)

    project: Mapped["Project"] = relationship(back_populates="instructions")


class ProjectUpdateFile(Base):
    """Project update file metadata stored in R2."""

    __tablename__ = "project_update_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bucket: Mapped[str] = mapped_column(
        Text, server_default=text("'lawai-prod'"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    version_id: Mapped[str | None] = mapped_column(Text)
    etag: Mapped[str | None] = mapped_column(Text)
    sha256_hex: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    content_disp: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    cdn_path: Mapped[str | None] = mapped_column(Text)

    updates: Mapped[list["Update"]] = relationship(back_populates="project_update_file")


class Update(Base):
    """Project updates with optional file attachments."""

    __tablename__ = "updates"
    __table_args__ = (
        Index("updates_index_0", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", onupdate="NO ACTION", ondelete="CASCADE")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column()
    body: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    project_update_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "project_update_files.id", onupdate="NO ACTION", ondelete="SET NULL"
        )
    )

    project: Mapped["Project | None"] = relationship(back_populates="updates")
    project_update_file: Mapped["ProjectUpdateFile | None"] = relationship(
        back_populates="updates"
    )
