# Workspace 통합 - 빠른 시작 가이드

## 🚀 시작하기

### 1. 데이터베이스 마이그레이션 및 초기화

터미널 1에서 (최초 1회만):

```bash
cd /Users/brainer/Programming/law

# Python 환경 설정 (이미 되어있다면 생략)
uv venv
uv sync

# 데이터베이스 마이그레이션 실행
uv run python scripts/run_workspace_migrations.py

# 데이터베이스 초기화 (데모 데이터 생성)
uv run python scripts/init_workspace_db.py
```

> 참고: 프로젝트 생성 시 기본 Organization을 자동으로 만들고 싶다면
> `LAW_WORKSPACE_AUTO_CREATE_DEFAULT_ORG=true` 환경 변수를 설정하세요.

### 2. Backend API 실행

터미널 1에서:

```bash
# Workspace API 서버 실행 (포트 8082)
uv run law-cli workspace-serve
```

또는 커스텀 포트:

```bash
uv run law-cli workspace-serve --port 8001
```

### 3. Frontend 실행

터미널 2에서:

```bash
cd packages/ai_frontend

# 환경 변수 설정 (.env.local 파일이 없다면)
# NEXT_PUBLIC_WORKSPACE_API_URL=http://localhost:8082 추가

# 개발 서버 실행
npm run dev
```

### 4. 브라우저에서 확인

1. http://localhost:3000 접속
2. 로그인 (또는 개발 모드에서는 자동으로 demo user 사용)
3. 상단 내비게이션에서 "프로젝트" 클릭
4. Demo Project가 표시되는지 확인
5. "새 프로젝트" 버튼으로 프로젝트 생성

## 📁 주요 화면

### 프로젝트 타임라인 (`/workspace`)

- 최근에 업데이트된 프로젝트부터 순서대로 노출
- 각 카드에서 지침 최신 버전 및 요약 미리보기 제공
- 아카이브 여부, 마지막 업데이트 시점, 설명을 빠르게 확인

### 프로젝트 상세 (`/workspace/[projectId]`)

- 지침 버전 히스토리를 타임라인으로 표시
- 새 시스템 지침을 작성하면 자동으로 버전이 증가
- 작성자, 작성 일시, 본문을 그대로 확인 가능
- 멤버 수와 마지막 프로젝트 업데이트 시간을 상단에서 집계

## 🛠️ API 엔드포인트

### 프로젝트

- `GET /v1/projects` - 프로젝트 목록
- `POST /v1/projects` - 프로젝트 생성
- `GET /v1/projects/{id}` - 프로젝트 조회
- `PATCH /v1/projects/{id}` - 프로젝트 수정
- `DELETE /v1/projects/{id}` - 프로젝트 삭제
- `POST /v1/projects/{id}/clone` - 프로젝트 복제

### 멤버십

- `GET /v1/projects/{id}/members` - 멤버 목록
- `POST /v1/projects/{id}/members` - 멤버 추가
- `PATCH /v1/projects/{id}/members/{userId}` - 역할 변경
- `DELETE /v1/projects/{id}/members/{userId}` - 멤버 제거

### 지침

- `GET /v1/projects/{id}/instructions` - 지침 버전 목록
- `GET /v1/projects/{id}/instructions/{version}` - 특정 버전 조회
- `POST /v1/projects/{id}/instructions` - 새 버전 생성

## 💡 사용 팁

### 프로젝트 구성 아이디어

각 프로젝트는 독립된 컨텍스트를 가지며, 지침(versioned instruction)과 멤버 권한을 독립적으로 관리합니다:

```
프로젝트 A (계약 검토)
├── 지침: v1 "근거 조문 필수", v2 "존댓말 답변"
├── 멤버: Owner 1명, Reviewer 2명
└── 상태: 진행 중 (status = "active")

프로젝트 B (소송 준비)
├── 지침: v1 "판례 우선 정리"
├── 멤버: Owner 1명, Collaborator 3명
└── 상태: 보류 (status = "blocked"), archived = true
```

### 지침 버전 관리 팁

- 주요 정책 변경은 새로운 버전으로 남겨 변경 이력을 투명하게 유지하세요.
- 버전을 되돌리는 대신, 최신 버전에 이전 내용을 다시 기록해 추적 가능성을 확보합니다.
- 작성자 UUID가 표시되므로, 협업 시 누가 어떤 버전을 만들었는지 쉽게 확인할 수 있습니다.

## 🐛 문제 해결

### Backend 연결 안 됨

```
Failed to fetch
```

**체크리스트**:
1. Backend API가 8001 포트에서 실행 중인지 확인
2. `http://localhost:8001/docs` 접속하여 API 문서 확인
3. CORS 설정 확인 (이미 추가됨)

### 인증 오류

```
Authentication required
```

**해결**:
1. 로그인 상태 확인
2. `useAuth` 훅에서 `user.id` 반환 확인
3. API 클라이언트가 `X-User-ID` 헤더를 보내는지 확인

### 타입스크립트 오류

```bash
npm run build
```
로 미리 빌드 오류 체크

## 📚 더 보기

- [상세 통합 가이드](./WORKSPACE_INTEGRATION.md)
- [Workspace API 문서](../../docs/workspace-api-overview.md)
- [Backend API 구현](../legal_tools/workspace/)
