from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_content(content_dir: Path) -> dict[str, Any]:
    # Load site-wide JSON files
    bundle = {
        "site": load_json(content_dir / "site.json"),
        "projects": load_json(content_dir / "projects.json"),
        "news": load_json(content_dir / "news.json"),
        "team": load_json(content_dir / "team.json"),
    }

    # Load publications
    if (content_dir / "publications.json").exists():
        bundle["publications"] = load_json(content_dir / "publications.json")
    else:
        bundle["publications"] = []

    # Backwards-compatible blog loading: expect a single blog.json bundle
    bundle["blog"] = load_json(content_dir / "blog.json")

    return bundle


def sort_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        projects,
        key=lambda item: (item.get("featured", False), int(item.get("year") or 0), item["title"]),
        reverse=True,
    )


def sort_blog(blog_posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        blog_posts,
        key=lambda item: (item.get("date", ""), item["title"]),
        reverse=True,
    )


def sort_publications(publications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    month_order = {
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
    return sorted(
        publications,
        key=lambda item: (int(item.get("year") or 0), month_order.get(item.get("month", ""), 0), item["title"]),
        reverse=True,
    )


def sort_news(news_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(news_items, key=lambda item: item.get("date", ""), reverse=True)


def sort_team(team: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_order = {"faculty": 0, "postdoc": 1, "phd": 2, "master": 3, "engineer": 4, "alumni": 5}
    return sorted(team, key=lambda member: (group_order.get(member.get("group", ""), 99), member["name"]))


def as_index(items: list[dict[str, Any]], key: str = "slug") -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}
