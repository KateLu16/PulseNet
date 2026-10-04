from datetime import datetime

from pydantic import BaseModel, Field


class AnswerCreateRequest(BaseModel):
    student_id: str = Field(
        min_length=1,
        max_length=20,
    )

    device_mac: str = Field(
        min_length=17,
        max_length=17,
    )

    quiz_id: int = Field(
        ge=1,
    )

    question_id: str = Field(
        min_length=1,
        max_length=10,
    )

    answer: str = Field(
        pattern="^[ABCDabcd]$",
    )

    sequence: int | None = Field(
        default=None,
        ge=1,
    )


class AnswerResponse(BaseModel):
    success: bool
    status: str
    quiz_id: int
    question_id: int
    student_id: str
    answer: str
    correct: bool
    answered_at: datetime
