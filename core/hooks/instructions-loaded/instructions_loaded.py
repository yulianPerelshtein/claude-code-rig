#!/usr/bin/env python3
"""InstructionsLoaded hook — audit which instruction files entered context (#27).

Claude Code fires InstructionsLoaded when a CLAUDE.md or .claude/rules/*.md file
is loaded — at session start and on lazy loads (nested CLAUDE.md, paths:-globbed
rules, includes, post-compaction). This event has NO decision control and its
exit code is ignored; it exists purely for observability. We append one JSONL
line per load so you can later see exactly which instruction files loaded, when,
and why (debugging path-specific rules / lazy loads).

Each line: {ts, session_id, hook_event_name, file_path, memory_type, load_reason
[, globs, trigger_file_path, parent_file_path]}. Never raises; bounded via a
stat-then-trim rotation. Set CC_INSTRUCTIONS_LOG=0 to disable the audit entirely.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# utils/ lives at the hooks root (core/hooks/), one level up from this
# event subdirectory (core/hooks/instructions-loaded/).
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.constants import LOG_DIR, safe_session_id  # noqa: E402
from utils.hooklib import append_jsonl  # noqa: E402

LOG_NAME = "instructions_loaded.jsonl"
# keep_lines must stay under the ~512 KB rotate budget so a rotation actually
# trims: a line is ~280-380 B (ts + session_id + absolute file_path + reason,
# plus optional globs/paths), so 1200 lines ≈ 0.4 MB with headroom.
LOG_KEEP_LINES = 1200
# Optional fields, included only when the load reason supplies them.
OPTIONAL_FIELDS = ("globs", "trigger_file_path", "parent_file_path")
_OFF = {"0", "false", "no", "off"}


def logging_enabled() -> bool:
    return os.environ.get("CC_INSTRUCTIONS_LOG", "1").strip().lower() not in _OFF


def main() -> None:
    if not logging_enabled():
        sys.exit(0)
    try:
        data = json.loads(sys.stdin.read())

        entry = {
            "ts": datetime.now().isoformat(),
            "session_id": safe_session_id(data.get("session_id")),
            "hook_event_name": data.get("hook_event_name", "InstructionsLoaded"),
            "file_path": data.get("file_path", ""),
            "memory_type": data.get("memory_type", ""),
            "load_reason": data.get("load_reason", ""),
        }
        for field in OPTIONAL_FIELDS:
            value = data.get(field)
            if value:
                entry[field] = value

        append_jsonl(LOG_DIR / LOG_NAME, entry, LOG_KEEP_LINES)

    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
