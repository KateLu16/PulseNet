"""
AI question generation from an uploaded document.

Flow:
    uploaded file (PDF / DOCX / TXT / MD)
        -> extracted plain text
        -> Gemini API (JSON mode)
        -> validated list of MCQ rows shaped like the Question model

The API key is read from backend/.env (GEMINI_API_KEY=...) or the
process environment. The Gemini call uses urllib from the standard
library so no HTTP client dependency is added.
"""

import io
import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from dotenv import load_dotenv

# backend/.env sits two levels above app/services/
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
)

DEFAULT_MODEL = "gemini-2.5-flash"

MAX_FILE_BYTES = 10 * 1024 * 1024      # 10 MB upload cap
MAX_DOC_CHARS = 20_000                 # keeps the prompt small and fast
MIN_DOC_CHARS = 200                    # below this there is nothing to quiz on
API_TIMEOUT_SEC = 120

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")

VALID_ANSWERS = ("A", "B", "C", "D")


# ============================================================
# CONFIG
# ============================================================

def get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_model() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def ai_configured() -> bool:
    return bool(get_api_key())


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text(filename: str, raw_bytes: bytes) -> str:
    """
    Extract plain text from an uploaded document.

    Raises ValueError with a teacher-readable message when the
    file type is unsupported or the content cannot be read.
    """

    lower_name = (filename or "").lower()

    if lower_name.endswith(".pdf"):
        text = _extract_pdf(raw_bytes)
    elif lower_name.endswith(".docx"):
        text = _extract_docx(raw_bytes)
    elif lower_name.endswith((".txt", ".md")):
        text = _decode_text(raw_bytes)
    else:
        raise ValueError(
            "Unsupported file type. "
            "Supported: PDF, DOCX, TXT, MD"
        )

    # Collapse runs of blank lines so the prompt stays compact.
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    return text


def _decode_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue

    return raw_bytes.decode("utf-8", errors="replace")


def _extract_pdf(raw_bytes: bytes) -> str:
    # Imported lazily so the server still boots when pypdf
    # is missing — only PDF uploads would fail.
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise ValueError(
            f"Could not read the PDF file ({exc.__class__.__name__})"
        ) from exc

    pages = []

    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")

    return "\n".join(pages)


# OOXML namespace used by Word for <w:p> paragraphs and <w:t> runs.
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _extract_docx(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
            xml_data = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError(
            "Could not read the DOCX file (not a valid Word document)"
        ) from exc

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise ValueError(
            "Could not parse the DOCX file (malformed document.xml)"
        ) from exc

    paragraphs = []

    for paragraph in root.iter(f"{_WORD_NS}p"):
        runs = [
            node.text or ""
            for node in paragraph.iter(f"{_WORD_NS}t")
        ]
        paragraphs.append("".join(runs))

    return "\n".join(paragraphs)


# ============================================================
# PROMPT
# ============================================================

_LANGUAGE_INSTRUCTIONS = {
    "auto": "Write the questions in the same language as the document.",
    "vietnamese": "Write the questions in Vietnamese.",
    "english": "Write the questions in English.",
}


def build_prompt(
    document_text: str,
    num_questions: int,
    language: str,
) -> str:

    language_rule = _LANGUAGE_INSTRUCTIONS.get(
        language,
        _LANGUAGE_INSTRUCTIONS["auto"],
    )

    return f"""You are an exam writer for a university classroom quiz system.

Create exactly {num_questions} multiple-choice questions based ONLY on the document text at the end of this message.

Rules:
- Each question has exactly 4 options labeled A, B, C, D and exactly one correct answer.
- Test real understanding: definitions, how things work, differences, causes, applications.
- Wrong options must be plausible, not absurd.
- Do not copy whole sentences from the document into the question text.
- Spread correct answers across A, B, C, D instead of repeating one letter.
- {language_rule}

Return ONLY a JSON array (no markdown, no commentary). Each element must be:
{{"question_text": "...", "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "correct_answer": "A"}}

DOCUMENT:
\"\"\"
{document_text}
\"\"\""""


# ============================================================
# GEMINI API CALL
# ============================================================

class AIGenerationError(Exception):
    """Raised when the Gemini call fails or returns unusable output."""


def call_gemini_api(payload: dict) -> dict:
    """
    POST one generateContent request. Separated from the parsing
    logic so tests can monkeypatch it.
    """

    url = (
        f"{GEMINI_BASE_URL}/{get_model()}:generateContent"
    )

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": get_api_key(),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=API_TIMEOUT_SEC,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as exc:
        body = ""

        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass

        if exc.code in (400, 401, 403):
            raise AIGenerationError(
                "Gemini rejected the request — check GEMINI_API_KEY. "
                f"(HTTP {exc.code})"
            ) from exc

        if exc.code == 429:
            raise AIGenerationError(
                "Gemini quota exceeded (HTTP 429) — try again later "
                "or lower the number of questions."
            ) from exc

        if exc.code == 404:
            raise AIGenerationError(
                f"Gemini model '{get_model()}' not found — set "
                "GEMINI_MODEL in backend/.env to an available model."
            ) from exc

        raise AIGenerationError(
            f"Gemini API error (HTTP {exc.code}): {body[:200]}"
        ) from exc

    except urllib.error.URLError as exc:
        raise AIGenerationError(
            f"Cannot reach the Gemini API ({exc.reason})"
        ) from exc

    except (KeyError, json.JSONDecodeError) as exc:
        raise AIGenerationError(
            "Gemini returned an unreadable response"
        ) from exc


def generate_questions_from_text(
    document_text: str,
    num_questions: int,
    language: str = "auto",
) -> list[dict]:
    """
    Ask Gemini for MCQs and return a validated list of dicts:
    question_text, option_a..d, correct_answer.

    Raises AIGenerationError when the call or parsing fails.
    Invalid rows are skipped, not fatal.
    """

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": build_prompt(
                            document_text,
                            num_questions,
                            language,
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.7,
        },
    }

    data = call_gemini_api(payload)

    # candidates[0].content.parts[*].text — with JSON mode the
    # text is itself a JSON array.
    try:
        candidate = data["candidates"][0]
        raw_text = "".join(
            part.get("text", "")
            for part in candidate["content"]["parts"]
        )
    except (KeyError, IndexError, TypeError):
        raise AIGenerationError(
            "Gemini returned an unexpected response structure"
        )

    if candidate.get("finishReason") == "SAFETY":
        raise AIGenerationError(
            "Gemini blocked the document content (safety filter)"
        )

    try:
        items = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AIGenerationError(
            "Gemini output was not valid JSON"
        ) from exc

    if isinstance(items, dict):
        items = items.get("questions", [])

    if not isinstance(items, list):
        raise AIGenerationError(
            "Gemini output was not a question list"
        )

    questions = []

    for item in items:
        question = _normalize_question(item)

        if question is not None:
            questions.append(question)

    return questions[:num_questions]


def _normalize_question(item) -> dict | None:
    """Validate one AI answer row; return None when unusable."""

    if not isinstance(item, dict):
        return None

    def clean(key: str) -> str:
        value = item.get(key, "")
        return str(value).strip() if value is not None else ""

    question_text = clean("question_text")
    option_a = clean("option_a")
    option_b = clean("option_b")
    option_c = clean("option_c")
    option_d = clean("option_d")
    correct_answer = clean("correct_answer").upper()[:1]

    if not question_text:
        return None

    if not all((option_a, option_b, option_c, option_d)):
        return None

    if correct_answer not in VALID_ANSWERS:
        return None

    return {
        "question_text": question_text,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_d": option_d,
        "correct_answer": correct_answer,
    }
