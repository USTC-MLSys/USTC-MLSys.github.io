from __future__ import annotations

import argparse
from pathlib import Path

import sys

from .service import append_pending_record, create_record_from_submission_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a pending publication entry from a submission folder.")
    parser.add_argument("--submission", required=True, help="Path to a folder containing paper.pdf and meta.json.")
    return parser.parse_args()


def main() -> str:
    args = parse_args()
    submission_dir = Path(args.submission).resolve()
    record, copied_pdf = create_record_from_submission_dir(submission_dir)
    append_pending_record(record)
    print(f"Created pending publication: {record['slug']}")
    print(f"PDF copied to: {copied_pdf}")
    if record["_workflow"]["warnings"]:
        print("Review warnings:")
        for warning in record["_workflow"]["warnings"]:
            print(f"- {warning}")
    return str(record["slug"])


if __name__ == "__main__":
    main()
