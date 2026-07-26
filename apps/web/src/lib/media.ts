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

export interface MediaFormat {
  format_id: string;
  extension: string | null;
  width: number | null;
  height: number | null;
  filesize_bytes: number | null;
  has_video: boolean;
  has_audio: boolean;
}

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
  formats: MediaFormat[];
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

const VIDEO_QUALITIES: Array<{
  value: ActionOptions["quality"];
  height: number | null;
}> = [
  { value: "best", height: null },
  { value: "1080p", height: 1080 },
  { value: "720p", height: 720 },
  { value: "480p", height: 480 },
  { value: "360p", height: 360 },
];

export function availableVideoQualities(
  formats: MediaFormat[],
): ActionOptions["quality"][] {
  const sourceHeights = new Set(
    formats
      .filter((format) => format.has_video && format.height !== null)
      .map((format) => format.height),
  );
  return VIDEO_QUALITIES.filter(
    ({ height }) => height === null || sourceHeights.has(height),
  ).map(({ value }) => value);
}

export function estimateVideoSize(
  formats: MediaFormat[],
  quality: ActionOptions["quality"],
  container: ActionOptions["container"],
): number | null {
  const targetHeight =
    VIDEO_QUALITIES.find(({ value }) => value === quality)?.height ?? null;
  let videoCandidates = formats.filter(
    (format) =>
      format.has_video &&
      format.filesize_bytes !== null &&
      (targetHeight === null || (format.height !== null && format.height <= targetHeight)),
  );
  const preferredExtension = container === "mp4" || container === "webm" ? container : null;
  if (
    preferredExtension !== null &&
    videoCandidates.some((format) => format.extension === preferredExtension)
  ) {
    videoCandidates = videoCandidates.filter(
      (format) => format.extension === preferredExtension,
    );
  }
  const videoOnly = videoCandidates.filter((format) => !format.has_audio);
  const selectedVideo = [...(videoOnly.length > 0 ? videoOnly : videoCandidates)].sort(
    compareVideoFormats,
  )[0];
  if (!selectedVideo || selectedVideo.filesize_bytes === null) return null;
  if (selectedVideo.has_audio) return selectedVideo.filesize_bytes;

  let audioCandidates = formats.filter(
    (format) => format.has_audio && !format.has_video && format.filesize_bytes !== null,
  );
  const preferredAudioExtension =
    container === "mp4" ? "m4a" : container === "webm" ? "webm" : null;
  if (
    preferredAudioExtension !== null &&
    audioCandidates.some((format) => format.extension === preferredAudioExtension)
  ) {
    audioCandidates = audioCandidates.filter(
      (format) => format.extension === preferredAudioExtension,
    );
  }
  const selectedAudio = audioCandidates.sort(
    (left, right) => (right.filesize_bytes ?? 0) - (left.filesize_bytes ?? 0),
  )[0];
  return selectedVideo.filesize_bytes + (selectedAudio?.filesize_bytes ?? 0);
}

export function estimateAudioSize(
  durationSeconds: number | null,
  codec: ActionOptions["codec"],
  bitrate: ActionOptions["bitrate"],
): number | null {
  if (durationSeconds === null || !Number.isFinite(durationSeconds) || durationSeconds <= 0) {
    return null;
  }
  const kilobitsPerSecond = codec === "wav" ? 1411.2 : Number(bitrate);
  return Math.round((durationSeconds * kilobitsPerSecond * 1000) / 8);
}

export function formatFileSize(bytes: number | null): string {
  if (bytes === null || !Number.isFinite(bytes) || bytes < 0) return "Size unavailable";
  if (bytes < 1024) return `${Math.round(bytes)} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unit = units[0];
  for (let index = 1; index < units.length && value >= 1024; index += 1) {
    value /= 1024;
    unit = units[index];
  }
  return `≈ ${value >= 100 ? value.toFixed(0) : value.toFixed(1)} ${unit}`;
}

function compareVideoFormats(left: MediaFormat, right: MediaFormat): number {
  return (
    (right.height ?? 0) - (left.height ?? 0) ||
    (right.filesize_bytes ?? 0) - (left.filesize_bytes ?? 0)
  );
}

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

export function resultDownloadUrl(jobId: string): string {
  return `/api/backend/jobs/${encodeURIComponent(jobId)}/result`;
}

export function isResultAvailable(job: Job, now = Date.now()): boolean {
  return (
    job.status === "succeeded" &&
    job.result_reference !== null &&
    job.storage_deleted_at === null &&
    job.result_expires_at !== null &&
    Date.parse(job.result_expires_at) > now
  );
}
