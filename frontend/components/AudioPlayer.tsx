"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AppIcon from "@/components/AppIcon";
import OverlayPlaybackIcon from "@/components/OverlayPlaybackIcon";
import PodcastArtwork from "@/components/PodcastArtwork";
import { AUDIO_JUMP_SECONDS } from "@/lib/audio-controls";

const SPEEDS = [0.75, 1, 1.25, 1.5, 2];

export default function AudioPlayer({
  src,
  transcript,
  variant = "inline",
  title = "正在播放",
  channel = "学习电台",
  artworkChannel = "ai_frontier",
  autoStart = false,
  disabled = false,
  onDismiss,
}: {
  src: string;
  transcript?: string;
  variant?: "inline" | "persistent" | "drawer" | "detail";
  title?: string;
  channel?: string;
  artworkChannel?: string;
  autoStart?: boolean;
  disabled?: boolean;
  onDismiss?: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const playerLayerRef = useRef<HTMLElement>(null);
  const [rate, setRate] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showTranscript, setShowTranscript] = useState(false);
  const [audioError, setAudioError] = useState("");
  const [expanded, setExpanded] = useState(variant === "drawer");

  const closeExpanded = useCallback(() => {
    setExpanded(false);
    onDismiss?.();
  }, [onDismiss]);

  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = rate;
  }, [rate]);

  useEffect(() => {
    // Media identity changed; reset the controls before the new element emits events.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setExpanded(variant === "drawer");
    setCurrentTime(0);
    setPlaying(false);
    setAudioError("");
  }, [src, variant]);

  useEffect(() => {
    if (!expanded) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const layer = playerLayerRef.current;
    const frame = requestAnimationFrame(() => layer?.focus());
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeExpanded();
        return;
      }
      if (event.key !== "Tab" || !layer) return;
      const focusable = Array.from(
        layer.querySelectorAll<HTMLElement>(
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
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [closeExpanded, expanded]);

  useEffect(() => {
    if (disabled || !autoStart || !audioRef.current) return;
    const audio = audioRef.current;
    const start = () => void audio.play().catch(() => undefined);
    if (audio.readyState >= 2) start();
    else audio.addEventListener("canplay", start, { once: true });
    return () => audio.removeEventListener("canplay", start);
  }, [autoStart, disabled, src]);

  function formatTime(seconds: number) {
    if (!Number.isFinite(seconds)) return "0:00";
    const minutes = Math.floor(seconds / 60);
    return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
  }

  async function togglePlay() {
    if (disabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      setAudioError("");
      try {
        await audio.play();
      } catch {
        setAudioError("暂时无法播放音频，请检查网络后重试。");
      }
    } else {
      audio.pause();
    }
  }

  function jump(amount: number) {
    if (disabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.min(Math.max(audio.currentTime + amount, 0), audio.duration || 0);
  }

  function seek(value: number) {
    if (disabled) return;
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = value;
    setCurrentTime(value);
  }

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;
  const transcriptCharacters = useMemo(() => Array.from(transcript ?? ""), [transcript]);
  const activeCharacter =
    duration > 0 && transcriptCharacters.length > 0
      ? Math.min(
          Math.floor((currentTime / duration) * transcriptCharacters.length),
          transcriptCharacters.length - 1,
        )
      : -1;

  const audioElement = disabled || !src ? null : (
    <audio
      ref={audioRef}
      src={src}
      preload="metadata"
      onLoadedMetadata={(event) => setDuration(event.currentTarget.duration)}
      onDurationChange={(event) => setDuration(event.currentTarget.duration)}
      onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
      onPlay={() => setPlaying(true)}
      onPause={() => setPlaying(false)}
      onEnded={() => setPlaying(false)}
      onError={() => setAudioError("音频加载失败，请稍后重试。")}
    />
  );

  const timeline = (
    <div className="audio-player__timeline">
      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={Math.min(currentTime, duration || 0)}
        onChange={(event) => seek(Number(event.target.value))}
        aria-label="播放进度"
        disabled={disabled}
        style={{ "--audio-progress": `${progress}%` } as React.CSSProperties}
      />
      <div className="audio-player__time">
        <span>{formatTime(currentTime)}</span>
        <span>-{formatTime(Math.max(duration - currentTime, 0))}</span>
      </div>
    </div>
  );

  const detailTimeline = (
    <div className="audio-player__detail-timeline">
      <span>{formatTime(currentTime)}</span>
      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={Math.min(currentTime, duration || 0)}
        onChange={(event) => seek(Number(event.target.value))}
        aria-label="播放进度"
        disabled={disabled}
        style={{ "--audio-progress": `${progress}%` } as React.CSSProperties}
      />
      <span>{formatTime(duration)}</span>
    </div>
  );

  const controls = (
    <div className="audio-player__controls">
      <button type="button" className="audio-player__jump" onClick={() => jump(-AUDIO_JUMP_SECONDS)} aria-label="后退 5 秒" disabled={disabled}>
        <AppIcon name="back" size={26} />
      </button>
      <button type="button" className="audio-player__play" onClick={togglePlay} aria-label={playing ? "暂停" : "播放"} disabled={disabled}>
        {variant === "detail" ? (
          <OverlayPlaybackIcon state={playing ? "pause" : "play"} size={48} />
        ) : (
          <AppIcon name={playing ? "pause" : "play"} size={28} />
        )}
      </button>
      <button type="button" className="audio-player__jump" onClick={() => jump(AUDIO_JUMP_SECONDS)} aria-label="前进 5 秒" disabled={disabled}>
        <AppIcon name="forward" size={26} />
      </button>
    </div>
  );

  const tools = (
    <div className="audio-player__tools">
      <span className="audio-player__tool-label">播放速度</span>
      <div className="audio-player__speeds" aria-label="播放速度">
        {SPEEDS.map((speed) => (
          <button
            key={speed}
            type="button"
            onClick={() => setRate(speed)}
            className={rate === speed ? "is-active" : ""}
            aria-pressed={rate === speed}
            disabled={disabled}
          >
            {speed}x
          </button>
        ))}
      </div>
    </div>
  );

  const transcriptPanel = transcript ? (
    <div className="audio-player__transcript">
      <button type="button" onClick={() => setShowTranscript((value) => !value)} aria-expanded={showTranscript}>
        <span>节目文字稿</span>
        <span className={showTranscript ? "is-open" : ""}>
          <AppIcon name="chevron" size={18} />
        </span>
      </button>
      {showTranscript && <p>{transcript}</p>}
    </div>
  ) : null;

  if (variant === "drawer") {
    return (
      <>
        {audioElement}
        {expanded && (
          <section
            className="program-player-layer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="program-player-title"
            ref={playerLayerRef}
            tabIndex={-1}
          >
            <button
              className="program-player-layer__backdrop"
              type="button"
              onClick={closeExpanded}
              aria-label="关闭播放器"
            />
            <div className="program-player-drawer">
              <header className="program-player-drawer__header">
                <span aria-hidden="true" />
                <div>
                  <small>{channel}</small>
                  <h2 id="program-player-title">{title}</h2>
                </div>
                <button type="button" onClick={closeExpanded} aria-label="关闭播放器">×</button>
              </header>

              <div className="program-player-drawer__transcript">
                <span>节目逐字稿</span>
                {transcriptCharacters.length > 0 ? (
                  <p aria-label={transcript}>
                    {transcriptCharacters.map((character, index) => (
                      <span
                        aria-hidden="true"
                        className={
                          index === activeCharacter
                            ? "is-current"
                            : index < activeCharacter
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
                  <p>这期节目暂时没有可展示的文字稿。</p>
                )}
              </div>

              <aside className="program-player-card" aria-label="播放控制">
                <input
                  type="range"
                  min={0}
                  max={duration || 0}
                  step={0.1}
                  value={Math.min(currentTime, duration || 0)}
                  onChange={(event) => seek(Number(event.target.value))}
                  aria-label="播放进度"
                  style={{ "--audio-progress": `${progress}%` } as React.CSSProperties}
                />
                <PodcastArtwork channel={artworkChannel} size="small" />
                <span className="program-player-card__copy">
                  <strong>{title}</strong>
                  <small role={audioError ? "alert" : undefined}>
                    {audioError || (playing ? "正在播放" : currentTime > 0 ? "已暂停" : "准备播放")}
                    {!audioError && duration > 0
                      ? ` · ${formatTime(currentTime)} / ${formatTime(duration)}`
                      : ""}
                  </small>
                </span>
                <button type="button" onClick={togglePlay} aria-label={playing ? "暂停" : "播放"}>
                  <OverlayPlaybackIcon state={playing ? "pause" : "play"} size={46} />
                </button>
              </aside>
            </div>
          </section>
        )}
      </>
    );
  }

  if (variant === "persistent") {
    return (
      <>
        {audioElement}
        <aside className="mini-player" aria-label="迷你播放器">
          <span className="mini-player__progress" style={{ width: `${progress}%` }} />
          <button className="mini-player__open" type="button" onClick={() => setExpanded(true)} aria-label="打开正在播放">
            <PodcastArtwork channel={artworkChannel} size="small" />
            <span className="mini-player__copy">
              <strong>{title}</strong>
              <small>{playing ? "正在播放" : currentTime > 0 ? "已暂停" : channel}</small>
            </span>
          </button>
          <button className="mini-player__play" type="button" onClick={togglePlay} aria-label={playing ? "暂停" : "播放"}>
            <AppIcon name={playing ? "pause" : "play"} size={22} />
          </button>
        </aside>

        {expanded && (
          <section className="player-sheet" role="dialog" aria-modal="true" aria-label="正在播放">
            <header className="player-sheet__header">
              <button type="button" onClick={closeExpanded} aria-label="收起播放器">
                <span><AppIcon name="chevron" size={23} /></span>
              </button>
              <div><strong>正在播放</strong><small>AI 学习电台</small></div>
              <span className="player-sheet__header-spacer" />
            </header>

            <div className="player-sheet__body">
              <div className="player-sheet__art"><PodcastArtwork channel={artworkChannel} size="player" /></div>
              <div className="player-sheet__identity">
                <p>{channel}</p>
                <h2>{title}</h2>
              </div>
              <div className="audio-player audio-player--sheet">
                {timeline}
                {controls}
                {audioError && <p className="audio-player__error" role="alert">{audioError}</p>}
                {tools}
                {transcriptPanel}
              </div>
            </div>
          </section>
        )}
      </>
    );
  }

  if (variant === "detail") {
    return (
      <div className={`audio-player audio-player--detail${disabled ? " is-disabled" : ""}`}>
        {audioElement}
        {detailTimeline}
        {controls}
        {audioError && <p className="audio-player__error" role="alert">{audioError}</p>}
        {tools}
        {transcriptPanel}
      </div>
    );
  }

  return (
    <div className="audio-player">
      {audioElement}
      {timeline}
      {controls}
      {audioError && <p className="audio-player__error" role="alert">{audioError}</p>}
      {tools}
      {transcriptPanel}
    </div>
  );
}
