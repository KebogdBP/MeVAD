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
  estimateLoopSize,
  formatDuration,
  estimateVideoSize,
  formatFileSize,
  isResultAvailable,
  outputDuration,
  readApiError,
  resultDownloadUrl,
  validateActionOptions,
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
  const actionError = useMemo(
    () => (analysis ? validateActionOptions(action, analysis, options) : null),
    [action, analysis, options],
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
    if (!analysis || actionError) return;
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
    <section
      className="workspace-shell"
      id="workspace"
      aria-label="Media workspace"
      aria-busy={busy}
    >
      <div className="workspace-bar">
        <div>
          <span className="workspace-step">01</span>
          <div>
            <strong>Start with a media link</strong>
            <small>Video, audio, clip or loop</small>
          </div>
        </div>
        <span className="workspace-secure"><i /> Secure workspace</span>
      </div>
      <form className="url-form" onSubmit={analyze}>
        <label htmlFor="media-url">Paste a supported URL</label>
        <div className="url-control">
          <span aria-hidden="true">⌁</span>
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
            {busy && !analysis ? "Analyzing…" : "Analyze"}
          </button>
        </div>
        <p>Nothing downloads before you choose an action.</p>
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
          <div className="preview-window" aria-hidden="true">
            <div className="preview-sky">
              <span className="preview-sun" />
              <i className="mountain mountain-back" />
              <i className="mountain mountain-front" />
              <b>▶</b>
            </div>
            <div className="preview-controls">
              <span>Ready for preview</span>
              <i><b /></i>
            </div>
          </div>
          <div className="empty-copy">
            <span>Choose after analysis</span>
            <h2>One link unlocks every action.</h2>
            <p>Preview metadata, inspect formats and create exactly what you need.</p>
          </div>
          <div className="empty-actions" aria-label="Available media actions">
            {actions.map((item) => (
              <span key={item.id}>
                <b aria-hidden="true">{item.icon}</b>
                {item.label}
              </span>
            ))}
          </div>
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
                    aria-pressed={action === item.id}
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

            {actionError && (
              <p className="field-error" role="alert">
                {actionError}
              </p>
            )}

            <button
              className="primary-action"
              type="button"
              onClick={createJob}
              disabled={busy || actionError !== null}
            >
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
  if (action === "cut_clip") {
    const duration = options.endSeconds - options.startSeconds;
    return (
      <>
        <div className="field-row">
          <NumberField
            label="Start (seconds)"
            value={options.startSeconds}
            max={analysis.duration_seconds ?? undefined}
            onChange={(startSeconds) => onChange({ ...options, startSeconds })}
          />
          <NumberField
            label="End (seconds)"
            value={options.endSeconds}
            max={analysis.duration_seconds ?? undefined}
            onChange={(endSeconds) => onChange({ ...options, endSeconds })}
          />
        </div>
        <div className="field-row single-field">
          <SelectField
            label="Cut mode"
            value={options.cutMode}
            values={["accurate", "fast"]}
            onChange={(cutMode) =>
              onChange({ ...options, cutMode: cutMode as ActionOptions["cutMode"] })
            }
          />
        </div>
        <div className="output-preview">
          <span>Output preview</span>
          <strong>{duration > 0 ? formatDuration(duration) : "Invalid interval"}</strong>
          <small>
            {options.cutMode === "fast"
              ? "Fast · starts near the closest keyframe · no re-encode"
              : "Accurate · precise boundaries · H.264/AAC re-encode"}
          </small>
        </div>
      </>
    );
  }

  const animated = options.outputFormat === "gif" || options.outputFormat === "webp";
  const fpsValues = animated ? ["10", "15", "24", "30"] : ["15", "24", "30", "60"];
  const estimatedBytes = estimateLoopSize(analysis, options);
  return (
    <>
      <div className="field-row">
        <NumberField
          label="Start (seconds)"
          value={options.startSeconds}
          max={analysis.duration_seconds ?? undefined}
          onChange={(startSeconds) => onChange({ ...options, startSeconds })}
        />
        <NumberField
          label="End (seconds)"
          value={options.endSeconds}
          max={analysis.duration_seconds ?? undefined}
          onChange={(endSeconds) => onChange({ ...options, endSeconds })}
        />
      </div>
      <div className="field-row">
        <SelectField
          label="Output"
          value={options.outputFormat}
          values={["gif", "webp", "mp4", "webm"]}
          onChange={(outputFormat) => {
            const nextFormat = outputFormat as ActionOptions["outputFormat"];
            onChange({
              ...options,
              outputFormat: nextFormat,
              fps:
                (nextFormat === "gif" || nextFormat === "webp") && options.fps > 30
                  ? 30
                  : options.fps,
            });
          }}
        />
        <SelectField
          label="Width"
          value={String(options.width)}
          values={["480", "640", "960", "1280"]}
          onChange={(width) => onChange({ ...options, width: Number(width) })}
        />
      </div>
      <div className="field-row">
        <SelectField
          label="Frame rate"
          value={String(options.fps)}
          values={fpsValues}
          onChange={(fps) => onChange({ ...options, fps: Number(fps) })}
        />
        <SelectField
          label="Quality"
          value={options.loopQuality}
          values={["small", "balanced", "high"]}
          onChange={(loopQuality) =>
            onChange({
              ...options,
              loopQuality: loopQuality as ActionOptions["loopQuality"],
            })
          }
        />
      </div>
      <div className="field-row">
        <SelectField
          label="Speed"
          value={options.speed}
          values={["0.5", "1", "1.5", "2"]}
          onChange={(speed) =>
            onChange({ ...options, speed: speed as ActionOptions["speed"] })
          }
        />
        <CheckboxField
          label="Repeat playback"
          checked={options.repeat}
          onChange={(repeat) => onChange({ ...options, repeat })}
        />
      </div>
      <div className="output-preview">
        <span>Output preview</span>
        <strong>
          {options.outputFormat.toUpperCase()} · {formatDuration(outputDuration(options))} ·{" "}
          {formatFileSize(estimatedBytes)}
        </strong>
        <small>
          {options.width}px · {options.fps} FPS · {options.loopQuality} quality ·{" "}
          {options.speed}× speed
        </small>
      </div>
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
  max,
  onChange,
}: {
  label: string;
  value: number;
  max?: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        type="number"
        min={0}
        max={max}
        step="0.1"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="checkbox-field">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>{label}</span>
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
      <div
        className="progress-track"
        role="progressbar"
        aria-label="Job progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={job.progress_percent}
      >
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
