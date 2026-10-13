from pydantic import BaseModel, Field

# Device display budget. The TFT shows long content by
# scrolling, but the ESP32 document buffer (MAX_DOC_ROWS) and
# the BLE fragmentation window bound how MUCH text can be
# pushed per question. These limits keep the worst case
# (400-char question + 4 x 160-char options) inside the
# device buffer with headroom.
QUESTION_TEXT_MAX_LENGTH = 400
OPTION_MAX_LENGTH = 160


class QuestionCreateRequest(BaseModel):
    question_number: int = Field(ge=1)
    question_text: str = Field(
        min_length=1,
        max_length=QUESTION_TEXT_MAX_LENGTH,
    )
    option_a: str = Field(
        min_length=1,
        max_length=OPTION_MAX_LENGTH,
    )
    option_b: str = Field(
        min_length=1,
        max_length=OPTION_MAX_LENGTH,
    )
    option_c: str = Field(
        min_length=1,
        max_length=OPTION_MAX_LENGTH,
    )
    option_d: str = Field(
        min_length=1,
        max_length=OPTION_MAX_LENGTH,
    )
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
