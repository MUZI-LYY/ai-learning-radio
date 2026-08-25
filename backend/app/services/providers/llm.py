"""LLM provider：mock 与火山方舟真实适配器。

统一入口 `get_llm_provider()` 按配置返回实例。真实实现使用固定模型、
关闭深度思考、通过 JSON Schema 生成结构化内容。
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.errors import ApiError, ErrorCode

# 保守单价（元 / 千 token），真实价格确认前用于估值
_ESTIMATED_PRICE_PER_1K_TOKENS_CNY = 0.02


@dataclass
class LLMResult:
    data: dict
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_cny: float = 0.0

    def __post_init__(self) -> None:
        if self.estimated_cost_cny == 0.0:
            total_k = (self.input_tokens + self.output_tokens) / 1000.0
            self.estimated_cost_cny = round(total_k * _ESTIMATED_PRICE_PER_1K_TOKENS_CNY, 6)


class LLMProvider(ABC):
    @abstractmethod
    async def complete_json(
        self, *, system: str, user: str, json_schema: dict
    ) -> LLMResult:
        """按 JSON Schema 生成结构化内容并返回校验前的原始 dict。"""


class MockLLMProvider(LLMProvider):
    """确定性 mock：按 schema title 返回合法结构，不产生费用。"""

    async def complete_json(self, *, system: str, user: str, json_schema: dict) -> LLMResult:
        title = json_schema.get("title", "")
        if title == "ChunkSummary":
            data = {
                "chunk_index": 0,
                "points": [
                    {"kind": "concept", "content": "这是一个 mock 概念要点", "source_ref": "第1段"},
                    {"kind": "example", "content": "这是一个 mock 示例", "source_ref": "第2段"},
                ],
            }
        elif title == "DailyNewsAgentOutput":
            refs = re.findall(r'"article_ref"\s*:\s*"(A\d{2})"', user)
            refs = list(dict.fromkeys(refs)) or [f"A{index:02d}" for index in range(1, 6)]
            data = {
                "title": "推理效率与工作流设计正在决定 AI 产品落地速度",
                "summary": (
                    "今日多条动态共同指向一个趋势：AI 与科技产品正在从能力展示"
                    "转向更稳定、更可复用的实际工作流。"
                ),
                "items": [
                    {
                        "article_ref": ref,
                        "narration": "这是一条 mock 新闻口播。",
                    }
                    for ref in refs
                ],
            }
        else:
            data = {
                "title": "Mock 教学节目：私人学习播客最小闭环",
                "learning_objectives": ["理解第一阶段最小闭环的构成"],
                "segments": [
                    {"section": "背景与概念", "origin": "source", "narration": "背景与概念说明。"},
                    {"section": "分点解释", "origin": "source", "narration": "分点解释正文。"},
                    {
                        "section": "示例或类比",
                        "origin": "ai_supplement",
                        "narration": "用一个例子帮助理解。",
                    },
                ],
                "summary": "总结复盘。",
                "knowledge_points": ["要点一", "要点二", "要点三", "要点四", "要点五"],
                "recall_questions": [
                    {"question": "问题一？", "answer": "答案一。"},
                    {"question": "问题二？", "answer": "答案二。"},
                    {"question": "问题三？", "answer": "答案三。"},
                ],
            }
        return LLMResult(data=data, model="mock")


class VolcArkLLMProvider(LLMProvider):
    """火山方舟 OpenAI 兼容接口。"""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete_json(self, *, system: str, user: str, json_schema: dict) -> LLMResult:
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        payload = _request_payload(
            model=self.settings.llm_model_primary,
            system=system,
            user=user,
            json_schema=json_schema,
            thinking_disabled=self.settings.llm_thinking_mode == "disabled",
            max_output_tokens=self.settings.llm_max_output_tokens,
        )

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
            response = await client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        usage = body.get("usage", {})
        return LLMResult(
            data=_parse_json_response(body),
            model=self.settings.llm_model_primary,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )


def _request_payload(
    *,
    model: str,
    system: str,
    user: str,
    json_schema: dict,
    thinking_disabled: bool,
    max_output_tokens: int,
) -> dict:
    """构造受控的结构化输出请求，并显式给出输出 token 预算。"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": json_schema.get("title", "result"), "schema": json_schema},
        },
        "temperature": 0.7,
        "max_tokens": max_output_tokens,
    }
    if thinking_disabled:
        payload["thinking"] = {"type": "disabled"}
    return payload


def _parse_json_response(body: dict) -> dict:
    """读取模型响应，优先识别服务端声明的长度截断。"""
    try:
        choice = body["choices"][0]
        finish_reason = choice.get("finish_reason")
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ApiError(ErrorCode.LLM_OUTPUT_INVALID) from exc

    if finish_reason in {"length", "max_tokens"}:
        raise ApiError(ErrorCode.LLM_OUTPUT_TRUNCATED)
    if not isinstance(content, str) or not content.strip():
        raise ApiError(ErrorCode.LLM_OUTPUT_INVALID)
    return _parse_json_content(content)


def _parse_json_content(content: str) -> dict:
    """兼容 Markdown 围栏，并把解析异常转换为安全、稳定的错误码。"""

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        is_truncated = exc.msg.startswith("Unterminated string") or (
            len(text) >= 256 and exc.pos >= len(text) - 64
        )
        code = ErrorCode.LLM_OUTPUT_TRUNCATED if is_truncated else ErrorCode.LLM_OUTPUT_INVALID
        raise ApiError(code) from exc
    if not isinstance(parsed, dict):
        raise ApiError(ErrorCode.LLM_OUTPUT_INVALID)
    return parsed


def get_llm_provider() -> LLMProvider:
    provider = get_settings().llm_provider
    if provider == "volcark":
        return VolcArkLLMProvider()
    return MockLLMProvider()
