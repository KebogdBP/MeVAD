import { describe, expect, it } from "vitest";
import {
  DEFAULT_OPTIONS,
  buildJobPayload,
  formatDuration,
  isResultAvailable,
  readApiError,
  resultDownloadUrl,
} from "./media";

describe("media workflow helpers", () => {
  it("builds the backend clip operation from the analyzer action", () => {
    expect(buildJobPayload("cut_clip", "https://example.com/video", DEFAULT_OPTIONS)).toEqual({
      operation: "cut_video",
      source_url: "https://example.com/video",
      options: { start_seconds: 0, end_seconds: 10, mode: "accurate" },
    });
  });

  it("builds a bounded GIF job", () => {
    expect(buildJobPayload("create_gif", "https://example.com/video", DEFAULT_OPTIONS)).toEqual({
      operation: "make_loop",
      source_url: "https://example.com/video",
      options: {
        start_seconds: 0,
        end_seconds: 10,
        output_format: "gif",
        width: 640,
        fps: 15,
        quality: "balanced",
        speed: "1",
        repeat: true,
      },
    });
  });

  it("formats media duration and stable API errors", () => {
    expect(formatDuration(3723)).toBe("1:02:03");
    expect(readApiError({ error: { message: "Analyzer is disabled." } })).toBe(
      "Analyzer is disabled.",
    );
  });

  it("builds an encoded same-origin result URL", () => {
    expect(resultDownloadUrl("job/with spaces")).toBe(
      "/api/backend/jobs/job%2Fwith%20spaces/result",
    );
  });

  it("only offers a live, retained completed result", () => {
    const job = {
      job_id: "job-1",
      operation: "download_video" as const,
      source_url: "https://example.com/video",
      status: "succeeded" as const,
      progress_percent: 100,
      result_reference: "job-1/results/video.mp4",
      result_expires_at: "2026-07-26T12:01:00Z",
      storage_deleted_at: null,
      error_code: null,
      error_message: null,
    };

    expect(isResultAvailable(job, Date.parse("2026-07-26T12:00:00Z"))).toBe(true);
    expect(isResultAvailable(job, Date.parse("2026-07-26T12:01:00Z"))).toBe(false);
    expect(isResultAvailable({ ...job, result_reference: null }, 0)).toBe(false);
  });
});
