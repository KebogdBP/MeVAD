import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  getJobStatusPresentation,
  workspaceErrorMessage,
} from "./media-workspace-model";
import { MediaWorkspaceView } from "./media-workspace-view";
import { DEFAULT_OPTIONS, type Job } from "@/lib/media";

const noop = () => undefined;

const baseProps = {
  url: "",
  analysis: null,
  action: "download_video" as const,
  options: DEFAULT_OPTIONS,
  job: null,
  operation: null,
  error: null,
  availableActions: new Set<string>(),
  actionError: null,
  onUrlChange: noop,
  onAnalyze: noop,
  onActionChange: noop,
  onOptionsChange: noop,
  onCreateJob: noop,
  onCancelJob: noop,
};

describe("MediaWorkspaceView", () => {
  it("renders a stable analysis loading state", () => {
    const markup = renderToStaticMarkup(
      <MediaWorkspaceView {...baseProps} operation="analyzing" />,
    );

    expect(markup).toContain('aria-busy="true"');
    expect(markup).toContain("Analyzing media and loading available actions.");
    expect(markup).toContain("skeleton-action-grid");
    expect(markup).not.toContain("One link unlocks every action.");
  });

  it("announces errors with consistent copy", () => {
    const markup = renderToStaticMarkup(
      <MediaWorkspaceView
        {...baseProps}
        error="The media URL is not supported."
      />,
    );

    expect(markup).toContain('role="alert"');
    expect(markup).toContain("We couldn’t continue");
    expect(markup).toContain("The media URL is not supported.");
  });
});

describe("workspace presentation helpers", () => {
  it.each([
    ["queued", "Queued", "neutral"],
    ["processing", "Processing", "warning"],
    ["succeeded", "Ready", "success"],
    ["failed", "Failed", "danger"],
  ] satisfies Array<[Job["status"], string, string]>)(
    "maps %s into predictable status copy",
    (status, label, tone) => {
      expect(getJobStatusPresentation(status)).toMatchObject({ label, tone });
    },
  );

  it("uses actionable fallbacks for unknown failures", () => {
    expect(workspaceErrorMessage("offline", "Try again.")).toBe("Try again.");
    expect(workspaceErrorMessage(new Error("Network unavailable"), "Try again.")).toBe(
      "Network unavailable",
    );
  });
});
