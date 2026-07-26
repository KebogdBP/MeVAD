import type { Job, MediaAction } from "@/lib/media";

export interface MediaActionDefinition {
  id: MediaAction;
  icon: string;
  label: string;
  hint: string;
}

export const MEDIA_ACTIONS: readonly MediaActionDefinition[] = [
  {
    id: "download_video",
    icon: "↓",
    label: "Video",
    hint: "MP4, WebM or source quality",
  },
  {
    id: "extract_audio",
    icon: "♪",
    label: "Audio",
    hint: "MP3, M4A, Opus or WAV",
  },
  {
    id: "cut_clip",
    icon: "✂",
    label: "Clip",
    hint: "Choose a precise interval",
  },
  {
    id: "create_gif",
    icon: "↻",
    label: "GIF & Loop",
    hint: "GIF, WebP, MP4 or WebM",
  },
];

export const TERMINAL_JOB_STATUSES = new Set<Job["status"]>([
  "succeeded",
  "failed",
  "cancelled",
]);

export type WorkspaceOperation =
  | "analyzing"
  | "creating-job"
  | "cancelling-job"
  | null;

type BadgeTone = "neutral" | "accent" | "success" | "warning" | "danger";

export interface JobStatusPresentation {
  label: string;
  detail: string;
  tone: BadgeTone;
}

const JOB_STATUS_PRESENTATION: Record<
  Job["status"],
  JobStatusPresentation
> = {
  queued: {
    label: "Queued",
    detail: "Waiting for an available worker.",
    tone: "neutral",
  },
  running: {
    label: "Downloading",
    detail: "Retrieving the source media.",
    tone: "accent",
  },
  processing: {
    label: "Processing",
    detail: "Preparing your selected output.",
    tone: "warning",
  },
  cancel_requested: {
    label: "Cancelling",
    detail: "Stopping safely at the next checkpoint.",
    tone: "warning",
  },
  succeeded: {
    label: "Ready",
    detail: "Your temporary result is ready.",
    tone: "success",
  },
  failed: {
    label: "Failed",
    detail: "The job could not be completed.",
    tone: "danger",
  },
  cancelled: {
    label: "Cancelled",
    detail: "The job stopped without creating a result.",
    tone: "neutral",
  },
};

export function getJobStatusPresentation(
  status: Job["status"],
): JobStatusPresentation {
  return JOB_STATUS_PRESENTATION[status];
}

export function workspaceErrorMessage(
  cause: unknown,
  fallback: string,
): string {
  return cause instanceof Error && cause.message.trim()
    ? cause.message
    : fallback;
}
