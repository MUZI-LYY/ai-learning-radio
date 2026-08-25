"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import BottomNav from "@/components/BottomNav";
import VoicePicker from "@/components/VoicePicker";
import { ApiError, api } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const MAX_MB = 15;
const ACCEPT = ".docx,.pdf,.md";

export default function LearnPage() {
  const router = useRouter();
  const { me, loading, refresh } = useMe();
  const [file, setFile] = useState<File | null>(null);
  const [focus, setFocus] = useState("");
  const [voiceKey, setVoiceKey] = useState("elegant_youth");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  if (loading || !me) {
    return <div className="min-h-dvh grid place-items-center text-slate-500">加载中…</div>;
  }

  function pickFile(f: File | null) {
    setError("");
    if (!f) return;
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ACCEPT.includes(ext)) {
      setError("仅支持 .docx、.pdf、.md 文件");
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`文件不能超过 ${MAX_MB}MB`);
      return;
    }
    setFile(f);
  }

  async function submit() {
    if (!file) {
      setError("请先选择一份学习资料");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("focus", focus);
      form.append("voice_key", voiceKey);
      const res = await api<{ task_id: string; status: string; quota_remaining: number }>(
        "/api/v1/learning/tasks",
        { method: "POST", body: form },
      );
      await refresh();
      router.push(`/tasks/${res.task_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "提交失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="learn-page mx-auto max-w-md px-4 pb-24 pt-4">
      <header className="app-page-header mb-5">
        <h1 className="text-xl font-bold">学习</h1>
        <p className="text-sm text-slate-500">
          今日剩余 {me.quota.remaining} / {me.quota.limit} 次生成
        </p>
      </header>

      <section className="space-y-6">
        <div>
          <label className="app-form-label block text-sm font-medium text-slate-700">
            学习资料（{ACCEPT}）
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="mt-2 w-full rounded-xl border-2 border-dashed border-slate-300 bg-white px-4 py-8 text-center"
            >
              {file ? (
                <span className="text-slate-800">{file.name}</span>
              ) : (
                <span className="text-slate-400">点击选择文件，最大 {MAX_MB}MB</span>
              )}
            </button>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        <div>
          <label className="app-form-label block text-sm font-medium text-slate-700">
            这次特别想理解什么
            <textarea
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              placeholder="可选，例如：想弄懂概念之间的联系"
              rows={3}
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-base outline-none focus:border-sky-500"
            />
          </label>
        </div>

        <div>
          <span className="app-form-label block text-sm font-medium text-slate-700">选择音色</span>
          <div className="mt-2">
            <VoicePicker value={voiceKey} onChange={setVoiceKey} />
          </div>
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <button
          onClick={submit}
          disabled={submitting || me.quota.remaining <= 0}
          className="w-full rounded-xl bg-slate-900 py-3 text-base font-semibold text-white disabled:opacity-40"
        >
          {me.quota.remaining <= 0
            ? "今日额度已用完"
            : submitting
              ? "提交中…"
              : "生成节目"}
        </button>
      </section>

      <BottomNav />
    </main>
  );
}
