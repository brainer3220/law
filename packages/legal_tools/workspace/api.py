"""FastAPI application for project workspace management.

프로젝트 중심 컨텍스트 관리 API (migration 007 호환):
- 프로젝트 수명주기 (생성/복제/보관/삭제)
- 권한/멤버십 관리
- 지침(Instructions) 버전 관리
"""

from __future__ import annotations

import uuid
from typing import Generator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from . import schemas
from .models import Project, ProjectMember, PermissionRole
from .service import WorkspaceDatabase, WorkspaceService, WorkspaceSettings, init_engine

__all__ = ["create_app", "WorkspaceSettings"]


def create_app(settings: WorkspaceSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application for workspace management."""

    settings = settings or WorkspaceSettings.from_env()
    engine = init_engine(settings)
    database = WorkspaceDatabase(engine=engine)

    app = FastAPI(
        title="Law Workspace API",
        version="1.0.0",
        description="프로젝트 중심 컨텍스트 관리 시스템",
    )

    # CORS 미들웨어 추가 (개발 환경용)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_session() -> Generator[Session, None, None]:
        session = database.session()
        try:
            yield session
        finally:
            session.close()

    def get_service(session: Session = Depends(get_session)) -> WorkspaceService:
        return WorkspaceService(session=session, settings=settings)

    def get_current_user(request: Request) -> uuid.UUID:
        """Extract user_id from auth header (구현 필요)."""
        # TODO: JWT/OAuth 토큰 검증
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        return uuid.UUID(user_id)

    @app.exception_handler(Exception)
    async def _handle_errors(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            raise exc
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    # ========================================================================
    # 프로젝트 수명주기
    # ========================================================================

    @app.post("/v1/projects", response_model=schemas.ProjectResponse, status_code=201)
    def create_project(
        request: schemas.ProjectCreateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.ProjectResponse:
        """프로젝트 생성."""
        try:
            project = service.create_project(request, user_id)
            return schemas.ProjectResponse.from_orm(project)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @app.get("/v1/projects/{project_id}", response_model=schemas.ProjectResponse)
    def get_project(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.ProjectResponse:
        """프로젝트 조회."""
        try:
            project = service.get_project(project_id, user_id)
            return schemas.ProjectResponse.from_orm(project)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get("/v1/projects", response_model=schemas.ProjectListResponse)
    def list_projects(
        org_id: Optional[uuid.UUID] = Query(None),
        archived: bool = Query(False),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.ProjectListResponse:
        """프로젝트 목록 조회."""
        projects = service.list_projects(
            user_id=user_id,
            org_id=org_id,
            archived=archived,
            limit=limit,
            offset=offset,
        )
        return schemas.ProjectListResponse(
            projects=[schemas.ProjectResponse.from_orm(p) for p in projects],
            total=len(projects),
        )

    @app.patch("/v1/projects/{project_id}", response_model=schemas.ProjectResponse)
    def update_project(
        project_id: uuid.UUID,
        request: schemas.ProjectUpdateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.ProjectResponse:
        """프로젝트 수정."""
        try:
            project = service.update_project(project_id, request, user_id)
            return schemas.ProjectResponse.from_orm(project)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.delete("/v1/projects/{project_id}", status_code=204)
    def delete_project(
        project_id: uuid.UUID,
        hard_delete: bool = Query(False, description="영구 삭제 여부"),
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> None:
        """프로젝트 삭제 (soft delete 또는 hard delete)."""
        try:
            service.delete_project(project_id, user_id, hard_delete=hard_delete)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.post("/v1/projects/{project_id}/clone", response_model=schemas.ProjectResponse)
    def clone_project(
        project_id: uuid.UUID,
        request: schemas.ProjectCloneRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.ProjectResponse:
        """프로젝트 복제."""
        try:
            project = service.clone_project(project_id, request, user_id)
            return schemas.ProjectResponse.from_orm(project)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 멤버십/권한
    # ========================================================================

    @app.post("/v1/projects/{project_id}/members", response_model=schemas.MemberResponse)
    def add_member(
        project_id: uuid.UUID,
        request: schemas.MemberAddRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.MemberResponse:
        """멤버 추가."""
        try:
            member = service.add_member(project_id, request, user_id)
            return schemas.MemberResponse.from_orm(member)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @app.get("/v1/projects/{project_id}/members", response_model=list[schemas.MemberResponse])
    def list_members(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.MemberResponse]:
        """멤버 목록."""
        try:
            members = service.list_members(project_id, user_id)
            return [schemas.MemberResponse.from_orm(m) for m in members]
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.patch(
        "/v1/projects/{project_id}/members/{member_user_id}",
        response_model=schemas.MemberResponse,
    )
    def update_member_role(
        project_id: uuid.UUID,
        member_user_id: uuid.UUID,
        request: schemas.MemberUpdateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.MemberResponse:
        """멤버 역할 변경."""
        try:
            member = service.update_member_role(project_id, member_user_id, request, user_id)
            return schemas.MemberResponse.from_orm(member)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Member not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.delete("/v1/projects/{project_id}/members/{member_user_id}", status_code=204)
    def remove_member(
        project_id: uuid.UUID,
        member_user_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> None:
        """멤버 제거."""
        try:
            service.remove_member(project_id, member_user_id, user_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Member not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 지침(Instructions)
    # ========================================================================

    @app.post(
        "/v1/projects/{project_id}/instructions",
        response_model=schemas.InstructionResponse,
        status_code=201,
    )
    def create_instruction(
        project_id: uuid.UUID,
        request: schemas.InstructionCreateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.InstructionResponse:
        """새 지침 버전 생성."""
        try:
            instruction = service.create_instruction(project_id, request, user_id)
            return schemas.InstructionResponse.from_orm(instruction)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get(
        "/v1/projects/{project_id}/instructions",
        response_model=list[schemas.InstructionResponse],
    )
    def list_instructions(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.InstructionResponse]:
        """지침 버전 목록."""
        try:
            instructions = service.list_instructions(project_id, user_id)
            return [schemas.InstructionResponse.from_orm(i) for i in instructions]
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get(
        "/v1/projects/{project_id}/instructions/{version}",
        response_model=schemas.InstructionResponse,
    )
    def get_instruction(
        project_id: uuid.UUID,
        version: int,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.InstructionResponse:
        """특정 버전 지침 조회."""
        try:
            instruction = service.get_instruction(project_id, version, user_id)
            return schemas.InstructionResponse.from_orm(instruction)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Instruction not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 프로젝트 업데이트
    # ========================================================================

    @app.post("/v1/projects/{project_id}/updates", response_model=schemas.UpdateResponse, status_code=201)
    def create_update(
        project_id: uuid.UUID,
        request: schemas.UpdateCreateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.UpdateResponse:
        """프로젝트 업데이트 생성."""
        try:
            update = service.create_update(project_id, request, user_id)
            return schemas.UpdateResponse.from_orm(update)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @app.get("/v1/projects/{project_id}/updates", response_model=list[schemas.UpdateResponse])
    def list_updates(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.UpdateResponse]:
        """프로젝트 업데이트 목록 조회."""
        try:
            updates = service.list_updates(project_id, user_id)
            return [schemas.UpdateResponse.from_orm(u) for u in updates]
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get("/v1/projects/{project_id}/updates/{update_id}", response_model=schemas.UpdateResponse)
    def get_update(
        project_id: uuid.UUID,
        update_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.UpdateResponse:
        """프로젝트 업데이트 단건 조회."""
        try:
            update = service.get_update(project_id, update_id, user_id)
            return schemas.UpdateResponse.from_orm(update)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Update not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None


    # ========================================================================
    # LEGACY ENDPOINTS REMOVED - Models removed in migration 007
    # Memory, File, Chat, Snapshot, AuditLog, Budget, Usage endpoints
    # ========================================================================

    return app
