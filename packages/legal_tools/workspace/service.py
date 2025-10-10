"""Service layer for workspace management.

비즈니스 로직:
- 권한 검사 (ABAC/RBAC)
- 컨텍스트 주입 (지침 + 메모리 + 파일)
- 감사 로깅
- 예산 체크
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, select, and_, or_, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Base,
    Organization,
    Project,
    ProjectMember,
    ProjectChat,
    Instruction,
    Memory,
    File,
    Snapshot,
    AuditLog,
    ProjectBudget,
    UsageLedger,
    PermissionRole,
)
from . import schemas
from .storage import R2Client, R2Config

__all__ = ["WorkspaceSettings", "WorkspaceDatabase", "WorkspaceService", "init_engine"]


@dataclass(slots=True)
class WorkspaceSettings:
    """Workspace 서비스 설정."""

    database_url: str
    enable_audit: bool = True
    enable_budget_check: bool = True
    r2_config: Optional[R2Config] = None

    @classmethod
    def from_env(cls) -> WorkspaceSettings:
        database_url = os.getenv("LAW_SHARE_DB_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "PostgreSQL connection required: set LAW_SHARE_DB_URL or DATABASE_URL"
            )
        
        # R2 설정 (선택)
        r2_config = None
        try:
            r2_config = R2Config.from_env()
        except ValueError:
            # R2 설정이 없으면 None (파일 업로드 비활성화)
            pass
        
        return cls(
            database_url=database_url,
            enable_audit=os.getenv("LAW_ENABLE_AUDIT", "true").lower() == "true",
            enable_budget_check=os.getenv("LAW_ENABLE_BUDGET_CHECK", "true").lower()
            == "true",
            r2_config=r2_config,
        )


def init_engine(settings: WorkspaceSettings) -> Engine:
    """SQLAlchemy 엔진 초기화."""
    # SQLAlchemy 1.4+ requires 'postgresql://' not 'postgres://'
    # Use psycopg3 driver explicitly since psycopg2 is not installed
    database_url = settings.database_url
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    engine = create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    return engine


class WorkspaceDatabase:
    """데이터베이스 세션 관리."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self._session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def session(self) -> Session:
        return self._session_factory()

    def create_all(self):
        """테이블 생성 (개발용)."""
        Base.metadata.create_all(self.engine)


class WorkspaceService:
    """Workspace 비즈니스 로직."""

    def __init__(self, session: Session, settings: WorkspaceSettings):
        self.session = session
        self.settings = settings
        self.r2_client = R2Client(settings.r2_config) if settings.r2_config else None

    # ========================================================================
    # 권한 체크
    # ========================================================================

    def _check_permission(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        required_role: PermissionRole,
    ) -> ProjectMember:
        """프로젝트 권한 확인."""
        member = (
            self.session.execute(
                select(ProjectMember).where(
                    and_(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == user_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        if not member:
            raise PermissionError("Not a project member")

        # 역할 계층: OWNER > MAINTAINER > EDITOR > COMMENTER > VIEWER
        role_order = {
            PermissionRole.OWNER: 5,
            PermissionRole.MAINTAINER: 4,
            PermissionRole.EDITOR: 3,
            PermissionRole.COMMENTER: 2,
            PermissionRole.VIEWER: 1,
        }

        if role_order.get(member.role, 0) < role_order.get(required_role, 99):
            raise PermissionError(f"Requires {required_role.value} role or higher")

        return member

    def _log_audit(
        self,
        project_id: uuid.UUID,
        actor_id: uuid.UUID,
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        meta: Optional[dict] = None,
    ):
        """감사 로그 기록."""
        if not self.settings.enable_audit:
            return

        log = AuditLog(
            project_id=project_id,
            actor_user_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            meta=meta or {},
        )
        self.session.add(log)

    # ========================================================================
    # 프로젝트
    # ========================================================================

    def create_project(
        self, request: schemas.ProjectCreateRequest, user_id: uuid.UUID
    ) -> Project:
        """프로젝트 생성."""
        # org_id가 없으면 기본 organization 사용
        org_id = request.org_id
        if not org_id:
            stmt = select(Organization).where(Organization.name == "Default Organization")
            default_org = self.session.execute(stmt).scalar_one_or_none()
            if not default_org:
                # 기본 organization 생성
                default_org = Organization(name="Default Organization")
                self.session.add(default_org)
                self.session.flush()
            org_id = default_org.id
        
        project = Project(
            name=request.name,
            description=request.description,
            visibility=request.visibility,
            org_id=org_id,
            budget_quota=request.budget_quota,
            created_by=user_id,
        )
        self.session.add(project)
        self.session.flush()

        # OWNER로 멤버 추가
        member = ProjectMember(
            project_id=project.id,
            user_id=user_id,
            role=PermissionRole.OWNER,
        )
        self.session.add(member)
        self.session.commit()

        self._log_audit(project.id, user_id, "project.created", "project", str(project.id))
        return project

    def get_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
        """프로젝트 조회."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        project = self.session.get(Project, project_id)
        if not project:
            raise NoResultFound()
        return project

    def list_projects(
        self,
        user_id: uuid.UUID,
        org_id: Optional[uuid.UUID] = None,
        archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """프로젝트 목록."""
        stmt = (
            select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == user_id)
        )
        if org_id:
            stmt = stmt.where(Project.org_id == org_id)
        if not archived:
            stmt = stmt.where(Project.archived == False)  # noqa: E712

        stmt = stmt.limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars())

    def update_project(
        self,
        project_id: uuid.UUID,
        request: schemas.ProjectUpdateRequest,
        user_id: uuid.UUID,
    ) -> Project:
        """프로젝트 수정."""
        self._check_permission(project_id, user_id, PermissionRole.MAINTAINER)
        project = self.session.get(Project, project_id)
        if not project:
            raise NoResultFound()

        if request.name is not None:
            project.name = request.name
        if request.description is not None:
            project.description = request.description
        if request.visibility is not None:
            project.visibility = request.visibility
        if request.archived is not None:
            project.archived = request.archived
        if request.budget_quota is not None:
            project.budget_quota = request.budget_quota

        project.updated_at = func.now()
        self.session.commit()
        self._log_audit(project_id, user_id, "project.updated", "project", str(project_id))
        return project

    def delete_project(
        self, project_id: uuid.UUID, user_id: uuid.UUID, hard_delete: bool = False
    ):
        """프로젝트 삭제."""
        self._check_permission(project_id, user_id, PermissionRole.OWNER)
        project = self.session.get(Project, project_id)
        if not project:
            raise NoResultFound()

        if hard_delete:
            self.session.delete(project)
        else:
            project.deleted_at = dt.datetime.now(dt.timezone.utc)

        self.session.commit()
        action = "project.hard_deleted" if hard_delete else "project.soft_deleted"
        self._log_audit(project_id, user_id, action, "project", str(project_id))

    def clone_project(
        self,
        project_id: uuid.UUID,
        request: schemas.ProjectCloneRequest,
        user_id: uuid.UUID,
    ) -> Project:
        """프로젝트 복제."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        original = self.session.get(Project, project_id)
        if not original:
            raise NoResultFound()

        clone = Project(
            name=request.name,
            description=original.description,
            visibility=original.visibility,
            org_id=original.org_id,
            template_id=project_id,
            created_by=user_id,
        )
        self.session.add(clone)
        self.session.flush()

        # OWNER 멤버 추가
        clone_member = ProjectMember(
            project_id=clone.id,
            user_id=user_id,
            role=PermissionRole.OWNER,
        )
        self.session.add(clone_member)

        # 메모리 복제
        if request.include_memories:
            for memory in original.memories:
                clone_memory = Memory(
                    project_id=clone.id,
                    k=memory.k,
                    v=memory.v,
                    source=memory.source,
                    confidence=memory.confidence,
                    created_by=user_id,
                )
                self.session.add(clone_memory)

        self.session.commit()
        self._log_audit(clone.id, user_id, "project.cloned", "project", str(clone.id))
        return clone

    # ========================================================================
    # 멤버십
    # ========================================================================

    def add_member(
        self,
        project_id: uuid.UUID,
        request: schemas.MemberAddRequest,
        user_id: uuid.UUID,
    ) -> ProjectMember:
        """멤버 추가."""
        self._check_permission(project_id, user_id, PermissionRole.MAINTAINER)

        member = ProjectMember(
            project_id=project_id,
            user_id=request.user_id,
            role=request.role,
            invited_by=user_id,
        )
        self.session.add(member)
        try:
            self.session.commit()
        except IntegrityError:
            raise ValueError("User already a member")

        self._log_audit(
            project_id,
            user_id,
            "member.added",
            "member",
            str(request.user_id),
            {"role": request.role.value},
        )
        return member

    def list_members(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ProjectMember]:
        """멤버 목록."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        return list(
            self.session.execute(
                select(ProjectMember).where(ProjectMember.project_id == project_id)
            ).scalars()
        )

    def update_member_role(
        self,
        project_id: uuid.UUID,
        member_user_id: uuid.UUID,
        request: schemas.MemberUpdateRequest,
        user_id: uuid.UUID,
    ) -> ProjectMember:
        """멤버 역할 변경."""
        self._check_permission(project_id, user_id, PermissionRole.MAINTAINER)

        member = (
            self.session.execute(
                select(ProjectMember).where(
                    and_(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == member_user_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        if not member:
            raise NoResultFound()

        member.role = request.role
        self.session.commit()
        self._log_audit(
            project_id,
            user_id,
            "member.role_updated",
            "member",
            str(member_user_id),
            {"new_role": request.role.value},
        )
        return member

    def remove_member(
        self, project_id: uuid.UUID, member_user_id: uuid.UUID, user_id: uuid.UUID
    ):
        """멤버 제거."""
        self._check_permission(project_id, user_id, PermissionRole.MAINTAINER)

        member = (
            self.session.execute(
                select(ProjectMember).where(
                    and_(
                        ProjectMember.project_id == project_id,
                        ProjectMember.user_id == member_user_id,
                    )
                )
            )
            .scalars()
            .first()
        )
        if not member:
            raise NoResultFound()

        self.session.delete(member)
        self.session.commit()
        self._log_audit(
            project_id, user_id, "member.removed", "member", str(member_user_id)
        )

    # ========================================================================
    # 지침
    # ========================================================================

    def create_instruction(
        self,
        project_id: uuid.UUID,
        request: schemas.InstructionCreateRequest,
        user_id: uuid.UUID,
    ) -> Instruction:
        """새 지침 버전 생성."""
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)

        # 최신 버전 조회
        latest = (
            self.session.execute(
                select(Instruction)
                .where(Instruction.project_id == project_id)
                .order_by(Instruction.version.desc())
            )
            .scalars()
            .first()
        )
        next_version = (latest.version + 1) if latest else 1

        instruction = Instruction(
            project_id=project_id,
            version=next_version,
            content=request.content,
            created_by=user_id,
        )
        self.session.add(instruction)
        self.session.commit()
        self._log_audit(
            project_id,
            user_id,
            "instruction.created",
            "instruction",
            f"{project_id}:{next_version}",
        )
        return instruction

    def list_instructions(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Instruction]:
        """지침 목록."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        return list(
            self.session.execute(
                select(Instruction)
                .where(Instruction.project_id == project_id)
                .order_by(Instruction.version.desc())
            ).scalars()
        )

    def get_instruction(
        self, project_id: uuid.UUID, version: int, user_id: uuid.UUID
    ) -> Instruction:
        """특정 버전 지침 조회."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        instruction = (
            self.session.execute(
                select(Instruction).where(
                    and_(
                        Instruction.project_id == project_id,
                        Instruction.version == version,
                    )
                )
            )
            .scalars()
            .first()
        )
        if not instruction:
            raise NoResultFound()
        return instruction

    # ========================================================================
    # 메모리
    # ========================================================================

    def create_memory(
        self,
        project_id: uuid.UUID,
        request: schemas.MemoryCreateRequest,
        user_id: uuid.UUID,
    ) -> Memory:
        """메모리 항목 생성."""
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)

        memory = Memory(
            project_id=project_id,
            k=request.k,
            v=request.v,
            source=request.source,
            confidence=request.confidence,
            expires_at=request.expires_at,
            created_by=user_id,
        )
        self.session.add(memory)
        try:
            self.session.commit()
        except IntegrityError:
            raise ValueError("Memory key already exists")

        self._log_audit(
            project_id, user_id, "memory.created", "memory", str(memory.id)
        )
        return memory

    def list_memories(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Memory]:
        """메모리 목록."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        return list(
            self.session.execute(
                select(Memory).where(Memory.project_id == project_id)
            ).scalars()
        )

    def get_memory(
        self, project_id: uuid.UUID, memory_id: uuid.UUID, user_id: uuid.UUID
    ) -> Memory:
        """메모리 조회."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        memory = self.session.get(Memory, memory_id)
        if not memory or memory.project_id != project_id:
            raise NoResultFound()
        return memory

    def update_memory(
        self,
        project_id: uuid.UUID,
        memory_id: uuid.UUID,
        request: schemas.MemoryUpdateRequest,
        user_id: uuid.UUID,
    ) -> Memory:
        """메모리 수정."""
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)
        memory = self.session.get(Memory, memory_id)
        if not memory or memory.project_id != project_id:
            raise NoResultFound()

        if request.v is not None:
            memory.v = request.v
        if request.source is not None:
            memory.source = request.source
        if request.expires_at is not None:
            memory.expires_at = request.expires_at
        if request.confidence is not None:
            memory.confidence = request.confidence

        self.session.commit()
        self._log_audit(project_id, user_id, "memory.updated", "memory", str(memory_id))
        return memory

    def delete_memory(
        self, project_id: uuid.UUID, memory_id: uuid.UUID, user_id: uuid.UUID
    ):
        """메모리 삭제."""
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)
        memory = self.session.get(Memory, memory_id)
        if not memory or memory.project_id != project_id:
            raise NoResultFound()

        self.session.delete(memory)
        self.session.commit()
        self._log_audit(project_id, user_id, "memory.deleted", "memory", str(memory_id))

    # ========================================================================
    # 파일 (스텁)
    # ========================================================================

    def create_file(
        self,
        project_id: uuid.UUID,
        request: schemas.FileUploadRequest,
        user_id: uuid.UUID,
        file_content: Optional[bytes] = None,
    ) -> File:
        """파일 메타 생성 및 R2 업로드.
        
        Args:
            project_id: 프로젝트 ID
            request: 파일 업로드 요청
            user_id: 사용자 ID
            file_content: 파일 내용 (바이너리, 직접 업로드 시)
        
        Returns:
            생성된 File 객체
        """
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)

        # R2 업로드 (file_content가 제공된 경우)
        if file_content and self.r2_client:
            upload_result = self.r2_client.upload_file(
                file_content=file_content,
                key=request.r2_key,
                content_type=request.mime,
                metadata={
                    "project_id": str(project_id),
                    "uploaded_by": str(user_id),
                },
            )
            # R2 업로드 결과로 체크섬 업데이트
            if not request.checksum:
                request.checksum = upload_result["checksum"]
            if not request.size_bytes:
                request.size_bytes = upload_result["size"]

        file = File(
            project_id=project_id,
            r2_key=request.r2_key,
            name=request.name,
            mime=request.mime,
            size_bytes=request.size_bytes,
            sensitivity=request.sensitivity,
            checksum=request.checksum,
            created_by=user_id,
        )
        self.session.add(file)
        self.session.commit()
        self._log_audit(project_id, user_id, "file.uploaded", "file", str(file.id))
        return file

    def list_files(self, project_id: uuid.UUID, user_id: uuid.UUID) -> list[File]:
        """파일 목록."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        return list(
            self.session.execute(
                select(File).where(File.project_id == project_id)
            ).scalars()
        )

    def get_file(self, file_id: uuid.UUID, user_id: uuid.UUID) -> File:
        """파일 조회."""
        file = self.session.get(File, file_id)
        if not file:
            raise NoResultFound()
        self._check_permission(file.project_id, user_id, PermissionRole.VIEWER)
        return file

    def reindex_file(self, file_id: uuid.UUID, user_id: uuid.UUID):
        """파일 재인덱싱 (큐 전송 등)."""
        file = self.get_file(file_id, user_id)
        self._check_permission(file.project_id, user_id, PermissionRole.EDITOR)
        # TODO: 실제 인덱싱 큐 전송
        self._log_audit(file.project_id, user_id, "file.reindex", "file", str(file_id))

    def delete_file(self, file_id: uuid.UUID, user_id: uuid.UUID):
        """파일 삭제 (DB 및 R2)."""
        file = self.get_file(file_id, user_id)
        self._check_permission(file.project_id, user_id, PermissionRole.EDITOR)
        
        # R2에서 파일 삭제
        if self.r2_client:
            try:
                self.r2_client.delete_file(file.r2_key)
            except Exception as e:
                # R2 삭제 실패해도 DB 레코드는 삭제 (로그만 남김)
                import logging
                logging.error(f"Failed to delete file from R2: {file.r2_key}", exc_info=e)
        
        self.session.delete(file)
        self.session.commit()
        self._log_audit(file.project_id, user_id, "file.deleted", "file", str(file_id))

    def generate_upload_url(
        self,
        project_id: uuid.UUID,
        key: str,
        content_type: Optional[str],
        user_id: uuid.UUID,
    ) -> str:
        """파일 업로드용 Presigned URL 생성.
        
        클라이언트가 직접 R2에 업로드할 수 있는 임시 URL을 생성합니다.
        
        Args:
            project_id: 프로젝트 ID
            key: R2 객체 키
            content_type: MIME 타입
            user_id: 사용자 ID
        
        Returns:
            Presigned upload URL
        
        Raises:
            ValueError: R2가 설정되지 않은 경우
        """
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)
        
        if not self.r2_client:
            raise ValueError("R2 storage is not configured")
        
        return self.r2_client.generate_presigned_upload_url(
            key=key,
            content_type=content_type,
        )

    def generate_download_url(
        self,
        file_id: uuid.UUID,
        user_id: uuid.UUID,
        expiry: Optional[int] = None,
    ) -> str:
        """파일 다운로드용 Presigned URL 생성.
        
        Args:
            file_id: 파일 ID
            user_id: 사용자 ID
            expiry: URL 유효 시간 (초)
        
        Returns:
            Presigned download URL
        
        Raises:
            ValueError: R2가 설정되지 않은 경우
        """
        file = self.get_file(file_id, user_id)
        
        if not self.r2_client:
            raise ValueError("R2 storage is not configured")
        
        return self.r2_client.generate_presigned_download_url(
            key=file.r2_key,
            expiry=expiry,
            filename=file.name,
        )

    # ========================================================================
    # 검색 (스텁)
    # ========================================================================

    def search(
        self, request: schemas.SearchRequest, user_id: uuid.UUID
    ) -> list[schemas.SearchResult]:
        """하이브리드 검색."""
        self._check_permission(request.project_id, user_id, PermissionRole.VIEWER)
        # TODO: 실제 BM25 + 벡터 검색
        return []

    # ========================================================================
    # 채팅
    # ========================================================================

    def list_chats(self, project_id: uuid.UUID, user_id: uuid.UUID) -> list[ProjectChat]:
        """프로젝트의 채팅 목록."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        return list(
            self.session.execute(
                select(ProjectChat).where(ProjectChat.project_id == project_id)
            ).scalars()
        )

    def create_chat(
        self,
        project_id: uuid.UUID,
        request: schemas.ChatCreateRequest,
        user_id: uuid.UUID,
    ) -> ProjectChat:
        """채팅 생성."""
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)

        chat = ProjectChat(
            project_id=project_id,
            title=request.title or "New Chat",
            created_by=user_id,
            added_by=user_id,
        )
        self.session.add(chat)
        self.session.flush()  # Flush to get DB-generated timestamps
        self.session.commit()
        self._log_audit(
            project_id, user_id, "chat.created", "chat", str(chat.id)
        )
        return chat

    # ========================================================================
    # 스냅샷
    # ========================================================================

    def create_snapshot(
        self,
        project_id: uuid.UUID,
        request: schemas.SnapshotCreateRequest,
        user_id: uuid.UUID,
    ) -> Snapshot:
        """스냅샷 생성."""
        self._check_permission(project_id, user_id, PermissionRole.EDITOR)

        # 현재 지침 버전
        latest_instr = (
            self.session.execute(
                select(Instruction)
                .where(Instruction.project_id == project_id)
                .order_by(Instruction.version.desc())
            )
            .scalars()
            .first()
        )

        snapshot = Snapshot(
            project_id=project_id,
            name=request.name,
            instruction_ver=latest_instr.version if latest_instr else None,
            created_by=user_id,
        )
        self.session.add(snapshot)
        self.session.commit()
        self._log_audit(
            project_id, user_id, "snapshot.created", "snapshot", str(snapshot.id)
        )
        return snapshot

    def list_snapshots(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Snapshot]:
        """스냅샷 목록."""
        self._check_permission(project_id, user_id, PermissionRole.VIEWER)
        return list(
            self.session.execute(
                select(Snapshot).where(Snapshot.project_id == project_id)
            ).scalars()
        )

    # ========================================================================
    # 감사/비용 (스텁)
    # ========================================================================

    def list_audit_logs(
        self,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """감사 로그 조회."""
        if project_id:
            self._check_permission(project_id, user_id, PermissionRole.MAINTAINER)

        stmt = select(AuditLog)
        if project_id:
            stmt = stmt.where(AuditLog.project_id == project_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)

        stmt = stmt.order_by(AuditLog.at.desc()).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars())

    def get_usage(
        self,
        user_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
        period: str = "current_month",
    ) -> schemas.UsageResponse:
        """사용량 조회."""
        if project_id:
            self._check_permission(project_id, user_id, PermissionRole.VIEWER)

        # TODO: 실제 집계 로직
        return schemas.UsageResponse(
            project_id=project_id,
            period=period,
            tokens_in=0,
            tokens_out=0,
            cost_cents=0,
        )

    def update_budget(
        self,
        project_id: uuid.UUID,
        request: schemas.BudgetUpdateRequest,
        user_id: uuid.UUID,
    ) -> ProjectBudget:
        """예산 설정."""
        self._check_permission(project_id, user_id, PermissionRole.MAINTAINER)

        budget = self.session.get(ProjectBudget, project_id)
        if not budget:
            budget = ProjectBudget(project_id=project_id)
            self.session.add(budget)

        if request.token_limit is not None:
            budget.token_limit = request.token_limit
        if request.hardcap is not None:
            budget.hardcap = request.hardcap

        self.session.commit()
        self._log_audit(project_id, user_id, "budget.updated", "budget", str(project_id))
        return budget
