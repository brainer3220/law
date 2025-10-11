# Workspace UI Components - Quick Reference

## 버튼 컴포넌트

### Filled Button (프라이머리 버튼)
```tsx
<button type="button" className="material-filled-button">
  <IconComponent className="material-icon" aria-hidden="true" />
  <span>버튼 텍스트</span>
</button>
```

### Filled Tonal Button (보조 버튼)
```tsx
<button type="button" className="material-filled-button material-filled-button--tonal">
  <IconComponent className="material-icon" aria-hidden="true" />
  <span>버튼 텍스트</span>
</button>
```

### Outlined Button (아웃라인 버튼)
```tsx
<button type="button" className="material-outlined-button">
  <IconComponent className="material-icon" aria-hidden="true" />
  <span>버튼 텍스트</span>
</button>
```

### Outlined Button (에러 버전)
```tsx
<button type="button" className="material-outlined-button material-outlined-button--error">
  <IconComponent className="material-icon" aria-hidden="true" />
  <span>삭제</span>
</button>
```

### Small Outlined Button
```tsx
<button type="button" className="material-outlined-button material-outlined-button--small">
  <IconComponent className="material-icon" aria-hidden="true" />
  <span>버튼 텍스트</span>
</button>
```

### Icon Button
```tsx
<button
  type="button"
  aria-label="설명"
  className="material-icon-button"
>
  <IconComponent className="material-icon" aria-hidden="true" />
</button>
```

### Icon Button (Tonal)
```tsx
<button
  type="button"
  aria-label="설명"
  className="material-icon-button material-icon-button--tonal"
>
  <IconComponent className="material-icon" aria-hidden="true" />
</button>
```

---

## 알림 및 상태 컴포넌트

### Error Alert
```tsx
<div className="material-alert material-alert--error">
  에러 메시지
</div>
```

### Error Alert (애니메이션 포함)
```tsx
<div className="material-alert material-alert--error material-project__error-alert">
  에러 메시지가 shake 애니메이션과 함께 나타납니다
</div>
```

---

## Empty State 컴포넌트

### Basic Empty State
```tsx
<div className="material-empty">
  <div className="material-empty__icon-wrapper">
    <IconComponent className="material-empty__icon" />
  </div>
  <h2 className="material-title material-empty__title">제목</h2>
  <p className="material-body material-empty__body">
    설명 텍스트
  </p>
  <button type="button" className="material-filled-button">
    <span>액션 버튼</span>
  </button>
</div>
```

### Empty State (Auth variant with gradient)
```tsx
<div className="material-empty material-empty--auth">
  <div className="material-empty__icon-wrapper">
    <RocketLaunchIcon className="material-empty__icon" />
  </div>
  <h2 className="material-title material-empty__title">로그인이 필요합니다</h2>
  <p className="material-body material-empty__body">
    프로젝트를 보려면 먼저 로그인하세요.
  </p>
  <button type="button" className="material-filled-button">
    <span>로그인하기</span>
  </button>
</div>
```

---

## 타임라인 상태 컴포넌트

### Loading State
```tsx
<div className="project-timeline-loading">
  <div className="project-timeline-spinner">
    <div className="spinner-ring"></div>
    <p className="spinner-text">프로젝트를 불러오는 중...</p>
  </div>
</div>
```

### Error State
```tsx
<div className="project-timeline-error">
  <svg className="error-icon" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
  </svg>
  <p className="error-text">에러 메시지</p>
</div>
```

### Empty State
```tsx
<div className="project-timeline-empty">
  <div className="empty-icon-wrapper">
    <FolderIcon className="empty-icon" />
  </div>
  <h3 className="empty-title">프로젝트가 없습니다</h3>
  <p className="empty-body">
    새 프로젝트를 만들어 시작하세요.
  </p>
</div>
```

---

## 통계 카드

### Stat Tile Component
```tsx
<div className="material-project__stat">
  <span className="material-project__stat-icon">
    <IconComponent className="material-icon" aria-hidden="true" />
  </span>
  <div>
    <span className="material-caption">라벨</span>
    <p className="material-stat-value">값</p>
  </div>
</div>
```

### Stats Grid Container
```tsx
<section className="material-project__stats">
  {/* 여러 개의 stat 카드 */}
  <div className="material-project__stat">...</div>
  <div className="material-project__stat">...</div>
  <div className="material-project__stat">...</div>
</section>
```

---

## 업데이트 카드

### Update Card
```tsx
<article className="material-update-card">
  <header className="material-update-card__header">
    <div className="material-update-card__meta">
      <span className="material-update-card__badge">Update</span>
      <span className="material-caption">2024년 1월 1일 12:00</span>
    </div>
    <span className="material-support-text">작성자 ID</span>
    <button
      type="button"
      className="material-outlined-button material-outlined-button--small material-update-card__delete"
      onClick={handleDelete}
    >
      <TrashIcon className="material-icon" aria-hidden="true" />
      <span>삭제</span>
    </button>
  </header>
  <div className="material-update-card__body">
    업데이트 내용이 여기에 표시됩니다.
  </div>
</article>
```

---

## 사이드바 컴포넌트

### Hint Card
```tsx
<div className="material-workspace__hint">
  <div className="material-workspace__hint-icon">
    <LightBulbIcon className="material-icon" aria-hidden="true" />
  </div>
  <div className="material-workspace__hint-content">
    <h3 className="material-caption material-workspace__hint-title">
      제목
    </h3>
    <p className="material-body material-workspace__hint-body">
      설명 텍스트
    </p>
  </div>
</div>
```

### Quick Tips
```tsx
<div className="material-workspace__quick-tips">
  <h4 className="material-workspace__tips-title">빠른 팁</h4>
  <ul className="material-workspace__tips-list">
    <li>
      <span className="material-workspace__tip-emoji">📋</span>
      <span>팁 내용 1</span>
    </li>
    <li>
      <span className="material-workspace__tip-emoji">✏️</span>
      <span>팁 내용 2</span>
    </li>
    <li>
      <span className="material-workspace__tip-emoji">👥</span>
      <span>팁 내용 3</span>
    </li>
  </ul>
</div>
```

---

## 폼 컴포넌트

### Textarea
```tsx
<textarea
  value={value}
  onChange={handleChange}
  rows={6}
  placeholder="입력 안내 텍스트"
  className="material-textarea"
  disabled={isSubmitting}
/>
```

### Form Footer
```tsx
<div className="material-project__form-footer">
  <span className="material-support-text">
    도움말 텍스트
  </span>
  <button
    type="submit"
    disabled={isSubmitting}
    className="material-filled-button"
  >
    <span>{isSubmitting ? '저장 중…' : '저장하기'}</span>
  </button>
</div>
```

---

## CSS 커스텀 프로퍼티 (Design Tokens)

### Colors
```css
--md-sys-color-primary: #2563eb;
--md-sys-color-on-primary: #ffffff;
--md-sys-color-error: #e11d48;
--md-sys-color-surface: #f8fafc;
--md-sys-color-on-surface: #0f172a;
--md-sys-color-on-surface-variant: #64748b;
--md-sys-color-outline: #cbd5f5;
--md-sys-color-outline-variant: #e2e8f0;
```

### Usage Example
```css
.my-component {
  background: var(--md-sys-color-surface, #f8fafc);
  color: var(--md-sys-color-on-surface, #0f172a);
}
```

---

## 애니메이션 사용 가이드

### Fade In
```css
.my-element {
  animation: fadeIn 0.3s ease-out;
}
```

### Scale In
```css
.my-element {
  animation: scaleIn 0.4s ease-out;
}
```

### Slide In Up
```css
.my-element {
  animation: slideInUp 0.4s ease-out;
}
```

### Staggered Animation
```css
.my-element:nth-child(1) { animation-delay: 0.1s; }
.my-element:nth-child(2) { animation-delay: 0.2s; }
.my-element:nth-child(3) { animation-delay: 0.3s; }
```

---

## 반응형 브레이크포인트

### Desktop (기본)
- 너비: > 1024px
- 2단 그리드 레이아웃

### Tablet (1024px 이하)
```css
@media (max-width: 1024px) {
  /* 1단 그리드 레이아웃 */
}
```

### Mobile (768px 이하)
```css
@media (max-width: 768px) {
  /* 축소된 패딩, 세로 레이아웃 */
}
```

### Small Mobile (480px 이하)
```css
@media (max-width: 480px) {
  /* 최소 패딩, 전체 너비 버튼 */
}
```

---

## 접근성 체크리스트

- [ ] 모든 인터랙티브 요소에 적절한 ARIA 레이블
- [ ] 장식 아이콘에 `aria-hidden="true"` 추가
- [ ] 키보드로 모든 기능 접근 가능
- [ ] 포커스 상태가 명확하게 표시
- [ ] 색상 대비가 WCAG AA 기준 충족
- [ ] 에러 메시지가 스크린 리더에게 전달

---

## 성능 최적화 팁

1. **CSS 애니메이션 사용**: `transform`과 `opacity`만 애니메이션
2. **적절한 지속 시간**: 0.2s~0.4s
3. **하드웨어 가속**: `transform: translateZ(0)` 또는 `will-change`
4. **애니메이션 지연**: `animation-fill-mode: both`로 깜빡임 방지
5. **불필요한 리페인트 방지**: `width`, `height`, `left`, `top` 애니메이션 지양
