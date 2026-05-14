"""FastAPI application for the sharing service."""

from __future__ import annotations

import hmac
import uuid
from typing import Iterator, Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from . import schemas
from .models import Share
from .service import ShareDatabase, ShareService, ShareSettings, init_engine

__all__ = ["create_app", "ShareSettings"]


def create_app(settings: ShareSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = settings or ShareSettings.from_env()
    engine = init_engine(settings)
    database = ShareDatabase(engine=engine)

    app = FastAPI(title="Law Share Service", version="1.0.0")

    def get_session() -> Iterator[Session]:
        session = database.session()
        try:
            yield session
        finally:
            session.close()

    def get_service(session: Session = Depends(get_session)) -> ShareService:
        return ShareService(session=session, settings=settings)

    def get_current_actor(
        authorization: Optional[str] = Header(default=None),
        actor_id: Optional[str] = Header(default=None, alias="X-Actor-ID"),
    ) -> str:
        if not settings.management_api_key:
            raise HTTPException(
                status_code=503, detail="Share management API key is not configured"
            )
        scheme, _, token = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(
            token, settings.management_api_key
        ):
            raise HTTPException(status_code=401, detail="Authentication required")
        if not actor_id:
            raise HTTPException(status_code=401, detail="Actor identity required")
        return actor_id

    def request_domain(request: Request) -> Optional[str]:
        for header in ("origin", "referer"):
            raw = request.headers.get(header)
            if raw:
                parsed = urlparse(raw)
                if parsed.hostname:
                    return parsed.hostname
        host = request.headers.get("host")
        if not host:
            return None
        return host.split(":", 1)[0]

    @app.exception_handler(Exception)
    async def _handle_errors(request: Request, exc: Exception):  # type: ignore[override]
        if isinstance(exc, HTTPException):
            raise exc
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    @app.post("/v1/redactions/preview", response_model=schemas.RedactionPreviewResponse)
    def redaction_preview(
        request: schemas.RedactionPreviewRequest,
        service: ShareService = Depends(get_service),
    ) -> schemas.RedactionPreviewResponse:
        return service.preview_redaction(request)

    @app.post("/v1/redactions/apply", response_model=schemas.RedactionApplyResponse)
    def redaction_apply(
        request: schemas.RedactionApplyRequest,
        service: ShareService = Depends(get_service),
    ) -> schemas.RedactionApplyResponse:
        return service.apply_redaction(request)

    @app.post("/v1/shares", response_model=schemas.ShareResponse)
    def create_share(
        request: schemas.ShareCreateRequest,
        service: ShareService = Depends(get_service),
        actor_id: str = Depends(get_current_actor),
    ) -> schemas.ShareResponse:
        try:
            share = service.create_share(request, actor_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Resource not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        return _share_to_response(share)

    @app.get("/v1/shares/{share_id}", response_model=schemas.ShareResponse)
    def get_share(
        share_id: uuid.UUID,
        service: ShareService = Depends(get_service),
        actor_id: str = Depends(get_current_actor),
    ) -> schemas.ShareResponse:
        try:
            share = service.get_share(share_id, actor_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Share not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        return _share_to_response(share)

    @app.post("/v1/shares/{share_id}/revoke", response_model=schemas.ShareResponse)
    def revoke_share(
        share_id: uuid.UUID,
        request: schemas.ShareRevokeRequest,
        service: ShareService = Depends(get_service),
        actor_id: str = Depends(get_current_actor),
    ) -> schemas.ShareResponse:
        try:
            share = service.revoke_share(share_id, actor_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Share not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        return _share_to_response(share)

    @app.post(
        "/v1/shares/{share_id}/links", response_model=schemas.ShareLinkCreateResponse
    )
    def create_share_link(
        share_id: uuid.UUID,
        request: schemas.ShareLinkCreateRequest,
        service: ShareService = Depends(get_service),
        actor_id: str = Depends(get_current_actor),
    ) -> schemas.ShareLinkCreateResponse:
        try:
            return service.create_share_link(share_id, request, actor_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Share not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None

    @app.post("/v1/permissions/bulk", response_model=list[schemas.PermissionEntry])
    def bulk_permissions(
        entries: list[schemas.PermissionEntry],
        service: ShareService = Depends(get_service),
        actor_id: str = Depends(get_current_actor),
    ) -> list[schemas.PermissionEntry]:
        try:
            permissions = service.bulk_permissions(entries, actor_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Resource not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        return [
            schemas.PermissionEntry(
                resource_id=p.resource_id,
                principal_type=p.principal_type,
                principal_id=p.principal_id,
                role=p.role,
            )
            for p in permissions
        ]

    @app.get("/v1/audit", response_model=schemas.AuditLogResponse)
    def audit_logs(
        resource_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        service: ShareService = Depends(get_service),
        actor_id: str = Depends(get_current_actor),
    ) -> schemas.AuditLogResponse:
        try:
            logs = service.list_audit_logs(
                actor_id=actor_id, resource_id=resource_id, action=action
            )
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Resource not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        return schemas.AuditLogResponse(
            results=[
                schemas.AuditLogEntry.model_validate(log, from_attributes=True)
                for log in logs
            ]
        )

    @app.get("/v1/s/{token}", response_model=schemas.ShareAccessResponse)
    def access_link(
        token: str,
        request: Request = None,
        service: ShareService = Depends(get_service),
    ) -> schemas.ShareAccessResponse:
        ip = request.client.host if request and request.client else None
        domain = request_domain(request) if request else None
        try:
            link = service.access_via_token(token, domain=domain, ip=ip)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Link not found") from None
        except PermissionError as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from None
        share = link.share
        response = _share_to_response(share)
        return schemas.ShareAccessResponse(share=response, link_id=link.id)

    return app


def _share_to_response(share: Share) -> schemas.ShareResponse:
    resource = schemas.ResourceRead.model_validate(share.resource, from_attributes=True)
    links = [
        schemas.ShareLinkResponse.model_validate(link, from_attributes=True)
        for link in sorted(share.links, key=lambda share_link: share_link.created_at)
    ]
    return schemas.ShareResponse(
        id=share.id,
        resource=resource,
        mode=share.mode,
        allow_download=share.allow_download,
        allow_comments=share.allow_comments,
        is_live=share.is_live,
        created_by=share.created_by,
        created_at=share.created_at,
        expires_at=share.expires_at,
        revoked_at=share.revoked_at,
        links=links,
    )
