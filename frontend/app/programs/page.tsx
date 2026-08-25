"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppIcon from "@/components/AppIcon";
import AudioPlayer from "@/components/AudioPlayer";
import BottomNav from "@/components/BottomNav";
import OverlayPlaybackIcon from "@/components/OverlayPlaybackIcon";
import PodcastArtwork from "@/components/PodcastArtwork";
import {
  api,
  audioUrl,
  newsAudioUrl,
  type NewsFavoriteSummary,
  type NewsProgramDetail,
  type ProgramDetail,
  type ProgramSummary,
} from "@/lib/api";
import {
  formatProgramCreatedAt,
  personalProgramArtwork,
  programPresentation,
} from "@/lib/program-presentation";
import { useMe } from "@/lib/use-me";

function durationText(seconds: number | null): string {
  if (seconds == null) return "";
  const minutes = Math.floor(seconds / 60);
  const remainder = Math.round(seconds % 60);
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

type LibraryPlayback = {
  key: string;
  title: string;
  channel: string;
  artworkChannel: string;
  src: string;
  transcript: string;
};

function personalTranscript(program: ProgramDetail): string {
  return [
    program.learning_objectives.length > 0
      ? `学习目标\n${program.learning_objectives.map((item, index) => `${index + 1}. ${item}`).join("\n")}`
      : "",
    ...program.segments.map((segment) =>
      `${segment.section}\n${segment.origin === "ai_supplement" ? "AI 补充：" : ""}${segment.narration}`,
    ),
    program.summary ? `总结复盘\n${program.summary}` : "",
  ].filter(Boolean).join("\n\n");
}

function favoriteTranscript(program: NewsProgramDetail): string {
  return [
    `${program.channel_name} · 核心观点\n${program.summary}`,
    ...program.items.map((item) => `${item.source_name}\n${item.narration}`),
  ].join("\n\n");
}

function PersonalProgramCard({
  item,
  artworkChannel,
  loading,
  onPlay,
}: {
  item: ProgramSummary;
  artworkChannel: string;
  loading: boolean;
  onPlay: (item: ProgramSummary) => void;
}) {
  const presentation = programPresentation(item.status, item.audio_ready);
  const playable = presentation.playable;
  const copy = (
    <>
      <span className="library-card__art">
        <PodcastArtwork channel={artworkChannel} size="library" />
      </span>
      <span className="library-card__copy">
        <strong>{item.title || "未命名节目"}</strong>
        <span className="library-card__meta">
          <time dateTime={item.created_at}>{formatProgramCreatedAt(item.created_at)}</time>
          <span className={`program-status program-status--${presentation.key}`}>
            {presentation.label}
          </span>
        </span>
      </span>
    </>
  );

  if (!playable) {
    return (
      <Link
        className="library-card library-card--personal library-card--pending"
        href={`/programs/${item.id}`}
        aria-label={`查看 ${item.title || "未命名节目"}`}
      >
        {copy}
      </Link>
    );
  }

  return (
    <div className="library-card library-card--personal library-card--play">
      <Link
        className="library-card__link"
        href={`/programs/${item.id}`}
        aria-label={`查看 ${item.title || "未命名节目"}`}
      >
        {copy}
      </Link>
      <button
        type="button"
        className="library-card__play-icon"
        onClick={() => onPlay(item)}
        disabled={loading}
        aria-label={`播放 ${item.title || "未命名节目"}`}
      >
        {loading
          ? <span className="library-card__spinner" aria-hidden="true" />
          : <OverlayPlaybackIcon state="play" size={40} />}
      </button>
    </div>
  );
}

export default function ProgramsPage() {
  const router = useRouter();
  const { me, loading, unauthorized } = useMe();
  const [programs, setPrograms] = useState<ProgramSummary[]>([]);
  const [favorites, setFavorites] = useState<NewsFavoriteSummary[]>([]);
  const [activeTab, setActiveTab] = useState<"private" | "favorites">("private");
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [playerLoadingKey, setPlayerLoadingKey] = useState("");
  const [playback, setPlayback] = useState<LibraryPlayback | null>(null);

  useEffect(() => {
    if (unauthorized) router.replace("/");
  }, [unauthorized, router]);

  useEffect(() => {
    if (!me) return;
    Promise.all([
      api<ProgramSummary[]>("/api/v1/programs"),
      api<NewsFavoriteSummary[]>("/api/v1/news/favorites"),
    ])
      .then(([privatePrograms, savedNews]) => {
        setPrograms(privatePrograms);
        setFavorites(savedNews);
      })
      .catch(() => setLoadError("节目库暂时没有连接上，请稍后再试。"))
      .finally(() => setLoaded(true));
  }, [me]);

  async function openPrivateProgram(item: ProgramSummary, artworkChannel: string) {
    const key = `private-${item.id}`;
    setPlayerLoadingKey(key);
    setLoadError("");
    try {
      const detail = await api<ProgramDetail>(`/api/v1/programs/${item.id}`);
      if (!detail.audio_ready) {
        setLoadError("这期节目的音频还在准备中，稍后再来收听。");
        return;
      }
      setPlayback({
        key,
        title: detail.title || "未命名节目",
        channel: detail.voice_name || "个人专属节目",
        artworkChannel,
        src: audioUrl(item.id),
        transcript: personalTranscript(detail),
      });
    } catch {
      setLoadError("这期节目暂时无法打开，请稍后重试。");
    } finally {
      setPlayerLoadingKey("");
    }
  }

  async function openFavoriteProgram(item: NewsFavoriteSummary) {
    const key = `favorite-${item.program_id}`;
    setPlayerLoadingKey(key);
    setLoadError("");
    try {
      const detail = await api<NewsProgramDetail>(`/api/v1/news/programs/${item.program_id}`);
      if (!detail.audio_ready) {
        setLoadError("这期收藏节目的音频还在准备中，稍后再来收听。");
        return;
      }
      setPlayback({
        key,
        title: detail.title,
        channel: detail.channel_name,
        artworkChannel: detail.channel,
        src: newsAudioUrl(detail.id),
        transcript: favoriteTranscript(detail),
      });
    } catch {
      setLoadError("这期收藏节目暂时无法打开，请稍后重试。");
    } finally {
      setPlayerLoadingKey("");
    }
  }

  if (loading || !me) {
    return <div className="brand-loading">正在打开节目库…</div>;
  }

  const empty = activeTab === "private" ? programs.length === 0 : favorites.length === 0;

  return (
    <main className="program-library">
      <header>
        <h1>个人节目</h1>
      </header>

      <Link className="program-library__create" href="/learn">
        <span>
          <AppIcon name="learn" size={26} />
        </span>
        <div>
          <strong>生成你的专属节目</strong>
          <small>上传学习资料，AI 为你整理并生成可收听的节目</small>
        </div>
        <AppIcon name="chevron" size={19} />
      </Link>

      <div className="program-library__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "private"}
          className={activeTab === "private" ? "is-active" : ""}
          onClick={() => setActiveTab("private")}
        >
          我的节目 <span>{programs.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === "favorites"}
          className={activeTab === "favorites" ? "is-active" : ""}
          onClick={() => setActiveTab("favorites")}
        >
          我的收藏 <span>{favorites.length}</span>
        </button>
      </div>

      {loadError && <p className="program-library__error" role="alert">{loadError}</p>}

      {loaded && empty ? (
        <section className="program-library__empty">
          <AppIcon name={activeTab === "private" ? "library" : "star"} size={28} />
          <h2>{activeTab === "private" ? "还没有个人节目" : "还没有收藏节目"}</h2>
          <p>
            {activeTab === "private"
              ? "从上方上传学习资料，生成属于你的第一期专属节目。"
              : "在每日资讯播放卡中点击收藏，就会保存在这里。"}
          </p>
        </section>
      ) : activeTab === "private" ? (
        <ul className="program-library__list">
          {programs.map((item, index) => {
            const artworkChannel = personalProgramArtwork(index);
            return (
            <li key={item.id}>
              <PersonalProgramCard
                item={item}
                artworkChannel={artworkChannel}
                loading={playerLoadingKey === `private-${item.id}`}
                onPlay={(program) => void openPrivateProgram(program, artworkChannel)}
              />
            </li>
            );
          })}
        </ul>
      ) : (
        <ul className="program-library__list">
          {favorites.map((item) => (
            <li key={item.program_id}>
              <button
                type="button"
                className="library-card library-card--play"
                onClick={() => void openFavoriteProgram(item)}
                disabled={playerLoadingKey === `favorite-${item.program_id}`}
                aria-label={`播放 ${item.title}`}
              >
                <span
                  className="library-card__art library-card__art--news"
                  style={item.image_url ? { backgroundImage: `url(${item.image_url})` } : undefined}
                >
                  {!item.image_url && <AppIcon name="radio" size={24} />}
                </span>
                <span className="library-card__copy">
                  <small>{item.channel_name} · {item.program_date}</small>
                  <strong>{item.title}</strong>
                  <span>{durationText(item.audio_duration_seconds)} · 已收藏</span>
                </span>
                <span className="library-card__play-icon">
                  {playerLoadingKey === `favorite-${item.program_id}`
                    ? <span className="library-card__spinner" aria-hidden="true" />
                    : <OverlayPlaybackIcon state="play" size={40} />}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <BottomNav />
      {playback && (
        <AudioPlayer
          key={playback.key}
          variant="drawer"
          src={playback.src}
          transcript={playback.transcript}
          title={playback.title}
          channel={playback.channel}
          artworkChannel={playback.artworkChannel}
          autoStart
          onDismiss={() => setPlayback(null)}
        />
      )}
    </main>
  );
}
