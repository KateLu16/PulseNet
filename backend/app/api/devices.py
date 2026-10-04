from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.device import Device
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
    # 1. Find student by MSSV
    student = (
        db.query(Student)
        .filter(Student.student_id == data.student_id)
        .first()
    )

    # 2. Create student if not found
    if student is None:
        student = Student(
            student_id=data.student_id,
        )

        db.add(student)
        db.commit()
        db.refresh(student)

    # 3. Check whether MAC already exists
    device = (
        db.query(Device)
        .filter(Device.device_mac == data.device_mac)
        .first()
    )

    # Check whether the device_code is already used by another device
    if data.device_code is not None:
        device_with_same_code = (
            db.query(Device)
            .filter(Device.device_code == data.device_code)
            .first()
        )

        if (
            device_with_same_code is not None
            and (
                device is None
                or device_with_same_code.id != device.id
            )
        ):
            return DeviceRegisterResponse(
                success=False,
                message="Device code is already registered to another device",
                student_id=student.student_id,
                device_mac=data.device_mac,
                device_code=data.device_code,
            )

    if device is None:
        device = Device(
            device_mac=data.device_mac,
            device_code=data.device_code,
            student_id=student.id,
            status="online",
        )
        db.add(device)
    else:
        device.student_id = student.id
        device.status = "online"

        if data.device_code is not None:
            device.device_code = data.device_code


    db.refresh(device)

    return DeviceRegisterResponse(
        success=True,
        message="Device registered successfully",
        student_id=student.student_id,
        device_mac=device.device_mac,
        device_code=device.device_code,
    )
