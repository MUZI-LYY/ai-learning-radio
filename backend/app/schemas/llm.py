"""LLM 结构化输出契约（Pydantic 二次校验）。

数量约束在此强制：正好 5 个知识点、正好 3 道回忆题；
segments.origin 只允许 source 或 ai_supplement。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

SegmentOrigin = Literal["source", "ai_supplement"]

# segments 必须包含的中间章节（学习目标在 learning_objectives，总结在 summary）
REQUIRED_SECTIONS = [
    "背景与概念",
    "分点解释",
    "示例或类比",
]


class ChunkPoint(BaseModel):
    kind: Literal["concept", "argument", "example"]
    content: str = Field(min_length=1, max_length=280)
    source_ref: str = Field(default="", max_length=80)  # 来源片段位置（章节/段落），可为空


class ChunkSummary(BaseModel):
    chunk_index: int = Field(ge=0)
    points: list[ChunkPoint] = Field(min_length=1, max_length=12)


class LessonSegment(BaseModel):
    section: str
    origin: SegmentOrigin
    narration: str = Field(min_length=1)


class RecallQuestion(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class LessonResult(BaseModel):
    title: str = Field(min_length=1)
    learning_objectives: list[str] = Field(min_length=1)
    segments: list[LessonSegment] = Field(min_length=1)
    summary: str = Field(min_length=1)
    knowledge_points: list[str]
    recall_questions: list[RecallQuestion]

    @field_validator("knowledge_points")
    @classmethod
    def _exactly_five_points(cls, v: list[str]) -> list[str]:
        if len(v) != 5:
            raise ValueError(f"knowledge_points 必须正好 5 条，当前 {len(v)} 条")
        if any(not p.strip() for p in v):
            raise ValueError("knowledge_points 不能包含空内容")
        return v

    @field_validator("recall_questions")
    @classmethod
    def _exactly_three_questions(cls, v: list[RecallQuestion]) -> list[RecallQuestion]:
        if len(v) != 3:
            raise ValueError(f"recall_questions 必须正好 3 道，当前 {len(v)} 道")
        return v

    @field_validator("segments")
    @classmethod
    def _required_sections(cls, v: list[LessonSegment]) -> list[LessonSegment]:
        sections = [s.section for s in v]
        for required in REQUIRED_SECTIONS:
            if required not in sections:
                raise ValueError(f"缺少必需教学章节: {required}")
        return v
