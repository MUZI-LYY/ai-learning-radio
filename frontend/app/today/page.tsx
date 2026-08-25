"use client";

import { useEffect, useState } from "react";
import AppIcon from "@/components/AppIcon";
import BottomNav from "@/components/BottomNav";
import DailyNewsPlayer from "@/components/DailyNewsPlayer";
import { api, type NewsChannel, type NewsProgramDetail } from "@/lib/api";
import { useMe } from "@/lib/use-me";

export default function TodayPage() {
  const { me, loading } = useMe();
  const [programs, setPrograms] = useState<NewsProgramDetail[]>([]);
  const [loadingPrograms, setLoadingPrograms] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (!me) return;
    let cancelled = false;
    async function loadPrograms() {
      setLoadingPrograms(true);
      setError("");
      try {
        const channels = await api<NewsChannel[]>("/api/v1/news/channels");
        const details = await Promise.all(
          channels.map(async (channel) => {
            if (!channel.program_id) return null;
            try {
              return await api<NewsProgramDetail>(
                `/api/v1/news/programs/${channel.program_id}`,
              );
            } catch {
              return null;
            }
          }),
        );
        if (!cancelled) setPrograms(details.filter((item): item is NewsProgramDetail => item != null));
      } catch {
        if (!cancelled) {
          setPrograms([]);
          setError("暂时没有收到频道信号，请稍后再试。");
        }
      } finally {
        if (!cancelled) setLoadingPrograms(false);
      }
    }
    void loadPrograms();
    return () => {
      cancelled = true;
    };
  }, [me, reloadToken]);

  if (loading || !me) {
    return (
      <div className="brand-loading">
        <span className="brand-mark">
          <AppIcon name="radio" size={22} />
        </span>
        <span>正在调到你的频道…</span>
      </div>
    );
  }

  return (
    <main className="today-page">
      <header className="today-header">
        <h1>每日资讯</h1>
      </header>

      {loadingPrograms ? (
        <div className="daily-feature-skeleton" aria-label="正在加载今日节目">
          <span />
          <i />
          <i />
        </div>
      ) : error ? (
        <div className="episode-empty">
          <h2>信号暂时走丢了</h2>
          <p>{error}</p>
          <button type="button" onClick={() => setReloadToken((value) => value + 1)}>
            重新加载
          </button>
        </div>
      ) : programs.length > 0 ? (
        <DailyNewsPlayer programs={programs} />
      ) : (
        <div className="episode-empty">
          <h2>节目还在准备中</h2>
          <p>三个频道都还没有可播放的节目，请稍后回来。</p>
        </div>
      )}

      <BottomNav />
    </main>
  );
}
