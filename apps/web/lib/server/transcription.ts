import type { SpeakerSegment, TranscriptionPayload } from "@/types/audio";

type JsonRecord = Record<string, unknown>;

function generateId(): string {
  const globalCrypto = (globalThis as typeof globalThis & { crypto?: Crypto }).crypto;
  if (globalCrypto && typeof globalCrypto.randomUUID === "function") {
    return globalCrypto.randomUUID();
  }
  return `${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}`;
}

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : null;
}

function asArray(value: unknown): unknown[] | null {
  return Array.isArray(value) ? value : null;
}

const OPENAI_API_URL = "https://api.openai.com/v1/audio/transcriptions";
const DEFAULT_MODEL = process.env.OPENAI_TRANSCRIBE_MODEL ?? "gpt-4o-mini-transcribe";

export function guessAudioFormat(file: File, filename?: string | null): string {
  const mime = (file.type || "").toLowerCase();
  if (mime) {
    if (mime.includes("wav")) return "wav";
    if (mime.includes("mpeg") || mime.includes("mp3")) return "mp3";
    if (mime.includes("aac")) return "aac";
    if (mime.includes("m4a")) return "m4a";
    if (mime.includes("ogg")) return "ogg";
    if (mime.includes("flac")) return "flac";
    if (mime.includes("webm")) return "webm";
  }
  const ext = filename?.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "wav":
    case "wave":
      return "wav";
    case "m4a":
      return "m4a";
    case "aac":
      return "aac";
    case "ogg":
      return "ogg";
    case "flac":
      return "flac";
    case "webm":
      return "webm";
    case "mp3":
    default:
      return "mp3";
  }
}

export async function transcribeWithOpenAI(
  file: File,
  bytes: Uint8Array,
  diarize: boolean,
): Promise<TranscriptionPayload> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.");
  }

  const model = diarize
    ? process.env.OPENAI_DIARIZE_MODEL ?? "gpt-4o-transcribe-diarize"
    : DEFAULT_MODEL;
  const body = new FormData();
  // Supply the bytes actually read by the route, retaining the recording name.
  body.append("file", new Blob([new Uint8Array(bytes)], { type: file.type || "application/octet-stream" }), file.name);
  body.append("model", model);
  body.append("response_format", diarize ? "diarized_json" : model === "whisper-1" ? "verbose_json" : "json");
  if (diarize) body.append("chunking_strategy", "auto");

  const response = await fetch(OPENAI_API_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}` },
    body,
  });
  const result = asRecord(await response.json().catch(() => null));
  if (!response.ok) {
    const message = asRecord(result?.error)?.message;
    throw new Error(typeof message === "string" ? message : `OpenAI 응답이 실패했습니다. (HTTP ${response.status})`);
  }
  if (!result) throw new Error("전사 JSON을 해석하지 못했습니다.");

  const segments: SpeakerSegment[] = (asArray(result.segments) ?? []).flatMap((value) => {
    const segment = asRecord(value);
    if (typeof segment?.text !== "string" || !segment.text.trim()) return [];
    const start = typeof segment.start === "number" && Number.isFinite(segment.start) ? Math.max(0, segment.start) : 0;
    const end = typeof segment.end === "number" && Number.isFinite(segment.end) ? Math.max(start, segment.end) : start;
    return [{
      speaker: typeof segment.speaker === "string" && segment.speaker.trim() ? segment.speaker.trim() : "speaker",
      start,
      end,
      text: segment.text,
    }];
  });
  const duration = typeof result.duration === "number" && Number.isFinite(result.duration) ? Math.max(0, result.duration) : undefined;
  // Ordinary transcription JSON provides text, not speaker/timing annotations.
  // Keep that distinction explicit instead of inventing timestamps or speakers.
  if (!segments.length && typeof result.text === "string" && result.text.trim()) {
    if (diarize) throw new Error("화자 분리 응답에 화자 구간이 포함되어 있지 않습니다.");
    segments.push({ speaker: "speaker", start: 0, end: duration ?? 0, text: result.text });
  }
  if (!segments.length) throw new Error("OpenAI 응답에서 전사 결과를 찾을 수 없습니다.");

  return {
    id: typeof result.id === "string" ? result.id : generateId(),
    language: typeof result.language === "string" ? result.language : undefined,
    duration,
    segments,
    metadata: {
      provider: "openai",
      model,
      diarization: diarize,
      timestamps_available: Boolean(asArray(result.segments)?.length),
      usage: result.usage ?? null,
    },
    generatedAt: new Date().toISOString(),
  };
}

export function createMockTranscription(
  fileName: string,
  diarize: boolean,
): TranscriptionPayload {
  const now = new Date().toISOString();
  const baseSegments: SpeakerSegment[] = [
    {
      speaker: diarize ? "speaker_1" : "speaker",
      start: 0,
      end: 6.2,
      text: "안녕하세요. 계약서 주요 조항을 같이 검토해보시죠.",
      confidence: 0.92,
    },
    {
      speaker: diarize ? "speaker_2" : "speaker",
      start: 6.2,
      end: 12.8,
      text: "네, 특히 손해배상 범위와 해지 조건이 궁금합니다.",
      confidence: 0.89,
    },
    {
      speaker: diarize ? "speaker_1" : "speaker",
      start: 12.8,
      end: 20.5,
      text: "손해배상은 민법 390조를 준용해 과실 범위 내에서 제한됩니다.",
      confidence: 0.93,
    },
  ];

  return {
    id: generateId(),
    language: "ko",
    duration: 20.5,
    summary: diarize
      ? "두 명의 화자가 계약서 손해배상과 해지 조건을 논의했습니다."
      : "계약서 주요 조항에 대한 간단한 전사입니다.",
    segments: baseSegments,
    metadata: {
      provider: "mock",
      diarization: diarize,
      sample: true,
      filename: fileName,
    },
    generatedAt: now,
  };
}
