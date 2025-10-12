import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  LiveTranscribeClientMessage,
  LiveTranscribeServerMessage,
  LiveTranscriptSegment,
} from "@/types/audio";

type RecorderState = "idle" | "connecting" | "recording" | "stopping" | "error";

export interface RealtimeTranscriptState {
  status: RecorderState;
  connecting: boolean;
  error: string | null;
  segments: LiveTranscriptSegment[];
  diarization: boolean;
  elapsedMs: number;
}

export interface RealtimeTranscriberControls {
  start: () => Promise<void>;
  stop: () => Promise<void>;
  reset: () => void;
  setDiarization: (value: boolean) => void;
}

export function useRealtimeTranscriber(url = "/api/transcribe/live"): [
  RealtimeTranscriptState,
  RealtimeTranscriberControls,
] {
  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunkSeq = useRef(0);
  const startTimeRef = useRef<number | null>(null);
  const elapsedTimerRef = useRef<number | null>(null);
  const [diarization, setDiarizationEnabled] = useState(true);
  const [status, setStatus] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [segments, setSegments] = useState<LiveTranscriptSegment[]>([]);
  const [elapsedMs, setElapsedMs] = useState(0);

  const clearTimer = useCallback(() => {
    if (elapsedTimerRef.current) {
      window.clearInterval(elapsedTimerRef.current);
    }
    elapsedTimerRef.current = null;
  }, []);

  const updateElapsed = useCallback(() => {
    if (startTimeRef.current) {
      const delta = Date.now() - startTimeRef.current;
      setElapsedMs(delta);
    }
  }, []);

  const handleServerMessage = useCallback((event: MessageEvent<string>) => {
    try {
      const payload = JSON.parse(event.data) as LiveTranscribeServerMessage;
      if (payload.type === "segment") {
        setSegments((prev) => {
          const existingIndex = prev.findIndex((item) => item.id === payload.segment.id);
          if (existingIndex >= 0) {
            const next = [...prev];
            next[existingIndex] = payload.segment;
            return next;
          }
          return [...prev, payload.segment];
        });
      } else if (payload.type === "segments") {
        setSegments(payload.segments);
      } else if (payload.type === "error") {
        setError(payload.message);
        setStatus("error");
      } else if (payload.type === "status") {
        if (payload.state === "streaming") {
          setStatus("recording");
        } else if (payload.state === "finalizing") {
          setStatus("stopping");
        } else if (payload.state === "closed") {
          setStatus("idle");
        }
      } else if (payload.type === "ready") {
        setStatus((prev) => (prev === "connecting" ? "idle" : prev));
      }
    } catch (parseError) {
      console.warn("[RealtimeTranscriber] Failed to parse message", event.data, parseError);
    }
  }, []);

  const closeSocket = useCallback((reason?: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      try {
        socketRef.current.close(1000, reason);
      } catch (socketError) {
        console.warn("[RealtimeTranscriber] Socket close error:", socketError);
      }
    }
    socketRef.current = null;
  }, []);

  const stopMediaRecorder = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (stopError) {
        console.warn("[RealtimeTranscriber] Failed to stop recorder", stopError);
      }
    }
    mediaRecorderRef.current = null;
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    streamRef.current = null;
    clearTimer();
  }, [clearTimer]);

  const reset = useCallback(() => {
    closeSocket();
    stopMediaRecorder();
    setSegments([]);
    setError(null);
    setStatus("idle");
    chunkSeq.current = 0;
    setElapsedMs(0);
    startTimeRef.current = null;
  }, [closeSocket, stopMediaRecorder]);

  useEffect(() => () => {
    reset();
  }, [reset]);

  const sendMessage = useCallback(
    (message: LiveTranscribeClientMessage) => {
      const socket = socketRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        return;
      }
      socket.send(JSON.stringify(message));
    },
    [],
  );

  const handleAudioChunk = useCallback(async (event: BlobEvent) => {
    const blob = event.data;
    if (!blob || blob.size === 0) {
      return;
    }
    const buffer = await blob.arrayBuffer();
    const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
    const id = `chunk-${Date.now()}-${chunkSeq.current}`;
    chunkSeq.current += 1;
    sendMessage({
      type: "audio-chunk",
      id,
      data: base64,
      mimeType: blob.type || "audio/webm",
    });
    sendMessage({ type: "commit" });
  }, [sendMessage]);

  const start = useCallback(async () => {
    if (status === "recording" || status === "connecting") {
      return;
    }
    setError(null);
    setStatus("connecting");

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("이 브라우저는 마이크 입력을 지원하지 않습니다.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
        audioBitsPerSecond: 64000,
      });

      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.addEventListener("open", () => {
        sendMessage({ type: "start", diarize: diarization });
      });
      socket.addEventListener("message", handleServerMessage);
      socket.addEventListener("error", (event) => {
        console.error("[RealtimeTranscriber] socket error", event);
        setError("실시간 전사 연결에 실패했습니다.");
        setStatus("error");
      });
      socket.addEventListener("close", () => {
        setStatus((prev) => (prev === "error" ? prev : "idle"));
        clearTimer();
      });

      recorder.addEventListener("dataavailable", (event) => {
        void handleAudioChunk(event);
      });

      recorder.addEventListener("start", () => {
        setStatus("recording");
        startTimeRef.current = Date.now();
        updateElapsed();
        clearTimer();
        elapsedTimerRef.current = window.setInterval(updateElapsed, 500);
      });

      recorder.addEventListener("stop", () => {
        sendMessage({ type: "stop" });
        setStatus("stopping");
        clearTimer();
      });

      mediaRecorderRef.current = recorder;
      recorder.start(1500);
    } catch (err) {
      console.error("[RealtimeTranscriber] start error", err);
      setError(err instanceof Error ? err.message : "실시간 전사를 시작하지 못했습니다.");
      setStatus("error");
      stopMediaRecorder();
      closeSocket();
    }
  }, [
    diarization,
    status,
    url,
    sendMessage,
    handleServerMessage,
    updateElapsed,
    clearTimer,
    stopMediaRecorder,
    closeSocket,
  ]);

  const stop = useCallback(async () => {
    if (status !== "recording" && status !== "stopping") {
      return;
    }
    stopMediaRecorder();
    sendMessage({ type: "stop" });
    setStatus("stopping");
  }, [sendMessage, status, stopMediaRecorder]);

  const state = useMemo<RealtimeTranscriptState>(
    () => ({
      status,
      connecting: status === "connecting",
      error,
      segments,
      diarization,
      elapsedMs,
    }),
    [status, error, segments, diarization, elapsedMs],
  );

  const controls = useMemo<RealtimeTranscriberControls>(
    () => ({
      start,
      stop,
      reset,
      setDiarization: setDiarizationEnabled,
    }),
    [start, stop, reset],
  );

  return [state, controls];
}
