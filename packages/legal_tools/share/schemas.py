"""Pydantic schemas for the sharing API."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import PermissionRole, PrincipalType, ShareMode

__all__ = [
    "ResourceCreate",
    "ResourceRead",
    "ShareCreateRequest",
    "ShareResponse",
    "ShareLinkResponse",
    "ShareLinkCreateRequest",
    "ShareLinkCreateResponse",
    "ShareRevokeRequest",
    "RedactionPreviewRequest",
    "RedactionApplyRequest",
    "RedactionApplyResponse",
    "RedactionPreviewResponse",
    "PermissionEntry",
    "AuditLogResponse",
    "ShareAccessResponse",
]


class ResourceCreate(BaseModel):
    type: str
    owner_id: str
    org_id: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None
    snapshot_of: Optional[uuid.UUID] = None


class ResourceRead(ResourceCreate):
    id: uuid.UUID
    created_at: dt.datetime
    updated_at: Optional[dt.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ShareCreateRequest(BaseModel):
    resource_id: uuid.UUID
    actor_id: str
    mode: ShareMode = ShareMode.UNLISTED
    allow_download: bool = False
    allow_comments: bool = True
    is_live: bool = False
    expires_at: Optional[dt.datetime] = None
    create_link: bool = False
    link_domain_whitelist: Optional[List[str]] = None
    allow_reshare: bool = False
    permissions: Optional[List["PermissionEntry"]] = None


class PermissionEntry(BaseModel):
    resource_id: uuid.UUID
    principal_type: PrincipalType
    principal_id: str
    role: PermissionRole


class ShareLinkResponse(BaseModel):
    id: uuid.UUID
    domain_whitelist: Optional[List[str]] = None
    created_at: dt.datetime
    revoked_at: Optional[dt.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ShareLinkCreateRequest(BaseModel):
    actor_id: str
    domain_whitelist: Optional[List[str]] = None


class ShareLinkCreateResponse(BaseModel):
    token: str
    url: str
    link: ShareLinkResponse


class ShareRevokeRequest(BaseModel):
    actor_id: str


class ShareResponse(BaseModel):
    id: uuid.UUID
    resource: ResourceRead
    mode: ShareMode
    allow_download: bool
    allow_comments: bool
    is_live: bool
    created_by: str
    created_at: dt.datetime
    expires_at: Optional[dt.datetime] = None
    revoked_at: Optional[dt.datetime] = None
    links: List[ShareLinkResponse]

    model_config = ConfigDict(from_attributes=True)


class RedactionPreviewRequest(BaseModel):
    payloads: Dict[str, str] = Field(default_factory=dict)


class RedactionPreviewResponse(BaseModel):
    redacted: Dict[str, str]
    matches: List[Dict[str, object]]


class RedactionApplyRequest(BaseModel):
    resource: ResourceCreate
    payloads: Dict[str, str] = Field(default_factory=dict)
    actor_id: str


class RedactionApplyResponse(BaseModel):
    resource: ResourceRead
    redaction_id: uuid.UUID
    redacted: Dict[str, str]


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    actor_id: Optional[str]
    action: str
    resource_id: Optional[uuid.UUID]
    context_json: Optional[Dict[str, object]]
    created_at: dt.datetime
    ip: Optional[str]
    ua: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    results: List[AuditLogEntry]


class ShareAccessResponse(BaseModel):
    share: ShareResponse
    link_id: Optional[uuid.UUID] = None
