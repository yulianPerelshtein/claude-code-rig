#!/usr/bin/env python3
"""SubagentStart hook — inject lightweight global context into a spawning subagent.

SubagentStart is a context-only event: plain stdout is NOT shown to the subagent
(it goes to the debug log). Context must be delivered via
hookSpecificOutput.additionalContext on exit 0. (Verified against the Claude Code
hooks docs.)

Mirrors session_start.sh's token discipline: NO full `cat` of learnings.md (that
is token waste paid on every subagent spawn). Distilled learnings load on demand
via /load-learnings or paths:-scoped domain skills. We only point the subagent at
its rules + surface a short project-CLAUDE.md reminder.
"""

import json
import os
import sys
from pathlib import Path


def main() -> None:
    try:
        # Drain stdin so the harness never blocks on an unread pipe.
        sys.stdin.read()

        parts = [
            "You are a sub-agent. Follow ~/.claude/CLAUDE.md (global rules) at all "
            "times. Distilled learnings are not auto-loaded — run /load-learnings or "
            "rely on paths:-scoped domain skills that surface on matching files.",
        ]

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if project_dir:
            project_claude = Path(project_dir) / ".claude" / "CLAUDE.md"
            if project_claude.is_file():
                parts.append(
                    f"This project has its own rules at {project_claude} — read "
                    "and follow them."
                )

        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStart",
                        "additionalContext": " ".join(parts),
                    }
                }
            )
        )
    except Exception:
        # Never break a subagent launch.
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
