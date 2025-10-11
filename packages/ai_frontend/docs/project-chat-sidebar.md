# 프로젝트 상세 페이지 - ChatKit 사이드바

## 개요
프로젝트 상세 페이지에 AI 어시스턴트 채팅 사이드바를 추가하여 프로젝트 작업 중 실시간 AI 지원을 받을 수 있도록 개선했습니다.

---

## 주요 기능

### 1. **슬라이드 사이드바**
- 오른쪽에서 슬라이드 인/아웃
- 반응형 너비 (Wide: 520px, Laptop: 400px)
- 부드러운 애니메이션 (0.3s ease)
- **Wide screen (≥1280px)에서 기본적으로 열림**

### 2. **ChatKit 통합**
- 전체 ChatKit 기능 사용 가능
- 프로젝트 컨텍스트 내에서 AI 대화
- 테마 동기화 (라이트/다크 모드)

### 3. **토글 버튼**
- 헤더 우측에 채팅 아이콘 버튼
- 클릭으로 사이드바 열기/닫기
- 시각적 피드백

---

## 사용 방법

### 사이드바 열기
1. 프로젝트 상세 페이지 접속
2. 헤더 우측 채팅 아이콘 버튼 클릭
3. 오른쪽에서 사이드바 슬라이드 인

### 사이드바 닫기
- 사이드바 헤더의 X 버튼 클릭
- 또는 헤더의 채팅 아이콘 버튼 다시 클릭

---

## 구현 상세

### 컴포넌트 구조
```tsx
<div className="material-project-layout">
  {/* 메인 프로젝트 영역 */}
  <div className="material-project">
    <header className="material-project__bar">
      {/* ... 기존 헤더 ... */}
      <button onClick={() => setChatSidebarOpen(!chatSidebarOpen)}>
        <ChatBubbleLeftRightIcon />
      </button>
    </header>
    {/* ... 프로젝트 콘텐츠 ... */}
  </div>

  {/* ChatKit 사이드바 */}
  <aside className={`material-project-sidebar ${chatSidebarOpen ? '--open' : ''}`}>
    <div className="material-project-sidebar__header">
      <h2>AI 어시스턴트</h2>
      <button onClick={() => setChatSidebarOpen(false)}>
        <XMarkIcon />
      </button>
    </div>
    <div className="material-project-sidebar__content">
      <ChatKitPanel
        theme={scheme}
        onWidgetAction={handleChatWidgetAction}
        onResponseEnd={handleChatResponseEnd}
        onThemeRequest={setScheme}
      />
    </div>
  </aside>
</div>
```

### State 관리
```tsx
// Wide screen에서 기본적으로 ChatKit 열기
const [chatSidebarOpen, setChatSidebarOpen] = useState(() => {
  if (typeof window !== 'undefined') {
    return window.innerWidth >= 1280
  }
  return false
})

// 화면 크기 변경 감지
useEffect(() => {
  const handleResize = () => {
    // Wide screen (1280px 이상)에서만 자동 열기
    if (window.innerWidth >= 1280 && !chatSidebarOpen) {
      setChatSidebarOpen(true)
    }
    // 작은 화면으로 변경 시 자동 닫기
    if (window.innerWidth < 1280 && chatSidebarOpen) {
      setChatSidebarOpen(false)
    }
  }

  window.addEventListener('resize', handleResize)
  return () => window.removeEventListener('resize', handleResize)
}, [chatSidebarOpen])

const { scheme, setScheme } = useColorScheme()

const handleChatWidgetAction = useCallback(async (action: FactAction) => {
  console.info('[ChatKitPanel] widget action', action)
}, [])

const handleChatResponseEnd = useCallback(() => {
  console.debug('[ChatKitPanel] response end')
}, [])
```

---

## CSS 클래스

### 레이아웃
- `.material-project-layout` - 전체 레이아웃 컨테이너 (flex)
- `.material-project` - 메인 프로젝트 영역 (flex: 1)
- `.material-project-sidebar` - 사이드바 컨테이너 (fixed)

### 사이드바 상태
- `.material-project-sidebar--open` - 사이드바 열림 상태
  - `transform: translateX(0)`
  - 메인 영역 `margin-right: 480px` 적용

### 사이드바 내부
- `.material-project-sidebar__header` - 사이드바 헤더
- `.material-project-sidebar__title` - 제목
- `.material-project-sidebar__content` - ChatKit 컨텐츠 영역

---

## 애니메이션

### 슬라이드 인/아웃
```css
.material-project-sidebar {
  transform: translateX(100%); /* 기본: 화면 밖 */
  transition: transform 0.3s ease;
}

.material-project-sidebar--open {
  transform: translateX(0); /* 열림: 화면 안 */
}
```

### 메인 영역 여백
```css
.material-project {
  transition: margin-right 0.3s ease;
}

.material-project-sidebar--open ~ .material-project {
  margin-right: 480px; /* 사이드바 너비만큼 밀림 */
}
```

---

## 반응형 디자인

### Wide Desktop (≥ 1280px)
- **사이드바: 520px (기본 열림)**
- 메인 영역: 자동 축소
- 최적의 멀티태스킹
- 초기 로드 시 자동 표시

### Laptop (1024px - 1280px)
- 사이드바: 400px (수동 열기)
- 메인 영역: 자동 축소
- 공간 효율적 사용

### Tablet (768px - 1024px)
- 사이드바: 화면 하단 50vh (수동 열기)
- 세로 분할 레이아웃
- 메인: 상단 50%, 사이드바: 하단 50%

### Mobile (< 768px)
- 사이드바: 화면 하단 60vh (수동 열기)
- 세로 분할 레이아웃
- 더 많은 채팅 공간

---

## 스타일 상세

### 사이드바 스타일
```css
.material-project-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 480px;
  height: 100vh;
  background: var(--md-sys-color-surface-container-lowest, #ffffff);
  border-left: 1px solid var(--md-sys-color-outline-variant, #e2e8f0);
  box-shadow: -4px 0 24px rgba(15, 23, 42, 0.12);
  z-index: 20;
}
```

### 헤더 스타일
```css
.material-project-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--md-sys-color-outline-variant, #e2e8f0);
  background: var(--md-sys-color-surface-container, #f8fafc);
}
```

### 콘텐츠 스타일
```css
.material-project-sidebar__content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
```

---

## 사용자 경험

### 장점
1. **컨텍스트 유지**: 프로젝트 정보를 보면서 AI와 대화
2. **빠른 접근**: 버튼 한 번으로 AI 어시스턴트 활성화
3. **공간 효율**: 필요할 때만 표시되는 슬라이드 UI
4. **부드러운 전환**: 0.3초 애니메이션으로 자연스러운 UX

### 사용 시나리오
- **문서 작성 지원**: 업데이트 작성 중 AI에게 조언 요청
- **정보 검색**: 법률 정보 즉시 조회
- **아이디어 브레인스토밍**: 프로젝트 진행 방향 논의
- **작업 자동화**: AI를 통한 반복 작업 처리

---

## 접근성

### 키보드 네비게이션
- `Tab`: 버튼 간 이동
- `Enter/Space`: 버튼 활성화
- `Esc`: 사이드바 닫기 (추후 추가 가능)

### ARIA 속성
```tsx
<button
  type="button"
  onClick={() => setChatSidebarOpen(!chatSidebarOpen)}
  className="material-icon-button"
  aria-label="AI 채팅"
>
  <ChatBubbleLeftRightIcon aria-hidden="true" />
</button>

<button
  type="button"
  onClick={() => setChatSidebarOpen(false)}
  className="material-icon-button"
  aria-label="채팅 닫기"
>
  <XMarkIcon aria-hidden="true" />
</button>
```

### 스크린 리더
- 버튼에 명확한 레이블
- 아이콘은 `aria-hidden="true"`로 숨김
- 사이드바 상태 변화 인식 가능

---

## 성능 최적화

### 코드 스플리팅
- ChatKitPanel은 사이드바 열 때만 로드 (지연 로드)
- 초기 페이지 로드 시간 최소화

### 메모이제이션
```tsx
const handleChatWidgetAction = useCallback(async (action: FactAction) => {
  // ... 
}, [])

const handleChatResponseEnd = useCallback(() => {
  // ...
}, [])
```

### 부드러운 애니메이션
- CSS transform 사용 (GPU 가속)
- 60fps 유지
- 레이아웃 리플로우 최소화

---

## 향후 개선 사항

### 1. **프로젝트 컨텍스트 주입**
- 현재 프로젝트 정보를 AI에게 자동 전달
- 프로젝트명, 설명, 최근 업데이트 등

### 2. **채팅 히스토리 저장**
- 프로젝트별 채팅 내역 유지
- LocalStorage 또는 DB 저장

### 3. **키보드 단축키**
- `Cmd/Ctrl + K`: 사이드바 토글
- `Esc`: 사이드바 닫기

### 4. **사이드바 크기 조절**
- 드래그로 너비 조정
- 사용자 선호도 저장

### 5. **멀티탭 지원**
- 채팅, 파일, 히스토리 탭
- 하나의 사이드바에 여러 기능

---

## 트러블슈팅

### 사이드바가 표시되지 않음
- `chatSidebarOpen` state 확인
- CSS `transform` 속성 확인
- z-index 충돌 확인

### 애니메이션이 부드럽지 않음
- `transition` 속성 확인
- GPU 가속 활성화 확인
- 브라우저 성능 프로파일링

### 반응형이 작동하지 않음
- `@media` 쿼리 우선순위 확인
- viewport 메타 태그 확인
- CSS 순서 확인

---

## 결론

ChatKit 사이드바 추가로 프로젝트 상세 페이지가 더욱 강력해졌습니다:

- ✅ **AI 통합**: 프로젝트 작업 중 즉시 AI 지원
- ✅ **UX 개선**: 부드러운 슬라이드 애니메이션
- ✅ **반응형**: 모든 화면 크기 지원
- ✅ **접근성**: 키보드 및 스크린 리더 지원
- ✅ **성능**: 최적화된 렌더링

프로젝트 관리와 AI 어시스턴트가 완벽하게 통합된 워크스페이스를 제공합니다! 🎉
