#!/usr/bin/env python3
"""
Fetch repositories from a GitHub organization and update content/projects.json.

Usage:
  python tools/fetch_org_repos.py --org ORGANIZATION [--output content/projects.json] [--token YOUR_TOKEN]

Token can also be provided via environment variable `GITHUB_TOKEN`.

This script requires the `requests` package: `pip install requests`.
"""
import os
import sys
import argparse
import json
from typing import List

try:
    import requests
except Exception:
    print("Missing dependency 'requests'. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def slug_token(value: str) -> str:
    if not value:
        return ""
    # mimic labsite.render.slug_token: lower, replace '/' and '&' with space, split and join with '-'
    return "-".join(value.lower().replace("/", " ").replace("&", " ").split())


def get_repos(org: str, token: str = None) -> List[dict]:
    session = requests.Session()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos"
        params = {"per_page": 100, "page": page, "type": "public"}
        r = session.get(url, headers=headers, params=params, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
        data = r.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def load_json(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_json(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Keyword → category map
_CATEGORY_KEYWORDS = {
    "training": ["train", "twist", "megatron", "llm", "rl", "sft", "alignment"],
    "inference": ["infer", "serve", "sglang", "vllm", "llm", "chatbot", "arena"],
    "systems": ["system", "schedul", "cluster", "resource", "storage", "kv", "cache"],
    "benchmark": ["bench", "eval", "metric", "measure"],
}

# Known project name → category override
_CATEGORY_OVERRIDE = {
    "twist": "Training",
    "megatron-lm": "Infrastructure",
    "megatron_lm": "Infrastructure",
    "adacluster": "Systems",
    "tccl": "Training",
    "dhellam": "Training",
    "sglang": "Inference",
}

# Known project name → icon (abbreviation, max 3 chars)
_ICON_OVERRIDE = {
    "twist": "TW",
    "megatron-lm": "Meg",
    "megatron_lm": "Meg",
    "adacluster": "Ada",
    "tccl": "TC",
    "dhellam": "DH",
    "sglang": "SG",
}

# Known project name → status override (default to Active if repo has recent commits)
_STATUS_OVERRIDE = {}


def _infer_category(name: str, topics: list[str], description: str) -> str:
    # Explicit override wins
    name_lower = name.lower()
    for key, override in _CATEGORY_OVERRIDE.items():
        if key in name_lower:
            return override
    # Match topics/description keywords
    text = " ".join(topics).lower() + " " + (description or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category.capitalize()
    return "Systems"


def _infer_icon(name: str) -> str:
    name_lower = name.lower()
    if name_lower in _ICON_OVERRIDE:
        return _ICON_OVERRIDE[name_lower]
    # Fallback: first letter(s) of each dash-separated part, max 3
    parts = name.replace("-", " ").replace("_", " ").split()
    return "".join(p[0].upper() for p in parts[:3])


def _infer_status(repo: dict) -> str:
    name_lower = repo.get("name", "").lower()
    if name_lower in _STATUS_OVERRIDE:
        return _STATUS_OVERRIDE[name_lower]
    # Archival check
    if repo.get("archived", False):
        return "Archived"
    return "Active"


def build_entry(repo: dict) -> dict:
    name = repo.get("name") or ""
    description = repo.get("description") or ""
    topics = repo.get("topics") or []
    github_url = repo.get("html_url") or ""

    # summary: prefer description, else a short fallback
    summary = description if description else f"Code repository for {name}."

    category = _infer_category(name, topics, description)
    icon = _infer_icon(name)
    status = _infer_status(repo)
        return {
            "name": name,
            "title": name,
            "slug": slug_token(name),
            "summary": summary,
            "subtitle": "",
            "description": description,
            "icon": icon,
            "category": category,
            "status": status,
            "tags": topics,
            "homepage": repo.get("homepage") or "",
            "language": repo.get("language") or "",
            "url": github_url,
        }
    }


def merge_existing(existing: List[dict], new_entries: List[dict]) -> List[dict]:
    """
    Merge by URL if available, otherwise by name.
    Existing entries (local overrides) take priority for: icon, category, status, summary, tags.
    New entries (from GitHub API) provide: name, slug, description, links, homepage, language.
    """
        # Merge by URL if available, otherwise by name.
        # Preserve existing order. For existing entries, only update if any
        # of the tracked fields actually changed. Otherwise keep the original
        # entry (so unrelated fields or manual edits are preserved).
        key_of = lambda item: item.get("url") or item.get("name")
        existing_map = {key_of(e): e for e in existing if key_of(e)}
        new_map = {key_of(n): n for n in new_entries if key_of(n)}

        tracked_fields = [
            "name",
            "title",
            "summary",
            "subtitle",
            "description",
            "links",
            "tags",
            "topics",
            "language",
            "homepage",
            "url",
        ]

        merged: List[dict] = []
        seen_keys = set()

        # Update existing entries in original order
        for e in existing:
            key = key_of(e)
            if not key:
                merged.append(e)
                continue
            seen_keys.add(key)
            if key in new_map:
                n = new_map[key]
                # decide if update is needed by comparing tracked fields
                changed = False
                for f in tracked_fields:
                    ev = e.get(f)
                    nv = n.get(f)
                    if ev != nv:
                        changed = True
                        break
                if changed:
                    # merge: start from existing to preserve manual additions, then overwrite tracked fields
                    updated = dict(e)
                    for f in tracked_fields:
                        if f in n and n.get(f) is not None:
                            updated[f] = n.get(f)
                    merged.append(updated)
                else:
                    merged.append(e)
            else:
                merged.append(e)

        # Append new entries that weren't in existing
        for key, n in new_map.items():
            if key not in seen_keys:
                merged.append(n)

        return merged


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--org", required=True, help="GitHub organization or user")
    p.add_argument("--output", default="content/projects.json", help="Output JSON path")
    p.add_argument("--token", default=None, help="GitHub token (overrides GITHUB_TOKEN env)")
    p.add_argument(
        "--exclude-names",
        default="",
        help="Comma-separated repo names to exclude (default also excludes <org>.github.io)",
    )
    args = p.parse_args()

    token = args.token or os.getenv("GITHUB_TOKEN")
    # build exclude set (default: exclude the organization pages repo)
    excludes = set([n.strip() for n in args.exclude_names.split(",") if n.strip()])
    excludes.add(f"{args.org}.github.io")
    try:
        repos = get_repos(args.org, token)
    except Exception as e:
        print(f"Failed to fetch repos: {e}", file=sys.stderr)
        sys.exit(1)

    # filter excluded repos by name or by org pages url
    filtered = []
    for r in repos:
        name = r.get("name") or ""
        html_url = r.get("html_url") or ""
        if name in excludes:
            continue
        # also exclude explicit org pages URL pattern
        if html_url.lower().endswith(f"/{args.org}.github.io"):
            continue
        filtered.append(r)

    new_entries = [build_entry(r) for r in filtered]
    existing = load_json(args.output)
    merged = merge_existing(existing, new_entries)
    save_json(args.output, merged)
    print(f"Wrote {len(merged)} projects to {args.output}")


if __name__ == "__main__":
    main()
