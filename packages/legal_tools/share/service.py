"""Service layer for the sharing API."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session, sessionmaker

from .models import AuditLog, Base, Permission, Resource, Share, ShareLink
from .redaction import RedactionEngine
from .schemas import (
    PermissionEntry,
    RedactionApplyRequest,
    RedactionApplyResponse,
    RedactionPreviewRequest,
    RedactionPreviewResponse,
    ShareCreateRequest,
    ShareLinkCreateRequest,
    ShareLinkCreateResponse,
)
from .tokens import GeneratedToken, generate_token

__all__ = ["ShareSettings", "ShareDatabase", "ShareService", "init_engine"]


@dataclass(slots=True)
class ShareSettings:
    """Runtime configuration for the sharing service."""

    database_url: str
    external_base_url: str = "http://localhost:8081"
    default_link_ttl_days: int = 14
    token_bytes: int = 16

    @classmethod
    def from_env(cls) -> "ShareSettings":
        import os

        database_url = (
            os.getenv("LAW_SHARE_DB_URL")
            or os.getenv("DATABASE_URL")
            or "sqlite+pysqlite:///./share.db"
        )
        external_base_url = os.getenv("LAW_SHARE_BASE_URL", "http://localhost:8081")
        default_ttl = int(os.getenv("LAW_SHARE_LINK_TTL_DAYS", "14"))
        token_bytes = int(os.getenv("LAW_SHARE_TOKEN_BYTES", "16"))
        return cls(
            database_url=database_url,
            external_base_url=external_base_url,
            default_link_ttl_days=default_ttl,
            token_bytes=token_bytes,
        )


def init_engine(settings: ShareSettings) -> Engine:
    """Create an SQLAlchemy engine with sensible defaults."""

    database_url = settings.database_url
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://") :]
    elif database_url.startswith("postgresql://") and "+" not in database_url.split("://", 1)[1].split("/", 1)[0]:
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    connect_args = {}
    engine_kwargs = {"future": True}
    if database_url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        engine_kwargs["poolclass"] = StaticPool
        connect_args["check_same_thread"] = False
    if connect_args:
        engine_kwargs["connect_args"] = connect_args
    engine = create_engine(database_url, pool_pre_ping=True, **engine_kwargs)
    Base.metadata.create_all(engine)
    return engine


@dataclass(slots=True)
class ShareDatabase:
    """Session factory wrapper."""

    engine: Engine
    _session_factory: sessionmaker | None = None

    def __post_init__(self) -> None:
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def session(self) -> Session:
        if self._session_factory is None:
            raise RuntimeError("Session factory not initialized")
        return self._session_factory()


@dataclass(slots=True)
class ShareService:
    """Encapsulates share-related operations."""

    session: Session
    settings: ShareSettings
    redaction_engine: RedactionEngine = RedactionEngine()

    # ---------------------------- redactions -----------------------------
    def preview_redaction(
        self, request: RedactionPreviewRequest
    ) -> RedactionPreviewResponse:
        preview = self.redaction_engine.preview(request.payloads)
        matches = [match.model_dump() for match in preview.matches]
        return RedactionPreviewResponse(redacted=preview.redacted, matches=matches)

    def apply_redaction(self, request: RedactionApplyRequest) -> RedactionApplyResponse:
        from .models import Redaction, ResourceType

        preview = self.redaction_engine.preview(request.payloads)
        resource = Resource(
            type=ResourceType(request.resource.type),
            owner_id=request.resource.owner_id,
            org_id=request.resource.org_id,
            title=request.resource.title,
            tags=request.resource.tags,
            version=request.resource.version,
            snapshot_of=request.resource.snapshot_of,
        )
        self.session.add(resource)
        self.session.flush()
        redaction = Redaction(
            resource_id=resource.id,
            rule_id="composite",
            preview_diff={
                "matches": [match.model_dump() for match in preview.matches],
                "redacted": preview.redacted,
            },
        )
        self.session.add(redaction)
        self._log(
            actor_id=request.actor_id,
            action="redaction.apply",
            resource_id=resource.id,
            context={"match_count": len(preview.matches)},
        )
        self.session.commit()
        from .schemas import ResourceRead

        return RedactionApplyResponse(
            resource=ResourceRead.model_validate(resource, from_attributes=True),
            redaction_id=redaction.id,
            redacted=preview.redacted,
        )

    # ---------------------------- shares -----------------------------
    def create_share(self, request: ShareCreateRequest) -> Share:
        from .models import ShareMode

        resource = self.session.get(Resource, request.resource_id)
        if not resource:
            raise NoResultFound("Resource not found")
        expires_at = request.expires_at
        if not expires_at:
            expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
                days=self.settings.default_link_ttl_days
            )
        share = Share(
            resource_id=request.resource_id,
            mode=ShareMode(request.mode),
            created_by=request.actor_id,
            allow_download=request.allow_download,
            allow_comments=request.allow_comments,
            is_live=request.is_live,
            expires_at=expires_at,
        )
        self.session.add(share)
        self.session.flush()
        if request.permissions:
            self._upsert_permissions(request.permissions)
        self._log(
            actor_id=request.actor_id,
            action="share.create",
            resource_id=resource.id,
            context={"share_id": str(share.id), "mode": share.mode.value},
        )
        if request.create_link:
            self._create_link(share, request.link_domain_whitelist)
        self.session.commit()
        return share

    def revoke_share(self, share_id: uuid.UUID, actor_id: str) -> Share:
        share = self._get_share_or_raise(share_id)
        now = dt.datetime.now(dt.timezone.utc)
        share.revoked_at = now
        for link in share.links:
            link.revoked_at = now
        self._log(
            actor_id=actor_id,
            action="share.revoke",
            resource_id=share.resource_id,
            context={"share_id": str(share.id)},
        )
        self.session.commit()
        return share

    def create_share_link(
        self, share_id: uuid.UUID, request: ShareLinkCreateRequest, actor_id: str
    ) -> ShareLinkCreateResponse:
        share = self._get_share_or_raise(share_id)
        token = self._create_link(share, request.domain_whitelist)
        self._log(
            actor_id=actor_id,
            action="share.link.create",
            resource_id=share.resource_id,
            context={"share_id": str(share.id)},
        )
        self.session.commit()
        url = f"{self.settings.external_base_url.rstrip('/')}/s/{token.token}"
        from .schemas import ShareLinkResponse

        return ShareLinkCreateResponse(
            token=token.token,
            url=url,
            link=ShareLinkResponse.model_validate(
                share.links[-1], from_attributes=True
            ),
        )

    def get_share(self, share_id: uuid.UUID) -> Share:
        return self._get_share_or_raise(share_id)

    def access_via_token(
        self, token: str, domain: Optional[str] = None, ip: str | None = None
    ) -> ShareLink:
        hashed = sha256(token.encode("utf-8")).hexdigest()
        stmt = select(ShareLink).where(ShareLink.token_hash == hashed)
        link = self.session.scalars(stmt).first()
        if not link:
            raise NoResultFound("Link not found")
        share = link.share
        now = dt.datetime.now(dt.timezone.utc)
        revoked_at = share.revoked_at
        expires_at = share.expires_at
        if revoked_at and revoked_at.tzinfo is None:
            revoked_at = revoked_at.replace(tzinfo=dt.timezone.utc)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
        if revoked_at or (expires_at and expires_at < now):
            raise PermissionError("Share expired or revoked")
        if link.revoked_at:
            raise PermissionError("Link revoked")
        if link.domain_whitelist and domain and domain not in link.domain_whitelist:
            raise PermissionError("Domain not allowed")
        self._log(
            actor_id=None,
            action="share.link.view",
            resource_id=share.resource_id,
            context={"share_id": str(share.id), "link_id": str(link.id)},
            ip=ip,
        )
        self.session.commit()
        return link

    def bulk_permissions(self, entries: Iterable[PermissionEntry]) -> List[Permission]:
        updated: List[Permission] = []
        for entry in entries:
            permission = (
                self.session.query(Permission)
                .filter(
                    Permission.resource_id == entry.resource_id,
                    Permission.principal_type == entry.principal_type,
                    Permission.principal_id == entry.principal_id,
                )
                .one_or_none()
            )
            if permission:
                permission.role = entry.role
            else:
                permission = Permission(
                    resource_id=entry.resource_id,
                    principal_type=entry.principal_type,
                    principal_id=entry.principal_id,
                    role=entry.role,
                )
                self.session.add(permission)
            updated.append(permission)
        self.session.commit()
        return updated

    def list_audit_logs(
        self, *, resource_id: Optional[uuid.UUID] = None, action: Optional[str] = None
    ) -> List[AuditLog]:
        stmt = select(AuditLog)
        if resource_id:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.order_by(AuditLog.created_at.desc())
        return list(self.session.scalars(stmt))

    # ---------------------------- helpers -----------------------------
    def _create_link(
        self, share: Share, domain_whitelist: Optional[List[str]]
    ) -> GeneratedToken:
        token = generate_token(self.settings.token_bytes)
        link = ShareLink(
            share_id=share.id,
            token_hash=token.token_hash,
            domain_whitelist=domain_whitelist,
        )
        self.session.add(link)
        self.session.flush()
        return token

    def _get_share_or_raise(self, share_id: uuid.UUID) -> Share:
        share = self.session.get(Share, share_id)
        if not share:
            raise NoResultFound("Share not found")
        return share

    def _upsert_permissions(self, entries: Iterable[PermissionEntry]) -> None:
        for entry in entries:
            permission = (
                self.session.query(Permission)
                .filter(
                    Permission.resource_id == entry.resource_id,
                    Permission.principal_type == entry.principal_type,
                    Permission.principal_id == entry.principal_id,
                )
                .one_or_none()
            )
            if permission:
                permission.role = entry.role
            else:
                permission = Permission(
                    resource_id=entry.resource_id,
                    principal_type=entry.principal_type,
                    principal_id=entry.principal_id,
                    role=entry.role,
                )
                self.session.add(permission)

    def _log(
        self,
        *,
        actor_id: Optional[str],
        action: str,
        resource_id: Optional[uuid.UUID],
        context: Optional[dict] = None,
        ip: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_id=resource_id,
            context_json=context,
            ip=ip,
        )
        self.session.add(entry)
