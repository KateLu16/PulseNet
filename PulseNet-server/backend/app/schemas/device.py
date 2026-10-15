from pydantic import BaseModel, Field


class DeviceRegisterRequest(BaseModel):
    student_id: str = Field(
        min_length=1,
        max_length=20,
    )

    device_mac: str = Field(
        min_length=17,
        max_length=17,
    )

    device_code: str | None = Field(
        default=None,
        max_length=20,
    )

    quiz_id: int = Field(
        ge=1,
    )

class DeviceRegisterResponse(BaseModel):
    success: bool
    message: str
    student_id: str
    device_mac: str
    device_code: str | None
    quiz_id: int
