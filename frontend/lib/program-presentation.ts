export type ProgramPresentation = {
  key: "generating" | "completed" | "failed";
  label: "生成中" | "已生成" | "生成失败";
  playable: boolean;
};

const PERSONAL_PROGRAM_ARTWORKS = [
  "personal_01",
  "personal_02",
  "personal_03",
  "personal_04",
  "personal_05",
  "personal_06",
] as const;

export function personalProgramArtwork(index: number): string {
  const safeIndex = Number.isFinite(index) ? Math.max(0, Math.floor(index)) : 0;
  return PERSONAL_PROGRAM_ARTWORKS[safeIndex % PERSONAL_PROGRAM_ARTWORKS.length];
}

export function programPresentation(status: string, audioReady: boolean): ProgramPresentation {
  if (status === "completed" && audioReady) {
    return { key: "completed", label: "已生成", playable: true };
  }
  if (status === "text_ready" || status === "failed") {
    return { key: "failed", label: "生成失败", playable: false };
  }
  return { key: "generating", label: "生成中", playable: false };
}

export function formatProgramCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "生成时间未知";
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `生成于 ${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours()}:${minutes}`;
}
