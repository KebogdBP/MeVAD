"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  MEDIA_ACTIONS,
  TERMINAL_JOB_STATUSES,
  type WorkspaceOperation,
  workspaceErrorMessage,
} from "@/components/media-workspace-model";
import { MediaWorkspaceView } from "@/components/media-workspace-view";
import {
  type ActionOptions,
  DEFAULT_OPTIONS,
  type Job,
  type MediaAction,
  type MediaAnalysis,
  buildJobPayload,
  readApiError,
  validateActionOptions,
} from "@/lib/media";
import {
  telemetryDuration,
  telemetryFailureKind,
  trackTelemetry,
} from "@/lib/telemetry-client";

export function MediaWorkspace() {
  const [url, setUrl] = useState("");
  const [analysis, setAnalysis] = useState<MediaAnalysis | null>(null);
  const [action, setAction] = useState<MediaAction>("download_video");
  const [options, setOptions] = useState<ActionOptions>(DEFAULT_OPTIONS);
  const [job, setJob] = useState<Job | null>(null);
  const [operation, setOperation] = useState<WorkspaceOperation>(null);
  const [error, setError] = useState<string | null>(null);
  const trackedTerminalJob = useRef<string | null>(null);

  const availableActions = useMemo(
    () => new Set(analysis?.available_actions ?? []),
    [analysis],
  );
  const actionError = useMemo(
    () => (analysis ? validateActionOptions(action, analysis, options) : null),
    [action, analysis, options],
  );

  useEffect(() => {
    if (!job || TERMINAL_JOB_STATUSES.has(job.status)) return;

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/backend/jobs/${job.job_id}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        if (response.ok) setJob((await response.json()) as Job);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(
            workspaceErrorMessage(
              cause,
              "We couldn’t refresh the job. Check your connection and try again.",
            ),
          );
        }
      }
    }, 1200);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [job]);

  useEffect(() => {
    if (
      !job ||
      !TERMINAL_JOB_STATUSES.has(job.status) ||
      trackedTerminalJob.current === job.job_id
    ) {
      return;
    }
    trackedTerminalJob.current = job.job_id;
    trackTelemetry("job_terminal", {
      action: actionForJob(job),
      status: job.status,
    });
  }, [job]);

  async function analyze() {
    const startedAt = performance.now();
    trackTelemetry("analysis_started");
    setOperation("analyzing");
    setError(null);
    setJob(null);
    try {
      const response = await fetch("/api/backend/media/analyze", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(readApiError(payload));

      const result = payload as MediaAnalysis;
      const firstAvailableAction = MEDIA_ACTIONS.find((candidate) =>
        result.available_actions.includes(candidate.id),
      );
      setAnalysis(result);
      if (firstAvailableAction) setAction(firstAvailableAction.id);
      setOptions((current) => ({
        ...current,
        quality: "best",
        startSeconds: 0,
        endSeconds: Math.min(10, result.duration_seconds ?? 10),
      }));
      trackTelemetry("analysis_succeeded", {
        duration_ms: telemetryDuration(startedAt),
        available_actions: Math.min(4, result.available_actions.length),
      });
    } catch (cause) {
      setAnalysis(null);
      trackTelemetry("analysis_failed", {
        duration_ms: telemetryDuration(startedAt),
        failure_kind: telemetryFailureKind(cause),
      });
      setError(
        workspaceErrorMessage(
          cause,
          "We couldn’t analyze this link. Check the URL and try again.",
        ),
      );
    } finally {
      setOperation(null);
    }
  }

  async function createJob() {
    if (!analysis || actionError) return;
    setOperation("creating-job");
    setError(null);
    try {
      const response = await fetch("/api/backend/jobs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(
          buildJobPayload(action, analysis.source_url, options),
        ),
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(readApiError(payload));
      setJob(payload as Job);
      trackTelemetry("job_created", { action });
    } catch (cause) {
      setError(
        workspaceErrorMessage(
          cause,
          "We couldn’t start this job. Review the options and try again.",
        ),
      );
    } finally {
      setOperation(null);
    }
  }

  async function cancelJob() {
    if (!job) return;
    trackTelemetry("job_cancel_requested", { action: actionForJob(job) });
    setOperation("cancelling-job");
    setError(null);
    try {
      const response = await fetch(`/api/backend/jobs/${job.job_id}/cancel`, {
        method: "POST",
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(readApiError(payload));
      setJob(payload as Job);
    } catch (cause) {
      setError(
        workspaceErrorMessage(
          cause,
          "We couldn’t cancel the job. Check its latest status and try again.",
        ),
      );
    } finally {
      setOperation(null);
    }
  }

  return (
    <MediaWorkspaceView
      url={url}
      analysis={analysis}
      action={action}
      options={options}
      job={job}
      operation={operation}
      error={error}
      availableActions={availableActions}
      actionError={actionError}
      onUrlChange={setUrl}
      onAnalyze={analyze}
      onActionChange={(nextAction) => {
        setAction(nextAction);
        trackTelemetry("action_selected", { action: nextAction });
      }}
      onOptionsChange={setOptions}
      onCreateJob={createJob}
      onCancelJob={cancelJob}
    />
  );
}

function actionForJob(job: Job): MediaAction {
  if (job.operation === "extract_audio") return "extract_audio";
  if (job.operation === "cut_video") return "cut_clip";
  if (job.operation === "make_loop") return "create_gif";
  return "download_video";
}
