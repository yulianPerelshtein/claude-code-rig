"""
Constants for Claude Code global hooks.

LOG_DIR points to the active project's .claude/data/logs/ when
CLAUDE_PROJECT_DIR is set, otherwise falls back to ~/.claude/data/logs/.
"""

import os
import re
from pathlib import Path

# session_id is used to build log/summary paths; treat it as untrusted input.
# fullmatch (not match) so a trailing newline can't slip past the `$` anchor.
_SAFE_SESSION = re.compile(r"[A-Za-z0-9_-]+")


def safe_session_id(session_id: str | None) -> str:
    """Return session_id if it is a safe path component, else 'unknown'.

    Blocks path traversal (``../``), absolute paths, null bytes, and control
    characters (incl. a trailing newline) from reaching the filesystem via an
    attacker-controlled session_id."""
    return (
        session_id if session_id and _SAFE_SESSION.fullmatch(session_id) else "unknown"
    )


_project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
if _project_dir:
    LOG_DIR = Path(_project_dir) / ".claude" / "data" / "logs"
else:
    LOG_DIR = Path.home() / ".claude" / "data" / "logs"

# Home-based data store shared by the continuous-improvement loop. Unlike LOG_DIR
# these are intentionally NOT project-scoped: the dream loop consolidates across
# every project's sessions, so summaries and reports need one stable location.
# All under ~/.claude/data/ so they inherit the SECURITY_REVIEW §6 exclusion.
DATA_DIR = Path.home() / ".claude" / "data"
SESSION_SUMMARY_DIR = DATA_DIR / "session-summaries"
DREAM_REPORT_DIR = DATA_DIR / "dream-reports"
DREAM_LOG = DATA_DIR / "dream-loop.log"

# Session performance analyzer (item #30): the deterministic Layer-1 scorer
# writes flagged-session reports here and one JSONL telemetry line per run to
# SESSION_PERF_LOG. COST_LOG is the home-based cost log written by the
# cost_tracker.py Stop hook (NOT project-scoped — costs are keyed by session_id).
SESSION_PERF_DIR = DATA_DIR / "session-perf"
SESSION_PERF_LOG = DATA_DIR / "session-perf.log"
COST_LOG = Path.home() / ".claude" / "cost-log.jsonl"


def get_session_log_dir(session_id: str) -> Path:
    """Get the log directory for a specific session (session_id sanitized)."""
    return LOG_DIR / safe_session_id(session_id)


def ensure_session_log_dir(session_id: str) -> Path:
    """Ensure the log directory for a session exists and return it."""
    log_dir = get_session_log_dir(session_id)
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir
