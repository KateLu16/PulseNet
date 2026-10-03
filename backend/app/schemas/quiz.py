from pydantic import BaseModel, Field


class QuizCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class QuizResponse(BaseModel):
    id: int
    title: str
    status: str

    class Config:
        from_attributes = True
