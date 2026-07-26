import type { Metadata } from "next";
import { Inter, Manrope } from "next/font/google";
import type { ReactNode } from "react";
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
