import type { NextRequest } from "next/server";

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
    ]) {
      const value = response.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(response.body, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { error: { code: "backend_unavailable", message: "The media service is unavailable." } },
      { status: 503 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
