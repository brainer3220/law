import { NextRequest } from "next/server";
import { createMockTranscription, transcribeWithOpenAI } from "@/lib/server/transcription";
import type {
  LiveTranscribeClientMessage,
  LiveTranscribeServerMessage,
  LiveTranscriptSegment,
} from "@/types/audio";

export const runtime = "edge";

interface EdgeWebSocket extends WebSocket {
  accept(): void;
}

interface WebSocketPairGlobal {
  WebSocketPair?: new () => { 0: WebSocket; 1: EdgeWebSocket };
}

interface WebSocketResponseInit extends ResponseInit {
  webSocket?: WebSocket;
}

function createWebSocketPair(): { client: WebSocket; server: EdgeWebSocket } {
  const { WebSocketPair } = globalThis as typeof globalThis & WebSocketPairGlobal;
  if (typeof WebSocketPair !== "function") {
    throw new Error("WebSocketPair is not supported in this runtime.");
  }

  const pair = new WebSocketPair();
  return { client: pair[0], server: pair[1] };
}

interface ChunkJob {
  id: string;
  bytes: Uint8Array;
  mimeType: string;
  receivedAt: number;
}

function base64ToUint8Array(base64: string): Uint8Array {
  if (typeof Buffer !== "undefined") {
    return Uint8Array.from(Buffer.from(base64, "base64"));
  }
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function sendMessage(socket: WebSocket, message: LiveTranscribeServerMessage) {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(message));
  }
}

class LiveTranscribeSession {
  private readonly downstream: WebSocket;

  private readonly hasOpenAIKey: boolean;

  private diarize = true;

  private jobs: ChunkJob[] = [];

  private processing = false;

  private closed = false;

  private timelineCursor = 0;

  private mockSegments = createMockTranscription("live", true).segments;

  private mockIndex = 0;

  constructor(socket: WebSocket) {
    this.downstream = socket;
    this.hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
  }

  start() {
    sendMessage(this.downstream, { type: "ready" });
    this.downstream.addEventListener("message", (event) => {
      this.handleClientMessage(event.data);
    });
    this.downstream.addEventListener("close", () => {
      this.closed = true;
      this.jobs = [];
    });
    this.downstream.addEventListener("error", () => {
      this.closed = true;
      this.jobs = [];
    });
  }

  private handleClientMessage(raw: unknown) {
    if (typeof raw !== "string") {
      return;
    }
    let message: LiveTranscribeClientMessage | null = null;
    try {
      message = JSON.parse(raw) as LiveTranscribeClientMessage;
    } catch {
      sendMessage(this.downstream, {
        type: "error",
        message: "클라이언트 메시지를 해석하지 못했습니다.",
      });
      return;
    }

    switch (message.type) {
      case "start":
        this.diarize = Boolean(message.diarize);
        sendMessage(this.downstream, {
          type: "status",
          state: "streaming",
        });
        break;
      case "audio-chunk":
        this.enqueueChunk({
          id: message.id,
          bytes: base64ToUint8Array(message.data),
          mimeType: message.mimeType || "audio/webm",
          receivedAt: Date.now(),
        });
        break;
      case "commit":
        // handled implicitly per chunk.
        break;
      case "stop":
        this.closed = true;
        this.jobs = [];
        sendMessage(this.downstream, {
          type: "status",
          state: "finalizing",
        });
        setTimeout(() => {
          sendMessage(this.downstream, { type: "status", state: "closed" });
          this.downstream.close();
        }, 500);
        break;
      default:
        sendMessage(this.downstream, {
          type: "error",
          message: "지원되지 않는 메시지 유형입니다.",
        });
        break;
    }
  }

  private enqueueChunk(job: ChunkJob) {
    if (this.closed) {
      return;
    }
    this.jobs.push(job);
    void this.processQueue();
  }

  private async processQueue() {
    if (this.processing || this.closed) {
      return;
    }
    this.processing = true;

    while (this.jobs.length > 0 && !this.closed) {
      const job = this.jobs.shift();
      if (!job) {
        continue;
      }
      try {
        if (this.hasOpenAIKey) {
          await this.processOpenAI(job);
        } else {
          this.processMock(job);
        }
      } catch (err) {
        console.error("[LiveTranscribeSession] job error", err);
        sendMessage(this.downstream, {
          type: "error",
          message:
            err instanceof Error ? err.message : "실시간 전사 처리 중 오류가 발생했습니다.",
        });
      }
    }

    this.processing = false;
  }

  private async processOpenAI(job: ChunkJob) {
    const fileName = `${job.id}.${job.mimeType.split("/")[1] ?? "webm"}`;
    const chunkArrayBuffer = new ArrayBuffer(job.bytes.byteLength);
    new Uint8Array(chunkArrayBuffer).set(job.bytes);
    const file = new File([chunkArrayBuffer], fileName, { type: job.mimeType });
    const payload = await transcribeWithOpenAI(file, job.bytes, this.diarize);
    const baseStart = this.timelineCursor;
    const chunkDuration =
      payload.duration ??
      payload.segments.reduce((max, segment) => Math.max(max, segment.end), 0);

    const segments: LiveTranscriptSegment[] = payload.segments.map((segment, index) => ({
      id: `${payload.id}-${job.id}-${index}`,
      speaker: segment.speaker,
      start: baseStart + segment.start,
      end: baseStart + segment.end,
      text: segment.text,
      confidence: segment.confidence,
      isFinal: true,
    }));

    segments.forEach((segment) => {
      sendMessage(this.downstream, {
        type: "segment",
        segment,
      });
    });

    this.timelineCursor += chunkDuration || 0;
  }

  private processMock(job: ChunkJob) {
    const sample = this.mockSegments[this.mockIndex % this.mockSegments.length];
    this.mockIndex += 1;
    const duration = Math.max(sample.end - sample.start, 4);
    const baseStart = this.timelineCursor;
    const segment: LiveTranscriptSegment = {
      id: `mock-${job.id}-${this.mockIndex}`,
      speaker: this.diarize ? sample.speaker : "speaker",
      start: baseStart,
      end: baseStart + duration,
      text: sample.text,
      confidence: sample.confidence,
      isFinal: true,
    };

    sendMessage(this.downstream, {
      type: "segment",
      segment,
    });

    this.timelineCursor += duration;
  }
}

export async function GET(req: NextRequest) {
  if (req.headers.get("upgrade")?.toLowerCase() !== "websocket") {
    return new Response("Expected WebSocket upgrade", { status: 426 });
  }

  const { client, server } = createWebSocketPair();

  server.accept();

  const session = new LiveTranscribeSession(server);
  session.start();

  const init: WebSocketResponseInit = {
    status: 101,
    webSocket: client,
  };

  return new Response(null, init);
}
