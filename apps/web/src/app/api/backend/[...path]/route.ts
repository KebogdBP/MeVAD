import type { NextRequest } from "next/server";

import { recordTelemetry } from "@/lib/telemetry-server";

const backendOrigin = process.env.MEVAD_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  const target = new URL(`/api/v1/${path.join("/")}`, backendOrigin);
  target.search = request.nextUrl.search;
  const isResultDownload = request.method === "GET" && path.at(-1) === "result";
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  try {
    const response = await fetch(target, {
      method: request.method,
      headers: {
        accept: request.headers.get("accept") ?? "application/json",
        ...(request.headers.get("x-forwarded-for")
          ? { "x-forwarded-for": request.headers.get("x-forwarded-for")! }
          : {}),
        ...(request.headers.get("x-request-id")
          ? { "x-request-id": request.headers.get("x-request-id")! }
          : {}),
        ...(body ? { "content-type": request.headers.get("content-type") ?? "application/json" } : {}),
      },
      body,
      cache: "no-store",
      signal: isResultDownload ? undefined : AbortSignal.timeout(30_000),
    });
    const responseHeaders = new Headers();
    for (const name of [
      "cache-control",
      "content-disposition",
      "content-length",
      "content-type",
      "x-content-type-options",
      "retry-after",
      "x-ratelimit-limit",
      "x-ratelimit-remaining",
      "x-request-id",
    ]) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    if (response.status >= 500) {
      recordTelemetry("api_proxy_failed", "/", {
        operation: telemetryOperation(path),
        status_class: "5xx",
      });
    }
    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    recordTelemetry("api_proxy_failed", "/", {
      operation: telemetryOperation(path),
      status_class: "network",
    });
    return Response.json(
      { error: { code: "backend_unavailable", message: "The media service is unavailable." } },
      { status: 503 },
    );
  }
}

function telemetryOperation(path: string[]): string {
  if (path[0] === "media" && path[1] === "analyze") return "analyze";
  if (path[0] !== "jobs") return "unknown";
  if (path.length === 1) return "create-job";
  if (path.at(-1) === "cancel") return "cancel-job";
  if (path.at(-1) === "result") return "result";
  return "job-status";
}

export const GET = proxy;
export const POST = proxy;
