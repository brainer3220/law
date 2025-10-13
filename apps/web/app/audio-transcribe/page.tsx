"use client";

import { type ChangeEvent, type FormEvent, useCallback, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  DocumentDuplicateIcon,
  MicrophoneIcon,
  SpeakerWaveIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import clsx from "clsx";
import Link from "next/link";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { useAuth } from "@/lib/auth/AuthContext";
import type { SpeakerSegment, TranscriptionPayload } from "@/types/audio";

type ApiSuccess = {
  ok: true;
  data: TranscriptionPayload;
};

type ApiError = {
  ok: false;
  error: string;
  details?: string;
};

const ACCEPTED_TYPES = [
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/x-wav",
  "audio/flac",
  "audio/webm",
  "audio/ogg",
  "audio/m4a",
  "audio/aac",
];

const MAX_SIZE_MB = 25;

function formatTimestamp(seconds: number | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) {
    return "00:00";
  }
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  if (hrs > 0) {
    return [hrs, mins.toString().padStart(2, "0"), secs.toString().padStart(2, "0")].join(":");
  }
  return [mins.toString().padStart(2, "0"), secs.toString().padStart(2, "0")].join(":");
}

function buildDefaultSpeakerLabels(segments: SpeakerSegment[]): Record<string, string> {
  const mapping: Record<string, string> = {};
  let index = 1;
  for (const segment of segments) {
    if (!mapping[segment.speaker]) {
      mapping[segment.speaker] = `화자 ${index}`;
      index += 1;
    }
  }
  return mapping;
}

function copyToClipboard(text: string): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    return navigator.clipboard.writeText(text);
  }
  return Promise.reject(new Error("클립보드에 접근할 수 없습니다."));
}

export default function AudioTranscribePage() {
  const { user, loading } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [diarizationEnabled, setDiarizationEnabled] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptionPayload | null>(null);
  const [speakerLabels, setSpeakerLabels] = useState<Record<string, string>>({});
  const [copySuccess, setCopySuccess] = useState(false);

  const handleFileChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    if (!nextFile) {
      setFile(null);
      return;
    }
    if (!ACCEPTED_TYPES.includes(nextFile.type)) {
      setError("지원되지 않는 오디오 형식입니다. MP3, WAV, OGG 등 표준 코덱을 업로드하세요.");
      setFile(null);
      return;
    }
    if (nextFile.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`파일 용량이 ${MAX_SIZE_MB}MB를 초과했습니다.`);
      setFile(null);
      return;
    }
    setError(null);
    setFile(nextFile);
  }, []);

  const handleReset = useCallback(() => {
    setFile(null);
    setTranscript(null);
    setSpeakerLabels({});
    setCopySuccess(false);
    setError(null);
  }, []);

  const handleSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!file) {
        setError("오디오 파일을 선택해주세요.");
        return;
      }

      const formData = new FormData();
      formData.append("audio", file);
      formData.append("filename", file.name);
      formData.append("mimetype", file.type);
      formData.append("diarize", diarizationEnabled ? "true" : "false");

      setIsSubmitting(true);
      setError(null);
      setCopySuccess(false);

      try {
        const response = await fetch("/api/transcribe", {
          method: "POST",
          body: formData,
        });

        const contentType = response.headers.get("content-type") ?? "";
        const payload = contentType.includes("application/json")
          ? ((await response.json()) as ApiSuccess | ApiError)
          : ({ ok: false, error: "서버 응답을 해석할 수 없습니다." } satisfies ApiError);

        if (!response.ok || !payload.ok) {
          throw new Error(
            !payload.ok ? payload.error : `전사 요청이 실패했습니다. (HTTP ${response.status})`,
          );
        }

        setTranscript(payload.data);
        setSpeakerLabels(buildDefaultSpeakerLabels(payload.data.segments));
      } catch (submitError) {
        const message =
          submitError instanceof Error ? submitError.message : "전사 요청 중 오류가 발생했습니다.";
        setError(message);
      } finally {
        setIsSubmitting(false);
      }
    },
    [diarizationEnabled, file],
  );

  const handleSpeakerRename = useCallback(
    (speaker: string, label: string) => {
      setSpeakerLabels((prev) => ({
        ...prev,
        [speaker]: label.trim() || prev[speaker] || speaker,
      }));
    },
    [],
  );

  const combinedTranscriptText = useMemo(() => {
    if (!transcript) {
      return "";
    }
    return transcript.segments
      .map((segment) => {
        const label = speakerLabels[segment.speaker] ?? segment.speaker;
        return `[${label}] ${segment.text}`;
      })
      .join("\n");
  }, [speakerLabels, transcript]);

  const handleCopy = useCallback(async () => {
    if (!combinedTranscriptText) {
      return;
    }
    try {
      await copyToClipboard(combinedTranscriptText);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 1800);
    } catch (copyError) {
      const message =
        copyError instanceof Error ? copyError.message : "클립보드로 복사하지 못했습니다.";
      setError(message);
    }
  }, [combinedTranscriptText]);

  if (loading) {
    return (
      <div className="material-screen">
        <LoadingSpinner label="음성 전사 화면을 준비하는 중입니다…" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="material-screen">
        <MicrophoneIcon className="h-10 w-10 text-blue-500" aria-hidden="true" />
        <p className="material-body">음성 전사 도구를 사용하려면 로그인해주세요.</p>
        <button
          type="button"
          onClick={() => {
            window.location.href = "/auth/login";
          }}
          className="material-filled-button"
        >
          지금 로그인
        </button>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 dark:bg-slate-950">
      <div className="mx-auto max-w-5xl space-y-8">
        <header className="rounded-3xl bg-white p-8 shadow-sm dark:bg-slate-900">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-3 text-slate-900 dark:text-slate-100">
                <div className="rounded-full bg-blue-100 p-3 dark:bg-blue-900/40">
                  <MicrophoneIcon className="h-6 w-6 text-blue-600 dark:text-blue-300" aria-hidden="true" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold">음성 전사 & 화자 분리</h1>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    오디오를 업로드하면 자동으로 전사하고, 화자별 대화를 분리해 타임라인으로 보여드립니다.
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-3 rounded-full border border-slate-200 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={diarizationEnabled}
                  onChange={(event) => setDiarizationEnabled(event.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-600"
                />
                <span>화자 분리 활성화</span>
              </label>
              {transcript && (
                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:text-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-500"
                >
                  <ArrowPathIcon className="h-4 w-4" aria-hidden="true" />
                  초기화
                </button>
              )}
              <Link
                href="/audio-transcribe/live"
                className="inline-flex items-center gap-2 rounded-full border border-blue-200 px-4 py-2 text-sm font-semibold text-blue-600 transition hover:border-blue-300 hover:text-blue-700 dark:border-blue-500/40 dark:text-blue-300 dark:hover:text-blue-200"
              >
                실시간 전사
              </Link>
            </div>
          </div>
        </header>

        <section className="space-y-6">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-6 rounded-3xl bg-white p-8 shadow-sm dark:bg-slate-900"
          >
            <div
              className={clsx(
                "flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-8 text-center transition",
                error ? "border-rose-400 bg-rose-50/60 dark:border-rose-500/80 dark:bg-rose-900/20" : "border-slate-200 bg-slate-50/80 dark:border-slate-700 dark:bg-slate-900/40",
              )}
            >
              <CloudArrowUpIcon
                className={clsx("h-12 w-12", error ? "text-rose-500 dark:text-rose-300" : "text-blue-600 dark:text-blue-300")}
                aria-hidden="true"
              />
              <div>
                <p className="text-base font-medium text-slate-800 dark:text-slate-100">
                  오디오 파일을 업로드하거나 끌어다 놓으세요
                </p>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  지원 형식: MP3, WAV, OGG, M4A • 최대 {MAX_SIZE_MB}MB
                </p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center justify-center rounded-full bg-blue-600 px-5 py-2 text-sm font-semibold text-white shadow transition hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 dark:bg-blue-500 dark:hover:bg-blue-400">
                <span>파일 선택</span>
                <input
                  type="file"
                  accept={ACCEPTED_TYPES.join(",")}
                  onChange={handleFileChange}
                  className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
                />
              </label>

              {file && (
                <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm text-slate-700 shadow-sm dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-200">
                  <div className="flex items-center gap-3">
                    <SpeakerWaveIcon className="h-5 w-5 text-blue-500" aria-hidden="true" />
                    <div className="flex-1">
                      <p className="font-medium">{file.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {(file.size / 1024 / 1024).toFixed(2)}MB · {file.type || "알 수 없는 형식"}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setFile(null)}
                      className="rounded-full p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700"
                    >
                      <XMarkIcon className="h-5 w-5" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="rounded-xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-700 shadow-sm dark:border-rose-500/80 dark:bg-rose-900/30 dark:text-rose-200">
                {error}
              </div>
            )}

            <div className="flex items-center justify-between">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                전사 과정은 일반적으로 오디오 길이에 따라 수 초에서 수 분 정도 소요됩니다.
              </p>
              <button
                type="submit"
                disabled={!file || isSubmitting}
                className={clsx(
                  "inline-flex items-center gap-2 rounded-full px-6 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500",
                  !file || isSubmitting
                    ? "cursor-not-allowed bg-slate-300 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
                    : "bg-blue-600 text-white shadow hover:bg-blue-500 dark:bg-blue-500 dark:hover:bg-blue-400",
                )}
              >
                {isSubmitting ? (
                  <>
                    <LoadingSpinner size="sm" label="" className="!flex !flex-row !items-center !gap-0" />
                    처리 중...
                  </>
                ) : (
                  <>
                    <MicrophoneIcon className="h-4 w-4" aria-hidden="true" />
                    전사 시작
                  </>
                )}
              </button>
            </div>
          </form>
        </section>

        {transcript && (
          <section className="space-y-6">
            <div className="rounded-3xl bg-white p-8 shadow-sm dark:bg-slate-900">
              <div className="flex flex-col gap-3 border-b border-slate-200 pb-6 dark:border-slate-800">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <CheckCircleIcon className="h-6 w-6 text-emerald-500" aria-hidden="true" />
                    <div>
                      <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                        전사 결과
                      </h2>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {transcript.generatedAt
                          ? new Date(transcript.generatedAt).toLocaleString("ko-KR")
                          : "방금 생성됨"}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={handleCopy}
                    className="inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:text-slate-900 dark:border-slate-700 dark:text-slate-200 dark:hover:border-slate-500"
                  >
                    {copySuccess ? (
                      <>
                        <CheckCircleIcon className="h-4 w-4 text-emerald-500" aria-hidden="true" />
                        복사 완료
                      </>
                    ) : (
                      <>
                        <DocumentDuplicateIcon className="h-4 w-4" aria-hidden="true" />
                        화자별 텍스트 복사
                      </>
                    )}
                  </button>
                </div>

                <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
                    <dt className="text-slate-500 dark:text-slate-400">언어</dt>
                    <dd className="text-base font-medium text-slate-800 dark:text-slate-100">
                      {transcript.language ?? "감지된 언어"}
                    </dd>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
                    <dt className="text-slate-500 dark:text-slate-400">오디오 길이</dt>
                    <dd className="text-base font-medium text-slate-800 dark:text-slate-100">
                      {transcript.duration != null ? formatTimestamp(transcript.duration) : "측정 중"}
                    </dd>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60">
                    <dt className="text-slate-500 dark:text-slate-400">화자 수</dt>
                    <dd className="text-base font-medium text-slate-800 dark:text-slate-100">
                      {Object.keys(speakerLabels).length}
                    </dd>
                  </div>
                </dl>
              </div>

              {transcript.summary && (
                <div className="mt-6 rounded-2xl bg-blue-50 px-5 py-4 text-sm text-blue-900 shadow-sm dark:bg-blue-900/30 dark:text-blue-100">
                  <p className="font-medium">요약</p>
                  <p className="mt-1 leading-relaxed">{transcript.summary}</p>
                </div>
              )}

              <div className="mt-8 space-y-6">
                {Object.entries(
                  transcript.segments.reduce<Record<string, SpeakerSegment[]>>((acc, segment) => {
                    if (!acc[segment.speaker]) {
                      acc[segment.speaker] = [];
                    }
                    acc[segment.speaker].push(segment);
                    return acc;
                  }, {}),
                ).map(([speaker, segments]) => (
                  <article key={speaker} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900/70">
                    <div className="flex flex-col gap-2 border-b border-slate-100 pb-4 dark:border-slate-800">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <SpeakerWaveIcon className="h-5 w-5 text-blue-500" aria-hidden="true" />
                          <input
                            type="text"
                            value={speakerLabels[speaker] ?? speaker}
                            onChange={(event) => handleSpeakerRename(speaker, event.target.value)}
                            className="rounded-full border border-transparent bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-900 transition focus:border-blue-300 focus:outline-none dark:bg-blue-900/40 dark:text-blue-100"
                          />
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                          {segments.length}개의 발화
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 space-y-4">
                      {segments.map((segment, index) => (
                        <div
                          key={`${segment.speaker}-${segment.start}-${index}`}
                          className="rounded-2xl bg-slate-50 px-4 py-3 text-sm leading-relaxed shadow-sm transition hover:bg-slate-100 dark:bg-slate-800/80 dark:hover:bg-slate-800"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400">
                            <span>
                              {formatTimestamp(segment.start)} - {formatTimestamp(segment.end)}
                            </span>
                            {segment.confidence != null && (
                              <span>신뢰도 {(segment.confidence * 100).toFixed(0)}%</span>
                            )}
                          </div>
                          <p className="mt-2 text-slate-800 dark:text-slate-100">{segment.text}</p>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
