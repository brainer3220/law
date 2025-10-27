/**
 * Audio transcription result shared types.
 */

export interface SpeakerSegment {
  speaker: string;
  start: number;
  end: number;
  text: string;
  confidence?: number;
}

export interface TranscriptionPayload {
  id: string;
  language?: string;
  duration?: number;
  summary?: string;
  segments: SpeakerSegment[];
  metadata?: Record<string, unknown>;
  generatedAt?: string;
}

export interface LiveTranscriptSegment extends SpeakerSegment {
  id: string;
  isFinal: boolean;
}

export type LiveTranscribeServerMessage =
  | { type: "ready" }
  | { type: "status"; state: "connecting-upstream" | "streaming" | "finalizing" | "closed" }
  | { type: "segment"; segment: LiveTranscriptSegment }
  | { type: "segments"; segments: LiveTranscriptSegment[] }
  | { type: "error"; message: string }
  | { type: "debug"; payload: unknown }
  | { type: "info"; message: string };

export type LiveTranscribeClientMessage =
  | { type: "start"; diarize: boolean }
  | { type: "audio-chunk"; id: string; mimeType: string; data: string }
  | { type: "commit" }
  | { type: "stop" };
