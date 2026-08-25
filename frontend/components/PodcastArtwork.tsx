const CHANNEL_ART = {
  ai_frontier: {
    index: "01",
    label: "AI 前沿",
    accent: "#d8f56a",
    field: "#173f35",
    ink: "#111714",
  },
  tech_product: {
    index: "02",
    label: "科技产品",
    accent: "#ff765f",
    field: "#173c68",
    ink: "#151919",
  },
  startup_business: {
    index: "03",
    label: "创业商业",
    accent: "#f4c95d",
    field: "#7f2d35",
    ink: "#171713",
  },
  personal_01: {
    index: "P1",
    label: "深度学习",
    accent: "#b9ddff",
    field: "#175aa5",
    ink: "#10233b",
  },
  personal_02: {
    index: "P2",
    label: "灵感笔记",
    accent: "#c9f2cf",
    field: "#28735d",
    ink: "#15352b",
  },
  personal_03: {
    index: "P3",
    label: "知识拆解",
    accent: "#ffd0bf",
    field: "#a64556",
    ink: "#3d2024",
  },
  personal_04: {
    index: "P4",
    label: "思维地图",
    accent: "#dfd0ff",
    field: "#6346a8",
    ink: "#291b4e",
  },
  personal_05: {
    index: "P5",
    label: "每日精进",
    accent: "#ffe29a",
    field: "#244a78",
    ink: "#3b2c10",
  },
  personal_06: {
    index: "P6",
    label: "专属课堂",
    accent: "#bceee9",
    field: "#1d7180",
    ink: "#12343a",
  },
} as const;

export default function PodcastArtwork({
  channel,
  size = "large",
}: {
  channel: string;
  size?: "large" | "small" | "library" | "player";
}) {
  const art = CHANNEL_ART[channel as keyof typeof CHANNEL_ART] ?? CHANNEL_ART.ai_frontier;

  return (
    <div
      className={`podcast-art podcast-art--${size} podcast-art--${channel}`}
      style={{
        "--art-accent": art.accent,
        "--art-field": art.field,
        "--art-ink": art.ink,
      } as React.CSSProperties}
      aria-hidden="true"
    >
      <span className="podcast-art__kicker">
        {channel.startsWith("personal_") ? "PRIVATE RADIO" : "DAILY SIGNAL"}
      </span>
      <span className="podcast-art__index">{art.index}</span>
      <span className="podcast-art__label">{art.label}</span>
      <span className="podcast-art__wave">
        <i />
        <i />
        <i />
        <i />
        <i />
      </span>
    </div>
  );
}
