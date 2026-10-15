from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import Question
from app.models.quiz import Quiz
from app.schemas.question import (
    QuestionCreateRequest,
    QuestionResponse,
)
from app.services.question_import import import_questions_from_csv


router = APIRouter(
    prefix="/api/quizzes",
    tags=["Questions"],
)


# ============================================================
# CREATE QUESTION
# ============================================================

@router.post(
    "/{quiz_id}/questions",
    response_model=QuestionResponse,
)
def create_question(
    quiz_id: int,
    data: QuestionCreateRequest,
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

    # Prevent duplicate question numbers
    existing_question = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz_id,
            Question.question_number == data.question_number,
        )
        .first()
    )

    if existing_question is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Question number {data.question_number} "
                "already exists in this quiz"
            ),
        )

    question = Question(
        quiz_id=quiz_id,
        question_number=data.question_number,
        question_text=data.question_text,
        option_a=data.option_a,
        option_b=data.option_b,
        option_c=data.option_c,
        option_d=data.option_d,
        correct_answer=data.correct_answer,
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return question


# ============================================================
# GET ALL QUESTIONS OF A QUIZ
# ============================================================

@router.get(
    "/{quiz_id}/questions",
    response_model=list[QuestionResponse],
)
def get_questions(
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

    return (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.question_number)
        .all()
    )


# ============================================================
# IMPORT QUESTIONS FROM CSV
# ============================================================

@router.post(
    "/{quiz_id}/questions/import",
)
def import_questions(
    quiz_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Check quiz
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if file.filename is None:
        raise HTTPException(
            status_code=400,
            detail="No file provided",
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported",
        )

    # --------------------------------------------------------
    # Import CSV
    # --------------------------------------------------------

    result = import_questions_from_csv(
        file=file,
        quiz_id=quiz_id,
        db=db,
    )

    # --------------------------------------------------------
    # Handle validation errors
    # --------------------------------------------------------

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result,
        )

    return result
