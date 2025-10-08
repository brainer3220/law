"""SQLAlchemy models for the sharing service."""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "Base",
    "Resource",
    "Share",
    "ShareLink",
    "Permission",
    "Redaction",
    "AuditLog",
    "Embed",
    "ResourceType",
    "ShareMode",
    "PrincipalType",
    "PermissionRole",
]


class Base(DeclarativeBase):
    """Declarative base with UUID primary key convenience."""

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4, primary_key=True, index=True
    )


class ResourceType(str, Enum):
    CONVERSATION = "conversation"
    PROMPT = "prompt"
    SYSTEM_PROMPT = "system_prompt"
    AGENT = "agent"
    WORKFLOW = "workflow"
    FILE = "file"
    ARTIFACT = "artifact"
    BOARD = "board"
    DATASET = "dataset"


class ShareMode(str, Enum):
    PRIVATE = "private"
    ORG = "org"
    UNLISTED = "unlisted"
    PUBLIC = "public"
    EMBED = "embed"


class PrincipalType(str, Enum):
    USER = "user"
    TEAM = "team"
    ORG = "org"
    LINK = "link"


class PermissionRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    COMMENTER = "commenter"
    VIEWER = "viewer"
    GUEST = "guest"


class Resource(Base):
    """Shareable resource metadata."""

    __tablename__ = "resources"

    type: Mapped[ResourceType] = mapped_column(SqlEnum(ResourceType), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(512))
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    version: Mapped[str | None] = mapped_column(String(128))
    snapshot_of: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    shares: Mapped[list["Share"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    redactions: Mapped[list["Redaction"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class Share(Base):
    """Sharing configuration for a resource."""

    __tablename__ = "shares"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[ShareMode] = mapped_column(SqlEnum(ShareMode), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    allow_download: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    resource: Mapped[Resource] = relationship(back_populates="shares")
    links: Mapped[list["ShareLink"]] = relationship(
        back_populates="share", cascade="all, delete-orphan"
    )
    embeds: Mapped[list["Embed"]] = relationship(
        back_populates="share", cascade="all, delete-orphan"
    )


class ShareLink(Base):
    """Tokenized access link for a share."""

    __tablename__ = "share_links"

    share_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shares.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    domain_whitelist: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    share: Mapped[Share] = relationship(back_populates="links")

    __table_args__ = (
        Index("ix_share_links_share_id", "share_id"),
        Index("ix_share_links_token_hash", "token_hash", unique=True),
    )


class Permission(Base):
    """Access control list entry."""

    __tablename__ = "permissions"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    principal_type: Mapped[PrincipalType] = mapped_column(
        SqlEnum(PrincipalType), nullable=False
    )
    principal_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[PermissionRole] = mapped_column(
        SqlEnum(PermissionRole), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    resource: Mapped[Resource] = relationship(back_populates="permissions")

    __table_args__ = (
        Index(
            "ix_permissions_principal",
            "principal_type",
            "principal_id",
        ),
    )


class Redaction(Base):
    """Applied redaction snapshot for a resource."""

    __tablename__ = "redactions"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[str | None] = mapped_column(String(64))
    preview_diff: Mapped[dict] = mapped_column(JSON, nullable=False)
    applied_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    resource: Mapped[Resource] = relationship(back_populates="redactions")

    __table_args__ = (Index("ix_redactions_resource_id", "resource_id"),)


class AuditLog(Base):
    """Audit events covering share lifecycle actions."""

    __tablename__ = "audit_logs"

    actor_id: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resources.id"))
    context_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ip: Mapped[str | None] = mapped_column(String(64))
    ua: Mapped[str | None] = mapped_column(Text)

    resource: Mapped[Resource | None] = relationship()

    __table_args__ = (
        Index("ix_audit_logs_resource_id", "resource_id"),
        Index("ix_audit_logs_action", "action"),
    )


class Embed(Base):
    """Embed configuration for a share."""

    __tablename__ = "embeds"

    share_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shares.id", ondelete="CASCADE"), nullable=False
    )
    jwt_kid: Mapped[str | None] = mapped_column(String(64))
    domain: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    share: Mapped[Share] = relationship(back_populates="embeds")

    __table_args__ = (Index("ix_embeds_share_id", "share_id"),)
