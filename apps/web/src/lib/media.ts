export type MediaAction =
  | "download_video"
  | "extract_audio"
  | "cut_clip"
  | "create_gif";

export type JobOperation =
  | "download_video"
  | "extract_audio"
  | "cut_video"
  | "make_loop";

export interface MediaAnalysis {
  source_url: string;
  extractor: string;
  media_id: string;
  title: string;
  author: string | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  webpage_url: string;
  is_playlist: boolean;
  playlist_entry_count: number | null;
  formats: Array<{
    format_id: string;
    extension: string | null;
    width: number | null;
    height: number | null;
    filesize_bytes: number | null;
    has_video: boolean;
    has_audio: boolean;
  }>;
  subtitle_languages: string[];
  available_actions: string[];
}

export interface Job {
  job_id: string;
  operation: JobOperation;
  source_url: string;
  status:
    | "queued"
    | "running"
    | "processing"
    | "cancel_requested"
    | "succeeded"
    | "failed"
    | "cancelled";
  progress_percent: number;
  result_reference: string | null;
  result_expires_at: string | null;
  storage_deleted_at: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface ActionOptions {
  quality: "best" | "1080p" | "720p" | "480p" | "360p";
  container: "auto" | "mp4" | "mkv" | "webm";
  codec: "mp3" | "m4a" | "opus" | "wav";
  bitrate: "128" | "192" | "256" | "320";
  startSeconds: number;
  endSeconds: number;
  outputFormat: "gif" | "webp" | "mp4" | "webm";
  width: number;
  fps: number;
}

export const DEFAULT_OPTIONS: ActionOptions = {
  quality: "best",
  container: "mp4",
  codec: "mp3",
  bitrate: "192",
  startSeconds: 0,
  endSeconds: 10,
  outputFormat: "gif",
  width: 640,
  fps: 15,
};

export function buildJobPayload(
  action: MediaAction,
  sourceUrl: string,
  options: ActionOptions,
): Record<string, unknown> {
  if (action === "download_video") {
    return {
      operation: "download_video",
      source_url: sourceUrl,
      options: { quality: options.quality, container: options.container },
    };
  }
  if (action === "extract_audio") {
    return {
      operation: "extract_audio",
      source_url: sourceUrl,
      options: { codec: options.codec, bitrate: options.bitrate },
    };
  }
  if (action === "cut_clip") {
    return {
      operation: "cut_video",
      source_url: sourceUrl,
      options: {
        start_seconds: options.startSeconds,
        end_seconds: options.endSeconds,
        mode: "accurate",
      },
    };
  }
  return {
    operation: "make_loop",
    source_url: sourceUrl,
    options: {
      start_seconds: options.startSeconds,
      end_seconds: options.endSeconds,
      output_format: options.outputFormat,
      width: options.width,
      fps: options.fps,
      quality: "balanced",
      speed: "1",
      repeat: true,
    },
  };
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null) return "Unknown duration";
  const rounded = Math.max(0, Math.round(seconds));
  const hours = Math.floor(rounded / 3600);
  const minutes = Math.floor((rounded % 3600) / 60);
  const remainder = rounded % 60;
  return hours > 0
    ? `${hours}:${minutes.toString().padStart(2, "0")}:${remainder.toString().padStart(2, "0")}`
    : `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

export function readApiError(payload: unknown): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof payload.error === "object" &&
    payload.error !== null &&
    "message" in payload.error &&
    typeof payload.error.message === "string"
  ) {
    return payload.error.message;
  }
  return "Something went wrong. Please try again.";
}
