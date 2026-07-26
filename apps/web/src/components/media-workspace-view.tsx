import type { FormEvent } from "react";

import {
  MEDIA_ACTIONS,
  TERMINAL_JOB_STATUSES,
  getJobStatusPresentation,
  type WorkspaceOperation,
} from "@/components/media-workspace-model";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChoiceCard } from "@/components/ui/choice-card";
import {
  CheckboxField,
  Input,
  NumberField,
  SelectField,
} from "@/components/ui/field";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  type ActionOptions,
  type Job,
  type MediaAction,
  type MediaAnalysis,
  availableVideoQualities,
  estimateAudioSize,
  estimateLoopSize,
  estimateVideoSize,
  formatDuration,
  formatFileSize,
  isResultAvailable,
  outputDuration,
  resultDownloadUrl,
} from "@/lib/media";

export interface MediaWorkspaceViewProps {
  url: string;
  analysis: MediaAnalysis | null;
  action: MediaAction;
  options: ActionOptions;
  job: Job | null;
  operation: WorkspaceOperation;
  error: string | null;
  availableActions: ReadonlySet<string>;
  actionError: string | null;
  onUrlChange: (url: string) => void;
  onAnalyze: () => void | Promise<void>;
  onActionChange: (action: MediaAction) => void;
  onOptionsChange: (options: ActionOptions) => void;
  onCreateJob: () => void | Promise<void>;
  onCancelJob: () => void | Promise<void>;
}

export function MediaWorkspaceView({
  url,
  analysis,
  action,
  options,
  job,
  operation,
  error,
  availableActions,
  actionError,
  onUrlChange,
  onAnalyze,
  onActionChange,
  onOptionsChange,
  onCreateJob,
  onCancelJob,
}: MediaWorkspaceViewProps) {
  const analyzing = operation === "analyzing";
  const creatingJob = operation === "creating-job";
  const busy = operation !== null;

  function submitAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onAnalyze();
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
        <span className="workspace-secure">
          <i /> Secure workspace
        </span>
      </div>

      <form className="url-form" onSubmit={submitAnalysis}>
        <label htmlFor="media-url">Paste a supported URL</label>
        <div className="url-control">
          <span aria-hidden="true">⌁</span>
          <Input
            id="media-url"
            className="url-input"
            type="url"
            required
            maxLength={2048}
            autoComplete="url"
            inputMode="url"
            placeholder="Paste a YouTube or supported media URL"
            value={url}
            onChange={(event) => onUrlChange(event.target.value)}
          />
          <Button
            type="submit"
            variant="primary"
            disabled={busy}
            loading={analyzing}
            loadingLabel="Analyzing…"
            aria-controls="workspace-results"
          >
            Analyze
          </Button>
        </div>
        <p>Nothing downloads before you choose an action.</p>
      </form>

      {error && <WorkspaceError message={error} />}

      <div id="workspace-results">
        {analyzing ? (
          <AnalysisSkeleton />
        ) : analysis ? (
          <WorkspaceContent
            analysis={analysis}
            action={action}
            options={options}
            availableActions={availableActions}
            actionError={actionError}
            creatingJob={creatingJob}
            onActionChange={onActionChange}
            onOptionsChange={onOptionsChange}
            onCreateJob={onCreateJob}
          />
        ) : (
          !error && <WorkspaceEmpty />
        )}

        {creatingJob && <JobSkeleton />}
        {job && !creatingJob && (
          <JobCard
            job={job}
            cancelling={operation === "cancelling-job"}
            onCancel={onCancelJob}
          />
        )}
      </div>
    </section>
  );
}

function WorkspaceError({ message }: { message: string }) {
  const networkDisabled = message.toLowerCase().includes("disabled");

  return (
    <div className="error-banner" role="alert">
      <strong>We couldn’t continue</strong>
      <span>{message}</span>
      {networkDisabled && (
        <small>
          Remote analysis remains unavailable until backend network access is
          enabled.
        </small>
      )}
    </div>
  );
}

function WorkspaceEmpty() {
  return (
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
          <i>
            <b />
          </i>
        </div>
      </div>
      <div className="empty-copy">
        <span>Choose after analysis</span>
        <h2>One link unlocks every action.</h2>
        <p>
          Preview metadata, inspect formats and create exactly what you need.
        </p>
      </div>
      <div className="empty-actions" aria-label="Available media actions">
        {MEDIA_ACTIONS.map((item) => (
          <span key={item.id}>
            <b aria-hidden="true">{item.icon}</b>
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function AnalysisSkeleton() {
  return (
    <div className="workspace-loading" role="status" aria-live="polite">
      <span className="sr-only">Analyzing media and loading available actions.</span>
      <div className="skeleton-media-card">
        <Skeleton className="skeleton-thumbnail" />
        <div>
          <Skeleton width="30%" />
          <Skeleton width="82%" />
          <Skeleton width="55%" />
        </div>
      </div>
      <div className="skeleton-action-panel">
        <Skeleton width="42%" />
        <div className="skeleton-action-grid">
          {MEDIA_ACTIONS.map((item) => (
            <Skeleton key={item.id} />
          ))}
        </div>
        <Skeleton className="skeleton-control" />
        <Skeleton className="skeleton-control" />
      </div>
    </div>
  );
}

function JobSkeleton() {
  return (
    <div className="job-card job-card--loading" role="status" aria-live="polite">
      <span className="sr-only">Starting media job.</span>
      <Skeleton width="110px" />
      <Skeleton className="skeleton-progress" />
      <Skeleton width="34px" />
    </div>
  );
}

interface WorkspaceContentProps {
  analysis: MediaAnalysis;
  action: MediaAction;
  options: ActionOptions;
  availableActions: ReadonlySet<string>;
  actionError: string | null;
  creatingJob: boolean;
  onActionChange: (action: MediaAction) => void;
  onOptionsChange: (options: ActionOptions) => void;
  onCreateJob: () => void | Promise<void>;
}

function WorkspaceContent({
  analysis,
  action,
  options,
  availableActions,
  actionError,
  creatingJob,
  onActionChange,
  onOptionsChange,
  onCreateJob,
}: WorkspaceContentProps) {
  const actionLabel =
    MEDIA_ACTIONS.find((item) => item.id === action)?.label ?? "media";

  return (
    <div className="workspace-content">
      <article className="media-card">
        <div
          className="thumbnail"
          role="img"
          aria-label={`Thumbnail for ${analysis.title}`}
          style={
            analysis.thumbnail_url
              ? {
                  backgroundImage: `linear-gradient(0deg, rgba(18,20,20,.25), transparent), url("${analysis.thumbnail_url}")`,
                }
              : undefined
          }
        >
          <span>{formatDuration(analysis.duration_seconds)}</span>
        </div>
        <div className="media-copy">
          <Badge tone="accent" className="source-badge">
            {analysis.extractor}
          </Badge>
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
          <Badge tone="success">Simple mode</Badge>
        </div>
        <div className="action-grid" aria-label="Media action">
          {MEDIA_ACTIONS.map((item) => {
            const available = availableActions.has(item.id);
            return (
              <ChoiceCard
                key={item.id}
                selected={action === item.id}
                icon={item.icon}
                label={item.label}
                description={available ? item.hint : "Not available"}
                disabled={!available || creatingJob}
                onClick={() => onActionChange(item.id)}
              />
            );
          })}
        </div>

        <ActionFields
          action={action}
          analysis={analysis}
          options={options}
          onChange={onOptionsChange}
        />

        {actionError && (
          <p className="field-error" role="alert">
            {actionError}
          </p>
        )}

        <Button
          className="primary-action"
          variant="primary"
          size="lg"
          type="button"
          onClick={() => void onCreateJob()}
          disabled={creatingJob || actionError !== null}
          loading={creatingJob}
          loadingLabel="Starting job…"
        >
          <span>{`Create ${actionLabel} job`}</span>
          <span aria-hidden="true">→</span>
        </Button>
      </div>
    </div>
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
              onChange({
                ...options,
                quality: quality as ActionOptions["quality"],
              })
            }
          />
          <SelectField
            label="Container"
            value={options.container}
            values={["mp4", "webm", "mkv", "auto"]}
            onChange={(container) =>
              onChange({
                ...options,
                container: container as ActionOptions["container"],
              })
            }
          />
        </div>
        <SizeEstimate
          value={estimatedBytes}
          detail="Actual size may vary after merging streams."
        />
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
            onChange={(codec) =>
              onChange({
                ...options,
                codec: codec as ActionOptions["codec"],
              })
            }
          />
          <SelectField
            label="Bitrate"
            value={options.bitrate}
            values={["128", "192", "256", "320"]}
            disabled={options.codec === "wav"}
            onChange={(bitrate) =>
              onChange({
                ...options,
                bitrate: bitrate as ActionOptions["bitrate"],
              })
            }
          />
        </div>
        <SizeEstimate
          value={estimatedBytes}
          detail="Calculated from duration and output bitrate."
        />
      </>
    );
  }

  if (action === "cut_clip") {
    const duration = options.endSeconds - options.startSeconds;
    return (
      <>
        <TimeRangeFields
          analysis={analysis}
          options={options}
          onChange={onChange}
        />
        <div className="field-row single-field">
          <SelectField
            label="Cut mode"
            value={options.cutMode}
            values={["accurate", "fast"]}
            onChange={(cutMode) =>
              onChange({
                ...options,
                cutMode: cutMode as ActionOptions["cutMode"],
              })
            }
          />
        </div>
        <div className="output-preview">
          <span>Output preview</span>
          <strong>
            {duration > 0 ? formatDuration(duration) : "Invalid interval"}
          </strong>
          <small>
            {options.cutMode === "fast"
              ? "Fast · closest keyframe · no re-encode"
              : "Accurate · precise boundaries · H.264/AAC re-encode"}
          </small>
        </div>
      </>
    );
  }

  const animated =
    options.outputFormat === "gif" || options.outputFormat === "webp";
  const fpsValues = animated
    ? ["10", "15", "24", "30"]
    : ["15", "24", "30", "60"];
  const estimatedBytes = estimateLoopSize(analysis, options);

  return (
    <>
      <TimeRangeFields
        analysis={analysis}
        options={options}
        onChange={onChange}
      />
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
                (nextFormat === "gif" || nextFormat === "webp") &&
                options.fps > 30
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
            onChange({
              ...options,
              speed: speed as ActionOptions["speed"],
            })
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
          {options.outputFormat.toUpperCase()} ·{" "}
          {formatDuration(outputDuration(options))} ·{" "}
          {formatFileSize(estimatedBytes)}
        </strong>
        <small>
          {options.width}px · {options.fps} FPS · {options.loopQuality} quality
          · {options.speed}× speed
        </small>
      </div>
    </>
  );
}

function TimeRangeFields({
  analysis,
  options,
  onChange,
}: {
  analysis: MediaAnalysis;
  options: ActionOptions;
  onChange: (options: ActionOptions) => void;
}) {
  return (
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
  );
}

function SizeEstimate({
  value,
  detail,
}: {
  value: number | null;
  detail: string;
}) {
  return (
    <p className="size-estimate">
      Estimated download: <strong>{formatFileSize(value)}</strong>
      <span>{detail}</span>
    </p>
  );
}

function JobCard({
  job,
  cancelling,
  onCancel,
}: {
  job: Job;
  cancelling: boolean;
  onCancel: () => void | Promise<void>;
}) {
  const terminal = TERMINAL_JOB_STATUSES.has(job.status);
  const resultAvailable = isResultAvailable(job);
  const status = getJobStatusPresentation(job.status);

  return (
    <aside
      className={`job-card ${job.status}`}
      aria-live="polite"
      aria-label="Media job status"
    >
      <div className="job-status">
        <span className="pulse" aria-hidden="true" />
        <div>
          <small>Job status</small>
          <Badge tone={status.tone}>{status.label}</Badge>
        </div>
      </div>
      <div className="job-progress">
        <Progress value={job.progress_percent} label="Job progress" />
        <small>{status.detail}</small>
      </div>
      <b>{job.progress_percent}%</b>
      {!terminal && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          loading={cancelling}
          loadingLabel="Cancelling…"
          onClick={() => void onCancel()}
        >
          Cancel
        </Button>
      )}
      {job.error_message && (
        <p className="job-error" role="alert">
          {job.error_message}
        </p>
      )}
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
