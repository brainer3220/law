"""SQLAlchemy ORM models mirroring the Supabase workspace schema."""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
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
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import INET, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "Base",
    "Organization",
    "Project",
    "ProjectMember",
    "Instruction",
    "Memory",
    "File",
    "Document",
    "DocumentChunk",
    "Permission",
    "ShareLink",
    "RedactionRule",
    "RedactionRun",
    "RedactionRunItem",
    "Snapshot",
    "SnapshotFile",
    "ProjectChat",
    "AuditLog",
    "ProjectBudget",
    "UsageLedger",
    "PermissionRole",
    "SensitivityLevel",
    "ShareMode",
    "PrincipalType",
    "ResourceType",
]


class Base(DeclarativeBase):
    """Declarative base class shared by all workspace models."""


class PermissionRole(str, Enum):
    OWNER = "owner"
    MAINTAINER = "maintainer"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SECRET = "secret"


class ShareMode(str, Enum):
    PRIVATE = "private"
    ORG = "org"
    LINK = "link"
    DOMAIN = "domain"


class PrincipalType(str, Enum):
    USER = "user"
    ORG = "org"
    DOMAIN = "domain"
    GROUP = "group"
    LINK = "link"


class ResourceType(str, Enum):
    PROJECT = "project"
    FILE = "file"
    DOCUMENT = "document"
    MEMORY = "memory"
    INSTRUCTION = "instruction"
    CHAT = "chat"
    SNAPSHOT = "snapshot"


def permission_role_enum() -> PgEnum:
    """Return a configured ENUM for the permission_role type."""

    return PgEnum(PermissionRole, name="permission_role", create_type=False)


def sensitivity_level_enum() -> PgEnum:
    """Return a configured ENUM for the sensitivity_level type."""

    return PgEnum(SensitivityLevel, name="sensitivity_level", create_type=False)


def share_mode_enum() -> PgEnum:
    """Return a configured ENUM for the share_mode type."""

    return PgEnum(ShareMode, name="share_mode", create_type=False)


def principal_type_enum() -> PgEnum:
    """Return a configured ENUM for the principal_type type."""

    return PgEnum(PrincipalType, name="principal_type", create_type=False)


def resource_type_enum() -> PgEnum:
    """Return a configured ENUM for the resource_type type."""

    return PgEnum(ResourceType, name="resource_type", create_type=False)


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

    project: Mapped[Project] = relationship(back_populates="instructions")


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

    project: Mapped[Project] = relationship(back_populates="memories")

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

    project: Mapped[Project] = relationship(back_populates="files")
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

    project: Mapped[Project] = relationship(back_populates="documents")
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
            "to_tsvector('simple', unaccent(coalesce(heading, '') || ' ' || coalesce(body, '')))",
            persisted=True,
        ),
    )

    project: Mapped[Project] = relationship(back_populates="chunks")
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

    project: Mapped[Project] = relationship(back_populates="permissions")

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

    project: Mapped[Project] = relationship(back_populates="share_links")


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
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="redaction_rules")


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
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="redaction_runs")
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
        ForeignKey("auth.users.id"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="snapshots")
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
    file: Mapped[File] = relationship()


class ProjectChat(Base):
    """Association between projects and existing chats."""

    __tablename__ = "project_chats"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    added_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.users.id"), nullable=False
    )
    added_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="project_chats")


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

    project: Mapped[Project | None] = relationship(back_populates="audit_logs")
    organization: Mapped[Organization | None] = relationship()

    __table_args__ = (
        Index("idx_audit_project", "project_id", "at", postgresql_using="btree"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_meta", "meta", postgresql_using="gin"),
    )


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

    project: Mapped[Project] = relationship(back_populates="project_budget")


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
    chat_id: Mapped[uuid.UUID | None] = mapped_column()
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

    project: Mapped[Project] = relationship(back_populates="usage_entries")

    __table_args__ = (Index("idx_usage_project_at", "project_id", "at"),)
