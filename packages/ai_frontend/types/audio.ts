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
