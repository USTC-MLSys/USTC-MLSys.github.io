from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .common import build_summary, infer_tags, infer_type, slugify


@dataclass
class SubmissionMeta:
    status: str
    venue: str = ""
    month: str = ""
    year: int | None = None
    research_area: str = ""
    project_slug: str = ""
    code_url: str = ""
    award: str = ""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SubmissionMeta":
        return cls(
            status=str(payload.get("status", "")).strip(),
            venue=str(payload.get("venue", "")).strip(),
            month=str(payload.get("month", "")).strip(),
            year=payload.get("year"),
            research_area=str(payload.get("research_area", "")).strip(),
            project_slug=str(payload.get("project_slug", "")).strip(),
            code_url=str(payload.get("code_url", "")).strip(),
            award=str(payload.get("award", "")).strip(),
            title=str(payload.get("title", "")).strip(),
            authors=[str(author).strip() for author in payload.get("authors", []) if str(author).strip()],
            abstract=str(payload.get("abstract", "")).strip(),
            tags=[str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()],
        )


@dataclass
class ParsedPaper:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    year: int | None = None


def merge_submission_inputs(meta: SubmissionMeta, parsed: ParsedPaper) -> ParsedPaper:
    return ParsedPaper(
        title=parsed.title or meta.title,
        authors=parsed.authors or meta.authors,
        abstract=parsed.abstract or meta.abstract,
        year=parsed.year or meta.year,
    )


def build_publication_record(meta: SubmissionMeta, parsed: ParsedPaper, pdf_target_path: Path) -> dict[str, Any]:
    merged = merge_submission_inputs(meta, parsed)
    title = merged.title
    authors = merged.authors
    abstract = merged.abstract
    year = merged.year

    slug_parts = [slugify(title)]
    if meta.venue:
        slug_parts.append(slugify(meta.venue.split()[0]))
    if year:
        slug_parts.append(str(year))
    slug = "-".join(part for part in slug_parts if part)

    tags = meta.tags or infer_tags(title, abstract, meta.research_area)
    return {
        "slug": slug,
        "title": title,
        "summary": build_summary(abstract),
        "abstract": abstract,
        "authors": authors,
        "venue": meta.venue,
        "month": meta.month,
        "year": year,
        "type": infer_type(meta.venue),
        "research_area": meta.research_area,
        "tags": tags,
        "award": meta.award,
        "project_slug": meta.project_slug,
        "pdf_url": f"/assets/papers/{pdf_target_path.name}",
        "code_url": meta.code_url,
        "content": [
            {
                "type": "paragraph",
                "title": "Abstract",
                "text": abstract,
            }
        ],
        "_workflow": {
            "status": meta.status,
            "source": "publication_agent",
        },
    }
