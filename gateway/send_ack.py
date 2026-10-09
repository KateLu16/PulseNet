import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from bleak import BleakClient


# ============================================================
# CONFIGURATION
# ============================================================

DEVICE_ADDRESS = "54:43:B2:DC:B0:B2"

FASTAPI_URL = "http://127.0.0.1:8000"

# Whole-quiz countdown (seconds) used when the teacher has
# not set a custom time limit on the dashboard.
QUIZ_DEFAULT_TIME_LIMIT_SEC = 300

# How often the gateway re-reads quiz state from the backend.
QUIZ_POLL_INTERVAL = 1.5

# Headless mode: run without the interactive menu so the
# gateway can be daemonized with nohup/systemd. Active
# automatically when stdin is not a TTY (e.g. background
# start via start_gateway.sh).
INTERACTIVE = sys.stdin.isatty()

HEARTBEAT_INTERVAL = 2.0

QUESTION_POLL_INTERVAL = 1.5

RECONNECT_DELAY = 3.0


# ============================================================
# BLE UUID
# ============================================================

REGISTRATION_CHAR_UUID = (
    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
)

QUESTION_CHAR_UUID = (
    "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
)

ANSWER_CHAR_UUID = (
    "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"
)

ACK_CHAR_UUID = (
    "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"
)


# ============================================================
# ACTIVE QUIZ STATE
# ============================================================

# The gateway does NOT hard-code quiz_id anymore.
#
# Teacher Web starts a quiz:
#
#     POST /api/quizzes/{quiz_id}/start
#
# Then this gateway discovers the quiz whose status is "running".
#
ACTIVE_QUIZ_ID = None
ACTIVE_SESSION_ID = None

# Mirrored quiz attributes for QUIZ_INFO packets and the
# quiz countdown.
ACTIVE_QUIZ_TITLE = ""
ACTIVE_QUIZ_STATUS = ""
ACTIVE_QUIZ_TIME_LIMIT = 300
ACTIVE_QUIZ_EXPECTED = 0
ACTIVE_QUIZ_PREFIX = ""
ACTIVE_QUIZ_ID_LENGTH = 0

# Last question number pushed to the device by the
# auto-push loop (None = nothing pushed yet).
LAST_PUSHED_QUESTION = None

# When the current question was pushed, and whether we are
# still waiting for an answer to it (informational only —
# the quiz countdown is global, not per question).
PUSHED_AT = 0.0

# Question list cache per quiz (for self-paced advancing).
QUIZ_QUESTIONS = []
QUIZ_QUESTIONS_QUIZ_ID = None

# (quiz_id, status, time_limit) of the last QUIZ_INFO packet
# sent to the device, so we only resend when something
# actually changed.
QUIZ_SENT_INFO_KEY = None

# Quiz id for which a QUIZ_END has already been sent.
QUIZ_END_SENT_QUIZ = None


# ============================================================
# RUNTIME REGISTRATION DATA
# ============================================================

# student_id -> {
#     "device_mac": "...",
#     "device_name": "...",
#     "quiz_id": 1,
# }
registered_devices = {}


# ============================================================
# GLOBAL BLE CLIENT
# ============================================================

current_client = None


# ============================================================
# HELPER - NORMALIZE MAC
# ============================================================

def normalize_mac(device_mac):
    """
    Normalize BLE MAC address.

    Example:

        54:43:b2:dc:b0:b2

    becomes:

        54:43:B2:DC:B0:B2
    """

    return str(device_mac).strip().upper()


# ============================================================
# HELPER - HTTP JSON GET
# ============================================================

def http_get_json(url):
    """
    Perform HTTP GET and return:

        (success, result)

    result is parsed JSON when possible.
    """

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:

            body = response.read().decode(
                "utf-8"
            )

            print(
                f"[HTTP GET] {url}"
            )

            print(
                f"[HTTP] {response.status}"
            )

            print(
                f"[BODY] {body}"
            )

            if (
                response.status < 200
                or response.status >= 300
            ):
                return False, None

            try:
                return True, json.loads(body)

            except json.JSONDecodeError as e:

                print(
                    "[ERROR] Invalid JSON response."
                )

                print(
                    f"Reason: {e}"
                )

                return False, None

    except urllib.error.HTTPError as e:

        body = e.read().decode(
            "utf-8",
            errors="replace",
        )

        print(
            f"[ERROR] HTTP GET failed: {e.code}"
        )

        print(
            f"Response: {body}"
        )

        try:
            return False, json.loads(body)

        except json.JSONDecodeError:
            return False, None

    except urllib.error.URLError as e:

        print(
            "[ERROR] Cannot connect to FastAPI."
        )

        print(
            f"Reason: {e.reason}"
        )

        return False, None

    except Exception as e:

        print(
            "[ERROR] HTTP GET failed."
        )

        print(
            f"Type  : {type(e).__name__}"
        )

        print(
            f"Reason: {e}"
        )

        return False, None


# ============================================================
# HELPER - HTTP JSON POST
# ============================================================

def http_post_json(
    url,
    payload,
):
    """
    Perform HTTP POST with JSON body.

    Returns:

        (success, result)
    """

    data = json.dumps(
        payload
    ).encode(
        "utf-8"
    )

    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    print()
    print("======================================")
    print("[HTTP POST]")
    print("======================================")

    print(
        f"URL     : {url}"
    )

    print(
        f"Payload : {json.dumps(payload)}"
    )

    print("======================================")

    try:

        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:

            response_body = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

            print(
                f"HTTP    : {response.status}"
            )

            print(
                f"Response: {response_body}"
            )

            if (
                response.status < 200
                or response.status >= 300
            ):
                return False, None

            try:

                result = json.loads(
                    response_body
                )

            except json.JSONDecodeError as e:

                print(
                    "[ERROR] Invalid JSON response."
                )

                print(
                    f"Reason: {e}"
                )

                return False, None

            return True, result

    except urllib.error.HTTPError as e:

        error_body = (
            e.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        print(
            f"[ERROR] HTTP error: {e.code}"
        )

        print(
            f"Response: {error_body}"
        )

        try:

            return False, json.loads(
                error_body
            )

        except json.JSONDecodeError:

            return False, None

    except urllib.error.URLError as e:

        print(
            "[ERROR] Cannot connect to FastAPI."
        )

        print(
            f"Reason: {e.reason}"
        )

        return False, None

    except Exception as e:

        print(
            "[ERROR] HTTP POST failed."
        )

        print(
            f"Type  : {type(e).__name__}"
        )

        print(
            f"Reason: {e}"
        )

        return False, None


# ============================================================
# QUIET HTTP HELPERS
# For background loops (heartbeat, question poll):
# no logging — they run every 1.5-2 seconds.
# ============================================================

def http_get_json_quiet(url):
    try:
        with urllib.request.urlopen(
            url,
            timeout=5,
        ) as response:
            body = response.read().decode("utf-8")
            if not (200 <= response.status < 300):
                return False, None
            return True, json.loads(body)
    except Exception:
        return False, None


def http_post_json_quiet(url, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            body = response.read().decode("utf-8")
            if not (200 <= response.status < 300):
                return False, None
            return True, json.loads(body)
    except Exception:
        return False, None


# ============================================================
# GET RUNNING QUIZ
# Teacher Web -> FastAPI -> Gateway
# ============================================================

def get_running_quiz():
    """
    Discover the quiz currently running in FastAPI.

    Teacher Web starts a quiz through:

        POST /api/quizzes/{quiz_id}/start

    Then:

        GET /api/quizzes

    returns all quizzes.

    We select the quiz with:

        status == "running"

    Returns:

        {
            "id": ...,
            "title": ...,
            "status": "running",
            ...
        }

    or None.
    """

    url = (
        f"{FASTAPI_URL}"
        "/api/quizzes"
    )

    success, result = (
        http_get_json(url)
    )

    if not success:
        print(
            "[ERROR] Cannot get quizzes "
            "from FastAPI."
        )

        return None

    if not isinstance(
        result,
        list,
    ):

        print(
            "[ERROR] /api/quizzes "
            "did not return a list."
        )

        return None

    running_quizzes = [
        quiz
        for quiz in result
        if quiz.get("status") == "running"
    ]

    if not running_quizzes:

        # ------------------------------------------------
        # No running quiz.
        #
        # Fall back to the NEWEST draft quiz so students
        # can register BEFORE the teacher starts the quiz
        # (the backend accepts registration for both
        # draft and running quizzes).
        # ------------------------------------------------

        draft_quizzes = [
            quiz
            for quiz in result
            if quiz.get("status") == "draft"
        ]

        if draft_quizzes:

            draft_quizzes.sort(
                key=lambda quiz: quiz.get("id") or 0,
                reverse=True,
            )

            if len(draft_quizzes) > 1:

                print(
                    "[WARN] Multiple draft quizzes. "
                    "Using the newest one."
                )

            print(
                "[INFO] No running quiz. "
                "Using newest draft quiz "
                f"{draft_quizzes[0].get('id')} "
                "for registration."
            )

            return draft_quizzes[0]

        print(
            "[INFO] No running or draft quiz."
        )

        return None

    if len(running_quizzes) > 1:

        print()
        print("======================================")
        print("[ERROR] MULTIPLE RUNNING QUIZZES")
        print("======================================")

        for quiz in running_quizzes:

            print(
                f"Quiz ID : {quiz.get('id')}"
            )

            print(
                f"Title   : {quiz.get('title')}"
            )

            print(
                "--------------------------------------"
            )

        print(
            "[ERROR] Gateway cannot determine "
            "which quiz should receive registration."
        )

        print("======================================")

        return None

    quiz = running_quizzes[0]

    return quiz


# ============================================================
# REFRESH ACTIVE QUIZ
# ============================================================

def refresh_active_quiz():
    """
    Discover and store the currently running quiz.
    """

    global ACTIVE_QUIZ_ID
    global ACTIVE_SESSION_ID

    quiz = get_running_quiz()

    if quiz is None:

        ACTIVE_QUIZ_ID = None
        ACTIVE_SESSION_ID = None

        return False

    ACTIVE_QUIZ_ID = quiz.get(
        "id"
    )

    # The current backend does not have a
    # dedicated session_id field.
    #
    # Therefore we use a deterministic runtime
    # session identifier based on quiz_id.
    ACTIVE_SESSION_ID = (
        f"QUIZ-{ACTIVE_QUIZ_ID}"
    )

    print()
    print("======================================")
    print("[ACTIVE QUIZ]")
    print("======================================")

    print(
        f"Quiz ID : {ACTIVE_QUIZ_ID}"
    )

    print(
        f"Title   : {quiz.get('title')}"
    )

    print(
        f"Status  : {quiz.get('status')}"
    )

    print(
        f"Session : {ACTIVE_SESSION_ID}"
    )

    print("======================================")

    return True


# ============================================================
# GET CURRENT QUESTION FROM FASTAPI
# ============================================================

def get_current_question():
    """
    Get the current question selected by Teacher Web.

    Endpoint:

        GET /api/quizzes/{quiz_id}/current
    """

    if ACTIVE_QUIZ_ID is None:

        print(
            "[ERROR] No active quiz."
        )

        return None

    url = (
        f"{FASTAPI_URL}"
        f"/api/quizzes/"
        f"{ACTIVE_QUIZ_ID}"
        "/current"
    )

    success, result = (
        http_get_json(url)
    )

    if not success:
        print(
            "[ERROR] Failed to get current "
            "question."
        )

        return None

    return result


# ============================================================
# GET BLE CHARACTERISTIC
# ============================================================

def get_characteristic(
    client,
    uuid,
):
    """
    Get GATT characteristic.

    Bleak performs service discovery after connection.
    """

    if not client.is_connected:

        raise RuntimeError(
            "BLE client is not connected."
        )

    services = client.services

    if services is None:

        raise RuntimeError(
            "BLE services are not available."
        )

    characteristic = (
        services.get_characteristic(
            uuid
        )
    )

    if characteristic is None:

        raise RuntimeError(
            f"Characteristic not found: {uuid}"
        )

    return characteristic


# ============================================================
# SEND ACK
# Raspberry Pi -> ESP32
# ============================================================

async def send_ack(
    client,
    message,
):
    data = message.encode(
        "utf-8"
    )

    print()
    print("======================================")
    print("[ACK TX]")
    print("======================================")

    print(message)

    print("======================================")

    ack_char = get_characteristic(
        client,
        ACK_CHAR_UUID,
    )

    print(
        f"[INFO] ACK characteristic: "
        f"{ack_char.uuid}"
    )

    print(
        f"[INFO] Properties: "
        f"{ack_char.properties}"
    )

    await client.write_gatt_char(
        ack_char,
        data,
        response=True,
    )

    print(
        "[OK] ACK sent."
    )


# ============================================================
# SEND REGISTER ACK
# ============================================================

async def send_register_ack(
    client,
    student_id,
    status,
    reason=None,
):
    packet = {
        "type": "REGISTER_ACK",
        "session_id": ACTIVE_SESSION_ID,
        "quiz_id": ACTIVE_QUIZ_ID,
        "student_id": student_id,
        "status": status,
    }

    if reason:
        packet["reason"] = reason

    await send_ack(
        client,
        json.dumps(
            packet,
            separators=(
                ",",
                ":",
            ),
        ),
    )


# ============================================================
# SEND ANSWER ACK
# ============================================================

async def send_answer_ack(
    client,
    question_id,
    status,
    reason=None,
    correct=None,
):
    packet = {
        "type": "ANSWER_ACK",
        "session_id": ACTIVE_SESSION_ID,
        "quiz_id": ACTIVE_QUIZ_ID,
        "question_id": question_id,
        "status": status,
    }

    if correct is not None:
        packet["correct"] = correct

    if reason:
        packet["reason"] = reason

    await send_ack(
        client,
        json.dumps(
            packet,
            separators=(
                ",",
                ":",
            ),
        ),
    )


# ============================================================
# REGISTER DEVICE WITH FASTAPI
# Raspberry Pi -> FastAPI
# ============================================================

def register_device_with_fastapi(
    student_id,
    device_mac,
    device_name,
    quiz_id,
):
    """
    Register a physical device to a student
    for ONE SPECIFIC QUIZ.

    Backend endpoint:

        POST /api/devices/register

    Required payload:

        {
            "student_id": "...",
            "device_mac": "...",
            "device_code": "...",
            "quiz_id": 2
        }
    """

    device_mac = normalize_mac(
        device_mac
    )

    payload = {
        "student_id": student_id,
        "device_mac": device_mac,
        "device_code": device_name,
        "quiz_id": quiz_id,
    }

    url = (
        f"{FASTAPI_URL}"
        "/api/devices/register"
    )

    success, result = (
        http_post_json(
            url,
            payload,
        )
    )

    if not success:

        print(
            "[ERROR] FastAPI registration failed."
        )

        return False, result

    if not isinstance(
        result,
        dict,
    ):

        print(
            "[ERROR] Invalid FastAPI response."
        )

        return False, None

    if result.get(
        "success"
    ) is not True:

        print(
            "[ERROR] FastAPI rejected "
            "device registration."
        )

        print(
            f"Reason: "
            f"{result.get('message', 'Unknown error')}"
        )

        return False, result

    print(
        "[OK] Device registered "
        "with FastAPI."
    )

    return True, result


# ============================================================
# SUBMIT ANSWER TO FASTAPI
# Raspberry Pi -> FastAPI
# ============================================================

def submit_answer_to_fastapi(
    student_id,
    device_mac,
    question_id,
    answer,
    quiz_id,
    sequence=None,
):
    """
    Submit answer using the active quiz.

    Endpoint:

        POST /api/responses/answer
    """

    device_mac = normalize_mac(
        device_mac
    )

    payload = {
        "student_id": student_id,
        "device_mac": device_mac,
        "quiz_id": quiz_id,
        "question_id": question_id,
        "answer": answer,
    }

    if sequence is not None:

        payload["sequence"] = sequence

    url = (
        f"{FASTAPI_URL}"
        "/api/responses/answer"
    )

    success, result = (
        http_post_json(
            url,
            payload,
        )
    )

    if not success:

        print(
            "[ERROR] FastAPI rejected answer."
        )

        return False, result

    if not isinstance(
        result,
        dict,
    ):

        return False, None

    if result.get(
        "success"
    ) is not True:

        print(
            "[ERROR] FastAPI did not "
            "accept the answer."
        )

        return False, result

    print(
        "[OK] Answer accepted by FastAPI."
    )

    print(
        f"[RESULT] "
        f"{'CORRECT' if result.get('correct') else 'WRONG'}"
    )

    return True, result


# ============================================================
# REGISTRATION PROCESS
# ESP32 -> Raspberry Pi -> FastAPI
# ============================================================

async def process_registration(
    client,
    message,
):
    global current_student_id
    global current_device_mac
    global current_device_name

    print()
    print("======================================")
    print("[REGISTRATION RECEIVED]")
    print("======================================")

    print(message)

    print("======================================")

    # --------------------------------------------------------
    # REFRESH ACTIVE QUIZ
    # --------------------------------------------------------

    if not refresh_active_quiz():

        await send_register_ack(
            client,
            "",
            "REJECTED",
            "NO_ACTIVE_QUIZ",
        )

        return

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    try:

        packet = json.loads(
            message
        )

    except json.JSONDecodeError as e:

        print(
            f"[ERROR] Invalid JSON: {e}"
        )

        await send_register_ack(
            client,
            "",
            "REJECTED",
            "INVALID_JSON",
        )

        return

    # --------------------------------------------------------
    # CHECK TYPE
    # --------------------------------------------------------

    if packet.get(
        "type"
    ) != "REGISTER":

        print(
            "[ERROR] Invalid registration type."
        )

        await send_register_ack(
            client,
            packet.get(
                "student_id",
                "",
            ),
            "REJECTED",
            "INVALID_TYPE",
        )

        return

    # --------------------------------------------------------
    # EXTRACT DATA
    # --------------------------------------------------------

    student_id = str(
        packet.get(
            "student_id",
            "",
        )
    ).strip()

    device_mac = normalize_mac(
        packet.get(
            "device_mac",
            "",
        )
    )

    device_name = str(
        packet.get(
            "device_name",
            "",
        )
    ).strip()

    print(
        f"Student ID : {student_id}"
    )

    print(
        f"Device MAC : {device_mac}"
    )

    print(
        f"Device Name: {device_name}"
    )

    print(
        f"Quiz ID    : {ACTIVE_QUIZ_ID}"
    )

    # --------------------------------------------------------
    # VALIDATE STUDENT ID
    # --------------------------------------------------------

    if not student_id:

        print(
            "[ERROR] Student ID is empty."
        )

        await send_register_ack(
            client,
            "",
            "REJECTED",
            "EMPTY_STUDENT_ID",
        )

        return

    # --------------------------------------------------------
    # VALIDATE MAC
    # --------------------------------------------------------

    if not device_mac:

        print(
            "[ERROR] Device MAC is empty."
        )

        await send_register_ack(
            client,
            student_id,
            "REJECTED",
            "EMPTY_DEVICE_MAC",
        )

        return

    # --------------------------------------------------------
    # REGISTER WITH FASTAPI
    # --------------------------------------------------------

    success, result = (
        register_device_with_fastapi(
            student_id=student_id,
            device_mac=device_mac,
            device_name=device_name,
            quiz_id=ACTIVE_QUIZ_ID,
        )
    )

    # --------------------------------------------------------
    # FASTAPI REJECTED
    # --------------------------------------------------------

    if not success:

        print(
            "[ERROR] FastAPI rejected "
            "device registration."
        )

        reason = (
            "SERVER_REGISTRATION_FAILED"
        )

        if result is not None:

            detail = result.get(
                "detail"
            )

            message_from_server = (
                result.get(
                    "message"
                )
            )

            if detail:

                if isinstance(
                    detail,
                    str,
                ):
                    reason = detail

                else:
                    reason = str(
                        detail
                    )

            elif message_from_server:

                reason = str(
                    message_from_server
                )

        await send_register_ack(
            client,
            student_id,
            "REJECTED",
            reason,
        )

        return

    # --------------------------------------------------------
    # STORE RUNTIME MAPPING
    # --------------------------------------------------------

    registered_devices[
        student_id
    ] = {
        "device_mac": device_mac,
        "device_name": device_name,
        "quiz_id": ACTIVE_QUIZ_ID,
    }

    current_student_id = student_id
    current_device_mac = device_mac
    current_device_name = device_name

    # --------------------------------------------------------
    # PRINT REGISTRATION
    # --------------------------------------------------------

    print()
    print("======================================")
    print("[OK] REGISTRATION ACCEPTED")
    print("======================================")

    print(
        f"Quiz ID    : {ACTIVE_QUIZ_ID}"
    )

    print(
        f"Student ID : {student_id}"
    )

    print(
        f"Device MAC : {device_mac}"
    )

    print(
        f"Device Name: {device_name}"
    )

    print("======================================")

    # --------------------------------------------------------
    # SEND ACCEPTED ACK
    # --------------------------------------------------------

    await send_register_ack(
        client,
        student_id,
        "ACCEPTED",
    )


# ============================================================
# REGISTRATION CALLBACK
# ESP32 -> Raspberry Pi
# ============================================================

def registration_callback(
    characteristic,
    data,
):
    message = data.decode(
        "utf-8",
        errors="replace",
    )

    client = current_client

    if client is None:

        print(
            "[ERROR] No active BLE client."
        )

        return

    asyncio.create_task(
        process_registration(
            client,
            message,
        )
    )


# ============================================================
# ANSWER PROCESS
# ESP32 -> Raspberry Pi -> FastAPI
# ============================================================

async def process_answer(
    client,
    message,
):
    print()
    print("======================================")
    print("[ANSWER RECEIVED]")
    print("======================================")

    print(message)

    print("======================================")

    # --------------------------------------------------------
    # PARSE JSON
    # --------------------------------------------------------

    try:

        packet = json.loads(
            message
        )

    except json.JSONDecodeError as e:

        print(
            f"[ERROR] Invalid JSON: {e}"
        )

        await send_answer_ack(
            client,
            "",
            "REJECTED",
            "INVALID_JSON",
        )

        return

    # --------------------------------------------------------
    # CHECK TYPE
    # --------------------------------------------------------

    if packet.get(
        "type"
    ) != "ANSWER":

        print(
            "[ERROR] Invalid answer type."
        )

        await send_answer_ack(
            client,
            packet.get(
                "question_id",
                "",
            ),
            "REJECTED",
            "INVALID_TYPE",
        )

        return

    # --------------------------------------------------------
    # GET ACTIVE QUIZ
    # --------------------------------------------------------

    if ACTIVE_QUIZ_ID is None:

        refresh_active_quiz()

    if ACTIVE_QUIZ_ID is None:

        print(
            "[ERROR] No active quiz."
        )

        await send_answer_ack(
            client,
            packet.get(
                "question_id",
                "",
            ),
            "REJECTED",
            "NO_ACTIVE_QUIZ",
        )

        return

    # --------------------------------------------------------
    # EXTRACT DATA
    # --------------------------------------------------------

    student_id = str(
        packet.get(
            "student_id",
            "",
        )
    ).strip()

    question_id = str(
        packet.get(
            "question_id",
            "",
        )
    ).strip().upper()

    answer = str(
        packet.get(
            "answer",
            "",
        )
    ).strip().upper()

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    if not student_id:

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "EMPTY_STUDENT_ID",
        )

        return

    if not question_id:

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "EMPTY_QUESTION_ID",
        )

        return

    if answer not in (
        "A",
        "B",
        "C",
        "D",
    ):

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "INVALID_ANSWER",
        )

        return

    # --------------------------------------------------------
    # CHECK REGISTRATION
    # --------------------------------------------------------

    if student_id not in registered_devices:

        print(
            "[ERROR] Student is not registered."
        )

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "STUDENT_NOT_REGISTERED",
        )

        return

    # --------------------------------------------------------
    # GET REGISTERED DEVICE
    # --------------------------------------------------------

    device_info = (
        registered_devices[
            student_id
        ]
    )

    device_mac = normalize_mac(
        device_info[
            "device_mac"
        ]
    )

    registered_quiz_id = (
        device_info.get(
            "quiz_id"
        )
    )

    # --------------------------------------------------------
    # MAKE SURE DEVICE BELONGS TO
    # CURRENT QUIZ
    # --------------------------------------------------------

    if (
        registered_quiz_id
        != ACTIVE_QUIZ_ID
    ):

        print(
            "[ERROR] Student registration "
            "belongs to another quiz."
        )

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            "QUIZ_REGISTRATION_MISMATCH",
        )

        return

    print(
        f"Student ID : {student_id}"
    )

    print(
        f"Device MAC : {device_mac}"
    )

    print(
        f"Quiz ID    : {ACTIVE_QUIZ_ID}"
    )

    print(
        f"Question   : {question_id}"
    )

    print(
        f"Answer     : {answer}"
    )

    # --------------------------------------------------------
    # SEQUENCE
    # --------------------------------------------------------

    sequence = packet.get(
        "sequence"
    )

    if sequence is None:

        try:

            sequence = int(
                question_id
                .replace(
                    "Q",
                    "",
                )
            )

        except ValueError:

            sequence = None

    # --------------------------------------------------------
    # SUBMIT ANSWER
    # --------------------------------------------------------

    success, result = (
        submit_answer_to_fastapi(
            student_id=student_id,
            device_mac=device_mac,
            question_id=question_id,
            answer=answer,
            quiz_id=ACTIVE_QUIZ_ID,
            sequence=sequence,
        )
    )

    # --------------------------------------------------------
    # FASTAPI REJECTED
    # --------------------------------------------------------

    if not success:

        print(
            "[ERROR] Answer rejected by FastAPI."
        )

        reason = (
            "SERVER_ANSWER_FAILED"
        )

        if result is not None:

            detail = result.get(
                "detail"
            )

            if detail:

                if isinstance(
                    detail,
                    str,
                ):
                    reason = detail

                else:
                    reason = str(
                        detail
                    )

            elif result.get(
                "status"
            ):

                reason = str(
                    result.get(
                        "status"
                    )
                )

        await send_answer_ack(
            client,
            question_id,
            "REJECTED",
            reason,
        )

        return

    # --------------------------------------------------------
    # GET RESULT
    # --------------------------------------------------------

    is_correct = bool(
        result.get(
            "correct",
            False,
        )
    )

    status = result.get(
        "status",
        "ACCEPTED",
    )

    print()
    print("======================================")
    print("[ANSWER RESULT]")
    print("======================================")

    print(
        f"Quiz   : {ACTIVE_QUIZ_ID}"
    )

    print(
        f"Student: {student_id}"
    )

    print(
        f"Question: {question_id}"
    )

    print(
        f"Answer : {answer}"
    )

    print(
        f"Status : {status}"
    )

    print(
        f"Result : "
        f"{'CORRECT' if is_correct else 'WRONG'}"
    )

    print("======================================")

    # --------------------------------------------------------
    # SEND ACK
    # --------------------------------------------------------

    await send_answer_ack(
        client,
        question_id,
        "ACCEPTED",
        correct=is_correct,
    )

    # ------------------------------------------------
    # SELF-PACED ADVANCE: push the next question right
    # after the answer is accepted.
    # ------------------------------------------------

    try:
        answered_number = int(
            str(question_id).replace("Q", "")
        )
    except ValueError:
        answered_number = LAST_PUSHED_QUESTION or 0

    await push_next_question(
        client,
        answered_number,
    )


# ============================================================
# ANSWER CALLBACK
# ESP32 -> Raspberry Pi
# ============================================================

def answer_callback(
    characteristic,
    data,
):
    message = data.decode(
        "utf-8",
        errors="replace",
    )

    client = current_client

    if client is None:

        print(
            "[ERROR] No active BLE client."
        )

        return

    asyncio.create_task(
        process_answer(
            client,
            message,
        )
    )


# ============================================================
# SEND CURRENT QUESTION
# Raspberry Pi -> ESP32
# ============================================================

async def send_current_question(
    client,
):
    """
    Get the question currently selected by Teacher Web
    and send it to ESP32.

    Teacher Web controls:

        POST /api/quizzes/{quiz_id}/start
        POST /api/quizzes/{quiz_id}/next

    Gateway reads:

        GET /api/quizzes/{quiz_id}/current
    """

    if ACTIVE_QUIZ_ID is None:

        if not refresh_active_quiz():

            print(
                "[ERROR] No active quiz."
            )

            return False

    question = (
        get_current_question()
    )

    if question is None:

        print(
            "[ERROR] No current question."
        )

        return False

    question_id = (
        f"Q{int(question['question_number']):02d}"
    )

    packet = {
        "type": "QUESTION",
        "session_id": ACTIVE_SESSION_ID,
        "quiz_id": ACTIVE_QUIZ_ID,
        "question_id": question_id,
        "question": question[
            "question_text"
        ],
        "A": question[
            "option_a"
        ],
        "B": question[
            "option_b"
        ],
        "C": question[
            "option_c"
        ],
        "D": question[
            "option_d"
        ],
    }

    message = json.dumps(
        packet,
        separators=(
            ",",
            ":",
        ),
    )

    data = message.encode(
        "utf-8"
    )

    print()
    print("======================================")
    print("[QUESTION TX]")
    print("======================================")

    print(
        f"Quiz ID  : {ACTIVE_QUIZ_ID}"
    )

    print(
        f"Question : {question_id}"
    )

    print(
        message
    )

    print("======================================")

    try:

        question_char = (
            get_characteristic(
                client,
                QUESTION_CHAR_UUID,
            )
        )

        await client.write_gatt_char(
            question_char,
            data,
            response=True,
        )

        print(
            "[OK] Current question "
            "sent successfully."
        )

        return True

    except Exception as e:

        print(
            "[ERROR] Failed to send question."
        )

        print(
            f"Type  : {type(e).__name__}"
        )

        print(
            f"Reason: {e}"
        )

        return False


# ============================================================
# SELF-PACED QUESTION ADVANCE
# After a student answers (or the time runs out), the
# gateway pushes the next question to the device without
# waiting for the teacher.
# ============================================================

async def ensure_questions_cache():
    """
    Load the quiz's question list once per quiz.

    An EMPTY cache is re-fetched on every call: questions
    may have been imported after the first load (e.g. the
    gateway connected before the teacher finished importing).
    """
    global QUIZ_QUESTIONS
    global QUIZ_QUESTIONS_QUIZ_ID

    if ACTIVE_QUIZ_ID is None:
        return False

    if (
        QUIZ_QUESTIONS_QUIZ_ID == ACTIVE_QUIZ_ID
        and QUIZ_QUESTIONS
    ):
        return True

    url = (
        f"{FASTAPI_URL}/api/quizzes/"
        f"{ACTIVE_QUIZ_ID}/questions"
    )

    success, questions = await asyncio.to_thread(
        http_get_json_quiet,
        url,
    )

    if not success or not isinstance(questions, list):
        return False

    previous_count = len(QUIZ_QUESTIONS)

    QUIZ_QUESTIONS = sorted(
        questions,
        key=lambda q: q.get("question_number") or 0,
    )

    QUIZ_QUESTIONS_QUIZ_ID = ACTIVE_QUIZ_ID

    if len(QUIZ_QUESTIONS) != previous_count:
        print(
            f"[CACHE] {len(QUIZ_QUESTIONS)} questions "
            f"loaded for quiz {ACTIVE_QUIZ_ID}."
        )

    return bool(QUIZ_QUESTIONS)


async def send_question_dict(
    client,
    question,
):
    """
    Send one QUESTION packet (from the cache) to the device.
    """
    global LAST_PUSHED_QUESTION
    global PUSHED_AT

    question_number = int(
        question["question_number"]
    )

    question_id = f"Q{question_number:02d}"

    packet = {
        "type": "QUESTION",
        "session_id": ACTIVE_SESSION_ID,
        "quiz_id": ACTIVE_QUIZ_ID,
        "question_id": question_id,
        "number": question_number,
        "total": len(QUIZ_QUESTIONS),
        "question": question["question_text"],
        "A": question["option_a"],
        "B": question["option_b"],
        "C": question["option_c"],
        "D": question["option_d"],
    }

    data = json.dumps(
        packet,
        separators=(",", ":"),
    ).encode("utf-8")

    print()
    print("======================================")
    print("[QUESTION TX]")
    print(f"Quiz ID  : {ACTIVE_QUIZ_ID}")
    print(f"Question : {question_id}")
    print("======================================")

    try:
        question_char = get_characteristic(
            client,
            QUESTION_CHAR_UUID,
        )

        await client.write_gatt_char(
            question_char,
            data,
            response=True,
        )

        LAST_PUSHED_QUESTION = question_number
        PUSHED_AT = time.time()

        print(
            "[OK] Question sent to device."
        )

        return True

    except Exception as e:
        print(
            f"[ERROR] Failed to send question: {e}"
        )

        return False


async def push_next_question(
    client,
    after_number,
):
    """
    Push the question right after `after_number`.
    Returns False when there are no more questions.
    """

    if not await ensure_questions_cache():
        return False

    for question in QUIZ_QUESTIONS:
        number = question.get("question_number")

        if number is not None and number > after_number:
            print(
                f"[AUTO] Advancing to question "
                f"{number}..."
            )

            return await send_question_dict(
                client,
                question,
            )

    # All questions answered — the device stays on its
    # "answered all, waiting" screen until the quiz time
    # expires (or the teacher finishes the quiz), then the
    # gateway sends QUIZ_END with the final result screen.
    print(
        "[AUTO] No more questions for this student."
    )

    return False


# ============================================================
# BACKGROUND LOOP - HEARTBEAT
# Gateway -> FastAPI -> Teacher dashboard
# ============================================================

async def heartbeat_loop():
    """
    Report gateway status to FastAPI every HEARTBEAT_INTERVAL
    seconds — including while waiting for the device to
    appear — so the dashboard can tell "gateway running,
    waiting for device" from "gateway not running".
    """
    url = f"{FASTAPI_URL}/api/gateway/heartbeat"

    while True:
        client = current_client

        payload = {
            "connected": bool(
                client is not None and client.is_connected
            ),
            "device_address": DEVICE_ADDRESS,
            "quiz_id": ACTIVE_QUIZ_ID,
            "registered_count": len(registered_devices),
            "last_pushed_question": LAST_PUSHED_QUESTION,
        }

        # to_thread: keep the event loop free for BLE events.
        await asyncio.to_thread(
            http_post_json_quiet,
            url,
            payload,
        )

        await asyncio.sleep(HEARTBEAT_INTERVAL)


# ============================================================
# BACKGROUND LOOP - QUIZ WATCH
# FastAPI -> Gateway -> ESP32
#
# Watches quiz state on the backend:
# - new quiz / start / time limit change -> send QUIZ_INFO
# - quiz starts                          -> push question 1
# - quiz time expires                    -> finish + QUIZ_END
# - teacher finishes on the dashboard    -> QUIZ_END
#
# Self-paced advancing to the next question after each
# answer is handled in process_answer -> push_next_question.
#
# NOTE: questions are NEVER re-pushed based on the backend's
# current_question_number — that caused the device to jump
# back to an old question while students worked ahead.
# ============================================================

def parse_iso_utc(value):
    """
    '2026-10-07T19:35:18.485264' -> POSIX seconds (UTC).
    """
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.timestamp()


async def send_quiz_info(client):
    """
    Tell the device which quiz is active:
    title, status, time limit and total questions.
    """
    global QUIZ_SENT_INFO_KEY

    await ensure_questions_cache()

    packet = {
        "type": "QUIZ_INFO",
        "quiz_id": ACTIVE_QUIZ_ID,
        "title": ACTIVE_QUIZ_TITLE,
        "status": ACTIVE_QUIZ_STATUS,
        "time_limit": ACTIVE_QUIZ_TIME_LIMIT,
        "total": len(QUIZ_QUESTIONS),
        "expected": ACTIVE_QUIZ_EXPECTED,
        "prefix": ACTIVE_QUIZ_PREFIX,
        "id_length": ACTIVE_QUIZ_ID_LENGTH,
    }

    try:
        ack_char = get_characteristic(
            client,
            ACK_CHAR_UUID,
        )

        await client.write_gatt_char(
            ack_char,
            json.dumps(
                packet,
                separators=(",", ":"),
            ).encode("utf-8"),
            response=True,
        )

        QUIZ_SENT_INFO_KEY = (
            ACTIVE_QUIZ_ID,
            ACTIVE_QUIZ_STATUS,
            ACTIVE_QUIZ_TIME_LIMIT,
            len(QUIZ_QUESTIONS),
        )

        print(
            f"[INFO] QUIZ_INFO sent: {packet}"
        )

        return True

    except Exception as e:
        print(
            f"[ERROR] QUIZ_INFO failed: {e}"
        )

        return False


async def send_quiz_end(client):
    """
    Tell the device the quiz is over so it can show the
    final result (correct count / total and score /10).
    """
    global QUIZ_END_SENT_QUIZ

    packet = {
        "type": "QUIZ_END",
        "quiz_id": ACTIVE_QUIZ_ID,
    }

    try:
        ack_char = get_characteristic(
            client,
            ACK_CHAR_UUID,
        )

        await client.write_gatt_char(
            ack_char,
            json.dumps(
                packet,
                separators=(",", ":"),
            ).encode("utf-8"),
            response=True,
        )

        QUIZ_END_SENT_QUIZ = ACTIVE_QUIZ_ID

        print("[INFO] QUIZ_END sent to device.")

        return True

    except Exception as e:
        print(
            f"[ERROR] QUIZ_END failed: {e}"
        )

        return False


async def quiz_watch_loop(client):
    global ACTIVE_QUIZ_ID
    global ACTIVE_SESSION_ID
    global ACTIVE_QUIZ_TITLE
    global ACTIVE_QUIZ_STATUS
    global ACTIVE_QUIZ_TIME_LIMIT
    global ACTIVE_QUIZ_EXPECTED
    global ACTIVE_QUIZ_PREFIX
    global ACTIVE_QUIZ_ID_LENGTH
    global QUIZ_SENT_INFO_KEY
    global QUIZ_END_SENT_QUIZ
    global LAST_PUSHED_QUESTION
    global QUIZ_QUESTIONS_QUIZ_ID

    quizzes_url = f"{FASTAPI_URL}/api/quizzes"

    while True:
        try:
            if not client.is_connected:
                await asyncio.sleep(QUIZ_POLL_INTERVAL)
                continue

            success, quizzes = await asyncio.to_thread(
                http_get_json_quiet,
                quizzes_url,
            )

            if not success or not isinstance(quizzes, list):
                await asyncio.sleep(QUIZ_POLL_INTERVAL)
                continue

            running = [
                quiz
                for quiz in quizzes
                if quiz.get("status") == "running"
            ]

            lobbies = [
                quiz
                for quiz in quizzes
                if quiz.get("status") == "lobby"
            ]

            drafts = [
                quiz
                for quiz in quizzes
                if quiz.get("status") == "draft"
            ]

            # Priority: running > lobby > newest draft.
            if running:
                quiz = running[0]
            elif lobbies:
                quiz = lobbies[0]
            elif drafts:
                drafts.sort(
                    key=lambda q: q.get("id") or 0,
                    reverse=True,
                )
                quiz = drafts[0]
            else:
                quiz = None

            if quiz is None:
                if ACTIVE_QUIZ_ID is not None:
                    ACTIVE_QUIZ_ID = None
                    ACTIVE_SESSION_ID = None
                    ACTIVE_QUIZ_TITLE = ""
                    ACTIVE_QUIZ_STATUS = ""
                    QUIZ_SENT_INFO_KEY = None

                await asyncio.sleep(QUIZ_POLL_INTERVAL)
                continue

            quiz_id = quiz.get("id")
            status = quiz.get("status") or ""
            title = quiz.get("title") or ""

            time_limit = (
                quiz.get("time_limit_sec")
                or QUIZ_DEFAULT_TIME_LIMIT_SEC
            )

            expected = quiz.get("expected_students") or 0
            prefix = quiz.get("id_prefix") or ""
            id_length = quiz.get("id_length") or 0

            # --------------------------------------------
            # Active quiz changed
            # --------------------------------------------

            if quiz_id != ACTIVE_QUIZ_ID:
                ACTIVE_QUIZ_ID = quiz_id
                ACTIVE_SESSION_ID = f"QUIZ-{quiz_id}"
                ACTIVE_QUIZ_TITLE = title
                ACTIVE_QUIZ_STATUS = status
                ACTIVE_QUIZ_TIME_LIMIT = time_limit
                ACTIVE_QUIZ_EXPECTED = expected
                ACTIVE_QUIZ_PREFIX = prefix
                ACTIVE_QUIZ_ID_LENGTH = id_length

                # Force a question-cache reload.
                QUIZ_QUESTIONS_QUIZ_ID = None
                LAST_PUSHED_QUESTION = None
                QUIZ_END_SENT_QUIZ = None

                print(
                    f"[WATCH] Following quiz {quiz_id} "
                    f"'{title}' ({status})."
                )

            else:
                ACTIVE_QUIZ_TITLE = title
                ACTIVE_QUIZ_STATUS = status
                ACTIVE_QUIZ_TIME_LIMIT = time_limit
                ACTIVE_QUIZ_EXPECTED = expected
                ACTIVE_QUIZ_PREFIX = prefix
                ACTIVE_QUIZ_ID_LENGTH = id_length

            # --------------------------------------------
            # QUIZ_INFO whenever something changed
            # (status, time limit, question count)
            # --------------------------------------------

            await ensure_questions_cache()

            info_key = (
                ACTIVE_QUIZ_ID,
                ACTIVE_QUIZ_STATUS,
                ACTIVE_QUIZ_TIME_LIMIT,
                len(QUIZ_QUESTIONS),
            )

            if info_key != QUIZ_SENT_INFO_KEY:
                # Force a question-cache reload so QUIZ_INFO
                # and the Q1 push see fresh data.
                QUIZ_QUESTIONS_QUIZ_ID = None

                await ensure_questions_cache()

                await send_quiz_info(client)

            # --------------------------------------------
            # Running quiz lifecycle
            # --------------------------------------------

            if ACTIVE_QUIZ_STATUS == "running":

                started = parse_iso_utc(
                    quiz.get("started_at")
                )

                deadline = (
                    started + ACTIVE_QUIZ_TIME_LIMIT
                    if started
                    else None
                )

                if deadline and time.time() >= deadline:
                    print(
                        "[WATCH] Quiz time expired — "
                        "finishing quiz."
                    )

                    await asyncio.to_thread(
                        http_post_json_quiet,
                        f"{FASTAPI_URL}/api/quizzes/"
                        f"{ACTIVE_QUIZ_ID}/finish",
                        {},
                    )

                    if QUIZ_END_SENT_QUIZ != ACTIVE_QUIZ_ID:
                        await send_quiz_end(client)

                    await asyncio.sleep(QUIZ_POLL_INTERVAL)
                    continue

                # Push Q1 right after the quiz starts.
                if (
                    LAST_PUSHED_QUESTION is None
                    and QUIZ_END_SENT_QUIZ != ACTIVE_QUIZ_ID
                ):
                    await ensure_questions_cache()

                    if QUIZ_QUESTIONS:
                        await send_question_dict(
                            client,
                            QUIZ_QUESTIONS[0],
                        )

            elif ACTIVE_QUIZ_STATUS == "finished":

                if QUIZ_END_SENT_QUIZ != ACTIVE_QUIZ_ID:
                    print(
                        "[WATCH] Quiz finished by teacher — "
                        "notifying device."
                    )

                    await send_quiz_end(client)

        except Exception as e:
            print(
                f"[ERROR] Quiz watch loop: {e}"
            )

        await asyncio.sleep(QUIZ_POLL_INTERVAL)


# ============================================================
# SHOW REGISTERED DEVICES
# ============================================================

def show_registered_devices():
    print()
    print("======================================")
    print("[REGISTERED DEVICES]")
    print("======================================")

    if not registered_devices:

        print(
            "No devices registered."
        )

        print(
            "======================================"
        )

        return

    for student_id, info in (
        registered_devices.items()
    ):

        print(
            f"Student ID : {student_id}"
        )

        print(
            f"Device MAC : "
            f"{info['device_mac']}"
        )

        print(
            f"Device Name: "
            f"{info['device_name']}"
        )

        print(
            f"Quiz ID    : "
            f"{info['quiz_id']}"
        )

        print(
            "--------------------------------------"
        )


# ============================================================
# SHOW ACTIVE QUIZ
# ============================================================

def show_active_quiz():
    print()
    print("======================================")
    print("[ACTIVE QUIZ]")
    print("======================================")

    if ACTIVE_QUIZ_ID is None:

        print(
            "No active quiz."
        )

    else:

        print(
            f"Quiz ID : {ACTIVE_QUIZ_ID}"
        )

        print(
            f"Session : {ACTIVE_SESSION_ID}"
        )

    print("======================================")


# ============================================================
# SHOW BLE STATUS
# ============================================================

def show_ble_status(
    client,
):
    print()
    print("======================================")
    print("[BLE STATUS]")
    print("======================================")

    if client.is_connected:

        print(
            "[STATUS] BLE connected."
        )

    else:

        print(
            "[STATUS] BLE disconnected."
        )

    print(
        f"Device : {DEVICE_ADDRESS}"
    )

    print("======================================")


# ============================================================
# MENU
# ============================================================

def show_menu():
    print()
    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")

    print(
        "1. Refresh active quiz"
    )

    print(
        "2. Show active quiz"
    )

    print(
        "3. Send current question"
    )

    print(
        "4. Send CONNECTED ACK"
    )

    print(
        "5. Show registered devices"
    )

    print(
        "6. Show BLE connection status"
    )

    print(
        "7. Exit"
    )

    print(
        "======================================"
    )


# ============================================================
# MENU LOOP
# ============================================================

async def menu_loop(
    client,
):
    while True:

        show_menu()

        choice = await asyncio.to_thread(
            input,
            "Select option: ",
        )

        choice = choice.strip()

        # ----------------------------------------------------
        # REFRESH ACTIVE QUIZ
        # ----------------------------------------------------

        if choice == "1":

            refresh_active_quiz()

        # ----------------------------------------------------
        # SHOW ACTIVE QUIZ
        # ----------------------------------------------------

        elif choice == "2":

            show_active_quiz()

        # ----------------------------------------------------
        # SEND CURRENT QUESTION
        # ----------------------------------------------------

        elif choice == "3":

            await send_current_question(
                client
            )

        # ----------------------------------------------------
        # CONNECTED ACK
        # ----------------------------------------------------

        elif choice == "4":

            if ACTIVE_QUIZ_ID is None:

                refresh_active_quiz()

            packet = {
                "type": "ACK",
                "status": "CONNECTED",
                "quiz_id": ACTIVE_QUIZ_ID,
                "session_id": ACTIVE_SESSION_ID,
            }

            await send_ack(
                client,
                json.dumps(
                    packet,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
            )

        # ----------------------------------------------------
        # REGISTERED DEVICES
        # ----------------------------------------------------

        elif choice == "5":

            show_registered_devices()

        # ----------------------------------------------------
        # BLE STATUS
        # ----------------------------------------------------

        elif choice == "6":

            show_ble_status(
                client
            )

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        elif choice == "7":

            print()
            print(
                "[INFO] Exiting gateway..."
            )

            break

        else:

            print()
            print(
                "[ERROR] Invalid option."
            )

        await asyncio.sleep(
            0.2
        )


# ============================================================
# PRINT GATT SERVICES
# ============================================================

def print_gatt_services(
    client,
):
    print()
    print("======================================")
    print("[GATT SERVICES]")
    print("======================================")

    for service in client.services:

        print()
        print(
            f"Service: {service.uuid}"
        )

        for char in (
            service.characteristics
        ):

            print(
                f"  Characteristic: "
                f"{char.uuid}"
            )

            print(
                f"    Properties: "
                f"{char.properties}"
            )

    print(
        "======================================"
    )


# ============================================================
# MAIN
# ============================================================

async def run_gateway_session():
    global current_client
    global LAST_PUSHED_QUESTION

    print("======================================")
    print("       PulseNet BLE Gateway")
    print("======================================")

    print(
        f"Target device: {DEVICE_ADDRESS}"
    )

    print(
        f"FastAPI      : {FASTAPI_URL}"
    )

    print("======================================")

    try:

        async with BleakClient(
            DEVICE_ADDRESS
        ) as client:

            current_client = client

            # Re-push the current question after every
            # (re)connect so the device is never left behind.
            LAST_PUSHED_QUESTION = None

            # ------------------------------------------------
            # BLE CONNECTED
            # ------------------------------------------------

            print()
            print(
                "[OK] BLE connected."
            )

            # ------------------------------------------------
            # GATT SERVICES
            # ------------------------------------------------

            print_gatt_services(
                client
            )

            # ------------------------------------------------
            # INITIAL QUIZ DISCOVERY
            # ------------------------------------------------

            print()
            print(
                "[INFO] Checking active quiz..."
            )

            refresh_active_quiz()

            # ------------------------------------------------
            # REGISTRATION NOTIFICATION
            # ------------------------------------------------

            print()
            print(
                "[INFO] Subscribing to "
                "registration notifications..."
            )

            await client.start_notify(
                REGISTRATION_CHAR_UUID,
                registration_callback,
            )

            # ------------------------------------------------
            # ANSWER NOTIFICATION
            # ------------------------------------------------

            print(
                "[INFO] Subscribing to "
                "answer notifications..."
            )

            await client.start_notify(
                ANSWER_CHAR_UUID,
                answer_callback,
            )

            print(
                "[OK] Notification handlers enabled."
            )

            # ------------------------------------------------
            # INITIAL CONNECTED ACK
            # ------------------------------------------------

            packet = {
                "type": "ACK",
                "status": "CONNECTED",
                "quiz_id": ACTIVE_QUIZ_ID,
                "session_id": ACTIVE_SESSION_ID,
            }

            await send_ack(
                client,
                json.dumps(
                    packet,
                    separators=(
                        ",",
                        ":",
                    ),
                ),
            )

            # ------------------------------------------------
            # GATEWAY READY
            # ------------------------------------------------

            print()
            print("======================================")
            print("       Gateway is running")
            print("======================================")

            if ACTIVE_QUIZ_ID is None:

                print(
                    "No quiz is currently running."
                )

                print(
                    "Start a quiz from Teacher Web."
                )

            else:

                print(
                    f"Active Quiz ID: "
                    f"{ACTIVE_QUIZ_ID}"
                )

                print(
                    "Waiting for Student ID registration."
                )

            print("======================================")

            # ------------------------------------------------
            # BACKGROUND LOOP (auto question push)
            # (heartbeat runs globally from main(), so it
            # keeps reporting even between reconnects)
            # ------------------------------------------------

            push_task = asyncio.create_task(
                quiz_watch_loop(client)
            )

            # ------------------------------------------------
            # RUN: interactive menu, or headless forever
            # ------------------------------------------------

            try:
                if INTERACTIVE:
                    await menu_loop(client)
                else:
                    print(
                        "[INFO] Headless mode — "
                        "questions are pushed to the device "
                        "automatically. Ctrl+C to stop."
                    )

                    while True:
                        if not client.is_connected:
                            raise RuntimeError(
                                "BLE device disconnected"
                            )

                        await asyncio.sleep(2)

            finally:
                push_task.cancel()

            # ------------------------------------------------
            # CLEANUP
            # ------------------------------------------------

            try:

                await client.stop_notify(
                    REGISTRATION_CHAR_UUID
                )

            except Exception:
                pass

            try:

                await client.stop_notify(
                    ANSWER_CHAR_UUID
                )

            except Exception:
                pass

            current_client = None

            print()
            print(
                "[INFO] BLE notifications stopped."
            )

    except Exception as e:

        current_client = None

        print()
        print("======================================")
        print("[WARN] BLE session ended")
        print("======================================")

        print(
            f"Type   : {type(e).__name__}"
        )

        print(
            f"Reason : {e}"
        )

        print(
            "======================================"
        )

        raise


# ============================================================
# MAIN LOOP
# Connect -> run -> auto-reconnect on loss
# ============================================================

async def main():
    # Global heartbeat: reports "running" even while waiting
    # for the device to appear or reconnecting.
    heartbeat_task = asyncio.create_task(
        heartbeat_loop()
    )

    while True:
        try:
            await run_gateway_session()

            # Session ended via menu option 7 — clean stop.
            heartbeat_task.cancel()
            return

        except Exception:
            print(
                f"[INFO] Reconnecting in "
                f"{RECONNECT_DELAY}s..."
            )

            await asyncio.sleep(RECONNECT_DELAY)


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print("======================================")
        print("[INFO] Gateway stopped by user.")
        print("======================================")
