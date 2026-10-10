"""Small, deliberately conservative parser for text-based student-list PDFs."""

from io import BytesIO
from typing import Any

import pdfplumber
from pydantic import ValidationError

from app.schemas import RecipientInput

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

_NAME_HEADERS = {
    "name",
    "full name",
    "student name",
    "student",
}
_EMAIL_HEADERS = {
    "email",
    "email address",
    "student email",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _header_indexes(row: list[Any]) -> tuple[int | None, int | None]:
    normalized = [_clean(cell).lower() for cell in row]
    name_index = next(
        (index for index, value in enumerate(normalized) if value in _NAME_HEADERS),
        None,
    )
    email_index = next(
        (index for index, value in enumerate(normalized) if value in _EMAIL_HEADERS),
        None,
    )
    return name_index, email_index


def _table_candidates(table: list[list[Any]]) -> list[dict[str, str]]:
    for header_index, row in enumerate(table):
        name_index, email_index = _header_indexes(row)
        if name_index is None or email_index is None:
            continue

        candidates = []
        for data_row in table[header_index + 1 :]:
            if not data_row or all(not _clean(cell) for cell in data_row):
                continue
            candidates.append(
                {
                    "name": _clean(data_row[name_index]) if name_index < len(data_row) else "",
                    "email": _clean(data_row[email_index]) if email_index < len(data_row) else "",
                }
            )
        return candidates
    return []


def _text_candidates(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    def split_line(line: str) -> list[str]:
        if "|" in line:
            return [_clean(part) for part in line.split("|")]
        if "\t" in line:
            return [_clean(part) for part in line.split("\t")]
        if "," in line:
            return [_clean(part) for part in line.split(",")]
        return [_clean(line)]

    header_index = None
    name_index = email_index = None
    for index, line in enumerate(lines):
        parts = [part.lower() for part in split_line(line)]
        found_name, found_email = _header_indexes(parts)
        if found_name is not None and found_email is not None:
            header_index, name_index, email_index = index, found_name, found_email
            break
    if header_index is None:
        return []

    candidates = []
    for line in lines[header_index + 1 :]:
        parts = split_line(line)
        if len(parts) <= max(name_index, email_index):
            continue
        candidates.append({"name": parts[name_index], "email": parts[email_index]})
    return candidates


def _validate_candidates(candidates: list[dict[str, str]]) -> dict[str, Any]:
    rows = []
    email_rows: dict[str, list[int]] = {}

    for row_id, candidate in enumerate(candidates, start=1):
        name = candidate["name"]
        email = candidate["email"]
        errors = []
        try:
            recipient = RecipientInput(name=name, email=email)
            name = recipient.name
            email = str(recipient.email)
        except ValidationError as exc:
            for issue in exc.errors():
                field = issue["loc"][-1]
                if field == "name":
                    errors.append("Name is required and must be 100 characters or fewer.")
                elif field == "email":
                    errors.append("Enter a valid email address.")

        normalized_email = email.casefold().strip()
        if normalized_email:
            email_rows.setdefault(normalized_email, []).append(row_id)
        rows.append(
            {
                "row_id": row_id,
                "name": name,
                "email": email,
                "errors": errors,
                "duplicate": False,
            }
        )

    duplicate_count = 0
    for row in rows:
        matching_rows = email_rows.get(row["email"].casefold().strip(), [])
        if len(matching_rows) > 1:
            row["duplicate"] = True
            row["errors"].append("Duplicate email address also appears in another row.")
            duplicate_count += 1

    invalid_count = sum(bool(row["errors"]) for row in rows)
    valid_count = len(rows) - invalid_count
    return {
        "rows": rows,
        "summary": {
            "total_candidates": len(rows),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "duplicate_count": duplicate_count,
            "requires_correction": invalid_count > 0,
        },
    }


def parse_student_pdf(contents: bytes) -> dict[str, Any]:
    """Extract rows from a PDF containing a Name/Email table."""

    try:
        with pdfplumber.open(BytesIO(contents)) as pdf:
            candidates = []
            extracted_text = []
            for page in pdf.pages:
                extracted_text.append(page.extract_text() or "")
                for table in page.extract_tables() or []:
                    candidates.extend(_table_candidates(table))
            if not candidates:
                candidates = _text_candidates("\n".join(extracted_text))
    except Exception as exc:
        raise ValueError("The uploaded PDF could not be read. Upload a valid, unlocked PDF.") from exc

    if not any(text.strip() for text in extracted_text):
        raise ValueError(
            "This PDF has no extractable text. Scanned or image-only PDFs are not supported; "
            "upload a text-based PDF."
        )
    if not candidates:
        raise ValueError(
            "No student table was found. Use a text-based table with Name and Email headers."
        )
    return _validate_candidates(candidates)
