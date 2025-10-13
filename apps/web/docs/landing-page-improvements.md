# Landing Page UI/UX 개선 사항

## 개요
메인 랜딩 페이지(`/`)를 워크스페이스 페이지와 동일한 디자인 시스템으로 개선하여 일관성 있는 사용자 경험을 제공합니다.

---

## 주요 개선 사항

### 1. **Hero 섹션 추가**

#### Before
```
[헤더]
  - 브랜드 로고
  - 로그인/회원가입 버튼

[콘텐츠]
  - SoftrHero (iframe)
```

#### After
```
[헤더] ✨ 애니메이션 + 그라데이션 브랜드
  - 아이콘 + 브랜드명 (sparkle 애니메이션)
  - 로그인/회원가입 버튼 (slideInRight)

[Hero 섹션] 🎯 2단 그리드 레이아웃
  [좌측] 콘텐츠
    - 대형 제목 (3.5rem)
    - 그라데이션 하이라이트
    - 설명 텍스트
    - CTA 버튼 2개

  [우측] 비주얼 카드
    - 3개의 플로팅 카드
    - 각각 다른 타이밍으로 애니메이션
    - 호버 시 3D 효과

[Features 섹션]
  - SoftrHero 컨텐츠
```

---

### 2. **애니메이션 시스템**

#### 페이지 진입 애니메이션
1. **fadeIn** (0.4s) - 전체 페이지
2. **slideDown** (0.5s) - 헤더
3. **slideInRight** (0.6s) - 액션 버튼
4. **fadeIn + slideInLeft** (0.8s, 순차) - Hero 콘텐츠
   - 제목: 0.3s delay
   - 설명: 0.4s delay
   - 버튼: 0.5s delay
5. **floatCard + slideInRight** - 비주얼 카드
   - 카드 1: 0.6s delay
   - 카드 2: 0.7s delay
   - 카드 3: 0.8s delay

#### 지속 애니메이션
- **sparkle**: 브랜드 아이콘 (무한 반복)
- **floatCard**: 비주얼 카드 부유 효과 (무한 반복)

---

### 3. **시각적 개선**

#### 그라데이션 효과
```css
/* 배경 그라데이션 */
background: linear-gradient(135deg, 
  #f8fafc 0%,
  color-mix(in srgb, #2563eb 3%, #f8fafc) 100%
);

/* 브랜드 텍스트 그라데이션 */
background: linear-gradient(135deg, 
  #2563eb 0%, 
  color-mix(in srgb, #2563eb 70%, #7c3aed) 100%
);
background-clip: text;
-webkit-text-fill-color: transparent;

/* 제목 하이라이트 그라데이션 */
background: linear-gradient(135deg, 
  #2563eb 0%, 
  #7c3aed 100%
);
```

#### 타이포그래피
- **Hero 제목**: 3.5rem, 굵게(700), letter-spacing: -0.02em
- **Hero 설명**: 1.25rem, line-height: 1.7
- **브랜드**: 1.25rem, 그라데이션 적용

---

### 4. **인터랙티브 요소**

#### 플로팅 카드
```tsx
<div className="material-landing__hero-card material-landing__hero-card--1">
  <ShieldCheckIcon className="material-landing__feature-icon" />
  <span>안전한 데이터 보호</span>
</div>
```

**특징:**
- 3D perspective 효과
- floatCard 애니메이션 (3초 주기)
- 호버 시 확대 + 들어올림
- 각 카드마다 다른 애니메이션 지연

**카드 내용:**
1. 🛡️ 안전한 데이터 보호
2. ⚡ 실시간 분석
3. 🔍 정확한 판례 검색

---

### 5. **CTA (Call To Action) 개선**

#### 주요 CTA 버튼
```tsx
<button className="material-filled-button material-landing__hero-cta">
  <span>무료로 시작하기</span>
  <ArrowIcon />
</button>
```

**특징:**
- 더 큰 패딩 (14px 32px)
- 더 큰 폰트 (1.125rem)
- 강한 그림자 효과
- 호버 시 더 강한 그림자 + 들어올림

#### 보조 CTA 버튼
```tsx
<button 
  className="material-outlined-button"
  onClick={() => scrollToFeatures()}
>
  <span>기능 둘러보기</span>
</button>
```

**특징:**
- 부드러운 스크롤
- 아웃라인 스타일
- 주 CTA와 시각적 구분

---

### 6. **로딩 상태 개선**

#### Before
```jsx
<md-circular-progress indeterminate />
<p>계정을 확인하는 중입니다…</p>
```

#### After
```jsx
<div className="material-loading">
  <div className="material-loading__spinner">
    <div className="spinner-ring"></div>
  </div>
  <p className="material-body">계정을 확인하는 중입니다…</p>
</div>
```

**개선점:**
- 커스텀 링 스피너
- 일관된 스타일
- 브랜드 색상 적용

---

### 7. **반응형 디자인**

#### Desktop (> 1024px)
- 2단 그리드 레이아웃
- 제목 3.5rem
- 카드 원래 위치

#### Tablet (768px - 1024px)
- 1단 레이아웃
- 제목 2.5rem
- 카드 위치 조정

#### Mobile (< 768px)
- 헤더 세로 배치
- 제목 2rem
- 버튼 전체 너비
- 카드 크기 축소
- 더 작은 패딩

---

## 사용된 기술

### React Components
```tsx
import {
  SparklesIcon,          // 브랜드 아이콘
  ShieldCheckIcon,       // 보안 카드
  BoltIcon,              // 속도 카드
  DocumentMagnifyingGlassIcon, // 검색 카드
  ArrowRightOnRectangleIcon,   // 로그인 버튼
  UserPlusIcon,          // 회원가입 버튼
} from '@heroicons/react/24/outline';
```

### CSS Animations
```css
@keyframes slideDown { ... }
@keyframes floatCard { ... }
@keyframes sparkle { ... }
@keyframes slideInLeft { ... }
@keyframes slideInRight { ... }
```

### CSS Variables
```css
--md-sys-color-primary
--md-sys-color-surface
--md-sys-color-on-surface
--md-sys-color-on-surface-variant
--md-sys-color-outline-variant
```

---

## 성능 최적화

### 애니메이션 최적화
- `transform` 및 `opacity`만 사용 (GPU 가속)
- `will-change` 없이도 부드러운 애니메이션
- 적절한 지속 시간 (0.4s ~ 0.8s)

### 번들 크기 최적화
- Material Web Components 제거
- 순수 CSS 사용
- Tree-shaking 가능한 Heroicons

---

## 접근성

### ARIA 속성
```tsx
<SparklesIcon aria-hidden="true" />
<button type="button" onClick={...}>
  <span>버튼 텍스트</span>
</button>
```

### 키보드 네비게이션
- 모든 버튼 키보드 접근 가능
- 포커스 상태 명확
- 논리적인 탭 순서

### 시맨틱 HTML
```tsx
<main className="material-landing">
  <section className="material-landing__hero">
    <h1>제목</h1>
    <p>설명</p>
  </section>
  <section id="features">
    ...
  </section>
</main>
```

---

## 비교 요약

| 항목 | Before | After | 개선도 |
|------|--------|-------|--------|
| Hero 섹션 | ❌ 없음 | ✅ 풀 기능 Hero | ⭐⭐⭐⭐⭐ |
| 애니메이션 | ⚠️ 기본 | ✅ 8+ 애니메이션 | ⭐⭐⭐⭐⭐ |
| 브랜드 표현 | ⚠️ 텍스트만 | ✅ 아이콘 + 그라데이션 | ⭐⭐⭐⭐⭐ |
| CTA | ⚠️ 기본 버튼 | ✅ 강조된 CTA | ⭐⭐⭐⭐⭐ |
| 비주얼 요소 | ❌ 없음 | ✅ 3D 플로팅 카드 | ⭐⭐⭐⭐⭐ |
| 반응형 | ⚠️ 기본 | ✅ 3단계 최적화 | ⭐⭐⭐⭐ |
| 로딩 상태 | ⚠️ Material | ✅ 커스텀 스피너 | ⭐⭐⭐⭐ |

---

## 테스트 체크리스트

### 시각적 테스트
- [ ] 페이지 로딩 시 애니메이션이 순차적으로 나타나는가?
- [ ] 브랜드 아이콘이 반짝이는가?
- [ ] 플로팅 카드가 부유하는가?
- [ ] 그라데이션이 올바르게 표시되는가?

### 인터랙션 테스트
- [ ] 버튼 호버 시 효과가 나타나는가?
- [ ] 카드 호버 시 3D 효과가 나타나는가?
- [ ] "기능 둘러보기" 버튼이 부드럽게 스크롤하는가?
- [ ] 모든 버튼이 올바른 페이지로 이동하는가?

### 반응형 테스트
- [ ] 태블릿에서 1단 레이아웃으로 변경되는가?
- [ ] 모바일에서 헤더가 세로 배치되는가?
- [ ] 작은 화면에서 버튼이 전체 너비를 차지하는가?
- [ ] 카드 크기가 적절히 조정되는가?

### 성능 테스트
- [ ] 애니메이션이 60 FPS로 동작하는가?
- [ ] 페이지 로드 시간이 적절한가?
- [ ] 메모리 사용량이 정상적인가?

### 접근성 테스트
- [ ] 키보드로 모든 버튼에 접근 가능한가?
- [ ] 포커스 상태가 명확한가?
- [ ] 스크린 리더가 올바르게 읽는가?
- [ ] 색상 대비가 충분한가?

---

## 결론

랜딩 페이지가 현대적이고 매력적인 디자인으로 개선되었습니다:

- **첫인상 개선**: Hero 섹션으로 핵심 가치 전달
- **브랜드 강화**: 그라데이션과 애니메이션으로 브랜드 정체성 강화
- **전환율 증가**: 강조된 CTA로 회원가입 유도
- **사용자 참여**: 인터랙티브 요소로 사용자 흥미 유발
- **일관성**: 워크스페이스와 동일한 디자인 시스템

전체적으로 사용자에게 더 전문적이고 신뢰할 수 있는 첫인상을 제공합니다! 🎉
