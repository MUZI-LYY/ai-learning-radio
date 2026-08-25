"use client";

import { useEffect, useRef, useState } from "react";
import { api, previewUrl, type VoiceOption } from "@/lib/api";

export default function VoicePicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (key: string) => void;
}) {
  const [voices, setVoices] = useState<VoiceOption[]>([]);
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    api<VoiceOption[]>("/api/v1/tts/voices").then(setVoices).catch(() => {});
  }, []);

  useEffect(() => {
    return () => audioRef.current?.pause();
  }, []);

  function togglePreview(voice: VoiceOption) {
    audioRef.current?.pause();
    if (playing === voice.voice_key) {
      setPlaying(null);
      return;
    }
    const audio = new Audio(previewUrl(voice.preview_url));
    audioRef.current = audio;
    audio.onended = () => setPlaying(null);
    void audio.play();
    setPlaying(voice.voice_key);
  }

  if (voices.length === 0) {
    return <div className="text-sm text-slate-400">音色加载中…</div>;
  }

  return (
    <div className="space-y-2">
      {voices.map((voice) => (
        <div
          key={voice.voice_key}
          className={`flex items-center gap-3 rounded-xl border p-3 ${
            value === voice.voice_key ? "border-sky-500 bg-sky-50" : "border-slate-200"
          }`}
        >
          <button
            type="button"
            onClick={() => onChange(voice.voice_key)}
            className="flex flex-1 flex-col items-start text-left"
          >
            <span className="font-medium">{voice.display_name}</span>
            <span className="text-xs text-slate-500">{voice.description}</span>
          </button>
          <button
            type="button"
            onClick={() => togglePreview(voice)}
            className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700"
          >
            {playing === voice.voice_key ? "停止" : "试听"}
          </button>
        </div>
      ))}
    </div>
  );
}
