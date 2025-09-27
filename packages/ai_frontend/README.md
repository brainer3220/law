# @law/ai-frontend

Next.js(App Router) 기반의 법률 에이전트 UI 패키지입니다. LangGraph 백엔드(`/app/api/chat`)와 Vercel AI SDK v5를 활용하여 툴 호출 과정을 실시간으로 시각화합니다.

## 주요 기능

- **Edge Runtime** 호환 `app/api/chat/route.ts`
  - OpenAI-호환 엔드포인트(`OPENAI_BASE_URL`) 설정 지원
  - `tool()`과 `stepCountIs()`로 LangGraph 에이전트의 도구 호출을 제어
  - `onStepFinish` 콜백을 이용해 툴 타임라인 스트림 생성
- **툴 타임라인 패널**
  - `useChat` 메시지의 `parts`를 분석하여 단계별 상태/결과를 카드 형태로 렌더
  - 커스텀 UIMessage 파트를 통해 실행 중(progress) 이벤트를 스트리밍
- **shadcn/ui 스타일 시스템**
  - 최소한의 카드/배지 컴포넌트를 Tailwind로 래핑하여 재사용

## 사용 방법

```bash
cd packages/ai_frontend
pnpm install # 또는 npm install / yarn
pnpm dev
```

환경 변수:

- `OPENAI_API_KEY` – OpenAI 호환 서버에 전달될 키
- `OPENAI_BASE_URL` – 예: `http://localhost:8000/v1`
- `OPENAI_MODEL` – 기본값 `gpt-4o-mini`

## 모노레포 통합

Python 기반 LangGraph 서비스(`main.py`)와 함께 루트 모노레포에서 관리합니다. 배포 시에는 Vercel에 `packages/ai_frontend`만 빌드 대상으로 올리고, 서버리스 함수가 LangGraph 백엔드(예: FastAPI, Cloud Run)에 요청을 위임하도록 구성할 수 있습니다.
