# Workspace Integration - 구현 가이드

## 개요

Workspace API를 ai_frontend에 통합하여 프로젝트 중심의 컨텍스트 관리 UI를 구현했습니다. 제공된 스크린샷과 유사한 타임라인 스타일로, 최신 프로젝트가 위에 표시되는 방식입니다.

## 구현된 기능

### 1. 프로젝트 타임라인 (`/workspace`)

- **최신 업데이트 순 정렬**: `updated_at` 기준으로 최신 프로젝트가 상단에 표시
- **지침 스냅샷**: 카드에서 최신 지침 버전과 본문 요약 제공
- **상태 표시**: Active/Archived 상태 뱃지, 다크 모드 대응

### 2. 프로젝트 생성 모달

- 프로젝트 이름, 설명, 진행 상태 설정
- 실시간 유효성 검증
- 에러 핸들링 및 사용자 피드백

### 3. 프로젝트 상세 페이지 (`/workspace/[projectId]`)

- 지침 버전 히스토리를 타임라인으로 표시
- 새 지침 버전을 작성할 수 있는 에디터 제공
- 작성자, 작성 시각, 본문이 한 카드에 정리되어 감사 추적이 간편
- 프로젝트 멤버 수, 마지막 업데이트 시각을 상단에서 확인

## 파일 구조

```
packages/ai_frontend/
├── lib/
│   └── workspace/
│       └── client.ts              # Workspace API 클라이언트 (zod 스키마 + fetch 래퍼)
├── components/
│   └── workspace/
│       ├── ProjectTimeline.tsx    # 프로젝트 타임라인 (지침 요약 포함)
│       └── CreateProjectModal.tsx # 프로젝트 생성 모달
└── app/
    └── workspace/
        ├── page.tsx               # 워크스페이스 메인 페이지
        └── [projectId]/
            └── page.tsx           # 지침 중심 프로젝트 상세 페이지
```

## 설정 방법

### 1. 환경 변수 설정

`.env.local` 파일에 다음을 추가:

```bash
NEXT_PUBLIC_WORKSPACE_API_URL=http://localhost:8001
```

### 2. 의존성 설치

이미 설치되었지만, 새로 설치할 경우:

```bash
cd packages/ai_frontend
npm install zod date-fns @heroicons/react
```

### 3. Backend API 실행

Workspace API 서버를 실행해야 합니다:

```bash
cd packages/legal_tools/workspace
# Python 환경 활성화 후
uvicorn api:app --host 0.0.0.0 --port 8001
```

또는 `law-cli`로:

```bash
uv run law-cli serve-workspace --port 8001
```

## 사용 방법

### 1. 프로젝트 목록 보기

로그인 후 상단 내비게이션에서 "프로젝트" 클릭:

- `/workspace` 경로로 이동
- 최신 프로젝트부터 타임라인 형태로 표시
- 각 카드 클릭 시 상세 페이지로 이동

### 2. 새 프로젝트 만들기

1. "새 프로젝트" 버튼 클릭
2. 모달에서 이름, 설명, 진행 상태 입력
3. "프로젝트 만들기" 버튼 클릭
4. 타임라인에 자동으로 추가됨

### 3. 프로젝트 상세 보기

프로젝트 카드 클릭 → `/workspace/[projectId]`

- **지침 히스토리**: 버전별 작성자, 작성 시각, 본문 확인
- **새 지침 작성**: 상단 입력창에서 새로운 버전 저장
- **멤버 현황**: 현재 멤버 수를 상단에서 확인

## API 클라이언트 사용 예시

```typescript
import { workspaceClient } from '@/lib/workspace/client'

// 사용자 ID 설정
workspaceClient.setUserId(user.id)

// 프로젝트 목록 가져오기
const { projects } = await workspaceClient.listProjects({ archived: false, limit: 50 })

// 새 프로젝트 생성
const project = await workspaceClient.createProject({
  name: '계약서 검토',
  description: '고객사 A 계약서 검토 프로젝트',
  status: 'active'
})

// 지침 새 버전 추가
await workspaceClient.createInstruction(project.id, {
  content: '답변 시 반드시 근거 법령과 판례를 명시합니다.',
})

// 최신 지침 조회
const instructions = await workspaceClient.listInstructions(project.id)
const latest = instructions.at(0)

// 멤버 목록 가져오기
const members = await workspaceClient.listMembers(project.id)
```

## 디자인 특징

### 타임라인 스타일

제공된 스크린샷을 참고하여:

- **카드 기반 레이아웃**: 각 프로젝트는 독립된 카드
- **지침 요약**: 최신 버전을 카드 요약으로 제공
- **메타 정보**: 멤버 수, 마지막 업데이트 시각을 아이콘과 함께 표시
- **호버 효과**: 마우스 오버 시 배경색 변경으로 인터랙티브함 강조
- **다크 모드**: 자동 다크 모드 지원

### 색상 시스템

- **Primary**: Blue-600 (액션 버튼, 링크)
- **Status**: Green-500 (Active), Gray-400 (Archived)
- **Instruction Badges**: Blue 계열 강조, 작성자/버전은 뉴트럴 톤 유지

## 향후 개선 사항

### 1. 실시간 업데이트

- WebSocket/SSE 연동으로 실시간 프로젝트 상태 업데이트
- 다른 팀원의 지침 변경을 즉시 반영

### 2. 지침 비교 뷰

- 버전 간 Diff UI 제공
- 변경 요약 및 영향도 표시

### 3. 검색 및 필터

- 프로젝트 이름/설명/지침 본문으로 검색
- 상태, 멤버, 최신 버전 작성자별 필터링

### 4. 활동 피드

- 프로젝트 내 최근 지침 변경과 멤버 활동 로그
- 알림 채널과 연동

### 5. 협업 기능

- 프로젝트 멤버 초대/관리 UX
- 권한 관리 (Owner, Maintainer, Editor 등) 시각화
- 코멘트/승인 워크플로우

### 6. 통계 대시보드

- 프로젝트별 지침 변경 빈도
- 멤버별 기여도
- 지침 준수 여부 리포트

## 트러블슈팅

### API 연결 실패

```
Failed to load projects: Failed to fetch
```

**해결책**:
1. Backend API가 실행 중인지 확인
2. `NEXT_PUBLIC_WORKSPACE_API_URL` 환경 변수 확인
3. CORS 설정 확인 (FastAPI에서 `CORSMiddleware` 설정)

### 인증 오류

```
Authentication required
```

**해결책**:
1. 사용자가 로그인되어 있는지 확인
2. `X-User-ID` 헤더가 올바르게 전송되는지 확인
3. Backend에서 인증 미들웨어 확인

### 타입 오류

TypeScript 컴파일 오류 발생 시:
```bash
npm run build
```
로 미리 확인하고 수정

## 참고 자료

- [Workspace API 문서](../../docs/workspace-api-overview.md)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Tailwind CSS](https://tailwindcss.com/)
