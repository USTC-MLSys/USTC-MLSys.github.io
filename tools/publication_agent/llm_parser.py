from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .schema import ParsedPaper


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"


def read_llm_config() -> dict[str, str]:
    return {
        "api_key": os.getenv("DEEPSEEK_API_KEY", "").strip(),
        "base_url": os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).strip().rstrip("/"),
        "model": os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip(),
    }


def llm_is_enabled() -> bool:
    return bool(read_llm_config()["api_key"])


def _build_prompt(raw_text: str, heuristic: ParsedPaper) -> str:
    heuristic_json = json.dumps(asdict(heuristic), ensure_ascii=False, indent=2)
    excerpt = raw_text[:12000]
    return (
        "You are extracting metadata from a research paper PDF.\n"
        "Return ONLY valid JSON with keys: title, authors, abstract, year.\n"
        "Rules:\n"
        "- title: string\n"
        "- authors: array of author names in order\n"
        "- abstract: string\n"
        "- year: integer or null\n"
        "- Do not include affiliations in authors.\n"
        "- Do not include markdown fences or explanations.\n\n"
        "Heuristic extraction result:\n"
        f"{heuristic_json}\n\n"
        "Raw PDF text excerpt:\n"
        f"{excerpt}"
    )


def _post_chat_completion(prompt: str, config: dict[str, str]) -> dict[str, Any]:
    url = f"{config['base_url']}/chat/completions"
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": "You extract structured metadata from paper PDFs."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek API connection failed: {exc}") from exc

    payload = json.loads(body)
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected DeepSeek response payload: {payload}") from exc
    return json.loads(content)


def _sanitize_llm_result(result: dict[str, Any], heuristic: ParsedPaper) -> ParsedPaper:
    title = str(result.get("title") or heuristic.title or "").strip()
    abstract = str(result.get("abstract") or heuristic.abstract or "").strip()
    raw_authors = result.get("authors") or heuristic.authors or []
    if not isinstance(raw_authors, list):
        raw_authors = heuristic.authors or []
    authors = [str(author).strip() for author in raw_authors if str(author).strip()]
    year_value = result.get("year", heuristic.year)
    year = int(year_value) if isinstance(year_value, int) or (isinstance(year_value, str) and year_value.isdigit()) else heuristic.year
    return ParsedPaper(title=title, authors=authors, abstract=abstract, year=year)


def enrich_with_llm(raw_text: str, heuristic: ParsedPaper) -> ParsedPaper:
    config = read_llm_config()
    if not config["api_key"]:
        return heuristic
    result = _post_chat_completion(_build_prompt(raw_text, heuristic), config)
    return _sanitize_llm_result(result, heuristic)
