from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
from app.models.quiz import Quiz
from app.models.quiz_registration import QuizRegistration
from app.models.student import Student
from app.schemas.device import (
    DeviceRegisterRequest,
    DeviceRegisterResponse,
)


router = APIRouter(
    prefix="/api/devices",
    tags=["Devices"],
)


@router.post(
    "/register",
    response_model=DeviceRegisterResponse,
)
def register_device(
    data: DeviceRegisterRequest,
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # 1. Check quiz
    # --------------------------------------------------------

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

    if quiz.status != "draft":
        raise HTTPException(
            status_code=400,
            detail="Quiz is not in draft status",
        )

    # --------------------------------------------------------
    # 2. Find or create student
    # --------------------------------------------------------

    student = (
        db.query(Student)
        .filter(
            Student.student_id == data.student_id
        )
        .first()
    )

    if student is None:
        student = Student(
            student_id=data.student_id,
        )

        db.add(student)
        db.flush()

    # --------------------------------------------------------
    # 3. Find device by MAC
    # --------------------------------------------------------

    device = (
        db.query(Device)
        .filter(
            Device.device_mac == data.device_mac
        )
        .first()
    )

    if device is None:

        device = Device(
            device_mac=data.device_mac,
            device_code=data.device_code,
            status="online",
            last_seen=datetime.utcnow(),
        )

        db.add(device)
        db.flush()

    else:

        # Device already exists.
        # It is NOT permanently associated with a student.

        device.status = "online"
        device.last_seen = datetime.utcnow()

        if data.device_code is not None:
            device.device_code = data.device_code

    # --------------------------------------------------------
    # 4. Check device-code conflict
    # --------------------------------------------------------

    if data.device_code is not None:

        device_with_same_code = (
            db.query(Device)
            .filter(
                Device.device_code
                == data.device_code
            )
            .first()
        )

        if (
            device_with_same_code is not None
            and device_with_same_code.id
            != device.id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Device code is already "
                    "registered to another device"
                ),
            )

    # --------------------------------------------------------
    # 5. Check existing registration
    # --------------------------------------------------------

    registration = (
        db.query(QuizRegistration)
        .filter(
            QuizRegistration.quiz_id
            == data.quiz_id,
            QuizRegistration.device_id
            == device.id,
        )
        .first()
    )

    # --------------------------------------------------------
    # 6. Device already registered in this quiz
    # --------------------------------------------------------

    if registration is not None:

        existing_student = (
            db.query(Student)
            .filter(
                Student.id
                == registration.student_id
            )
            .first()
        )

        if (
            existing_student is not None
            and existing_student.id
            == student.id
        ):
            return DeviceRegisterResponse(
                success=True,
                message=(
                    "Device already registered "
                    "to this student for this quiz"
                ),
                student_id=student.student_id,
                device_mac=device.device_mac,
                device_code=device.device_code,
                quiz_id=data.quiz_id,
            )

        raise HTTPException(
            status_code=400,
            detail=(
                "Device is already registered "
                "to another student in this quiz"
            ),
        )

    # --------------------------------------------------------
    # 7. Check whether student already uses another device
    # --------------------------------------------------------

    student_registration = (
        db.query(QuizRegistration)
        .filter(
            QuizRegistration.quiz_id
            == data.quiz_id,
            QuizRegistration.student_id
            == student.id,
        )
        .first()
    )

    if student_registration is not None:

        raise HTTPException(
            status_code=400,
            detail=(
                "Student is already registered "
                "to another device in this quiz"
            ),
        )

    # --------------------------------------------------------
    # 8. Create quiz-scoped registration
    # --------------------------------------------------------

    registration = QuizRegistration(
        quiz_id=data.quiz_id,
        device_id=device.id,
        student_id=student.id,
        registered_at=datetime.utcnow(),
    )

    db.add(registration)

    db.commit()

    db.refresh(device)
    db.refresh(registration)

    # --------------------------------------------------------
    # 9. Return success
    # --------------------------------------------------------

    return DeviceRegisterResponse(
        success=True,
        message="Device registered successfully",
        student_id=student.student_id,
        device_mac=device.device_mac,
        device_code=device.device_code,
        quiz_id=data.quiz_id,
    )
