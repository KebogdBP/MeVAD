import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";

import { chromium } from "playwright";

const thresholds = {
  mobile: {
    performance: 0.5,
    accessibility: 1,
    "best-practices": 0.9,
    seo: 0.9,
  },
  desktop: {
    performance: 0.75,
    accessibility: 1,
    "best-practices": 0.9,
    seo: 0.9,
  },
};
const publicPaths = [
  "/",
  "/video-downloader",
  "/audio-downloader",
  "/video-cutter",
  "/video-to-gif",
];
const publicOrigin = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://mevad.app"
).replace(/\/$/, "");

const browserPath = [
  process.env.CHROME_PATH,
  chromium.executablePath(),
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((candidate) => candidate && existsSync(candidate));

if (!browserPath) {
  throw new Error(
    "No Chromium browser found. Run `npx playwright install chromium` first.",
  );
}

async function freePort() {
  const server = createServer();
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
  if (!address || typeof address === "string") {
    throw new Error("Unable to allocate a local audit port.");
  }
  return address.port;
}

async function waitForApplication(url, process, output) {
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (process.exitCode !== null) {
      throw new Error(`Next.js exited before the audit started.\n${output()}`);
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The production server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${url}.\n${output()}`);
}

async function stopProcess(process) {
  if (process.exitCode !== null) return;
  process.kill("SIGTERM");
  await Promise.race([
    new Promise((resolve) => process.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 3_000)),
  ]);
  if (process.exitCode === null) process.kill("SIGKILL");
}

async function launchAuditBrowser(profileDirectory) {
  const port = await freePort();
  let output = "";
  const process = spawn(
    browserPath,
    [
      "--headless=new",
      "--no-sandbox",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${profileDirectory}`,
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );
  process.stdout.on("data", (chunk) => {
    output += chunk;
  });
  process.stderr.on("data", (chunk) => {
    output += chunk;
  });

  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (process.exitCode !== null) {
      throw new Error(`Chromium exited before Lighthouse connected.\n${output}`);
    }
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return { process, port };
    } catch {
      // The remote debugging endpoint is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  await stopProcess(process);
  throw new Error(`Timed out waiting for Chromium.\n${output}`);
}

async function runLighthouse({ url, mode, reportPath, browserPort }) {
  const lighthouseCli = path.resolve("node_modules/lighthouse/cli/index.js");
  const argumentsList = [
    lighthouseCli,
    url,
    "--quiet",
    "--output=json",
    `--output-path=${reportPath}`,
    "--only-categories=performance,accessibility,best-practices,seo",
    `--port=${browserPort}`,
    mode === "desktop" ? "--preset=desktop" : "--form-factor=mobile",
  ];

  let output = "";
  const audit = spawn(process.execPath, argumentsList, {
    cwd: process.cwd(),
    env: process.env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  audit.stdout.on("data", (chunk) => {
    output += chunk;
  });
  audit.stderr.on("data", (chunk) => {
    output += chunk;
  });

  const exitCode = await new Promise((resolve) => audit.once("exit", resolve));
  if (exitCode !== 0) {
    throw new Error(`Lighthouse ${mode} audit failed.\n${output}`);
  }

  const report = JSON.parse(await readFile(reportPath, "utf8"));
  const scores = Object.fromEntries(
    Object.keys(thresholds[mode]).map((category) => [
      category,
      report.categories[category]?.score ?? 0,
    ]),
  );
  const metrics = Object.fromEntries(
    [
      "first-contentful-paint",
      "largest-contentful-paint",
      "speed-index",
      "total-blocking-time",
      "cumulative-layout-shift",
    ].map((auditId) => [
      auditId,
      report.audits[auditId]?.displayValue ?? "n/a",
    ]),
  );
  return { scores, metrics };
}

async function auditSeoRoutes(origin) {
  const failures = [];

  for (const pathname of publicPaths) {
    const response = await fetch(`${origin}${pathname}`);
    const html = await response.text();
    const canonical =
      pathname === "/" ? publicOrigin : `${publicOrigin}${pathname}`;
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
    if (!/<title>[^<]{20,}<\/title>/.test(html)) {
      failures.push({ pathname, check: "title" });
    }
    if (!/<meta name="description" content="[^"]{80,}"/.test(html)) {
      failures.push({ pathname, check: "description" });
    }
    if (!html.includes(`<link rel="canonical" href="${canonical}"`)) {
      failures.push({ pathname, check: "canonical", expected: canonical });
    }
    if (!html.includes(`property="og:image" content="${publicOrigin}/og.png"`)) {
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
  }

  const robots = await (await fetch(`${origin}/robots.txt`)).text();
  const sitemap = await (await fetch(`${origin}/sitemap.xml`)).text();
  if (!robots.includes(`Sitemap: ${publicOrigin}/sitemap.xml`)) {
    failures.push({ pathname: "/robots.txt", check: "sitemap-reference" });
  }
  for (const pathname of publicPaths) {
    const expected =
      pathname === "/" ? `${publicOrigin}/` : `${publicOrigin}${pathname}`;
    if (!sitemap.includes(`<loc>${expected}</loc>`)) {
      failures.push({ pathname: "/sitemap.xml", check: "route", expected });
    }
  }

  if (failures.length > 0) {
    throw new Error(
      `Technical SEO audit failed:\n${JSON.stringify(failures, null, 2)}`,
    );
  }
  console.log(
    `Technical SEO audit passed for ${publicPaths.length} public routes, robots.txt and sitemap.xml.`,
  );
}

const appPort = await freePort();
const url = `http://127.0.0.1:${appPort}`;
const reportsDirectory = await mkdtemp(path.join(tmpdir(), "mevad-lighthouse-"));
const nextCli = path.resolve("node_modules/next/dist/bin/next");
let serverOutput = "";
const application = spawn(
  process.execPath,
  [nextCli, "start", "-H", "127.0.0.1", "-p", String(appPort)],
  {
    cwd: process.cwd(),
    env: { ...process.env, NODE_ENV: "production" },
    stdio: ["ignore", "pipe", "pipe"],
  },
);
application.stdout.on("data", (chunk) => {
  serverOutput += chunk;
});
application.stderr.on("data", (chunk) => {
  serverOutput += chunk;
});
let auditBrowser;

try {
  await waitForApplication(url, application, () => serverOutput);
  await auditSeoRoutes(url);
  auditBrowser = await launchAuditBrowser(
    path.join(reportsDirectory, "browser-profile"),
  );

  const results = {};
  for (const mode of ["mobile", "desktop"]) {
    results[mode] = await runLighthouse({
      url,
      mode,
      reportPath: path.join(reportsDirectory, `${mode}.json`),
      browserPort: auditBrowser.port,
    });
  }

  const failures = [];
  for (const [mode, result] of Object.entries(results)) {
    for (const [category, threshold] of Object.entries(thresholds[mode])) {
      if (result.scores[category] < threshold) {
        failures.push({
          mode,
          category,
          score: result.scores[category],
          threshold,
        });
      }
    }
  }

  console.log(JSON.stringify({ thresholds, results }, null, 2));
  if (failures.length > 0) {
    throw new Error(
      `Lighthouse release gate failed:\n${JSON.stringify(failures, null, 2)}`,
    );
  }
} finally {
  if (auditBrowser) await stopProcess(auditBrowser.process);
  await stopProcess(application);
  await rm(reportsDirectory, { recursive: true, force: true });
}
