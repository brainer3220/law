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

  const json = (await response.json().catch(() => null)) as unknown;
  const jsonRecord = asRecord(json);

  if (!response.ok) {
    const errorRecord =
      jsonRecord && typeof jsonRecord.error === "object" && jsonRecord.error !== null
        ? asRecord(jsonRecord.error)
        : null;
    const messageValue = errorRecord?.message;
    const errorMessage =
      typeof messageValue === "string"
        ? messageValue
        : `OpenAI 응답이 실패했습니다. (HTTP ${response.status})`;
    throw new Error(errorMessage);
  }

  let raw: unknown = null;
  if (jsonRecord) {
    if (typeof jsonRecord["output_text"] === "string") {
      raw = jsonRecord["output_text"];
    } else if (Array.isArray(jsonRecord["output"])) {
      const [firstOutput] = jsonRecord["output"] as unknown[];
      const firstOutputRecord = asRecord(firstOutput);
      const firstContent = firstOutputRecord?.["content"];
      if (Array.isArray(firstContent)) {
        const [firstItem] = firstContent as unknown[];
        const firstItemRecord = asRecord(firstItem);
        if (firstItemRecord && typeof firstItemRecord["text"] === "string") {
          raw = firstItemRecord["text"];
        }
      }
    }
  }

  if (!raw) {
    throw new Error("OpenAI 응답에서 전사 결과를 찾을 수 없습니다.");
  }

  let parsedValue: unknown = raw;
  if (typeof raw === "string") {
    try {
      parsedValue = JSON.parse(raw);
    } catch {
      throw new Error("전사 JSON을 해석하지 못했습니다.");
    }
  }

  const parsedRecord = asRecord(parsedValue);
  if (!parsedRecord) {
    throw new Error("전사 JSON을 해석하지 못했습니다.");
  }

  const segments: SpeakerSegment[] = (asArray(parsedRecord.segments) ?? []).map(
    (segmentValue, index) => {
      const segmentRecord = asRecord(segmentValue);
      const speakerValue = segmentRecord?.["speaker"];
      const startValue = segmentRecord?.["start"];
      const endValue = segmentRecord?.["end"];
      const textValue = segmentRecord?.["text"];
      const confidenceValue = segmentRecord?.["confidence"];

      return {
        speaker:
          typeof speakerValue === "string" && speakerValue.trim()
            ? speakerValue.trim()
            : `speaker_${index + 1}`,
        start: typeof startValue === "number" ? startValue : 0,
        end: typeof endValue === "number" ? endValue : 0,
        text: typeof textValue === "string" ? textValue : "",
        confidence:
          typeof confidenceValue === "number" && Number.isFinite(confidenceValue)
            ? Math.min(Math.max(confidenceValue, 0), 1)
            : undefined,
      } satisfies SpeakerSegment;
    },
  );

  if (segments.length === 0) {
    throw new Error("전사 결과에 화자 구간이 포함되어 있지 않습니다.");
  }

  return {
    id:
      jsonRecord && typeof jsonRecord["id"] === "string"
        ? (jsonRecord["id"] as string)
        : generateId(),
    language:
      typeof parsedRecord["language"] === "string"
        ? (parsedRecord["language"] as string)
        : undefined,
    duration:
      typeof parsedRecord["duration"] === "number"
        ? (parsedRecord["duration"] as number)
        : undefined,
    summary:
      typeof parsedRecord["summary"] === "string"
        ? (parsedRecord["summary"] as string)
        : undefined,
    segments,
    metadata: {
      provider: "openai",
      model: DEFAULT_MODEL,
      diarization: diarize,
      usage: jsonRecord?.["usage"] ?? null,
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
