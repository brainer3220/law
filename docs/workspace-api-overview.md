# Law Workspace API

프로젝트 중심 컨텍스트 관리 시스템 - 법률 AI 작업 공간 API

## 개요

Law Workspace API는 생성형 AI 사용 맥락을 프로젝트 단위로 관리하는 시스템입니다. 채팅, 파일, 지침, 메모리, 도구 구성을 하나의 프로젝트로 묶어 일관된 문맥과 권한/감사/비용 단위를 제공합니다.

## 주요 기능

### 1. 프로젝트 수명주기
- ✅ 프로젝트 생성/조회/수정/삭제 (soft/hard delete)
- ✅ 프로젝트 복제 (템플릿 기반)
- ✅ 프로젝트 보관 (archive)
- ✅ 가시성 제어 (private/internal/public)

### 2. 멤버십 & 권한 (RBAC)
- ✅ 역할 기반 권한: Owner, Maintainer, Editor, Commenter, Viewer
- ✅ 멤버 초대/제거
- ✅ 역할 변경
- 🔸 ABAC 확장 (라벨/민감도 기반)

### 3. 지침 (Instructions)
- ✅ 프로젝트 전역 시스템 프롬프트
- ✅ 버전 관리
- ✅ 변경 이력 추적
- 🔸 금칙어/포맷 규칙

### 4. 메모리 (Memory)
- ✅ 장기 맥락 저장 (사실/정책/용어집)
- ✅ 출처/신뢰도/만료일 메타데이터
- ✅ 키-값 기반 조회
- 🔸 충돌 해결 (프로젝트 > 조직 > 개인)

### 5. 파일 관리
- ✅ 파일 업로드 메타 관리
- ✅ 민감도 레벨 (public/internal/restricted/secret)
- ✅ 버전 관리
- 🔸 인덱싱 상태 추적
- 🔸 재인덱싱 요청

### 6. 채팅 & 메시지
- 🔸 채팅 생성
- 🔸 메시지 전송 + 컨텍스트 자동 주입
- 🔸 인용/근거 첨부

### 7. 검색
- 🔸 프로젝트 내 하이브리드 검색 (BM25 + 벡터)
- 🔸 필터링 (파일/민감도)
- 🔸 교차 프로젝트 검색

### 8. 스냅샷
- ✅ 프로젝트 상태 스냅샷 (재현성)
- ✅ 지침 버전 고정
- 🔸 파일 버전 고정

### 9. 감사 로그
- ✅ 모든 작업 기록
- ✅ 프로젝트/액션별 필터링
- ✅ IP/User-Agent 추적

### 10. 비용/예산
- 🔸 프로젝트 단위 토큰/비용 추적
- 🔸 예산 한도 설정
- 🔸 초과 시 차단/승인 요청

## 권한 매트릭스

| 권한/역할 | Owner | Maintainer | Editor | Commenter | Viewer |
|-----------|-------|------------|--------|-----------|--------|
| 프로젝트 설정/삭제 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 멤버 초대/권한 변경 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 지침/메모리 편집 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 파일 업/삭제 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 채팅 생성/이동 | ✅ | ✅ | ✅ | ✅ | ❌ |
| 스냅샷 생성 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 감사 로그 조회 | ✅ | ✅ | 🔸 | ❌ | ❌ |

## API 엔드포인트

### 프로젝트
```
POST   /v1/projects                    # 프로젝트 생성
GET    /v1/projects                    # 프로젝트 목록
GET    /v1/projects/{id}               # 프로젝트 조회
PATCH  /v1/projects/{id}               # 프로젝트 수정
DELETE /v1/projects/{id}               # 프로젝트 삭제
POST   /v1/projects/{id}/clone         # 프로젝트 복제
```

### 멤버십
```
POST   /v1/projects/{id}/members       # 멤버 추가
GET    /v1/projects/{id}/members       # 멤버 목록
PATCH  /v1/projects/{id}/members/{uid} # 역할 변경
DELETE /v1/projects/{id}/members/{uid} # 멤버 제거
```

### 지침
```
POST   /v1/projects/{id}/instructions      # 지침 생성 (새 버전)
GET    /v1/projects/{id}/instructions      # 지침 목록
GET    /v1/projects/{id}/instructions/{v}  # 특정 버전 조회
```

### 메모리
```
POST   /v1/projects/{id}/memories          # 메모리 생성
GET    /v1/projects/{id}/memories          # 메모리 목록
GET    /v1/projects/{id}/memories/{mid}    # 메모리 조회
PATCH  /v1/projects/{id}/memories/{mid}    # 메모리 수정
DELETE /v1/projects/{id}/memories/{mid}    # 메모리 삭제
```

### 파일
```
POST   /v1/projects/{id}/files         # 파일 업로드
GET    /v1/projects/{id}/files         # 파일 목록
GET    /v1/files/{fid}                 # 파일 조회
POST   /v1/files/{fid}/reindex         # 재인덱싱
DELETE /v1/files/{fid}                 # 파일 삭제
```

### 채팅
```
POST   /v1/projects/{id}/chats         # 채팅 생성
POST   /v1/chats/{id}/messages         # 메시지 전송
```

### 검색
```
POST   /v1/search                      # 하이브리드 검색
```

### 스냅샷
```
POST   /v1/projects/{id}/snapshots     # 스냅샷 생성
GET    /v1/projects/{id}/snapshots     # 스냅샷 목록
```

### 감사/비용
```
GET    /v1/audit                       # 감사 로그
GET    /v1/billing/usage               # 사용량 조회
PATCH  /v1/projects/{id}/budget        # 예산 설정
```

## 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
export LAW_WORKSPACE_DB_URL="postgresql://user:pass@localhost/law_workspace"
export LAW_ENABLE_AUDIT=true
export LAW_ENABLE_BUDGET_CHECK=true
```

### 2. 서버 시작

```bash
# 기본 포트 (8082)
uv run law-cli workspace-serve

# 커스텀 포트
uv run law-cli workspace-serve --host 0.0.0.0 --port 3000

# 개발 모드 (auto-reload)
uv run law-cli workspace-serve --reload
```

### 3. API 문서 확인

- Swagger UI: http://localhost:8082/docs
- ReDoc: http://localhost:8082/redoc
- OpenAPI JSON: http://localhost:8082/openapi.json

## 사용 예시

### 프로젝트 생성

```bash
curl -X POST http://localhost:8082/v1/projects \
  -H "Content-Type: application/json" \
  -H "X-User-ID: <your-user-id>" \
  -d '{
    "name": "계약 검토 프로젝트",
    "description": "2024 Q4 계약 검토",
    "visibility": "private"
  }'
```

### 지침 추가

```bash
curl -X POST http://localhost:8082/v1/projects/{project_id}/instructions \
  -H "Content-Type: application/json" \
  -H "X-User-ID: <your-user-id>" \
  -d '{
    "content": "법률 조언 시 반드시 근거 조문과 판례를 명시하세요. 답변은 존댓말로 작성하고, 불확실한 경우 명시적으로 표기하세요."
  }'
```

### 메모리 추가

```bash
curl -X POST http://localhost:8082/v1/projects/{project_id}/memories \
  -H "Content-Type: application/json" \
  -H "X-User-ID: <your-user-id>" \
  -d '{
    "key": "회사정책",
    "value": {"policy": "계약서 검토 시 반드시 법무팀 승인 필요"},
    "source": "사내 규정 2024-01",
    "confidence": 1.0
  }'
```

### 파일 업로드

```bash
curl -X POST http://localhost:8082/v1/projects/{project_id}/files \
  -H "Content-Type: application/json" \
  -H "X-User-ID: <your-user-id>" \
  -d '{
    "r2_key": "contracts/2024/contract-001.pdf",
    "name": "계약서 001",
    "mime": "application/pdf",
    "size_bytes": 1048576,
    "sensitivity": "restricted"
  }'
```

## 데이터베이스 스키마

### 주요 테이블

- `projects` - 프로젝트 메타데이터
- `project_members` - 멤버십
- `instructions` - 버전별 지침
- `memories` - 키-값 메모리
- `files` - 파일 메타
- `documents` - 문서 논리 단위
- `document_chunks` - 전문검색 청크
- `snapshots` - 재현성 스냅샷
- `audit_logs` - 감사 로그
- `project_budgets` - 예산 설정
- `usage_ledger` - 사용량 기록

## 아키텍처

```
┌─────────────────────┐
│   FastAPI Gateway   │
│  (workspace/api.py) │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Service Layer      │
│ (workspace/service) │
│  - 권한 체크        │
│  - 감사 로깅        │
│  - 예산 체크        │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   SQLAlchemy ORM    │
│  (workspace/models) │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   PostgreSQL 16+    │
│  + pgvector + FTS   │
└─────────────────────┘
```

## 컨텍스트 주입 플로

```
1. 권한 검사 (사용자 → 프로젝트 읽기)
2. 지침 로딩 (최신 버전)
3. 메모리 머지 (프로젝트 > 조직 > 개인)
4. 파일 스코프 결정
5. 색인/검색 (하이브리드 검색)
6. 프롬프트 구성 (지침 + 메모리 + 검색 컨텍스트)
7. 모델 호출 → 응답/인용
8. 감사 로그 기록
```

## 보안

- ✅ 역할 기반 권한 (RBAC)
- ✅ 감사 로그 (모든 작업 추적)
- 🔸 속성 기반 권한 (ABAC) - 라벨/민감도
- 🔸 PII/Privilege 자동 마스킹
- 🔸 JWT/OAuth 인증
- 🔸 MFA 지원

## 개발

### 테스트

```bash
pytest tests/test_workspace_*.py
```

### 코드 품질

```bash
ruff check packages/legal_tools/workspace/
ruff format packages/legal_tools/workspace/
mypy packages/legal_tools/workspace/
```

### 마이그레이션

```bash
# Supabase 마이그레이션 적용
psql $LAW_WORKSPACE_DB_URL < supabase/migrations/20240308000000_project_workspace_schema.sql
```

## 로드맵

- [ ] 파일 인덱싱 파이프라인 통합
- [ ] 하이브리드 검색 (BM25 + 벡터)
- [ ] 채팅 + RAG 통합
- [ ] 예산/쿼터 체크 로직
- [ ] Webhook 지원
- [ ] ABAC 정책 엔진 (OPA)
- [ ] 실시간 협업 (WebSocket)
- [ ] 대시보드/모니터링

## 라이선스

MIT

## 기여

PR 환영합니다! 

Conventional Commits 사용:
```
feat(workspace): add file indexing pipeline
fix(workspace): resolve permission check bug
docs(workspace): update API examples
```
