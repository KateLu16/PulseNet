
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.question import Question
from app.models.quiz import Quiz
from app.models.quiz_registration import QuizRegistration
from app.models.response import Response
from app.models.student import Student
from app.services.quiz_lifecycle import (
    finalize_expired_quiz,
    finalize_expired_quizzes,
)


router = APIRouter(
    prefix="/api",
    tags=["monitoring"],
)


# ============================================================
# GATEWAY STATUS
#
# The BLE gateway (gateway/send_ack.py) POSTs a heartbeat
# every 2 seconds. The teacher dashboard polls
# /api/gateway/status to show whether the gateway is
# running and which devices are connected over BLE.
#
# State is kept in memory: it is transient by nature and
# the gateway re-populates it within seconds of a backend
# restart.
# ============================================================

GATEWAY_OFFLINE_AFTER_SECONDS = 6.0

# A device counts as online only while the gateway reports
# it connected — plus this freshness window on last_seen, so
# a dead gateway does not leave every device stuck "online".
DEVICE_ONLINE_TIMEOUT_SEC = 30

_gateway_state = {
    "last_seen": 0.0,
    "payload": {},
}


class GatewayDeviceHeartbeat(BaseModel):
    # BLE address of the student device (ESP32 BLE MAC).
    address: str = ""

    # BLE link state as seen by the gateway.
    connected: bool = False

    # Student logged in on that device (when known).
    student_id: str | None = None

    # Last question number pushed to that device.
    last_pushed_question: int | None = None


class GatewayHeartbeat(BaseModel):
    connected: bool = False
    device_address: str = ""
    quiz_id: int | None = None
    registered_count: int = 0
    last_pushed_question: int | None = None

    # Multi-device gateway: per-device BLE link states.
    # Older single-device gateboards keep sending the flat
    # fields above; `devices` defaults to empty.
    devices: list[GatewayDeviceHeartbeat] = []


@router.post("/gateway/heartbeat")
def gateway_heartbeat(
    data: GatewayHeartbeat,
    db: Session = Depends(get_db),
):
    _gateway_state["last_seen"] = time.time()
    _gateway_state["payload"] = data.model_dump()

    # --------------------------------------------------------
    # Device online/offline bookkeeping.
    #
    # The gateway is the only one that knows the live BLE
    # link state. Device.status used to be set to "online"
    # on first answer and never cleared — devices stayed
    # "online" forever. Sync the column here instead:
    #
    #   connected link   -> online + last_seen refreshed
    #   missing link     -> offline
    # --------------------------------------------------------

    connected_macs = {
        dev.address.strip().upper()
        for dev in data.devices
        if dev.connected and dev.address
    }

    if connected_macs:
        db.query(Device).filter(
            Device.device_mac.in_(connected_macs)
        ).update(
            {
                "status": "online",
                "last_seen": datetime.utcnow(),
            },
            synchronize_session=False,
        )

    db.query(Device).filter(
        Device.status == "online",
        Device.device_mac.notin_(connected_macs),
    ).update(
        {"status": "offline"},
        synchronize_session=False,
    )

    db.commit()

    return {"ok": True}


@router.get("/gateway/status")
def gateway_status():
    payload = dict(_gateway_state["payload"])
    age = time.time() - _gateway_state["last_seen"]
    online = age < GATEWAY_OFFLINE_AFTER_SECONDS

    devices = payload.get("devices") or []

    # Keep the flat single-device fields working for the
    # dashboard: "connected" = at least one BLE link up.
    if devices:
        payload["connected"] = any(
            dev.get("connected") for dev in devices
        )
        payload["device_address"] = ", ".join(
            dev.get("address", "")
            for dev in devices
            if dev.get("connected")
        )

    return {
        "online": online,
        "last_seen_seconds_ago": round(age, 1) if online else None,
        **payload,
    }


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

    finalize_expired_quiz(db, quiz)

    # Aggregate response statistics per student for this quiz.
    response_stats = (
        select(
            Response.student_id.label("student_id"),
            func.count(Response.id).label("answered_count"),
            func.sum(
                cast(Response.is_correct, Integer)
            ).label("correct_count"),
            func.max(
                Question.question_number
            ).label("last_answered_question"),
        )
        .join(
            Question,
            Question.id == Response.question_id,
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
            response_stats.c.last_answered_question,
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

    now = datetime.utcnow()
    online_cutoff = now - timedelta(
        seconds=DEVICE_ONLINE_TIMEOUT_SEC
    )

    students = []

    for row in rows:
        answered_count = int(row.answered_count or 0)
        correct_count = int(row.correct_count or 0)
        wrong_count = max(answered_count - correct_count, 0)

        # Unanswered questions = blanks (not wrong answers).
        blank_count = max(total_questions - answered_count, 0)

        score = (
            round(correct_count / total_questions * 10, 2)
            if total_questions > 0
            else 0
        )

        # A device is online only when the BLE link is fresh;
        # the stored column alone can go stale.
        device_online = (
            row.device_status == "online"
            and row.last_seen is not None
            and row.last_seen >= online_cutoff
        )

        students.append(
            {
                "student_id": row.student_id,
                "name": row.name,
                "device_mac": row.device_mac,
                "device_code": row.device_code,
                "device_status": "online" if device_online else "offline",
                "battery": row.battery,
                "last_seen": row.last_seen,
                "registered_at": row.registered_at,
                "answered_count": answered_count,
                "correct_count": correct_count,
                "wrong_count": max(answered_count - correct_count, 0),
                "blank_count": blank_count,
                "total_questions": total_questions,
                "score": score,
                # Highest question number the student has
                # answered — the dashboard shows "now on Qn".
                "last_answered_question": (
                    int(row.last_answered_question)
                    if row.last_answered_question is not None
                    else 0
                ),
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

    Student association is per-quiz (QuizRegistration),
    so this endpoint lists devices only. Use
    /quizzes/{quiz_id}/students or /quizzes/{quiz_id}/devices
    to see which student used a device in a quiz.
    """

    stmt = (
        select(
            Device.device_mac,
            Device.device_code,
            Device.status,
            Device.battery,
            Device.last_seen,
            Device.created_at,
        )
        .order_by(Device.device_mac)
    )

    rows = db.execute(stmt).all()

    now = datetime.utcnow()
    online_cutoff = now - timedelta(
        seconds=DEVICE_ONLINE_TIMEOUT_SEC
    )

    devices = []

    for row in rows:
        # Online = status column AND a fresh heartbeat-driven
        # last_seen; a stale "online" flag shows as offline.
        online = (
            row.status == "online"
            and row.last_seen is not None
            and row.last_seen >= online_cutoff
        )

        devices.append(
            {
                "device_mac": row.device_mac,
                "device_code": row.device_code,
                "status": "online" if online else "offline",
                "battery": row.battery,
                "last_seen": row.last_seen,
                "created_at": row.created_at,
            }
        )

    return {
        "total_devices": len(devices),
        "devices": devices,
    }


# ============================================================
# SYSTEM OVERVIEW
#
# Aggregated numbers for the teacher Dashboard page:
# students, quizzes by status, questions, devices and
# answer accuracy — plus the recent quiz sessions with
# per-quiz student counts (one call instead of N).
# ============================================================

@router.get("/stats/overview")
def get_stats_overview(
    db: Session = Depends(get_db),
):
    finalize_expired_quizzes(db)

    total_students = db.scalar(
        select(func.count()).select_from(Student)
    ) or 0

    total_quizzes = db.scalar(
        select(func.count()).select_from(Quiz)
    ) or 0

    active_quizzes = db.scalar(
        select(func.count())
        .select_from(Quiz)
        .where(Quiz.status.in_(("lobby", "running")))
    ) or 0

    finished_quizzes = db.scalar(
        select(func.count())
        .select_from(Quiz)
        .where(Quiz.status == "finished")
    ) or 0

    total_questions = db.scalar(
        select(func.count()).select_from(Question)
    ) or 0

    devices_total = db.scalar(
        select(func.count()).select_from(Device)
    ) or 0

    online_cutoff = datetime.utcnow() - timedelta(
        seconds=DEVICE_ONLINE_TIMEOUT_SEC
    )

    devices_online = db.scalar(
        select(func.count())
        .select_from(Device)
        .where(
            Device.status == "online",
            Device.last_seen >= online_cutoff,
        )
    ) or 0

    total_responses = db.scalar(
        select(func.count()).select_from(Response)
    ) or 0

    correct_responses = db.scalar(
        select(func.count())
        .select_from(Response)
        .where(Response.is_correct.is_(True))
    ) or 0

    overall_accuracy = (
        round(correct_responses / total_responses * 100, 2)
        if total_responses > 0
        else 0.0
    )

    # Recent sessions with per-quiz student counts.
    student_counts = dict(
        db.execute(
            select(
                QuizRegistration.quiz_id,
                func.count(QuizRegistration.id),
            ).group_by(QuizRegistration.quiz_id)
        ).all()
    )

    quizzes = (
        db.query(Quiz)
        .order_by(Quiz.id.desc())
        .limit(8)
        .all()
    )

    recent_sessions = [
        {
            "id": quiz.id,
            "title": quiz.title,
            "status": quiz.status,
            "started_at": quiz.started_at,
            "finished_at": quiz.finished_at,
            "student_count": student_counts.get(quiz.id, 0),
        }
        for quiz in quizzes
    ]

    return {
        "total_students": total_students,
        "total_quizzes": total_quizzes,
        "active_quizzes": active_quizzes,
        "finished_quizzes": finished_quizzes,
        "total_questions": total_questions,
        "devices_total": devices_total,
        "devices_online": devices_online,
        "total_responses": total_responses,
        "correct_responses": correct_responses,
        "overall_accuracy": overall_accuracy,
        "recent_sessions": recent_sessions,
    }


