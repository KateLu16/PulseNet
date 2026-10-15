from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.quiz_registration import QuizRegistration
from app.models.response import Response
from app.schemas.quiz import (
    QuizCreateRequest,
    QuizResponse,
    QuizSetupRequest,
)
from app.services.quiz_lifecycle import (
    finalize_expired_quiz,
    finalize_expired_quizzes,
)


router = APIRouter(
    prefix="/api/quizzes",
    tags=["Quizzes"],
)


# ============================================================
# CREATE QUIZ
# ============================================================

@router.post(
    "",
    response_model=QuizResponse,
)
def create_quiz(
    data: QuizCreateRequest,
    db: Session = Depends(get_db),
):
    quiz = Quiz(
        title=data.title,
        status="draft",
        current_question_number=None,
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return quiz


# ============================================================
# GET ALL QUIZZES
# ============================================================

@router.get(
    "",
    response_model=list[QuizResponse],
)
def get_quizzes(
    db: Session = Depends(get_db),
):
    # Lazy expiry so the dashboard reflects the backend-owned
    # deadline even when the BLE gateway is down.
    finalize_expired_quizzes(db)

    return (
        db.query(Quiz)
        .order_by(Quiz.id.desc())
        .all()
    )


# ============================================================
# GET QUIZ
# ============================================================

@router.get(
    "/{quiz_id}",
    response_model=QuizResponse,
)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    finalize_expired_quiz(db, quiz)

    return quiz


# ============================================================
# DELETE QUIZ
# Permanently removes a session together with its questions,
# registrations and responses. SQLite runs without enforced
# foreign keys (database.py enables no PRAGMA), so children
# are deleted explicitly, responses first (they also point
# at questions). Students/devices are shared across quizzes
# and are kept. A running quiz must be finished first.
# ============================================================

@router.delete(
    "/{quiz_id}",
)
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    if quiz.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Quiz is running — finish it before deleting",
        )

    title = quiz.title

    db.query(Response).filter(Response.quiz_id == quiz_id).delete()
    db.query(QuizRegistration).filter(QuizRegistration.quiz_id == quiz_id).delete()
    db.query(Question).filter(Question.quiz_id == quiz_id).delete()
    db.query(Quiz).filter(Quiz.id == quiz_id).delete()

    db.commit()

    return {
        "deleted": True,
        "quiz_id": quiz_id,
        "title": title,
    }


# ============================================================
# QUIZ SETUP
# Time limit, expected student count and student-ID format.
# Kahoot-style: the teacher configures everything BEFORE
# pushing the session to the devices.
# ============================================================

@router.post(
    "/{quiz_id}/setup",
)
def setup_quiz(
    quiz_id: int,
    data: QuizSetupRequest,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    if quiz.status not in ("draft", "lobby"):
        raise HTTPException(
            status_code=400,
            detail="Quiz can only be configured before it starts",
        )

    if data.time_limit_sec is not None:
        quiz.time_limit_sec = data.time_limit_sec

    if data.expected_students is not None:
        quiz.expected_students = data.expected_students

    if data.id_prefix is not None:
        quiz.id_prefix = data.id_prefix.strip() or None

    if data.id_length is not None:
        quiz.id_length = data.id_length

    db.commit()
    db.refresh(quiz)

    return quiz


# ============================================================
# LOBBY (Kahoot-style)
# draft -> lobby: session pushed to the devices; students
# enter their IDs while the teacher watches the count.
# ============================================================

@router.post(
    "/{quiz_id}/lobby",
)
def open_lobby(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    if quiz.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Only a draft quiz can be pushed to devices",
        )

    has_questions = (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .first()
        is not None
    )

    if not has_questions:
        raise HTTPException(
            status_code=400,
            detail="Quiz has no questions",
        )

    quiz.status = "lobby"

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": quiz.id,
        "status": quiz.status,
        "message": "Lobby opened — devices now accept student IDs",
    }


# ============================================================
# CANCEL LOBBY
# lobby -> draft: pull the session back for reconfiguration.
# ============================================================

@router.post(
    "/{quiz_id}/cancel",
)
def cancel_lobby(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    if quiz.status != "lobby":
        raise HTTPException(
            status_code=400,
            detail="Quiz is not in the lobby state",
        )

    quiz.status = "draft"

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": quiz.id,
        "status": quiz.status,
    }


# ============================================================
# START QUIZ
# ============================================================

@router.post(
    "/{quiz_id}/start",
)
def start_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
        .first()
    )

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    # Prevent starting an already running quiz
    if quiz.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Quiz is already running",
        )

    # Prevent restarting a finished quiz
    if quiz.status == "finished":
        raise HTTPException(
            status_code=400,
            detail="Quiz has already finished",
        )

    has_questions = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz_id,
        )
        .first()
        is not None
    )

    if not has_questions:
        raise HTTPException(
            status_code=400,
            detail="Quiz has no questions",
        )

    # --------------------------------------------------------
    # SELF-PACED MODEL: there is no teacher-driven "current
    # question". Every device receives Q1 at start and then
    # advances on its own after each accepted answer, so the
    # shared current_question_number pointer is not used.
    # --------------------------------------------------------

    quiz.status = "running"
    quiz.current_question_number = None
    quiz.started_at = datetime.utcnow()
    quiz.finished_at = None

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "status": quiz.status,
        "started_at": quiz.started_at,
    }


# ============================================================
# FINISH QUIZ
# ============================================================

@router.post(
    "/{quiz_id}/finish",
)
def finish_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
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

    quiz.status = "finished"
    quiz.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "status": quiz.status,
        "started_at": quiz.started_at,
        "finished_at": quiz.finished_at,
    }
