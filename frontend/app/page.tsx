"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { useMe } from "@/lib/use-me";

export default function Home() {
  const router = useRouter();
  const { me, loading, unauthorized, error: connectionError, refresh } = useMe();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (me) router.replace("/today");
  }, [me, router]);

  async function submit() {
    setError("");
    setSubmitting(true);
    try {
      await api("/api/v1/auth/invite", {
        method: "POST",
        body: JSON.stringify({ invite_code: code.trim() }),
      });
      await refresh();
      router.replace("/today");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "登录失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="min-h-dvh grid place-items-center text-slate-500">加载中…</div>;
  }

  if (connectionError) {
    return (
      <main className="min-h-dvh grid place-items-center px-6 text-center">
        <div>
          <p className="font-semibold text-slate-800">暂时连接不上本地服务</p>
          <p className="mt-2 text-sm text-slate-500">{connectionError}</p>
          <button
            type="button"
            onClick={() => void refresh()}
            className="mt-4 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white"
          >
            重新连接
          </button>
        </div>
      </main>
    );
  }

  if (unauthorized) {
    return (
      <main className="min-h-dvh flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="mx-auto mb-3 h-14 w-14 rounded-2xl bg-slate-900 grid place-items-center text-2xl">
              📻
            </div>
            <h1 className="text-2xl font-bold">AI 学习电台</h1>
            <p className="mt-1 text-sm text-slate-500">
              把学习资料转换成可收听、可复习的中文节目
            </p>
          </div>

          <label className="block text-sm font-medium text-slate-700">
            邀请码
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder="输入你的邀请码"
              className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 text-base outline-none focus:border-sky-500"
              autoFocus
            />
          </label>

          {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

          <button
            onClick={submit}
            disabled={submitting || !code.trim()}
            className="mt-4 w-full rounded-xl bg-slate-900 py-3 text-base font-semibold text-white disabled:opacity-40"
          >
            {submitting ? "验证中…" : "进入"}
          </button>
        </div>
      </main>
    );
  }

  return <div className="min-h-dvh grid place-items-center text-slate-500">跳转中…</div>;
}
