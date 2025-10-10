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
  sm: "h-4 w-4 border-2",
  md: "h-8 w-8 border-3",
  lg: "h-12 w-12 border-4",
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
      <div
        className={cn(
          "animate-spin rounded-full border-blue-600 border-t-transparent dark:border-blue-400",
          sizeClass
        )}
        aria-hidden="true"
      />
      {label && (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {label}
        </span>
      )}
    </div>
  );
}
