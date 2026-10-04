from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("quizzes.id"),
        nullable=False,
        index=True,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    device_mac: Mapped[str] = mapped_column(
        String(17),
        nullable=False,
        index=True,
    )

    answer: Mapped[str] = mapped_column(
        String(1),
        nullable=False,
    )

    is_correct: Mapped[bool] = mapped_column(
        nullable=False,
    )

    sequence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

