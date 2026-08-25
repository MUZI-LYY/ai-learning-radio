"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useMe } from "@/lib/use-me";

export default function Home() {
  const router = useRouter();
  const { me, loading, error: connectionError, refresh } = useMe();

  useEffect(() => {
    if (me) router.replace("/today");
  }, [me, router]);

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

  return <div className="min-h-dvh grid place-items-center text-slate-500">跳转中…</div>;
}
