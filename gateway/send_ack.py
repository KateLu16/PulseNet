import asyncio
import json
import os
from urllib import error, request

from bleak import BleakClient


# =====================================================
# CONFIGURATION
# =====================================================

DEVICE_ADDRESS = os.getenv(
    "PULSENET_DEVICE_ADDRESS",
    "54:43:B2:DC:B0:B2",
)

API_BASE_URL = os.getenv(
    "PULSENET_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

ACTIVE_QUIZ_ID = int(
    os.getenv("PULSENET_QUIZ_ID", "1")
)

SESSION_ID = os.getenv(
    "PULSENET_SESSION_ID",
    f"QUIZ-{ACTIVE_QUIZ_ID}",
)


# =====================================================
# BLE UUID
# =====================================================

REGISTRATION_CHAR_UUID = \
    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

QUESTION_CHAR_UUID = \
    "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

ANSWER_CHAR_UUID = \
    "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"

ACK_CHAR_UUID = \
    "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"


# =====================================================
# RUNTIME STATE
# =====================================================

registered_devices = {}

current_student_id = ""
current_device_mac = ""
current_device_name = ""

current_client = None


# =====================================================
# HTTP API HELPERS
# =====================================================

def api_request(method, path, payload=None):
    url = f"{API_BASE_URL}{path}"

    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with request.urlopen(req, timeout=5) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}

    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")

        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body

        return exc.code, detail

    except Exception as exc:
        print(
            f"[API ERROR] {method} {url}: "
            f"{type(exc).__name__}: {exc}"
        )
        return None, None


async def api_request_async(method, path, payload=None):
    return await asyncio.to_thread(
        api_request,
        method,
        path,
        payload,
    )


# =====================================================
# BLE HELPERS
# =====================================================

def get_characteristic(client, uuid):
    characteristic = client.services.get_characteristic(uuid)

    if characteristic is None:
        raise RuntimeError(
            f"Characteristic not found: {uuid}"
        )

    return characteristic


async def send_ack(client, message):
    data = message.encode("utf-8")

    print()
    print("======================================")
    print("[ACK TX]")
    print("======================================")
    print(message)

    ack_char = get_characteristic(
        client,
        ACK_CHAR_UUID,
    )

    await client.write_gatt_char(
        ack_char,
        data,
        response=True,
    )

    print("[OK] ACK sent.")
    print("======================================")


async def send_register_ack(
    client,
    student_id,
    status,
    reason=None,
):
    packet = {
        "type": "REGISTER_ACK",
        "session_id": SESSION_ID,
        "student_id": student_id,
        "status": status,
    }

    if reason:
        packet["reason"] = reason

    await send_ack(
        client,
        json.dumps(packet, separators=(",", ":")),
    )


async def send_answer_ack(
    client,
    question_id,
    status,
    reason=None,
    correct=None,
):
    packet = {
        "type": "ANSWER_ACK",
        "session_id": SESSION_ID,
        "question_id": question_id,
        "status": status,
    }

    if correct is not None:
        packet["correct"] = correct

    if reason:
        packet["reason"] = reason

    await send_ack(
        client,
        json.dumps(packet, separators=(",", ":")),
    )


# =====================================================
# REGISTRATION
# ESP32 -> Gateway -> FastAPI -> SQLite
# =====================================================

async def process_registration(client, message):
    global current_student_id
    global current_device_mac
    global current_device_name

    print()
    print("======================================")
    print("[REGISTRATION RECEIVED]")
    print("======================================")
    print(message)
    print("======================================")

    try:
        packet = json.loads(message)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON: {exc}")

        await send_register_ack(
            client,
            "",
            "REJECTED",
            "INVALID_JSON",
        )
        return

    if packet.get("type") != "REGISTER":
        await send_register_ack(
            client,
            packet.get("student_id", ""),
            "REJECTED",
            "INVALID_TYPE",
        )
        return

    student_id = str(
        packet.get("student_id", "")
    ).strip()

    device_mac = str(
        packet.get("device_mac", "")
    ).strip().lower()

    device_name = str(
        packet.get("device_name", "")
    ).strip()

    if not student_id:
        await send_register_ack(
            client,
            "",
            "REJECTED",
            "EMPTY_STUDENT_ID",
        )
        return

    if not device_mac:
        await send_register_ack(
            client,
            student_id,
            "REJECTED",
            "EMPTY_DEVICE_MAC",
        )
        return

    payload = {
        "student_id": student_id,
        "device_mac": device_mac,
        "device_code": device_name or None,
    }

    status, result = await api_request_async(
        "POST",
        "/api/devices/register",
        payload,
    )

    print(
        f"[API] Device registration -> "
        f"HTTP {status}: {result}"
    )

    if status != 200 or not result or not result.get("success"):
        reason = "BACKEND_REGISTRATION_FAILED"

        if isinstance(result, dict):
            detail = result.get("detail")
            if detail:
                reason = str(detail)

        await send_register_ack(
            client,
            student_id,
            "REJECTED",
            reason,
        )
        return

    registered_devices[student_id] = {
        "device_mac": device_mac,
        "device_name": device_name,
    }

    current_student_id = student_id
    current_device_mac = device_mac
    current_device_name = device_name

    print(
        f"[OK] Registered in backend: "
        f"{student_id} <-> {device_mac}"
    )

    await send_register_ack(
        client,
        student_id,
        "ACCEPTED",
    )


# =====================================================
# REGISTRATION CALLBACK
# =====================================================

def registration_callback(characteristic, data):
    message = data.decode(
        "utf-8",
        errors="replace",
    )

    client = current_client

    if client is None:
        print("[ERROR] No active BLE client.")
        return

    asyncio.create_task(
        process_registration(
            client,
            message,
        )
    )


# =====================================================
# ANSWER
# ESP32 -> Gateway -> FastAPI -> SQLite
# =====================================================

async def process_answer(client, message):
    print()
    print("======================================")
    print("[ANSWER RECEIVED]")
    print("======================================")
    print(message)
    print("======================================")

    try:
        packet = json.loads(message)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON: {exc}")

        await send_answer_ack(
            client,
            "",
            "REJECTED",
            "INVALID_JSON",
        )
        return

    student_id = str(
        packet.get("student_id", "")
    ).strip()

    question_id = str(
        packet.get("question_id", "")
    ).strip()

    answer = str(
        packet.get("answer", "")
    ).strip().upper()

    sequence = packet.get("sequence")

    if (
        packet.get("type") != "ANSWER"
        or not student_id
        or not question_id
        or answer not in ("A", "B", "C", "D")
    ):
        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "INVALID_PACKET",
        )
        return

    device_info = registered_devices.get(student_id)

    if device_info is None:
        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "STUDENT_NOT_REGISTERED",
        )
        return

    payload = {
        "student_id": student_id,
        "device_mac": device_info["device_mac"],
        "question_id": question_id,
        "answer": answer,
    }

    if sequence is not None:
        payload["sequence"] = sequence

    status, result = await api_request_async(
        "POST",
        "/api/responses/answer",
        payload,
    )

    print(
        f"[API] Answer submission -> "
        f"HTTP {status}: {result}"
    )

    if status != 200 or not result:
        reason = "BACKEND_ANSWER_REJECTED"

        if isinstance(result, dict):
            detail = result.get("detail")
            if detail:
                reason = str(detail)

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            reason,
        )
        return

    await send_answer_ack(
        client,
        question_id,
        "ACCEPTED",
        correct=bool(result.get("correct", False)),
    )


# =====================================================
# ANSWER CALLBACK
# =====================================================

def answer_callback(characteristic, data):
    message = data.decode(
        "utf-8",
        errors="replace",
    )

    client = current_client

    if client is None:
        print("[ERROR] No active BLE client.")
        return

    asyncio.create_task(
        process_answer(
            client,
            message,
        )
    )


# =====================================================
# SEND CURRENT QUESTION
# FastAPI -> Gateway -> ESP32
# =====================================================

async def send_current_question(client):
    status, result = await api_request_async(
        "GET",
        f"/api/quizzes/{ACTIVE_QUIZ_ID}/current",
    )

    print(
        f"[API] Current question -> "
        f"HTTP {status}: {result}"
    )

    if status != 200 or not result:
        print("[ERROR] Could not fetch current question.")
        return

    question_number = result["question_number"]

    packet = {
        "type": "QUESTION",
        "session_id": SESSION_ID,
        "question_id": f"Q{question_number:02d}",
        "question": result["question_text"],
        "A": result["option_a"],
        "B": result["option_b"],
        "C": result["option_c"],
        "D": result["option_d"],
    }

    message = json.dumps(
        packet,
        separators=(",", ":"),
    )

    try:
        question_char = get_characteristic(
            client,
            QUESTION_CHAR_UUID,
        )

        await client.write_gatt_char(
            question_char,
            message.encode("utf-8"),
            response=True,
        )

        print()
        print("======================================")
        print("[QUESTION TX]")
        print("======================================")
        print(message)
        print("[OK] Current question sent.")
        print("======================================")

    except Exception as exc:
        print(
            f"[ERROR] Failed to send question: "
            f"{type(exc).__name__}: {exc}"
        )


# =====================================================
# MENU
# =====================================================

def show_menu():
    print()
    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")
    print("1. Send current question")
    print("2. Send CONNECTED ACK")
    print("3. Show registered devices")
    print("4. Show BLE connection status")
    print("5. Show backend status")
    print("6. Exit")
    print("======================================")


async def menu_loop(client):
    while True:
        show_menu()

        choice = await asyncio.to_thread(
            input,
            "Select option: ",
        )

        choice = choice.strip()

        if choice == "1":
            await send_current_question(client)

        elif choice == "2":
            await send_ack(
                client,
                '{"type":"ACK","status":"CONNECTED"}',
            )

        elif choice == "3":
            print()
            print("[REGISTERED DEVICES]")

            if not registered_devices:
                print("No devices registered in this gateway session.")
            else:
                for sid, info in registered_devices.items():
                    print(
                        f"  {sid} -> "
                        f"{info['device_mac']} "
                        f"({info['device_name']})"
                    )

        elif choice == "4":
            print(
                "[STATUS] BLE connected."
                if client.is_connected
                else "[STATUS] BLE disconnected."
            )

        elif choice == "5":
            status, result = await api_request_async(
                "GET",
                "/health",
            )

            print(
                f"[STATUS] Backend HTTP {status}: {result}"
            )

        elif choice == "6":
            print("[INFO] Exiting gateway...")
            break

        else:
            print("[ERROR] Invalid option.")

        await asyncio.sleep(0.2)


# =====================================================
# MAIN
# =====================================================

async def main():
    global current_client

    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")
    print(f"Target device : {DEVICE_ADDRESS}")
    print(f"Backend API   : {API_BASE_URL}")
    print(f"Active quiz   : {ACTIVE_QUIZ_ID}")
    print(f"Session ID    : {SESSION_ID}")
    print()

    try:
        status, result = await api_request_async(
            "GET",
            "/health",
        )

        if status == 200:
            print("[OK] Backend API is reachable.")
        else:
            print(
                f"[WARNING] Backend health check failed: "
                f"HTTP {status}"
            )

        async with BleakClient(
            DEVICE_ADDRESS
        ) as client:
            current_client = client

            print("[OK] BLE connected")

            print("\n[INFO] GATT services:")

            for service in client.services:
                print(f"\nService: {service.uuid}")

                for char in service.characteristics:
                    print(
                        f"  Characteristic: {char.uuid} "
                        f"properties={char.properties}"
                    )

            print(
                "\n[INFO] Subscribing to "
                "registration notifications..."
            )

            await client.start_notify(
                REGISTRATION_CHAR_UUID,
                registration_callback,
            )

            print(
                "[INFO] Subscribing to "
                "answer notifications..."
            )

            await client.start_notify(
                ANSWER_CHAR_UUID,
                answer_callback,
            )

            await send_ack(
                client,
                '{"type":"ACK","status":"CONNECTED"}',
            )

            print()
            print("======================================")
            print(" Gateway is running")
            print(" Waiting for Student ID registration")
            print("======================================")

            await menu_loop(client)

            try:
                await client.stop_notify(
                    REGISTRATION_CHAR_UUID
                )
                await client.stop_notify(
                    ANSWER_CHAR_UUID
                )
            except Exception:
                pass

            current_client = None

    except Exception as exc:
        current_client = None

        print()
        print("======================================")
        print("[ERROR] BLE Gateway failed")
        print("======================================")
        print(f"Type   : {type(exc).__name__}")
        print(f"Reason : {exc}")
        print("======================================")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Gateway stopped by user.")
