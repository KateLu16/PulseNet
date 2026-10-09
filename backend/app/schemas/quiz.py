from datetime import datetime

from pydantic import BaseModel, Field


class QuizCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class QuizTimeLimitRequest(BaseModel):
    minutes: int = Field(gt=0, le=180)


class QuizSetupRequest(BaseModel):
    time_limit_sec: int | None = Field(default=None, gt=0, le=180 * 60)
    expected_students: int | None = Field(default=None, gt=0, le=500)
    id_prefix: str | None = Field(default=None, max_length=20)
    id_length: int | None = Field(default=None, gt=0, le=20)


class QuizResponse(BaseModel):
    id: int
    title: str
    status: str
    time_limit_sec: int | None = None
    expected_students: int | None = None
    id_prefix: str | None = None
    id_length: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    class Config:
        from_attributes = True
