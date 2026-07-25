import type { NextRequest } from "next/server";

const backendOrigin = process.env.MEVAD_API_INTERNAL_URL ?? "http://127.0.0.1:8000";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
): Promise<Response> {
  const { path } = await context.params;
  const target = new URL(`/api/v1/${path.join("/")}`, backendOrigin);
  target.search = request.nextUrl.search;
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.text();
  try {
    const response = await fetch(target, {
      method: request.method,
      headers: {
        accept: "application/json",
        ...(body ? { "content-type": request.headers.get("content-type") ?? "application/json" } : {}),
      },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    return new Response(response.body, {
      status: response.status,
      headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
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
