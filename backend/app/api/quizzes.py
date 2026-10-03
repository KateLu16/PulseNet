from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Quiz
from app.schemas.quiz import QuizCreateRequest, QuizResponse


router = APIRouter(
    prefix="/api/quizzes",
    tags=["Quizzes"],
)


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
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return quiz


@router.get(
    "",
    response_model=list[QuizResponse],
)
def get_quizzes(
    db: Session = Depends(get_db),
):
    return db.query(Quiz).order_by(Quiz.id.desc()).all()


@router.get(
    "/{quiz_id}",
    response_model=QuizResponse,
)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    return quiz
