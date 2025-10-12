import { randomUUID } from "node:crypto";
import type { SpeakerSegment, TranscriptionPayload } from "@/types/audio";

const OPENAI_API_URL = "https://api.openai.com/v1/responses";
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

function bytesToBase64(bytes: Uint8Array): string {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(bytes).toString("base64");
  }

  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const subArray = bytes.subarray(i, Math.min(bytes.length, i + chunkSize));
    binary += String.fromCharCode(...subArray);
  }
  return btoa(binary);
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

  const format = guessAudioFormat(file, file.name);
  const base64 = bytesToBase64(bytes);

  const schema = {
    name: "transcription_payload",
    schema: {
      type: "object",
      additionalProperties: false,
      properties: {
        language: { type: "string", description: "ISO 639-1 or BCP-47 language tag" },
        duration: { type: "number", description: "Audio duration in seconds" },
        summary: { type: "string", description: "Short summary of the conversation" },
        segments: {
          type: "array",
          items: {
            type: "object",
            additionalProperties: false,
            required: ["speaker", "start", "end", "text"],
            properties: {
              speaker: { type: "string", description: "Speaker identifier" },
              start: { type: "number", description: "Segment start time in seconds" },
              end: { type: "number", description: "Segment end time in seconds" },
              text: { type: "string", description: "Transcribed content" },
              confidence: {
                type: "number",
                description: "Model confidence between 0 and 1",
              },
            },
          },
        },
      },
      required: ["segments"],
    },
    strict: true,
  };

  const body = {
    model: DEFAULT_MODEL,
    modalities: ["text"],
    audio: diarize ? { diarization: { enable: true } } : undefined,
    input: [
      {
        role: "user",
        content: [
          {
            type: "input_text",
            text: diarize
              ? "Transcribe the audio and produce a diarized JSON structure with speaker segments."
              : "Transcribe the audio and produce JSON segments.",
          },
          {
            type: "input_audio",
            audio: {
              data: base64,
              format,
            },
          },
        ],
      },
    ],
    response_format: {
      type: "json_schema",
      json_schema: schema,
    },
  };

  const response = await fetch(OPENAI_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(body),
  });

  const json: any = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMessage =
      typeof json?.error?.message === "string"
        ? json.error.message
        : `OpenAI 응답이 실패했습니다. (HTTP ${response.status})`;
    throw new Error(errorMessage);
  }

  const raw =
    (json?.output_text as string | undefined) ??
    json?.output?.[0]?.content?.[0]?.text ??
    null;

  if (!raw) {
    throw new Error("OpenAI 응답에서 전사 결과를 찾을 수 없습니다.");
  }

  let parsed: any;
  try {
    parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch (err) {
    throw new Error("전사 JSON을 해석하지 못했습니다.");
  }

  const segments: SpeakerSegment[] = Array.isArray(parsed.segments)
    ? parsed.segments.map((segment: any, index: number) => ({
        speaker: typeof segment.speaker === "string" && segment.speaker.trim()
          ? segment.speaker.trim()
          : `speaker_${index + 1}`,
        start: typeof segment.start === "number" ? segment.start : 0,
        end: typeof segment.end === "number" ? segment.end : 0,
        text: typeof segment.text === "string" ? segment.text : "",
        confidence:
          typeof segment.confidence === "number" && Number.isFinite(segment.confidence)
            ? Math.min(Math.max(segment.confidence, 0), 1)
            : undefined,
      }))
    : [];

  if (segments.length === 0) {
    throw new Error("전사 결과에 화자 구간이 포함되어 있지 않습니다.");
  }

  return {
    id: (json?.id as string | undefined) ?? randomUUID(),
    language: typeof parsed.language === "string" ? parsed.language : undefined,
    duration: typeof parsed.duration === "number" ? parsed.duration : undefined,
    summary: typeof parsed.summary === "string" ? parsed.summary : undefined,
    segments,
    metadata: {
      provider: "openai",
      model: DEFAULT_MODEL,
      diarization: diarize,
      usage: json?.usage ?? null,
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
    id: randomUUID(),
    language: "ko",
    duration: 20.5,
    summary: diarize
      ? "두 명의 화자가 계약서 손해배상과 해지 조건을 논의했습니다."
      : "계약서 주요 조항에 대한 간단한 전사입니다.",
    segments: baseSegments,
    metadata: {
      provider: "mock",
      diarization,
      sample: true,
      filename: fileName,
    },
    generatedAt: now,
  };
}
