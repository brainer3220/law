import { randomUUID } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import type { SpeakerSegment, TranscriptionPayload } from "@/types/audio";

export const runtime = "nodejs";

const OPENAI_API_URL = "https://api.openai.com/v1/responses";
const DEFAULT_MODEL = process.env.OPENAI_TRANSCRIBE_MODEL ?? "gpt-4o-mini-transcribe";

function badRequest(error: string, details?: unknown, status = 400) {
  return NextResponse.json(
    { ok: false, error, details: details ?? null },
    { status },
  );
}

function guessFormat(file: File, filename?: string | null): string {
  const mime = file.type.toLowerCase();
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

async function transcribeWithOpenAI(
  file: File,
  buffer: Buffer,
  diarize: boolean,
): Promise<TranscriptionPayload> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.");
  }

  const format = guessFormat(file, file.name);
  const base64 = buffer.toString("base64");

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
              ? "Transcribe the audio. Return JSON with segments and speaker labels."
              : "Transcribe the audio and return JSON with segments.",
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

  const json: any = await response.json();

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

function mockTranscription(fileName: string, diarize: boolean): TranscriptionPayload {
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
      diarization: diarize,
      sample: true,
      filename: fileName,
    },
    generatedAt: now,
  };
}

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const audio = formData.get("audio");

    if (!audio || !(audio instanceof File)) {
      return badRequest("유효한 오디오 파일이 필요합니다.");
    }

    const diarize = (formData.get("diarize") ?? "").toString().toLowerCase() === "true";

    const arrayBuffer = await audio.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    const hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
    const transcription = hasOpenAIKey
      ? await transcribeWithOpenAI(audio, buffer, diarize)
      : mockTranscription(audio.name, diarize);

    return NextResponse.json(
      {
        ok: true,
        data: transcription,
      },
      { status: 200 },
    );
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "전사 처리 중 알 수 없는 오류가 발생했습니다.";

    return badRequest(message, undefined, 500);
  }
}
