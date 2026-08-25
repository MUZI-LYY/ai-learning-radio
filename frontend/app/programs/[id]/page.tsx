"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import AppIcon from "@/components/AppIcon";
import AudioPlayer from "@/components/AudioPlayer";
import BottomNav from "@/components/BottomNav";
import { api, audioUrl, type ProgramDetail } from "@/lib/api";
import { formatProgramCreatedAt, programPresentation } from "@/lib/program-presentation";
import { useMe } from "@/lib/use-me";

function RecallCard({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  const answerId = useId();
  return (
    <div className="recall-card">
      <div className="recall-card__header">
        <span className="recall-card__question">{question}</span>
        <button
          type="button"
          className="recall-card__toggle"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls={answerId}
        >
          <span className="recall-card__toggle-pill">
            <span>{open ? "收起" : "展开"}</span>
            <AppIcon name="chevron" size={13} />
          </span>
        </button>
      </div>
      {open && <p id={answerId} className="recall-card__answer">{answer}</p>}
    </div>
  );
}

export default function ProgramDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { unauthorized } = useMe();
  const [program, setProgram] = useState<ProgramDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (unauthorized) router.replace("/");
  }, [unauthorized, router]);

  useEffect(() => {
    api<ProgramDetail>(`/api/v1/programs/${params.id}`)
      .then(setProgram)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [params.id]);

  async function remove() {
    if (!confirm("确定删除这期节目吗？删除后无法恢复。")) return;
    try {
      await api(`/api/v1/programs/${params.id}`, { method: "DELETE" });
      router.replace("/programs");
    } catch (e) {
      alert(e instanceof Error ? e.message : "删除失败");
    }
  }

  if (error) {
    return <div className="min-h-dvh grid place-items-center text-slate-500">{error}</div>;
  }
  if (!program) {
    return <div className="min-h-dvh grid place-items-center text-slate-500">加载中…</div>;
  }

  const presentation = programPresentation(program.status, program.audio_ready);
  const transcript = [
    program.title,
    program.learning_objectives.length > 0
      ? `学习目标：${program.learning_objectives.join("；")}`
      : "",
    ...program.segments.map((segment) => {
      const prefix = segment.origin === "ai_supplement" ? "（AI 补充说明）" : "";
      return `${segment.section}：${prefix}${segment.narration}`;
    }),
    program.summary ? `总结复盘：${program.summary}` : "",
  ].filter(Boolean).join("\n\n");

  return (
    <main className="program-detail-page mx-auto max-w-md px-4 pb-24 pt-4">
      <header className="program-detail-page__back mb-4">
        <button onClick={() => router.back()} className="text-sm text-slate-500">
          ← 返回
        </button>
      </header>

      <h1 className="program-detail-page__title text-xl font-bold">{program.title}</h1>
      <div className="program-detail-page__meta">
        <time dateTime={program.created_at}>{formatProgramCreatedAt(program.created_at)}</time>
        <span className={`program-status program-status--${presentation.key}`}>
          {presentation.label}
        </span>
        {program.voice_name && <span>{program.voice_name}</span>}
      </div>

      <div className="program-detail-page__player">
        <AudioPlayer
          variant="detail"
          src={program.audio_ready ? audioUrl(program.id) : ""}
          transcript={transcript}
          disabled={!program.audio_ready}
        />
        {!program.audio_ready && (
          <p className={`program-detail-page__audio-state is-${presentation.key}`}>
            {presentation.key === "failed"
              ? "音频生成失败，仍可查看下方文字内容。"
              : "音频正在生成，完成后即可播放。"}
          </p>
        )}
      </div>

      {program.learning_objectives.length > 0 && (
        <section className="program-detail-page__section mt-6">
          <h2 className="mb-2 font-semibold">学习目标</h2>
          <ul className="list-disc pl-5 text-slate-700">
            {program.learning_objectives.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="program-detail-page__section mt-6">
        <h2 className="mb-2 font-semibold">核心知识点</h2>
        <ol className="space-y-2">
          {program.knowledge_points.map((kp, i) => (
            <li key={i} className="flex gap-2 rounded-xl border border-slate-200 bg-white p-3">
              <span className="font-semibold text-sky-600">{i + 1}.</span>
              <span>{kp}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="program-detail-page__section mt-6">
        <h2 className="mb-2 font-semibold">主动回忆</h2>
        <div className="space-y-2">
          {program.recall_questions.map((q, i) => (
            <RecallCard key={i} question={q.question} answer={q.answer} />
          ))}
        </div>
      </section>

      <button
        onClick={remove}
        className="program-detail-page__delete mt-8 w-full rounded-xl border border-rose-200 py-3 text-sm font-medium text-rose-600"
      >
        删除这期节目
      </button>

      <BottomNav />
    </main>
  );
}
