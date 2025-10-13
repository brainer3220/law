"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  ChartBarIcon,
  CheckCircleIcon,
  MicrophoneIcon,
  PauseIcon,
  PlayIcon,
} from "@heroicons/react/24/outline";
import clsx from "clsx";
import { useAuth } from "@/lib/auth/AuthContext";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useRealtimeTranscriber } from "@/hooks/useRealtimeTranscriber";
import type { LiveTranscriptSegment } from "@/types/audio";

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const seconds = totalSeconds % 60;
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const hours = Math.floor(totalSeconds / 3600);
  if (hours > 0) {
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds
      .toString()
      .padStart(2, "0")}`;
  }
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

function formatTimestamp(seconds: number | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) {
    return "00:00";
  }
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(totalSeconds / 60);
  const secs = totalSeconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function assignLabels(segments: LiveTranscriptSegment[]): Record<string, string> {
  const labels: Record<string, string> = {};
  let index = 1;
  for (const segment of segments) {
    if (!labels[segment.speaker]) {
      labels[segment.speaker] = `화자 ${index}`;
      index += 1;
    }
  }
  return labels;
}

export default function LiveTranscribePage() {
  const { user, loading } = useAuth();
  const [state, controls] = useRealtimeTranscriber("/api/transcribe/live");
  const [speakerLabels, setSpeakerLabels] = useState<Record<string, string>>({});

  useEffect(() => {
    if (state.segments.length > 0) {
      setSpeakerLabels((prev) => {
        const defaults = assignLabels(state.segments);
        const next = { ...defaults };
        for (const [speaker, label] of Object.entries(prev)) {
          next[speaker] = label;
        }
        return next;
      });
    }
  }, [state.segments]);

  const diarizedSegments = useMemo(
    () =>
      state.segments.map((segment) => ({
        ...segment,
        label: speakerLabels[segment.speaker] ?? segment.speaker,
      })),
    [state.segments, speakerLabels],
  );

  const isRecording = state.status === "recording";
  const statusBadge = (() => {
    switch (state.status) {
      case "connecting":
        return (
          <span className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500"></span>
            </span>
            연결 중
          </span>
        );
      case "recording":
        return (
          <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            실시간 전사 중
          </span>
        );
      case "stopping":
        return (
          <span className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
            마무리 중
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-2 rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700 dark:bg-rose-900/40 dark:text-rose-300">
            오류 발생
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-2 rounded-full bg-slate-200 px-3 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
            대기 중
          </span>
        );
    }
  })();

  if (loading) {
    return (
      <div className="material-screen">
        <LoadingSpinner label="실시간 음성 전사 도구를 불러오는 중입니다…" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="material-screen">
        <MicrophoneIcon className="h-10 w-10 text-blue-500" aria-hidden="true" />
        <p className="material-body">실시간 음성 전사를 사용하려면 로그인하세요.</p>
        <button
          type="button"
          onClick={() => {
            window.location.href = "/auth/login";
          }}
          className="material-filled-button"
        >
          로그인
        </button>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 dark:bg-slate-950">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="rounded-3xl bg-white p-8 shadow-sm dark:bg-slate-900">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4 text-slate-900 dark:text-slate-100">
              <div className="rounded-full bg-violet-100 p-3 dark:bg-violet-900/40">
                <ChartBarIcon className="h-6 w-6 text-violet-600 dark:text-violet-300" aria-hidden="true" />
              </div>
              <div>
                <h1 className="text-2xl font-semibold">실시간 음성 전사</h1>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  마이크 입력을 즉시 전사하며, 화자 분리 결과를 실시간으로 확인합니다.
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-3">
              {statusBadge}
              <div className="text-xs font-medium text-slate-500 dark:text-slate-400">
                진행 시간 <span className="font-semibold text-slate-800 dark:text-slate-200">{formatElapsed(state.elapsedMs)}</span>
              </div>
            </div>
          </div>
        </header>

        <section className="flex flex-col gap-6 rounded-3xl bg-white p-8 shadow-sm dark:bg-slate-900">
          <div className="flex flex-col gap-6 lg:flex-row">
            <div className="flex-1 space-y-4">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                전사 제어
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                시작 버튼을 누르면 브라우저에서 마이크 권한을 요청합니다. 전사 중에는 오디오가 서버로 암호화된 WebSocket을 통해 전송됩니다.
              </p>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    if (isRecording) {
                      void controls.stop();
                    } else {
                      void controls.start();
                    }
                  }}
                  className={clsx(
                    "inline-flex items-center gap-2 rounded-full px-6 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500",
                    isRecording
                      ? "bg-rose-500 text-white shadow hover:bg-rose-400 dark:bg-rose-400 dark:hover:bg-rose-300"
                      : "bg-blue-600 text-white shadow hover:bg-blue-500 dark:bg-blue-500 dark:hover:bg-blue-400",
                  )}
                >
                  {isRecording ? (
                    <>
                      <PauseIcon className="h-4 w-4" aria-hidden="true" />
                      전사 중지
                    </>
                  ) : (
                    <>
                      <PlayIcon className="h-4 w-4" aria-hidden="true" />
                      전사 시작
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => controls.reset()}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-5 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500"
                >
                  <ArrowPathIcon className="h-4 w-4" aria-hidden="true" />
                  초기화
                </button>
              </div>
              <div className="flex items-center gap-3 rounded-2xl bg-slate-50 px-5 py-4 dark:bg-slate-800/60">
                <label className="flex items-center gap-3 text-sm font-medium text-slate-700 dark:text-slate-200">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-600"
                    checked={state.diarization}
                    onChange={(event) => controls.setDiarization(event.target.checked)}
                    disabled={isRecording}
                  />
                  <span>화자 분리 사용</span>
                </label>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  전사 시작 시 적용되며, 진행 중에는 변경할 수 없습니다.
                </span>
              </div>
              {state.error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-sm dark:border-rose-500/60 dark:bg-rose-900/20 dark:text-rose-200">
                  {state.error}
                </div>
              )}
            </div>

            <div className="flex w-full flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-900/50 lg:w-72">
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                전사 상태
              </h3>
              <dl className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                <div className="flex justify-between">
                  <dt>상태</dt>
                  <dd>{state.status === "idle" ? "대기 중" : state.status === "recording" ? "전사 중" : state.status === "connecting" ? "연결 중" : state.status === "stopping" ? "마무리 중" : "오류"}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>화자 수</dt>
                  <dd>{Object.keys(speakerLabels).length}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>수신 세그먼트</dt>
                  <dd>{state.segments.length}</dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-8 shadow-sm dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                화자별 전사 결과
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                실시간으로 업데이트되는 전사 내용을 확인하세요.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <CheckCircleIcon className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              <span>완료된 발화는 녹색 배지로 표시됩니다.</span>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {diarizedSegments.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-6 py-12 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900/50 dark:text-slate-400">
                아직 수신된 전사 내용이 없습니다. 전사를 시작하거나 발화를 계속하세요.
              </div>
            ) : (
              diarizedSegments.map((segment) => (
                <article
                  key={segment.id}
                  className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 shadow-sm transition hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900/60 dark:hover:border-slate-600"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="inline-flex items-center gap-2 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-200">
                      {segment.label}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                      <span>
                        {formatTimestamp(segment.start)} - {formatTimestamp(segment.end)}
                      </span>
                      <span
                        className={clsx(
                          "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold",
                          segment.isFinal
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                            : "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
                        )}
                      >
                        {segment.isFinal ? "Final" : "Draft"}
                      </span>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-800 dark:text-slate-100">
                    {segment.text}
                  </p>
                </article>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
