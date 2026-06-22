#!/usr/bin/env python3
"""Validator: enforces TDD task ordering in plan documents.

Usage:
    uv run python core/hooks/validators/validate_tdd_tasks.py \
        --directory specs --extension .md \
        --contains-before 'TDD|Write tests|Test Definition' 'Implement|Build|Create'

Finds the most recently modified file matching the extension in the
directory, then verifies:
  1. At least one task/section matches the first pattern (TDD-related)
  2. The first TDD match appears BEFORE the first implementation match

Exits 0 if valid, exits 2 if no TDD task found or TDD appears after implementation.
"""

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_TDD_PATTERN = r"(?:TDD|Write tests|Test Definition)"
DEFAULT_IMPL_PATTERN = r"(?:Implement|Build|Create|Code the)"


def find_first(lines: list[str], pattern: str) -> tuple[int, str] | None:
    for i, line in enumerate(lines, start=1):
        if re.search(pattern, line, re.IGNORECASE):
            return (i, line.strip())
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--extension", required=True)
    parser.add_argument(
        "--contains-before", nargs=2, metavar=("TDD_PATTERN", "IMPL_PATTERN")
    )
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

    tdd_pat = args.contains_before[0] if args.contains_before else DEFAULT_TDD_PATTERN
    impl_pat = args.contains_before[1] if args.contains_before else DEFAULT_IMPL_PATTERN

    lines = files[0].read_text(encoding="utf-8").splitlines()
    first_tdd = find_first(lines, tdd_pat)
    first_imp = find_first(lines, impl_pat)

    if first_tdd is None:
        print(f"File '{files[0].name}' has no TDD/testing task.", file=sys.stderr)
        print(f"  Expected pattern: {tdd_pat}", file=sys.stderr)
        print("\nEvery plan must include a TDD task.", file=sys.stderr)
        if first_imp:
            print(
                f"  Implementation found at line {first_imp[0]}: {first_imp[1][:100]}",
                file=sys.stderr,
            )
        sys.exit(2)

    if first_imp is not None and first_tdd[0] > first_imp[0]:
        print(
            f"File '{files[0].name}' has TDD task AFTER implementation task:",
            file=sys.stderr,
        )
        print(
            f"  Implementation at line {first_imp[0]}: {first_imp[1][:100]}",
            file=sys.stderr,
        )
        print(
            f"  TDD task at line {first_tdd[0]}: {first_tdd[1][:100]}", file=sys.stderr
        )
        print("\nTDD tasks must appear BEFORE implementation tasks.", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
