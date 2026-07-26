const backendOrigin =
  process.env.MEVAD_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const response = await fetch(new URL("/health/ready", backendOrigin), {
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });
    const payload: unknown = await response.json();
    const apiReady =
      response.ok &&
      typeof payload === "object" &&
      payload !== null &&
      "status" in payload &&
      payload.status === "ready";

    return healthResponse(apiReady);
  } catch {
    return healthResponse(false);
  }
}

function healthResponse(apiReady: boolean): Response {
  return Response.json(
    {
      status: apiReady ? "ready" : "not_ready",
      checks: {
        web: true,
        api: apiReady,
      },
    },
    {
      status: apiReady ? 200 : 503,
      headers: {
        "cache-control": "no-store",
        "x-robots-tag": "noindex, nofollow",
      },
    },
  );
}
