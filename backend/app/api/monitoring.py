
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.quiz_registration import QuizRegistration
from app.models.response import Response
from app.models.student import Student


router = APIRouter(
    prefix="/api",
    tags=["monitoring"],
)


@router.get("/quizzes/{quiz_id}/students")
def get_quiz_students(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all students registered for a quiz,
    including device status and answering progress.
    """

    quiz = db.get(Quiz, quiz_id)

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    # Aggregate response statistics per student for this quiz.
    response_stats = (
        select(
            Response.student_id.label("student_id"),
            func.count(Response.id).label("answered_count"),
            func.sum(
                func.cast(Response.is_correct, Integer)
            ).label("correct_count"),
        )
        .where(Response.quiz_id == quiz_id)
        .group_by(Response.student_id)
        .subquery()
    )

    total_questions = db.scalar(
    select(func.count())
    .select_from(Question)
    .where(Question.quiz_id == quiz_id)
) or 0

    stmt = (
        select(
            Student.student_id,
            Student.name,
            Device.device_mac,
            Device.device_code,
            Device.status.label("device_status"),
            Device.battery,
            Device.last_seen,
            QuizRegistration.registered_at,
            func.coalesce(
                response_stats.c.answered_count,
                0,
            ).label("answered_count"),
            func.coalesce(
                response_stats.c.correct_count,
                0,
            ).label("correct_count"),
        )
        .join(
            Student,
            Student.id == QuizRegistration.student_id,
        )
        .join(
            Device,
            Device.id == QuizRegistration.device_id,
        )
        .outerjoin(
            response_stats,
            response_stats.c.student_id == Student.student_id,
        )
        .where(
            QuizRegistration.quiz_id == quiz_id,
        )
        .order_by(Student.student_id)
    )

    rows = db.execute(stmt).all()

    students = []

    for row in rows:
        answered_count = int(row.answered_count or 0)
        correct_count = int(row.correct_count or 0)
        wrong_count = max(answered_count - correct_count, 0)

        score = (
            round(correct_count / total_questions * 10, 2)
            if total_questions > 0
            else 0
        )

        students.append(
            {
                "student_id": row.student_id,
                "name": row.name,
                "device_mac": row.device_mac,
                "device_code": row.device_code,
                "device_status": row.device_status,
                "battery": row.battery,
                "last_seen": row.last_seen,
                "registered_at": row.registered_at,
                "answered_count": answered_count,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "total_questions": total_questions,
                "score": score,
            }
        )

    return {
        "quiz_id": quiz_id,
        "quiz_status": quiz.status,
        "total_students": len(students),
        "students": students,
    }


@router.get("/quizzes/{quiz_id}/devices")
def get_quiz_devices(
    quiz_id: int,
    db: Session = Depends(get_db),
):
    """
    Get all devices registered for a quiz.
    """

    quiz = db.get(Quiz, quiz_id)

    if quiz is None:
        raise HTTPException(
            status_code=404,
            detail="Quiz not found",
        )

    response_stats = (
        select(
            Response.device_mac.label("device_mac"),
            func.count(Response.id).label("answered_count"),
        )
        .where(Response.quiz_id == quiz_id)
        .group_by(Response.device_mac)
        .subquery()
    )

    stmt = (
        select(
            Device.device_mac,
            Device.device_code,
            Device.status,
            Device.battery,
            Device.last_seen,
            Student.student_id,
            Student.name,
            QuizRegistration.registered_at,
            func.coalesce(
                response_stats.c.answered_count,
                0,
            ).label("answered_count"),
        )
        .join(
            QuizRegistration,
            QuizRegistration.device_id == Device.id,
        )
        .join(
            Student,
            Student.id == QuizRegistration.student_id,
        )
        .outerjoin(
            response_stats,
            response_stats.c.device_mac == Device.device_mac,
        )
        .where(
            QuizRegistration.quiz_id == quiz_id,
        )
        .order_by(Device.device_mac)
    )

    rows = db.execute(stmt).all()

    devices = []

    for row in rows:
        devices.append(
            {
                "device_mac": row.device_mac,
                "device_code": row.device_code,
                "status": row.status,
                "battery": row.battery,
                "last_seen": row.last_seen,
                "student_id": row.student_id,
                "student_name": row.name,
                "registered_at": row.registered_at,
                "answered_count": int(row.answered_count or 0),
            }
        )

    return {
        "quiz_id": quiz_id,
        "total_devices": len(devices),
        "devices": devices,
    }


@router.get("/devices")
def get_all_devices(
    db: Session = Depends(get_db),
):
    """
    Get all known devices in the system.
    """

    stmt = (
        select(
            Device.device_mac,
            Device.device_code,
            Device.status,
            Device.battery,
            Device.last_seen,
            Device.created_at,
            Student.student_id,
            Student.name,
        )
        .outerjoin(
            Student,
            Student.id == Device.student_id,
        )
        .order_by(Device.device_mac)
    )

    rows = db.execute(stmt).all()

    devices = []

    for row in rows:
        devices.append(
            {
                "device_mac": row.device_mac,
                "device_code": row.device_code,
                "status": row.status,
                "battery": row.battery,
                "last_seen": row.last_seen,
                "created_at": row.created_at,
                "student_id": row.student_id,
                "student_name": row.name,
            }
        )

    return {
        "total_devices": len(devices),
        "devices": devices,
    }
