from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .common import PAPERS_DIR, PENDING_PUBLICATIONS_PATH, PUBLICATIONS_PATH, load_json, save_json, sort_publications


def copy_pdf_to_assets(source: Path, target_name: str) -> Path:
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    target = PAPERS_DIR / target_name
    shutil.copy2(source, target)
    return target


def load_publications() -> list[dict[str, Any]]:
    return load_json(PUBLICATIONS_PATH, [])


def load_pending_publications() -> list[dict[str, Any]]:
    return load_json(PENDING_PUBLICATIONS_PATH, [])


def save_publications(publications: list[dict[str, Any]]) -> None:
    save_json(PUBLICATIONS_PATH, sort_publications(publications))


def save_pending_publications(publications: list[dict[str, Any]]) -> None:
    save_json(PENDING_PUBLICATIONS_PATH, publications)
