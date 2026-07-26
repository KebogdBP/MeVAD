import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { POST } from "./route";

const validEvent = {
  version: 1,
  name: "page_view",
  route: "/",
  properties: {},
};

describe("telemetry collector", () => {
  it("accepts a same-origin allowlisted event without setting cookies", async () => {
    const response = await POST(
      new NextRequest("https://mevad.app/api/telemetry", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          origin: "https://mevad.app",
          "sec-fetch-site": "same-origin",
        },
        body: JSON.stringify(validEvent),
      }),
    );

    expect(response.status).toBe(204);
    expect(response.headers.get("set-cookie")).toBeNull();
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  it("rejects cross-origin and non-allowlisted payloads", async () => {
    const crossOrigin = await POST(
      new NextRequest("https://mevad.app/api/telemetry", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          origin: "https://attacker.example",
          "sec-fetch-site": "cross-site",
        },
        body: JSON.stringify(validEvent),
      }),
    );
    const unsafePayload = await POST(
      new NextRequest("https://mevad.app/api/telemetry", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          origin: "https://mevad.app",
        },
        body: JSON.stringify({
          ...validEvent,
          properties: { source_url: "https://example.com/private" },
        }),
      }),
    );

    expect(crossOrigin.status).toBe(403);
    expect(unsafePayload.status).toBe(400);
  });

  it("rejects oversized events before processing", async () => {
    const response = await POST(
      new NextRequest("https://mevad.app/api/telemetry", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          origin: "https://mevad.app",
          "content-length": "9000",
        },
        body: JSON.stringify(validEvent),
      }),
    );

    expect(response.status).toBe(413);
  });
});
