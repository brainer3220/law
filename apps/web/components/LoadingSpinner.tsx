/**
 * LoadingSpinner - 로딩 스피너 컴포넌트
 * 
 * 데이터 로딩, 비동기 작업 진행 중 표시.
 */

import { cn } from "@/lib/utils";

export interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

const SIZE_CLASSES = {
  sm: "w-5 h-5",
  md: "w-8 h-8",
  lg: "w-11 h-11",
};

export function LoadingSpinner({
  size = "md",
  label = "로딩 중...",
  className,
}: LoadingSpinnerProps) {
  const sizeClass = SIZE_CLASSES[size];

  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-2", className)}
      role="status"
      aria-live="polite"
      aria-label={label}
    >
      <div className={cn("spinner-ring", sizeClass)} aria-hidden="true" />
      {label && (
        <span className="material-support-text">{label}</span>
      )}
    </div>
  );
}
