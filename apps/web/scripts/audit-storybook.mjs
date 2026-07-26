import { createServer } from "node:http";
import { readFile, stat, mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const root = path.resolve("storybook-static");
const index = JSON.parse(await readFile(path.join(root, "index.json"), "utf8"));
const stories = Object.values(index.entries).filter(
  (entry) => entry.type === "story",
);
const screenshotsEnabled = process.argv.includes("--screenshots");
const baselineId = "patterns-visual-baseline--component-matrix";
const screenshotDirectory = path.resolve(
  "..",
  "..",
  "docs",
  "product",
  "assets",
);

const contentTypes = new Map([
  [".css", "text/css; charset=utf-8"],
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".png", "image/png"],
  [".svg", "image/svg+xml"],
  [".woff2", "font/woff2"],
]);

const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(
      new URL(request.url ?? "/", "http://127.0.0.1").pathname,
    );
    const requestedPath = pathname === "/" ? "/index.html" : pathname;
    const filePath = path.resolve(root, `.${requestedPath}`);

    if (!filePath.startsWith(`${root}${path.sep}`)) {
      response.writeHead(403).end("Forbidden");
      return;
    }

    const fileStats = await stat(filePath);
    if (!fileStats.isFile()) {
      response.writeHead(404).end("Not found");
      return;
    }

    const extension = path.extname(filePath);
    response.writeHead(200, {
      "content-type":
        contentTypes.get(extension) ?? "application/octet-stream",
    });
    response.end(await readFile(filePath));
  } catch {
    response.writeHead(404).end("Not found");
  }
});

await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const address = server.address();
if (!address || typeof address === "string") {
  throw new Error("Unable to start the Storybook audit server.");
}

const browserPath = process.env.STORYBOOK_BROWSER_PATH;
const browser = await chromium.launch({
  headless: true,
  executablePath: browserPath || undefined,
  args: browserPath ? ["--no-proxy-server"] : undefined,
});
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const baseUrl = `http://127.0.0.1:${address.port}`;
const axePath = require.resolve("axe-core/axe.min.js");
const violations = [];

try {
  for (const story of stories) {
    await page.goto(`${baseUrl}/iframe.html?id=${story.id}&viewMode=story`, {
      waitUntil: "networkidle",
    });
    await page.waitForSelector("#storybook-root > *");
    await page.addScriptTag({ path: axePath });

    const result = await page.evaluate(async () =>
      globalThis.axe.run(document, {
        runOnly: {
          type: "tag",
          values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
        },
      }),
    );

    for (const violation of result.violations) {
      violations.push({
        story: story.id,
        rule: violation.id,
        impact: violation.impact,
        help: violation.help,
        targets: violation.nodes.flatMap((node) => node.target),
      });
    }
  }

  if (screenshotsEnabled) {
    await mkdir(screenshotDirectory, { recursive: true });
    for (const viewport of [
      { name: "desktop", width: 1440, height: 1000 },
      { name: "tablet", width: 768, height: 1024 },
      { name: "mobile", width: 375, height: 812 },
    ]) {
      await page.setViewportSize(viewport);
      await page.goto(
        `${baseUrl}/iframe.html?id=${baselineId}&viewMode=story`,
        { waitUntil: "networkidle" },
      );
      await page.waitForSelector("#storybook-root > *");
      await page.screenshot({
        path: path.join(
          screenshotDirectory,
          `phase-7-storybook-${viewport.name}.png`,
        ),
        fullPage: true,
      });
    }
  }
} finally {
  await browser.close();
  await new Promise((resolve, reject) =>
    server.close((error) => (error ? reject(error) : resolve())),
  );
}

if (violations.length > 0) {
  console.error(JSON.stringify(violations, null, 2));
  throw new Error(
    `Storybook accessibility audit found ${violations.length} violation(s).`,
  );
}

console.log(
  `Storybook accessibility audit passed for ${stories.length} stories.`,
);
