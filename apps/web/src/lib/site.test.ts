import { describe, expect, it } from "vitest";

import sitemap from "@/app/sitemap";
import {
  infoPageMap,
  infoPages,
  type InfoPage,
} from "@/lib/info-pages";
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
    for (const page of infoPages as readonly InfoPage[]) {
      expect(urls).toContain(absoluteUrl(`/${page.slug}`));
    }
  });

  it("keeps information routes unique and complete", () => {
    expect(infoPageMap.size).toBe(infoPages.length);
    expect(infoPages.map((page) => page.slug)).toEqual([
      "how-it-works",
      "supported-sites",
      "privacy",
      "terms",
      "copyright",
    ]);
  });

  it("prevents thin or duplicated information content", () => {
    const titles = infoPages.map((page) => page.title);
    const descriptions = infoPages.map((page) => page.description);
    const headlines = infoPages.map((page) => page.headline);

    expect(new Set(titles).size).toBe(infoPages.length);
    expect(new Set(descriptions).size).toBe(infoPages.length);
    expect(new Set(headlines).size).toBe(infoPages.length);

    for (const page of infoPages as readonly InfoPage[]) {
      const sectionTitles = page.sections.map((section) => section.title);
      const visibleCopy = [
        page.headline,
        page.lede,
        page.notice ?? "",
        ...page.sections.flatMap((section) => [
          section.title,
          ...section.paragraphs,
          ...(section.bullets ?? []),
        ]),
      ].join(" ");

      expect(page.description.length).toBeGreaterThanOrEqual(100);
      expect(page.sections.length).toBeGreaterThanOrEqual(3);
      expect(new Set(sectionTitles).size).toBe(sectionTitles.length);
      expect(visibleCopy.length).toBeGreaterThanOrEqual(1_200);
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
