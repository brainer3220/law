"""SQLAlchemy models for the sharing and conversation services."""

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
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

__all__ = [
    "Base",
    "UUIDPrimaryKeyMixin",
    "Resource",
    "Share",
    "ShareLink",
    "Permission",
    "Redaction",
    "AuditLog",
    "Embed",
    "Chat",
    "Document",
    "Message",
    "MessageV2",
    "Stream",
    "Suggestion",
    "User",
    "Vote",
    "VoteV2",
    "ResourceType",
    "ShareMode",
    "PrincipalType",
    "PermissionRole",
]


class Base(DeclarativeBase):
    """Declarative base for all sharing models."""


class UUIDPrimaryKeyMixin:
    """Mixin providing a UUID primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
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


class Resource(UUIDPrimaryKeyMixin, Base):
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


class Share(UUIDPrimaryKeyMixin, Base):
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


class ShareLink(UUIDPrimaryKeyMixin, Base):
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


class Permission(UUIDPrimaryKeyMixin, Base):
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


class Redaction(UUIDPrimaryKeyMixin, Base):
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


class AuditLog(UUIDPrimaryKeyMixin, Base):
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


class Embed(UUIDPrimaryKeyMixin, Base):
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


# ---------------------------------------------------------------------------
# Conversation records
# ---------------------------------------------------------------------------


class User(UUIDPrimaryKeyMixin, Base):
    """Human owner for chats and documents."""

    __tablename__ = "User"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str | None] = mapped_column(String(255))

    chats: Mapped[list["Chat"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Chat(UUIDPrimaryKeyMixin, Base):
    """Chat session containing messages and votes."""

    __tablename__ = "Chat"

    created_at: Mapped[dt.datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32), server_default=text("'private'"), nullable=False
    )
    last_context: Mapped[dict | None] = mapped_column("lastContext", JSONB)

    user: Mapped[User] = relationship(back_populates="chats")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    messages_v2: Mapped[list["MessageV2"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    streams: Mapped[list["Stream"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )
    votes_v2: Mapped[list["VoteV2"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )


class Document(UUIDPrimaryKeyMixin, Base):
    """Document that suggestions can annotate."""

    __tablename__ = "Document"

    created_at: Mapped[dt.datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=False),
        primary_key=True,
        server_default=func.now(),
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    text_type: Mapped[str] = mapped_column(
        "text", String(32), server_default=text("'text'::character varying"), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="documents")
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Message(UUIDPrimaryKeyMixin, Base):
    """First generation message payloads."""

    __tablename__ = "Message"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        "chatId", ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    chat: Mapped[Chat] = relationship(back_populates="messages")
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageV2(UUIDPrimaryKeyMixin, Base):
    """Structured message payloads with parts and attachments."""

    __tablename__ = "Message_v2"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        "chatId", ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    parts: Mapped[dict] = mapped_column(JSON, nullable=False)
    attachments: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    chat: Mapped[Chat] = relationship(back_populates="messages_v2")
    votes: Mapped[list["VoteV2"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class Stream(UUIDPrimaryKeyMixin, Base):
    """Live stream sessions tied to a chat."""

    __tablename__ = "Stream"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        "chatId", ForeignKey("Chat.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    chat: Mapped[Chat] = relationship(back_populates="streams")


class Suggestion(UUIDPrimaryKeyMixin, Base):
    """User suggestions attached to a document."""

    __tablename__ = "Suggestion"

    document_id: Mapped[uuid.UUID] = mapped_column(
        "documentId", PGUUID(as_uuid=True), nullable=False
    )
    document_created_at: Mapped[dt.datetime] = mapped_column(
        "documentCreatedAt", DateTime(timezone=False), nullable=False
    )
    original_text: Mapped[str] = mapped_column("originalText", Text, nullable=False)
    suggested_text: Mapped[str] = mapped_column("suggestedText", Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(
        "isResolved", Boolean, server_default=text("false"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("User.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        "createdAt", DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="suggestions")
    user: Mapped[User] = relationship(back_populates="suggestions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["document_id", "document_created_at"],
            lambda: [Document.id, Document.created_at],
            name="Suggestion_document_fk",
            ondelete="CASCADE",
        ),
    )


class Vote(Base):
    """Legacy votes on v1 messages."""

    __tablename__ = "Vote"

    message_id: Mapped[uuid.UUID] = mapped_column(
        "messageId",
        ForeignKey("Message.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        "chatId",
        ForeignKey("Chat.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_upvoted: Mapped[bool] = mapped_column("isUpvoted", Boolean, nullable=False)

    chat: Mapped[Chat] = relationship(back_populates="votes")
    message: Mapped[Message] = relationship(back_populates="votes")

    __table_args__ = (
        ForeignKeyConstraint(
            ["message_id", "chat_id"],
            ["Message.id", "Message.chatId"],
            name="Vote_message_chat_fk",
            ondelete="CASCADE",
        ),
    )


class VoteV2(Base):
    """Votes targeting the second generation message table."""

    __tablename__ = "Vote_v2"

    message_id: Mapped[uuid.UUID] = mapped_column(
        "messageId",
        ForeignKey("Message_v2.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        "chatId",
        ForeignKey("Chat.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_upvoted: Mapped[bool] = mapped_column("isUpvoted", Boolean, nullable=False)

    chat: Mapped[Chat] = relationship(back_populates="votes_v2")
    message: Mapped[MessageV2] = relationship(back_populates="votes")

    __table_args__ = (
        ForeignKeyConstraint(
            ["message_id", "chat_id"],
            ["Message_v2.id", "Message_v2.chatId"],
            name="Vote_v2_message_chat_fk",
            ondelete="CASCADE",
        ),
    )
