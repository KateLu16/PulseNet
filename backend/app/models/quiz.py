from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
    )

    current_question_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Whole-quiz time limit in seconds (shown on the device
    # as a countdown; the quiz auto-finishes when it expires).
    time_limit_sec: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Lobby settings (Kahoot-style): how many students the
    # teacher expects, and the student-ID format used for
    # device-side validation.
    expected_students: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    id_prefix: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    id_length: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
