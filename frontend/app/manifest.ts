import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AI 学习电台",
    short_name: "学习电台",
    description: "把学习资料转换成可收听、可复习的中文节目",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f6f1",
    theme_color: "#f5f6f1",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
