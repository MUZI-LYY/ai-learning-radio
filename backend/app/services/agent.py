"""AI 学习电台的单 Agent 门面。

当前落地的首个能力是把可信文章加工为可追溯的每日资讯脚本。Agent 只负责
内容判断与表达，不负责抓取、数据库、预算或文件写入；这些副作用由确定性
服务控制，避免模型绕过来源约束。后续产品能力继续挂在这个 Agent 上，不新增
相互协作的 Agent。
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.news import NewsItem, NewsScript
from app.services.prompts import load_prompt, prompt_version, render_prompt
from app.services.providers.llm import LLMProvider, LLMResult, get_llm_provider

LEARNING_RADIO_AGENT_VERSION = "learning_radio_agent_v1"
MAX_AGENT_ARTICLES = 6


@dataclass(frozen=True)
class AgentArticle:
    """已由确定性管线选中的一篇可信文章。"""

    title: str
    source_name: str
    source_url: str
    content: str
    published_at: str | None


class DailyNewsAgentItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    article_ref: str = Field(pattern=r"^A\d{2}$")
    narration: str = Field(min_length=1, max_length=600)


class DailyNewsAgentOutput(BaseModel):
    """LLM 内部输出；来源字段不交给模型填写。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=8, max_length=48)
    summary: str = Field(min_length=10, max_length=300)
    items: list[DailyNewsAgentItem] = Field(min_length=1, max_length=MAX_AGENT_ARTICLES)

    @field_validator("title")
    @classmethod
    def _reject_generic_title(cls, value: str) -> str:
        if value in {"今日资讯", "今日资讯速递", "新闻速递", "每日资讯"}:
            raise ValueError("title 必须是观点型标题，不能只写栏目名")
        return value

    @model_validator(mode="after")
    def _title_and_summary_must_differ(self) -> DailyNewsAgentOutput:
        if self.title == self.summary:
            raise ValueError("title 与 summary 不能完全相同")
        return self


@dataclass(frozen=True)
class DailyNewsAgentRun:
    script: NewsScript
    llm_result: LLMResult
    agent_version: str
    prompt_version: str


class LearningRadioAgent:
    """项目内唯一的产品 Agent；通过显式方法暴露不同能力。"""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_llm_provider()

    async def produce_daily_news(
        self,
        *,
        channel_name: str,
        program_date: str,
        articles: list[AgentArticle],
    ) -> DailyNewsAgentRun:
        if not 1 <= len(articles) <= MAX_AGENT_ARTICLES:
            raise ValueError(f"Agent 输入文章数必须为 1-{MAX_AGENT_ARTICLES} 条")

        refs = [f"A{index:02d}" for index in range(1, len(articles) + 1)]
        payload = [
            {
                "article_ref": ref,
                "title": article.title,
                "source_name": article.source_name,
                "published_at": article.published_at,
                "content": article.content,
            }
            for ref, article in zip(refs, articles, strict=True)
        ]
        result = await self.provider.complete_json(
            system=load_prompt("news_agent_system"),
            user=render_prompt(
                "news_script",
                channel_name=channel_name,
                program_date=program_date,
                articles_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ),
            json_schema=DailyNewsAgentOutput.model_json_schema(),
        )
        output = DailyNewsAgentOutput.model_validate(result.data)

        # 代码级门禁：必须逐条、按原顺序引用输入。模型不能增删、换序或伪造来源。
        output_refs = [item.article_ref for item in output.items]
        if output_refs != refs:
            raise ValueError(
                "每日资讯 Agent 返回的 article_ref 与输入不一致："
                f"期望 {refs}，实际 {output_refs}"
            )

        script_items = [
            NewsItem(
                title=article.title,
                source_name=article.source_name,
                source_url=article.source_url,
                narration=generated.narration,
            )
            for article, generated in zip(articles, output.items, strict=True)
        ]
        return DailyNewsAgentRun(
            script=NewsScript(title=output.title, summary=output.summary, items=script_items),
            llm_result=result,
            agent_version=LEARNING_RADIO_AGENT_VERSION,
            prompt_version=prompt_version("news_script"),
        )
