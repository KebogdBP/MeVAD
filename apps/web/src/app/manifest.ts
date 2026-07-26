import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MeVAD Media Workspace",
    short_name: "MeVAD",
    description:
      "Video downloads, audio extraction, precise clips and GIF loops from one workspace.",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f4ee",
    theme_color: "#ff9275",
  };
}
