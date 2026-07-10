from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "content"
ASSETS_DIR = ROOT / "assets"
PAPERS_DIR = ASSETS_DIR / "papers"
PUBLICATIONS_PATH = CONTENT_DIR / "publications.json"
PENDING_PUBLICATIONS_PATH = CONTENT_DIR / "publications_pending.json"

MONTH_ORDER = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def slugify(value: str) -> str:
    cleaned = value.lower().replace("/", " ").replace("&", " ")
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", cleaned)
    return "-".join(cleaned.split())


def publication_date_label(publication: dict[str, Any]) -> str:
    parts = [str(publication.get("month", "")).strip(), str(publication.get("year", "")).strip()]
    return " ".join(part for part in parts if part)


def infer_type(venue: str) -> str:
    venue_upper = venue.upper()
    if any(token in venue_upper for token in ("TPDS", "PVLDB", "PACMMOD", "TOCS", "TKDE", "TODS", "JMLR")):
        return "journal"
    return "conference"


def build_summary(abstract: str, limit: int = 140) -> str:
    text = " ".join(abstract.split())
    if len(text) <= limit:
        return text
    shortened = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return f"{shortened}."


def infer_tags(title: str, abstract: str, research_area: str, limit: int = 4) -> list[str]:
    tag_map = {
        "llm": "LLM",
        "language model": "language models",
        "training": "training",
        "distributed": "distributed systems",
        "storage": "storage",
        "metadata": "metadata management",
        "database": "database",
        "cloud": "cloud systems",
        "object storage": "object storage",
        "graph": "graph learning",
        "quantization": "quantization",
        "parallel": "parallel computing",
    }
    text = f"{title} {abstract} {research_area}".lower()
    tags: list[str] = []
    for needle, tag in tag_map.items():
        if needle in text and tag not in tags:
            tags.append(tag)
        if len(tags) >= limit:
            break
    if research_area and research_area not in tags and len(tags) < limit:
        tags.append(research_area)
    return tags


def infer_research_area(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    if any(term in text for term in ("rlhf", "llm", "language model", "post-training", "tensor parallelism")):
        return "distributed machine learning"
    if any(term in text for term in ("storage", "metadata", "object storage", "filesystem")):
        return "storage systems"
    if any(term in text for term in ("database", "transaction", "query")):
        return "distributed databases"
    if any(term in text for term in ("graph", "gnn", "vertex")):
        return "graph neural networks"
    return "parallel and distributed intelligent computing"


def sort_publications(publications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        publications,
        key=lambda item: (
            int(item.get("year") or 0),
            MONTH_ORDER.get(item.get("month", ""), 0),
            item.get("title", ""),
        ),
        reverse=True,
    )


def find_duplicate(publications: list[dict[str, Any]], slug: str, title: str) -> dict[str, Any] | None:
    title_normalized = " ".join(title.lower().split())
    for publication in publications:
        if publication.get("slug") == slug:
            return publication
        existing_title = " ".join(str(publication.get("title", "")).lower().split())
        if existing_title == title_normalized:
            return publication
    return None
