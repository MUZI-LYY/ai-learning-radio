"use client";

import Image from "next/image";
import Link from "next/link";
import {
  type CSSProperties,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import AppIcon from "@/components/AppIcon";
import PodcastArtwork from "@/components/PodcastArtwork";
import {
  api,
  newsAudioUrl,
  previewUrl,
  type NewsProgramDetail,
  type VoiceOption,
} from "@/lib/api";

const SPEEDS = [0.75, 1, 1.25, 1.5, 2];
const GEAR_TICKS = Array.from({ length: 41 }, (_, index) => {
  const x = index * 12.5;
  const normalizedX = (x - 250) / 250;
  const y = 39 - 31 * normalizedX * normalizedX;
  const angle = (Math.atan((-62 * normalizedX) / 250) * 180) / Math.PI;
  return {
    angle,
    length: index % 5 === 0 ? 10 : index % 2 === 0 ? 6 : 4,
    x,
    y,
  };
});

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return "0:00";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

function programCover(program: NewsProgramDetail): string | null {
  return program.items.find((item) => item.image_url)?.image_url ?? null;
}

type PlaybackSegment = {
  label: string;
  text: string;
  articleId: string | null;
};

export default function DailyNewsPlayer({ programs }: { programs: NewsProgramDetail[] }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const previewRef = useRef<HTMLAudioElement | null>(null);
  const carouselRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);
  const scrollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(programs[0]?.audio_duration_seconds ?? 0);
  const [rate, setRate] = useState(1);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [audioError, setAudioError] = useState("");
  const [isFavorited, setIsFavorited] = useState(programs[0]?.is_favorited ?? false);
  const [favoriteBusy, setFavoriteBusy] = useState(false);
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null);

  const program = programs[Math.min(activeIndex, programs.length - 1)];
  const started = currentTime > 0 || playing;
  const hasFiniteDuration = Number.isFinite(duration) && duration > 0;
  const progress = hasFiniteDuration ? Math.min(currentTime / duration, 1) : 0;

  const playbackSegments = useMemo<PlaybackSegment[]>(
    () => [
      {
        label: `${program.channel_name} · 核心观点`,
        text: program.summary,
        articleId: null,
      },
      ...program.items.map((item) => ({
        label: item.source_name,
        text: item.narration,
        articleId: item.article_id,
      })),
    ],
    [program],
  );

  const syncedTranscript = useMemo(() => {
    const weights = playbackSegments.map((segment) => Math.max(segment.text.length, 1));
    const total = weights.reduce((sum, value) => sum + value, 0);
    const position = progress * total;
    let cursor = 0;
    for (let index = 0; index < weights.length; index += 1) {
      const end = cursor + weights[index];
      if (position <= end || index === weights.length - 1) {
        const segment = playbackSegments[index];
        const localPosition = Math.max(position - cursor, 0);
        return {
          index,
          segment,
          characterIndex: Math.min(
            Math.floor(localPosition),
            Math.max(segment.text.length - 1, 0),
          ),
        };
      }
      cursor = end;
    }
    return { index: 0, segment: playbackSegments[0], characterIndex: -1 };
  }, [playbackSegments, progress]);

  const carouselItems = useMemo(
    () =>
      programs.length > 1
        ? [programs[programs.length - 1], ...programs, programs[0]]
        : programs,
    [programs],
  );

  const channelSelectors = useMemo(() => {
    if (programs.length <= 1) return programs.map((item, index) => ({ item, index }));
    const previousIndex = (activeIndex - 1 + programs.length) % programs.length;
    const nextIndex = (activeIndex + 1) % programs.length;
    return [previousIndex, activeIndex, nextIndex].map((index) => ({
      item: programs[index],
      index,
    }));
  }, [activeIndex, programs]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => scrollToSlot(programs.length > 1 ? 1 : 0, false));
    return () => cancelAnimationFrame(frame);
  }, [programs.length]);

  useEffect(() => {
    const audio = audioRef.current;
    audio?.pause();
    audio?.load();
    // Program identity changed; reset playback UI before loading the new source.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlaying(false);
    setCurrentTime(0);
    setDuration(program.audio_duration_seconds ?? 0);
    setAudioError("");
    setIsFavorited(program.is_favorited);
    setSettingsOpen(false);
    previewRef.current?.pause();
    setPreviewingVoice(null);
  }, [program]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = rate;
  }, [rate, program.id]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
    }, 80);
    return () => window.clearInterval(timer);
  }, [playing]);

  useEffect(() => {
    if (!settingsOpen || voices.length > 0) return;
    api<VoiceOption[]>("/api/v1/tts/voices").then(setVoices).catch(() => {});
  }, [settingsOpen, voices.length]);

  useEffect(() => {
    if (!settingsOpen) previewRef.current?.pause();
  }, [settingsOpen]);

  useEffect(() => {
    if (!settingsOpen) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const sheet = settingsRef.current;
    const frame = requestAnimationFrame(() => sheet?.focus());

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setSettingsOpen(false);
        return;
      }
      if (event.key !== "Tab" || !sheet) return;
      const focusable = Array.from(
        sheet.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [settingsOpen]);

  useEffect(
    () => () => {
      previewRef.current?.pause();
      if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
    },
    [],
  );

  function scrollToSlot(slot: number, smooth: boolean) {
    const carousel = carouselRef.current;
    const card = carousel?.children.item(slot) as HTMLElement | null;
    if (!carousel || !card) return;
    carousel.scrollTo({
      left: card.offsetLeft - (carousel.clientWidth - card.clientWidth) / 2,
      behavior: smooth ? "smooth" : "instant",
    });
  }

  function chooseProgram(index: number) {
    if (index === activeIndex) return;
    audioRef.current?.pause();
    setActiveIndex(index);
    scrollToSlot(programs.length > 1 ? index + 1 : index, true);
  }

  function settleCarousel() {
    const carousel = carouselRef.current;
    if (!carousel || programs.length <= 1) return;
    const center = carousel.scrollLeft + carousel.clientWidth / 2;
    const cards = Array.from(carousel.children) as HTMLElement[];
    let closestSlot = 0;
    let closestDistance = Number.POSITIVE_INFINITY;
    cards.forEach((card, index) => {
      const distance = Math.abs(card.offsetLeft + card.clientWidth / 2 - center);
      if (distance < closestDistance) {
        closestDistance = distance;
        closestSlot = index;
      }
    });

    if (closestSlot === 0) {
      setActiveIndex(programs.length - 1);
      requestAnimationFrame(() => scrollToSlot(programs.length, false));
    } else if (closestSlot === programs.length + 1) {
      setActiveIndex(0);
      requestAnimationFrame(() => scrollToSlot(1, false));
    } else {
      setActiveIndex(closestSlot - 1);
    }
  }

  function handleCarouselScroll() {
    if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
    scrollTimerRef.current = setTimeout(settleCarousel, 110);
  }

  async function togglePlay() {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      setAudioError("");
      try {
        await audio.play();
      } catch {
        setAudioError("暂时无法播放，请检查网络后重试。");
      }
    } else {
      audio.pause();
    }
  }

  function seek(value: number) {
    if (!audioRef.current) return;
    audioRef.current.currentTime = value;
    setCurrentTime(value);
  }

  async function toggleFavorite() {
    if (favoriteBusy) return;
    const next = !isFavorited;
    setFavoriteBusy(true);
    setIsFavorited(next);
    try {
      await api(`/api/v1/news/programs/${program.id}/favorite`, {
        method: next ? "PUT" : "DELETE",
      });
    } catch {
      setIsFavorited(!next);
    } finally {
      setFavoriteBusy(false);
    }
  }

  function toggleVoicePreview(voice: VoiceOption) {
    previewRef.current?.pause();
    if (previewingVoice === voice.voice_key) {
      setPreviewingVoice(null);
      return;
    }
    const preview = new Audio(previewUrl(voice.preview_url));
    previewRef.current = preview;
    preview.onended = () => setPreviewingVoice(null);
    preview.onerror = () => setPreviewingVoice(null);
    void preview.play();
    setPreviewingVoice(voice.voice_key);
  }

  function renderCard(
    cardProgram: NewsProgramDetail,
    slot: number,
    realIndex: number,
    isClone: boolean,
  ) {
    const isActive = !isClone && realIndex === activeIndex;
    const cardCover = programCover(cardProgram);
    return (
      <article
        className={`daily-feature ${isActive ? "is-active is-expanded" : ""}`}
        key={`${cardProgram.id}-${slot}`}
        aria-hidden={!isActive}
      >
        <div className="daily-feature__heading">
          <span>{cardProgram.channel_name}</span>
          {isActive && (
            <Image
              className="daily-feature__agent"
              src="/ai-agent-cat.png"
              alt=""
              width={768}
              height={739}
              priority
            />
          )}
        </div>
        <div className="daily-feature__body">
          <div className="daily-feature__media">
            {cardCover ? (
              <div
                className="daily-feature__cover"
                role="img"
                aria-label="本期节目来源配图"
                style={{ backgroundImage: `url(${cardCover})` }}
              />
            ) : (
              <PodcastArtwork channel={cardProgram.channel} />
            )}
          </div>
          <div className="daily-feature__copy">
            <h2>{cardProgram.title}</h2>
            {isActive && (
              <Link className="daily-feature__more" href={`/today/programs/${cardProgram.id}`}>
                查看更多 <AppIcon name="chevron" size={16} />
              </Link>
            )}
          </div>
        </div>

        {isActive && (
          <div className="daily-feature__expanded">
            <div className="daily-feature__timeline">
              <span>{formatTime(currentTime)}</span>
              <input
                type="range"
                min={0}
                max={hasFiniteDuration ? duration : 0}
                step={0.1}
                value={Math.min(currentTime, hasFiniteDuration ? duration : 0)}
                onChange={(event) => seek(Number(event.target.value))}
                aria-label="播放进度"
                style={{ "--audio-progress": `${progress * 100}%` } as CSSProperties}
              />
              <span>{formatTime(duration)}</span>
            </div>
            <div className="daily-feature__actions">
              <button
                type="button"
                className={isFavorited ? "is-active" : ""}
                onClick={toggleFavorite}
                aria-pressed={isFavorited}
                aria-busy={favoriteBusy}
                aria-label={isFavorited ? "取消收藏" : "收藏到个人节目"}
                disabled={favoriteBusy}
              >
                <AppIcon name="favorite" size={26} filled={isFavorited} />
              </button>
              <button
                className="daily-feature__play"
                type="button"
                onClick={togglePlay}
                aria-label={playing ? "暂停今日节目" : "播放今日节目"}
              >
                <AppIcon
                  key={playing ? "round-pause" : "round-play"}
                  name={playing ? "round-pause" : "round-play"}
                  size={48}
                />
              </button>
              <button type="button" onClick={() => setSettingsOpen(true)} aria-label="播放设置">
                <AppIcon name="settings" size={26} />
              </button>
            </div>
          </div>
        )}
        {isActive && audioError && (
          <p className="daily-player-error" role="alert">
            {audioError}
          </p>
        )}
      </article>
    );
  }

  return (
    <>
      <audio
        ref={audioRef}
        src={newsAudioUrl(program.id)}
        preload="metadata"
        onLoadedMetadata={(event) => {
          if (Number.isFinite(event.currentTarget.duration) && event.currentTarget.duration > 0) {
            setDuration(event.currentTarget.duration);
          }
        }}
        onDurationChange={(event) => {
          if (Number.isFinite(event.currentTarget.duration) && event.currentTarget.duration > 0) {
            setDuration(event.currentTarget.duration);
          }
        }}
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onError={() => setAudioError("音频加载失败，请稍后再试。")}
      />

      <section className="program-carousel" aria-label="三个资讯频道">
        <div
          ref={carouselRef}
          className="program-carousel__track"
          onScroll={handleCarouselScroll}
        >
          {carouselItems.map((item, slot) => {
            const isClone = programs.length > 1 && (slot === 0 || slot === programs.length + 1);
            const realIndex =
              slot === 0
                ? programs.length - 1
                : slot === programs.length + 1
                  ? 0
                  : slot - 1;
            return renderCard(item, slot, realIndex, isClone);
          })}
        </div>
      </section>

      <section
        className="channel-gear"
        style={{ "--channel-index": activeIndex } as CSSProperties}
        aria-label="切换资讯频道"
      >
        <div className="channel-gear__labels" role="tablist" key={activeIndex}>
          {channelSelectors.map(({ item, index }, position) => (
            <button
              type="button"
              role="tab"
              aria-selected={index === activeIndex}
              className={index === activeIndex ? "is-active" : ""}
              key={`${item.id}-${position}`}
              onClick={() => chooseProgram(index)}
            >
              {item.channel_name}
            </button>
          ))}
        </div>
        <div className="channel-gear__scale" aria-hidden="true">
          <svg viewBox="0 0 500 48" preserveAspectRatio="none">
            <g transform="translate(0 -11)">
              <g transform="translate(0 48) scale(1 -1)">
                <path className="channel-gear__arc" d="M0 8 Q250 70 500 8" />
                <g className="channel-gear__ticks">
                  {GEAR_TICKS.map((tick, index) => (
                    <line
                      key={index}
                      x1={tick.x}
                      y1={tick.y}
                      x2={tick.x}
                      y2={tick.y - tick.length}
                      transform={`rotate(${tick.angle} ${tick.x} ${tick.y})`}
                    />
                  ))}
                </g>
              </g>
            </g>
            <path
              className="channel-gear__needle"
              d="M250 10 L245.5 18 H248.2 V39 H251.8 V18 H254.5 Z"
              transform="translate(0 -22.5)"
            />
          </svg>
        </div>
      </section>

      <section
        className={`daily-transcript ${started ? "is-playing" : ""}`}
        aria-live="polite"
      >
        <span className="daily-transcript__quote" aria-hidden="true">
          “
        </span>
        <div className="daily-transcript__content" key={`${program.id}-${syncedTranscript.index}`}>
          <div className="daily-transcript__source">
            <span>
              {String(syncedTranscript.index + 1).padStart(2, "0")} /{" "}
              {String(playbackSegments.length).padStart(2, "0")}
            </span>
            <strong>{syncedTranscript.segment.label}</strong>
          </div>
          {started ? (
            <p
              className="karaoke-text"
              aria-label={syncedTranscript.segment.text}
            >
              {Array.from(syncedTranscript.segment.text).map((character, index) => (
                <span
                  aria-hidden="true"
                  className={
                    index === syncedTranscript.characterIndex
                      ? "is-current"
                      : index < syncedTranscript.characterIndex
                        ? "is-past"
                        : ""
                  }
                  key={`${index}-${character}`}
                >
                  {character}
                </span>
              ))}
            </p>
          ) : (
            <p className="daily-transcript__lead">{program.summary}</p>
          )}
          {syncedTranscript.segment.articleId && (
            <Link href={`/today/articles/${syncedTranscript.segment.articleId}`}>
              阅读这篇来源
            </Link>
          )}
        </div>
        <div
          className="daily-transcript__dots"
          aria-label={`当前第 ${syncedTranscript.index + 1} 段，共 ${playbackSegments.length} 段`}
        >
          {playbackSegments.map((segment, index) => (
            <i className={index === syncedTranscript.index ? "is-active" : ""} key={`${segment.label}-${index}`} />
          ))}
        </div>
      </section>

      {settingsOpen && (
        <section className="playback-settings" role="dialog" aria-modal="true" aria-labelledby="playback-settings-title">
          <button
            className="playback-settings__backdrop"
            type="button"
            onClick={() => setSettingsOpen(false)}
            aria-label="关闭播放设置"
          />
          <div className="playback-settings__sheet" ref={settingsRef} tabIndex={-1}>
            <header>
              <div>
                <span>PLAYBACK</span>
                <h2 id="playback-settings-title">播放设置</h2>
              </div>
              <button type="button" onClick={() => setSettingsOpen(false)} aria-label="关闭">
                ×
              </button>
            </header>
            <section>
              <h3>播放速度</h3>
              <div className="playback-settings__speeds">
                {SPEEDS.map((speed) => (
                  <button
                    type="button"
                    key={speed}
                    className={speed === rate ? "is-active" : ""}
                    onClick={() => setRate(speed)}
                    aria-pressed={speed === rate}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </section>
            <section>
              <h3>节目音色</h3>
              <p className="playback-settings__note">
                当前节目已使用“{program.voice_name}”生成。其他音色可先试听；切换完整节目需要额外音轨。
              </p>
              <div className="playback-settings__voices">
                {voices.length === 0 ? (
                  <p>音色加载中…</p>
                ) : (
                  voices.map((voice) => (
                    <div
                      className={voice.voice_key === program.voice_key ? "is-current" : ""}
                      key={voice.voice_key}
                    >
                      <span>
                        <strong>{voice.display_name}</strong>
                        <small>
                          {voice.voice_key === program.voice_key ? "当前音色" : voice.description}
                        </small>
                      </span>
                      <button type="button" onClick={() => toggleVoicePreview(voice)}>
                        {previewingVoice === voice.voice_key ? "停止" : "试听"}
                      </button>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </section>
      )}
    </>
  );
}
