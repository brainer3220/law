import { NextResponse, type NextRequest } from "next/server";
import { createMockTranscription, transcribeWithOpenAI } from "@/lib/server/transcription";
import { requireAuthenticatedUserId } from "../auth/require-user";

export const runtime = "nodejs";

const MAX_AUDIO_BYTES = 25 * 1024 * 1024;
const ALLOWED_AUDIO_TYPES = new Set([
  "audio/aac",
  "audio/flac",
  "audio/m4a",
  "audio/mp3",
  "audio/mp4",
  "audio/mpeg",
  "audio/ogg",
  "audio/wav",
  "audio/webm",
  "audio/x-m4a",
]);

function badRequest(error: string, details?: unknown, status = 400) {
  return NextResponse.json(
    { ok: false, error, details: details ?? null },
    { status },
  );
}

export async function POST(request: NextRequest) {
  try {
    const userId = await requireAuthenticatedUserId();
    if (userId instanceof Response) {
      return userId;
    }
    const formData = (await request.formData()) as unknown as {
      get(name: string): FormDataEntryValue | null;
    };
    const audio = formData.get("audio");

    if (!audio || !(audio instanceof File)) {
      return badRequest("유효한 오디오 파일이 필요합니다.");
    }
    if (audio.size > MAX_AUDIO_BYTES) {
      return badRequest("오디오 파일이 허용 크기를 초과했습니다.", null, 413);
    }
    if (audio.type && !ALLOWED_AUDIO_TYPES.has(audio.type.toLowerCase())) {
      return badRequest("지원하지 않는 오디오 형식입니다.");
    }

    const diarize = (formData.get("diarize") ?? "").toString().toLowerCase() === "true";

    const arrayBuffer = await audio.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);

    const hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
    const transcription = hasOpenAIKey
      ? await transcribeWithOpenAI(audio, bytes, diarize)
      : createMockTranscription(audio.name, diarize);

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
