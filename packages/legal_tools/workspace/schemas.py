"""Pydantic schemas for workspace API requests/responses."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .models import PermissionRole, SensitivityLevel, ShareMode

__all__ = [
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
    "MemoryCreateRequest",
    "MemoryUpdateRequest",
    "MemoryResponse",
    "FileUploadRequest",
    "FileResponse",
    "PresignedUploadRequest",
    "PresignedUploadResponse",
    "PresignedDownloadResponse",
    "DirectFileUploadRequest",
    "ChatCreateRequest",
    "ChatResponse",
    "MessageSendRequest",
    "MessageResponse",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "SnapshotCreateRequest",
    "SnapshotResponse",
    "AuditLogResponse",
    "UsageResponse",
    "BudgetUpdateRequest",
    "BudgetResponse",
]


# ========================================================================
# 프로젝트
# ========================================================================


class ProjectCreateRequest(BaseModel):
    """프로젝트 생성 요청."""

    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    visibility: str = Field(default="private")
    org_id: Optional[uuid.UUID] = None
    budget_quota: Optional[int] = None


class ProjectUpdateRequest(BaseModel):
    """프로젝트 수정 요청."""

    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    visibility: Optional[str] = None
    archived: Optional[bool] = None
    budget_quota: Optional[int] = None


class ProjectCloneRequest(BaseModel):
    """프로젝트 복제 요청."""

    name: str = Field(..., max_length=255)
    include_members: bool = Field(default=False)
    include_files: bool = Field(default=True)
    include_memories: bool = Field(default=True)


class ProjectResponse(BaseModel):
    """프로젝트 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    visibility: str
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


# ========================================================================
# 메모리
# ========================================================================


class MemoryCreateRequest(BaseModel):
    """메모리 생성 요청."""

    k: str = Field(..., max_length=255, alias="key")
    v: dict = Field(..., alias="value")
    source: Optional[str] = None
    expires_at: Optional[dt.datetime] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemoryUpdateRequest(BaseModel):
    """메모리 수정 요청."""

    v: Optional[dict] = Field(None, alias="value")
    source: Optional[str] = None
    expires_at: Optional[dt.datetime] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    """메모리 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    k: str = Field(..., alias="key")
    v: dict = Field(..., alias="value")
    source: Optional[str]
    expires_at: Optional[dt.datetime]
    confidence: Optional[float]
    created_by: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


# ========================================================================
# 파일
# ========================================================================


class FileUploadRequest(BaseModel):
    """파일 업로드 요청."""

    r2_key: str
    name: str
    mime: Optional[str] = None
    size_bytes: Optional[int] = None
    sensitivity: SensitivityLevel = Field(default=SensitivityLevel.INTERNAL)
    checksum: Optional[str] = None


class FileResponse(BaseModel):
    """파일 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    r2_key: str
    name: str
    mime: Optional[str]
    size_bytes: Optional[int]
    version: int
    sensitivity: SensitivityLevel
    checksum: Optional[str]
    created_by: uuid.UUID
    created_at: dt.datetime
    updated_at: dt.datetime


class PresignedUploadRequest(BaseModel):
    """Presigned URL 생성 요청 (클라이언트 직접 업로드용)."""

    name: str = Field(..., description="파일명")
    mime: Optional[str] = Field(None, description="MIME 타입")
    size_bytes: Optional[int] = Field(None, description="파일 크기 (bytes)")
    sensitivity: SensitivityLevel = Field(default=SensitivityLevel.INTERNAL)


class PresignedUploadResponse(BaseModel):
    """Presigned URL 응답."""

    upload_url: str = Field(..., description="파일 업로드용 Presigned URL")
    r2_key: str = Field(..., description="R2 객체 키 (업로드 완료 후 메타 생성 시 사용)")
    expires_in: int = Field(..., description="URL 유효 시간 (초)")


class PresignedDownloadResponse(BaseModel):
    """Presigned 다운로드 URL 응답."""

    download_url: str = Field(..., description="파일 다운로드용 Presigned URL")
    expires_in: int = Field(..., description="URL 유효 시간 (초)")


class DirectFileUploadRequest(BaseModel):
    """직접 파일 업로드 요청 (multipart/form-data)."""

    name: str = Field(..., description="파일명")
    sensitivity: SensitivityLevel = Field(default=SensitivityLevel.INTERNAL)


# ========================================================================
# 채팅
# ========================================================================


class ChatCreateRequest(BaseModel):
    """채팅 생성 요청."""

    title: Optional[str] = None


class ChatResponse(BaseModel):
    """채팅 응답."""

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    created_at: Optional[dt.datetime]
    updated_at: Optional[dt.datetime]

    @classmethod
    def from_orm(cls, obj):
        """ORM 객체로부터 생성."""
        return cls(
            id=obj.chat_id,
            project_id=obj.project_id,
            title=f"Chat {obj.chat_id}",  # ProjectChat에는 title이 없으므로 임시
            created_at=obj.added_at,
            updated_at=obj.added_at,
        )


class MessageSendRequest(BaseModel):
    """메시지 전송 요청."""

    role: str = Field(default="user")
    content: str
    retrieval_scope: str = Field(default="project")


class MessageResponse(BaseModel):
    """메시지 응답."""

    id: uuid.UUID
    chat_id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, Any]]
    created_at: Optional[dt.datetime]


# ========================================================================
# 검색
# ========================================================================


class SearchRequest(BaseModel):
    """검색 요청."""

    project_id: uuid.UUID
    query: str
    k: int = Field(default=10, ge=1, le=50)
    filters: Optional[dict[str, Any]] = None
    scope: str = Field(default="project")


class SearchResult(BaseModel):
    """검색 결과 항목."""

    chunk_id: int
    document_id: uuid.UUID
    file_id: uuid.UUID
    heading: Optional[str]
    body: str
    page: Optional[int]
    score: float


class SearchResponse(BaseModel):
    """검색 응답."""

    results: list[SearchResult]
    total: int


# ========================================================================
# 스냅샷
# ========================================================================


class SnapshotCreateRequest(BaseModel):
    """스냅샷 생성 요청."""

    name: Optional[str] = None


class SnapshotResponse(BaseModel):
    """스냅샷 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: Optional[str]
    instruction_ver: Optional[int]
    created_by: uuid.UUID
    created_at: dt.datetime


# ========================================================================
# 감사 로그
# ========================================================================


class AuditLogResponse(BaseModel):
    """감사 로그 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    at: dt.datetime
    actor_user_id: Optional[uuid.UUID]
    project_id: Optional[uuid.UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip: Optional[str]
    user_agent: Optional[str]
    meta: Optional[dict[str, Any]]


# ========================================================================
# 비용/예산
# ========================================================================


class UsageResponse(BaseModel):
    """사용량 응답."""

    project_id: Optional[uuid.UUID]
    period: str
    tokens_in: int
    tokens_out: int
    cost_cents: int


class BudgetUpdateRequest(BaseModel):
    """예산 수정 요청."""

    token_limit: Optional[int] = None
    hardcap: Optional[bool] = None


class BudgetResponse(BaseModel):
    """예산 응답."""

    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    period: str
    token_limit: Optional[int]
    hardcap: bool
    updated_at: dt.datetime
