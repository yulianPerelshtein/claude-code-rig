#!/usr/bin/env python3
"""Scan a directory for secret files and key-shaped strings before sharing.

Mirrors the API-key + secret-file checks in .github/scripts/check-redactions.sh
and SHARING_STRATEGY.md §3 step 3. Any hit aborts the export.

Usage:
    python3 tools/scripts/verify-no-secrets.py <dir>
Exits 0 when clean, 1 otherwise.
"""

import re
import sys
from pathlib import Path

# Filenames that must never appear in a shareable bundle.
SECRET_GLOBS = (
    "*.env", "*.pem", "*.key", "*.p12", "*.pfx",
    "id_rsa*", "auth.json", "oauth_creds*", "*credentials*",
)
ENV_EXAMPLE = {".env.example", ".env.sample"}

# Well-known key prefixes with key-shaped suffixes.
KEY_RE = re.compile(
    r"(^|[^A-Za-z0-9])(gsk_[A-Za-z0-9]{40,}|sk-[A-Za-z0-9_-]{40,}"
    r"|xai-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}"
    r"|glpat-[A-Za-z0-9_-]{20,}|ABSK[A-Za-z0-9+/=]{40,})"
)
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt"}


def find_secret_files(root: Path) -> list[str]:
    hits = []
    for pattern in SECRET_GLOBS:
        for path in root.rglob(pattern):
            if path.is_file() and path.name not in ENV_EXAMPLE:
                hits.append(f"secret-shaped file: {path}")
    return hits


def find_key_strings(root: Path) -> list[str]:
    hits = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if KEY_RE.search(line):
                hits.append(f"{path}:{lineno}: key-shaped string")
    return hits


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: verify-no-secrets.py <dir>", file=sys.stderr)
        sys.exit(2)
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        sys.exit(2)
    hits = find_secret_files(root) + find_key_strings(root)
    if hits:
        print("SECRETS FOUND (export aborted):")
        for hit in hits:
            print(f"  {hit}")
        sys.exit(1)
    print(f"secret scan clean: {root}")


if __name__ == "__main__":
    main()
