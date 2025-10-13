# 법률 LLM 에이전트 프론트엔드

법률 LLM 에이전트를 위한 [ChatKit](http://openai.github.io/chatkit-js/) 기반 프론트엔드 애플리케이션. 근거 기반 법률 문서 생성, 인용 검증, 정책 검토 등을 지원하는 UI 컴포넌트 라이브러리를 포함합니다.

## 주요 기능

- **ChatKit 통합**: OpenAI의 ChatKit 웹 컴포넌트와 테마 제어
- **법률 전용 UI 컴포넌트**: 근거 카드, 조항 비교, 인용 팝오버, 정책 위반 알림 등
- **RAG-First 아키텍처**: 검색 기반 근거 제시 및 인용 검증
- **투명성 & Provenance**: 모델/프롬프트/인덱스 버전 추적
- **다크 모드 지원**: 색맹 친화적 디자인

## Getting Started

Follow every step below to run the app locally and configure it for your preferred backend.

### 1. Install dependencies

```bash
npm install
```

### 2. Create your environment file

Copy the example file and fill in the required values:

```bash
cp .env.example .env.local
```

### 3. Configure ChatKit credentials

Update `.env.local` with the variables that match your setup.

- `OPENAI_API_KEY` — API key with access to ChatKit.
- `NEXT_PUBLIC_CHATKIT_WORKFLOW_ID` — the workflow you created in the ChatKit dashboard.
- (optional) `CHATKIT_API_BASE` - customizable base URL for the ChatKit API endpoint

### 4. Run the app

```bash
npm run dev
```

Visit `http://localhost:3000` and start chatting. Use the prompts on the start screen to verify your workflow connection, then customize the UI or prompt list in [`lib/config.ts`](lib/config.ts) and [`components/ChatKitPanel.tsx`](components/ChatKitPanel.tsx).

### 5. Build for production (optional)

```bash
npm run build
npm start
```

## 공유 UI 컴포넌트 라이브러리

### 근거 & 인용 컴포넌트

#### `<EvidenceCard />`
법령/판례/문서 근거를 표시하는 카드. 출처 유형, 제목/번호, 스니펫, pin-cite 포함.

```tsx
import { EvidenceCard } from "@/components/EvidenceCard";

<EvidenceCard
  evidence={{
    id: "ev1",
    type: "statute",
    title: "민법",
    number: "제750조",
    snippet: "고의 또는 과실로 인한 위법행위로...",
    pinCite: "제750조",
    confidence: 0.95,
  }}
  onOpenSource={(ev) => console.log(ev)}
/>
```

#### `<CitationPopover />`
문단 내 주장에 호버/클릭 시 근거를 팝오버로 표시.

```tsx
import { CitationPopover } from "@/components/CitationPopover";

<p>
  계약 당사자는{" "}
  <CitationPopover
    text="불법행위에 대해 손해배상책임을 진다"
    evidence={evidenceList}
    status="verified"
  />
</p>
```

#### `<ClaimEvidenceMatrix />`
주장 × 근거 매트릭스 테이블. 관련도를 시각화.

```tsx
import { ClaimEvidenceMatrix } from "@/components/ClaimEvidenceMatrix";

<ClaimEvidenceMatrix
  claims={claims}
  evidence={evidence}
  cells={cells}
  onCellClick={(claimId, evidenceId) => {...}}
/>
```

### 문서 검토 컴포넌트

#### `<ClauseDiffCard />`
계약서 조항 before/after 비교 카드. 위험 태그, 인용 각주, 승인/거부/수정 액션 포함.

```tsx
import { ClauseDiffCard } from "@/components/ClauseDiffCard";

<ClauseDiffCard
  diff={{
    before: "원래 조항...",
    after: "수정된 조항...",
    riskLevel: "medium",
    citations: [...],
  }}
  onAccept={(id) => {...}}
  onReject={(id) => {...}}
  onRevise={(id) => {...}}
/>
```

#### `<PolicyViolationAlert />`
UPL, 개인정보, Hallucination 등 정책 위반 알림.

```tsx
import { PolicyViolationAlert } from "@/components/PolicyViolationAlert";

<PolicyViolationAlert
  violations={violations}
  onResolve={(id) => {...}}
  onViewGuide={(violation) => {...}}
/>
```

### 상태 & 메타데이터 컴포넌트

#### `<StatusBadge />`
문서 상태(Draft → CiteCheck → PolicyCheck → Approved) 뱃지.

```tsx
import { StatusBadge } from "@/components/StatusBadge";

<StatusBadge status="cite_check" />
```

#### `<RiskBadge />`
위험도(High/Medium/Low) 뱃지.

```tsx
import { RiskBadge } from "@/components/RiskBadge";

<RiskBadge level="high" />
```

#### `<ProvenanceFooter />`
모델/프롬프트/인덱스/정책 버전 정보 푸터.

```tsx
import { ProvenanceFooter } from "@/components/ProvenanceFooter";

<ProvenanceFooter
  provenance={{
    modelVersion: "gpt-4-turbo-2024-04-09",
    promptVersion: "v2.3.1",
    indexVersion: "idx-20240815",
    policyVersion: "policy-v1.2",
    timestamp: new Date().toISOString(),
  }}
  auditId="audit-20241008-001"
/>
```

### 검색 & 입력 컴포넌트

#### `<SearchBar />`
법령/판례/문서 검색 바. Debounce, 필터(분야/출처/날짜) 포함.

```tsx
import { SearchBar } from "@/components/SearchBar";

<SearchBar
  onSearch={(filter) => console.log(filter)}
  showFilters
/>
```

#### `<LoadingSpinner />`
로딩 상태 표시.

```tsx
import { LoadingSpinner } from "@/components/LoadingSpinner";

<LoadingSpinner size="md" label="검색 중..." />
```

## 공유 로직 & Hooks

### `lib/utils.ts`
- `cn()`: Tailwind 클래스 병합
- `formatDate()`, `formatLegalReference()`: 날짜/법령 포맷팅
- `highlightText()`, `truncate()`: 텍스트 처리
- `parsePinCite()`: Pin cite 파싱 (예: "제10조 제2항")
- `getRiskColorClass()`, `getCiteStatusColorClass()`: 색상 유틸
- `maskPII()`: 개인정보 마스킹
- `debounce()`, `deepClone()`, `chunkArray()`: 일반 유틸

### `lib/types.ts`
공용 타입 정의:
- `EvidenceSource`, `Claim`, `ClauseDiff`, `ClaimEvidenceCell`
- `PolicyViolation`, `CitationVerificationResult`
- `DocumentMetadata`, `Matter`, `SearchFilter`
- `Provenance`, `AuditLogEntry`, `UserPermissions`

### Custom Hooks

#### `useDebounce(value, delay)`
값 변경을 지연시켜 빈번한 업데이트 방지.

```tsx
import { useDebounce } from "@/hooks/useDebounce";

const [query, setQuery] = useState("");
const debouncedQuery = useDebounce(query, 500);
```

#### `useLocalStorage(key, initialValue)`
localStorage와 React state 동기화.

```tsx
import { useLocalStorage } from "@/hooks/useLocalStorage";

const [settings, setSettings] = useLocalStorage("legal-settings", {});
```

#### `useColorScheme()`
다크/라이트 모드 전환.

```tsx
import { useColorScheme } from "@/hooks/useColorScheme";

const { scheme, setScheme } = useColorScheme();
```

## 데모 페이지

모든 컴포넌트의 사용 예시는 `/demo` 경로에서 확인:

```bash
npm run dev
# http://localhost:3000/demo
```

## 아키텍처 원칙

1. **근거 우선 (RAG-First)**: 모든 주장에 인용 근거 필수
2. **투명성 (Transparency)**: Provenance 정보 추적
3. **정책 준수 (Compliance)**: UPL/PII/Scope 자동 검증
4. **접근성 (Accessibility)**: ARIA 레이블, 키보드 탐색, 색맹 친화적
5. **타입 안정성 (Type Safety)**: TypeScript strict 모드

## 프로젝트 구조

```
ai_frontend/
├── app/
│   ├── api/create-session/    # ChatKit 세션 생성 API
│   ├── demo/                   # 컴포넌트 데모 페이지
│   ├── App.tsx                 # 메인 앱 컴포넌트
│   └── page.tsx                # 홈 페이지
├── components/
│   ├── ChatKitPanel.tsx        # ChatKit 통합 패널
│   ├── EvidenceCard.tsx        # 근거 카드
│   ├── CitationPopover.tsx     # 인용 팝오버
│   ├── ClaimEvidenceMatrix.tsx # 주장×근거 매트릭스
│   ├── ClauseDiffCard.tsx      # 조항 비교 카드
│   ├── PolicyViolationAlert.tsx # 정책 위반 알림
│   ├── ProvenanceFooter.tsx    # Provenance 푸터
│   ├── SearchBar.tsx           # 검색 바
│   ├── StatusBadge.tsx         # 상태 뱃지
│   ├── RiskBadge.tsx           # 위험도 뱃지
│   ├── LoadingSpinner.tsx      # 로딩 스피너
│   └── ErrorOverlay.tsx        # 에러 오버레이
├── hooks/
│   ├── useColorScheme.ts       # 다크모드 hook
│   ├── useDebounce.ts          # Debounce hook
│   └── useLocalStorage.ts      # LocalStorage hook
├── lib/
│   ├── config.ts               # ChatKit 설정
│   ├── types.ts                # 공용 타입 정의
│   └── utils.ts                # 유틸리티 함수
└── README.md
```

## 라이선스

이 프로젝트는 법률 LLM 에이전트 프로젝트의 일부입니다.

## Customization Tips

- Adjust starter prompts, greeting text, and placeholder copy in [`lib/config.ts`](lib/config.ts).
- Update the theme defaults or event handlers inside[`components/ChatKitPanel.tsx`](components/ChatKitPanel.tsx) to integrate with your product analytics or storage.

## References

- [ChatKit JavaScript Library](http://openai.github.io/chatkit-js/)
- [Advanced Self-Hosting Examples](https://github.com/openai/openai-chatkit-advanced-samples)
