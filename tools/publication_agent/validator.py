from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = ("slug", "title", "abstract", "authors", "venue", "year", "research_area", "pdf_url")


def validate_publication_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value in (None, "", [], {}):
            errors.append(f"Missing required field: {field}")

    if record.get("authors") and not isinstance(record["authors"], list):
        errors.append("authors must be a list")
    if record.get("tags") and not isinstance(record["tags"], list):
        errors.append("tags must be a list")
    if record.get("year") and not isinstance(record["year"], int):
        errors.append("year must be an integer")

    return errors


def build_review_warnings(record: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not record.get("month"):
        warnings.append("month is empty; card meta will only show venue/year")
    if not record.get("code_url"):
        warnings.append("code_url is empty; no Code button will be rendered")
    if len(record.get("tags", [])) < 2:
        warnings.append("fewer than 2 tags were inferred; review suggested tags manually")
    if len(record.get("authors", [])) <= 1:
        warnings.append("authors extraction looks suspicious; please verify author list")
    return warnings
