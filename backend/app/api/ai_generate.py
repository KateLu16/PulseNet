"""
AI document -> quiz endpoints.

POST /api/quizzes/{quiz_id}/questions/generate-ai
    Upload a document; the AI service turns it into MCQ rows that
    are appended to the selected draft quiz, exactly like the CSV
    importer does.

GET /api/ai/status
    Lets the dashboard show whether GEMINI_API_KEY is configured.
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.question import Question
from app.models.quiz import Quiz
from app.services.ai_quiz_gen import (
    AIGenerationError,
    MAX_FILE_BYTES,
    MIN_DOC_CHARS,
    SUPPORTED_EXTENSIONS,
    ai_configured,
    extract_text,
    generate_questions_from_text,
    get_model,
)


router = APIRouter(
    tags=["AI generation"],
)

MAX_QUESTIONS = 30

ALLOWED_LANGUAGES = ("auto", "vietnamese", "english")


# ============================================================
# STATUS — is the AI feature usable on this server?
# ============================================================

@router.get("/api/ai/status")
def ai_status():
    return {
        "configured": ai_configured(),
        "model": get_model(),
    }


# ============================================================
# GENERATE QUESTIONS FROM DOCUMENT
# ============================================================

@router.post(
    "/api/quizzes/{quiz_id}/questions/generate-ai",
)
def generate_questions_ai(
    quiz_id: int,
    file: UploadFile = File(...),
    num_questions: int = Form(10),
    language: str = Form("auto"),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Quiz must exist and still be a draft — adding AI questions
    # to a lobby/running/finished quiz would corrupt its results.
    # --------------------------------------------------------

    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id)
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
            detail=(
                "Questions can only be generated while "
                "the quiz is still a draft"
            ),
        )

    # --------------------------------------------------------
    # Fail fast on a missing API key before touching the file.
    # --------------------------------------------------------

    if not ai_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "AI generation is not configured — add "
                "GEMINI_API_KEY to backend/.env on the server "
                "and restart"
            ),
        )

    # --------------------------------------------------------
    # Validate parameters
    # --------------------------------------------------------

    num_questions = max(1, min(MAX_QUESTIONS, num_questions))

    if language not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="language must be auto, vietnamese or english",
        )

    # --------------------------------------------------------
    # Validate the upload
    # --------------------------------------------------------

    filename = file.filename or ""

    if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type — "
                "supported: PDF, DOCX, TXT, MD"
            ),
        )

    raw_bytes = file.file.read()

    if len(raw_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty",
        )

    if len(raw_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="File too large — the limit is 10 MB",
        )

    # --------------------------------------------------------
    # Extract text
    # --------------------------------------------------------

    try:
        document_text = extract_text(
            filename,
            raw_bytes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    if len(document_text) < MIN_DOC_CHARS:
        raise HTTPException(
            status_code=400,
            detail=(
                "The document text is too short to build a quiz "
                f"(need at least {MIN_DOC_CHARS} characters)"
            ),
        )

    # --------------------------------------------------------
    # Call the AI
    # --------------------------------------------------------

    try:
        generated = generate_questions_from_text(
            document_text,
            num_questions,
            language,
        )
    except AIGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        )

    if not generated:
        raise HTTPException(
            status_code=502,
            detail=(
                "The AI returned no usable questions — "
                "try again or use another document"
            ),
        )

    # --------------------------------------------------------
    # Append to the quiz, continuing the question numbering
    # --------------------------------------------------------

    last_question = (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.question_number.desc())
        .first()
    )

    next_number = (
        last_question.question_number + 1
        if last_question
        else 1
    )

    rows = []

    for item in generated:
        rows.append(
            Question(
                quiz_id=quiz_id,
                question_number=next_number,
                question_text=item["question_text"],
                option_a=item["option_a"],
                option_b=item["option_b"],
                option_c=item["option_c"],
                option_d=item["option_d"],
                correct_answer=item["correct_answer"],
            )
        )

        next_number += 1

    db.add_all(rows)
    db.commit()

    return {
        "success": True,
        "quiz_id": quiz_id,
        "filename": filename,
        "generated": len(rows),
        "questions": generated,
    }
