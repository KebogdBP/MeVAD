import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./tokens.css";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "MeVAD — Online Video, Audio, Clip & GIF Workspace",
    template: "%s · MeVAD",
  },
  description:
    "Analyze one media link, then download video, extract audio, cut a clip or create a GIF in a private, temporary workspace.",
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
    siteName: "MeVAD",
    title: "MeVAD — One link, every media action",
    description:
      "Download video, extract audio, cut clips and create GIFs from one private media workspace.",
  },
  twitter: {
    card: "summary_large_image",
    title: "MeVAD — One link, every media action",
    description:
      "Download video, extract audio, cut clips and create GIFs from one private media workspace.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
