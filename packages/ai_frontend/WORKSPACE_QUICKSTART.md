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

- 최신 프로젝트부터 위에서 아래로 표시
- "On track" 상태 표시
- 멤버 수, 파일 수, 생성 시간 표시

### 프로젝트 상세 (`/workspace/[projectId]`)

3개 탭으로 구성:
- **파일**: 업로드된 문서 관리
- **채팅**: 대화 세션 관리
- **메모리**: 프로젝트 컨텍스트 저장

## 🛠️ API 엔드포인트

### 프로젝트

- `GET /v1/projects` - 프로젝트 목록
- `POST /v1/projects` - 프로젝트 생성
- `GET /v1/projects/{id}` - 프로젝트 조회
- `PATCH /v1/projects/{id}` - 프로젝트 수정
- `DELETE /v1/projects/{id}` - 프로젝트 삭제

### 파일

- `GET /v1/projects/{id}/files` - 파일 목록
- `POST /v1/projects/{id}/files` - 파일 업로드
- `DELETE /v1/files/{id}` - 파일 삭제

### 채팅

- `GET /v1/projects/{id}/chats` - 채팅 목록
- `POST /v1/projects/{id}/chats` - 채팅 생성
- `GET /v1/chats/{id}/messages` - 메시지 목록
- `POST /v1/chats/{id}/messages` - 메시지 전송

### 메모리

- `GET /v1/projects/{id}/memories` - 메모리 목록
- `POST /v1/projects/{id}/memories` - 메모리 생성
- `PATCH /v1/memories/{id}` - 메모리 수정
- `DELETE /v1/memories/{id}` - 메모리 삭제

## 💡 사용 팁

### 프로젝트 구조화

각 프로젝트는 독립된 컨텍스트를 가집니다:

```
프로젝트 A (계약서 검토)
├── 파일: contract_v1.pdf, contract_v2.pdf
├── 채팅: "조항 해석", "리스크 분석"
└── 메모리:
    ├── fact: "당사자는 A사와 B사"
    ├── preference: "간결한 요약 선호"
    └── context: "부동산 매매 계약"

프로젝트 B (소송 준비)
├── 파일: evidence1.pdf, testimony.docx
├── 채팅: "증거 분석", "전략 수립"
└── 메모리: ...
```

### 메모리 타입 활용

- **fact**: 객관적 사실 ("당사자 이름: 김철수")
- **preference**: 사용자 선호 ("상세 설명 원함")
- **context**: 배경 정보 ("부동산 계약 관련")
- **decision**: 중요 결정 ("A안으로 진행")

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
