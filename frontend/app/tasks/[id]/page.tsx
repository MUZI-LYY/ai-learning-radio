"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import BottomNav from "@/components/BottomNav";
import { api, type TaskStatus } from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  queued: "排队中",
  validating: "校验文件",
  parsing: "解析正文",
  summarizing: "提取要点",
  generating: "生成讲稿",
  synthesizing: "合成音频",
  retry_wait: "等待重试",
  completed: "已完成",
  text_ready: "文字稿已就绪",
  failed: "失败",
};

const TERMINAL = new Set(["completed", "text_ready", "failed"]);

export default function TaskPage() {
  const params = useParams<{ id: string }>();
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [retryingGeneration, setRetryingGeneration] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;

    async function poll() {
      try {
        const t = await api<TaskStatus>(`/api/v1/tasks/${params.id}`);
        if (cancelled) return;
        setTask(t);
        if (!TERMINAL.has(t.status)) {
          timer = setTimeout(poll, 2000);
        }
      } catch {
        if (!cancelled) timer = setTimeout(poll, 3000);
      }
    }
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [params.id]);

  async function retryAudio() {
    setRetrying(true);
    try {
      await api(`/api/v1/tasks/${params.id}/retry-audio`, { method: "POST" });
      // 重新进入轮询
      setTask(null);
      const t = await api<TaskStatus>(`/api/v1/tasks/${params.id}`);
      setTask(t);
      if (!TERMINAL.has(t.status)) window.location.reload();
    } finally {
      setRetrying(false);
    }
  }

  async function retryGeneration() {
    setRetryingGeneration(true);
    try {
      await api(`/api/v1/tasks/${params.id}/retry-generation`, { method: "POST" });
      window.location.reload();
    } finally {
      setRetryingGeneration(false);
    }
  }

  if (!task) {
    return <div className="min-h-dvh grid place-items-center text-slate-500">加载中…</div>;
  }

  const label = STEP_LABELS[task.status] ?? task.status;

  return (
    <main className="task-page mx-auto max-w-md px-4 pb-24 pt-4">
      <header className="app-page-header mb-6">
        <h1 className="text-xl font-bold">生成进度</h1>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center">
        {!TERMINAL.has(task.status) ? (
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-sky-500" />
        ) : task.status === "failed" ? (
          <div className="mb-2 text-3xl">❌</div>
        ) : task.status === "text_ready" ? (
          <div className="mb-2 text-3xl">⚠️</div>
        ) : (
          <div className="mb-2 text-3xl">✅</div>
        )}

        <p className="text-lg font-semibold">{label}</p>
        {!TERMINAL.has(task.status) && (
          <p className="mt-1 text-sm text-slate-500">请稍候，正在处理…</p>
        )}

        {task.error_message && (
          <p className="mt-3 text-sm text-rose-600">{task.error_message}</p>
        )}

        {task.status === "failed" && task.current_step === "summarizing" && (
          <button
            onClick={retryGeneration}
            disabled={retryingGeneration}
            className="mt-4 rounded-xl bg-sky-600 px-5 py-2 text-sm font-semibold text-white disabled:opacity-40"
          >
            {retryingGeneration ? "重新生成中…" : "重新生成"}
          </button>
        )}

        {task.status === "text_ready" && (
          <div className="mt-4">
            <p className="mb-3 text-sm text-amber-600">音频生成失败，可稍后重试。</p>
            <button
              onClick={retryAudio}
              disabled={retrying}
              className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
            >
              {retrying ? "重试中…" : "重试音频"}
            </button>
          </div>
        )}

        {task.program_id && (
          <Link
            href={`/programs/${task.program_id}`}
            className="mt-4 inline-block rounded-xl bg-sky-600 px-5 py-2 text-sm font-semibold text-white"
          >
            查看节目
          </Link>
        )}
      </div>

      <BottomNav />
    </main>
  );
}
