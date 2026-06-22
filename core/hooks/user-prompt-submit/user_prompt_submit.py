#!/usr/bin/env python3
"""UserPromptSubmit hook — append-only JSONL prompt audit trail.

Migrated from a whole-file JSON read+rewrite (the O(n)/unbounded-growth
anti-pattern already fixed in session_end.py, OPTIMIZATION_AUDIT §2.10) to an
append-only JSONL line per prompt with richer fields (turn index, timestamp,
session_id). This both removes the per-prompt rewrite cost and makes the prompt
stream analyzable by the session performance analyzer (session_perf.py,
ENHANCEMENTS_BACKLOG §2.10).

Each line: {session_id, hook_event_name, turn, ts, prompt_length, prompt_preview}.
Never raises; bounded via a cheap stat-then-trim rotation.

Privacy: prompt_preview captures the first PREVIEW_LEN chars of prompt text (the
prior behaviour, and what cross-session near-duplicate detection needs). Set
CC_PROMPT_LOG=0 to log metadata only (length/turn/ts/session_id, empty preview);
correction-density analysis still works from prompt_length. Everything lands
under ~/.claude/data/, which inherits the SECURITY_REVIEW §6 exclusion.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# utils/ lives at the hooks root (core/hooks/), one level up from this
# event subdirectory (core/hooks/user-prompt-submit/).
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import (  # noqa: E402
    LOG_DIR,
    ensure_session_log_dir,
    safe_session_id,
)
from utils.hooklib import append_jsonl  # noqa: E402

PROMPT_LOG_NAME = "user_prompt_submit.jsonl"
PREVIEW_LEN = 120
# Retention: keep_lines must stay well under ~512 KB so a rotation actually trims
# (a prompt line is ~140-250 B; 1500 lines ≈ 300 KB, leaving headroom). With a
# larger keep the trim would shed nothing and re-introduce the O(n) rewrite.
LOG_KEEP_LINES = 1500
_OFF = {"0", "false", "no", "off"}


def preview_enabled() -> bool:
    """CC_PROMPT_LOG=0 logs metadata only (no on-disk prompt text)."""
    return os.environ.get("CC_PROMPT_LOG", "1").strip().lower() not in _OFF


def next_turn(session_id: str) -> int:
    """Per-session monotonic turn index via a tiny O(1) sidecar counter under the
    session log dir. Best-effort: any failure returns 0 rather than raising, so a
    counter glitch never costs the audit line."""
    try:
        counter = ensure_session_log_dir(session_id) / "prompt_turn"
        try:
            current = int(counter.read_text().strip())
        except (OSError, ValueError):
            current = 0
        turn = current + 1
        counter.write_text(str(turn))
        return turn
    except OSError:
        return 0


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
        prompt = data.get("prompt", "")
        session_id = safe_session_id(data.get("session_id"))
        preview = prompt[:PREVIEW_LEN] if (prompt and preview_enabled()) else ""

        entry = {
            "session_id": session_id,
            "hook_event_name": data.get("hook_event_name", "UserPromptSubmit"),
            "turn": next_turn(session_id),
            "ts": datetime.now().isoformat(),
            "prompt_length": len(prompt),
            "prompt_preview": preview,
        }
        append_jsonl(LOG_DIR / PROMPT_LOG_NAME, entry, LOG_KEEP_LINES)

    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
