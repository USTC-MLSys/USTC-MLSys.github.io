from __future__ import annotations

import argparse
import json
import sys

from .storage import load_pending_publications
from .validator import build_review_warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect pending publication entries.")
    parser.add_argument("--slug", help="Show the full JSON payload for a specific pending entry.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pending = load_pending_publications()
    if not pending:
        print("No pending publications.")
        return 0

    if args.slug:
        match = next((item for item in pending if item.get("slug") == args.slug), None)
        if not match:
            raise ValueError(f"No pending publication found for slug: {args.slug}")
        print(json.dumps(match, ensure_ascii=False, indent=2))
        return 0

    for item in pending:
        print(f"- {item.get('slug')}")
        print(f"  title: {item.get('title')}")
        print(f"  venue: {item.get('venue')} {item.get('year')}")
        print(f"  authors: {', '.join(item.get('authors', []))}")
        print(f"  workflow status: {item.get('_workflow', {}).get('status', '')}")
        warnings = build_review_warnings(item)
        if warnings:
            print("  warnings:")
            for warning in warnings:
                print(f"    - {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
