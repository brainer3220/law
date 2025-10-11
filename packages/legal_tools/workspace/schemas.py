"""Pydantic schemas for workspace API requests/responses."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import PermissionRole

__all__ = [
    # Core schemas (match migration 007)
    "ProjectCreateRequest",
    "ProjectUpdateRequest",
    "ProjectCloneRequest",
    "ProjectResponse",
    "ProjectListResponse",
    "MemberAddRequest",
    "MemberUpdateRequest",
    "MemberResponse",
    "InstructionCreateRequest",
    "InstructionResponse",
    # Legacy schemas commented out - models removed in migration 007
    # "MemoryCreateRequest",
    # "MemoryUpdateRequest",
    # "MemoryResponse",
    # "FileUploadRequest",
    # "FileResponse",
    # "PresignedUploadRequest",
    # "PresignedUploadResponse",
    # "PresignedDownloadResponse",
    # "DirectFileUploadRequest",
    # "ChatCreateRequest",
    # "ChatResponse",
    # "MessageSendRequest",
    # "MessageResponse",
    # "SearchRequest",
    # "SearchResponse",
    # "SearchResult",
    # "SnapshotCreateRequest",
    # "SnapshotResponse",
    # "AuditLogResponse",
    # "UsageResponse",
    # "BudgetUpdateRequest",
    # "BudgetResponse",
]


# ========================================================================
# 프로젝트
# ========================================================================


class ProjectCreateRequest(BaseModel):
    """프로젝트 생성 요청."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(default="active")
    org_id: Optional[uuid.UUID] = None


class ProjectUpdateRequest(BaseModel):
    """프로젝트 수정 요청."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    archived: Optional[bool] = None
    org_id: Optional[uuid.UUID] = None


class ProjectCloneRequest(BaseModel):
    """프로젝트 복제 요청."""

    name: str = Field(..., max_length=255)


class ProjectResponse(BaseModel):
    """프로젝트 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    status: Optional[str]
    org_id: Optional[uuid.UUID]
    archived: bool
    created_at: dt.datetime
    updated_at: dt.datetime
    created_by: uuid.UUID


class ProjectListResponse(BaseModel):
    """프로젝트 목록 응답."""

    projects: list[ProjectResponse]
    total: int


# ========================================================================
# 멤버십
# ========================================================================


class MemberAddRequest(BaseModel):
    """멤버 추가 요청."""

    user_id: uuid.UUID
    role: PermissionRole


class MemberUpdateRequest(BaseModel):
    """멤버 역할 변경 요청."""

    role: PermissionRole


class MemberResponse(BaseModel):
    """멤버 응답."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    role: PermissionRole
    invited_by: Optional[uuid.UUID]
    created_at: dt.datetime


# ========================================================================
# 지침
# ========================================================================


class InstructionCreateRequest(BaseModel):
    """지침 생성 요청."""

    content: str = Field(..., min_length=1)


class InstructionResponse(BaseModel):
    """지침 응답."""

    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    version: int
    content: str
    created_by: uuid.UUID
    created_at: dt.datetime
