from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.response import Response
from app.models.student import Student
from app.schemas.response import (
    AnswerCreateRequest,
    AnswerResponse,
)


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
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid question_id",
        )

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

    # --------------------------------------------------------
    # 1. Check device
    # --------------------------------------------------------

    device = (
        db.query(Device)
        .filter(
            Device.device_mac == data.device_mac
        )
        .first()
    )

    if device is None or device.student_id is None:
        raise HTTPException(
            status_code=400,
            detail="Device is not registered",
        )

    # --------------------------------------------------------
    # 2. Check student-device relationship
    # --------------------------------------------------------

    student = (
        db.query(Student)
        .filter(
            Student.id == device.student_id
        )
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=400,
            detail="Registered student not found",
        )

    if student.student_id != data.student_id:
        raise HTTPException(
            status_code=400,
            detail="Student ID does not match registered device",
        )

    # --------------------------------------------------------
    # 3. Check quiz
    # --------------------------------------------------------

    quiz = (
        db.query(Quiz)
        .filter(
            Quiz.id == data.quiz_id
        )
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    if quiz.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Quiz is not running",
        )

    # --------------------------------------------------------
    # 4. Convert Q01 -> question number 1
    # --------------------------------------------------------

    question_number = parse_question_number(
        data.question_id
    )

    # --------------------------------------------------------
    # 5. Find question
    # --------------------------------------------------------

    question = (
        db.query(Question)
        .filter(
            Question.quiz_id == data.quiz_id,
            Question.question_number == question_number,
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question does not belong to this quiz",
        )

    # --------------------------------------------------------
    # 6. Check current question
    # --------------------------------------------------------

    if (
        quiz.current_question_number is not None
        and question.question_number
        != quiz.current_question_number
    ):
        raise HTTPException(
            status_code=400,
            detail="Question is not the current quiz question",
        )

    # --------------------------------------------------------
    # 7. Check answer
    # --------------------------------------------------------

    is_correct = (
        answer == question.correct_answer.upper()
    )

    # --------------------------------------------------------
    # 8. Save response
    # --------------------------------------------------------

    response = Response(
        quiz_id=data.quiz_id,
        question_id=question.id,
        student_id=data.student_id,
        device_mac=data.device_mac,
        answer=answer,
        is_correct=is_correct,
        sequence=data.sequence,
        answered_at=datetime.utcnow(),
    )

    db.add(response)

    # Update device activity
    device.status = "online"
    device.last_seen = datetime.utcnow()

    db.commit()
    db.refresh(response)

    # --------------------------------------------------------
    # 9. Return result
    # --------------------------------------------------------

    return AnswerResponse(
        success=True,
        status="ACCEPTED",
        quiz_id=response.quiz_id,
        question_id=response.question_id,
        student_id=response.student_id,
        answer=response.answer,
        correct=response.is_correct,
        answered_at=response.answered_at,
    )
