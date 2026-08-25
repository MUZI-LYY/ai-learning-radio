"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppIcon from "@/components/AppIcon";
import { api, type NewsProgramDetail } from "@/lib/api";
import { useMe } from "@/lib/use-me";

export default function NewsSourcesPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { me, loading, unauthorized } = useMe();
  const [program, setProgram] = useState<NewsProgramDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (unauthorized) router.replace("/");
  }, [unauthorized, router]);

  useEffect(() => {
    if (!me || !params.id) return;
    api<NewsProgramDetail>(`/api/v1/news/programs/${params.id}`)
      .then(setProgram)
      .catch(() => setError("没有找到这期节目的来源。"));
  }, [me, params.id]);

  if (loading || (!program && !error)) return <div className="detail-loading">正在整理本期来源…</div>;
  if (error || !program) return <div className="detail-error"><p>{error}</p><button type="button" onClick={() => router.back()}>返回</button></div>;

  return (
    <main className="sources-page">
      <header className="detail-header">
        <button type="button" onClick={() => router.back()} aria-label="返回"><AppIcon name="chevron" size={22} /></button>
        <span>本期来源</span><i />
      </header>
      <section className="sources-page__intro">
        <h1>{program.title}</h1>
        <p>{program.summary}</p>
        <div className="sources-page__meta">
          <span>{program.channel_name}</span>
          <time>{program.program_date}</time>
        </div>
        <p className="sources-page__count">{program.items.length}篇来源文章</p>
      </section>
      <ol className="article-card-list">
        {program.items.map((item, index) => {
          const content = (
            <>
              <div className="article-card__image" style={item.image_url ? { backgroundImage: `url(${item.image_url})` } : undefined}>
                {!item.image_url && <span>{String(index + 1).padStart(2, "0")}</span>}
              </div>
              <div className="article-card__copy">
                <h2>{item.title}</h2>
                <p>{item.excerpt}</p>
                <div className="article-card__meta">
                  <span className="article-card__source">{item.source_name}</span>
                  <span className="article-card__read">阅读全文 <AppIcon name="chevron" size={15} /></span>
                </div>
              </div>
            </>
          );
          return (
            <li key={item.source_url}>
              <span className="article-card__number" aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              {item.article_id ? <Link href={`/today/articles/${item.article_id}`} className="article-card">{content}</Link> : <a href={item.source_url} target="_blank" rel="noreferrer" className="article-card">{content}</a>}
            </li>
          );
        })}
      </ol>
    </main>
  );
}
