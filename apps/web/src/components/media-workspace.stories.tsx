import type { Meta, StoryObj } from "@storybook/nextjs-vite";

import { MediaWorkspaceView } from "./media-workspace-view";
import {
  type ActionOptions,
  DEFAULT_OPTIONS,
  type Job,
  type MediaAnalysis,
} from "@/lib/media";

const analysis: MediaAnalysis = {
  source_url: "https://example.com/watch?v=mevad",
  extractor: "Demo source",
  media_id: "mevad-demo",
  title: "A calm mountain workspace demo",
  author: "MeVAD Studio",
  duration_seconds: 125,
  thumbnail_url: null,
  webpage_url: "https://example.com/watch?v=mevad",
  is_playlist: false,
  playlist_entry_count: null,
  formats: [
    {
      format_id: "1080",
      extension: "mp4",
      width: 1920,
      height: 1080,
      filesize_bytes: 48_000_000,
      has_video: true,
      has_audio: true,
    },
    {
      format_id: "720",
      extension: "mp4",
      width: 1280,
      height: 720,
      filesize_bytes: 24_000_000,
      has_video: true,
      has_audio: true,
    },
  ],
  subtitle_languages: ["en", "de"],
  available_actions: [
    "download_video",
    "extract_audio",
    "cut_clip",
    "create_gif",
  ],
};

const availableActions = new Set(analysis.available_actions);
const noop = () => undefined;

function job(
  status: Job["status"],
  progressPercent: number,
  overrides: Partial<Job> = {},
): Job {
  return {
    job_id: "storybook-job",
    operation: "download_video",
    source_url: analysis.source_url,
    status,
    progress_percent: progressPercent,
    result_reference: null,
    result_expires_at: null,
    storage_deleted_at: null,
    error_code: null,
    error_message: null,
    ...overrides,
  };
}

const meta = {
  title: "Patterns/Media Workspace States",
  component: MediaWorkspaceView,
  parameters: {
    layout: "fullscreen",
  },
  decorators: [
    (Story) => (
      <main className="storybook-workspace-stage">
        <Story />
      </main>
    ),
  ],
  args: {
    url: "https://example.com/watch?v=mevad",
    analysis: null,
    action: "download_video",
    options: DEFAULT_OPTIONS,
    job: null,
    operation: null,
    error: null,
    availableActions,
    actionError: null,
    onUrlChange: noop,
    onAnalyze: noop,
    onActionChange: noop,
    onOptionsChange: noop,
    onCreateJob: noop,
    onCancelJob: noop,
  },
  argTypes: {
    availableActions: { control: false },
  },
} satisfies Meta<typeof MediaWorkspaceView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};

export const Analyzing: Story = {
  args: {
    operation: "analyzing",
  },
};

export const Analyzed: Story = {
  args: {
    analysis,
  },
};

export const ValidationError: Story = {
  args: {
    analysis,
    action: "cut_clip",
    options: {
      ...DEFAULT_OPTIONS,
      startSeconds: 30,
      endSeconds: 10,
    } satisfies ActionOptions,
    actionError: "End must be greater than start.",
  },
};

export const StartingJob: Story = {
  args: {
    analysis,
    operation: "creating-job",
  },
};

export const Processing: Story = {
  args: {
    analysis,
    job: job("processing", 64),
  },
};

export const Failed: Story = {
  args: {
    analysis,
    job: job("failed", 42, {
      error_code: "conversion_failed",
      error_message: "The source stream could not be converted.",
    }),
  },
};

export const Succeeded: Story = {
  args: {
    analysis,
    job: job("succeeded", 100, {
      result_reference: "results/storybook-job.mp4",
      result_expires_at: "2099-12-31T23:59:59Z",
    }),
  },
};
