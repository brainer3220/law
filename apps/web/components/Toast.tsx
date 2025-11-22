"use client";

import { useEffect } from "react";

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
    message: string;
    type: ToastType;
    duration?: number;
    onClose: () => void;
}

const TOAST_ICONS: Record<ToastType, string> = {
    success: '✅',
    error: '❌',
    info: 'ℹ️',
    warning: '⚠️',
};

const TOAST_COLORS: Record<ToastType, string> = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-950 dark:border-emerald-800 dark:text-emerald-200',
    error: 'bg-red-50 border-red-200 text-red-800 dark:bg-red-950 dark:border-red-800 dark:text-red-200',
    info: 'bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-200',
    warning: 'bg-amber-50 border-amber-200 text-amber-800 dark:bg-amber-950 dark:border-amber-800 dark:text-amber-200',
};

export function Toast({ message, type, duration = 3000, onClose }: ToastProps) {
    useEffect(() => {
        const timer = setTimeout(onClose, duration);
        return () => clearTimeout(timer);
    }, [duration, onClose]);

    return (
        <div
            role="alert"
            aria-live="assertive"
            className={`
        fixed bottom-4 right-4 z-50
        flex items-center gap-3 rounded-lg border px-4 py-3 shadow-lg
        animate-in slide-in-from-bottom-5 fade-in duration-300
        ${TOAST_COLORS[type]}
      `}
        >
            <span className="text-xl" role="img" aria-label={type}>
                {TOAST_ICONS[type]}
            </span>
            <p className="text-sm font-medium">{message}</p>
            <button
                onClick={onClose}
                className="ml-2 text-current opacity-70 hover:opacity-100 transition-opacity duration-150"
                aria-label="닫기"
            >
                ×
            </button>
        </div>
    );
}

// Toast Container for managing multiple toasts
interface ToastContainerProps {
    toasts: Array<{ id: string; message: string; type: ToastType }>;
    onRemove: (id: string) => void;
}

export function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    onClose={() => onRemove(toast.id)}
                />
            ))}
        </div>
    );
}
