"""FastAPI application for project workspace management.

프로젝트 중심 컨텍스트 관리 API:
- 프로젝트 수명주기 (생성/복제/보관/삭제)
- 지침(Instructions) 버전 관리
- 메모리(Memory) CRUD
- 파일 업로드/인덱싱
- 채팅/메시지
- 권한/멤버십
- 스냅샷/재현성
- 감사/비용 추적
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
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

    def get_session() -> Session:
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
    # 메모리(Memory)
    # ========================================================================

    @app.post(
        "/v1/projects/{project_id}/memories",
        response_model=schemas.MemoryResponse,
        status_code=201,
    )
    def create_memory(
        project_id: uuid.UUID,
        request: schemas.MemoryCreateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.MemoryResponse:
        """메모리 항목 생성."""
        try:
            memory = service.create_memory(project_id, request, user_id)
            return schemas.MemoryResponse.from_orm(memory)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None

    @app.get(
        "/v1/projects/{project_id}/memories", response_model=list[schemas.MemoryResponse]
    )
    def list_memories(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.MemoryResponse]:
        """메모리 목록."""
        try:
            memories = service.list_memories(project_id, user_id)
            return [schemas.MemoryResponse.from_orm(m) for m in memories]
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get(
        "/v1/projects/{project_id}/memories/{memory_id}",
        response_model=schemas.MemoryResponse,
    )
    def get_memory(
        project_id: uuid.UUID,
        memory_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.MemoryResponse:
        """메모리 항목 조회."""
        try:
            memory = service.get_memory(project_id, memory_id, user_id)
            return schemas.MemoryResponse.from_orm(memory)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Memory not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.patch(
        "/v1/projects/{project_id}/memories/{memory_id}",
        response_model=schemas.MemoryResponse,
    )
    def update_memory(
        project_id: uuid.UUID,
        memory_id: uuid.UUID,
        request: schemas.MemoryUpdateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.MemoryResponse:
        """메모리 항목 수정."""
        try:
            memory = service.update_memory(project_id, memory_id, request, user_id)
            return schemas.MemoryResponse.from_orm(memory)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Memory not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.delete("/v1/projects/{project_id}/memories/{memory_id}", status_code=204)
    def delete_memory(
        project_id: uuid.UUID,
        memory_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> None:
        """메모리 항목 삭제."""
        try:
            service.delete_memory(project_id, memory_id, user_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Memory not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 파일
    # ========================================================================

    @app.post(
        "/v1/projects/{project_id}/files", response_model=schemas.FileResponse, status_code=201
    )
    def upload_file(
        project_id: uuid.UUID,
        request: schemas.FileUploadRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.FileResponse:
        """파일 업로드 (메타만, 실제 파일은 별도 스토리지)."""
        try:
            file = service.create_file(project_id, request, user_id)
            return schemas.FileResponse.from_orm(file)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get("/v1/projects/{project_id}/files", response_model=list[schemas.FileResponse])
    def list_files(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.FileResponse]:
        """파일 목록."""
        try:
            files = service.list_files(project_id, user_id)
            return [schemas.FileResponse.from_orm(f) for f in files]
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get("/v1/files/{file_id}", response_model=schemas.FileResponse)
    def get_file(
        file_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.FileResponse:
        """파일 조회."""
        try:
            file = service.get_file(file_id, user_id)
            return schemas.FileResponse.from_orm(file)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="File not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.post("/v1/files/{file_id}/reindex", status_code=202)
    def reindex_file(
        file_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> dict:
        """파일 재인덱싱 요청."""
        try:
            service.reindex_file(file_id, user_id)
            return {"message": "Reindex queued", "file_id": str(file_id)}
        except NoResultFound:
            raise HTTPException(status_code=404, detail="File not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.delete("/v1/files/{file_id}", status_code=204)
    def delete_file(
        file_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> None:
        """파일 삭제."""
        try:
            service.delete_file(file_id, user_id)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="File not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 채팅
    # ========================================================================

    @app.post(
        "/v1/projects/{project_id}/chats", response_model=schemas.ChatResponse, status_code=201
    )
    def create_chat(
        project_id: uuid.UUID,
        request: schemas.ChatCreateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.ChatResponse:
        """채팅 생성."""
        try:
            # TODO: 실제 Chat 모델 연동
            return schemas.ChatResponse(
                id=uuid.uuid4(),
                project_id=project_id,
                title=request.title or "New Chat",
                created_at=None,
                updated_at=None,
            )
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.post("/v1/chats/{chat_id}/messages", response_model=schemas.MessageResponse)
    def send_message(
        chat_id: uuid.UUID,
        request: schemas.MessageSendRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.MessageResponse:
        """메시지 전송 + 컨텍스트 주입."""
        try:
            # TODO: 실제 메시지 처리 + RAG
            return schemas.MessageResponse(
                id=uuid.uuid4(),
                chat_id=chat_id,
                role="assistant",
                content="Response pending implementation",
                citations=[],
                created_at=None,
            )
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Chat not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 검색
    # ========================================================================

    @app.post("/v1/search", response_model=schemas.SearchResponse)
    def search(
        request: schemas.SearchRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.SearchResponse:
        """프로젝트 내 하이브리드 검색."""
        try:
            results = service.search(request, user_id)
            return schemas.SearchResponse(results=results, total=len(results))
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 스냅샷
    # ========================================================================

    @app.post(
        "/v1/projects/{project_id}/snapshots",
        response_model=schemas.SnapshotResponse,
        status_code=201,
    )
    def create_snapshot(
        project_id: uuid.UUID,
        request: schemas.SnapshotCreateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.SnapshotResponse:
        """스냅샷 생성."""
        try:
            snapshot = service.create_snapshot(project_id, request, user_id)
            return schemas.SnapshotResponse.from_orm(snapshot)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.get(
        "/v1/projects/{project_id}/snapshots", response_model=list[schemas.SnapshotResponse]
    )
    def list_snapshots(
        project_id: uuid.UUID,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.SnapshotResponse]:
        """스냅샷 목록."""
        try:
            snapshots = service.list_snapshots(project_id, user_id)
            return [schemas.SnapshotResponse.from_orm(s) for s in snapshots]
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 감사 로그
    # ========================================================================

    @app.get("/v1/audit", response_model=list[schemas.AuditLogResponse])
    def list_audit_logs(
        project_id: Optional[uuid.UUID] = Query(None),
        action: Optional[str] = Query(None),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> list[schemas.AuditLogResponse]:
        """감사 로그 조회."""
        try:
            logs = service.list_audit_logs(
                user_id=user_id,
                project_id=project_id,
                action=action,
                limit=limit,
                offset=offset,
            )
            return [schemas.AuditLogResponse.from_orm(log) for log in logs]
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    # ========================================================================
    # 비용/예산
    # ========================================================================

    @app.get("/v1/billing/usage", response_model=schemas.UsageResponse)
    def get_usage(
        project_id: Optional[uuid.UUID] = Query(None),
        period: Optional[str] = Query("current_month"),
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.UsageResponse:
        """사용량/비용 조회."""
        try:
            usage = service.get_usage(user_id=user_id, project_id=project_id, period=period)
            return usage
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    @app.patch(
        "/v1/projects/{project_id}/budget", response_model=schemas.BudgetResponse
    )
    def update_budget(
        project_id: uuid.UUID,
        request: schemas.BudgetUpdateRequest,
        service: WorkspaceService = Depends(get_service),
        user_id: uuid.UUID = Depends(get_current_user),
    ) -> schemas.BudgetResponse:
        """예산 설정."""
        try:
            budget = service.update_budget(project_id, request, user_id)
            return schemas.BudgetResponse.from_orm(budget)
        except NoResultFound:
            raise HTTPException(status_code=404, detail="Project not found") from None
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from None

    return app
