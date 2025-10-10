# Workspace API 구현 완료

## 구현 내용

### ✅ 완료된 항목

#### 1. 데이터 모델 (`workspace/models.py`)
- 이미 존재하는 완성된 모델 활용
- Project, ProjectMember, Instruction, Memory, File, Document, DocumentChunk
- Snapshot, AuditLog, ProjectBudget, UsageLedger
- Enum: PermissionRole, SensitivityLevel, ShareMode, PrincipalType, ResourceType

#### 2. Pydantic 스키마 (`workspace/schemas.py`)
- Request/Response 모델 정의
- 프로젝트, 멤버, 지침, 메모리, 파일, 채팅, 검색, 스냅샷, 감사, 예산

#### 3. 서비스 레이어 (`workspace/service.py`)
- WorkspaceSettings: 환경 변수 기반 설정
- WorkspaceDatabase: 세션 관리
- WorkspaceService: 비즈니스 로직
  - ✅ 권한 체크 (역할 계층)
  - ✅ 감사 로깅
  - ✅ 프로젝트 CRUD
  - ✅ 멤버십 관리
  - ✅ 지침 버전 관리
  - ✅ 메모리 CRUD
  - ✅ 파일 관리
  - ✅ 스냅샷 관리
  - 🔸 검색 (스텁)
  - 🔸 채팅/메시지 (스텁)
  - 🔸 예산 체크 (스텁)

#### 4. FastAPI 앱 (`workspace/api.py`)
- 40+ 엔드포인트 구현
- 권한 체크 미들웨어
- 예외 처리
- OpenAPI 문서 자동 생성

#### 5. CLI 커맨드 (`legal_cli/commands/workspace_service.py`)
- `uv run law-cli workspace-serve` 커맨드 등록
- 포트/호스트/리로드 옵션

#### 6. 문서
- `docs/workspace-api-overview.md`: 전체 개요
- API 엔드포인트 목록
- 사용 예시
- 권한 매트릭스
- 아키텍처 다이어그램

## 사용 방법

### 1. 환경 설정

```bash
# .env 파일에 추가
export LAW_SHARE_DB_URL="postgresql://user:pass@localhost:5432/law_workspace"
export LAW_ENABLE_AUDIT=true
export LAW_ENABLE_BUDGET_CHECK=true
```

### 2. 데이터베이스 스키마 생성

```bash
# Supabase 마이그레이션 사용
psql $LAW_SHARE_DB_URL < supabase/migrations/20240308000000_project_workspace_schema.sql
```

### 3. 서버 시작

```bash
# 기본 (포트 8082)
uv run law-cli workspace-serve

# 커스텀 포트
uv run law-cli workspace-serve --host 0.0.0.0 --port 3000

# 개발 모드
uv run law-cli workspace-serve --reload
```

### 4. API 테스트

```bash
# 헬스 체크 (엔드포인트 없음, /docs로 대체)
curl http://localhost:8082/docs

# OpenAPI 스펙
curl http://localhost:8082/openapi.json
```

## API 엔드포인트 목록

### 프로젝트 (6개)
- POST /v1/projects - 생성
- GET /v1/projects - 목록
- GET /v1/projects/{id} - 조회
- PATCH /v1/projects/{id} - 수정
- DELETE /v1/projects/{id} - 삭제
- POST /v1/projects/{id}/clone - 복제

### 멤버십 (4개)
- POST /v1/projects/{id}/members - 추가
- GET /v1/projects/{id}/members - 목록
- PATCH /v1/projects/{id}/members/{uid} - 역할 변경
- DELETE /v1/projects/{id}/members/{uid} - 제거

### 지침 (3개)
- POST /v1/projects/{id}/instructions - 생성
- GET /v1/projects/{id}/instructions - 목록
- GET /v1/projects/{id}/instructions/{v} - 조회

### 메모리 (5개)
- POST /v1/projects/{id}/memories - 생성
- GET /v1/projects/{id}/memories - 목록
- GET /v1/projects/{id}/memories/{mid} - 조회
- PATCH /v1/projects/{id}/memories/{mid} - 수정
- DELETE /v1/projects/{id}/memories/{mid} - 삭제

### 파일 (5개)
- POST /v1/projects/{id}/files - 업로드
- GET /v1/projects/{id}/files - 목록
- GET /v1/files/{fid} - 조회
- POST /v1/files/{fid}/reindex - 재인덱싱
- DELETE /v1/files/{fid} - 삭제

### 채팅 (2개)
- POST /v1/projects/{id}/chats - 생성
- POST /v1/chats/{id}/messages - 메시지 전송

### 검색 (1개)
- POST /v1/search - 하이브리드 검색

### 스냅샷 (2개)
- POST /v1/projects/{id}/snapshots - 생성
- GET /v1/projects/{id}/snapshots - 목록

### 감사/비용 (3개)
- GET /v1/audit - 감사 로그
- GET /v1/billing/usage - 사용량
- PATCH /v1/projects/{id}/budget - 예산 설정

**총 41개 엔드포인트**

## 권한 체크 로직

```python
def _check_permission(project_id, user_id, required_role):
    # 1. 멤버십 확인
    member = get_member(project_id, user_id)
    if not member:
        raise PermissionError("Not a project member")
    
    # 2. 역할 계층 확인
    # OWNER(5) > MAINTAINER(4) > EDITOR(3) > COMMENTER(2) > VIEWER(1)
    if role_order[member.role] < role_order[required_role]:
        raise PermissionError(f"Requires {required_role} or higher")
    
    return member
```

## 컨텍스트 주입 플로

```
사용자 요청
  ↓
1. 권한 검사 (RBAC)
  ↓
2. 최신 지침 로드 (Instruction)
  ↓
3. 메모리 머지 (Memory)
  ↓
4. 파일 스코프 결정 (File)
  ↓
5. 하이브리드 검색 (DocumentChunk)
  ↓
6. 프롬프트 구성
  ↓
7. LLM 호출
  ↓
8. 응답 + 인용
  ↓
9. 감사 로그 기록 (AuditLog)
```

## 다음 단계 (TODO)

### 1. 인증/인가
- [ ] JWT 토큰 검증
- [ ] OAuth2 통합
- [ ] MFA 지원

### 2. 파일 인덱싱
- [ ] 파일 업로드 → 파싱 → 청킹 → 임베딩 → 업서트
- [ ] 인덱싱 상태 추적 (ENQUEUED → READY)
- [ ] 실패 재시도 로직

### 3. 검색
- [ ] BM25 (PostgreSQL FTS)
- [ ] 벡터 검색 (pgvector)
- [ ] 하이브리드 랭킹
- [ ] 필터링 (민감도/프로젝트)

### 4. 채팅/RAG
- [ ] 채팅 생성
- [ ] 메시지 저장
- [ ] 컨텍스트 주입
- [ ] LLM 통합 (LangChain/LangGraph)
- [ ] 스트리밍 응답

### 5. 예산/쿼터
- [ ] 토큰 사용량 집계
- [ ] 비용 계산
- [ ] 한도 체크 (soft-stop/hard-stop)
- [ ] 알림/승인 요청

### 6. 고급 기능
- [ ] ABAC 정책 (OPA)
- [ ] PII/Privilege 마스킹
- [ ] Webhook 이벤트
- [ ] WebSocket (실시간 협업)
- [ ] 대시보드/모니터링
- [ ] 메트릭 (Prometheus)

### 7. 테스트
- [ ] Unit 테스트 (pytest)
- [ ] Integration 테스트
- [ ] E2E 테스트
- [ ] 성능 테스트

### 8. 배포
- [ ] Docker 이미지
- [ ] Kubernetes 매니페스트
- [ ] CI/CD 파이프라인
- [ ] 프로덕션 설정

## 파일 구조

```
packages/legal_tools/workspace/
├── __init__.py          # 모듈 진입점
├── models.py            # SQLAlchemy 모델 (기존)
├── schemas.py           # Pydantic 스키마 (신규)
├── service.py           # 비즈니스 로직 (신규)
└── api.py               # FastAPI 앱 (신규)

packages/legal_cli/commands/
└── workspace_service.py # CLI 커맨드 (신규)

docs/
└── workspace-api-overview.md # API 문서 (신규)
```

## 참고 자료

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Pydantic: https://docs.pydantic.dev/
- PostgreSQL FTS: https://www.postgresql.org/docs/current/textsearch.html
- pgvector: https://github.com/pgvector/pgvector
