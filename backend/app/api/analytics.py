from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.quiz import Quiz
from app.models.question import Question
from app.models.response import Response
from app.models.student import Student
from app.models.device import Device
from app.models.quiz_registration import QuizRegistration


router = APIRouter(
    prefix="/api/quizzes",
    tags=["analytics"],
)


def get_quiz_or_404(quiz_id: int, db: Session) -> Quiz:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()

    if not quiz:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    return quiz


@router.get("/{quiz_id}/results")
def get_quiz_results(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    """
    Return result for every student registered in the quiz.

    Score:
        correct_count / total_questions * 10

    Accuracy:
        correct_count / answered_count * 100
    """

    get_quiz_or_404(quiz_id, db)

    total_questions = (
        db.query(func.count(Question.id))
        .filter(Question.quiz_id == quiz_id)
        .scalar()
        or 0
    )

    registrations = (
        db.query(
            QuizRegistration,
            Student,
            Device,
        )
        .join(
            Student,
            QuizRegistration.student_id == Student.id,
        )
        .join(
            Device,
            QuizRegistration.device_id == Device.id,
        )
        .filter(
            QuizRegistration.quiz_id == quiz_id,
        )
        .all()
    )

    results = []

    for registration, student, device in registrations:

        responses = (
            db.query(Response)
            .filter(
                Response.quiz_id == quiz_id,
                Response.student_id == student.student_id,
            )
            .all()
        )

        answered_count = len(responses)
        correct_count = sum(
            1 for response in responses
            if response.is_correct
        )

        wrong_count = answered_count - correct_count

        if total_questions > 0:
            score = round(
                (correct_count / total_questions) * 10,
                2,
            )
        else:
            score = 0.0

        if answered_count > 0:
            accuracy = round(
                (correct_count / answered_count) * 100,
                2,
            )
        else:
            accuracy = 0.0

        results.append(
            {
                "student_id": student.student_id,
                "student_name": student.name,
                "device_mac": device.device_mac,
                "device_status": device.status,
                "answered_count": answered_count,
                "total_questions": total_questions,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "score": score,
                "accuracy": accuracy,
            }
        )

    # Highest score first.
    results.sort(
        key=lambda item: (
            item["score"],
            item["correct_count"],
        ),
        reverse=True,
    )

    return {
        "quiz_id": quiz_id,
        "total_students": len(results),
        "total_questions": total_questions,
        "results": results,
    }


@router.get("/{quiz_id}/statistics")
def get_quiz_statistics(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    """
    Return overall/class statistics for a quiz.
    """

    get_quiz_or_404(quiz_id, db)

    total_questions = (
        db.query(func.count(Question.id))
        .filter(Question.quiz_id == quiz_id)
        .scalar()
        or 0
    )

    total_students = (
        db.query(func.count(QuizRegistration.id))
        .filter(
            QuizRegistration.quiz_id == quiz_id,
        )
        .scalar()
        or 0
    )

    total_responses = (
        db.query(func.count(Response.id))
        .filter(Response.quiz_id == quiz_id)
        .scalar()
        or 0
    )

    correct_responses = (
        db.query(func.count(Response.id))
        .filter(
            Response.quiz_id == quiz_id,
            Response.is_correct.is_(True),
        )
        .scalar()
        or 0
    )

    wrong_responses = total_responses - correct_responses

    answered_students = (
        db.query(
            func.count(
                func.distinct(Response.student_id)
            )
        )
        .filter(Response.quiz_id == quiz_id)
        .scalar()
        or 0
    )

    if total_responses > 0:
        overall_accuracy = round(
            (correct_responses / total_responses) * 100,
            2,
        )
    else:
        overall_accuracy = 0.0

    # Calculate average student score.
    student_scores = []

    registrations = (
        db.query(Student.student_id)
        .join(
            QuizRegistration,
            QuizRegistration.student_id == Student.id,
        )
        .filter(
            QuizRegistration.quiz_id == quiz_id,
        )
        .all()
    )

    for (student_id,) in registrations:

        correct_count = (
            db.query(func.count(Response.id))
            .filter(
                Response.quiz_id == quiz_id,
                Response.student_id == student_id,
                Response.is_correct.is_(True),
            )
            .scalar()
            or 0
        )

        if total_questions > 0:
            score = (
                correct_count / total_questions
            ) * 10
        else:
            score = 0.0

        student_scores.append(score)

    if student_scores:
        average_score = round(
            sum(student_scores) / len(student_scores),
            2,
        )
    else:
        average_score = 0.0

    return {
        "quiz_id": quiz_id,
        "total_students": total_students,
        "answered_students": answered_students,
        "total_questions": total_questions,
        "total_responses": total_responses,
        "correct_responses": correct_responses,
        "wrong_responses": wrong_responses,
        "overall_accuracy": overall_accuracy,
        "average_score": average_score,
    }


@router.get("/{quiz_id}/questions/statistics")
def get_question_statistics(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    """
    Return statistics for every question.

    Includes:
    - correct answer
    - total answers
    - correct/wrong
    - accuracy
    - A/B/C/D answer distribution
    """

    get_quiz_or_404(quiz_id, db)

    questions = (
        db.query(Question)
        .filter(
            Question.quiz_id == quiz_id,
        )
        .order_by(
            Question.question_number.asc(),
        )
        .all()
    )

    statistics = []

    for question in questions:

        responses = (
            db.query(Response)
            .filter(
                Response.quiz_id == quiz_id,
                Response.question_id == question.id,
            )
            .all()
        )

        total_answers = len(responses)

        correct_count = sum(
            1
            for response in responses
            if response.is_correct
        )

        wrong_count = total_answers - correct_count

        if total_answers > 0:
            accuracy = round(
                (correct_count / total_answers) * 100,
                2,
            )
        else:
            accuracy = 0.0

        distribution = {
            "A": 0,
            "B": 0,
            "C": 0,
            "D": 0,
        }

        for response in responses:
            answer = response.answer.upper()

            if answer in distribution:
                distribution[answer] += 1

        statistics.append(
            {
                "question_id": question.id,
                "question_number": question.question_number,
                "question_text": question.question_text,
                "correct_answer": question.correct_answer,
                "total_answers": total_answers,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "accuracy": accuracy,
                "answer_distribution": distribution,
            }
        )

    return {
        "quiz_id": quiz_id,
        "total_questions": len(statistics),
        "questions": statistics,
    }
