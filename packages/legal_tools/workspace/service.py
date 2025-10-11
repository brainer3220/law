"""Service layer for workspace management.

비즈니스 로직:
- 권한 검사 (RBAC)
- 프로젝트/멤버 수명주기
- 지침 버전 관리
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, select, and_, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound, IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from .models import (
    Base,
    Organization,
    Project,
    ProjectMember,
    Instruction,
    PermissionRole,
)

from . import schemas

__all__ = ["WorkspaceSettings", "WorkspaceDatabase", "WorkspaceService", "init_engine"]


@dataclass(slots=True)
class WorkspaceSettings:
    """Workspace 서비스 설정."""

    database_url: str
    enable_audit: bool = True
    auto_create_default_org: bool = False

    @classmethod
    def from_env(cls) -> WorkspaceSettings:
        database_url = os.getenv("LAW_SHARE_DB_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "PostgreSQL connection required: set LAW_SHARE_DB_URL or DATABASE_URL"
            )
        return cls(
            database_url=database_url,
            enable_audit=os.getenv("LAW_ENABLE_AUDIT", "true").lower() == "true",
            auto_create_default_org=os.getenv(
                "LAW_WORKSPACE_AUTO_CREATE_DEFAULT_ORG", "false"
            ).lower()
            == "true",
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
        """감사 로그 기록 (migration 007 이후 비활성화)."""
        return

    # ========================================================================
    # 프로젝트
    # ========================================================================

    def create_project(
        self, request: schemas.ProjectCreateRequest, user_id: uuid.UUID
    ) -> Project:
        """프로젝트 생성."""
        # org_id가 없으면 기본 organization 사용
        org_id = request.org_id
        if not org_id and self.settings.auto_create_default_org:
            stmt = select(Organization).where(Organization.name == "Default Organization")
            default_org = self.session.execute(stmt).scalar_one_or_none()
            if not default_org:
                # 기본 organization 생성
                default_org = Organization(
                    name="Default Organization",
                    created_by=user_id,
                )
                self.session.add(default_org)
                self.session.flush()
            org_id = default_org.id
        
        project = Project(
            name=request.name,
            description=request.description,
            status=request.status or "active",
            org_id=org_id,
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
        if request.status is not None:
            project.status = request.status
        if request.archived is not None:
            project.archived = request.archived
        if request.org_id is not None:
            project.org_id = request.org_id

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
            project.archived = True
            project.updated_at = func.now()

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
            status=original.status,
            org_id=original.org_id,
            archived=False,
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
