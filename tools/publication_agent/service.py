from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .common import CONTENT_DIR, ROOT, find_duplicate, infer_research_area, infer_tags, load_json, save_json, slugify
from .parser import extract_pdf_metadata
from .schema import SubmissionMeta, build_publication_record, merge_submission_inputs
from .storage import (
    copy_pdf_to_assets,
    load_pending_publications,
    load_publications,
    save_pending_publications,
    save_publications,
)
from .validator import build_review_warnings, validate_publication_record


def load_submission(submission_dir: Path) -> tuple[Path, SubmissionMeta]:
    pdf_path = submission_dir / "paper.pdf"
    meta_path = submission_dir / "meta.json"
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing required PDF: {pdf_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing required metadata file: {meta_path}")

    with meta_path.open("r", encoding="utf-8") as handle:
        meta_payload = json.load(handle)

    meta = SubmissionMeta.from_dict(meta_payload)
    if not meta.status:
        raise ValueError("meta.json must include a non-empty 'status'.")
    return pdf_path, meta


def ensure_required_fields(record: dict[str, object]) -> None:
    errors = validate_publication_record(record)
    if errors:
        raise ValueError(
            "The scaffold could not build a complete publication entry. "
            f"Issues: {'; '.join(errors)}. "
            "Add these values manually or improve the parser/LLM config."
        )


def parse_preview(pdf_path: Path) -> dict[str, Any]:
    parsed = extract_pdf_metadata(pdf_path)
    research_area_guess = infer_research_area(parsed.title, parsed.abstract)
    tags_guess = infer_tags(parsed.title, parsed.abstract, research_area_guess)
    return {
        "title": parsed.title,
        "authors": parsed.authors,
        "abstract": parsed.abstract,
        "year": parsed.year,
        "research_area_guess": research_area_guess,
        "tags_guess": tags_guess,
    }


def create_record_from_submission_dir(submission_dir: Path) -> tuple[dict[str, Any], Path]:
    pdf_path, meta = load_submission(submission_dir)
    parsed = extract_pdf_metadata(pdf_path)
    merged = merge_submission_inputs(meta, parsed)
    target_slug_seed = slugify(merged.title or pdf_path.stem)
    copied_pdf = copy_pdf_to_assets(pdf_path, f"{target_slug_seed or 'paper'}.pdf")

    effective_meta = SubmissionMeta(
        status=meta.status,
        venue=meta.venue,
        month=meta.month,
        year=meta.year,
        research_area=meta.research_area or infer_research_area(merged.title, merged.abstract),
        project_slug=meta.project_slug,
        code_url=meta.code_url,
        award=meta.award,
        title=meta.title,
        authors=meta.authors,
        abstract=meta.abstract,
        tags=meta.tags or infer_tags(merged.title, merged.abstract, meta.research_area or infer_research_area(merged.title, merged.abstract)),
    )
    record = build_publication_record(effective_meta, parsed, copied_pdf)
    ensure_required_fields(record)
    record["_workflow"]["submitted_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    record["_workflow"]["warnings"] = build_review_warnings(record)
    return record, copied_pdf


def append_pending_record(record: dict[str, Any]) -> None:
    pending = load_pending_publications()
    duplicate = find_duplicate(pending, str(record["slug"]), str(record["title"]))
    if duplicate:
        raise ValueError(f"Duplicate pending publication: {record['slug']}")
    pending.append(record)
    save_pending_publications(pending)


def publish_record(record: dict[str, Any], remove_from_pending: bool = True) -> str:
    publications = load_publications()
    duplicate = find_duplicate(publications, str(record["slug"]), str(record["title"]))
    if duplicate:
        raise ValueError(f"Publication already exists in content/publications.json: {record['slug']}")

    published_entry = dict(record)
    published_entry.pop("_workflow", None)
    publications.append(published_entry)
    save_publications(publications)

    if remove_from_pending:
        pending = load_pending_publications()
        remaining = [item for item in pending if item.get("slug") != record["slug"]]
        if len(remaining) != len(pending):
            save_pending_publications(remaining)
    return str(record["slug"])


def publish_pending_slug(slug: str) -> str:
    pending = load_pending_publications()
    match = next((item for item in pending if item.get("slug") == slug), None)
    if not match:
        raise ValueError(f"No pending publication found for slug: {slug}")
    return publish_record(match, remove_from_pending=True)


def rebuild_site() -> None:
    venv_python = ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        cmd = [str(venv_python), "build.py", "--base-path", "/"]
    else:
        cmd = ["python3", "build.py", "--base-path", "/"]
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Unknown build failure"
        if "No module named 'markdown'" in detail:
            detail += " Please install the site dependency with: ./.venv/bin/python -m pip install markdown"
        raise RuntimeError(f"Site rebuild failed: {detail}")
