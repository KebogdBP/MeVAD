"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ActionOptions,
  DEFAULT_OPTIONS,
  Job,
  MediaAction,
  MediaAnalysis,
  availableVideoQualities,
  buildJobPayload,
  estimateAudioSize,
  formatDuration,
  estimateVideoSize,
  formatFileSize,
  isResultAvailable,
  readApiError,
  resultDownloadUrl,
} from "@/lib/media";

const actions: Array<{ id: MediaAction; icon: string; label: string; hint: string }> = [
  { id: "download_video", icon: "↓", label: "Video", hint: "MP4, WebM or source quality" },
  { id: "extract_audio", icon: "♪", label: "Audio", hint: "MP3, M4A, Opus or WAV" },
  { id: "cut_clip", icon: "✂", label: "Clip", hint: "Choose a precise interval" },
  { id: "create_gif", icon: "↻", label: "GIF & Loop", hint: "GIF, WebP, MP4 or WebM" },
];

const terminalStatuses = new Set(["succeeded", "failed", "cancelled"]);

export function MediaWorkspace() {
  const [url, setUrl] = useState("");
  const [analysis, setAnalysis] = useState<MediaAnalysis | null>(null);
  const [action, setAction] = useState<MediaAction>("download_video");
  const [options, setOptions] = useState<ActionOptions>(DEFAULT_OPTIONS);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const availableActions = useMemo(
    () => new Set(analysis?.available_actions ?? []),
    [analysis],
  );

  useEffect(() => {
    if (!job || terminalStatuses.has(job.status)) return;
    const timer = window.setInterval(async () => {
      const response = await fetch(`/api/backend/jobs/${job.job_id}`, { cache: "no-store" });
      if (response.ok) setJob((await response.json()) as Job);
    }, 1200);
    return () => window.clearInterval(timer);
  }, [job]);

  async function analyze(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
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
      setAnalysis(result);
      const first = actions.find((candidate) => result.available_actions.includes(candidate.id));
      if (first) setAction(first.id);
      setOptions((current) => ({
        ...current,
        quality: "best",
        endSeconds: Math.min(10, result.duration_seconds ?? 10),
      }));
    } catch (cause) {
      setAnalysis(null);
      setError(cause instanceof Error ? cause.message : "The media could not be analyzed.");
    } finally {
      setBusy(false);
    }
  }

  async function createJob() {
    if (!analysis) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/backend/jobs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(buildJobPayload(action, analysis.source_url, options)),
      });
      const payload: unknown = await response.json();
      if (!response.ok) throw new Error(readApiError(payload));
      setJob(payload as Job);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The job could not be started.");
    } finally {
      setBusy(false);
    }
  }

  async function cancelJob() {
    if (!job) return;
    const response = await fetch(`/api/backend/jobs/${job.job_id}/cancel`, { method: "POST" });
    const payload: unknown = await response.json();
    if (response.ok) setJob(payload as Job);
    else setError(readApiError(payload));
  }

  return (
    <section className="workspace-shell" id="workspace" aria-label="Media workspace">
      <form className="url-form" onSubmit={analyze}>
        <label htmlFor="media-url">Video or audio link</label>
        <div className="url-control">
          <span aria-hidden="true">↗</span>
          <input
            id="media-url"
            type="url"
            required
            maxLength={2048}
            placeholder="Paste a YouTube or supported media URL"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <button type="submit" disabled={busy}>
            {busy && !job ? "Analyzing…" : "Analyze link"}
          </button>
        </div>
        <p>Your media is private and temporary. Nothing downloads before you choose an action.</p>
      </form>

      {error && (
        <div className="error-banner" role="alert">
          <strong>Couldn’t continue</strong>
          <span>{error}</span>
          {error.includes("disabled") && (
            <small>Remote analysis remains off until the backend network sandbox is enabled.</small>
          )}
        </div>
      )}

      {!analysis && !error && (
        <div className="workspace-empty">
          <div className="orbit" aria-hidden="true">
            <span>▶</span>
          </div>
          <h2>One analysis unlocks every action</h2>
          <p>Preview metadata, inspect available formats and choose what you want to make.</p>
        </div>
      )}

      {analysis && (
        <div className="workspace-content">
          <article className="media-card">
            <div
              className="thumbnail"
              role="img"
              aria-label={`Thumbnail for ${analysis.title}`}
              style={
                analysis.thumbnail_url
                  ? { backgroundImage: `linear-gradient(0deg, rgba(18,20,20,.25), transparent), url("${analysis.thumbnail_url}")` }
                  : undefined
              }
            >
              <span>{formatDuration(analysis.duration_seconds)}</span>
            </div>
            <div className="media-copy">
              <span className="source-badge">{analysis.extractor}</span>
              <h2>{analysis.title}</h2>
              <p>{analysis.author ?? "Unknown creator"}</p>
              <dl>
                <div>
                  <dt>Formats</dt>
                  <dd>{analysis.formats.length}</dd>
                </div>
                <div>
                  <dt>Subtitles</dt>
                  <dd>{analysis.subtitle_languages.length || "—"}</dd>
                </div>
              </dl>
            </div>
          </article>

          <div className="action-panel">
            <div className="panel-heading">
              <span>Choose what to make</span>
              <small>Simple mode</small>
            </div>
            <div className="action-grid">
              {actions.map((item) => {
                const available = availableActions.has(item.id);
                return (
                  <button
                    key={item.id}
                    className={action === item.id ? "action-card selected" : "action-card"}
                    disabled={!available}
                    onClick={() => setAction(item.id)}
                    type="button"
                  >
                    <b aria-hidden="true">{item.icon}</b>
                    <span>{item.label}</span>
                    <small>{available ? item.hint : "Not available"}</small>
                  </button>
                );
              })}
            </div>

            <ActionFields
              action={action}
              analysis={analysis}
              options={options}
              onChange={setOptions}
            />

            <button className="primary-action" type="button" onClick={createJob} disabled={busy}>
              {busy ? "Starting…" : `Create ${actions.find((item) => item.id === action)?.label} job`}
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      )}

      {job && <JobCard job={job} onCancel={cancelJob} />}
    </section>
  );
}

function ActionFields({
  action,
  analysis,
  options,
  onChange,
}: {
  action: MediaAction;
  analysis: MediaAnalysis;
  options: ActionOptions;
  onChange: (options: ActionOptions) => void;
}) {
  if (action === "download_video") {
    const qualities = availableVideoQualities(analysis.formats);
    const estimatedBytes = estimateVideoSize(
      analysis.formats,
      options.quality,
      options.container,
    );
    return (
      <>
        <div className="field-row">
          <SelectField
            label="Quality"
            value={options.quality}
            values={qualities}
            onChange={(quality) =>
              onChange({ ...options, quality: quality as ActionOptions["quality"] })
            }
          />
          <SelectField
            label="Container"
            value={options.container}
            values={["mp4", "webm", "mkv", "auto"]}
            onChange={(container) =>
              onChange({ ...options, container: container as ActionOptions["container"] })
            }
          />
        </div>
        <p className="size-estimate">
          Estimated download: <strong>{formatFileSize(estimatedBytes)}</strong>
          <span>Actual size may vary after merging streams.</span>
        </p>
      </>
    );
  }
  if (action === "extract_audio") {
    const estimatedBytes = estimateAudioSize(
      analysis.duration_seconds,
      options.codec,
      options.bitrate,
    );
    return (
      <>
        <div className="field-row">
          <SelectField
            label="Format"
            value={options.codec}
            values={["mp3", "m4a", "opus", "wav"]}
            onChange={(codec) => onChange({ ...options, codec: codec as ActionOptions["codec"] })}
          />
          <SelectField
            label="Bitrate"
            value={options.bitrate}
            values={["128", "192", "256", "320"]}
            disabled={options.codec === "wav"}
            onChange={(bitrate) =>
              onChange({ ...options, bitrate: bitrate as ActionOptions["bitrate"] })
            }
          />
        </div>
        <p className="size-estimate">
          Estimated download: <strong>{formatFileSize(estimatedBytes)}</strong>
          <span>Calculated from duration and output bitrate.</span>
        </p>
      </>
    );
  }
  return (
    <>
      <div className="field-row">
        <NumberField
          label="Start (seconds)"
          value={options.startSeconds}
          onChange={(startSeconds) => onChange({ ...options, startSeconds })}
        />
        <NumberField
          label="End (seconds)"
          value={options.endSeconds}
          onChange={(endSeconds) => onChange({ ...options, endSeconds })}
        />
      </div>
      {action === "create_gif" && (
        <div className="field-row">
          <SelectField
            label="Output"
            value={options.outputFormat}
            values={["gif", "webp", "mp4", "webm"]}
            onChange={(outputFormat) =>
              onChange({ ...options, outputFormat: outputFormat as ActionOptions["outputFormat"] })
            }
          />
          <SelectField
            label="Width"
            value={String(options.width)}
            values={["480", "640", "960", "1280"]}
            onChange={(width) => onChange({ ...options, width: Number(width) })}
          />
        </div>
      )}
    </>
  );
}

function SelectField({
  label,
  value,
  values,
  disabled = false,
  onChange,
}: {
  label: string;
  value: string;
  values: string[];
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {values.map((item) => (
          <option value={item} key={item}>
            {item.toUpperCase()}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min={0}
        step="0.1"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function JobCard({ job, onCancel }: { job: Job; onCancel: () => void }) {
  const terminal = terminalStatuses.has(job.status);
  const resultAvailable = isResultAvailable(job);
  return (
    <aside className={`job-card ${job.status}`} aria-live="polite">
      <div className="job-status">
        <span className="pulse" aria-hidden="true" />
        <div>
          <small>Job status</small>
          <strong>{job.status.replace("_", " ")}</strong>
        </div>
      </div>
      <div className="progress-track" aria-label={`${job.progress_percent}% complete`}>
        <span style={{ width: `${job.progress_percent}%` }} />
      </div>
      <b>{job.progress_percent}%</b>
      {!terminal && (
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      )}
      {job.error_message && <p>{job.error_message}</p>}
      {job.status === "succeeded" && resultAvailable && (
        <div className="result-ready">
          <p>
            Result ready
            {job.result_expires_at
              ? ` · expires ${new Date(job.result_expires_at).toLocaleString()}`
              : ""}
          </p>
          <a className="download-result" href={resultDownloadUrl(job.job_id)}>
            Download result
          </a>
        </div>
      )}
      {job.status === "succeeded" && !resultAvailable && (
        <p>The result has expired or is no longer available.</p>
      )}
    </aside>
  );
}
