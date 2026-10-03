import asyncio
import json
from bleak import BleakClient


# =====================================================
# DEVICE
# =====================================================

DEVICE_ADDRESS = "54:43:B2:DC:B0:B2"


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
# QUIZ DATA
# =====================================================

SESSION_ID = "S001"

QUESTIONS = {
    "Q01": {
        "question": "Which protocol is low power?",
        "A": "BLE",
        "B": "WiFi",
        "C": "HTTP",
        "D": "FTP",
        "correct_answer": "A",
    },
    "Q02": {
        "question": "Which device acts as the gateway?",
        "A": "TFT",
        "B": "Keypad",
        "C": "Raspberry Pi",
        "D": "Battery",
        "correct_answer": "C",
    },
}


# =====================================================
# RUNTIME REGISTRATION DATA
# =====================================================

# Student ID <-> device MAC mapping.
registered_devices = {}

# Latest registration received from the device.
current_student_id = ""
current_device_mac = ""
current_device_name = ""


# =====================================================
# HELPER - GET CHARACTERISTIC
# =====================================================

def get_characteristic(client, uuid):
    characteristic = client.services.get_characteristic(uuid)

    if characteristic is None:
        raise RuntimeError(
            f"Characteristic not found: {uuid}"
        )

    return characteristic


# =====================================================
# SEND ACK
# Raspberry Pi -> ESP32
# =====================================================

async def send_ack(client, message):
    data = message.encode("utf-8")

    print()
    print("======================================")
    print("[ACK TX]")
    print("======================================")
    print(message)

    ack_char = get_characteristic(client, ACK_CHAR_UUID)

    print(f"[INFO] ACK characteristic: {ack_char.uuid}")
    print(f"[INFO] Properties: {ack_char.properties}")

    await client.write_gatt_char(
        ack_char,
        data,
        response=True
    )

    print("[OK] ACK sent.")
    print("======================================")


# =====================================================
# SEND REGISTER ACK
# =====================================================

async def send_register_ack(client, student_id, status, reason=None):
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
        json.dumps(packet, separators=(",", ":"))
    )


# =====================================================
# SEND ANSWER ACK
# =====================================================

async def send_answer_ack(
    client,
    question_id,
    status,
    reason=None,
    correct=None
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

    print()
    print("======================================")
    print("[ANSWER ACK TX]")
    print("======================================")

    await send_ack(
        client,
        json.dumps(packet, separators=(",", ":"))
    )


# =====================================================
# REGISTRATION PROCESS
# ESP32 -> Raspberry Pi
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
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")

        await send_register_ack(
            client,
            "",
            "REJECTED",
            "INVALID_JSON"
        )
        return

    if packet.get("type") != "REGISTER":
        print("[ERROR] Invalid registration type.")

        await send_register_ack(
            client,
            packet.get("student_id", ""),
            "REJECTED",
            "INVALID_TYPE"
        )
        return

    student_id = str(packet.get("student_id", "")).strip()
    device_mac = str(packet.get("device_mac", "")).strip().lower()
    device_name = str(packet.get("device_name", "")).strip()

    print(f"Student ID : {student_id}")
    print(f"Device MAC : {device_mac}")
    print(f"Device Name: {device_name}")

    if not student_id:
        print("[ERROR] Student ID is empty.")

        await send_register_ack(
            client,
            "",
            "REJECTED",
            "EMPTY_STUDENT_ID"
        )
        return

    if not device_mac:
        print("[ERROR] Device MAC is empty.")

        await send_register_ack(
            client,
            student_id,
            "REJECTED",
            "EMPTY_DEVICE_MAC"
        )
        return

    # Store mapping in runtime memory.
    registered_devices[student_id] = {
        "device_mac": device_mac,
        "device_name": device_name,
    }

    current_student_id = student_id
    current_device_mac = device_mac
    current_device_name = device_name

    print()
    print("[OK] Registration accepted.")
    print(
        f"[MAP] {student_id} <-> "
        f"{device_mac}"
    )

    print()
    print("[REGISTERED DEVICES]")
    for sid, info in registered_devices.items():
        print(
            f"  {sid} -> "
            f"{info['device_mac']} "
            f"({info['device_name']})"
        )

    await send_register_ack(
        client,
        student_id,
        "ACCEPTED"
    )


# =====================================================
# REGISTRATION CALLBACK
# ESP32 -> Raspberry Pi
# =====================================================

def registration_callback(characteristic, data):
    message = data.decode(
        "utf-8",
        errors="replace"
    )

    client = current_client

    if client is None:
        print("[ERROR] No active BLE client.")
        return

    asyncio.create_task(
        process_registration(
            client,
            message
        )
    )


# =====================================================
# ANSWER PROCESS
# ESP32 -> Raspberry Pi
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
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")

        await send_answer_ack(
            client,
            "",
            "REJECTED",
            "INVALID_JSON"
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

    print(f"Student ID : {student_id}")
    print(f"Question   : {question_id}")
    print(f"Answer     : {answer}")

    # -------------------------------------------------
    # BASIC VALIDATION
    # -------------------------------------------------

    if (
        packet.get("type") != "ANSWER"
        or not student_id
        or not question_id
        or answer not in ("A", "B", "C", "D")
    ):
        print("[ERROR] Invalid answer packet.")

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "INVALID_PACKET"
        )
        return

    # -------------------------------------------------
    # REGISTRATION VALIDATION
    # -------------------------------------------------

    if student_id not in registered_devices:
        print(
            "[ERROR] Student is not registered."
        )

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "STUDENT_NOT_REGISTERED"
        )
        return

    # -------------------------------------------------
    # QUESTION VALIDATION
    # -------------------------------------------------

    if question_id not in QUESTIONS:
        print(
            f"[ERROR] Unknown question: "
            f"{question_id}"
        )

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "UNKNOWN_QUESTION"
        )
        return

    # -------------------------------------------------
    # CHECK ANSWER
    # -------------------------------------------------

    correct_answer = QUESTIONS[
        question_id
    ]["correct_answer"]

    is_correct = (
        answer == correct_answer
    )

    print()
    print(
        f"Correct answer: {correct_answer}"
    )
    print(
        f"Student answer: {answer}"
    )
    print(
        f"Result        : "
        f"{'CORRECT' if is_correct else 'WRONG'}"
    )

    # -------------------------------------------------
    # ACCEPT ANSWER
    # -------------------------------------------------

    await send_answer_ack(
        client,
        question_id,
        "ACCEPTED",
        correct=bool(is_correct)
    )


# =====================================================
# ANSWER CALLBACK
# ESP32 -> Raspberry Pi
# =====================================================

def answer_callback(characteristic, data):
    message = data.decode(
        "utf-8",
        errors="replace"
    )

    client = current_client

    if client is None:
        print("[ERROR] No active BLE client.")
        return

    asyncio.create_task(
        process_answer(
            client,
            message
        )
    )


# =====================================================
# SEND QUESTION
# Raspberry Pi -> ESP32
# =====================================================

async def send_question(client, question_id):
    if question_id not in QUESTIONS:
        print(
            f"[ERROR] Unknown question: "
            f"{question_id}"
        )
        return

    q = QUESTIONS[question_id]

    packet = {
        "type": "QUESTION",
        "session_id": SESSION_ID,
        "question_id": question_id,
        "question": q["question"],
        "A": q["A"],
        "B": q["B"],
        "C": q["C"],
        "D": q["D"],
    }

    message = json.dumps(
        packet,
        separators=(",", ":")
    )

    data = message.encode("utf-8")

    print()
    print("======================================")
    print("[QUESTION TX]")
    print("======================================")
    print(message)
    print("======================================")

    try:
        question_char = get_characteristic(
            client,
            QUESTION_CHAR_UUID
        )

        await client.write_gatt_char(
            question_char,
            data,
            response=True
        )

        print(
            f"[OK] {question_id} sent successfully."
        )

    except Exception as e:
        print(
            "[ERROR] Failed to send question."
        )
        print(
            f"Reason: {type(e).__name__}: {e}"
        )


# =====================================================
# MENU
# =====================================================

def show_menu():
    print()
    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")
    print("1. Send Q01")
    print("2. Send Q02")
    print("3. Send CONNECTED ACK")
    print("4. Show registered devices")
    print("5. Show BLE connection status")
    print("6. Exit")
    print("======================================")


async def menu_loop(client):
    while True:
        show_menu()

        choice = await asyncio.to_thread(
            input,
            "Select option: "
        )

        choice = choice.strip()

        # -------------------------------------------------
        # Q01
        # -------------------------------------------------

        if choice == "1":
            await send_question(
                client,
                "Q01"
            )

        # -------------------------------------------------
        # Q02
        # -------------------------------------------------

        elif choice == "2":
            await send_question(
                client,
                "Q02"
            )

        # -------------------------------------------------
        # CONNECTED ACK
        # -------------------------------------------------

        elif choice == "3":
            await send_ack(
                client,
                '{"type":"ACK","status":"CONNECTED"}'
            )

        # -------------------------------------------------
        # REGISTERED DEVICES
        # -------------------------------------------------

        elif choice == "4":
            print()
            print("======================================")
            print("[REGISTERED DEVICES]")
            print("======================================")

            if not registered_devices:
                print("No devices registered.")
            else:
                for sid, info in registered_devices.items():
                    print(
                        f"Student ID : {sid}"
                    )
                    print(
                        f"Device MAC : "
                        f"{info['device_mac']}"
                    )
                    print(
                        f"Device Name: "
                        f"{info['device_name']}"
                    )
                    print("--------------------------------------")

        # -------------------------------------------------
        # CONNECTION STATUS
        # -------------------------------------------------

        elif choice == "5":
            print()

            if client.is_connected:
                print(
                    "[STATUS] BLE connected."
                )
            else:
                print(
                    "[STATUS] BLE disconnected."
                )

        # -------------------------------------------------
        # EXIT
        # -------------------------------------------------

        elif choice == "6":
            print(
                "\n[INFO] Exiting gateway..."
            )
            break

        else:
            print(
                "\n[ERROR] Invalid option."
            )

        await asyncio.sleep(0.2)


# =====================================================
# GLOBAL CLIENT
# =====================================================

current_client = None


# =====================================================
# MAIN
# =====================================================

async def main():
    global current_client

    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")
    print(
        f"Target device: {DEVICE_ADDRESS}"
    )
    print()

    try:
        async with BleakClient(
            DEVICE_ADDRESS
        ) as client:

            current_client = client

            print("[OK] BLE connected")

            # -------------------------------------------------
            # GATT SERVICES
            # -------------------------------------------------

            print("\n[INFO] GATT services:")

            for service in client.services:
                print(
                    f"\nService: {service.uuid}"
                )

                for char in service.characteristics:
                    print(
                        f"  Characteristic: "
                        f"{char.uuid} "
                        f"properties="
                        f"{char.properties}"
                    )

            # -------------------------------------------------
            # SUBSCRIBE REGISTRATION
            # -------------------------------------------------

            print(
                "\n[INFO] Subscribing to "
                "registration notifications..."
            )

            await client.start_notify(
                REGISTRATION_CHAR_UUID,
                registration_callback
            )

            # -------------------------------------------------
            # SUBSCRIBE ANSWER
            # -------------------------------------------------

            print(
                "[INFO] Subscribing to "
                "answer notifications..."
            )

            await client.start_notify(
                ANSWER_CHAR_UUID,
                answer_callback
            )

            print(
                "[OK] Notification handlers enabled"
            )

            # -------------------------------------------------
            # INITIAL CONNECTED ACK
            # -------------------------------------------------

            await send_ack(
                client,
                '{"type":"ACK","status":"CONNECTED"}'
            )

            print()
            print("======================================")
            print(" Gateway is running")
            print(" Waiting for Student ID registration")
            print("======================================")

            await menu_loop(client)

            # -------------------------------------------------
            # CLEANUP
            # -------------------------------------------------

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

            print(
                "\n[INFO] BLE notifications stopped."
            )

    except Exception as e:
        current_client = None

        print()
        print("======================================")
        print("[ERROR] BLE Gateway failed")
        print("======================================")
        print(
            f"Type   : {type(e).__name__}"
        )
        print(
            f"Reason : {e}"
        )
        print("======================================")


# =====================================================
# PROGRAM ENTRY
# =====================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n")
        print("======================================")
        print("[INFO] Gateway stopped by user.")
        print("======================================")
