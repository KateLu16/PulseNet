"""
End-to-end integration test for the PulseNet backend.

Run from the backend directory:
    .venv/Scripts/python test_integration_e2e.py        (Windows)
    .venv/bin/python test_integration_e2e.py            (Pi)

Simulates a full classroom session with THREE devices on a
throwaway database — no HTTP server, no BLE hardware, no
network. The endpoint functions are called directly with a
database session (routing is a thin layer).

Covers the 2026-10-10 review items:
    [P1] self-paced answers (any question, any order)
    [P1] sequence control: duplicate delivery, stale packet,
         re-answer with a newer sequence
    [P1] backend-owned quiz deadline (gateway offline)
    [P2] device online/offline via gateway heartbeat
    [P2] wrong answers vs blanks in results/statistics
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Use a throwaway database before any app import touches one.
_TEMP_DIR = tempfile.mkdtemp(prefix="pulsenet_e2e_")
os.chdir(_TEMP_DIR)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import HTTPException  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402

from app.api.analytics import (  # noqa: E402
    get_quiz_results,
    get_question_statistics,
    get_quiz_statistics,
)
from app.api.devices import register_device  # noqa: E402
from app.api.monitoring import (  # noqa: E402
    gateway_heartbeat,
    gateway_status,
    get_all_devices,
    get_quiz_students,
    get_stats_overview,
    GatewayHeartbeat,
    GatewayDeviceHeartbeat,
)
from app.api.quizzes import (  # noqa: E402
    create_quiz,
    finish_quiz,
    get_quiz,
    get_quizzes,
    open_lobby,
    setup_quiz,
    start_quiz,
)
from app.api.responses import submit_answer  # noqa: E402
from app.models.quiz import Quiz  # noqa: E402
from app.schemas.device import DeviceRegisterRequest  # noqa: E402
from app.schemas.quiz import QuizCreateRequest, QuizSetupRequest  # noqa: E402
from app.schemas.response import AnswerCreateRequest  # noqa: E402

QUESTIONS = [
    # (number, text, A, B, C, D, correct)
    (1, "2+2=?", "3", "4", "5", "6", "B"),
    (2, "BLE stands for?", "Blue Low Energy", "Bluetooth Low Energy",
     "Basic Link Envelope", "Broadband Link Engine", "B"),
    (3, "IoT gateway here?", "ESP32", "Raspberry Pi", "Arduino", "CRT", "B"),
    (4, "Unit of frequency?", "Hertz", "Newton", "Joule", "Lux", "A"),
    (5, "SQLite is a?", "Network DB", "File DB", "Queue", "Broker", "B"),
]

STUDENTS = {
    # student_id: device mac
    "2151001": "AA:AA:AA:AA:AA:01",
    "2151002": "AA:AA:AA:AA:AA:02",
    "2151003": "AA:AA:AA:AA:AA:03",
}


PASSED = 0
FAILED = 0


def check(name, condition, detail=""):
    global PASSED, FAILED

    if condition:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name} {detail}")


def expect_rejected(name, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except HTTPException as e:
        print(f"  [PASS] {name} (HTTP {e.status_code}: {e.detail})")
        global PASSED
        PASSED += 1
        return e

    global FAILED
    FAILED += 1
    print(f"  [FAIL] {name} — no HTTPException raised")


def answer_payload(student_id, mac, quiz_id, question_number,
                   letter, sequence):
    return AnswerCreateRequest(
        student_id=student_id,
        device_mac=mac,
        quiz_id=quiz_id,
        question_id=f"Q{question_number:02d}",
        answer=letter,
        sequence=sequence,
    )


def main():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # ========================================================
    # 1. SESSION SETUP
    # ========================================================

    print("\n=== 1. Session setup ===")

    quiz = create_quiz(
        QuizCreateRequest(title="E2E IoT Midterm"), db
    )

    quiz_id = quiz.id

    from app.api.questions import create_question
    from app.schemas.question import QuestionCreateRequest

    for number, text, a, b, c, d, correct in QUESTIONS:
        create_question(
            quiz_id,
            QuestionCreateRequest(
                question_number=number,
                question_text=text,
                option_a=a,
                option_b=b,
                option_c=c,
                option_d=d,
                correct_answer=correct,
            ),
            db,
        )

    setup_quiz(
        quiz_id,
        QuizSetupRequest(
            time_limit_sec=600,
            expected_students=3,
            id_prefix="2151",
            id_length=7,
        ),
        db,
    )

    open_lobby(quiz_id, db)

    check("lobby opened", get_quiz(quiz_id, db).status == "lobby")

    for student_id, mac in STUDENTS.items():
        result = register_device(
            DeviceRegisterRequest(
                student_id=student_id,
                device_mac=mac,
                device_code=f"PULSENET-{student_id[-2:]}",
                quiz_id=quiz_id,
            ),
            db,
        )
        check(
            f"registered {student_id} on {mac}",
            result.success is True,
        )

    start_quiz(quiz_id, db)

    check("quiz running", get_quiz(quiz_id, db).status == "running")

    # ========================================================
    # 2. SELF-PACED ANSWERS
    # Each student answers in a DIFFERENT order to prove the
    # backend does not enforce a shared "current question".
    # ========================================================

    print("\n=== 2. Self-paced answers (3 devices) ===")

    # student -> {question_number: (letter, sequence)}
    plans = {
        "2151001": {1: ("B", 1), 2: ("B", 2), 3: ("B", 3), 4: ("A", 4), 5: ("B", 5)},
        "2151002": {3: ("B", 1), 1: ("A", 2), 2: ("B", 3)},   # Q3 first!
        "2151003": {1: ("C", 1)},                               # 1 answer only
    }

    for student_id, answers in plans.items():
        mac = STUDENTS[student_id]

        for number, (letter, seq) in answers.items():
            result = submit_answer(
                answer_payload(student_id, mac, quiz_id, number, letter, seq),
                db,
            )
            check(
                f"{student_id} answered Q{number}={letter}",
                result.success and result.status in ("ACCEPTED", "UPDATED"),
                f"(status={result.status})",
            )

    # ========================================================
    # 3. SEQUENCE CONTROL
    # ========================================================

    print("\n=== 3. Sequence control (duplicate / stale / re-answer) ===")

    mac1 = STUDENTS["2151001"]

    # 3a. DUPLICATE: gateway redelivers Q2 seq=2 (ACK was
    # lost). Stored answer (B, correct) must survive and the
    # row must not be re-counted.
    dup = submit_answer(
        answer_payload("2151001", mac1, quiz_id, 2, "B", 2), db
    )
    check(
        "duplicate delivery -> DUPLICATE, kept stored answer",
        dup.status == "DUPLICATE" and dup.answer == "B" and dup.correct,
        f"(status={dup.status})",
    )

    # 3b. STALE: an old delayed packet (Q2 seq=1, answer C)
    # arrives AFTER the newer attempt. It must NOT roll the
    # answer back to C.
    stale = submit_answer(
        answer_payload("2151001", mac1, quiz_id, 2, "C", 1), db
    )
    check(
        "stale packet -> STALE_IGNORED, newer answer kept",
        stale.status == "STALE_IGNORED" and stale.answer == "B" and stale.correct,
        f"(status={stale.status}, answer={stale.answer})",
    )

    # 3c. RE-ANSWER with a NEWER sequence: student changes
    # their mind on Q3 (B -> A). Newer attempt wins.
    reanswer = submit_answer(
        answer_payload("2151001", mac1, quiz_id, 3, "A", 9), db
    )
    check(
        "re-answer with higher sequence -> UPDATED, wrong now",
        reanswer.status == "UPDATED" and reanswer.correct is False,
        f"(status={reanswer.status})",
    )

    # 3d. Legacy firmware (no sequence): last-write-wins.
    legacy = submit_answer(
        answer_payload("2151002", STUDENTS["2151002"], quiz_id, 1, "B", None),
        db,
    )
    check(
        "answer without sequence still accepted (legacy)",
        legacy.success and legacy.answer == "B",
    )

    # ========================================================
    # 4. HEARTBEAT / DEVICE ONLINE-OFFLINE
    # ========================================================

    print("\n=== 4. Gateway heartbeat per-device status ===")

    gateway_heartbeat(
        GatewayHeartbeat(
            connected=True,
            device_address=STUDENTS["2151001"],
            quiz_id=quiz_id,
            registered_count=3,
            devices=[
                GatewayDeviceHeartbeat(
                    address=STUDENTS["2151001"],
                    connected=True,
                    student_id="2151001",
                    last_pushed_question=3,
                ),
                GatewayDeviceHeartbeat(
                    address=STUDENTS["2151002"],
                    connected=True,
                    student_id="2151002",
                    last_pushed_question=5,
                ),
                GatewayDeviceHeartbeat(
                    address=STUDENTS["2151003"],
                    connected=False,
                ),
            ],
        ),
        db,
    )

    devices = get_all_devices(db)["devices"]
    by_mac = {d["device_mac"]: d["status"] for d in devices}

    check(
        "connected devices online, disconnected offline",
        by_mac[STUDENTS["2151001"]] == "online"
        and by_mac[STUDENTS["2151002"]] == "online"
        and by_mac[STUDENTS["2151003"]] == "offline",
        f"({by_mac})",
    )

    status = gateway_status()
    check(
        "gateway status aggregates multi-device payload",
        status["connected"] is True
        and STUDENTS["2151001"] in status["device_address"]
        and len(status["devices"]) == 3,
    )

    # Gateway link dropped -> everything goes offline.
    gateway_heartbeat(
        GatewayHeartbeat(
            connected=False,
            devices=[
                GatewayDeviceHeartbeat(address=mac, connected=False)
                for mac in STUDENTS.values()
            ],
        ),
        db,
    )

    devices = get_all_devices(db)["devices"]
    check(
        "all devices offline after link loss",
        all(d["status"] == "offline" for d in devices),
    )

    # ========================================================
    # 5. LIVE MONITORING (students endpoint)
    # ========================================================

    print("\n=== 5. Live per-student monitoring ===")

    students = get_quiz_students(quiz_id, db)

    rows = {s["student_id"]: s for s in students["students"]}

    s1 = rows["2151001"]
    check(
        "2151001: 5 answered, 4 correct, 1 wrong, 0 blank",
        s1["answered_count"] == 5
        and s1["correct_count"] == 4
        and s1["wrong_count"] == 1
        and s1["blank_count"] == 0,
        f"(a={s1['answered_count']} c={s1['correct_count']} "
        f"w={s1['wrong_count']} b={s1['blank_count']})",
    )

    s3 = rows["2151003"]
    check(
        "2151003: 1 answered, 0 correct, 1 wrong, 4 blank",
        s3["answered_count"] == 1
        and s3["correct_count"] == 0
        and s3["wrong_count"] == 1
        and s3["blank_count"] == 4,
        f"(a={s3['answered_count']} c={s3['correct_count']} "
        f"w={s3['wrong_count']} b={s3['blank_count']})",
    )

    # ========================================================
    # 6. BACKEND-OWNED DEADLINE
    # Simulate the gateway dying: backdate started_at past
    # the time limit, then check lazy finalization.
    # ========================================================

    print("\n=== 6. Quiz deadline enforced by backend ===")

    quiz_row = db.get(Quiz, quiz_id)
    quiz_row.started_at = datetime.utcnow() - timedelta(
        seconds=600 + 60  # limit 600s + grace 15s already passed
    )
    db.commit()

    # A late answer must be rejected AND finish the quiz.
    expect_rejected(
        "late answer rejected (quiz expired)",
        submit_answer,
        answer_payload("2151002", STUDENTS["2151002"], quiz_id, 4, "B", 4),
        db,
    )

    check(
        "quiz auto-finished by backend",
        get_quiz(quiz_id, db).status == "finished",
    )

    expect_rejected(
        "answer after finish rejected",
        submit_answer,
        answer_payload("2151002", STUDENTS["2151002"], quiz_id, 5, "B", 5),
        db,
    )

    expect_rejected(
        "double finish rejected",
        finish_quiz,
        quiz_id,
        db,
    )

    # ========================================================
    # 7. FINAL RESULTS / STATISTICS / DASHBOARD
    # ========================================================

    print("\n=== 7. Final results, statistics, dashboard ===")

    results = get_quiz_results(quiz_id, db)

    check("3 students in results", results["total_students"] == 3)

    res = {r["student_id"]: r for r in results["results"]}

    r1 = res["2151001"]
    check(
        "results 2151001: 5 answered, 4 correct, 0 blank, score 8",
        r1["answered_count"] == 5
        and r1["correct_count"] == 4
        and r1["wrong_count"] == 1
        and r1["blank_count"] == 0
        and r1["score"] == 8.0,
        f"(score={r1['score']})",
    )

    r3 = res["2151003"]
    check(
        "results 2151003: blanks separated from wrong",
        r3["wrong_count"] == 1 and r3["blank_count"] == 4 and r3["score"] == 0.0,
    )

    # Ranking: 2151001 (8.0) > 2151002 (4.0) > 2151003 (0.0)
    scores = [r["score"] for r in results["results"]]
    check("results sorted by score desc", scores == sorted(scores, reverse=True))

    stats = get_quiz_statistics(quiz_id, db)

    # answered: s1=5, s2=3 (Q3,Q1,Q2), s3=1 -> 9 responses
    # correct:  s1=4 (Q1,Q2,Q4,Q5; Q3 re-answered to A=wrong),
    #           s2=3 (Q3; Q1 fixed to B by the legacy
    #           re-answer; Q2), s3=0 -> 7
    check(
        "statistics: 9 responses, 7 correct",
        stats["total_responses"] == 9 and stats["correct_responses"] == 7,
        f"(r={stats['total_responses']} c={stats['correct_responses']})",
    )

    check(
        "statistics: 2 answered students",
        stats["answered_students"] == 3,
        f"(got {stats['answered_students']})",
    )

    qstats = get_question_statistics(quiz_id, db)

    q4 = next(
        q for q in qstats["questions"] if q["question_number"] == 4
    )
    # Q4 correct = A; s1 answered A -> 1 answer, 1 correct.
    check(
        "question stats Q4: 1 answer, 1 correct",
        q4["total_answers"] == 1 and q4["correct_count"] == 1,
        f"(answers={q4['total_answers']}, correct={q4['correct_count']})",
    )

    q5 = next(
        q for q in qstats["questions"] if q["question_number"] == 5
    )
    check(
        "question stats Q5: 1 answer, 1 correct (blank=2 elsewhere)",
        q5["total_answers"] == 1 and q5["correct_count"] == 1,
    )

    overview = get_stats_overview(db)

    check(
        "dashboard overview: quiz counted finished, devices online=0",
        overview["finished_quizzes"] >= 1
        and overview["devices_online"] == 0,
        f"(finished={overview['finished_quizzes']} "
        f"online={overview['devices_online']})",
    )

    quizzes = get_quizzes(db)
    row = next(q for q in quizzes if q.id == quiz_id)
    check("quiz list reflects finished status", row.status == "finished")

    # ========================================================
    # FLEET WITH IDENTICAL FIRMWARE (2026-10-10 bug)
    #
    # Every board flashed with the same binary reports the
    # SAME device_code. Registering a second such device used
    # to crash on the devices.device_code UNIQUE constraint
    # (HTTP 500) — the MAC must stay the identity, and the
    # duplicate label must be resolved, never rejected.
    # ========================================================

    print("\n=== Identical-firmware fleet (duplicate device_code) ===")

    fleet_quiz = create_quiz(
        QuizCreateRequest(title="E2E Fleet Quiz"), db
    )

    create_question(
        fleet_quiz.id,
        QuestionCreateRequest(
            question_number=1,
            question_text="Fleet question?",
            option_a="a",
            option_b="b",
            option_c="c",
            option_d="d",
            correct_answer="B",
        ),
        db,
    )

    open_lobby(fleet_quiz.id, db)

    first = register_device(
        DeviceRegisterRequest(
            student_id="2151001",
            device_mac="BB:BB:BB:BB:BB:01",
            device_code="PULSENET-001",
            quiz_id=fleet_quiz.id,
        ),
        db,
    )
    check(
        "fleet: first device keeps the reported code",
        first.success and first.device_code == "PULSENET-001",
    )

    second = register_device(
        DeviceRegisterRequest(
            student_id="2151002",
            device_mac="BB:BB:BB:BB:BB:02",
            device_code="PULSENET-001",
            quiz_id=fleet_quiz.id,
        ),
        db,
    )
    check(
        "fleet: second device registers despite duplicate code",
        second.success is True,
        f"(device_code={second.device_code})",
    )
    check(
        "fleet: second device gets a MAC-derived code",
        second.device_code not in (None, "PULSENET-001"),
        f"(device_code={second.device_code})",
    )

    devices = {
        d["device_mac"]: d["device_code"]
        for d in get_all_devices(db)["devices"]
    }
    check(
        "fleet: both devices exist with distinct codes",
        "BB:BB:BB:BB:BB:01" in devices
        and "BB:BB:BB:BB:BB:02" in devices
        and devices["BB:BB:BB:BB:BB:01"]
        != devices["BB:BB:BB:BB:BB:02"],
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print("\n======================================")
    print(f" E2E RESULT: {PASSED} passed, {FAILED} failed")
    print("======================================")

    db.close()

    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
