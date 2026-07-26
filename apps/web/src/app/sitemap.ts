import type { MetadataRoute } from "next";

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
  ];
}
