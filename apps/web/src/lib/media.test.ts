import { describe, expect, it } from "vitest";
import { DEFAULT_OPTIONS, buildJobPayload, formatDuration, readApiError } from "./media";

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
});
