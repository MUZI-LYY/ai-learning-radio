"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppIcon from "@/components/AppIcon";
import BottomNav from "@/components/BottomNav";
import { api, type ProgramSummary } from "@/lib/api";
import { useMe } from "@/lib/use-me";

export default function AccountPage() {
  const router = useRouter();
  const { me, loading, unauthorized } = useMe();
  const [generatedCount, setGeneratedCount] = useState(0);

  useEffect(() => {
    if (unauthorized) router.replace("/");
  }, [unauthorized, router]);

  useEffect(() => {
    if (!me) return;
    api<ProgramSummary[]>("/api/v1/programs")
      .then((items) => setGeneratedCount(items.length))
      .catch(() => setGeneratedCount(0));
  }, [me]);

  if (loading || !me) {
    return <div className="min-h-dvh grid place-items-center text-slate-500">加载中…</div>;
  }

  return (
    <main className="account-page">
      <header className="app-page-header">
        <h1>我的</h1>
      </header>

      <section className="account-profile">
        <span className="account-profile__avatar" aria-hidden="true">
          <AppIcon name="account" size={42} filled />
        </span>
        <div>
          <strong>亲爱的用户</strong>
          <small>AI 学习电台听众</small>
        </div>
        <Link href="/account/settings" aria-label="打开设置">
          <AppIcon name="settings" size={25} />
        </Link>
      </section>

      <section className="account-dashboard" aria-labelledby="account-dashboard-title">
        <header>
          <span>LEARNING DATA</span>
          <h2 id="account-dashboard-title">你的学习电台</h2>
        </header>
        <div className="account-dashboard__grid">
          <div><strong>{generatedCount}</strong><span>生成资料</span></div>
          <div><strong>0</strong><span>收听节目</span></div>
          <div><strong>0</strong><span>收听分钟</span></div>
        </div>
        <p>收听数据会从你开始播放个人节目后逐步积累。</p>
      </section>

      <section className="account-quota">
        <span>今日可生成</span>
        <strong>{me.quota.remaining}<small> / {me.quota.limit} 次</small></strong>
      </section>

      <BottomNav />
    </main>
  );
}
