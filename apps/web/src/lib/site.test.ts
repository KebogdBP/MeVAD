import { describe, expect, it } from "vitest";

import sitemap from "@/app/sitemap";
import { absoluteUrl, siteConfig } from "@/lib/site";
import { toolPageMap, toolPages } from "@/lib/tool-pages";

describe("public SEO surface", () => {
  it("keeps tool slugs unique and addressable", () => {
    expect(toolPageMap.size).toBe(toolPages.length);
    expect(toolPages.map((tool) => tool.slug)).toEqual([
      "video-downloader",
      "audio-downloader",
      "video-cutter",
      "video-to-gif",
    ]);
  });

  it("publishes every tool page in the sitemap", () => {
    const urls = sitemap().map((entry) => entry.url);

    expect(urls).toContain(absoluteUrl("/"));
    for (const tool of toolPages) {
      expect(urls).toContain(absoluteUrl(`/${tool.slug}`));
    }
  });

  it("keeps visible FAQ content complete enough for structured data", () => {
    for (const tool of toolPages) {
      expect(tool.faqs.length).toBeGreaterThanOrEqual(3);
      for (const faq of tool.faqs) {
        expect(faq.question.length).toBeGreaterThan(20);
        expect(faq.answer.length).toBeGreaterThan(40);
      }
    }
  });

  it("uses an absolute canonical origin", () => {
    expect(siteConfig.url.protocol).toBe("https:");
    expect(absoluteUrl("/video-downloader")).toMatch(
      /^https:\/\/[^/]+\/video-downloader$/,
    );
  });
});
