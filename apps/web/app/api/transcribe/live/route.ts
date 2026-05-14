import { NextRequest } from "next/server";
import { createMockTranscription, transcribeWithOpenAI } from "@/lib/server/transcription";
import { requireAuthenticatedUserId } from "../../auth/require-user";
import type {
  LiveTranscribeClientMessage,
  LiveTranscribeServerMessage,
  LiveTranscriptSegment,
} from "@/types/audio";

export const runtime = "edge";

// Connection management constants
const CONNECTION_TIMEOUT_MS = 30000; // 30 seconds idle timeout
const MAX_CHUNK_RATE = 10; // Maximum chunks per second
const CHUNK_RATE_WINDOW_MS = 1000; // Rate limiting window
const HEARTBEAT_INTERVAL_MS = 15000; // Send heartbeat every 15 seconds
const MAX_CHUNK_BYTES = 1024 * 1024;
const MAX_QUEUE_BYTES = 5 * 1024 * 1024;

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

  private queuedBytes = 0;

  private processing = false;

  private closed = false;

  private timelineCursor = 0;

  private mockSegments = createMockTranscription("live", true).segments;

  private mockIndex = 0;

  // Connection management
  private lastActivityTime = Date.now();

  private chunkTimestamps: number[] = [];

  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  private timeoutTimer: ReturnType<typeof setInterval> | null = null;

  constructor(socket: WebSocket) {
    this.downstream = socket;
    this.hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
    this.startConnectionMonitoring();
  }

  start() {
    sendMessage(this.downstream, { type: "ready" });
    this.downstream.addEventListener("message", (event) => {
      this.handleClientMessage(event.data);
    });
    this.downstream.addEventListener("close", () => {
      this.cleanup();
    });
    this.downstream.addEventListener("error", () => {
      this.cleanup();
    });
  }

  private startConnectionMonitoring() {
    // Heartbeat to keep connection alive
    this.heartbeatTimer = setInterval(() => {
      if (!this.closed) {
        sendMessage(this.downstream, { type: "info", message: "heartbeat" });
      }
    }, HEARTBEAT_INTERVAL_MS);

    // Connection timeout checker
    this.timeoutTimer = setInterval(() => {
      const idleTime = Date.now() - this.lastActivityTime;
      if (idleTime > CONNECTION_TIMEOUT_MS && !this.closed) {
        sendMessage(this.downstream, {
          type: "error",
          message: "연결 시간 초과: 활동이 감지되지 않았습니다.",
        });
        this.cleanup();
        this.downstream.close();
      }
    }, 5000); // Check every 5 seconds
  }

  private cleanup() {
    this.closed = true;
    this.jobs = [];
    this.queuedBytes = 0;
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.timeoutTimer) {
      clearInterval(this.timeoutTimer);
      this.timeoutTimer = null;
    }
  }

  private handleClientMessage(raw: unknown) {
    if (typeof raw !== "string") {
      return;
    }

    // Update activity time for timeout monitoring
    this.lastActivityTime = Date.now();

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
        if (message.data.length > Math.ceil((MAX_CHUNK_BYTES * 4) / 3) + 4) {
          sendMessage(this.downstream, {
            type: "error",
            message: "오디오 청크가 허용 크기를 초과했습니다.",
          });
          return;
        }
        // Rate limiting check
        if (!this.checkRateLimit()) {
          sendMessage(this.downstream, {
            type: "error",
            message: "전송 속도 제한 초과: 오디오 청크를 너무 빠르게 전송하고 있습니다.",
          });
          return;
        }
        {
          let bytes: Uint8Array;
          try {
            bytes = base64ToUint8Array(message.data);
          } catch {
            sendMessage(this.downstream, {
              type: "error",
              message: "오디오 청크 인코딩이 올바르지 않습니다.",
            });
            return;
          }
          if (bytes.byteLength > MAX_CHUNK_BYTES) {
            sendMessage(this.downstream, {
              type: "error",
              message: "오디오 청크가 허용 크기를 초과했습니다.",
            });
            return;
          }
          this.enqueueChunk({
            id: message.id,
            bytes,
            mimeType: message.mimeType || "audio/webm",
            receivedAt: Date.now(),
          });
        }
        break;
      case "commit":
        // handled implicitly per chunk.
        break;
      case "stop":
        this.cleanup();
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

  private checkRateLimit(): boolean {
    const now = Date.now();
    // Remove timestamps outside the window
    this.chunkTimestamps = this.chunkTimestamps.filter(
      (timestamp) => now - timestamp < CHUNK_RATE_WINDOW_MS,
    );

    // Check if we're over the limit
    if (this.chunkTimestamps.length >= MAX_CHUNK_RATE) {
      return false;
    }

    // Add current timestamp
    this.chunkTimestamps.push(now);
    return true;
  }

  private enqueueChunk(job: ChunkJob) {
    if (this.closed) {
      return;
    }
    if (this.queuedBytes + job.bytes.byteLength > MAX_QUEUE_BYTES) {
      sendMessage(this.downstream, {
        type: "error",
        message: "오디오 처리 대기열이 허용 크기를 초과했습니다.",
      });
      return;
    }
    this.queuedBytes += job.bytes.byteLength;
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
      this.queuedBytes = Math.max(0, this.queuedBytes - job.bytes.byteLength);
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
  const userId = await requireAuthenticatedUserId();
  if (userId instanceof Response) {
    return userId;
  }
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
