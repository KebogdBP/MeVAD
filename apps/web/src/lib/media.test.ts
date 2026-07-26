import { describe, expect, it } from "vitest";
import {
  DEFAULT_OPTIONS,
  availableVideoQualities,
  buildJobPayload,
  estimateAudioSize,
  estimateLoopSize,
  estimateVideoSize,
  formatDuration,
  formatFileSize,
  isResultAvailable,
  outputDuration,
  readApiError,
  resultDownloadUrl,
  validateActionOptions,
} from "./media";

describe("media workflow helpers", () => {
  const formats = [
    {
      format_id: "video-1080",
      extension: "mp4",
      width: 1920,
      height: 1080,
      filesize_bytes: 100 * 1024 * 1024,
      has_video: true,
      has_audio: false,
    },
    {
      format_id: "video-720",
      extension: "mp4",
      width: 1280,
      height: 720,
      filesize_bytes: 60 * 1024 * 1024,
      has_video: true,
      has_audio: false,
    },
    {
      format_id: "audio",
      extension: "m4a",
      width: null,
      height: null,
      filesize_bytes: 10 * 1024 * 1024,
      has_video: false,
      has_audio: true,
    },
  ];

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

  it("offers only quality presets present in analyzer formats", () => {
    expect(availableVideoQualities(formats)).toEqual(["best", "1080p", "720p"]);
  });

  it("estimates selected video and audio streams without claiming precision", () => {
    expect(estimateVideoSize(formats, "720p", "mp4")).toBe(70 * 1024 * 1024);
    expect(formatFileSize(70 * 1024 * 1024)).toBe("≈ 70.0 MB");
    expect(formatFileSize(null)).toBe("Size unavailable");
  });

  it("estimates compressed audio and ignores bitrate for WAV", () => {
    expect(estimateAudioSize(60, "mp3", "192")).toBe(1_440_000);
    expect(estimateAudioSize(60, "wav", "128")).toBe(10_584_000);
    expect(estimateAudioSize(null, "mp3", "192")).toBeNull();
  });

  it("validates clip bounds against the analyzed source", () => {
    const analysis = {
      source_url: "https://example.com/video",
      extractor: "Example",
      media_id: "video-1",
      title: "Video",
      author: null,
      duration_seconds: 20,
      thumbnail_url: null,
      webpage_url: "https://example.com/video",
      is_playlist: false,
      playlist_entry_count: null,
      formats,
      subtitle_languages: [],
      available_actions: ["cut_clip"],
    };

    expect(
      validateActionOptions("cut_clip", analysis, {
        ...DEFAULT_OPTIONS,
        startSeconds: 10,
        endSeconds: 5,
      }),
    ).toBe("End must be greater than start.");
    expect(
      validateActionOptions("cut_clip", analysis, {
        ...DEFAULT_OPTIONS,
        endSeconds: 21,
      }),
    ).toContain("source duration");
  });

  it("enforces animated limits and estimates loop preview metadata", () => {
    const analysis = {
      source_url: "https://example.com/video",
      extractor: "Example",
      media_id: "video-1",
      title: "Video",
      author: null,
      duration_seconds: 60,
      thumbnail_url: null,
      webpage_url: "https://example.com/video",
      is_playlist: false,
      playlist_entry_count: null,
      formats,
      subtitle_languages: [],
      available_actions: ["create_gif"],
    };
    const options = {
      ...DEFAULT_OPTIONS,
      endSeconds: 40,
      speed: "2" as const,
    };

    expect(validateActionOptions("create_gif", analysis, options)).toBe(
      "GIF and WebP clips cannot exceed 30 seconds.",
    );
    expect(outputDuration(options)).toBe(20);
    expect(
      estimateLoopSize(analysis, { ...options, endSeconds: 20 }),
    ).toBeGreaterThan(0);
  });

  it("builds selected cut and loop controls into job payloads", () => {
    expect(
      buildJobPayload("cut_clip", "https://example.com/video", {
        ...DEFAULT_OPTIONS,
        cutMode: "fast",
      }),
    ).toMatchObject({ options: { mode: "fast" } });
    expect(
      buildJobPayload("create_gif", "https://example.com/video", {
        ...DEFAULT_OPTIONS,
        loopQuality: "high",
        speed: "1.5",
        repeat: false,
      }),
    ).toMatchObject({
      options: { quality: "high", speed: "1.5", repeat: false },
    });
  });
});
