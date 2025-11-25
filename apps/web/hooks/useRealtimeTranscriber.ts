import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  LiveTranscribeClientMessage,
  LiveTranscribeServerMessage,
  LiveTranscriptSegment,
} from "@/types/audio";

// Configuration constants
const MAX_RECONNECT_ATTEMPTS = 5;
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const MAX_SEGMENTS_HISTORY = 1000; // Prevent memory leaks
const AUDIO_LEVEL_SMOOTHING = 0.8;

type RecorderState = "idle" | "connecting" | "recording" | "stopping" | "error";

export interface RealtimeTranscriptState {
  status: RecorderState;
  connecting: boolean;
  error: string | null;
  segments: LiveTranscriptSegment[];
  diarization: boolean;
  elapsedMs: number;
  audioLevel: number; // 0-100
  reconnectAttempt: number;
}

export interface RealtimeTranscriberControls {
  start: () => Promise<void>;
  stop: () => Promise<void>;
  reset: () => void;
  setDiarization: (value: boolean) => void;
  clearSegments: () => void;
}

export function useRealtimeTranscriber(url = "/api/transcribe/live"): [
  RealtimeTranscriptState,
  RealtimeTranscriberControls,
] {
  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const chunkSeq = useRef(0);
  const startTimeRef = useRef<number | null>(null);
  const elapsedTimerRef = useRef<number | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isRecordingRef = useRef(false); // Track recording state for reconnection
  const [diarization, setDiarizationEnabled] = useState(true);
  const [status, setStatus] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [segments, setSegments] = useState<LiveTranscriptSegment[]>([]);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const startAudioLevelMonitoring = useCallback((stream: MediaStream) => {
    try {
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);

      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = AUDIO_LEVEL_SMOOTHING;
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const updateLevel = () => {
        if (!analyserRef.current) return;

        analyserRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((sum, value) => sum + value, 0) / dataArray.length;
        const level = Math.min(100, Math.round((average / 255) * 100));
        setAudioLevel(level);

        animationFrameRef.current = requestAnimationFrame(updateLevel);
      };

      updateLevel();
    } catch (err) {
      console.warn("[RealtimeTranscriber] Audio level monitoring failed:", err);
    }
  }, []);

  const stopAudioLevelMonitoring = useCallback(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(console.warn);
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0);
  }, []);

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
          let next: LiveTranscriptSegment[];

          if (existingIndex >= 0) {
            // Update existing segment
            next = [...prev];
            next[existingIndex] = payload.segment;
          } else {
            // Add new segment
            next = [...prev, payload.segment];
          }

          // Limit history to prevent memory leaks
          if (next.length > MAX_SEGMENTS_HISTORY) {
            next = next.slice(-MAX_SEGMENTS_HISTORY);
          }

          return next;
        });
      } else if (payload.type === "segments") {
        setSegments(payload.segments.slice(-MAX_SEGMENTS_HISTORY));
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
        setReconnectAttempt(0); // Reset on successful connection
      } else if (payload.type === "info") {
        // Handle heartbeat and other info messages silently
        console.debug("[RealtimeTranscriber] Info:", payload.message);
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
    stopAudioLevelMonitoring();
    clearTimer();
  }, [clearTimer, stopAudioLevelMonitoring]);

  const reset = useCallback(() => {
    closeSocket();
    stopMediaRecorder();
    setSegments([]);
    setError(null);
    setStatus("idle");
    chunkSeq.current = 0;
    setElapsedMs(0);
    startTimeRef.current = null;
    setReconnectAttempt(0);
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, [closeSocket, stopMediaRecorder]);

  const clearSegments = useCallback(() => {
    setSegments([]);
  }, []);

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
      startAudioLevelMonitoring(stream);

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

        // Attempt reconnection if was recording and not manually stopped
        if (isRecordingRef.current && reconnectAttempt < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            INITIAL_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttempt),
            MAX_RECONNECT_DELAY_MS,
          );
          setReconnectAttempt((prev) => prev + 1);
          console.log(`[RealtimeTranscriber] Reconnecting in ${delay}ms (attempt ${reconnectAttempt + 1}/${MAX_RECONNECT_ATTEMPTS})`);

          reconnectTimeoutRef.current = window.setTimeout(() => {
            void start();
          }, delay);
        } else {
          isRecordingRef.current = false;
        }
      });

      recorder.addEventListener("dataavailable", (event) => {
        void handleAudioChunk(event);
      });

      recorder.addEventListener("start", () => {
        setStatus("recording");
        isRecordingRef.current = true;
        startTimeRef.current = Date.now();
        updateElapsed();
        clearTimer();
        elapsedTimerRef.current = window.setInterval(updateElapsed, 500);
      });

      recorder.addEventListener("stop", () => {
        isRecordingRef.current = false;
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
    startAudioLevelMonitoring,
    reconnectAttempt,
  ]);

  const stop = useCallback(async () => {
    if (status !== "recording" && status !== "stopping") {
      return;
    }
    isRecordingRef.current = false; // Prevent reconnection
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
      audioLevel,
      reconnectAttempt,
    }),
    [status, error, segments, diarization, elapsedMs, audioLevel, reconnectAttempt],
  );

  const controls = useMemo<RealtimeTranscriberControls>(
    () => ({
      start,
      stop,
      reset,
      setDiarization: setDiarizationEnabled,
      clearSegments,
    }),
    [start, stop, reset, clearSegments],
  );

  return [state, controls];
}
