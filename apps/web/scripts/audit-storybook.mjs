import { createServer } from "node:http";
import { existsSync } from "node:fs";
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

const browserPath = [
  process.env.STORYBOOK_BROWSER_PATH,
  chromium.executablePath(),
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((candidate) => candidate && existsSync(candidate));
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
const responsiveFailures = [];
const interactionFailures = [];

async function openStory(storyId) {
  await page.goto(`${baseUrl}/iframe.html?id=${storyId}&viewMode=story`, {
    waitUntil: "networkidle",
  });
  await page.waitForSelector("#storybook-root > *");
}

function requireInteraction(condition, detail) {
  if (!condition) interactionFailures.push(detail);
}

async function runAxe(page) {
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      return await page.evaluate(async () =>
        globalThis.axe.run(document, {
          runOnly: {
            type: "tag",
            values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
          },
        }),
      );
    } catch (error) {
      if (
        !String(error).includes("Axe is already running") ||
        attempt === 3
      ) {
        throw error;
      }
      await page.waitForTimeout(250);
    }
  }
}

try {
  for (const story of stories) {
    for (const theme of ["light", "dark"]) {
      await page.goto(`${baseUrl}/iframe.html?id=${story.id}&viewMode=story`, {
        waitUntil: "networkidle",
      });
      await page.waitForSelector("#storybook-root > *");
      await page.evaluate((activeTheme) => {
        document.documentElement.dataset.theme = activeTheme;
      }, theme);
      await page.addScriptTag({ path: axePath });

      const result = await runAxe(page);

      for (const violation of result.violations) {
        violations.push({
          story: story.id,
          theme,
          rule: violation.id,
          impact: violation.impact,
          help: violation.help,
          targets: violation.nodes.flatMap((node) => node.target),
        });
      }
    }
  }

  const responsiveCases = [
    "patterns-site-header--menu-open",
    "patterns-media-workspace-states--empty",
    "patterns-media-workspace-states--analyzed",
  ];
  const responsiveViewports = [
    { name: "mobile-compact", width: 320, height: 812 },
    { name: "mobile", width: 375, height: 812 },
    { name: "zoom-200-reflow", width: 720, height: 900 },
    { name: "tablet", width: 768, height: 1024 },
    { name: "laptop", width: 1024, height: 900 },
    { name: "desktop", width: 1440, height: 1000 },
  ];

  for (const story of responsiveCases) {
    for (const viewport of responsiveViewports) {
      await page.setViewportSize(viewport);
      await page.goto(`${baseUrl}/iframe.html?id=${story}&viewMode=story`, {
        waitUntil: "networkidle",
      });
      await page.waitForSelector("#storybook-root > *");

      const overflow = await page.evaluate(() => {
        const viewportWidth = document.documentElement.clientWidth;
        const menuToggle = document.querySelector(".mobile-nav-toggle");
        const offenders = Array.from(document.body.querySelectorAll("*"))
          .filter((element) => {
            const bounds = element.getBoundingClientRect();
            return bounds.left < -1 || bounds.right > viewportWidth + 1;
          })
          .slice(0, 8)
          .map((element) => ({
            tag: element.tagName.toLowerCase(),
            className:
              element instanceof HTMLElement ? element.className : "",
          }));
        return {
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth,
          offenders,
          menuDisplay: menuToggle ? getComputedStyle(menuToggle).display : null,
        };
      });

      if (overflow.documentWidth > overflow.viewportWidth + 1) {
        responsiveFailures.push({
          story,
          mode: viewport.name,
          viewport: viewport.width,
          ...overflow,
        });
      }

      if (
        story === "patterns-site-header--menu-open" &&
        ((viewport.width <= 900 && overflow.menuDisplay === "none") ||
          (viewport.width > 900 && overflow.menuDisplay !== "none"))
      ) {
        responsiveFailures.push({
          story,
          mode: viewport.name,
          viewport: viewport.width,
          menuDisplay: overflow.menuDisplay,
        });
      }
    }
  }

  await page.setViewportSize({ width: 720, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(
    `${baseUrl}/iframe.html?id=patterns-media-workspace-states--analyzing&viewMode=story`,
    { waitUntil: "networkidle" },
  );
  const reducedMotionActive = await page.evaluate(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  if (!reducedMotionActive) {
    responsiveFailures.push({ feature: "prefers-reduced-motion" });
  }

  await page.emulateMedia({
    reducedMotion: "no-preference",
    forcedColors: "active",
  });
  await page.goto(
    `${baseUrl}/iframe.html?id=patterns-media-workspace-states--analyzed&viewMode=story`,
    { waitUntil: "networkidle" },
  );
  const forcedColorsActive = await page.evaluate(
    () => matchMedia("(forced-colors: active)").matches,
  );
  if (!forcedColorsActive) {
    responsiveFailures.push({ feature: "forced-colors" });
  }
  await page.emulateMedia({
    reducedMotion: "no-preference",
    forcedColors: "none",
  });

  await page.setViewportSize({ width: 1440, height: 1000 });
  await openStory("patterns-media-workspace-states--analyzed");
  const keyboardSequence = [];
  for (let index = 0; index < 20; index += 1) {
    await page.keyboard.press("Tab");
    const activeControl = await page.evaluate(() => {
      const element = document.activeElement;
      if (!(element instanceof HTMLElement) || element === document.body) {
        return null;
      }
      const style = getComputedStyle(element);
      const label =
        element.getAttribute("aria-label") ||
        ("labels" in element && element.labels?.length
          ? Array.from(element.labels)
              .map((item) => item.textContent?.trim())
              .filter(Boolean)
              .join(" ")
          : "") ||
        element.innerText.trim();
      return {
        label,
        tag: element.tagName.toLowerCase(),
        visibleFocus:
          style.outlineStyle !== "none" ||
          (style.boxShadow !== "none" && style.boxShadow !== ""),
      };
    });
    if (!activeControl) continue;
    if (
      keyboardSequence.length > 0 &&
      activeControl.label === keyboardSequence[0].label &&
      activeControl.tag === keyboardSequence[0].tag
    ) {
      break;
    }
    keyboardSequence.push(activeControl);
  }

  const keyboardLabels = keyboardSequence.map((item) => item.label);
  for (const expectedLabel of [
    "Paste a supported URL",
    "Analyze",
    "Video",
    "Audio",
    "Clip",
    "GIF & Loop",
    "Quality",
    "Container",
    "Create Video job",
  ]) {
    requireInteraction(
      keyboardLabels.some((label) => label.includes(expectedLabel)),
      {
        check: "keyboard-order",
        expectedLabel,
        keyboardLabels,
      },
    );
  }
  requireInteraction(
    keyboardSequence.every((item) => item.visibleFocus),
    {
      check: "visible-keyboard-focus",
      controls: keyboardSequence.filter((item) => !item.visibleFocus),
    },
  );

  await openStory("patterns-media-workspace-states--analyzing");
  const analysisStatus = page.getByRole("status");
  requireInteraction((await analysisStatus.count()) === 1, {
    check: "screen-reader-analysis-status",
    count: await analysisStatus.count(),
  });
  requireInteraction(
    (await analysisStatus.textContent())?.includes(
      "Analyzing media and loading available actions.",
    ),
    { check: "screen-reader-analysis-announcement" },
  );

  await openStory("patterns-media-workspace-states--processing");
  const jobRegion = page.locator('[aria-label="Media job status"]');
  const jobProgress = page.getByRole("progressbar", { name: "Job progress" });
  requireInteraction((await jobRegion.count()) === 1, {
    check: "screen-reader-job-region",
  });
  requireInteraction(
    (await jobRegion.getAttribute("aria-live")) === "polite",
    { check: "screen-reader-job-live-region" },
  );
  requireInteraction(
    (await jobProgress.getAttribute("aria-valuenow")) === "64",
    { check: "screen-reader-job-progress" },
  );
  requireInteraction(
    (await page.getByRole("button", { name: "Cancel" }).count()) === 1,
    { check: "keyboard-job-cancel" },
  );

  await openStory("patterns-media-workspace-states--failed");
  requireInteraction(
    (await page.getByRole("alert").allTextContents()).some((message) =>
      message.includes("The source stream could not be converted."),
    ),
    { check: "screen-reader-job-error" },
  );

  await openStory("patterns-media-workspace-states--succeeded");
  requireInteraction(
    (await page.getByRole("link", { name: "Download result" }).count()) === 1,
    { check: "keyboard-download-result" },
  );

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

if (responsiveFailures.length > 0) {
  console.error(JSON.stringify(responsiveFailures, null, 2));
  throw new Error(
    `Responsive audit found ${responsiveFailures.length} failure(s).`,
  );
}

if (interactionFailures.length > 0) {
  console.error(JSON.stringify(interactionFailures, null, 2));
  throw new Error(
    `Keyboard and screen-reader audit found ${interactionFailures.length} failure(s).`,
  );
}

console.log(
  `Storybook audit passed for ${stories.length} stories in light/dark themes, five target widths, 200% zoom reflow, reduced motion, forced colors, keyboard traversal and screen-reader semantics.`,
);
