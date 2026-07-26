export const siteConfig = {
  name: "MeVAD",
  url: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://mevad.app"),
  description:
    "Analyze one media link, then download video, extract audio, cut a clip or create a GIF in a private, temporary workspace.",
  ogImage: "/og.png",
} as const;

export function absoluteUrl(pathname: string) {
  return new URL(pathname, siteConfig.url).toString();
}
