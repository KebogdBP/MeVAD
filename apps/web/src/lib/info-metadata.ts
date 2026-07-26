import type { Metadata } from "next";

import type { InfoPage } from "@/lib/info-pages";
import { siteConfig } from "@/lib/site";

export function createInfoMetadata(page: InfoPage): Metadata {
  const path = `/${page.slug}`;
  return {
    title: page.title,
    description: page.description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      url: path,
      title: page.title,
      description: page.description,
      images: [
        {
          url: siteConfig.ogImage,
          width: 1200,
          height: 630,
          alt: "MeVAD — one link, four media tools",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.description,
      images: [siteConfig.ogImage],
    },
  };
}
