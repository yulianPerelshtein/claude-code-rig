#!/usr/bin/env python3
"""SessionEnd hook — logs the session-end event and writes a session summary.

The summary (session metrics + the first prompts + last results) is the raw
material the continuous-improvement / dream loop consolidates later
(`dream_loop.py`, items #3 + #12). It is written to
~/.claude/data/session-summaries/<date>-<session-id>.md and never raises.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# utils/ lives at the hooks root (core/hooks/), one level up from this
# event subdirectory (core/hooks/session/).
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import (  # noqa: E402
    LOG_DIR,
    SESSION_SUMMARY_DIR,
    safe_session_id,
)

MAX_TRANSCRIPT_LINES = 5000  # bound the read; transcripts can be huge
MAX_PROMPTS = 5
MAX_RESULTS = 5
SNIPPET_LEN = 280
# Off-switches (default on). CC_SESSION_SUMMARY=0 disables writing the
# prompt/result summary; the continuous-improvement loop then has nothing to
# consolidate. Documented in playbooks/continuous-improvement/sleep-dream-mode.md.
_OFF = {"0", "false", "no", "off"}


def summaries_enabled() -> bool:
    return os.environ.get("CC_SESSION_SUMMARY", "1").strip().lower() not in _OFF


def log_event(data: dict) -> None:
    """Append the session-end event as one JSONL line (O(1), bounded growth)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "session_id": data.get("session_id", "unknown"),
        "hook_event_name": data.get("hook_event_name", "SessionEnd"),
        "reason": data.get("reason", "other"),
        "logged_at": datetime.now().isoformat(),
    }
    with (LOG_DIR / "session_end.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def extract_text(content: object) -> str:
    """Pull text from a message content that is a string or a list of blocks."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        return "\n".join(p for p in parts if p).strip()
    return ""


def parse_transcript(path: Path) -> tuple[list[str], list[str], int]:
    """Return (user_prompts, assistant_results, message_count) from a JSONL
    transcript, bounded to MAX_TRANSCRIPT_LINES. Best-effort; tolerates schema
    drift and bad lines."""
    prompts: list[str] = []
    results: list[str] = []
    count = 0
    with path.open(encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= MAX_TRANSCRIPT_LINES:
                break
            try:
                entry = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            message = entry.get("message") if isinstance(entry, dict) else None
            if not isinstance(message, dict):
                continue
            role = message.get("role") or entry.get("type")
            text = extract_text(message.get("content"))
            if not text:
                continue
            count += 1
            if role == "user":
                prompts.append(text)
            elif role == "assistant":
                results.append(text)
    return prompts, results, count


def render_summary(
    data: dict, prompts: list[str], results: list[str], count: int
) -> str:
    """Build the markdown session summary."""
    sid = data.get("session_id", "unknown")
    lines = [
        f"# Session summary — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Session: `{sid}`",
        f"- End reason: {data.get('reason', 'other')}",
        f"- Project: {data.get('cwd', '(unknown)')}",
        f"- Messages with text: {count} "
        f"({len(prompts)} user, {len(results)} assistant)",
        "",
        "## First prompts",
        "",
    ]
    head = prompts[:MAX_PROMPTS] or ["(none captured)"]
    lines += [f"- {p[:SNIPPET_LEN].replace(chr(10), ' ')}" for p in head]
    lines += ["", "## Last results", ""]
    tail = results[-MAX_RESULTS:] or ["(none captured)"]
    lines += [f"- {r[:SNIPPET_LEN].replace(chr(10), ' ')}" for r in tail]
    lines.append("")
    return "\n".join(lines)


def write_summary(data: dict) -> None:
    """Write the per-session markdown summary; skip quietly if disabled or no
    transcript."""
    if not summaries_enabled():
        return
    transcript = data.get("transcript_path", "")
    if not transcript:
        return
    path = Path(transcript).expanduser()
    if not path.is_file():
        return
    prompts, results, count = parse_transcript(path)
    SESSION_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    sid = safe_session_id(data.get("session_id"))
    out = SESSION_SUMMARY_DIR / f"{datetime.now().strftime('%Y%m%d')}-{sid}.md"
    out.write_text(render_summary(data, prompts, results, count), encoding="utf-8")


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError, OSError):
        sys.exit(0)
    try:
        log_event(data)
    except Exception:
        pass
    try:
        write_summary(data)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
