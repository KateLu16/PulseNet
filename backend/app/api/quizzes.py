from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Quiz
from app.models.question import Question
from app.schemas.quiz import QuizCreateRequest, QuizResponse


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

    return quiz


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

    # Find the first question
    first_question = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz_id,
        )
        .order_by(
            Question.question_number.asc()
        )
        .first()
    )

    if first_question is None:
        raise HTTPException(
            status_code=400,
            detail="Quiz has no questions",
        )

    # Start quiz
    quiz.status = "running"
    quiz.current_question_number = first_question.question_number
    quiz.started_at = datetime.utcnow()
    quiz.finished_at = None

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "status": quiz.status,
        "current_question_number": quiz.current_question_number,
        "started_at": quiz.started_at,
    }


# ============================================================
# GET CURRENT QUESTION
# ============================================================

@router.get(
    "/{quiz_id}/current",
)
def get_current_question(
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

    if quiz.current_question_number is None:
        raise HTTPException(
            status_code=400,
            detail="No current question",
        )

    question = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz_id,
            Question.question_number
            == quiz.current_question_number,
        )
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Current question not found",
        )

    # IMPORTANT:
    # Do NOT send correct_answer to the student-facing API.
    return {
        "quiz_id": quiz.id,
        "question_id": question.id,
        "question_number": question.question_number,
        "question_text": question.question_text,
        "option_a": question.option_a,
        "option_b": question.option_b,
        "option_c": question.option_c,
        "option_d": question.option_d,
    }


# ============================================================
# NEXT QUESTION
# ============================================================

@router.post(
    "/{quiz_id}/next",
)
def next_question(
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

    if quiz.current_question_number is None:
        raise HTTPException(
            status_code=400,
            detail="No current question",
        )

    # Find the next question by question_number
    next_question = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz_id,
            Question.question_number
            > quiz.current_question_number,
        )
        .order_by(
            Question.question_number.asc()
        )
        .first()
    )

    # No more questions
    if next_question is None:
        return {
            "quiz_id": quiz.id,
            "status": quiz.status,
            "current_question_number":
                quiz.current_question_number,
            "has_next": False,
            "message": "No more questions",
        }

    # Move to next question
    quiz.current_question_number = (
        next_question.question_number
    )

    db.commit()
    db.refresh(quiz)

    return {
        "quiz_id": quiz.id,
        "status": quiz.status,
        "current_question_number":
            quiz.current_question_number,
        "has_next": True,
        "question": {
            "question_id": next_question.id,
            "question_number":
                next_question.question_number,
            "question_text":
                next_question.question_text,
            "option_a":
                next_question.option_a,
            "option_b":
                next_question.option_b,
            "option_c":
                next_question.option_c,
            "option_d":
                next_question.option_d,
        },
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
        "current_question_number":
            quiz.current_question_number,
        "started_at": quiz.started_at,
        "finished_at": quiz.finished_at,
    }
