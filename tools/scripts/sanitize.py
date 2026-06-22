#!/usr/bin/env python3
"""Scan a directory for company/vendor/project markers before sharing.

Verification, not mutation: shareable content is already sanitized at authoring
time, so any marker here is a redaction regression. Patterns are loaded from a
private source (the real identifiers are NOT tracked in this public repo), in
priority order: $REDACTION_PATTERNS_FILE, then redaction-patterns.local.txt
(gitignored), then redaction-patterns.txt (tracked template; placeholders).

Usage:
    python3 tools/scripts/sanitize.py <dir>
Exits 0 when clean, 1 with file:line hits.
"""

import os
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent


def _patterns_file() -> Path:
    env = os.environ.get("REDACTION_PATTERNS_FILE")
    if env and Path(env).is_file():
        return Path(env)
    local = _SCRIPTS_DIR / "redaction-patterns.local.txt"
    if local.is_file():
        return local
    return _SCRIPTS_DIR / "redaction-patterns.txt"


PATTERNS_FILE = _patterns_file()
TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg",
}
# The PreToolUse guardrail legitimately contains the Windows-mount path it
# blocks as an enforced WSL OS-isolation rule, not a content leak. For that file
# only, exempt that single pattern from the MARKER scan (mirrors the intent of
# .github/scripts/check-redactions.sh) — every other brand/vendor/project marker
# is still enforced, and verify-no-secrets.py still scans it for key shapes.
MARKER_EXEMPT_NAMES = {"guardrail.py"}
WSL_MOUNT_PATTERN = "/mnt/" + "c/"


def load_patterns() -> list[re.Pattern]:
    out = []
    for line in PATTERNS_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(re.compile(line, re.IGNORECASE))
    return out


def patterns_for(path: Path, patterns: list[re.Pattern]) -> list[re.Pattern]:
    """Patterns to apply to a file: the full set, minus the WSL-mount pattern for
    exempt files (so a guardrail.py may carry the Windows mount path it blocks
    but is still scanned for every brand/vendor/project marker)."""
    if path.name in MARKER_EXEMPT_NAMES:
        return [p for p in patterns if p.pattern != WSL_MOUNT_PATTERN]
    return patterns


def scan(root: Path, patterns: list[re.Pattern]) -> list[str]:
    hits = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        active = patterns_for(path, patterns)
        for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for pat in active:
                if pat.search(line):
                    hits.append(f"{path}:{lineno}: matched /{pat.pattern}/")
    return hits


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: sanitize.py <dir>", file=sys.stderr)
        sys.exit(2)
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        sys.exit(2)
    hits = scan(root, load_patterns())
    if hits:
        print("REDACTION MARKERS FOUND (export aborted):")
        for hit in hits:
            print(f"  {hit}")
        sys.exit(1)
    print(f"marker scan clean: {root}")


if __name__ == "__main__":
    main()
