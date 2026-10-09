"""
Self-contained tests for the AI quiz generator.

Run from the backend directory:
    .venv/Scripts/python test_ai_quiz_gen.py        (Windows)
    .venv/bin/python test_ai_quiz_gen.py            (Pi)

Uses a temporary database and a monkeypatched Gemini call, so
no API key and no network access are required.
"""

import io
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

# Use a throwaway database before any app import touches one.
_TEMP_DIR = tempfile.mkdtemp(prefix="pulsenet_ai_test_")
os.chdir(_TEMP_DIR)

os.environ["GEMINI_API_KEY"] = "test-key-for-unit-tests"

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import HTTPException  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402

from app.models.question import Question  # noqa: E402
from app.models.quiz import Quiz  # noqa: E402
from app.services import ai_quiz_gen  # noqa: E402
from app.services.ai_quiz_gen import (  # noqa: E402
    extract_text,
    generate_questions_from_text,
)

from starlette.datastructures import UploadFile  # noqa: E402

from app.api.ai_generate import (  # noqa: E402
    ai_status,
    generate_questions_ai,
)


PASSED = 0
FAILED = 0


def check(name, condition, info=""):
    global PASSED, FAILED

    if condition:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED += 1
        print(f"  [FAIL] {name} {info}")


def expect_http(name, func, status_code):
    try:
        func()
    except HTTPException as exc:
        check(name, exc.status_code == status_code,
              f"(got {exc.status_code}: {exc.detail})")
        return
    check(name, False, "(no HTTPException raised)")


# ============================================================
# Test data helpers
# ============================================================

def make_upload(filename, content):
    data = content if isinstance(content, bytes) else content.encode("utf-8")
    return UploadFile(file=io.BytesIO(data), filename=filename)


def make_docx(paragraphs):
    document_xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>'
    )

    for paragraph in paragraphs:
        document_xml += (
            "<w:p><w:r><w:t>"
            + paragraph.replace("&", "&amp;").replace("<", "&lt;")
            + "</w:t></w:r></w:p>"
        )

    document_xml += "</w:body></w:document>"

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    return buffer.getvalue()


def make_pdf(lines):
    """Assemble a minimal one-page PDF with correct xref offsets."""

    content_parts = ["BT /F1 12 Tf 50 750 Td 14 TL"]

    for index, line in enumerate(lines):
        escaped = (
            line.replace("\\", r"\\")
            .replace("(", r"\(")
            .replace(")", r"\)")
        )

        if index == 0:
            content_parts.append(f"({escaped}) Tj")
        else:
            content_parts.append(f"T* ({escaped}) Tj")

    content_parts.append("ET")
    stream = " ".join(content_parts).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode()
        + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")

    offsets = []

    for number, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")

    xref_pos = out.tell()

    out.write(f"xref\n0 {len(objects) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")

    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())

    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF".encode()
    )

    return out.getvalue()


AI_ROWS = [
    {
        "question_text": "What does BLE stand for?",
        "option_a": "Bluetooth Low Energy",
        "option_b": "Basic Link Encryption",
        "option_c": "Broadband Loop Exchange",
        "option_d": "Binary Logic Engine",
        "correct_answer": "A",
    },
    {
        "question_text": "Which layer does IP operate at?",
        "option_a": "Physical",
        "option_b": "Network",
        "option_c": "Application",
        "option_d": "Session",
        "correct_answer": "B",
    },
    # Deliberately broken rows the normalizer must skip:
    {"question_text": "No options here", "correct_answer": "A"},
    {"question_text": "Bad letter", "option_a": "1", "option_b": "2",
     "option_c": "3", "option_d": "4", "correct_answer": "E"},
    "not even a dict",
]


def fake_gemini_ok(payload):
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(AI_ROWS)}]
                },
                "finishReason": "STOP",
            }
        ]
    }


DOC_TEXT = (
    "Bluetooth Low Energy (BLE) is a wireless personal area network "
    "technology designed for low power consumption. The PulseNet "
    "gateway on the Raspberry Pi forwards quiz answers from ESP32 "
    "student devices to the FastAPI backend over HTTP. " * 4
)


# ============================================================
# RUN
# ============================================================

Base.metadata.create_all(engine)

print("\n--- Text extraction ---")

check(
    "TXT extraction",
    "wireless" in extract_text("notes.txt", DOC_TEXT.encode("utf-8")),
)

check(
    "MD extraction",
    "wireless" in extract_text("notes.md", DOC_TEXT.encode("utf-8")),
)

docx_bytes = make_docx(["First paragraph about BLE.", "Second & <special> paragraph."])
docx_text = extract_text("lecture.docx", docx_bytes)
check("DOCX paragraph 1", "First paragraph about BLE." in docx_text)
check("DOCX paragraph 2 escaped", "Second & <special> paragraph." in docx_text)

try:
    pdf_bytes = make_pdf(["PDF line one about BLE.", "PDF line two."])
    pdf_text = extract_text("slides.pdf", pdf_bytes)
    check("PDF extraction", "PDF line one about BLE." in pdf_text)
    check("PDF line break", "PDF line two." in pdf_text)
except ImportError:
    print("  [SKIP] pypdf not installed — PDF tests skipped")

try:
    extract_text("virus.exe", b"whatever")
    check("Unsupported extension raises", False)
except ValueError:
    check("Unsupported extension raises", True)

try:
    extract_text("broken.docx", b"not a zip")
    check("Broken DOCX raises", False)
except ValueError:
    check("Broken DOCX raises", True)

print("\n--- AI output normalization ---")

ai_quiz_gen.call_gemini_api = fake_gemini_ok

rows = generate_questions_from_text(DOC_TEXT, 5)
check("Valid rows kept", len(rows) == 2, f"(got {len(rows)})")
check("First row normalized", rows[0]["correct_answer"] == "A")
check("Broken rows skipped", all(r["correct_answer"] in "ABCD" for r in rows))

ai_quiz_gen.call_gemini_api = lambda p: {"candidates": []}
try:
    generate_questions_from_text(DOC_TEXT, 5)
    check("Empty candidates raise", False)
except ai_quiz_gen.AIGenerationError:
    check("Empty candidates raise", True)

ai_quiz_gen.call_gemini_api = lambda p: {
    "candidates": [
        {"content": {"parts": [{"text": "garbage not json"}]},
         "finishReason": "STOP"}
    ]
}
try:
    generate_questions_from_text(DOC_TEXT, 5)
    check("Invalid JSON raises", False)
except ai_quiz_gen.AIGenerationError:
    check("Invalid JSON raises", True)

# Restore for endpoint tests.
ai_quiz_gen.call_gemini_api = fake_gemini_ok

print("\n--- Prompt build ---")

prompt = ai_quiz_gen.build_prompt(DOC_TEXT, 7, "vietnamese")
check("Prompt asks for 7", "exactly 7" in prompt)
check("Prompt Vietnamese rule", "in Vietnamese" in prompt)
check("Prompt carries document", "Bluetooth Low Energy" in prompt)

print("\n--- API endpoints ---")

db = SessionLocal()

status = ai_status()
check("AI status configured", status["configured"] is True)
check("AI status has model", bool(status["model"]))

quiz = Quiz(title="AI test quiz", status="draft")
db.add(quiz)
db.commit()

upload = make_upload("doc.txt", DOC_TEXT)
result = generate_questions_ai(
    quiz_id=quiz.id,
    file=upload,
    num_questions=5,
    language="auto",
    db=db,
)

check("Generate success flag", result["success"] is True)
check("Generated count", result["generated"] == 2, f"(got {result['generated']})")
check("Filename echoed", result["filename"] == "doc.txt")

stored = (
    db.query(Question)
    .filter(Question.quiz_id == quiz.id)
    .order_by(Question.question_number)
    .all()
)
check("Rows stored in DB", len(stored) == 2)
check("Numbering starts at 1", stored[0].question_number == 1)
check("Correct answer stored", stored[1].correct_answer == "B")

# Second run continues the numbering (DB must now hold 1..4).
upload2 = make_upload("doc.txt", DOC_TEXT)
generate_questions_ai(
    quiz_id=quiz.id,
    file=upload2,
    num_questions=5,
    language="auto",
    db=db,
)

stored_all = (
    db.query(Question)
    .filter(Question.quiz_id == quiz.id)
    .order_by(Question.question_number)
    .all()
)
check("Numbering continues 1..4",
      [q.question_number for q in stored_all] == [1, 2, 3, 4],
      f"(got {[q.question_number for q in stored_all]})")

# Non-draft quizzes must be rejected.
quiz.status = "finished"
db.commit()

expect_http(
    "Finished quiz rejected",
    lambda: generate_questions_ai(
        quiz_id=quiz.id,
        file=make_upload("doc.txt", DOC_TEXT),
        num_questions=5,
        language="auto",
        db=db,
    ),
    400,
)

fresh = Quiz(title="Other quiz", status="draft")
db.add(fresh)
db.commit()

expect_http(
    "Unknown quiz -> 404",
    lambda: generate_questions_ai(
        quiz_id=99999,
        file=make_upload("doc.txt", DOC_TEXT),
        num_questions=5,
        language="auto",
        db=db,
    ),
    404,
)

expect_http(
    "Unsupported extension -> 400",
    lambda: generate_questions_ai(
        quiz_id=fresh.id,
        file=make_upload("photo.jpg", DOC_TEXT),
        num_questions=5,
        language="auto",
        db=db,
    ),
    400,
)

expect_http(
    "Empty file -> 400",
    lambda: generate_questions_ai(
        quiz_id=fresh.id,
        file=make_upload("empty.txt", b""),
        num_questions=5,
        language="auto",
        db=db,
    ),
    400,
)

short_doc = "Too short."
expect_http(
    "Too-short document -> 400",
    lambda: generate_questions_ai(
        quiz_id=fresh.id,
        file=make_upload("short.txt", short_doc),
        num_questions=5,
        language="auto",
        db=db,
    ),
    400,
)

expect_http(
    "Bad language -> 400",
    lambda: generate_questions_ai(
        quiz_id=fresh.id,
        file=make_upload("doc.txt", DOC_TEXT),
        num_questions=5,
        language="klingon",
        db=db,
    ),
    400,
)

# Missing API key -> 503, checked before anything else.
real_key = os.environ.pop("GEMINI_API_KEY")
expect_http(
    "No API key -> 503",
    lambda: generate_questions_ai(
        quiz_id=fresh.id,
        file=make_upload("doc.txt", DOC_TEXT),
        num_questions=5,
        language="auto",
        db=db,
    ),
    503,
)
check(
    "Status reports unconfigured",
    ai_status()["configured"] is False,
)
os.environ["GEMINI_API_KEY"] = real_key

print(f"\n===== {PASSED} passed, {FAILED} failed =====")
sys.exit(1 if FAILED else 0)
