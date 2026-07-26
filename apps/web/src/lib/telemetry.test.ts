import { describe, expect, it } from "vitest";

import {
  normalizeTelemetryRoute,
  parseTelemetryEnvelope,
  safeErrorName,
} from "@/lib/telemetry";

describe("privacy-conscious telemetry contract", () => {
  it("accepts only the exact allowlisted event shape", () => {
    expect(
      parseTelemetryEnvelope({
        version: 1,
        name: "analysis_succeeded",
        route: "/",
        properties: {
          duration_ms: 1200,
          available_actions: 4,
        },
      }),
    ).toEqual({
      version: 1,
      name: "analysis_succeeded",
      route: "/",
      properties: {
        duration_ms: 1200,
        available_actions: 4,
      },
    });
  });

  it("rejects identifiers, media URLs and arbitrary error details", () => {
    for (const properties of [
      { source_url: "https://example.com/watch?v=secret" },
      { user_id: "visitor-123" },
      { message: "Failed for https://example.com/private" },
      { stack: "Error at media URL" },
    ]) {
      expect(
        parseTelemetryEnvelope({
          version: 1,
          name: "page_view",
          route: "/",
          properties,
        }),
      ).toBeNull();
    }
  });

  it("rejects query strings and normalizes unknown paths", () => {
    expect(normalizeTelemetryRoute("/privacy?token=secret")).toBe("/privacy");
    expect(normalizeTelemetryRoute("/jobs/private-job-id")).toBe("/other");
    expect(
      parseTelemetryEnvelope({
        version: 1,
        name: "page_view",
        route: "/privacy?token=secret",
        properties: {},
      }),
    ).toBeNull();
  });

  it("bounds performance values and enumerated dimensions", () => {
    expect(
      parseTelemetryEnvelope({
        version: 1,
        name: "web_vital",
        route: "/video-downloader",
        properties: {
          metric: "LCP",
          rating: "good",
          value: 1800,
          navigation_type: "navigate",
        },
      }),
    ).not.toBeNull();
    expect(
      parseTelemetryEnvelope({
        version: 1,
        name: "web_vital",
        route: "/video-downloader",
        properties: {
          metric: "memory",
          rating: "excellent",
          value: Number.POSITIVE_INFINITY,
          navigation_type: "navigate",
        },
      }),
    ).toBeNull();
  });

  it("keeps only safe error class names", () => {
    expect(safeErrorName(new TypeError("private URL"))).toBe("TypeError");
    expect(safeErrorName({ name: "https://example.com/private" })).toBe(
      "UnknownError",
    );
    expect(safeErrorName("raw failure message")).toBe("UnknownError");
  });
});
