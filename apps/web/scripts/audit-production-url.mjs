const publicPaths = [
  "/",
  "/video-downloader",
  "/audio-downloader",
  "/video-cutter",
  "/video-to-gif",
  "/how-it-works",
  "/supported-sites",
  "/privacy",
  "/terms",
  "/copyright",
];
const expectedHeaders = {
  "strict-transport-security": /max-age=\d+/i,
  "x-content-type-options": /^nosniff$/i,
  "x-frame-options": /^DENY$/i,
  "referrer-policy": /^strict-origin-when-cross-origin$/i,
  "permissions-policy": /camera=\(\).*microphone=\(\).*geolocation=\(\)/i,
};
const configuredOrigin = process.env.MEVAD_PRODUCTION_URL;

if (!configuredOrigin) {
  throw new Error("Set MEVAD_PRODUCTION_URL to the deployed HTTPS origin.");
}

const originUrl = new URL(configuredOrigin);
if (
  originUrl.protocol !== "https:" ||
  originUrl.pathname !== "/" ||
  originUrl.search ||
  originUrl.hash
) {
  throw new Error("MEVAD_PRODUCTION_URL must be an HTTPS origin without a path.");
}
const origin = originUrl.origin;
const failures = [];

async function request(pathname, init) {
  try {
    return await fetch(`${origin}${pathname}`, {
      ...init,
      signal: AbortSignal.timeout(15_000),
    });
  } catch (error) {
    failures.push({
      pathname,
      check: "request",
      error: error instanceof Error ? error.name : "UnknownError",
    });
    return null;
  }
}

for (const pathname of publicPaths) {
  const response = await request(pathname);
  if (!response) continue;
  const html = await response.text();
  const canonical = pathname === "/" ? `${origin}/` : `${origin}${pathname}`;
  const jsonLdBlocks = [
    ...html.matchAll(
      /<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/g,
    ),
  ];

  if (!response.ok) {
    failures.push({ pathname, check: "status", status: response.status });
  }
  if ((html.match(/<h1[\s>]/g) ?? []).length !== 1) {
    failures.push({ pathname, check: "single-h1" });
  }
  if (!html.includes(`<link rel="canonical" href="${canonical}"`)) {
    failures.push({ pathname, check: "canonical", expected: canonical });
  }
  if (!html.includes(`property="og:image" content="${origin}/og.png"`)) {
    failures.push({ pathname, check: "open-graph-image" });
  }
  if (jsonLdBlocks.length === 0) {
    failures.push({ pathname, check: "structured-data" });
  }
  for (const [, block] of jsonLdBlocks) {
    try {
      JSON.parse(block);
    } catch {
      failures.push({ pathname, check: "structured-data-json" });
    }
  }

  if (pathname === "/") {
    for (const [header, expected] of Object.entries(expectedHeaders)) {
      const value = response.headers.get(header) ?? "";
      if (!expected.test(value)) {
        failures.push({ pathname, check: `header:${header}`, actual: value });
      }
    }
    verifyOwnershipMeta(html);
  }
}

const health = await request("/api/health");
if (health) {
  const payload = await health.json().catch(() => null);
  if (!health.ok || payload?.status !== "ready") {
    failures.push({
      pathname: "/api/health",
      check: "readiness",
      status: health.status,
    });
  }
  if (health.headers.get("x-robots-tag") !== "noindex, nofollow") {
    failures.push({ pathname: "/api/health", check: "noindex" });
  }
}

const robots = await request("/robots.txt");
const sitemap = await request("/sitemap.xml");
if (robots && !(await robots.text()).includes(`Sitemap: ${origin}/sitemap.xml`)) {
  failures.push({ pathname: "/robots.txt", check: "sitemap-reference" });
}
if (sitemap) {
  const xml = await sitemap.text();
  for (const pathname of publicPaths) {
    const expected = pathname === "/" ? `${origin}/` : `${origin}${pathname}`;
    if (!xml.includes(`<loc>${expected}</loc>`)) {
      failures.push({ pathname: "/sitemap.xml", check: "route", expected });
    }
  }
}

await auditTelemetry();
await auditHttpRedirect();

if (failures.length > 0) {
  throw new Error(
    `Production launch audit failed:\n${JSON.stringify(failures, null, 2)}`,
  );
}

console.log(
  JSON.stringify(
    {
      status: "passed",
      origin,
      publicRoutes: publicPaths.length,
      checks: [
        "HTTPS redirect",
        "readiness",
        "security headers",
        "canonical and social metadata",
        "structured data JSON",
        "robots and sitemap",
        "webmaster verification metadata when configured",
        "telemetry privacy boundary",
      ],
    },
    null,
    2,
  ),
);

function verifyOwnershipMeta(html) {
  const google = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION;
  const bing = process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION;
  if (
    google &&
    !html.includes(`name="google-site-verification" content="${google}"`)
  ) {
    failures.push({ pathname: "/", check: "google-site-verification" });
  }
  if (bing && !html.includes(`name="msvalidate.01" content="${bing}"`)) {
    failures.push({ pathname: "/", check: "bing-site-verification" });
  }
}

async function auditTelemetry() {
  const validEvent = {
    version: 1,
    name: "page_view",
    route: "/",
    properties: {},
  };
  const valid = await request("/api/telemetry", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      origin,
      "sec-fetch-site": "same-origin",
    },
    body: JSON.stringify(validEvent),
  });
  const unsafe = await request("/api/telemetry", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      origin,
    },
    body: JSON.stringify({
      ...validEvent,
      properties: { source_url: "https://example.com/private" },
    }),
  });
  if (valid && (valid.status !== 204 || valid.headers.has("set-cookie"))) {
    failures.push({
      pathname: "/api/telemetry",
      check: "valid-cookie-free-event",
      status: valid.status,
    });
  }
  if (unsafe && unsafe.status !== 400) {
    failures.push({
      pathname: "/api/telemetry",
      check: "unsafe-event",
      status: unsafe.status,
    });
  }
}

async function auditHttpRedirect() {
  if (process.env.MEVAD_REQUIRE_HTTP_REDIRECT === "false") return;
  const httpUrl = new URL(origin);
  httpUrl.protocol = "http:";
  if (httpUrl.port === "443") httpUrl.port = "";
  try {
    const response = await fetch(httpUrl, {
      redirect: "manual",
      signal: AbortSignal.timeout(15_000),
    });
    const location = response.headers.get("location") ?? "";
    if (![301, 302, 307, 308].includes(response.status) || !location.startsWith(origin)) {
      failures.push({
        pathname: httpUrl.toString(),
        check: "https-redirect",
        status: response.status,
        location,
      });
    }
  } catch (error) {
    failures.push({
      pathname: httpUrl.toString(),
      check: "https-redirect-request",
      error: error instanceof Error ? error.name : "UnknownError",
    });
  }
}
