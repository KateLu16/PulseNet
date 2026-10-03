from pydantic import BaseModel, Field


class QuestionCreateRequest(BaseModel):
    question_number: int = Field(ge=1)
    question_text: str = Field(min_length=1)
    option_a: str = Field(min_length=1)
    option_b: str = Field(min_length=1)
    option_c: str = Field(min_length=1)
    option_d: str = Field(min_length=1)
    correct_answer: str = Field(pattern="^[ABCD]$")


class QuestionResponse(BaseModel):
    id: int
    quiz_id: int
    question_number: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str

    class Config:
        from_attributes = True
