import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import type { ReactNode } from "react";
import { siteConfig } from "@/lib/site";
import "./tokens.css";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const manrope = Manrope({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-manrope",
});

const themeScript = `
  (() => {
    try {
      const saved = localStorage.getItem("mevad-theme");
      const theme = saved === "light" || saved === "dark"
        ? saved
        : matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = theme;
    } catch {
      document.documentElement.dataset.theme = "light";
    }
  })();
`;

export const metadata: Metadata = {
  metadataBase: siteConfig.url,
  title: {
    default: "MeVAD — Online Video, Audio, Clip & GIF Workspace",
    template: "%s · MeVAD",
  },
  description:
    siteConfig.description,
  applicationName: "MeVAD",
  keywords: [
    "online video downloader",
    "audio extractor",
    "video cutter",
    "video to GIF",
    "media workspace",
  ],
  openGraph: {
    type: "website",
    url: "/",
    siteName: "MeVAD",
    title: "MeVAD — One link, every media action",
    description:
      "Download video, extract audio, cut clips and create GIFs from one private media workspace.",
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
    title: "MeVAD — One link, every media action",
    description:
      "Download video, extract audio, cut clips and create GIFs from one private media workspace.",
    images: [siteConfig.ogImage],
  },
  alternates: {
    canonical: "/",
  },
  manifest: "/manifest.webmanifest",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${manrope.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
