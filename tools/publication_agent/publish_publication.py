from __future__ import annotations

import argparse
import sys

from .service import publish_pending_slug, rebuild_site


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move a pending publication into the published collection.")
    parser.add_argument("--slug", required=True, help="Slug of the pending publication to publish.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    slug = publish_pending_slug(args.slug)
    rebuild_site()
    print(f"Published: {slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
