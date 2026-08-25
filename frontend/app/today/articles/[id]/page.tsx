"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import AppIcon from "@/components/AppIcon";
import { api, type NewsArticleDetail } from "@/lib/api";
import { useMe } from "@/lib/use-me";

function articleParagraphs(content: string): string[] {
  const sentences = content.match(/[^。！？.!?]+[。！？.!?]?/g)?.map((item) => item.trim()).filter(Boolean) ?? [content];
  const paragraphs: string[] = [];
  for (let index = 0; index < sentences.length; index += 3) paragraphs.push(sentences.slice(index, index + 3).join(""));
  return paragraphs;
}

export default function NewsArticlePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { me, loading } = useMe();
  const [article, setArticle] = useState<NewsArticleDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!me || !params.id) return;
    api<NewsArticleDetail>(`/api/v1/news/articles/${params.id}`)
      .then(setArticle)
      .catch(() => setError("这篇文章暂时无法读取。"));
  }, [me, params.id]);

  const paragraphs = useMemo(() => articleParagraphs(article?.content ?? ""), [article?.content]);
  if (loading || (!article && !error)) return <div className="detail-loading">正在打开阅读页…</div>;
  if (error || !article) return <div className="detail-error"><p>{error}</p><button type="button" onClick={() => router.back()}>返回</button></div>;

  return (
    <main className="reader-page">
      <header className="detail-header detail-header--reader">
        <button type="button" onClick={() => router.back()} aria-label="返回"><AppIcon name="chevron" size={22} /></button>
        <span>阅读来源</span>
        <a href={article.source_url} target="_blank" rel="noreferrer" aria-label="打开原文"><AppIcon name="external" size={19} /></a>
      </header>
      <article>
        <header className="reader-page__title">
          <div className="reader-page__meta">
            <span>{article.source_name}</span>
            {article.published_at && <time>{new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(article.published_at))}</time>}
          </div>
          <h1>{article.title}</h1>
        </header>
        {article.image_url && <div className="reader-page__image" role="img" aria-label="文章主图" style={{ backgroundImage: `url(${article.image_url})` }} />}
        <p className="reader-page__summary">{article.summary}</p>
        <div className="reader-page__content">{paragraphs.map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 12)}`}>{paragraph}</p>)}</div>
        <footer className="reader-page__source">
          <span>{article.content_is_complete ? "正文由公开页面提取，排版经过适配。" : "当前仅采集到部分正文。"}</span>
          <a href={article.source_url} target="_blank" rel="noreferrer">前往原网站阅读全文 <AppIcon name="external" size={17} /></a>
        </footer>
      </article>
    </main>
  );
}
