from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.response import Response
from app.models.student import Student
from app.schemas.response import AnswerCreateRequest, AnswerResponse


router = APIRouter(
    prefix="/api/responses",
    tags=["Responses"],
)


def parse_question_number(question_id: str) -> int:
    value = question_id.strip().upper()

    if value.startswith("Q"):
        value = value[1:]

    try:
        number = int(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid question_id",
        ) from exc

    if number < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid question_id",
        )

    return number


@router.post(
    "/answer",
    response_model=AnswerResponse,
)
def submit_answer(
    data: AnswerCreateRequest,
    db: Session = Depends(get_db),
):
    answer = data.answer.upper()

    device = (
        db.query(Device)
        .filter(Device.device_mac == data.device_mac)
        .first()
    )

    if device is None or device.student_id is None:
        raise HTTPException(
            status_code=400,
            detail="Device is not registered",
        )

    student = (
        db.query(Student)
        .filter(Student.id == device.student_id)
        .first()
    )

    if student is None or student.student_id != data.student_id:
        raise HTTPException(
            status_code=400,
            detail="Student ID does not match registered device",
        )

    quiz = (
        db.query(Quiz)
        .filter(Quiz.status == "running")
        .order_by(Quiz.id.desc())
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=400,
            detail="No quiz is currently running",
        )

    question_number = parse_question_number(data.question_id)

    question = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz.id,
            Question.question_number == question_number,
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=400,
            detail="Question does not belong to the active quiz",
        )

    if (
        quiz.current_question_number is not None
        and question.question_number != quiz.current_question_number
    ):
        raise HTTPException(
            status_code=400,
            detail="Question is not the current quiz question",
        )

    is_correct = answer == question.correct_answer.upper()

    response = Response(
        quiz_id=quiz.id,
        question_id=question.id,
        student_id=data.student_id,
        device_mac=data.device_mac,
        answer=answer,
        is_correct=is_correct,
        sequence=data.sequence,
        answered_at=datetime.utcnow(),
    )

    db.add(response)

    device.status = "online"
    device.last_seen = datetime.utcnow()

    db.commit()
    db.refresh(response)

    return AnswerResponse(
        success=True,
        status="ACCEPTED",
        quiz_id=quiz.id,
        question_id=question.id,
        student_id=data.student_id,
        answer=answer,
        correct=is_correct,
        answered_at=response.answered_at,
    )
