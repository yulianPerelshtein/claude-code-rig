#!/usr/bin/env python3
"""Validator: checks that files do NOT contain placeholder patterns.

Usage:
    uv run python core/hooks/validators/validate_no_placeholders.py \
        --directory specs --extension .md \
        --not-contains '[To be detailed]' \
        --not-contains 'TODO: flesh out'

Finds the most recently modified file matching the extension in the
directory, then checks it does NOT contain any of the forbidden
placeholder patterns. Exits 0 if clean, exits 2 with descriptive
error listing all found placeholders and their line numbers.
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_PATTERNS = [
    r"\[To be detailed",
    r"TODO:\s*flesh out",
    r"\[placeholder\]",
    r"\bTBD\b",
    r"\[INSERT",
    r"<describe",
    r"<list",
    r"<clearly",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--extension", required=True)
    parser.add_argument("--not-contains", action="append")
    args = parser.parse_args()

    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = hook_input.get("cwd", ".")
    search_dir = Path(cwd) / args.directory
    if not search_dir.exists():
        sys.exit(0)

    ext = args.extension if args.extension.startswith(".") else f".{args.extension}"
    files = sorted(
        search_dir.glob(f"*{ext}"), key=lambda f: f.stat().st_mtime, reverse=True
    )
    if not files:
        sys.exit(0)

    patterns = args.not_contains if args.not_contains else DEFAULT_PATTERNS
    lines = files[0].read_text(encoding="utf-8").splitlines()

    found: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines, start=1):
        for pat in patterns:
            if re.search(pat, line, re.IGNORECASE):
                found.append((i, pat, line.strip()))

    if found:
        print(
            f"File '{files[0].name}' contains skeleton/placeholder content:",
            file=sys.stderr,
        )
        for line_num, pat, text in found:
            print(f"  Line {line_num}: matched '{pat}'", file=sys.stderr)
            print(f"    > {text[:120]}", file=sys.stderr)
        print(
            "\nPlease flesh out all placeholder sections before finalizing.",
            file=sys.stderr,
        )
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
