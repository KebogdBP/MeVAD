import type { MetadataRoute } from "next";

import { infoPages } from "@/lib/info-pages";
import { absoluteUrl } from "@/lib/site";
import { toolPages } from "@/lib/tool-pages";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: absoluteUrl("/"),
      changeFrequency: "weekly",
      priority: 1,
    },
    ...toolPages.map((tool) => ({
      url: absoluteUrl(`/${tool.slug}`),
      changeFrequency: "monthly" as const,
      priority: 0.8,
    })),
    ...infoPages.map((page) => ({
      url: absoluteUrl(`/${page.slug}`),
      changeFrequency: "monthly" as const,
      priority: page.slug === "how-it-works" ? 0.7 : 0.5,
    })),
  ];
}
