"""Organization, project, and membership models."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, BigInteger, Text, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, PermissionRole, permission_role_enum

if TYPE_CHECKING:  # pragma: no cover
    from .content import Document, DocumentChunk, File, Instruction, Memory
    from .sharing import Permission, ShareLink
    from .redaction import RedactionRule, RedactionRun
    from .snapshots import Snapshot
    from .chats import ProjectChat
    from .audit import AuditLog
    from .budget import ProjectBudget
    from .usage import UsageLedger

__all__ = ["Organization", "Project", "ProjectMember"]


class Organization(Base):
    """Top level organization owning projects."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    projects: Mapped[list["Project"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class Project(Base):
    """Workspace project grouping files, chats, and policies."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, server_default=text("'active'"), nullable=False
    )
    visibility: Mapped[str] = mapped_column(
        Text, server_default=text("'private'"), nullable=False
    )
    budget_quota: Mapped[int | None] = mapped_column(BigInteger)
    current_instr_v: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped[Organization] = relationship(back_populates="projects")
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    instructions: Mapped[list["Instruction"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Instruction.version",
    )
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    files: Mapped[list["File"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    share_links: Mapped[list["ShareLink"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    redaction_rules: Mapped[list["RedactionRule"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    redaction_runs: Mapped[list["RedactionRun"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["Snapshot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    project_chats: Mapped[list["ProjectChat"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="project")
    project_budget: Mapped["ProjectBudget | None"] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
        single_parent=True,
    )
    usage_entries: Mapped[list["UsageLedger"]] = relationship(back_populates="project")


class ProjectMember(Base):
    """Membership mapping between users and projects."""

    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[PermissionRole] = mapped_column(permission_role_enum(), nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("auth.users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="members")

    __table_args__ = (Index("idx_project_members_user", "user_id"),)
