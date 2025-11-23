import { NextResponse, type NextRequest } from "next/server";
import type { TranscriptionPayload } from "@/types/audio";
import { createMockTranscription, transcribeWithOpenAI } from "@/lib/server/transcription";

export const runtime = "nodejs";

function badRequest(error: string, details?: unknown, status = 400) {
  return NextResponse.json(
    { ok: false, error, details: details ?? null },
    { status },
  );
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
