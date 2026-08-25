from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class VoiceOption(BaseModel):
    voice_key: str
    display_name: str
    description: str
    preview_url: str
    is_default: bool


class RecallQuestionOut(BaseModel):
    question: str
    answer: str


class SegmentOut(BaseModel):
    section: str
    origin: str
    narration: str


class ProgramSummary(BaseModel):
    id: str
    title: str
    status: str
    voice_key: str | None
    voice_name: str | None
    audio_duration_seconds: float | None
    audio_ready: bool
    source_name: str
    created_at: datetime


class ProgramDetail(BaseModel):
    id: str
    title: str
    status: str
    source_name: str
    voice_key: str | None
    voice_name: str | None
    audio_duration_seconds: float | None
    audio_ready: bool
    learning_objectives: list[str]
    segments: list[SegmentOut]
    summary: str
    knowledge_points: list[str]
    recall_questions: list[RecallQuestionOut]
    created_at: datetime
