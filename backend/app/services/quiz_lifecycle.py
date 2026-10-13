"""
Quiz lifecycle helpers enforced by the BACKEND so the system
does not depend on the BLE gateway being alive.

The gateway already finishes a running quiz when its countdown
expires, but if the gateway process dies (or the Pi reboots)
a running quiz would stay "running" forever:

- devices keep accepting/submitting answers,
- the dashboard clock freezes,
- new sessions cannot be pushed cleanly.

finalize_expired_quiz() is therefore called lazily from the
answer endpoint and the read paths the dashboard polls. It is
cheap: it only touches quizzes whose deadline (+ grace for BLE
clock skew) has actually passed.

Grace: the ESP32 starts its countdown when the RUNNING
QUIZ_INFO packet arrives — slightly AFTER started_at on the
server. A short grace window stops the backend from cutting
off answers the device is still legitimately sending.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.quiz import Quiz

# Extra seconds allowed after the deadline before the backend
# force-finishes the quiz (BLE delivery + clock skew).
QUIZ_EXPIRY_GRACE_SEC = 15


def quiz_expired(quiz: Quiz, now: datetime | None = None) -> bool:
    """
    True when a running quiz is past its time limit.
    Quizzes without started_at or time_limit_sec never expire.
    """
    if quiz.status != "running":
        return False

    if not quiz.started_at or not quiz.time_limit_sec:
        return False

    if now is None:
        now = datetime.utcnow()

    deadline = quiz.started_at + timedelta(
        seconds=quiz.time_limit_sec + QUIZ_EXPIRY_GRACE_SEC,
    )

    return now >= deadline


def finalize_expired_quiz(db: Session, quiz: Quiz) -> bool:
    """
    Finish `quiz` if its time limit has passed.

    Returns True when the quiz was transitioned to "finished"
    by this call (False = not expired / already finished).
    """
    if not quiz_expired(quiz):
        return False

    quiz.status = "finished"
    quiz.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(quiz)

    return True


def finalize_expired_quizzes(db: Session) -> None:
    """
    Finish every expired running quiz (dashboard read paths).
    """
    running = (
        db.query(Quiz)
        .filter(Quiz.status == "running")
        .all()
    )

    for quiz in running:
        finalize_expired_quiz(db, quiz)
