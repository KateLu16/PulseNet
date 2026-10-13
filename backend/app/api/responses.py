from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.quiz_registration import QuizRegistration
from app.models.response import Response
from app.models.student import Student
from app.schemas.response import (
    AnswerCreateRequest,
    AnswerResponse,
)
from app.services.quiz_lifecycle import finalize_expired_quiz


router = APIRouter(
    prefix="/api/responses",
    tags=["Responses"],
)


# ============================================================
# QUESTION ID PARSER
# ============================================================

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


# ============================================================
# SUBMIT ANSWER
# ============================================================

@router.post(
    "/answer",
    response_model=AnswerResponse,
)
def submit_answer(
    data: AnswerCreateRequest,
    db: Session = Depends(get_db),
):

    answer = data.answer.upper()

    # ========================================================
    # 1. CHECK DEVICE
    # ========================================================

    device = (
        db.query(Device)
        .filter(
            Device.device_mac == data.device_mac
        )
        .first()
    )

    if device is None:
        raise HTTPException(
            status_code=400,
            detail="Device not found",
        )

    # ========================================================
    # 2. CHECK STUDENT
    # ========================================================

    student = (
        db.query(Student)
        .filter(
            Student.student_id == data.student_id
        )
        .first()
    )

    if student is None:
        raise HTTPException(
            status_code=400,
            detail="Student not found",
        )

    # ========================================================
    # 3. CHECK QUIZ
    # ========================================================

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

    # ========================================================
    # 4. CHECK QUIZ STATUS
    #
    # The backend — not the gateway — owns the deadline: a
    # running quiz whose time limit expired is finished here
    # so late answers are rejected even if the gateway died.
    # ========================================================

    finalize_expired_quiz(db, quiz)

    if quiz.status != "running":
        raise HTTPException(
            status_code=400,
            detail="Quiz is not running",
        )

    # ========================================================
    # 5. CHECK QUIZ REGISTRATION
    #
    # Student and Device must be associated specifically
    # within this quiz.
    #
    # This replaces the old logic:
    #
    #     Device.student_id
    #
    # A physical device can therefore be reused by another
    # student in another quiz/session.
    # ========================================================

    registration = (
        db.query(QuizRegistration)
        .filter(
            QuizRegistration.quiz_id
            == data.quiz_id,

            QuizRegistration.device_id
            == device.id,

            QuizRegistration.student_id
            == student.id,
        )
        .first()
    )

    if registration is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "Student is not registered "
                "to this device for this quiz"
            ),
        )

    # ========================================================
    # 6. CONVERT QUESTION ID
    #
    # Examples:
    #
    #     Q01 -> 1
    #     Q02 -> 2
    #     1   -> 1
    # ========================================================

    question_number = parse_question_number(
        data.question_id
    )

    # ========================================================
    # 7. FIND QUESTION
    # ========================================================

    question = (
        db.query(Question)
        .filter(
            Question.quiz_id == data.quiz_id,
            Question.question_number
            == question_number,
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question does not belong to this quiz",
        )

    # ========================================================
    # 8. SELF-PACED QUIZ
    #
    # Students answer at their own pace, so ANY question of
    # this quiz is accepted — not just the teacher's
    # current_question_number.
    # ========================================================

    # ========================================================
    # 9. CHECK ANSWER
    # ========================================================

    is_correct = (
        answer
        == question.correct_answer.upper()
    )

    # ========================================================
    # 10. SAVE RESPONSE (UPSERT — NEWEST SEQUENCE WINS)
    #
    # A student may press a key twice or change their mind.
    # Instead of inserting a duplicate row (which would
    # double-count in analytics), update the existing
    # response for this (quiz, question, student).
    #
    # The device stamps every answer attempt with a rising
    # `sequence` counter. That makes the upsert safe against
    # BLE reordering and retries:
    #
    #   sequence >  stored  -> newer attempt, overwrite
    #   sequence == stored  -> duplicate delivery of the same
    #                          attempt (ACK was lost) — return
    #                          the stored answer unchanged
    #   sequence <  stored  -> an OLD delayed packet; the
    #                          stored answer is newer, ignore
    #                          the packet (it must NOT roll
    #                          the answer back)
    #
    # Answers without a sequence (older firmware) keep the
    # plain last-write-wins behaviour.
    # ========================================================

    existing_response = (
        db.query(Response)
        .filter(
            Response.quiz_id == data.quiz_id,
            Response.question_id == question.id,
            Response.student_id == data.student_id,
        )
        .first()
    )

    if existing_response is not None:

        stale_or_duplicate = (
            data.sequence is not None
            and existing_response.sequence is not None
            and data.sequence <= existing_response.sequence
        )

        if stale_or_duplicate:

            status = (
                "DUPLICATE"
                if data.sequence == existing_response.sequence
                else "STALE_IGNORED"
            )

            response = existing_response

            # Keep the device's score display in sync with
            # what is actually stored.
            device.status = "online"
            device.last_seen = datetime.utcnow()
            db.commit()
            db.refresh(response)

            return AnswerResponse(
                success=True,
                status=status,
                quiz_id=response.quiz_id,
                question_id=response.question_id,
                student_id=response.student_id,
                answer=response.answer,
                correct=response.is_correct,
                answered_at=response.answered_at,
            )

        existing_response.answer = answer
        existing_response.is_correct = is_correct
        existing_response.device_mac = data.device_mac
        existing_response.sequence = data.sequence
        existing_response.answered_at = datetime.utcnow()

        response = existing_response
        status = "UPDATED"

    else:

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
        status = "ACCEPTED"

    # ========================================================
    # 11. UPDATE DEVICE ACTIVITY
    # ========================================================

    device.status = "online"
    device.last_seen = datetime.utcnow()

    # ========================================================
    # 12. COMMIT
    # ========================================================

    db.commit()

    db.refresh(response)

    # ========================================================
    # 13. RETURN RESULT
    # ========================================================

    return AnswerResponse(
        success=True,
        status=status,
        quiz_id=response.quiz_id,
        question_id=response.question_id,
        student_id=response.student_id,
        answer=response.answer,
        correct=response.is_correct,
        answered_at=response.answered_at,
    )
