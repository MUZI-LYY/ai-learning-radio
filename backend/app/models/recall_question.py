from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class RecallQuestion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recall_questions"

    program_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)

    program = relationship("Program", back_populates="recall_questions")
