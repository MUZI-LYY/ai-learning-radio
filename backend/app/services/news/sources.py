"""新闻来源抓取：mock 与真实 RSS 适配器。

开发期使用 mock 返回确定性文章；真实 RSS 解析在配置可信源后使用。
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from html import unescape

import feedparser
import httpx
import trafilatura

from app.models.news_source import NewsSource

_TAG_RE = re.compile(r"<[^>]+>")

# 每个来源最多抓取的文章数与每篇正文上限（字符）
_MAX_ENTRIES_PER_SOURCE = 8
_MAX_CONTENT_CHARS = 30_000
_ARTICLE_TIMEOUT_SECONDS = 10
_META_TAG_RE = re.compile(r"<meta\s+[^>]*>", re.IGNORECASE)
_META_ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.IGNORECASE | re.DOTALL)

_MOCK_ARTICLES: dict[str, list[dict]] = {
    "ai_frontier": [
        (
            "大模型推理成本再降，长上下文成为新焦点",
            "某头部实验室发布新一代模型，长上下文窗口与推理成本成为关注点。",
        ),
        (
            "开源社区发布多模态评测基准",
            "新基准覆盖图文理解与推理，用于横向对比主流开源模型。",
        ),
        (
            "智能体编排框架获得新一轮采用",
            "多家团队开始用确定性状态机替代自由式工具调用，降低线上事故率。",
        ),
        ("端侧模型落地加速", "手机与边缘设备上的小型模型推理性能持续提升。"),
        ("AI 编程助手进入成熟期", "主流编码助手开始强调可复现与工程化能力。"),
    ],
    "tech_product": [
        ("折叠屏出货量稳步上升", "主流厂商加快折叠屏迭代，轻薄化与续航成为卖点。"),
        ("新一代无线耳机主打空间音频", "空间音频与低延迟成为高端耳机的核心卖点。"),
        ("智能手表健康监测功能扩展", "多品牌手表加入更多健康指标跟踪与异常提醒。"),
        ("充电协议走向统一", "多品牌推进统一快充协议，减少配件碎片化。"),
        ("家用机器人开始进入量产", "面向家庭场景的服务机器人进入小批量交付阶段。"),
    ],
    "startup_business": [
        ("早期融资市场回暖", "多个赛道早期融资活跃度回升，估值趋于理性。"),
        ("SaaS 公司转向盈利优先", "一批 SaaS 公司放缓扩张，把自由现金流放在首位。"),
        ("出海团队聚焦本地化合规", "本地化与合规能力成为出海产品的新门槛。"),
        ("创作者经济出现新平台", "新平台尝试更透明的分成机制吸引中小创作者。"),
        ("供应链韧性成为投资主题", "供应链多元化与韧性成为创业与投资共同关注的方向。"),
    ],
}


def fetch_source_articles(source: NewsSource) -> list[dict]:
    """抓取单个来源文章，并保留摘要、主图与可阅读正文。"""
    if source.kind == "mock":
        return _mock_articles(source)
    if source.kind == "rss":
        return _rss_articles(source)
    return []


def _rss_articles(source: NewsSource) -> list[dict]:
    feed = feedparser.parse(source.url)
    result: list[dict] = []
    for entry in feed.entries[:_MAX_ENTRIES_PER_SOURCE]:
        title = (entry.get("title") or "").strip()
        url = entry.get("link") or ""
        if not title or not url:
            continue
        summary = ""
        if entry.get("content"):
            summary = entry.content[0].get("value", "")
        else:
            summary = entry.get("summary") or entry.get("description") or ""
        summary = _clean_text(summary)

        # 抓取原文正文与开放图谱主图；正文失败时回退 RSS 摘要
        full, page_image = extract_article_page(url)
        content = full if len(full) > len(summary) else summary
        content = content[:_MAX_CONTENT_CHARS]
        image_url = _entry_image(entry) or page_image

        published_at = _parse_published(entry)
        result.append(
            {
                "title": title,
                "url": url,
                "summary": summary,
                "content": content,
                "image_url": image_url,
                "content_is_complete": bool(full) and len(full) <= _MAX_CONTENT_CHARS,
                "published_at": published_at,
            }
        )
    return result


def _clean_text(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    return re.sub(r"\s+", " ", text).strip()


def extract_article_page(url: str) -> tuple[str, str | None]:
    """抓取文章正文与主图；失败时返回空值，让调用方回退 RSS。"""
    try:
        response = httpx.get(
            url,
            timeout=_ARTICLE_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if response.status_code != 200:
            return "", None
        text = trafilatura.extract(response.text, include_comments=False, include_tables=False)
        return _clean_text(text or ""), _meta_image(response.text)
    except Exception:  # noqa: BLE001 - 抓取失败不阻断，回退摘要
        return "", None


def _meta_image(html: str) -> str | None:
    """读取 og:image / twitter:image，兼容属性顺序差异。"""
    for tag in _META_TAG_RE.findall(html):
        attrs = {
            name.lower(): unescape(value.strip()) for name, _, value in _META_ATTR_RE.findall(tag)
        }
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in {"og:image", "og:image:url", "twitter:image"} and attrs.get("content"):
            return attrs["content"]
    return None


def _entry_image(entry) -> str | None:
    for field in ("media_content", "media_thumbnail"):
        values = entry.get(field) or []
        if values and values[0].get("url"):
            return values[0]["url"]
    for enclosure in entry.get("enclosures") or []:
        if str(enclosure.get("type", "")).startswith("image/") and enclosure.get("href"):
            return enclosure["href"]
    return None


def _parse_published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime(*value[:6], tzinfo=UTC)
    return None


def _mock_articles(source: NewsSource) -> list[dict]:
    now = datetime.now(UTC)
    items = _MOCK_ARTICLES.get(source.channel, [])
    result = []
    for index, (title, content) in enumerate(items):
        result.append(
            {
                "title": title,
                "url": f"https://mock.example/{source.channel}/{source.id[:8]}/{index}",
                "summary": content,
                "content": content,
                "image_url": None,
                "content_is_complete": True,
                "published_at": now - timedelta(hours=index + 1),
            }
        )
    return result
