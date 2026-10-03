from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    device_mac: Mapped[str] = mapped_column(
        String(17),
        unique=True,
        nullable=False,
        index=True,
    )

    device_code: Mapped[str | None] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
    )

    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="offline",
        nullable=False,
    )

    battery: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

