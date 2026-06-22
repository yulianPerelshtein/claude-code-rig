"""Shared helpers for standalone hook scripts: stdin payload, env parsing, log rotation.

Kept tiny and dependency-free so each hook stays a self-contained `uv run python`
script (it still does `sys.path.insert(0, .../core/hooks)` then imports from
`utils`). Consolidated here so dream_loop.py, session_perf.py, and
user_prompt_submit.py share one implementation instead of drifting copies.
"""

import json
import os
import sys
from pathlib import Path


def int_env(name: str, default: int) -> int:
    """Parse an int env var defensively; never raises, always >= 1."""
    try:
        return max(1, int(os.environ.get(name) or default))
    except (TypeError, ValueError):
        return default


def read_payload() -> dict:
    """SessionEnd (etc.) passes JSON on stdin; cron passes nothing. Tolerate both."""
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError, OSError):
        return {}


def rotate_jsonl_log(path: Path, keep_lines: int, max_bytes: int = 512_000) -> None:
    """Cap an append-only log: a cheap stat, trimming to the last `keep_lines`
    only once it grows past `max_bytes`. Guarded — never raises.

    `keep_lines` MUST be small enough that the retained text sits comfortably
    under `max_bytes`, otherwise the trim sheds nothing and every subsequent
    append re-reads+rewrites the whole file (the O(n) anti-pattern this avoids).
    """
    try:
        if path.stat().st_size < max_bytes:
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        path.write_text("\n".join(lines[-keep_lines:]) + "\n", encoding="utf-8")
    except OSError:
        return


def append_jsonl(
    path: Path, entry: dict, keep_lines: int, max_bytes: int = 512_000
) -> None:
    """Append `entry` as one JSONL line (creating parents), then rotate the log.

    The single place every hook writes an append-only JSONL log, so the
    rotate-after-append contract lives in one spot. Not internally guarded: the
    caller wraps it in its own try/except to honour each hook's never-raises
    contract (some callers swallow only OSError, others Exception)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    rotate_jsonl_log(path, keep_lines, max_bytes)
