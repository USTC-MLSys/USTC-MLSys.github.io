from __future__ import annotations

import re
from pathlib import Path

from PyPDF2 import PdfReader

from .llm_parser import enrich_with_llm, llm_is_enabled
from .schema import ParsedPaper


SECTION_BREAK_RE = re.compile(
    r"^\s*(?:\d+\.?\s+)?(?:introduction|keywords|index terms|contents?)\s*$",
    re.IGNORECASE,
)
AUTHOR_MARK_RE = re.compile(r"[†§¶‡∗*]+")


def _normalize_line(line: str) -> str:
    return " ".join(line.replace("\x00", " ").split()).strip()


def _extract_text(reader: PdfReader, max_pages: int = 3) -> str:
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(chunks)


def extract_pdf_text(pdf_path: Path, max_pages: int = 3) -> str:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    return _extract_text(reader, max_pages=max_pages)


def _extract_title(lines: list[str], metadata_title: str) -> str:
    if metadata_title and len(metadata_title.split()) >= 4:
        return metadata_title.strip()

    if len(lines) >= 2:
        first, second = lines[0], lines[1]
        if len(first) >= 20 and len(second) >= 8 and len(second.split()) <= 8:
            second_lower = second.lower()
            if "abstract" not in second_lower and "university" not in second_lower:
                return f"{first} {second}".strip()

    candidates: list[str] = []
    for line in lines[:20]:
        lower = line.lower()
        if len(line) < 20:
            continue
        if lower in {"abstract", "introduction"}:
            continue
        if "@" in line:
            continue
        if re.search(r"\b(university|department|school|institute|laboratory|college)\b", lower):
            continue
        candidates.append(line)
    return max(candidates, key=len) if candidates else ""


def _extract_abstract(text: str) -> str:
    match = re.search(r"\babstract\b[:\s]*", text, re.IGNORECASE)
    if not match:
        return ""
    rest = text[match.end() :]
    lines = [_normalize_line(line) for line in rest.splitlines()]
    collected: list[str] = []
    for line in lines:
        if not line:
            if collected:
                collected.append("")
            continue
        if SECTION_BREAK_RE.match(line):
            break
        collected.append(line)
    abstract = " ".join(part for part in collected if part)
    abstract = re.sub(r"\s+", " ", abstract).strip()
    # Fix common PDF line-break hyphenation artifacts like "be- come".
    abstract = re.sub(r"(?<=\w)-\s+(?=\w)", "", abstract)
    return abstract


def _extract_authors(lines: list[str], title: str) -> list[str]:
    if not title:
        return []

    title_parts = title.split()
    title_line_count = 2 if len(title_parts) > 8 else 1

    candidate_lines: list[str] = []
    for line in lines[title_line_count : title_line_count + 6]:
        lower = line.lower()
        if lower == "abstract":
            break
        if re.search(r"\b(university|department|school|institute|laboratory|college|arxiv|independent researcher)\b", lower):
            break
        candidate_lines.append(line)

    if not candidate_lines:
        return []

    candidate = " ".join(candidate_lines)
    candidate = AUTHOR_MARK_RE.sub(",", candidate)
    candidate = re.sub(r"\b(and)\b", ",", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r",\s*,+", ",", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" ,;")

    parts = [part.strip(" ,;0123456789") for part in candidate.split(",") if part.strip(" ,;0123456789")]
    authors: list[str] = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip()
        if len(cleaned.split()) < 2 or len(cleaned.split()) > 4:
            continue
        if re.search(r"\b(university|department|school|institute|laboratory|college|center)\b", cleaned.lower()):
            continue
        if cleaned not in authors:
            authors.append(cleaned)
    return authors


def _extract_year(text: str) -> int | None:
    years = re.findall(r"\b(20\d{2})\b", text[:4000])
    if not years:
        return None
    plausible = [int(year) for year in years if 2015 <= int(year) <= 2100]
    return max(plausible) if plausible else None


def extract_pdf_metadata(pdf_path: Path) -> ParsedPaper:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    metadata_title = ""
    if reader.metadata:
        metadata_title = str(reader.metadata.get("/Title", "") or "").strip()

    text = _extract_text(reader)
    lines = [_normalize_line(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    title = _extract_title(lines, metadata_title)
    authors = _extract_authors(lines, title)
    abstract = _extract_abstract(text)
    year = _extract_year(text)

    heuristic = ParsedPaper(
        title=title,
        authors=authors,
        abstract=abstract,
        year=year,
    )
    if llm_is_enabled():
        return enrich_with_llm(text, heuristic)
    return heuristic
