"use client";

function apiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8002`;
  }
  return "http://127.0.0.1:8002";
}

export type UserSummary = {
  id: string;
  display_name: string;
  role: string;
};

export type MeResponse = {
  user: UserSummary;
  quota: { used: number; limit: number; remaining: number };
  channels: string[];
};

export type VoiceOption = {
  voice_key: string;
  display_name: string;
  description: string;
  preview_url: string;
  is_default: boolean;
};

export type TaskStatus = {
  task_id: string;
  status: string;
  current_step: string | null;
  error_code: string | null;
  error_message: string | null;
  program_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ProgramSummary = {
  id: string;
  title: string;
  status: string;
  voice_key: string | null;
  voice_name: string | null;
  audio_duration_seconds: number | null;
  audio_ready: boolean;
  source_name: string;
  created_at: string;
};

export type RecallQuestion = { question: string; answer: string };
export type Segment = { section: string; origin: "source" | "ai_supplement"; narration: string };

export type NewsChannel = {
  key: string;
  name: string;
  has_program: boolean;
  program_id: string | null;
};

export type NewsItem = {
  article_id: string | null;
  title: string;
  source_name: string;
  source_url: string;
  narration: string;
  excerpt: string;
  image_url: string | null;
  content_is_complete: boolean;
};

export type NewsProgramSummary = {
  id: string;
  channel: string;
  channel_name: string;
  program_date: string;
  title: string;
  status: string;
  audio_duration_seconds: number | null;
  published_at: string | null;
};

export type NewsProgramDetail = {
  id: string;
  channel: string;
  channel_name: string;
  program_date: string;
  title: string;
  summary: string;
  items: NewsItem[];
  audio_ready: boolean;
  audio_duration_seconds: number | null;
  status: string;
  voice_key: string;
  voice_name: string;
  is_favorited: boolean;
};

export type NewsFavoriteSummary = {
  program_id: string;
  channel: string;
  channel_name: string;
  program_date: string;
  title: string;
  summary: string;
  image_url: string | null;
  audio_duration_seconds: number | null;
  favorited_at: string;
};

export type NewsArticleDetail = {
  id: string;
  channel: string;
  title: string;
  source_name: string;
  source_url: string;
  summary: string;
  content: string;
  image_url: string | null;
  content_is_complete: boolean;
  published_at: string | null;
};

export type ProgramDetail = {
  id: string;
  title: string;
  status: string;
  source_name: string;
  voice_key: string | null;
  voice_name: string | null;
  audio_duration_seconds: number | null;
  audio_ready: boolean;
  learning_objectives: string[];
  segments: Segment[];
  summary: string;
  knowledge_points: string[];
  recall_questions: RecallQuestion[];
  created_at: string;
};

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const res = await fetch(`${apiBase()}${path}`, {
    ...init,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(init.headers ?? {}),
    },
  });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      data?.error?.code ?? "UNKNOWN",
      data?.error?.message ?? "请求失败，请稍后重试。",
      res.status,
    );
  }
  return data as T;
}

export function audioUrl(programId: string): string {
  return `${apiBase()}/api/v1/programs/${programId}/audio`;
}

export function previewUrl(path: string): string {
  return `${apiBase()}${path}`;
}

export function newsAudioUrl(programId: string): string {
  return `${apiBase()}/api/v1/news/programs/${programId}/audio`;
}
