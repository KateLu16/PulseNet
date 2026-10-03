import csv
from io import TextIOWrapper

from sqlalchemy.orm import Session

from app.models.question import Question


EXPECTED_HEADERS = [
    "Question",
    "A",
    "B",
    "C",
    "D",
    "Correct Answer",
]


def normalize_text(value: str) -> str:
    """
    Normalize text for duplicate comparison.

    Examples:
        "What is BLE?"
        " what is ble? "
        "WHAT   IS   BLE?"

    -> same normalized value
    """
    return " ".join(value.strip().lower().split())


def question_fingerprint(
    question_text: str,
    option_a: str,
    option_b: str,
    option_c: str,
    option_d: str,
    correct_answer: str,
) -> tuple:
    """
    Create a normalized fingerprint for a complete question.
    """

    return (
        normalize_text(question_text),
        normalize_text(option_a),
        normalize_text(option_b),
        normalize_text(option_c),
        normalize_text(option_d),
        correct_answer.upper(),
    )


def import_questions_from_csv(
    file,
    quiz_id: int,
    db: Session,
):
    text_file = TextIOWrapper(
        file.file,
        encoding="utf-8-sig",
    )

    reader = csv.DictReader(text_file)

    # ============================================================
    # VALIDATE HEADER
    # ============================================================

    if reader.fieldnames != EXPECTED_HEADERS:
        return {
            "success": False,
            "message": "Invalid CSV header",
            "errors": [
                {
                    "row": 1,
                    "field": "header",
                    "message": (
                        f"Expected: {EXPECTED_HEADERS}"
                    ),
                }
            ],
        }

    questions = []
    errors = []
    duplicates = []

    # Track questions appearing inside this CSV.
    seen_questions = {}

    # Track existing questions in this quiz.
    existing_questions = (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .all()
    )

    existing_by_fingerprint = {}
    existing_by_text = {}

    for existing in existing_questions:

        fingerprint = question_fingerprint(
            existing.question_text,
            existing.option_a,
            existing.option_b,
            existing.option_c,
            existing.option_d,
            existing.correct_answer,
        )

        existing_by_fingerprint[fingerprint] = existing

        normalized_text = normalize_text(
            existing.question_text
        )

        existing_by_text[normalized_text] = existing

    # ============================================================
    # VALIDATE ROWS
    # ============================================================

    for row_number, row in enumerate(reader, start=2):

        question_text = row["Question"].strip()
        option_a = row["A"].strip()
        option_b = row["B"].strip()
        option_c = row["C"].strip()
        option_d = row["D"].strip()
        correct_answer = (
            row["Correct Answer"]
            .strip()
            .upper()
        )

        # --------------------------------------------------------
        # Empty field validation
        # --------------------------------------------------------

        fields = {
            "Question": question_text,
            "A": option_a,
            "B": option_b,
            "C": option_c,
            "D": option_d,
            "Correct Answer": correct_answer,
        }

        row_has_error = False

        for field_name, value in fields.items():

            if not value:
                errors.append(
                    {
                        "row": row_number,
                        "field": field_name,
                        "message": "Field cannot be empty",
                    }
                )

                row_has_error = True

        # --------------------------------------------------------
        # Correct answer validation
        # --------------------------------------------------------

        if correct_answer not in {"A", "B", "C", "D"}:

            errors.append(
                {
                    "row": row_number,
                    "field": "Correct Answer",
                    "message": "Must be A, B, C or D",
                }
            )

            row_has_error = True

        # --------------------------------------------------------
        # Do not process duplicate/conflict if row is invalid
        # --------------------------------------------------------

        if row_has_error:
            continue

        # --------------------------------------------------------
        # Create fingerprint
        # --------------------------------------------------------

        fingerprint = question_fingerprint(
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
        )

        normalized_text = normalize_text(
            question_text
        )

        # ========================================================
        # DUPLICATE INSIDE CURRENT CSV
        # ========================================================

        if fingerprint in seen_questions:

            duplicates.append(
                {
                    "row": row_number,
                    "type": "duplicate",
                    "message": (
                        "Duplicate question in CSV. "
                        f"Same question found at row "
                        f"{seen_questions[fingerprint]}."
                    ),
                }
            )

            continue

        # ========================================================
        # CONFLICT INSIDE CURRENT CSV
        # ========================================================

        # Same question text but different options/answer.
        previous_same_text = None

        for previous_fingerprint, previous_row in seen_questions.items():

            if previous_fingerprint[0] == normalized_text:
                previous_same_text = previous_row
                break

        if previous_same_text is not None:

            errors.append(
                {
                    "row": row_number,
                    "field": "Question",
                    "message": (
                        "Question text already exists in this CSV "
                        "with different options or correct answer. "
                        f"Conflicts with row {previous_same_text}."
                    ),
                }
            )

            continue

        # ========================================================
        # DUPLICATE AGAINST DATABASE
        # ========================================================

        if fingerprint in existing_by_fingerprint:

            duplicates.append(
                {
                    "row": row_number,
                    "type": "duplicate",
                    "message": (
                        "Question already exists in this quiz."
                    ),
                }
            )

            continue

        # ========================================================
        # CONFLICT AGAINST DATABASE
        # ========================================================

        if normalized_text in existing_by_text:

            existing = existing_by_text[
                normalized_text
            ]

            errors.append(
                {
                    "row": row_number,
                    "field": "Question",
                    "message": (
                        "Question already exists in this quiz "
                        "with different options or correct answer. "
                        f"Existing question ID: {existing.id}."
                    ),
                }
            )

            continue

        # ========================================================
        # MARK AS SEEN
        # ========================================================

        seen_questions[fingerprint] = row_number

        # ========================================================
        # CREATE QUESTION OBJECT
        # ========================================================

        question = Question(
            quiz_id=quiz_id,
            question_number=len(questions) + 1,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
        )

        questions.append(question)

    # ============================================================
    # DO NOT PARTIALLY IMPORT WHEN VALIDATION ERRORS EXIST
    # ============================================================

    if errors:

        return {
            "success": False,
            "message": "CSV validation failed",
            "total_rows": (
                len(questions)
                + len(errors)
                + len(duplicates)
            ),
            "valid_rows": len(questions),
            "imported": 0,
            "duplicates": len(duplicates),
            "errors": len(errors),
            "duplicate_details": duplicates,
            "errors_details": errors,
        }

    # ============================================================
    # SAVE TO DATABASE
    # ============================================================

    if questions:

        db.add_all(questions)
        db.commit()

    # ============================================================
    # SUCCESS RESPONSE
    # ============================================================

    return {
        "success": True,
        "message": "Questions imported successfully",
        "total_rows": (
            len(questions)
            + len(duplicates)
        ),
        "imported": len(questions),
        "duplicates": len(duplicates),
        "errors": 0,
        "duplicate_details": duplicates,
        "errors_details": [],
    }
