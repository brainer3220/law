"use client";

import { memo } from "react";
import type { ReactNode } from "react";

type ErrorType = 'network' | 'config' | 'auth' | 'unknown';

type ErrorOverlayProps = {
  error: string | null;
  errorType?: ErrorType;
  fallbackMessage?: ReactNode;
  onRetry?: (() => void) | null;
  retryLabel?: string;
};

const ERROR_ICONS: Record<ErrorType, string> = {
  network: '🌐',
  config: '⚙️',
  auth: '🔐',
  unknown: '⚠️',
};

const ERROR_TITLES: Record<ErrorType, string> = {
  network: '네트워크 오류',
  config: '설정 오류',
  auth: '인증 오류',
  unknown: '오류 발생',
};

const ERROR_HELP_TEXT: Record<ErrorType, string> = {
  network: '인터넷 연결을 확인하고 다시 시도해주세요.',
  config: '환경 변수 설정을 확인해주세요.',
  auth: 'API 키 권한을 확인해주세요.',
  unknown: '문제가 지속되면 관리자에게 문의하세요.',
};

const ErrorOverlayComponent = ({
  error,
  errorType = 'unknown',
  fallbackMessage,
  onRetry,
  retryLabel,
}: ErrorOverlayProps) => {
  if (!error && !fallbackMessage) {
    return null;
  }

  const content = error ?? fallbackMessage;

  if (!content) {
    return null;
  }

  const isError = Boolean(error);
  const icon = isError ? ERROR_ICONS[errorType] : '⏳';
  const title = isError ? ERROR_TITLES[errorType] : null;
  const helpText = isError ? ERROR_HELP_TEXT[errorType] : null;

  return (
    <div className="pointer-events-none absolute inset-0 z-10 flex h-full w-full flex-col justify-center rounded-[inherit] bg-white/85 p-6 text-center backdrop-blur transition-opacity duration-300 dark:bg-slate-900/90">
      <div className="pointer-events-auto mx-auto w-full max-w-md space-y-4 rounded-xl bg-white px-6 py-6 shadow-lg transition-all duration-300 ease-out animate-in fade-in slide-in-from-bottom-4 dark:bg-slate-800">
        {/* Icon */}
        <div className="text-5xl animate-in zoom-in duration-500" role="img" aria-label={title || '로딩 중'}>
          {icon}
        </div>

        {/* Title */}
        {title && (
          <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {title}
          </h3>
        )}

        {/* Error Message */}
        <div className="text-base text-slate-700 dark:text-slate-300">
          {content}
        </div>

        {/* Help Text */}
        {helpText && (
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {helpText}
          </p>
        )}

        {/* Retry Button */}
        {error && onRetry ? (
          <button
            type="button"
            className="mt-4 inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:bg-slate-800 hover:shadow-md hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 active:scale-95 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
            onClick={onRetry}
          >
            {retryLabel ?? "다시 시도"}
          </button>
        ) : null}
      </div>
    </div>
  );
};

// Memoize to prevent unnecessary re-renders
export const ErrorOverlay = memo(ErrorOverlayComponent);
