import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("web readiness endpoint", () => {
  it("reports ready only when the API is ready", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ status: "ready", checks: {} }),
    );

    const response = await GET();

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      status: "ready",
      checks: { web: true, api: true },
    });
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("x-robots-tag")).toBe("noindex, nofollow");
  });

  it("reports not ready for an unhealthy or malformed API response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ status: "not_ready" }, { status: 503 }),
    );

    const response = await GET();

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      status: "not_ready",
      checks: { web: true, api: false },
    });
  });

  it("fails closed when the API cannot be reached", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("offline"));

    expect((await GET()).status).toBe(503);
  });
});
