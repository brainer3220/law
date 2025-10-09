"""Instruction, memory, file, and document domain models."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SensitivityLevel, sensitivity_level_enum

if TYPE_CHECKING:  # pragma: no cover
    from .projects import Project

__all__ = [
    "Instruction",
    "Memory",
    "File",
    "Document",
    "DocumentChunk",
]


class Instruction(Base):
    """Versioned system instructions for a project."""

    __tablename__ = "instructions"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="instructions")


class Memory(Base):
    """Project long-term memory key/value store."""

    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    k: Mapped[str] = mapped_column(Text, nullable=False)
    v: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    confidence: Mapped[float | None] = mapped_column(Float)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="memories")

    __table_args__ = (
        UniqueConstraint("project_id", "k", name="uq_memories_project_key"),
    )


class File(Base):
    """Files uploaded to a project."""

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    r2_key: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    mime: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(
        Integer, server_default=text("1"), nullable=False
    )
    sensitivity: Mapped[SensitivityLevel] = mapped_column(
        sensitivity_level_enum(),
        server_default=text("'internal'::sensitivity_level"),
        nullable=False,
    )
    checksum: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="files")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id", "r2_key", "version", name="uq_files_project_key_version"
        ),
    )


class Document(Base):
    """Logical document extracted from a file."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="documents")
    file: Mapped[File] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Full-text indexed chunk of a document."""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    page: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', immutable_unaccent(coalesce(heading, '') || ' ' || coalesce(body, '')))",
            persisted=True,
        ),
    )

    project: Mapped["Project"] = relationship(back_populates="chunks")
    document: Mapped[Document] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("idx_document_chunks_project", "project_id"),
        Index(
            "idx_document_chunks_tsv",
            "tsv",
            postgresql_using="gin",
        ),
        Index(
            "idx_document_chunks_trgm_heading",
            "heading",
            postgresql_using="gin",
            postgresql_ops={"heading": "gin_trgm_ops"},
        ),
        Index(
            "idx_document_chunks_trgm_body",
            "body",
            postgresql_using="gin",
            postgresql_ops={"body": "gin_trgm_ops"},
        ),
    )
