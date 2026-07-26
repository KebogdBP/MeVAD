import type { NextRequest } from "next/server";

import { parseTelemetryEnvelope } from "@/lib/telemetry";
import { recordTelemetry } from "@/lib/telemetry-server";

const MAX_EVENT_BYTES = 8_192;

export async function POST(request: NextRequest): Promise<Response> {
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > MAX_EVENT_BYTES) {
    return Response.json({ error: "event_too_large" }, { status: 413 });
  }
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return Response.json({ error: "unsupported_media_type" }, { status: 415 });
  }

  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  if (
    (origin !== null && !hasMatchingOrigin(request, origin)) ||
    (fetchSite !== null && !["same-origin", "none"].includes(fetchSite))
  ) {
    return Response.json({ error: "cross_origin_event" }, { status: 403 });
  }

  const raw = await request.text();
  if (Buffer.byteLength(raw, "utf8") > MAX_EVENT_BYTES) {
    return Response.json({ error: "event_too_large" }, { status: 413 });
  }

  let input: unknown;
  try {
    input = JSON.parse(raw);
  } catch {
    return Response.json({ error: "invalid_event" }, { status: 400 });
  }

  const event = parseTelemetryEnvelope(input);
  if (!event) {
    return Response.json({ error: "invalid_event" }, { status: 400 });
  }

  recordTelemetry(event.name, event.route, event.properties);
  return new Response(null, {
    status: 204,
    headers: { "cache-control": "no-store" },
  });
}

function hasMatchingOrigin(request: NextRequest, origin: string): boolean {
  try {
    const originUrl = new URL(origin);
    const host =
      request.headers.get("x-forwarded-host") ??
      request.headers.get("host") ??
      request.nextUrl.host;
    const protocol = request.headers.get("x-forwarded-proto");
    return (
      originUrl.host === host &&
      (protocol === null || originUrl.protocol === `${protocol}:`) &&
      ["http:", "https:"].includes(originUrl.protocol)
    );
  } catch {
    return false;
  }
}
